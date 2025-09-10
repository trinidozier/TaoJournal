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
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import matplotlib.pyplot as plt
from jose import jwt, JWTError
from tda.auth import easy_client
from tda.client import Client
from cryptography.fernet import Fernet
import pandas as pd  # For analytics
from db import engine, metadata, database, users, strategies, trade_rules, brokers  # Added brokers table
from auth import hash_password, verify_password
from import_trades import parse_smart_csv
from grouping import group_trades_by_entry_exit
from export_tools import export_to_excel as export_excel_util, export_to_pdf as export_pdf_util
from analytics import compute_summary_stats
from schemas import Strategy, StrategyCreate, Rule, RuleCreate, TradeIn, Trade, UserCreate, IBKRConnect, TradeRuleUpdate, Broker, BrokerCreate
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

load_dotenv()

# ─── Config & Logging ────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
SCHWAB_CLIENT_ID = os.getenv("SCHWAB_CLIENT_ID")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
IBKR_PORT = os.getenv("IBKR_PORT", "7497") # 7496 for live, 7497 for paper
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
    except (json.JSONDecodeError, OSError):
        return []

def load_trades(user_email: str) -> List[dict]:
    trades = [t for t in load_all_trades() if t.get("user") == user_email]
    # Add trade_id for analytics
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
        ts = t.get("buy_timestamp") or t.get("BuyTimestamp")
        try:
            dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
            d = dt.date()
        except Exception:
            continue
        if ((not start) or start <= d) and ((not end) or d <= end):
            out.append(t)
    return out

# ─── Authentication Helpers ─────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        query = users.select().where(users.c.email == email)
        user = await database.fetch_one(query)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# ─── Broker Import Logic (Placeholder - Expand as Needed) ───────────────────
async def perform_import(user_email: str, broker_id: Optional[int] = None):
    query = brokers.select().where(brokers.c.user_email == user_email)
    if broker_id:
        query = query.where(brokers.c.id == broker_id)
    brokers_list = await database.fetch_all(query)
    total_imported = 0
    for broker in brokers_list:
        creds_enc = broker["creds_json"]
        creds = json.loads(decrypt_data(creds_enc))
        last_import = broker["last_import"] or datetime.min
        new_trades = []
        if broker["broker_type"] == 'schwab':
            # Placeholder for Schwab import using tda
            client = easy_client(creds.get("api_token"), SCHWAB_CLIENT_ID, token_path='schwab_token.json')
            transactions = client.get_transactions(creds.get("account_id"), from_date=last_import, to_date=datetime.now())
            # Parse transactions to TradeIn format (implement parsing logic similar to parse_smart_csv)
            for tx in transactions:
                # Example parsing - adjust based on API response
                if tx.get('type') == 'TRADE':
                    trade = {
                        "instrument": tx.get('symbol'),
                        "buy_timestamp": tx.get('date'),
                        "sell_timestamp": tx.get('date'),  # Adjust for buy/sell
                        "buy_price": tx.get('price'),  # Adjust
                        "sell_price": tx.get('price'),  # Adjust
                        "qty": tx.get('quantity'),
                        # ... fill other fields
                    }
                    new_trades.append(trade)
        elif broker["broker_type"] == 'ibkr':
            # Placeholder for IBKR using ib-insync
            from ib_insync import IB
            ib = IB()
            ib.connect(creds.get("host", "127.0.0.1"), creds.get("port", 7497), clientId=creds.get("client_id", 1))
            executions = ib.executions()  # Get recent executions
            # Parse to TradeIn
            for exec in executions:
                trade = {
                    "instrument": exec.contract.symbol,
                    "buy_timestamp": exec.time,
                    "sell_timestamp": exec.time,  # Adjust for side
                    "buy_price": exec.avgPrice if exec.side == 'BOT' else exec.avgPrice,  # Adjust
                    # ... fill
                }
                new_trades.append(trade)
            ib.disconnect()
        # Add new trades
        trades = load_trades(user_email)
        for trade in new_trades:
            direction = trade.get("direction") or ("Long" if trade["sell_price"] > trade["buy_price"] else "Short")
            pnl = (trade["sell_price"] - trade["buy_price"]) if direction == "Long" else (trade["buy_price"] - trade["sell_price"])
            risk = abs(trade["buy_price"] - trade.get("stop", 0)) if trade.get("stop") else 0
            r_mult = round(pnl / risk, 2) if risk else 0.0
            record = trade.copy()
            record.update({
                "direction": direction,
                "pnl": round(pnl, 2),
                "r_multiple": r_mult,
                "image_path": "",
                "user": user_email,
                "id": len(trades)
            })
            trades.append(record)
        save_trades(trades, user_email)
        # Update last_import
        await database.execute(brokers.update().where(brokers.c.id == broker["id"]).values(last_import=datetime.now()))
        total_imported += len(new_trades)
    return total_imported

