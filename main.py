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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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
from analytics import (
    compute_summary_stats,
    compute_by_strategy,
    compute_by_rule,
    compute_by_trade_type,
    compute_by_hour,
    compute_by_day_of_week,
    compute_risk_metrics,
    compute_behavioral_insights
)
from schemas import Strategy, StrategyCreate, Rule, RuleCreate, TradeIn, Trade, UserCreate, TradeRuleUpdate
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from sqlalchemy import select

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
        shutil.move(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise
    finally:
        try:
            os.close(fd)
        except OSError:
            pass

def load_json(path: str) -> List[dict]:
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def backup_data():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")
    trades = load_json(SAVE_FILE)
    atomic_write_json(backup_path, trades)
    backups = sorted(os.listdir(BACKUP_DIR))
    if len(backups) > MAX_BACKUPS:
        old_backup = os.path.join(BACKUP_DIR, backups[0])
        os.remove(old_backup)

# ─── Auth Helpers ────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    query = select([users.c.id, users.c.email, users.c.is_active]).where(users.c.email == email)
    result = await database.fetch_one(query)
    if result is None:
        raise credentials_exception
    if not result["is_active"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    return {"email": result["email"]}

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.post("/register")
async def register(user: UserCreate):
    query = users.select().where(users.c.email == user.email)
    existing = await database.fetch_one(query)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(user.password)
    query = users.insert().values(
        first_name=user.first_name,
        last_name=user.last_name,
        billing_address=user.billing_address,
        email=user.email,
        hashed_password=hashed,
    )
    last_record_id = await database.execute(query)
    return {"msg": "User created", "user_id": last_record_id}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    query = users.select().where(users.c.email == form_data.username)
    user = await database.fetch_one(query)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: Dict = Depends(get_current_user)):
    return current_user

@app.post("/strategies")
async def create_strategy(strategy: StrategyCreate, current_user: Dict = Depends(get_current_user)):
    query = strategies.insert().values(
        user_email=current_user["email"],
        name=strategy.name,
        description=strategy.description,
    )
    strategy_id = await database.execute(query)
    # Insert entry rules
    for rule_text in strategy.entry_rules:
        rule_query = trade_rules.insert().values(
            strategy_id=strategy_id,
            rule_type="entry",
            rule_text=rule_text,
        )
        await database.execute(rule_query)
    # Insert exit rules
    for rule_text in strategy.exit_rules:
        rule_query = trade_rules.insert().values(
            strategy_id=strategy_id,
            rule_type="exit",
            rule_text=rule_text,
        )
        await database.execute(rule_query)
    return {"id": strategy_id, "name": strategy.name}

@app.get("/strategies")
async def get_strategies(current_user: Dict = Depends(get_current_user)):
    query = strategies.select().where(strategies.c.user_email == current_user["email"])
    return await database.fetch_all(query)

@app.get("/rules/{strategy_id}")
async def get_rules(strategy_id: int, current_user: Dict = Depends(get_current_user)):
    query = trade_rules.select().where(
        trade_rules.c.strategy_id == strategy_id,
        trade_rules.c.trade_id.is_(None)
    )
    return await database.fetch_all(query)

@app.post("/trades")
async def create_trade(trade: TradeIn, current_user: Dict = Depends(get_current_user)):
    # Prepare trade data excluding rule_adherence
    trade_data = trade.dict(exclude={"rule_adherence", "id", "user"})
    trade_data["user"] = current_user["email"]
    # Calculate PnL and R-multiple if not provided
    if trade_data.get("pnl") is None and trade.buy_price and trade.sell_price and trade.qty:
        trade_data["pnl"] = (trade.sell_price - trade.buy_price) * trade.qty * (1 if trade_data.get("direction") == "Long" else -1) - trade_data.get("fees", 0)
    if trade_data.get("r_multiple") is None and trade.buy_price and trade.stop and trade_data.get("pnl") is not None:
        risk = abs(trade.buy_price - trade.stop) * trade.qty
        trade_data["r_multiple"] = trade_data["pnl"] / risk if risk != 0 else 0
    # Insert trade
    query = trades.insert().values(**trade_data)
    trade_id = await database.execute(query)
    # Handle rule adherence
    rule_adherence = trade.rule_adherence or []
    for ra in rule_adherence:
        if "rule_id" in ra and "followed" in ra:
            # Fetch original rule
            rule_query = select([trade_rules]).where(trade_rules.c.id == ra["rule_id"])
            original_rule = await database.fetch_one(rule_query)
            if original_rule:
                # Insert adherence record with original_rule_id
                adherence_query = trade_rules.insert().values(
                    strategy_id=original_rule["strategy_id"],
                    rule_type=original_rule["rule_type"],
                    rule_text=original_rule["rule_text"],
                    trade_id=trade_id,
                    original_rule_id=ra["rule_id"],
                    followed=ra["followed"]
                )
                await database.execute(adherence_query)
    return JSONResponse(content={"id": trade_id, "msg": "Trade created successfully"}, status_code=201)

@app.get("/trades")
async def get_trades(
    skip: int = 0,
    limit: int = 100,
    current_user: Dict = Depends(get_current_user)
):
    # Fetch trades
    trade_query = trades.select().where(trades.c.user == current_user["email"]).offset(skip).limit(limit)
    trade_rows = await database.fetch_all(trade_query)
    trades_list = []
    for trade_row in trade_rows:
        trade_dict = dict(trade_row)
        # Fetch rule adherences for this trade
        rule_query = trade_rules.select().where(trade_rules.c.trade_id == trade_row["id"])
        rule_rows = await database.fetch_all(rule_query)
        trade_dict["rule_adherence"] = [
            {
                "rule_id": rule["original_rule_id"],
                "followed": rule["followed"],
                "rule_text": rule["rule_text"],
                "rule_type": rule["rule_type"]
            }
            for rule in rule_rows
        ]
        trades_list.append(trade_dict)
    return trades_list

@app.put("/trades/{trade_id}")
async def update_trade(trade_id: int, trade_update: TradeIn, current_user: Dict = Depends(get_current_user)):
    # Update trade
    trade_data = trade_update.dict(exclude_unset=True, exclude={"rule_adherence", "id", "user"})
    query = trades.update().where(
        trades.c.id == trade_id,
        trades.c.user == current_user["email"]
    ).values(**trade_data)
    result = await database.execute(query)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Trade not found")
    # Delete old adherences
    delete_query = trade_rules.delete().where(trade_rules.c.trade_id == trade_id)
    await database.execute(delete_query)
    # Insert new adherences
    rule_adherence = trade_update.rule_adherence or []
    for ra in rule_adherence:
        if "rule_id" in ra and "followed" in ra:
            rule_query = select([trade_rules]).where(trade_rules.c.id == ra["rule_id"])
            original_rule = await database.fetch_one(rule_query)
            if original_rule:
                adherence_query = trade_rules.insert().values(
                    strategy_id=original_rule["strategy_id"],
                    rule_type=original_rule["rule_type"],
                    rule_text=original_rule["rule_text"],
                    trade_id=trade_id,
                    original_rule_id=ra["rule_id"],
                    followed=ra["followed"]
                )
                await database.execute(adherence_query)
    return {"msg": "Trade updated"}

@app.delete("/trades/{trade_id}")
async def delete_trade(trade_id: int, current_user: Dict = Depends(get_current_user)):
    # Delete adherence rules first
    delete_rules = trade_rules.delete().where(trade_rules.c.trade_id == trade_id)
    await database.execute(delete_rules)
    # Delete trade
    query = trades.delete().where(
        trades.c.id == trade_id,
        trades.c.user == current_user["email"]
    )
    result = await database.execute(query)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {"msg": "Trade deleted"}

@app.post("/trades/{trade_id}/rules/{rule_id}/update")
async def update_rule_adherence(
    trade_id: int,
    rule_id: int,
    update: TradeRuleUpdate,
    current_user: Dict = Depends(get_current_user)
):
    query = trade_rules.update().where(
        trade_rules.c.id == rule_id,
        trade_rules.c.trade_id == trade_id,
    ).values(followed=update.followed)
    result = await database.execute(query)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Rule adherence not found")
    return {"msg": "Rule adherence updated"}

@app.post("/import/csv")
async def import_csv(file: UploadFile = File(...), current_user: Dict = Depends(get_current_user)):
    content = await file.read()
    trades_list = parse_smart_csv(content.decode("utf-8"))
    added = 0
    for trade_data in trades_list:
        trade_in = TradeIn(**trade_data, user=current_user["email"])
        query = trades.insert().values(**trade_in.dict(exclude={"rule_adherence"}))
        await database.execute(query)
        added += 1
    return {"msg": f"Imported {added} trades"}

@app.get("/analytics")
async def get_analytics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    strategy_id: Optional[int] = Query(None),
    trade_type: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    followed: Optional[str] = Query("all"),
    confidence_min: Optional[int] = Query(0),
    confidence_max: Optional[int] = Query(5),
    current_user: Dict = Depends(get_current_user)
):
    # Fetch trades with rule_adherence populated
    trades_list = await get_trades(0, 1000, current_user)
    # Apply filters
    filtered_trades = apply_analytics_filters(trades_list, {
        "start_date": start_date,
        "end_date": end_date,
        "strategy_id": strategy_id,
        "trade_type": trade_type,
        "direction": direction,
        "followed": followed,
        "confidence_min": confidence_min,
        "confidence_max": confidence_max
    })
    summary = compute_summary_stats(filtered_trades)
    by_strategy = compute_by_strategy(filtered_trades)
    by_rule = compute_by_rule(filtered_trades)
    by_type = compute_by_trade_type(filtered_trades)
    by_hour = compute_by_hour(filtered_trades)
    by_day_of_week = compute_by_day_of_week(filtered_trades)
    risk_metrics = compute_risk_metrics(filtered_trades)
    behavioral_insights = compute_behavioral_insights(filtered_trades)
    equity_curve = compute_equity_curve(filtered_trades)
    heatmap_hour = compute_heatmap_hour(filtered_trades)
    heatmap_day = compute_heatmap_day(filtered_trades)
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

