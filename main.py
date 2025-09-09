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
from typing import List, Optional
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

# ─── IBKR Endpoints ─────────────────────────────────────────────────────────
@app.post("/connect_ibkr")
async def connect_ibkr(data: IBKRConnect, current_user: dict = Depends(get_current_user)):
    try:
        f = Fernet(ENCRYPTION_KEY.encode())
        encrypted_token = f.encrypt(data.api_token.encode())
        update_query = users.update().where(users.c.email == current_user["email"]).values(
            broker_type="IBKR",
            encrypted_access_token=encrypted_token,
            account_id=data.account_id
        )
        await database.execute(update_query)
        return {"message": "Interactive Brokers account connected"}
    except Exception as e:
        logger.error(f"IBKR connect error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Connect error: {str(e)}")

@app.post("/import_from_ibkr")
async def import_from_ibkr(start_date: str, end_date: str, current_user: dict = Depends(get_current_user)):
    query = users.select().where(users.c.email == current_user["email"])
    db_user = await database.fetch_one(query)
    if db_user["broker_type"] != "IBKR":
        raise HTTPException(status_code=400, detail="IBKR not connected")
    f = Fernet(ENCRYPTION_KEY.encode())
    api_token = f.decrypt(db_user["encrypted_access_token"]).decode()
    account_id = db_user["account_id"]
    try:
        ib = IB()
        ib.connect(IBKR_HOST, int(IBKR_PORT), clientId=1)
        trades = ib.reqAllOpenOrders()  # Or use reqExecutions for historical trades
        ib.disconnect()
        trades_data = []
        for trade in trades:
            if trade.orderStatus.status == "Filled":
                trade_type = "Option" if trade.contract.secType == "OPT" else "Stock"
                direction = "Long" if trade.order.action == "BUY" else "Short"
                trade_data = {
                    "instrument": trade.contract.symbol,
                    "buy_timestamp": trade.orderStatus.fillTime or datetime.utcnow().isoformat(),
                    "sell_timestamp": trade.orderStatus.fillTime or datetime.utcnow().isoformat(),
                    "buy_price": trade.orderStatus.avgFillPrice,
                    "sell_price": trade.orderStatus.avgFillPrice,
                    "qty": int(trade.order.totalQuantity),
                    "direction": direction,
                    "trade_type": trade_type,
                    "strategy": "",
                    "confidence": 0,
                    "target": 0.0,
                    "stop": 0.0,
                    "notes": "",
                    "goals": "",
                    "preparedness": "",
                    "what_i_learned": "",
                    "changes_needed": "",
                    "user": current_user["email"]
                }
                trades_data.append(trade_data)
        trades = load_trades(current_user["email"])
        trades.extend(trades_data)
        save_trades(trades, current_user["email"])
        return {"imported": len(trades_data)}
    except Exception as e:
        logger.error(f"IBKR import error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")

# ─── Schwab OAuth Endpoints ─────────────────────────────────────────────────
@app.get("/connect_schwab")
async def connect_schwab(current_user: dict = Depends(get_current_user)):
    redirect_uri = "https://taojournal-production.up.railway.app/schwab_callback"
    try:
        temp_token_path = os.path.join(tempfile.gettempdir(), f"schwab_{current_user['email']}.json")
        auth_url = easy_client(
            client_id=SCHWAB_CLIENT_ID,
            redirect_uri=redirect_uri,
            token_path=temp_token_path,
            headless=False
        ).auth_url
        return {"redirect_url": auth_url}
    except Exception as e:
        logger.error(f"Schwab OAuth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")