# ─── FastAPI App Initialization ─────────────────────────────────────────────
app = FastAPI(title="Tao Trader API")

@app.get("/")
def root():
    return {"message": "Tao Trader is live"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    metadata.create_all(engine)
    await database.connect()
    # Setup daily auto-import scheduler at 5 PM EST
    scheduler = AsyncIOScheduler(timezone=timezone('America/New_York'))
    scheduler.add_job(import_all_users, 'cron', hour=17, minute=0)
    scheduler.start()

async def import_all_users():
    query = users.select()
    users_list = await database.fetch_all(query)
    for u in users_list:
        try:
            await perform_import(u["email"])
        except Exception as e:
            logger.error(f"Auto import failed for {u['email']}: {e}")

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── JWT Smoke-Test Endpoint ──────────────────────────────────────
@app.get("/jwt-test")
def jwt_test():
    dummy = {"sub": "test@example.com"}
    token = create_access_token(dummy)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return {"encoded": token, "decoded": decoded}

# ─── User Endpoints ─────────────────────────────────────────────────────────
@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    query = users.select().where(users.c.email == user.email)
    if await database.fetch_one(query):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = hash_password(user.password)
    insert = users.insert().values(
        first_name=user.first_name,
        last_name=user.last_name,
        billing_address=user.billing_address,
        email=user.email,
        hashed_password=hashed_pw
    )
    await database.execute(insert)
    return {"message": "User registered successfully"}

@app.post("/login")
async def login(request: Request):
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    query = users.select().where(users.c.email == email)
    user = await database.fetch_one(query)
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer"}

# ─── Broker Endpoints (Updated for Multiple and Encryption) ─────────────────
@app.post("/brokers", response_model=Broker)
async def connect_broker(broker: BrokerCreate, current_user: dict = Depends(get_current_user)):
    # Validate creds based on type (basic check)
    if broker.broker_type not in ['ibkr', 'schwab']:
        raise HTTPException(status_code=400, detail="Unsupported broker type")
    if broker.broker_type == 'ibkr':
        required = ['host', 'port', 'client_id']
    elif broker.broker_type == 'schwab':
        required = ['api_token', 'account_id']
    for key in required:
        if key not in broker.creds:
            raise HTTPException(status_code=400, detail=f"Missing credential: {key}")
    creds_json = json.dumps(broker.creds)
    encrypted_creds = encrypt_data(creds_json)
    insert = brokers.insert().values(
        user_email=current_user["email"],
        broker_type=broker.broker_type,
        creds_json=encrypted_creds
    )
    id = await database.execute(insert)
    return {"id": id, "user_email": current_user["email"], "broker_type": broker.broker_type, "creds": broker.creds, "last_import": None}

@app.get("/brokers", response_model=List[Broker])
async def get_brokers(current_user: dict = Depends(get_current_user)):
    query = brokers.select().where(brokers.c.user_email == current_user["email"])
    result = await database.fetch_all(query)
    decrypted = []
    for b in result:
        creds_enc = b["creds_json"]
        creds_json = decrypt_data(creds_enc)
        creds = json.loads(creds_json)
        decrypted.append(dict(b) | {"creds": creds})
    return decrypted

@app.get("/import_from_broker")
async def import_from_broker(broker_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    imported = await perform_import(current_user["email"], broker_id)
    if imported == 0:
        raise HTTPException(status_code=400, detail="No brokers connected or no new trades. Connect a supported broker or upload CSV.")
    return {"imported": imported, "message": f"Successfully imported {imported} trades."}

# ─── Strategy and Rule Endpoints ────────────────────────────────────────────
@app.post("/strategies", response_model=Strategy)
async def create_strategy(strategy: StrategyCreate, current_user: dict = Depends(get_current_user)):
    insert = strategies.insert().values(
        user_email=current_user["email"],
        name=strategy.name,
        description=strategy.description
    )
    strategy_id = await database.execute(insert)
    # Add entry and exit rules
    for rule_text in strategy.entry_rules:
        if rule_text:
            await database.execute(trade_rules.insert().values(
                strategy_id=strategy_id,
                rule_type="entry",
                rule_text=rule_text
            ))
    for rule_text in strategy.exit_rules:
        if rule_text:
            await database.execute(trade_rules.insert().values(
                strategy_id=strategy_id,
                rule_type="exit",
                rule_text=rule_text
            ))
    # Fetch the created strategy to return it fully
    query = strategies.select().where(strategies.c.id == strategy_id)
    result = await database.fetch_one(query)
    if not result:
        raise HTTPException(status_code=404, detail="Strategy not found after creation")
    return dict(result)  # Convert Record to dict for Pydantic

@app.put("/strategies/{strategy_id}", response_model=Strategy)
async def update_strategy(strategy_id: int, strategy: StrategyCreate, current_user: dict = Depends(get_current_user)):
    query = strategies.select().where(strategies.c.id == strategy_id, strategies.c.user_email == current_user["email"])
    if not await database.fetch_one(query):
        raise HTTPException(status_code=404, detail="Strategy not found or not owned by user")
    # Update name and description
    await database.execute(strategies.update().where(strategies.c.id == strategy_id).values(
        name=strategy.name,
        description=strategy.description
    ))
    # Delete old strategy rules (trade_id is None)
    await database.execute(trade_rules.delete().where(
        trade_rules.c.strategy_id == strategy_id,
        trade_rules.c.trade_id.is_(None)
    ))
    # Add new entry and exit rules
    for rule_text in strategy.entry_rules:
        if rule_text:
            await database.execute(trade_rules.insert().values(
                strategy_id=strategy_id,
                rule_type="entry",
                rule_text=rule_text
            ))
    for rule_text in strategy.exit_rules:
        if rule_text:
            await database.execute(trade_rules.insert().values(
                strategy_id=strategy_id,
                rule_type="exit",
                rule_text=rule_text
            ))
    # Fetch updated strategy
    result = await database.fetch_one(strategies.select().where(strategies.c.id == strategy_id))
    return dict(result)

@app.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(strategy_id: int, current_user: dict = Depends(get_current_user)):
    query = strategies.select().where(strategies.c.id == strategy_id, strategies.c.user_email == current_user["email"])
    if not await database.fetch_one(query):
        raise HTTPException(status_code=404, detail="Strategy not found or not owned by user")
    # Delete all associated rules
    await database.execute(trade_rules.delete().where(trade_rules.c.strategy_id == strategy_id))
    # Delete strategy
    await database.execute(strategies.delete().where(strategies.c.id == strategy_id))

@app.get("/strategies", response_model=List[Strategy])
async def list_strategies(current_user: dict = Depends(get_current_user)):
    query = strategies.select().where(strategies.c.user_email == current_user["email"])
    result = await database.fetch_all(query)
    return [dict(record) for record in result]  # Convert each Record to dict

@app.post("/rules", response_model=Rule)
async def create_rule(rule: RuleCreate, current_user: dict = Depends(get_current_user)):
    strategy_query = strategies.select().where(strategies.c.id == rule.strategy_id, strategies.c.user_email == current_user["email"])
    if not await database.fetch_one(strategy_query):
        raise HTTPException(status_code=404, detail="Strategy not found or not owned by user")
    insert = trade_rules.insert().values(
        strategy_id=rule.strategy_id,
        rule_type=rule.rule_type,
        rule_text=rule.rule_text
    )
    rule_id = await database.execute(insert)
    # Fetch the created rule to return it fully
    query = trade_rules.select().where(trade_rules.c.id == rule_id)
    result = await database.fetch_one(query)
    return dict(result)  # Convert Record to dict for Pydantic

@app.get("/rules/{strategy_id}", response_model=List[Rule])
async def list_rules(strategy_id: int, current_user: dict = Depends(get_current_user)):
    strategy_query = strategies.select().where(strategies.c.id == strategy_id, strategies.c.user_email == current_user["email"])
    if not await database.fetch_one(strategy_query):
        raise HTTPException(status_code=404, detail="Strategy not found or not owned by user")
    query = trade_rules.select().where(trade_rules.c.strategy_id == strategy_id, trade_rules.c.trade_id.is_(None))
    result = await database.fetch_all(query)
    return [dict(record) for record in result]  # Convert each Record to dict

@app.get("/trade_rules/{trade_id}", response_model=List[Rule])
async def list_trade_rules(trade_id: int, current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    if trade_id < 0 or trade_id >= len(trades):
        raise HTTPException(status_code=404, detail="Trade not found")
    query = trade_rules.select().where(trade_rules.c.trade_id == trade_id)
    result = await database.fetch_all(query)
    return [dict(record) for record in result]  # Convert each Record to dict

@app.post("/trade_rules", response_model=Rule)
async def create_trade_rule(rule: RuleCreate, trade_id: int, current_user: dict = Depends(get_current_user)):
    strategy_query = strategies.select().where(strategies.c.id == rule.strategy_id, strategies.c.user_email == current_user["email"])
    if not await database.fetch_one(strategy_query):
        raise HTTPException(status_code=404, detail="Strategy not found or not owned by user")
    trades = load_trades(current_user["email"])
    if trade_id < 0 or trade_id >= len(trades):
        raise HTTPException(status_code=404, detail="Trade not found")
    insert = trade_rules.insert().values(
        strategy_id=rule.strategy_id,
        rule_type=rule.rule_type,
        rule_text=rule.rule_text,
        trade_id=trade_id,
        followed=False
    )
    rule_id = await database.execute(insert)
    # Fetch the created rule to return it fully
    query = trade_rules.select().where(trade_rules.c.id == rule_id)
    result = await database.fetch_one(query)
    return dict(result)  # Convert Record to dict for Pydantic

@app.put("/trade_rules/{rule_id}", response_model=Rule)
async def update_trade_rule(rule_id: int, update: TradeRuleUpdate, current_user: dict = Depends(get_current_user)):
    rule_query = trade_rules.select().join(strategies, trade_rules.c.strategy_id == strategies.c.id).where(
        trade_rules.c.id == rule_id, strategies.c.user_email == current_user["email"]
    )
    rule = await database.fetch_one(rule_query)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found or not owned by user")
    update_query = trade_rules.update().where(trade_rules.c.id == rule_id).values(followed=update.followed)
    await database.execute(update_query)
    # Fetch the updated rule to return it fully
    query = trade_rules.select().where(trade_rules.c.id == rule_id)
    result = await database.fetch_one(query)
    return dict(result)  # Convert Record to dict for Pydantic

# ─── Analytics Endpoint with Rule Breakdown ─────────────────────────────────
@app.get("/analytics")
async def analytics(start: Optional[date] = Query(None), end: Optional[date] = Query(None), current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    filtered = filter_by_date(trades, start, end)
    basic_stats = compute_summary_stats(filtered)
    # Advanced rule analytics
    rule_analytics = {}
    strategy_query = strategies.select().where(strategies.c.user_email == current_user["email"])
    strategies_list = await database.fetch_all(strategy_query)
    for strat in strategies_list:
        strategy_id = strat["id"]
        rule_query = trade_rules.select().where(trade_rules.c.strategy_id == strategy_id, trade_rules.c.trade_id.is_not(None))
        rules = await database.fetch_all(rule_query)
        strategy_trades = [t for t in filtered if t.get('strategy_id') == strategy_id]
        if not strategy_trades:
            continue
        total_trades = len(strategy_trades)
        wins = len([t for t in strategy_trades if t['pnl'] > 0])
        win_rate = wins / total_trades if total_trades > 0 else 0
        avg_r = sum(t['r_multiple'] for t in strategy_trades) / total_trades if total_trades > 0 else 0
        rule_analytics[strat["name"]] = {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "avg_r_multiple": avg_r,
            "rules": {}
        }
        for rule in rules:
            rule_id = rule["id"]
            followed_trades = [t for t in strategy_trades if any(r["id"] == rule_id and r["followed"] for r in await database.fetch_all(trade_rules.select().where(trade_rules.c.trade_id == t["id"])))]
            not_followed_trades = [t for t in strategy_trades if t not in followed_trades]
            followed_count = len(followed_trades)
            followed_wins = len([t for t in followed_trades if t['pnl'] > 0])
            not_followed_wins = len([t for t in not_followed_trades if t['pnl'] > 0])
            rule_analytics[strat["name"]]["rules"][rule["rule_text"]] = {
                "followed_rate": followed_count / total_trades if total_trades > 0 else 0,
                "win_rate_followed": followed_wins / followed_count if followed_count > 0 else 0,
                "win_rate_not_followed": not_followed_wins / len(not_followed_trades) if len(not_followed_trades) > 0 else 0,
                "avg_r_followed": sum(t['r_multiple'] for t in followed_trades) / followed_count if followed_count > 0 else 0,
                "avg_r_not_followed": sum(t['r_multiple'] for t in not_followed_trades) / len(not_followed_trades) > 0 else 0
            }
    return {
        "basic_stats": basic_stats,
        "rule_analytics": rule_analytics
    }

# ─── Trade Endpoints ─────────────────────────────────────────────────
@app.get("/trades", response_model=List[Trade])
async def list_trades(current_user: dict = Depends(get_current_user)):
    return load_trades(current_user["email"])

@app.post("/trades", response_model=Trade)
async def add_trade(payload: TradeIn, current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    direction = payload.direction or ("Long" if payload.sell_price > payload.buy_price else "Short")
    pnl = (payload.sell_price - payload.buy_price) if direction == "Long" else (payload.buy_price - payload.sell_price)
    risk = abs(payload.buy_price - payload.stop) if payload.stop else 0
    r_mult = round(pnl / risk, 2) if risk else 0.0
    record = payload.dict()
    record.update({
        "direction": direction,
        "pnl": round(pnl, 2),
        "r_multiple": r_mult,
        "image_path": "",
        "user": current_user["email"],
        "id": len(trades)  # Assign trade_id
    })
    trades.append(record)
    save_trades(trades, current_user["email"])
    # Save rule adherence
    for rule in payload.rule_adherence:
        rule_query = trade_rules.select().where(trade_rules.c.id == rule["rule_id"], trade_rules.c.strategy_id == payload.strategy_id)
        if await database.fetch_one(rule_query):
            await database.execute(trade_rules.insert().values(
                strategy_id=payload.strategy_id,
                rule_type=(await database.fetch_one(rule_query))["rule_type"],
                rule_text=(await database.fetch_one(rule_query))["rule_text"],
                trade_id=len(trades) - 1,
                followed=rule["followed"]
            ))
    return record

@app.put("/trades/{index}", response_model=Trade)
async def update_trade(index: int, payload: TradeIn, current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    if index < 0 or index >= len(trades):
        raise HTTPException(status_code=404, detail="Trade not found")
    direction = payload.direction or ("Long" if payload.sell_price > payload.buy_price else "Short")
    pnl = (payload.sell_price - payload.buy_price) if direction == "Long" else (payload.buy_price - payload.sell_price)
    risk = abs(payload.buy_price - payload.stop) if payload.stop else 0
    r_mult = round(pnl / risk, 2) if risk else 0.0
    updated = payload.dict()
    updated.update({
        "direction": direction,
        "pnl": round(pnl, 2),
        "r_multiple": r_mult,
        "id": index
    })
    trades[index].update(updated)
    save_trades(trades, current_user["email"])
    # Update rule adherence
    for rule in payload.rule_adherence:
        rule_query = trade_rules.select().where(trade_rules.c.id == rule["rule_id"], trade_rules.c.trade_id == index)
        if await database.fetch_one(rule_query):
            await database.execute(trade_rules.update().where(trade_rules.c.id == rule["rule_id"], trade_rules.c.trade_id == index).values(followed=rule["followed"]))
        else:
            strategy_rule = await database.fetch_one(trade_rules.select().where(trade_rules.c.id == rule["rule_id"], trade_rules.c.strategy_id == payload.strategy_id))
            if strategy_rule:
                await database.execute(trade_rules.insert().values(
                    strategy_id=payload.strategy_id,
                    rule_type=strategy_rule["rule_type"],
                    rule_text=strategy_rule["rule_text"],
                    trade_id=index,
                    followed=rule["followed"]
                ))
    return updated

@app.delete("/trades/{index}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(index: int, current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    if index < 0 or index >= len(trades):
        raise HTTPException(status_code=404, detail="Trade not found")
    # Delete associated trade_rules
    await database.execute(trade_rules.delete().where(trade_rules.c.trade_id == index))
    trades.pop(index)
    save_trades(trades, current_user["email"])

@app.post("/import_csv")
async def import_csv(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    content = await file.read()
    try:
        rows = parse_smart_csv(io.BytesIO(content))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    trades = load_trades(current_user["email"])
    for payload in rows:
        direction = payload.get("direction", "Long" if payload["sell_price"] > payload["buy_price"] else "Short")
        pnl = (payload["sell_price"] - payload["buy_price"]) if direction == "Long" else (payload["buy_price"] - payload["sell_price"])
        risk = abs(payload["buy_price"] - payload.get("stop", 0)) if payload.get("stop") else 0
        r_mult = round(pnl / risk, 2) if risk else 0.0
        record = payload.copy()
        record.update({
            "direction": direction,
            "pnl": round(pnl, 2),
            "r_multiple": r_mult,
            "image_path": "",
            "user": current_user["email"],
            "id": len(trades)
        })
        trades.append(record)
    save_trades(trades, current_user["email"])
    return {"imported": len(rows), "message": f"Successfully imported {len(rows)} trades."}

@app.get("/export/excel")
async def export_excel(start: Optional[date] = Query(None), end: Optional[date] = Query(None), current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    filtered = filter_by_date(trades, start, end)
    xlsx_buf = export_excel_util(filtered)
    return FileResponse(xlsx_buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="trades.xlsx")

@app.get("/export/pdf")
async def export_pdf(start: Optional[date] = Query(None), end: Optional[date] = Query(None), current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    filtered = filter_by_date(trades, start, end)
    pdf_buf = export_pdf_util(filtered)
    return FileResponse(pdf_buf, media_type="application/pdf", filename="trades.pdf")

@app.get("/trades/{index}/image")
async def get_trade_image(index: int, current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    if index < 0 or index >= len(trades):
        raise HTTPException(status_code=404, detail="Trade not found")
    img_path = trades[index].get("image_path")
    if not img_path or not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(img_path)

@app.post("/trades/{index}/image")
async def upload_trade_image(index: int, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    if index < 0 or index >= len(trades):
        raise HTTPException(status_code=404, detail="Trade not found")
    ext = os.path.splitext(file.filename)[1]
    img_path = os.path.join(IMAGE_FOLDER, f"trade_{current_user['email']}_{index}{ext}")
    with open(img_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    trades[index]["image_path"] = img_path
    save_trades(trades, current_user["email"])
    return {"image_path": img_path}

# ─── Dashboard Endpoint (New: Serves Cleaned-Up HTML Dashboard) ─────────────
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(current_user: dict = Depends(get_current_user)):
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Tao Trader Dashboard</title>
    <style>
        .modal {
            display: none;
            position: fixed;
            z-index: 1;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.4);
        }
        .modal-content {
            background-color: #fefefe;
            margin: 15% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 80%;
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
        }
        .close:hover,
        .close:focus {
            color: black;
            text-decoration: none;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>Tao Trader Dashboard</h1>
    <button id="connectBrokerBtn">Connect Broker</button>
    <button id="importBrokerBtn">Import from Broker</button>
    <button id="uploadCsvBtn">Upload Broker CSV</button>
    <button id="addStrategyBtn">Add Strategy</button>
    <button id="editStrategiesBtn">Edit Strategies</button>
    <!-- Add other buttons as needed, e.g., Add Trade, View Analytics, Export, etc. -->

    <!-- Connect Broker Modal -->
    <div id="connectBrokerModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('connectBrokerModal')">&times;</span>
            <h2>Connect Broker</h2>
            <form id="connectForm">
                <label for="brokerType">Broker:</label>
                <select id="brokerType" onchange="showCredsFields()">
                    <option value="">Select</option>
                    <option value="ibkr">IBKR</option>
                    <option value="schwab">Schwab</option>
                </select>
                <div id="credsFields"></div>
                <button type="button" onclick="submitConnect()">Connect</button>
            </form>
        </div>
    </div>

    <!-- Add Strategy Modal -->
    <div id="addStrategyModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('addStrategyModal')">&times;</span>
            <h2>Add Strategy</h2>
            <form id="addStrategyForm">
                <label for="name">Name:</label>
                <input type="text" id="name" name="name"><br>
                <label for="description">Description:</label>
                <textarea id="description" name="description"></textarea><br>
                <h3>Entry Rules</h3>
                <div id="entryRules"></div>
                <a href="#" onclick="addRuleField('entryRules')">Add another entry rule</a><br>
                <h3>Exit Rules</h3>
                <div id="exitRules"></div>
                <a href="#" onclick="addRuleField('exitRules')">Add another exit rule</a><br>
                <button type="button" onclick="submitStrategy()">Save</button>
            </form>
        </div>
    </div>

    <!-- Edit Strategies Modal -->
    <div id="editStrategiesModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('editStrategiesModal')">&times;</span>
            <h2>Edit Strategies</h2>
            <div id="strategiesList"></div>
        </div>
    </div>

    <!-- Edit Strategy Sub-Modal -->
    <div id="editStrategyModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('editStrategyModal')">&times;</span>
            <h2>Edit Strategy</h2>
            <form id="editStrategyForm">
                <input type="hidden" id="editId" name="id">
                <label for="editName">Name:</label>
                <input type="text" id="editName" name="name"><br>
                <label for="editDescription">Description:</label>
                <textarea id="editDescription" name="description"></textarea><br>
                <h3>Entry Rules</h3>
                <div id="editEntryRules"></div>
                <a href="#" onclick="addRuleField('editEntryRules')">Add another entry rule</a><br>
                <h3>Exit Rules</h3>
                <div id="editExitRules"></div>
                <a href="#" onclick="addRuleField('editExitRules')">Add another exit rule</a><br>
                <button type="button" onclick="submitEditStrategy()">Update</button>
                <button type="button" onclick="deleteStrategy()">Delete</button>
            </form>
        </div>
    </div>

    <script>
        const token = localStorage.getItem('access_token');  // Assume token stored after login

        function openModal(id) {
            document.getElementById(id).style.display = 'block';
        }

        function closeModal(id) {
            document.getElementById(id).style.display = 'none';
        }

        function showCredsFields() {
            const type = document.getElementById('brokerType').value;
            const fields = document.getElementById('credsFields');
            fields.innerHTML = '';
            if (type === 'ibkr') {
                fields.innerHTML = `
                    <label for="host">Host:</label>
                    <input type="text" id="host" name="host" value="127.0.0.1"><br>
                    <label for="port">Port:</label>
                    <input type="number" id="port" name="port" value="7497"><br>
                    <label for="client_id">Client ID:</label>
                    <input type="number" id="client_id" name="client_id"><br>
                `;
            } else if (type === 'schwab') {
                fields.innerHTML = `
                    <label for="api_token">API Token:</label>
                    <input type="text" id="api_token" name="api_token"><br>
                    <label for="account_id">Account ID:</label>
                    <input type="text" id="account_id" name="account_id"><br>
                `;
            }
        }

        function submitConnect() {
            const form = document.getElementById('connectForm');
            const type = form.brokerType.value;
            let creds = {};
            if (type === 'ibkr') {
                creds = {
                    host: form.host.value,
                    port: parseInt(form.port.value),
                    client_id: parseInt(form.client_id.value)
                };
            } else if (type === 'schwab') {
                creds = {
                    api_token: form.api_token.value,
                    account_id: form.account_id.value
                };
            }
            fetch('/brokers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    broker_type: type,
                    creds: creds
                })
            }).then(response => response.json())
              .then(data => {
                  alert('Broker connected!');
                  closeModal('connectBrokerModal');
              }).catch(error => alert('Error: ' + error));
        }

        document.getElementById('connectBrokerBtn').onclick = () => openModal('connectBrokerModal');

        document.getElementById('importBrokerBtn').onclick = () => {
            fetch('/import_from_broker', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            }).then(response => {
                if (!response.ok) {
                    response.json().then(err => alert(err.detail || 'Error importing. You must first connect a supported broker, if your broker is not supported download your trade history to a csv file and import the csv through upload broker csv button.'));
                } else {
                    response.json().then(data => alert(`Imported ${data.imported} trades`));
                }
            }).catch(error => alert('Error: ' + error));
        };

        document.getElementById('uploadCsvBtn').onclick = () => {
            // Implement file upload to /import_csv (use input type=file, FormData)
            const input = document.createElement('input');
            input.type = 'file';
            input.onchange = (e) => {
                const file = e.target.files[0];
                const formData = new FormData();
                formData.append('file', file);
                fetch('/import_csv', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                }).then(response => response.json())
                  .then(data => alert(`Imported ${data.imported} trades from CSV`))
                  .catch(error => alert('Error: ' + error));
            };
            input.click();
        };

        function addRuleField(divId, value = '') {
            const div = document.getElementById(divId);
            const input = document.createElement('input');
            input.type = 'text';
            input.name = divId.toLowerCase().includes('entry') ? 'entry_rules[]' : 'exit_rules[]';
            input.value = value;
            const br = document.createElement('br');
            const remove = document.createElement('a');
            remove.href = '#';
            remove.textContent = 'Remove';
            remove.onclick = () => {
                div.removeChild(input);
                div.removeChild(br);
                div.removeChild(remove);
                div.removeChild(document.createElement('br'));
            };
            div.appendChild(input);
            div.appendChild(br);
            div.appendChild(remove);
            div.appendChild(document.createElement('br'));
        }

        document.getElementById('addStrategyBtn').onclick = () => {
            openModal('addStrategyModal');
            const entryDiv = document.getElementById('entryRules');
            entryDiv.innerHTML = '';
            addRuleField('entryRules');
            const exitDiv = document.getElementById('exitRules');
            exitDiv.innerHTML = '';
            addRuleField('exitRules');
        };

        function submitStrategy() {
            const form = document.getElementById('addStrategyForm');
            const entry_rules = Array.from(form.querySelectorAll('input[name="entry_rules[]"]')).map(i => i.value).filter(v => v);
            const exit_rules = Array.from(form.querySelectorAll('input[name="exit_rules[]"]')).map(i => i.value).filter(v => v);
            fetch('/strategies', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    name: form.name.value,
                    description: form.description.value,
                    entry_rules,
                    exit_rules
                })
            }).then(response => response.json())
              .then(data => {
                  alert('Strategy added!');
                  closeModal('addStrategyModal');
              }).catch(error => alert('Error: ' + error));
        }

        document.getElementById('editStrategiesBtn').onclick = () => {
            openModal('editStrategiesModal');
            fetch('/strategies', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            }).then(response => response.json())
              .then(strategies => {
                  const list = document.getElementById('strategiesList');
                  list.innerHTML = '';
                  strategies.forEach(s => {
                      const div = document.createElement('div');
                      div.textContent = s.name;
                      div.onclick = () => loadEditStrategy(s);
                      list.appendChild(div);
                  });
              }).catch(error => alert('Error: ' + error));
        };

        function loadEditStrategy(s) {
            closeModal('editStrategiesModal');
            openModal('editStrategyModal');
            document.getElementById('editId').value = s.id;
            document.getElementById('editName').value = s.name;
            document.getElementById('editDescription').value = s.description;
            const entryDiv = document.getElementById('editEntryRules');
            entryDiv.innerHTML = '';
            fetch(`/rules/${s.id}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            }).then(response => response.json())
              .then(rules => {
                  const entry_rules = rules.filter(r => r.rule_type === 'entry');
                  entry_rules.forEach(r => addRuleField('editEntryRules', r.rule_text));
                  if (entry_rules.length === 0) addRuleField('editEntryRules');
                  const exit_rules = rules.filter(r => r.rule_type === 'exit');
                  const exitDiv = document.getElementById('editExitRules');
                  exitDiv.innerHTML = '';
                  exit_rules.forEach(r => addRuleField('editExitRules', r.rule_text));
                  if (exit_rules.length === 0) addRuleField('editExitRules');
              }).catch(error => alert('Error: ' + error));
        }

        function submitEditStrategy() {
            const form = document.getElementById('editStrategyForm');
            const id = form.editId.value;
            const entry_rules = Array.from(form.querySelectorAll('input[name="entry_rules[]"]')).map(i => i.value).filter(v => v);
            const exit_rules = Array.from(form.querySelectorAll('input[name="exit_rules[]"]')).map(i => i.value).filter(v => v);
            fetch(`/strategies/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    name: form.editName.value,
                    description: form.editDescription.value,
                    entry_rules,
                    exit_rules
                })
            }).then(response => response.json())
              .then(data => {
                  alert('Strategy updated!');
                  closeModal('editStrategyModal');
              }).catch(error => alert('Error: ' + error));
        }

        function deleteStrategy() {
            const id = document.getElementById('editId').value;
            if (confirm('Are you sure you want to delete this strategy?')) {
                fetch(`/strategies/${id}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }).then(() => {
                    alert('Strategy deleted!');
                    closeModal('editStrategyModal');
                }).catch(error => alert('Error: ' + error));
            }
        }

        // Close on outside click
        window.onclick = function(event) {
            const modals = document.getElementsByClassName('modal');
            for (let m of modals) {
                if (event.target == m) {
                    m.style.display = "none";
                }
            }
        };
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)