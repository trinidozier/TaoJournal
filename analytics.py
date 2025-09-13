# analytics.py — Backend analytics functions matching the React Analytics.jsx logic

from collections import defaultdict
from datetime import datetime
import math

def compute_summary_stats(trades):
    """Compute overall summary stats."""
    if not trades:
        return {
            "totalTrades": 0,
            "totalPnl": 0,
            "winRate": 0,
            "avgR": 0,
            "longPnl": 0,
            "shortPnl": 0
        }

    total_trades = len(trades)
    total_pnl = sum(t.get("pnl", 0) or 0 for t in trades)
    wins = sum(1 for t in trades if (t.get("r_multiple") or 0) > 0)
    win_rate = round((wins / total_trades) * 100, 1)
    avg_r = round(sum(t.get("r_multiple") or 0 for t in trades) / total_trades, 2)

    longs = [t for t in trades if t.get("direction") == "Long"]
    shorts = [t for t in trades if t.get("direction") == "Short"]
    long_pnl = sum(t.get("pnl", 0) or 0 for t in longs)
    short_pnl = sum(t.get("pnl", 0) or 0 for t in shorts)

    return {
        "totalTrades": total_trades,
        "totalPnl": total_pnl,
        "winRate": win_rate,
        "avgR": avg_r,
        "longPnl": long_pnl,
        "shortPnl": short_pnl
    }


def compute_by_strategy(trades):
    """Group trades by strategy."""
    result = {}
    for t in trades:
        strat_name = t.get("strategy_name") or "No Strategy"
        if strat_name not in result:
            result[strat_name] = {"trades": 0, "pnl": 0, "wins": 0}
        result[strat_name]["trades"] += 1
        result[strat_name]["pnl"] += t.get("pnl", 0) or 0
        if (t.get("r_multiple") or 0) > 0:
            result[strat_name]["wins"] += 1
    return result


def compute_by_rule(trades):
    """Group trades by rule adherence."""
    result = {}
    for t in trades:
        for ra in t.get("rule_adherence", []):
            key = f"{t.get('strategy_id')}_{ra.get('rule_id')}_{'Followed' if ra.get('followed') else 'Broken'}"
            if key not in result:
                result[key] = {"trades": 0, "pnl": 0, "wins": 0}
            result[key]["trades"] += 1
            result[key]["pnl"] += t.get("pnl", 0) or 0
            if (t.get("r_multiple") or 0) > 0:
                result[key]["wins"] += 1
    return result


def compute_by_trade_type(trades):
    """Group trades by trade type."""
    result = {}
    for t in trades:
        trade_type = t.get("trade_type") or "Other"
        if trade_type not in result:
            result[trade_type] = {"trades": 0, "pnl": 0, "wins": 0}
        result[trade_type]["trades"] += 1
        result[trade_type]["pnl"] += t.get("pnl", 0) or 0
        if (t.get("r_multiple") or 0) > 0:
            result[trade_type]["wins"] += 1
    return result


def compute_by_hour(trades):
    """Group trades by buy hour."""
    result = {}
    for t in trades:
        ts = t.get("buy_timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except Exception:
                continue
        if not isinstance(ts, datetime):
            continue
        hour = ts.hour
        if hour not in result:
            result[hour] = {"trades": 0, "pnl": 0, "wins": 0}
        result[hour]["trades"] += 1
        result[hour]["pnl"] += t.get("pnl", 0) or 0
        if (t.get("r_multiple") or 0) > 0:
            result[hour]["wins"] += 1
    return result


def compute_by_day_of_week(trades):
    """Group trades by day of week (0=Monday)."""
    result = {}
    for t in trades:
        ts = t.get("buy_timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except Exception:
                continue
        if not isinstance(ts, datetime):
            continue
        day = ts.weekday()
        if day not in result:
            result[day] = {"trades": 0, "pnl": 0, "wins": 0}
        result[day]["trades"] += 1
        result[day]["pnl"] += t.get("pnl", 0) or 0
        if (t.get("r_multiple") or 0) > 0:
            result[day]["wins"] += 1
    return result


def compute_risk_metrics(trades):
    """Compute simplified risk metrics."""
    if not trades:
        return {"maxDrawdown": 0, "sharpe": 0}

    pnls = [t.get("pnl", 0) or 0 for t in trades]
    sorted_pnls = sorted(pnls)
    max_drawdown = 0
    for i in range(len(sorted_pnls) - 1):
        peak = max(sorted_pnls[:i+1])
        dd = sorted_pnls[i] - peak
        if dd < max_drawdown:
            max_drawdown = dd

    total_pnl = sum(pnls)
    sharpe = total_pnl / math.sqrt(len(trades)) if trades else 0

    return {"maxDrawdown": max_drawdown, "sharpe": sharpe}


def compute_behavioral_insights(trades):
    """Placeholder for behavioral insights logic."""
    return {}
