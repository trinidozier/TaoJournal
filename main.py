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
    status, Depends
)
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
import matplotlib.pyplot as plt
# switch to python-jose’s jwt + JWTError
from jose import jwt, JWTError


from db import engine, metadata, database, users
from auth import hash_password, verify_password
from import_trades import parse_tradovate_csv
from grouping import group_trades_by_entry_exit
from export_tools import export_to_excel as export_excel_util, export_to_pdf as export_pdf_util
from analytics import compute_summary_stats

from dotenv import load_dotenv

load_dotenv()   # reads .env into os.environ

# ─── Config & Logging ────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

SAVE_FILE    = "annotated_trades.json"
BACKUP_DIR   = "backups"
MAX_BACKUPS  = 10
IMAGE_FOLDER = "trade_images"

os.makedirs(BACKUP_DIR,   exist_ok=True)
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
    dst       = os.path.join(BACKUP_DIR, f"trades-{timestamp}.json")
    shutil.copy2(src, dst)
    backs = sorted(os.listdir(BACKUP_DIR))
    while len(backs) > MAX_BACKUPS:
        os.remove(os.path.join(BACKUP_DIR, backs.pop(0)))

def load_all_trades() -> List[dict]:
    if not os.path.exists(SAVE_FILE):
        return []
    with open(SAVE_FILE) as f:
        return json.load(f)

def load_trades(user_email: str) -> List[dict]:
    return [t for t in load_all_trades() if t.get("user") == user_email]

def save_trades(user_trades: List[dict], user_email: str):
    all_trades   = load_all_trades()
    others       = [t for t in all_trades if t.get("user") != user_email]
    merged       = others + user_trades

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
            d  = dt.date()
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

    # catch python-jose’s error, not PyJWTError
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


# ─── Pydantic Models ─────────────────────────────────────────────────────────
class TradeIn(BaseModel):
    instrument      : str
    buy_timestamp   : datetime
    sell_timestamp  : datetime
    buy_price       : float
    sell_price      : float
    qty             : int
    strategy        : Optional[str]   = ""
    confidence      : Optional[int]   = 0
    target          : Optional[float] = 0.0
    stop            : Optional[float] = 0.0
    notes           : Optional[str]   = ""
    goals           : Optional[str]   = ""
    preparedness    : Optional[str]   = ""
    what_i_learned  : Optional[str]   = ""
    changes_needed  : Optional[str]   = ""

class Trade(TradeIn):
    direction    : str
    pnl          : float
    r_multiple   : float
    image_path   : Optional[str] = ""
    user         : str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

# ─── FastAPI App Initialization ─────────────────────────────────────────────
app = FastAPI()

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
    
# ─── JWT Smoke-Test Endpoint  ──────────────────────────────────────
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
    insert = users.insert().values(email=user.email, hashed_password=hashed_pw)
    await database.execute(insert)
    return {"message": "User registered successfully"}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    query = users.select().where(users.c.email == form_data.username)
    user = await database.fetch_one(query)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer"}

# ─── Trade Endpoints ────────────────────────────────────────────────────────

@app.get("/trades", response_model=List[Trade])
async def list_trades(current_user: dict = Depends(get_current_user)):
    return load_trades(current_user["email"])


@app.post("/trades", response_model=Trade)
async def add_trade(payload: TradeIn,
                    current_user: dict = Depends(get_current_user)):
    trades    = load_trades(current_user["email"])
    direction = "Long" if payload.sell_price > payload.buy_price else "Short"
    pnl       = (payload.sell_price - payload.buy_price) if direction == "Long" else (payload.buy_price - payload.sell_price)
    risk      = abs(payload.buy_price - payload.stop) if payload.stop else 0
    r_mult    = round(pnl / risk, 2) if risk else 0.0

    record = payload.dict()
    record.update({
        "direction":  direction,
        "pnl":        round(pnl, 2),
        "r_multiple": r_mult,
        "image_path": "",
        "user":       current_user["email"]
    })

    trades.append(record)
    save_trades(trades, current_user["email"])
    return record


@app.delete("/trades/{index}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(index: int,
                       current_user: dict = Depends(get_current_user)):
    trades = load_trades(current_user["email"])
    if index < 0 or index >= len(trades):
        raise HTTPException(status_code=404, detail="Trade not found")
    trades.pop(index)
    save_trades(trades, current_user["email"])


@app.post("/import_csv")
async def import_csv(file: UploadFile = File(...),
                     current_user: dict = Depends(get_current_user)):
    content = await file.read()
    rows    = parse_tradovate_csv(io.BytesIO(content))
    trades  = load_trades(current_user["email"])

    for payload in rows:
        direction = "Long" if payload["sell_price"] > payload["buy_price"] else "Short"
        pnl       = (payload["sell_price"] - payload["buy_price"]) if direction == "Long" else (payload["buy_price"] - payload["sell_price"])
        risk      = abs(payload["buy_price"] - payload.get("stop", 0)) if payload.get("stop") else 0
        r_mult    = round(pnl / risk, 2) if risk else 0.0

        record = payload.copy()
        record.update({
            "direction":  direction,
            "pnl":        round(pnl, 2),
            "r_multiple": r_mult,
            "image_path": "",
            "user":       current_user["email"]
        })
        trades.append(record)

    save_trades(trades, current_user["email"])
    return {"imported": len(rows)}


@app.get("/analytics")
async def analytics(start: Optional[date] = Query(None),
                    end:   Optional[date] = Query(None),
                    current_user: dict = Depends(get_current_user)):
    trades   = load_trades(current_user["email"])
    filtered = filter_by_date(trades, start, end)
    return compute_summary_stats(filtered)


@app.get("/export/excel")
async def export_excel(start: Optional[date] = Query(None),
                       end:   Optional[date] = Query(None),
                       current_user: dict = Depends(get_current_user)):
    trades   = load_trades(current_user["email"])
    filtered = filter_by_date(trades, start, end)
    xlsx_buf = export_excel_util(filtered)
    return FileResponse(xlsx_buf,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        filename="trades.xlsx")


@app.get("/export/pdf")
async def export_pdf(start: Optional[date] = Query(None),
                     end:   Optional[date] = Query(None),
                     current_user: dict = Depends(get_current_user)):
    trades   = load_trades(current_user["email"])
    filtered = filter_by_date(trades, start, end)
    pdf_buf  = export_pdf_util(filtered)
    return FileResponse(pdf_buf, media_type="application/pdf", filename="trades.pdf")


@app.get("/trades/{index}/image")
async def get_trade_image(index: int,
                          current_user: dict = Depends(get_current_user)):
    trades     = load_trades(current_user["email"])
    if index < 0 or index >= len(trades):
        raise HTTPException(status_code=404, detail="Trade not found")

    img_path = trades[index].get("image_path")
    if not img_path or not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(img_path)
