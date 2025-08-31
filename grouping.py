from datetime import timedelta

def group_trades_by_entry_exit(trades, time_tolerance_sec=20):
    grouped = []
    used = set()

    for i, trade in enumerate(trades):
        if i in used:
            continue

        group = [trade]
        used.add(i)

        for j in range(i + 1, len(trades)):
            if j in used:
                continue

            other = trades[j]
            if (
                trade["Instrument"] == other["Instrument"] and
                trade["BuyPrice"] == other["BuyPrice"] and
                trade["SellPrice"] == other["SellPrice"] and
                timestamps_close(trade["BuyTimestamp"], other["BuyTimestamp"], time_tolerance_sec) and
                timestamps_close(trade["SellTimestamp"], other["SellTimestamp"], time_tolerance_sec)
            ):
                group.append(other)
                used.add(j)

        qty = sum(t["Qty"] for t in group)
        pnl = sum(t["PnL"] for t in group)
        merged = {
            "Instrument": trade["Instrument"],
            "BuyPrice": trade["BuyPrice"],
            "SellPrice": trade["SellPrice"],
            "BuyTimestamp": trade["BuyTimestamp"],
            "SellTimestamp": trade["SellTimestamp"],
            "Qty": qty,
            "PnL": pnl,
            "Duration": trade.get("Duration", ""),
            "GroupedCount": len(group),
            "OriginalTrades": group
        }
        grouped.append(merged)

    return grouped

def timestamps_close(ts1, ts2, tolerance_sec):
    return abs((ts1 - ts2).total_seconds()) <= tolerance_sec
