import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

from db import database, trades, engine, metadata

# Ensure tables exist (swap for Alembic in production)
metadata.create_all(engine)

app = FastAPI()


class TradeRequest(BaseModel):
    buy_price: float
    sell_price: float
    stop: float
    direction: str  # "Long" or "Short"


@app.on_event("startup")
async def connect_db():
    await database.connect()


@app.on_event("shutdown")
async def disconnect_db():
    await database.disconnect()


@app.post("/score-trade")
async def score_trade(req: TradeRequest):
    if req.direction not in ["Long", "Short"]:
        raise HTTPException(status_code=400, detail="Direction must be 'Long' or 'Short'")

    # Calculate risk, PnL, and R-multiple
    risk = abs(req.buy_price - req.stop)
    if risk == 0:
        raise HTTPException(status_code=400, detail="Risk cannot be zero")

    pnl = (
        req.sell_price - req.buy_price
        if req.direction == "Long"
        else req.buy_price - req.sell_price
    )
    r_multiple = round(pnl / risk, 2)

    # Persist with a timestamp
    query = trades.insert().values(
        buy_price=req.buy_price,
        sell_price=req.sell_price,
        stop=req.stop,
        direction=req.direction,
        pnl=round(pnl, 2),
        r_multiple=r_multiple,
        timestamp=datetime.utcnow()      # ← include UTC timestamp
    )
    record_id = await database.execute(query)

    return {
        "id": record_id,
        "PnL": round(pnl, 2),
        "R-Multiple": r_multiple
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
