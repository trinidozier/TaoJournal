# main.py

import os
import json
import shutil
import tempfile
import time
import logging

from datetime import datetime, date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from import_trades import parse_tradovate_csv
from grouping import group_trades_by_entry_exit
from export_tools import export_to_excel as export_excel_util, export_to_pdf as export_pdf_util
from analytics import compute_summary_stats, compute_dashboard

# ─── Setup & Logging ──────────────────────────────────────────────────────────
SAVE_FILE    = "annotated_trades.json"
BACKUP_DIR   = "backups"
MAX_BACKUPS  = 10
IMAGE_FOLDER = "trade_images"

os.makedirs(BACKUP_DIR,   exist_ok=True)
os.makedirs(IMAGE_FOLDER,  exist_ok=True)

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Atomic JSON Storage ──────────────────────────────────────────────────────
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

def load_trades() -> List[dict]:
    if not os.path.exists(SAVE_FILE):
        return []
    with open(SAVE_FILE) as f:
        return json.load(f)

def save_trades(trades: List[dict]):
    if os.path.exists(SAVE_FILE):
        rotate_backups(SAVE_FILE)
    atomic_write_json(SAVE_FILE, trades)

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

# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI()

@app.get("/trades", response_model=List[Trade])
def list_trades():
    return load_trades()

@app.post("/trades", response_model=Trade)
def add_trade(payload: TradeIn):
    try:
        trades   = load_trades()
        direction = "Long" if payload.sell_price > payload.buy_price else "Short"
        pnl       = (payload.sell_price - payload.buy_price) if direction == "Long" else (payload.buy_price - payload.sell_price)
        risk      = abs(payload.buy_price - payload.stop) if payload.stop else 0
        r_mult    = round(pnl / risk, 2) if risk else 0.0

        record = payload.dict()
        record.update({
            "direction":   direction,
            "pnl":         round(pnl, 2),
            "r_multiple":  r_mult,
            "image_path":  ""
        })

        trades.append(record)
        save_trades(trades)
        return record

    except Exception:
        logger.exception("Failed to save new trade")
        raise HTTPException(status_code=500, detail="Unable to persist trade—see server logs")

@app.delete("/trades/{idx}")
def delete_trade(idx: int):
    trades = load_trades()
    if idx < 0 or idx >= len(trades):
        raise HTTPException(404, "Trade not found")
    trades.pop(idx)
    save_trades(trades)
    return {"detail": "deleted"}

@app.post("/import-csv")
async def import_csv(file: UploadFile = File(...)):
    content       = (await file.read()).decode()
    raw           = parse_tradovate_csv(content)
    grouped       = group_trades_by_entry_exit(raw)

    trades        = load_trades()
    existing_keys = {
        (
            t["instrument"], t["buy_timestamp"], t["sell_timestamp"],
            t["qty"],        t["buy_price"],      t["sell_price"]
        )
        for t in trades
    }

    added = 0
    for t0 in grouped:
        key = (
            t0["Instrument"], t0["BuyTimestamp"], t0["SellTimestamp"],
            t0["Qty"],        t0["BuyPrice"],      t0["SellPrice"]
        )
        if key in existing_keys:
            continue

        payload = TradeIn(
            instrument      = t0["Instrument"],
            buy_timestamp   = t0["BuyTimestamp"],
            sell_timestamp  = t0["SellTimestamp"],
            buy_price       = t0["BuyPrice"],
            sell_price      = t0["SellPrice"],
            qty             = t0["Qty"]
        )
        _ = add_trade(payload)
        added += 1

    return {"added": added}

@app.get("/analytics/summary")
def analytics_summary():
    return compute_summary_stats(load_trades())

@app.get("/analytics/dashboard")
def analytics_dashboard():
    return compute_dashboard(load_trades())

@app.get("/export/excel")
def export_excel():
    path = export_excel_util(load_trades())
    return FileResponse(path, filename=os.path.basename(path))

@app.get("/export/pdf")
def export_pdf(
    start: Optional[date] = Query(None),
    end:   Optional[date] = Query(None),
):
    filtered = filter_by_date(load_trades(), start, end)
    path     = export_pdf_util(filtered)
    return FileResponse(path, filename=os.path.basename(path))

@app.post("/trades/{idx}/image")
async def attach_image(idx: int, file: UploadFile = File(...)):
    trades = load_trades()
    if idx < 0 or idx >= len(trades):
        raise HTTPException(404, "Trade not found")

    ext  = os.path.splitext(file.filename)[1]
    dest = os.path.join(IMAGE_FOLDER, f"trade_{idx}{ext}")
    with open(dest, "wb") as f:
        f.write(await file.read())

    trades[idx]["image_path"] = dest
    save_trades(trades)
    return {"image_path": dest}

@app.get("/trades/{idx}/image")
def get_image(idx: int):
    trades = load_trades()
    path   = trades[idx].get("image_path")
    if not path or not os.path.exists(path):
        raise HTTPException(404, "No image for this trade")
    return FileResponse(path)