def compute_equity_curve(trades):
    sorted_trades = sorted(trades, key=lambda t: t['buy_timestamp'])
    curve = []
    cumulative_pnl = 0
    for t in sorted_trades:
        cumulative_pnl += t.get('pnl', 0)
        curve.append({
            'date': str(t['buy_timestamp'])[:10],
            'pnl': cumulative_pnl
        })
    return curve

def compute_heatmap_hour(trades):
    from collections import defaultdict
    heatmap = defaultdict(float)
    for t in trades:
        ts = t['buy_timestamp']
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        hour = ts.hour
        heatmap[hour] += t.get('pnl', 0)
    return dict(heatmap)

def compute_heatmap_day(trades):
    from collections import defaultdict
    heatmap = defaultdict(float)
    for t in trades:
        ts = t['buy_timestamp']
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        day = ts.weekday()
        heatmap[day] += t.get('pnl', 0)
    return dict(heatmap)

# Broker integration endpoints (stubs)
@app.post("/brokers/ibkr")
async def add_ibkr_broker(form_data: dict, current_user: Dict = Depends(get_current_user)):
    creds_json = json.dumps(form_data)
    encrypted = encrypt_data(creds_json)
    query = brokers.insert().values(
        user_email=current_user["email"],
        broker_type="ibkr",
        creds_json=encrypted
    )
    broker_id = await database.execute(query)
    return {"id": broker_id}

