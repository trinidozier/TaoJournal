import os
import json
import shutil
import tempfile
import time
import logging
import io
import base64
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from fastapi import (
    FastAPI, HTTPException, UploadFile, File, Query,
    status, Depends, Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import matplotlib.pyplot as plt
from jose import jwt, JWTError
from tda.auth import easy_client
from tda.client import Client
from cryptography.fernet import Fernet
import pandas as pd
from db import engine, metadata, database, users, strategies, trade_rules, brokers, trades
from auth import hash_password, verify_password
from import_trades import parse_smart_csv
from grouping import group_trades_by_entry_exit
from export_tools import export_to_excel as export_excel_util, export_to_pdf as export_pdf_util
from analytics import compute_summary_stats, compute_by_strategy, compute_by_rule, compute_by_trade_type, compute_by_hour, compute_by_day_of_week, compute_risk_metrics, compute_behavioral_insights, compute_equity_curve, compute_heatmap_hour, compute_heatmap_day
from schemas import Strategy, StrategyCreate, Rule, RuleCreate, TradeIn, Trade, UserCreate, IBKRConnect, TradeRuleUpdate, Broker, BrokerCreate
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from sqlalchemy import select
from collections import defaultdict

load_dotenv()

# ─── Config & Logging ────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
SCHWAB_CLIENT_ID = os.getenv("SCHWAB_CLIENT_ID")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
IBKR_PORT = os.getenv("IBKR_PORT", "7497")
SAVE_FILE = "annotated_trades.json"
BACKUP_DIR = "backups"
MAX_BACKUPS = 10
IMAGE_FOLDER = "trade_images"
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Encryption helpers
def encrypt_data(data: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted.encode()).decode()

# ─── JSON Storage Helpers ────────────────────────────────────────────────────
def atomic_write_json(path: str, data: List[dict]):
    dirpath = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, text=True)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, default=str, indent=2)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        os.remove(tmp)
        raise

def rotate_backups(src: str):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    dst = os.path.join(BACKUP_DIR, f"trades-{timestamp}.json")
    shutil.copy2(src, dst)
    backs = sorted(os.listdir(BACKUP_DIR))
    while len(backs) > MAX_BACKUPS:
        os.remove(os.path.join(BACKUP_DIR, backs.pop(0)))

def load_all_trades() -> List[dict]:
    if not os.path.exists(SAVE_FILE):
        return []
    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error loading trades: {e}")
        return []

def load_trades(user_email: str) -> List[dict]:
    trades = [t for t in load_all_trades() if t.get("user") == user_email]
    for idx, trade in enumerate(trades):
        trade['id'] = idx
    return trades

def save_trades(user_trades: List[dict], user_email: str):
    all_trades = load_all_trades()
    others = [t for t in all_trades if t.get("user") != user_email]
    merged = others + user_trades
    if os.path.exists(SAVE_FILE):
        rotate_backups(SAVE_FILE)
    atomic_write_json(SAVE_FILE, merged)

def filter_by_date(trades: List[dict], start: Optional[date], end: Optional[date]) -> List[dict]:
    if not start and not end:
        return trades
    out = []
    for t in trades:
        ts = t.get("buy_timestamp") or t.get("timestamp") or t.get("BuyTimestamp")
        try:
            dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
            d = dt.date()
        except Exception as e:
            logger.error(f"Error parsing timestamp for trade {t}: {e}")
            continue
        if (not start or d >= start) and (not end or d <= end):
            out.append(t)
    return out

# ─── FastAPI Setup ───────────────────────────────────────────────────────────
app = FastAPI()

# Explicit CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://taojournal-production.up.railway.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Global exception handler to log errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers={"Access-Control-Allow-Origin": request.headers.get("origin", "*")}
    )

# ─── Database Connection ─────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    try:
        await database.connect()
        logger.info("Database connected successfully")
        scheduler = AsyncIOScheduler(timezone=timezone('US/Pacific'))
        scheduler.start()
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    try:
        await database.disconnect()
        logger.info("Database disconnected successfully")
    except Exception as e:
        logger.error(f"Database disconnection error: {e}")

