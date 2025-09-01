import tkinter as tk
from tkinter import simpledialog

def annotate_trade(trade):
    root = tk.Tk()
    root.withdraw()

    instrument = trade.get("Instrument", "Unknown")
    timestamp = trade.get("BuyTimestamp", "Unknown")
    buy_price = float(trade.get("BuyPrice", 0))
    sell_price = float(trade.get("SellPrice", 0))
    qty = trade.get("Qty", 1)

    direction = "Long" if sell_price > buy_price else "Short"

    strategy = simpledialog.askstring(
        "Strategy",
        f"{instrument} @ {timestamp} ({direction}, Qty: {qty})\nSelect strategy:",
        initialvalue="Breakout"
    )

    confidence = simpledialog.askinteger(
        "Confidence",
        f"{instrument} @ {timestamp} ({direction})\nConfidence level (1–5):",
        minvalue=1,
        maxvalue=5
    )

    target_price = simpledialog.askfloat(
        "Target Price",
        f"{instrument} @ {timestamp} ({direction})\nWhat was your target price?"
    )

    stop_loss = simpledialog.askfloat(
        "Stop Loss",
        f"{instrument} @ {timestamp} ({direction})\nWhat was your stop loss price?"
    )

    try:
        risk = abs(buy_price - stop_loss)
        pnl = (sell_price - buy_price) if direction == "Long" else (buy_price - sell_price)
        r_multiple = round(pnl / risk, 2) if risk != 0 else 0.0
    except Exception:
        r_multiple = 0.0

    root.destroy()

    return {
        "Strategy": strategy or "Unspecified",
        "Confidence": confidence if confidence is not None else 0,
        "TargetPrice": target_price if target_price is not None else 0.0,
        "StopLoss": stop_loss if stop_loss is not None else 0.0,
        "Direction": direction,
        "R-Multiple": r_multiple
    }

import tkinter as tk
from tkinter import simpledialog

def annotate_trade(trade):
    root = tk.Tk()
    root.withdraw()

    instrument = trade.get("Instrument", "Unknown")
    timestamp = trade.get("BuyTimestamp", "Unknown")
    buy_price = float(trade.get("BuyPrice", 0))
    sell_price = float(trade.get("SellPrice", 0))
    qty = trade.get("Qty", 1)

    direction = "Long" if sell_price > buy_price else "Short"

    strategy = simpledialog.askstring(
        "Strategy",
        f"{instrument} @ {timestamp} ({direction}, Qty: {qty})\nSelect strategy:",
        initialvalue="Breakout"
    )

    confidence = simpledialog.askinteger(
        "Confidence",
        f"{instrument} @ {timestamp} ({direction})\nConfidence level (1–5):",
        minvalue=1,
        maxvalue=5
    )

    target_price = simpledialog.askfloat(
        "Target Price",
        f"{instrument} @ {timestamp} ({direction})\nWhat was your target price?"
    )

    stop_loss = simpledialog.askfloat(
        "Stop Loss",
        f"{instrument} @ {timestamp} ({direction})\nWhat was your stop loss price?"
    )

    try:
        risk = abs(buy_price - stop_loss)
        pnl = (sell_price - buy_price) if direction == "Long" else (buy_price - sell_price)
        r_multiple = round(pnl / risk, 2) if risk != 0 else 0.0
    except Exception:
        r_multiple = 0.0

    root.destroy()

    return {
        "Strategy": strategy or "Unspecified",
        "Confidence": confidence if confidence is not None else 0,
        "TargetPrice": target_price if target_price is not None else 0.0,
        "StopLoss": stop_loss if stop_loss is not None else 0.0,
        "Direction": direction,
        "R-Multiple": r_multiple
    }