@app.post("/import/ibkr")
async def import_ibkr(start_date: str, end_date: str, broker_id: int, current_user: Dict = Depends(get_current_user)):
    return {"msg": "Import started"}

# Export endpoints
@app.get("/export/excel")
async def export_excel(current_user: Dict = Depends(get_current_user)):
    query = trades.select().where(trades.c.user == current_user["email"])
    trades_data = await database.fetch_all(query)
    trades_list = [dict(t) for t in trades_data]
    filename = export_excel_util(trades_list)
    return FileResponse(filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.get("/export/pdf")
async def export_pdf(current_user: Dict = Depends(get_current_user)):
    query = trades.select().where(trades.c.user == current_user["email"])
    trades_data = await database.fetch_all(query)
    trades_list = [dict(t) for t in trades_data]
    filename = export_pdf_util(trades_list)
    return FileResponse(filename, media_type="application/pdf")

# Scheduler for periodic tasks (e.g., backups)
scheduler = AsyncIOScheduler(timezone=timezone("UTC"))
scheduler.add_job(backup_data, "interval", hours=24)
scheduler.start()

# Health check
@app.get("/")
def read_root():
    return {"Tao Trader Journal": "Online"}

# Create tables on startup
@app.on_event("startup")
async def startup():
    # Use synchronous connection for metadata.create_all
    with engine.connect() as conn:
        metadata.create_all(conn)
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()