@app.get("/schwab_callback")
async def schwab_callback(code: str, current_user: dict = Depends(get_current_user)):
    redirect_uri = "https://taojournal-production.up.railway.app/schwab_callback"
    temp_token_path = os.path.join(tempfile.gettempdir(), f"schwab_{current_user['email']}.json")
    try:
        client = easy_client(
            client_id=SCHWAB_CLIENT_ID,
            redirect_uri=redirect_uri,
            token_path=temp_token_path,
            code=code
        )
        token_data = client.get_token()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        f = Fernet(ENCRYPTION_KEY.encode())
        update_query = users.update().where(users.c.email == current_user["email"]).values(
            broker_type="Schwab",
            encrypted_access_token=f.encrypt(access_token.encode()),
            encrypted_refresh_token=f.encrypt(refresh_token.encode())
        )
        await database.execute(update_query)
        if os.path.exists(temp_token_path):
            os.remove(temp_token_path)
        return {"message": "Schwab account connected"}
    except Exception as e:
        logger.error(f"Schwab callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Callback error: {str(e)}")

@app.post("/import_from_schwab")
async def import_from_schwab(start_date: str, end_date: str, current_user: dict = Depends(get_current_user)):
    query = users.select().where(users.c.email == current_user["email"])
    db_user = await database.fetch_one(query)
    if db_user["broker_type"] != "Schwab":
        raise HTTPException(status_code=400, detail="Schwab not connected")
    f = Fernet(ENCRYPTION_KEY.encode())
    access_token = f.decrypt(db_user["encrypted_access_token"]).decode()
    refresh_token = f.decrypt(db_user["encrypted_refresh_token"]).decode()
    try:
        client = Client(access_token=access_token)
        token_data = client.get_token()
        if token_data.get("access_token_expires_at") < time.time() + 300:
            new_tokens = client.refresh_token(refresh_token)
            new_access_token = new_tokens["access_token"]
            new_refresh_token = new_tokens["refresh_token"]
            update_query = users.update().where(users.c.email == current_user["email"]).values(
                encrypted_access_token=f.encrypt(new_access_token.encode()),
                encrypted_refresh_token=f.encrypt(new_refresh_token.encode())
            )
            await database.execute(update_query)
            client = Client(access_token=new_access_token)
        accounts = client.get_accounts(fields=["positions"]).json()
        account_id = accounts[0]["securitiesAccount"]["accountId"]
        transactions = client.get_transactions(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            transaction_type=Client.TransactionType.TRADE
        ).json()
        trades_data = []
        for tx in transactions.get("transactions", []):
            if tx["type"] == "TRADE":
                trade = {
                    "instrument": tx["symbol"],
                    "buy_timestamp": tx["transactionDate"],
                    "sell_timestamp": tx.get("settlementDate", tx["transactionDate"]),
                    "buy_price": tx.get("price", 0.0),
                    "sell_price": tx.get("price", 0.0),
                    "qty": int(tx.get("quantity", 0)),
                    "direction": "Long" if tx["activityType"] == "BUY" else "Short",
                    "trade_type": "Option" if tx.get("instrumentType") == "OPTION" else "Stock",
                    "strategy": "",
                    "confidence": 0,
                    "target": 0.0,
                    "stop": 0.0,
                    "notes": "",
                    "goals": "",
                    "preparedness": "",
                    "what_i_learned": "",
                    "changes_needed": "",
                    "user": current_user["email"]
                }
                trades_data.append(trade)
        trades = load_trades(current_user["email"])
        trades.extend(trades_data)
        save_trades(trades, current_user["email"])
        return {"imported": len(trades_data)}
    except Exception as e:
        logger.error(f"Schwab import error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")

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
        "user": current_user["email"]
    })
    trades.append(record)
    save_trades(trades, current_user["email"])
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
    })
    trades[index].update(updated)
    save_trades(trades, current_user["email"])
    return trades[index]

@app.delete("/trades/{index}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(index: int, current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    if index < 0 or index >= len(trades):
        raise HTTPException(status_code=404, detail="Trade not found")
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
            "user": current_user["email"]
        })
        trades.append(record)
    save_trades(trades, current_user["email"])
    return {"imported": len(rows), "message": f"Successfully imported {len(rows)} trades."}

@app.get("/analytics")
async def analytics(start: Optional[date] = Query(None), end: Optional[date] = Query(None), current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    filtered = filter_by_date(trades, start, end)
    return compute_summary_stats(filtered)

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