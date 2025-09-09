# main.py

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
from pydantic import BaseModel, EmailStr, validator
import matplotlib.pyplot as plt
from jose import jwt, JWTError
from tda.auth import easy_client
from tda.client import Client
from cryptography.fernet import Fernet
from ib_insync import IB, Trade
import pandas as pd  # For analytics

from db import engine, metadata, database, users
from auth import hash_password, verify_password
from import_trades import parse_smart_csv
from grouping import group_trades_by_entry_exit
from export_tools import export_to_excel as export_excel_util, export_to_pdf as export_pdf_util
from analytics import compute_summary_stats

from dotenv import load_dotenv

load_dotenv()

# ─── Config & Logging ────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
SCHWAB_CLIENT_ID = os.getenv("SCHWAB_CLIENT_ID")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
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
    return [t for t in load_all_trades() if t.get("user") == user_email]

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

# ─── Pydantic Models ─────────────────────────────────────────────────────────
class TradeIn(BaseModel):
    instrument: str
    buy_timestamp: datetime
    sell_timestamp: datetime
    buy_price: float
    sell_price: float
    qty: int
    direction: Optional[str] = None
    trade_type: Optional[str] = "Stock"
    strategy: Optional[str] = ""
    confidence: Optional[int] = 0
    target: Optional[float] = 0.0
    stop: Optional[float] = 0.0
    notes: Optional[str] = ""
    goals: Optional[str] = ""
    preparedness: Optional[str] = ""
    what_i_learned: Optional[str] = ""
    changes_needed: Optional[str] = ""

class Trade(TradeIn):
    direction: str
    pnl: float
    r_multiple: float
    image_path: Optional[str] = ""
    user: str

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    billing_address: str
    email: EmailStr
    password: str
    verify_password: str

    @validator("verify_password")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v

class IBKRConnect(BaseModel):
    api_token: str
    account_id: str

class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class RuleCreate(BaseModel):
    strategy_id: int
    rule_type: str  # 'entry' or 'exit'
    rule_text: str

class TradeRuleUpdate(BaseModel):
    followed: bool

# ─── FastAPI App Initialization ─────────────────────────────────────────────
app = FastAPI()

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

# ─── Strategy and Rule Endpoints ────────────────────────────────────────────
@app.post("/strategies", response_model=Dict)
async def create_strategy(strategy: StrategyCreate, current_user: dict = Depends(get_current_user)):
    insert = strategies.insert().values(
        user_email=current_user["email"],
        name=strategy.name,
        description=strategy.description
    )
    strategy_id = await database.execute(insert)
    return {"id": strategy_id, "name": strategy.name, "description": strategy.description}

@app.get("/strategies", response_model=List[Dict])
async def list_strategies(current_user: dict = Depends(get_current_user)):
    query = strategies.select().where(strategies.c.user_email == current_user["email"])
    return await database.fetch_all(query)

@app.post("/rules", response_model=Dict)
async def create_rule(rule: RuleCreate, current_user: dict = Depends(get_current_user)):
    # Verify strategy belongs to user
    strategy_query = strategies.select().where(strategies.c.id == rule.strategy_id, strategies.c.user_email == current_user["email"])
    if not await database.fetch_one(strategy_query):
        raise HTTPException(status_code=404, detail="Strategy not found or not owned by user")
    insert = trade_rules.insert().values(
        strategy_id=rule.strategy_id,
        rule_type=rule.rule_type,
        rule_text=rule.rule_text
    )
    rule_id = await database.execute(insert)
    return {"id": rule_id, "strategy_id": rule.strategy_id, "rule_type": rule.rule_type, "rule_text": rule.rule_text}

@app.get("/rules/{strategy_id}", response_model=List[Dict])
async def list_rules(strategy_id: int, current_user: dict = Depends(get_current_user)):
    strategy_query = strategies.select().where(strategies.c.id == strategy_id, strategies.c.user_email == current_user["email"])
    if not await database.fetch_one(strategy_query):
        raise HTTPException(status_code=404, detail="Strategy not found or not owned by user")
    query = trade_rules.select().where(trade_rules.c.strategy_id == strategy_id)
    return await database.fetch_all(query)

@app.put("/trade_rules/{rule_id}", response_model=Dict)
async def update_trade_rule(rule_id: int, update: TradeRuleUpdate, current_user: dict = Depends(get_current_user)):
    # Verify rule belongs to user's strategy
    rule_query = trade_rules.select().join(strategies, trade_rules.c.strategy_id == strategies.c.id).where(
        trade_rules.c.id == rule_id, strategies.c.user_email == current_user["email"]
    )
    if not await database.fetch_one(rule_query):
        raise HTTPException(status_code=404, detail="Rule not found or not owned by user")
    update_query = trade_rules.update().where(trade_rules.c.id == rule_id).values(followed=update.followed)
    await database.execute(update_query)
    return {"id": rule_id, "followed": update.followed}

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
        rule_query = trade_rules.select().where(trade_rules.c.strategy_id == strategy_id)
        rules = await database.fetch_all(rule_query)
        for rule in rules:
            rule_id = rule["id"]
            # Get trades associated with this strategy (assume strategy stored in trade notes or extend model)
            # For now, assume trades have 'strategy' field; extend if needed
            strategy_trades = [t for t in filtered if t.get('strategy') == strat['name']]
            # Get adherence for this rule in trades (assume trade_rules has trade_id)
            adherence_query = trade_rules.select().where(trade_rules.c.strategy_id == strategy_id, trade_rules.c.trade_id.in_([t['id'] for t in strategy_trades if 'id' in t]))
            adherence = await database.fetch_all(adherence_query)
            followed_count = len([a for a in adherence if a['followed']])
            total_count = len(adherence)
            if total_count > 0:
                win_rate_followed = len([t for t in strategy_trades if t['pnl'] > 0 and t.get('followed_rule_id') == rule_id]) / followed_count if followed_count > 0 else 0
                win_rate_not_followed = len([t for t in strategy_trades if t['pnl'] > 0 and t.get('followed_rule_id') != rule_id]) / (total_count - followed_count) if total_count > followed_count else 0
                rule_analytics[f"Strategy {strat['name']} - Rule {rule['rule_text']}"] = {
                    "followed_rate": followed_count / total_count,
                    "win_rate_followed": win_rate_followed,
                    "win_rate_not_followed": win_rate_not_followed
                }

    return {
        "basic_stats": basic_stats,
        "rule_analytics": rule_analytics
    }

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