# ─── Auth ────────────────────────────────────────────────────────────────────
def get_current_user_email(token: str = Depends(oauth2_scheme)) -> str:
    logger.debug(f"Validating token: {token[:10]}...")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Invalid token: No email in payload")
            raise HTTPException(status_code=401, detail="Invalid token")
        logger.debug(f"Token validated for user: {email}")
        return email
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info(f"Login attempt for user: {form_data.username}")
    query = users.select().where(users.c.email == form_data.username)
    try:
        user = await database.fetch_one(query)
        if not user or not verify_password(form_data.password, user["hashed_password"]):
            logger.warning(f"Invalid credentials for user: {form_data.username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        access_token = jwt.encode(
            {"sub": user["email"], "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        logger.info(f"Login successful for user: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Login error for user {form_data.username}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/register", response_model=UserCreate)
async def register(user: UserCreate):
    logger.info(f"Register attempt for email: {user.email}")
    hashed_password = hash_password(user.password)
    query = users.insert().values(
        first_name=user.first_name,
        last_name=user.last_name,
        billing_address=user.billing_address,
        email=user.email,
        hashed_password=hashed_password,
        is_active=True
    )
    try:
        await database.execute(query)
        logger.info(f"User registered: {user.email}")
        return user
    except Exception as e:
        logger.error(f"Registration error for {user.email}: {e}")
        raise HTTPException(status_code=400, detail="Email already registered")

# ─── Trades ──────────────────────────────────────────────────────────────────
@app.get("/trades", response_model=List[Trade])
async def get_trades(start_date: Optional[str] = None, end_date: Optional[str] = None, email: str = Depends(get_current_user_email)):
    logger.info(f"Fetching trades for user: {email}")
    start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    try:
        query = trades.select().where(trades.c.user == email)
        db_trades = await database.fetch_all(query)
        filtered = filter_by_date([dict(t) for t in db_trades], start, end)
        logger.info(f"Retrieved {len(filtered)} trades for user: {email}")
        return filtered
    except Exception as e:
        logger.error(f"Error fetching trades for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/trades", response_model=Trade)
async def create_trade(trade: TradeIn, email: str = Depends(get_current_user_email)):
    logger.info(f"Creating trade for user: {email}")
    try:
        # Validate required fields
        if not all([trade.buy_price is not None, trade.sell_price is not None, trade.qty is not None]):
            logger.error(f"Missing required fields in trade: {trade.dict()}")
            raise HTTPException(status_code=400, detail="Missing required fields: buy_price, sell_price, qty")
        
        direction = trade.direction or ("Long" if trade.sell_price > trade.buy_price else "Short")
        qty = trade.qty
        buy_price = trade.buy_price
        sell_price = trade.sell_price
        fees = trade.fees or 0
        stop = trade.stop or buy_price * (0.9 if direction == "Long" else 1.1)
        r_multiple = 0 if not stop else (
            (sell_price - buy_price) / (buy_price - stop) if direction == "Long" else
            (buy_price - sell_price) / (stop - buy_price)
        )
        r_multiple = round(r_multiple, 2)
        multiplier = qty * 100 if trade.trade_type in ("Call", "Put", "Straddle", "Covered Call", "Cash Secured Put") else qty
        pnl = round((sell_price - buy_price) * multiplier - fees, 2) if direction == "Long" else round((buy_price - sell_price) * multiplier - fees, 2)

        query = trades.insert().values(
            buy_price=buy_price,
            sell_price=sell_price,
            stop=stop,
            direction=direction,
            pnl=pnl,
            r_multiple=r_multiple,
            timestamp=trade.buy_timestamp or datetime.utcnow().isoformat(),
            user=email
        )
        trade_id = await database.execute(query)
        logger.info(f"Trade created with ID {trade_id} for user: {email}")
        return {
            "id": trade_id,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "stop": stop,
            "direction": direction,
            "pnl": pnl,
            "r_multiple": r_multiple,
            "timestamp": trade.buy_timestamp or datetime.utcnow().isoformat(),
            "user": email
        }
    except Exception as e:
        logger.error(f"Error creating trade for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/import_csv")
async def import_csv(file: UploadFile = File(...), email: str = Depends(get_current_user_email)):
    logger.info(f"Importing CSV for user: {email}")
    try:
        content = await file.read()
        trades_data = parse_smart_csv(io.BytesIO(content))
        inserted_trades = []
        for trade in trades_data:
            # Validate required fields
            if not all([trade.get("buy_price") is not None, trade.get("sell_price") is not None, trade.get("qty") is not None]):
                logger.warning(f"Skipping invalid trade: {trade}")
                continue
            direction = trade.get("direction", "Long")
            qty = trade["qty"]
            buy_price = trade["buy_price"]
            sell_price = trade["sell_price"]
            fees = trade.get("fees", 0)
            stop = trade.get("stop", buy_price * (0.9 if direction == "Long" else 1.1))
            r_multiple = 0 if not stop else (
                (sell_price - buy_price) / (buy_price - stop) if direction == "Long" else
                (buy_price - sell_price) / (stop - buy_price)
            )
            r_multiple = round(r_multiple, 2)
            multiplier = qty * 100 if trade.get("trade_type", "Stock") in ("Call", "Put", "Straddle", "Covered Call", "Cash Secured Put") else qty
            pnl = round((sell_price - buy_price) * multiplier - fees, 2) if direction == "Long" else round((buy_price - sell_price) * multiplier - fees, 2)

            query = trades.insert().values(
                buy_price=buy_price,
                sell_price=sell_price,
                stop=stop,
                direction=direction,
                pnl=pnl,
                r_multiple=r_multiple,
                timestamp=trade.get("buy_timestamp", datetime.utcnow().isoformat()),
                user=email
            )
            trade_id = await database.execute(query)
            inserted_trades.append(trade_id)
        logger.info(f"Imported {len(inserted_trades)} trades for user: {email}")
        return {"message": f"Imported {len(inserted_trades)} trades"}
    except Exception as e:
        logger.error(f"Error importing CSV for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ─── Strategies ──────────────────────────────────────────────────────────────
@app.get("/strategies", response_model=List[Strategy])
async def get_strategies(email: str = Depends(get_current_user_email)):
    logger.info(f"Fetching strategies for user: {email}")
    try:
        query = strategies.select().where(strategies.c.user_email == email)
        result = await database.fetch_all(query)
        logger.info(f"Retrieved {len(result)} strategies for user: {email}")
        return result
    except Exception as e:
        logger.error(f"Error fetching strategies for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/strategies", response_model=Strategy)
async def create_strategy(strategy: StrategyCreate, email: str = Depends(get_current_user_email)):
    logger.info(f"Creating strategy for user: {email}")
    try:
        query = strategies.insert().values(
            name=strategy.name,
            description=strategy.description,
            user_email=email,
        )
        strategy_id = await database.execute(query)
        logger.info(f"Strategy created with ID {strategy_id} for user: {email}")
        return {**strategy.dict(), "id": strategy_id, "user_email": email, "created_at": datetime.utcnow()}
    except Exception as e:
        logger.error(f"Error creating strategy for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put("/strategies/{strategy_id}", response_model=Strategy)
async def update_strategy(strategy_id: int, strategy: StrategyCreate, email: str = Depends(get_current_user_email)):
    logger.info(f"Updating strategy {strategy_id} for user: {email}")
    try:
        query = strategies.select().where(strategies.c.id == strategy_id, strategies.c.user_email == email)
        existing = await database.fetch_one(query)
        if not existing:
            logger.warning(f"Strategy {strategy_id} not found for user: {email}")
            raise HTTPException(status_code=404, detail="Strategy not found")
        query = strategies.update().where(strategies.c.id == strategy_id).values(
            name=strategy.name,
            description=strategy.description,
        )
        await database.execute(query)
        logger.info(f"Strategy {strategy_id} updated for user: {email}")
        return {**strategy.dict(), "id": strategy_id, "user_email": email, "created_at": existing["created_at"]}
    except Exception as e:
        logger.error(f"Error updating strategy {strategy_id} for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: int, email: str = Depends(get_current_user_email)):
    logger.info(f"Deleting strategy {strategy_id} for user: {email}")
    try:
        query = strategies.delete().where(strategies.c.id == strategy_id, strategies.c.user_email == email)
        await database.execute(query)
        await database.execute(trade_rules.delete().where(trade_rules.c.strategy_id == strategy_id))
        logger.info(f"Strategy {strategy_id} deleted for user: {email}")
        return {"message": "Strategy deleted"}
    except Exception as e:
        logger.error(f"Error deleting strategy {strategy_id} for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ─── Rules ───────────────────────────────────────────────────────────────────
@app.get("/rules/{strategy_id}", response_model=List[Rule])
async def get_rules(strategy_id: int, email: str = Depends(get_current_user_email)):
    logger.info(f"Fetching rules for strategy {strategy_id} by user: {email}")
    try:
        query = strategies.select().where(strategies.c.id == strategy_id, strategies.c.user_email == email)
        if not await database.fetch_one(query):
            logger.warning(f"Strategy {strategy_id} not found for user: {email}")
            raise HTTPException(status_code=404, detail="Strategy not found")
        query = trade_rules.select().where(trade_rules.c.strategy_id == strategy_id)
        result = await database.fetch_all(query)
        logger.info(f"Retrieved {len(result)} rules for strategy {strategy_id}")
        return result
    except Exception as e:
        logger.error(f"Error fetching rules for strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/rules", response_model=Rule)
async def create_rule(rule: RuleCreate, email: str = Depends(get_current_user_email)):
    logger.info(f"Creating rule for strategy {rule.strategy_id} by user: {email}")
    try:
        query = strategies.select().where(strategies.c.id == rule.strategy_id, strategies.c.user_email == email)
        if not await database.fetch_one(query):
            logger.warning(f"Strategy {rule.strategy_id} not found for user: {email}")
            raise HTTPException(status_code=404, detail="Strategy not found")
        query = trade_rules.insert().values(
            strategy_id=rule.strategy_id,
            rule_type=rule.rule_type,
            rule_text=rule.rule_text,
            followed=False,
        )
        rule_id = await database.execute(query)
        logger.info(f"Rule created with ID {rule_id} for strategy {rule.strategy_id}")
        return {**rule.dict(), "id": rule_id, "trade_id": None, "followed": False, "created_at": datetime.utcnow()}
    except Exception as e:
        logger.error(f"Error creating rule for strategy {rule.strategy_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/trade_rules/{trade_id}", response_model=List[Rule])
async def get_trade_rules(trade_id: int, email: str = Depends(get_current_user_email)):
    logger.info(f"Fetching trade rules for trade {trade_id} by user: {email}")
    try:
        query = trades.select().where(trades.c.id == trade_id, trades.c.user == email)
        if not await database.fetch_one(query):
            logger.warning(f"Trade {trade_id} not found for user: {email}")
            raise HTTPException(status_code=404, detail="Trade not found")
        query = trade_rules.select().where(trade_rules.c.trade_id == trade_id)
        result = await database.fetch_all(query)
        logger.info(f"Retrieved {len(result)} trade rules for trade {trade_id}")
        return result
    except Exception as e:
        logger.error(f"Error fetching trade rules for trade {trade_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put("/trade_rules/{trade_id}/{rule_id}", response_model=Rule)
async def update_trade_rule(trade_id: int, rule_id: int, update: TradeRuleUpdate, email: str = Depends(get_current_user_email)):
    logger.info(f"Updating trade rule {rule_id} for trade {trade_id} by user: {email}")
    try:
        query = trades.select().where(trades.c.id == trade_id, trades.c.user == email)
        if not await database.fetch_one(query):
            logger.warning(f"Trade {trade_id} not found for user: {email}")
            raise HTTPException(status_code=404, detail="Trade not found")
        query = trade_rules.select().where(trade_rules.c.trade_id == trade_id, trade_rules.c.rule_id == rule_id)
        existing = await database.fetch_one(query)
        if not existing:
            logger.warning(f"Trade rule {rule_id} not found for trade {trade_id}")
            raise HTTPException(status_code=404, detail="Trade rule not found")
        query = trade_rules.update().where(trade_rules.c.trade_id == trade_id, trade_rules.c.rule_id == rule_id).values(followed=update.followed)
        await database.execute(query)
        logger.info(f"Trade rule {rule_id} updated for trade {trade_id}")
        return {**existing, "followed": update.followed}
    except Exception as e:
        logger.error(f"Error updating trade rule {rule_id} for trade {trade_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ─── Brokers ─────────────────────────────────────────────────────────────────
@app.post("/connect_schwab")
async def connect_schwab(email: str = Depends(get_current_user_email)):
    logger.info(f"Connecting Schwab for user: {email}")
    redirect_uri = "https://127.0.0.1:8000/callback"
    try:
        client = easy_client(SCHWAB_CLIENT_ID, redirect_uri, None, asynchio=True)
        auth_url = client.get_auth_url()
        logger.info(f"Schwab auth URL generated for user: {email}")
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Schwab auth error for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Schwab auth error: {e}")

@app.get("/callback")
async def schwab_callback(code: str, email: str = Depends(get_current_user_email)):
    logger.info(f"Handling Schwab callback for user: {email}")
    redirect_uri = "https://127.0.0.1:8000/callback"
    try:
        client = easy_client(SCHWAB_CLIENT_ID, redirect_uri, None, asynchio=True)
        client.get_access_token(code)
        creds = encrypt_data(json.dumps(client.get_access_token()))
        query = brokers.insert().values(
            user_email=email,
            broker_type="schwab",
            creds_json=creds
        )
        await database.execute(query)
        logger.info(f"Schwab connected for user: {email}")
        return {"message": "Schwab connected"}
    except Exception as e:
        logger.error(f"Schwab callback error for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Schwab callback error: {e}")

@app.post("/connect_ibkr")
async def connect_ibkr(ibkr: IBKRConnect, email: str = Depends(get_current_user_email)):
    logger.info(f"Connecting IBKR for user: {email}")
    try:
        creds = {
            "host": IBKR_HOST,
            "port": int(IBKR_PORT),
            "api_token": ibkr.api_token,
            "account_id": ibkr.account_id,
        }
        encrypted = encrypt_data(json.dumps(creds))
        query = brokers.insert().values(
            user_email=email,
            broker_type="ibkr",
            creds_json=encrypted
        )
        await database.execute(query)
        logger.info(f"IBKR connected for user: {email}")
        return {"message": "IBKR connected"}
    except Exception as e:
        logger.error(f"IBKR connection error for {email}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/brokers", response_model=List[Broker])
async def get_brokers(email: str = Depends(get_current_user_email)):
    logger.info(f"Fetching brokers for user: {email}")
    try:
        query = brokers.select().where(brokers.c.user_email == email)
        result = await database.fetch_all(query)
        logger.info(f"Retrieved {len(result)} brokers for user: {email}")
        return result
    except Exception as e:
        logger.error(f"Error fetching brokers for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/import_from_schwab")
async def import_from_schwab(email: str = Depends(get_current_user_email)):
    logger.info(f"Importing trades from Schwab for user: {email}")
    try:
        query = brokers.select().where(brokers.c.user_email == email, brokers.c.broker_type == "schwab")
        broker = await database.fetch_one(query)
        if not broker:
            logger.warning(f"Schwab not connected for user: {email}")
            raise HTTPException(status_code=404, detail="Schwab not connected")
        creds = json.loads(decrypt_data(broker["creds_json"]))
        client = easy_client(SCHWAB_CLIENT_ID, "https://127.0.0.1:8000/callback", None, access_token=creds)
        start = (datetime.utcnow() - timedelta(days=30)).date()
        end = datetime.utcnow().date()
        orders = client.get_transactions(start, end, Client.Account.TransactionTypes.TRADE).json()
        trades_data = []
        for order in orders:
            legs = order.get("orderLegCollection", [])
            if not legs:
                continue
            instr = legs[0].get("instrument", {})
            buy_price = order.get("price", 0)
            sell_price = order.get("price", 0)
            qty = order.get("quantity", 0)
            direction = "Long" if order.get("side") == "BUY" else "Short"
            stop = buy_price * (0.9 if direction == "Long" else 1.1)
            multiplier = qty * 100 if order.get("trade_type", "Stock") in ("Call", "Put", "Straddle", "Covered Call", "Cash Secured Put") else qty
            pnl = round((sell_price - buy_price) * multiplier, 2) if direction == "Long" else round((buy_price - sell_price) * multiplier, 2)
            r_multiple = 0 if not stop else (
                (sell_price - buy_price) / (buy_price - stop) if direction == "Long" else
                (buy_price - sell_price) / (stop - buy_price)
            )
            r_multiple = round(r_multiple, 2)
            trade = {
                "buy_price": buy_price,
                "sell_price": sell_price,
                "stop": stop,
                "direction": direction,
                "pnl": pnl,
                "r_multiple": r_multiple,
                "timestamp": order.get("transactionDate"),
                "user": email
            }
            query = trades.insert().values(**trade)
            await database.execute(query)
            trades_data.append(trade)
        await database.execute(brokers.update().where(brokers.c.id == broker["id"]).values(last_import=datetime.utcnow()))
        logger.info(f"Imported {len(trades_data)} trades from Schwab for user: {email}")
        return {"message": f"Imported {len(trades_data)} trades from Schwab"}
    except Exception as e:
        logger.error(f"Error importing from Schwab for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/import_from_ibkr")
async def import_from_ibkr(email: str = Depends(get_current_user_email)):
    logger.info(f"Importing trades from IBKR for user: {email}")
    try:
        query = brokers.select().where(brokers.c.user_email == email, brokers.c.broker_type == "ibkr")
        broker = await database.fetch_one(query)
        if not broker:
            logger.warning(f"IBKR not connected for user: {email}")
            raise HTTPException(status_code=404, detail="IBKR not connected")
        # Placeholder for IBKR import logic
        logger.info(f"IBKR import not implemented for user: {email}")
        return {"message": "IBKR import not implemented"}
    except Exception as e:
        logger.error(f"Error importing from IBKR for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/export/{export_type}")
async def export_trades(export_type: str, email: str = Depends(get_current_user_email)):
    logger.info(f"Exporting trades as {export_type} for user: {email}")
    try:
        query = trades.select().where(trades.c.user == email)
        trades_data = await database.fetch_all(query)
        trades_data = [dict(t) for t in trades_data]
        if export_type == "excel":
            path = export_excel_util(trades_data)
            logger.info(f"Exported trades to Excel for user: {email}")
            return FileResponse(path, filename="trades.xlsx")
        elif export_type == "pdf":
            path = export_pdf_util(trades_data)
            logger.info(f"Exported trades to PDF for user: {email}")
            return FileResponse(path, filename="trades.pdf")
        else:
            logger.warning(f"Invalid export type {export_type} for user: {email}")
            raise HTTPException(status_code=400, detail="Invalid export type")
    except Exception as e:
        logger.error(f"Error exporting trades for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ─── Analytics Endpoint ───────────────────────────────────────────────────────
@app.get("/analytics")
async def get_analytics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    strategy_id: Optional[int] = Query(None),
    trade_type: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    followed: Optional[str] = Query(None),
    confidence_min: Optional[int] = Query(1),
    confidence_max: Optional[int] = Query(5),
    token: str = Depends(oauth2_scheme)
):
    logger.info(f"Fetching analytics for token: {token[:10]}...")
    try:
        user_email = get_current_user_email(token)
        query = select(trades).where(trades.c.user == user_email)
        db_trades = await database.fetch_all(query)
        trades_data = [dict(row) for row in db_trades]
        logger.debug(f"Fetched {len(trades_data)} trades for analytics")

        summary = compute_summary_stats(trades_data)
        by_strategy = compute_by_strategy(trades_data)
        by_rule = compute_by_rule(trades_data)
        by_type = compute_by_trade_type(trades_data)
        by_hour = compute_by_hour(trades_data)
        by_day_of_week = compute_by_day_of_week(trades_data)
        risk_metrics = compute_risk_metrics(trades_data)
        behavioral_insights = compute_behavioral_insights(trades_data)
        equity_curve = compute_equity_curve(trades_data)
        heatmap_hour = compute_heatmap_hour(trades_data)
        heatmap_day = compute_heatmap_day(trades_data)

        logger.info(f"Analytics computed for user: {user_email}")
        return {
            'summary': summary,
            'by_strategy': by_strategy,
            'by_rule': by_rule,
            'by_type': by_type,
            'by_hour': by_hour,
            'by_day_of_week': by_day_of_week,
            'risk_metrics': risk_metrics,
            'behavioral_insights': behavioral_insights,
            'equity_curve': equity_curve,
            'heatmap_hour': heatmap_hour,
            'heatmap_day': heatmap_day,
        }
    except Exception as e:
        logger.error(f"Error computing analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def apply_analytics_filters(trades, filters):
    filtered = trades
    if filters['start_date']:
        filtered = [t for t in filtered if t['buy_timestamp'] >= filters['start_date']]
    if filters['end_date']:
        filtered = [t for t in filtered if t['buy_timestamp'] <= filters['end_date']]
    if filters['strategy_id']:
        filtered = [t for t in filtered if t.get('strategy_id') == filters['strategy_id']]
    if filters['trade_type']:
        filtered = [t for t in filtered if t.get('trade_type') == filters['trade_type']]
    if filters['direction']:
        filtered = [t for t in filtered if t.get('direction') == filters['direction']]
    if filters['followed'] != 'all':
        filtered = [
            t for t in filtered
            if t.get('rule_adherence') and (
                (filters['followed'] == 'followed' and all(ra['followed'] for ra in t['rule_adherence'])) or
                (filters['followed'] == 'broken' and any(not ra['followed'] for ra in t['rule_adherence']))
            )
        ]
    if filters['confidence_min']:
        filtered = [t for t in filtered if (t.get('confidence') or 0) >= filters['confidence_min']]
    if filters['confidence_max']:
        filtered = [t for t in filtered if (t.get('confidence') or 0) <= filters['confidence_max']]
    return filtered