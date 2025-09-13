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
from db import engine, metadata, database, users, strategies, trade_rules, brokers
from auth import hash_password, verify_password
from import_trades import parse_smart_csv
from grouping import group_trades_by_entry_exit
from export_tools import export_to_excel as export_excel_util, export_to_pdf as export_pdf_util
from analytics import compute_summary_stats, compute_by_strategy, compute_by_rule, compute_by_trade_type, compute_by_hour, compute_by_day_of_week, compute_risk_metrics, compute_behavioral_insights, compute_equity_curve, compute_heatmap_hour, compute_heatmap_day
from schemas import Strategy, StrategyCreate, Rule, RuleCreate, TradeIn, Trade, UserCreate, IBKRConnect, TradeRuleUpdate, Broker, BrokerCreate
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from sqlalchemy import select  # Added for DB queries

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
IBKR_PORT = os.getenv("IBKR_PORT", "7497")  # 7496 for live, 7497 for paper
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
        if (not start or d >= start) and (not end or d <= end):
            out.append(t)
    return out

# ─── FastAPI Setup ───────────────────────────────────────────────────────────
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Database Connection ─────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await database.connect()
    scheduler = AsyncIOScheduler(timezone=timezone('US/Pacific'))
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ─── Auth ────────────────────────────────────────────────────────────────────
def get_current_user_email(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    query = users.select().where(users.c.email == form_data.username)
    user = await database.fetch_one(query)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = jwt.encode(
        {"sub": user["email"], "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=UserCreate)
async def register(user: UserCreate):
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
    except Exception:
        raise HTTPException(status_code=400, detail="Email already registered")
    return user

# ─── Trades ──────────────────────────────────────────────────────────────────
@app.get("/trades", response_model=List[Trade])
async def get_trades(start_date: Optional[str] = None, end_date: Optional[str] = None, email: str = Depends(get_current_user_email)):
    start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    query = trades.select().where(trades.c.user == email)
    db_trades = await database.fetch_all(query)
    filtered = filter_by_date([dict(t) for t in db_trades], start, end)
    return filtered

@app.post("/trades", response_model=Trade)
async def create_trade(trade: TradeIn, email: str = Depends(get_current_user_email)):
    direction = trade.direction or ("Long" if trade.sell_price > trade.buy_price else "Short")
    qty = trade.qty
    buy_price = trade.buy_price
    sell_price = trade.sell_price
    fees = trade.fees if hasattr(trade, 'fees') else 0
    stop = trade.stop or buy_price * (0.9 if direction == "Long" else 1.1)
    r_multiple = 0 if not stop else (
        (sell_price - buy_price) / (buy_price - stop) if direction == "Long" else
        (buy_price - sell_price) / (stop - buy_price)
    )
    r_multiple = round(r_multiple, 2)
    multiplier = qty * 100 if trade.trade_type in ("Call", "Put", "Straddle", "Covered Call", "Cash Secured Put") else qty
    pnl = round((sell_price - buy_price) * multiplier - fees, 2) if direction == "Long" else round((buy_price - sell_price) * multiplier - fees, 2)

    query = trades.insert().values(
        instrument=trade.instrument,
        buy_timestamp=trade.buy_timestamp,
        sell_timestamp=trade.sell_timestamp,
        buy_price=trade.buy_price,
        sell_price=trade.sell_price,
        qty=trade.qty,
        direction=direction,
        trade_type=trade.trade_type,
        strategy_id=trade.strategy_id,
        confidence=trade.confidence,
        target=trade.target,
        stop=trade.stop,
        notes=trade.notes,
        goals=trade.goals,
        preparedness=trade.preparedness,
        what_i_learned=trade.what_i_learned,
        changes_needed=trade.changes_needed,
        user=email,
        r_multiple=r_multiple,
        pnl=pnl,
    )
    trade_id = await database.execute(query)
    for rule in trade.rule_adherence:
        await database.execute(
            trade_rules.insert().values(
                strategy_id=trade.strategy_id,
                rule_id=rule["rule_id"],
                trade_id=trade_id,
                followed=rule["followed"],
            )
        )
    return {**trade.dict(), "id": trade_id, "direction": direction, "pnl": pnl, "r_multiple": r_multiple, "user": email}

@app.put("/trades/{trade_id}", response_model=Trade)
async def update_trade(trade_id: int, trade: TradeIn, email: str = Depends(get_current_user_email)):
    direction = trade.direction or ("Long" if trade.sell_price > trade.buy_price else "Short")
    qty = trade.qty
    buy_price = trade.buy_price
    sell_price = trade.sell_price
    fees = trade.fees if hasattr(trade, 'fees') else 0
    stop = trade.stop or buy_price * (0.9 if direction == "Long" else 1.1)
    r_multiple = 0 if not stop else (
        (sell_price - buy_price) / (buy_price - stop) if direction == "Long" else
        (buy_price - sell_price) / (stop - buy_price)
    )
    r_multiple = round(r_multiple, 2)
    multiplier = qty * 100 if trade.trade_type in ("Call", "Put", "Straddle", "Covered Call", "Cash Secured Put") else qty
    pnl = round((sell_price - buy_price) * multiplier - fees, 2) if direction == "Long" else round((buy_price - sell_price) * multiplier - fees, 2)

    query = trades.update().where(trades.c.id == trade_id, trades.c.user == email).values(
        instrument=trade.instrument,
        buy_timestamp=trade.buy_timestamp,
        sell_timestamp=trade.sell_timestamp,
        buy_price=trade.buy_price,
        sell_price=trade.sell_price,
        qty=trade.qty,
        direction=direction,
        trade_type=trade.trade_type,
        strategy_id=trade.strategy_id,
        confidence=trade.confidence,
        target=trade.target,
        stop=trade.stop,
        notes=trade.notes,
        goals=trade.goals,
        preparedness=trade.preparedness,
        what_i_learned=trade.what_i_learned,
        changes_needed=trade.changes_needed,
        r_multiple=r_multiple,
        pnl=pnl,
    )
    await database.execute(query)
    if trade.rule_adherence:
        await database.execute(trade_rules.delete().where(trade_rules.c.trade_id == trade_id))
        for rule in trade.rule_adherence:
            await database.execute(
                trade_rules.insert().values(
                    strategy_id=trade.strategy_id,
                    rule_id=rule["rule_id"],
                    trade_id=trade_id,
                    followed=rule["followed"],
                )
            )
    return {**trade.dict(), "id": trade_id, "direction": direction, "pnl": pnl, "r_multiple": r_multiple, "user": email}

@app.delete("/trades/{trade_id}")
async def delete_trade(trade_id: int, email: str = Depends(get_current_user_email)):
    query = trades.delete().where(trades.c.id == trade_id, trades.c.user == email)
    await database.execute(query)
    await database.execute(trade_rules.delete().where(trade_rules.c.trade_id == trade_id))
    return {"message": "Trade deleted"}

@app.post("/trades/{trade_id}/image")
async def upload_trade_image(trade_id: int, file: UploadFile = File(...), email: str = Depends(get_current_user_email)):
    query = trades.select().where(trades.c.id == trade_id, trades.c.user == email)
    trade = await database.fetch_one(query)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    img_path = os.path.join(IMAGE_FOLDER, f"{trade_id}_{file.filename}")
    with open(img_path, "wb") as f:
        f.write(await file.read())
    await database.execute(trades.update().where(trades.c.id == trade_id).values(image_path=img_path))
    return {"message": "Image uploaded"}

@app.get("/trades/{trade_id}/image")
async def get_trade_image(trade_id: int, token: str = Query(...)):
    email = get_current_user_email(token)
    query = trades.select().where(trades.c.id == trade_id, trades.c.user == email)
    trade = await database.fetch_one(query)
    if not trade or not trade["image_path"]:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(trade["image_path"])

# ─── Strategies ──────────────────────────────────────────────────────────────
@app.get("/strategies", response_model=List[Strategy])
async def get_strategies(email: str = Depends(get_current_user_email)):
    query = strategies.select().where(strategies.c.user_email == email)
    return await database.fetch_all(query)

@app.post("/strategies", response_model=Strategy)
async def create_strategy(strategy: StrategyCreate, email: str = Depends(get_current_user_email)):
    query = strategies.insert().values(
        name=strategy.name,
        description=strategy.description,
        user_email=email,
    )
    strategy_id = await database.execute(query)
    return {**strategy.dict(), "id": strategy_id, "user_email": email, "created_at": datetime.utcnow()}

@app.put("/strategies/{strategy_id}", response_model=Strategy)
async def update_strategy(strategy_id: int, strategy: StrategyCreate, email: str = Depends(get_current_user_email)):
    query = strategies.select().where(strategies.c.id == strategy_id, strategies.c.user_email == email)
    existing = await database.fetch_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Strategy not found")
    query = strategies.update().where(strategies.c.id == strategy_id).values(
        name=strategy.name,
        description=strategy.description,
    )
    await database.execute(query)
    return {**strategy.dict(), "id": strategy_id, "user_email": email, "created_at": existing["created_at"]}

@app.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: int, email: str = Depends(get_current_user_email)):
    query = strategies.delete().where(strategies.c.id == strategy_id, strategies.c.user_email == email)
    await database.execute(query)
    await database.execute(trade_rules.delete().where(trade_rules.c.strategy_id == strategy_id))
    return {"message": "Strategy deleted"}

# ─── Rules ───────────────────────────────────────────────────────────────────
@app.get("/rules/{strategy_id}", response_model=List[Rule])
async def get_rules(strategy_id: int, email: str = Depends(get_current_user_email)):
    query = strategies.select().where(strategies.c.id == strategy_id, strategies.c.user_email == email)
    if not await database.fetch_one(query):
        raise HTTPException(status_code=404, detail="Strategy not found")
    query = trade_rules.select().where(trade_rules.c.strategy_id == strategy_id)
    return await database.fetch_all(query)

@app.post("/rules", response_model=Rule)
async def create_rule(rule: RuleCreate, email: str = Depends(get_current_user_email)):
    query = strategies.select().where(strategies.c.id == rule.strategy_id, strategies.c.user_email == email)
    if not await database.fetch_one(query):
        raise HTTPException(status_code=404, detail="Strategy not found")
    query = trade_rules.insert().values(
        strategy_id=rule.strategy_id,
        rule_type=rule.rule_type,
        rule_text=rule.rule_text,
        followed=False,
    )
    rule_id = await database.execute(query)
    return {**rule.dict(), "id": rule_id, "trade_id": None, "followed": False, "created_at": datetime.utcnow()}

@app.get("/trade_rules/{trade_id}", response_model=List[Rule])
async def get_trade_rules(trade_id: int, email: str = Depends(get_current_user_email)):
    query = trades.select().where(trades.c.id == trade_id, trades.c.user == email)
    if not await database.fetch_one(query):
        raise HTTPException(status_code=404, detail="Trade not found")
    query = trade_rules.select().where(trade_rules.c.trade_id == trade_id)
    return await database.fetch_all(query)

@app.put("/trade_rules/{trade_id}/{rule_id}", response_model=Rule)
async def update_trade_rule(trade_id: int, rule_id: int, update: TradeRuleUpdate, email: str = Depends(get_current_user_email)):
    query = trades.select().where(trades.c.id == trade_id, trades.c.user == email)
    if not await database.fetch_one(query):
        raise HTTPException(status_code=404, detail="Trade not found")
    query = trade_rules.select().where(trade_rules.c.trade_id == trade_id, trade_rules.c.rule_id == rule_id)
    existing = await database.fetch_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Trade rule not found")
    query = trade_rules.update().where(trade_rules.c.trade_id == trade_id, trade_rules.c.rule_id == rule_id).values(followed=update.followed)
    await database.execute(query)
    return {**existing, "followed": update.followed}

# ─── Brokers ─────────────────────────────────────────────────────────────────
@app.post("/connect_schwab")
async def connect_schwab(email: str = Depends(get_current_user_email)):
    redirect_uri = "https://127.0.0.1:8000/callback"
    try:
        client = easy_client(SCHWAB_CLIENT_ID, redirect_uri, None, asynchio=True)
        auth_url = client.get_auth_url()
        return