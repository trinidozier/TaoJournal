from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Trade(BaseModel):
    buy_price: float
    sell_price: float
    stop: float
    direction: str  # "Long" or "Short"

@app.post("/score-trade")
async def score_trade(trade: Trade):
    if trade.direction not in ["Long", "Short"]:
        return {"error": "Direction must be 'Long' or 'Short'"}

    pnl = (trade.sell_price - trade.buy_price) if trade.direction == "Long" else (trade.buy_price - trade.sell_price)
    risk = abs(trade.buy_price - trade.stop)
    r_multiple = round(pnl / risk, 2) if risk else 0.0

    return {
        "PnL": round(pnl, 2),
        "R-Multiple": r_multiple
    }
