from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd

def compute_summary_stats(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not trades:
        return {
            "total_trades": 0,
            "total_pnl": 0,
            "win_rate": 0,
            "avg_r_multiple": 0,
            "long_pnl": 0,
            "short_pnl": 0
        }
    
    total_trades = len(trades)
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    wins = sum(1 for t in trades if t.get("r_multiple", 0) > 0)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    avg_r_multiple = sum(t.get("r_multiple", 0) for t in trades) / total_trades if total_trades > 0 else 0
    long_trades = [t for t in trades if t.get("direction") == "Long"]
    short_trades = [t for t in trades if t.get("direction") == "Short"]
    long_pnl = sum(t.get("pnl", 0) for t in long_trades)
    short_pnl = sum(t.get("pnl", 0) for t in short_trades)
    
    return {
        "total_trades": total_trades,
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 1),
        "avg_r_multiple": round(avg_r_multiple, 2),
        "long_pnl": round(long_pnl, 2),
        "short_pnl": round(short_pnl, 2)
    }

def compute_by_strategy(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_strategy = defaultdict(lambda: {"trades": 0, "pnl": 0, "wins": 0, "avg_r": 0, "avg_risk": 0, "expectancy": 0})
    for t in trades:
        strat = t.get("strategy_id", "No Strategy")
        by_strategy[strat]["trades"] += 1
        by_strategy[strat]["pnl"] += t.get("pnl", 0)
        by_strategy[strat]["avg_risk"] += (t.get("qty", 0) * t.get("buy_price", 0) * 0.01) or 0
        if t.get("r_multiple", 0) > 0:
            by_strategy[strat]["wins"] += 1
    
    for strat, stats in by_strategy.items():
        stats["win_rate"] = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
        stats["avg_r"] = (stats["pnl"] / stats["trades"] / 1000) if stats["trades"] > 0 else 0
        stats["avg_risk"] = (stats["avg_risk"] / stats["trades"]) if stats["trades"] > 0 else 0
        stats["expectancy"] = (stats["win_rate"] / 100 * stats["avg_r"] - (1 - stats["win_rate"] / 100)) if stats["trades"] > 0 else 0
        stats["pnl"] = round(stats["pnl"], 2)
        stats["avg_r"] = round(stats["avg_r"], 2)
        stats["avg_risk"] = round(stats["avg_risk"], 2)
        stats["expectancy"] = round(stats["expectancy"], 2)
        stats["win_rate"] = round(stats["win_rate"], 1)
    
    return dict(by_strategy)

def compute_by_rule(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_rule = defaultdict(lambda: {"trades": 0, "pnl": 0, "wins": 0, "avg_r": 0, "avg_risk": 0, "expectancy": 0})
    for t in trades:
        for ra in t.get("rule_adherence", []):
            key = f"{t.get('strategy_id', 0)}_{ra.get('rule_id', 0)}_{'Followed' if ra.get('followed', False) else 'Broken'}"
            by_rule[key]["trades"] += 1
            by_rule[key]["pnl"] += t.get("pnl", 0)
            by_rule[key]["avg_risk"] += (t.get("qty", 0) * t.get("buy_price", 0) * 0.01) or 0
            if t.get("r_multiple", 0) > 0:
                by_rule[key]["wins"] += 1
    
    for key, stats in by_rule.items():
        stats["win_rate"] = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
        stats["avg_r"] = (stats["pnl"] / stats["trades"] / 1000) if stats["trades"] > 0 else 0
        stats["avg_risk"] = (stats["avg_risk"] / stats["trades"]) if stats["trades"] > 0 else 0
        stats["expectancy"] = (stats["win_rate"] / 100 * stats["avg_r"] - (1 - stats["win_rate"] / 100)) if stats["trades"] > 0 else 0
        stats["pnl"] = round(stats["pnl"], 2)
        stats["avg_r"] = round(stats["avg_r"], 2)
        stats["avg_risk"] = round(stats["avg_risk"], 2)
        stats["expectancy"] = round(stats["expectancy"], 2)
        stats["win_rate"] = round(stats["win_rate"], 1)
    
    return dict(by_rule)

def compute_by_trade_type(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_type = defaultdict(lambda: {"trades": 0, "pnl": 0, "wins": 0, "avg_r": 0, "avg_risk": 0, "expectancy": 0})
    for t in trades:
        t_type = t.get("trade_type", "Other")
        by_type[t_type]["trades"] += 1
        by_type[t_type]["pnl"] += t.get("pnl", 0)
        by_type[t_type]["avg_risk"] += (t.get("qty", 0) * t.get("buy_price", 0) * 0.01) or 0
        if t.get("r_multiple", 0) > 0:
            by_type[t_type]["wins"] += 1
    
    for t_type, stats in by_type.items():
        stats["win_rate"] = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
        stats["avg_r"] = (stats["pnl"] / stats["trades"] / 1000) if stats["trades"] > 0 else 0
        stats["avg_risk"] = (stats["avg_risk"] / stats["trades"]) if stats["trades"] > 0 else 0
        stats["expectancy"] = (stats["win_rate"] / 100 * stats["avg_r"] - (1 - stats["win_rate"] / 100)) if stats["trades"] > 0 else 0
        stats["pnl"] = round(stats["pnl"], 2)
        stats["avg_r"] = round(stats["avg_r"], 2)
        stats["avg_risk"] = round(stats["avg_risk"], 2)
        stats["expectancy"] = round(stats["expectancy"], 2)
        stats["win_rate"] = round(stats["win_rate"], 1)
    
    return dict(by_type)

def compute_by_hour(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_hour = defaultdict(lambda: {"trades": 0, "pnl": 0, "wins": 0, "win_rate": 0, "avg_r": 0})
    for t in trades:
        hour = datetime.fromisoformat(t.get("buy_timestamp")).hour
        by_hour[hour]["trades"] += 1
        by_hour[hour]["pnl"] += t.get("pnl", 0)
        if t.get("r_multiple", 0) > 0:
            by_hour[hour]["wins"] += 1
    
    for hour, stats in by_hour.items():
        stats["win_rate"] = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
        stats["avg_r"] = (stats["pnl"] / stats["trades"] / 1000) if stats["trades"] > 0 else 0
        stats["pnl"] = round(stats["pnl"], 2)
        stats["avg_r"] = round(stats["avg_r"], 2)
        stats["win_rate"] = round(stats["win_rate"], 1)
    
    return dict(by_hour)

def compute_by_day_of_week(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_day = defaultdict(lambda: {"trades": 0, "pnl": 0, "wins": 0, "win_rate": 0, "avg_r": 0})
    for t in trades:
        day = datetime.fromisoformat(t.get("buy_timestamp")).weekday()
        by_day[day]["trades"] += 1
        by_day[day]["pnl"] += t.get("pnl", 0)
        if t.get("r_multiple", 0) > 0:
            by_day[day]["wins"] += 1
    
    for day, stats in by_day.items():
        stats["win_rate"] = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
        stats["avg_r"] = (stats["pnl"] / stats["trades"] / 1000) if stats["trades"] > 0 else 0
        stats["pnl"] = round(stats["pnl"], 2)
        stats["avg_r"] = round(stats["avg_r"], 2)
        stats["win_rate"] = round(stats["win_rate"], 1)
    
    return dict(by_day)

def compute_risk_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not trades:
        return {
            "max_drawdown": 0,
            "sharpe_ratio": 0,
            "avg_risk_reward": 0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0
        }
    
    pnls = [t.get("pnl", 0) for t in trades]
    sorted_pnl = sorted(pnls)
    max_drawdown = 0
    if len(sorted_pnl) > 1:
        peak = sorted_pnl[0]
        for i, pnl in enumerate(sorted_pnl[:-1]):
            peak = max(peak, sorted_pnl[i])
            drawdown = pnl - peak
            max_drawdown = min(max_drawdown, drawdown)
    
    total_pnl = sum(pnls)
    sharpe_ratio = total_pnl / (len(trades) ** 0.5) if trades else 0
    risk_rewards = [
        ((t.get("target", 0) - t.get("buy_price", 0)) / (t.get("buy_price", 0) - t.get("stop", 0)))
        for t in trades if t.get("buy_price", 0) and t.get("stop", 0) and t.get("buy_price", 0) != t.get("stop", 0)
    ]
    avg_risk_reward = sum(risk_rewards) / len(risk_rewards) if risk_rewards else 0
    
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_wins = 0
    current_losses = 0
    
    for t in trades:
        if t.get("r_multiple", 0) > 0:
            current_wins += 1
            current_losses = 0
            max_consecutive_wins = max(max_consecutive_wins, current_wins)
        else:
            current_losses += 1
            current_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, current_losses)
    
    return {
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "avg_risk_reward": round(avg_risk_reward, 2),
        "max_consecutive_wins": max_consecutive_wins,
        "max_consecutive_losses": max_consecutive_losses
    }

def compute_behavioral_insights(trades: List[Dict[str, Any]]) -> Dict[str, str]:
    if not trades:
        return {
            "overconfidence": "",
            "rule_break_impact": ""
        }
    
    high_confidence = [t for t in trades if t.get("confidence", 0) > 3]
    low_confidence = [t for t in trades if t.get("confidence", 0) <= 3]
    high_conf_win_rate = (sum(1 for t in high_confidence if t.get("r_multiple", 0) > 0) / len(high_confidence) * 100) if high_confidence else 0
    low_conf_win_rate = (sum(1 for t in low_confidence if t.get("r_multiple", 0) > 0) / len(low_confidence) * 100) if low_confidence else 0
    overconfidence = (
        f"Potential overconfidence: High confidence trades win {high_conf_win_rate:.1f}% vs. low: {low_conf_win_rate:.1f}%"
        if high_conf_win_rate < low_conf_win_rate else ""
    )
    
    broken_rules = [t for t in trades if any(not ra.get("followed", True) for ra in t.get("rule_adherence", []))]
    followed_rules = [t for t in trades if all(ra.get("followed", True) for ra in t.get("rule_adherence", []))]
    broken_win_rate = (sum(1 for t in broken_rules if t.get("r_multiple", 0) > 0) / len(broken_rules) * 100) if broken_rules else 0
    followed_win_rate = (sum(1 for t in followed_rules if t.get("r_multiple", 0) > 0) / len(followed_rules) * 100) if followed_rules else 0
    rule_break_impact = f"Win rate when rules broken: {broken_win_rate:.1f}% vs. followed: {followed_win_rate:.1f}%"
    
    return {
        "overconfidence": overconfidence,
        "rule_break_impact": rule_break_impact
    }

def compute_equity_curve(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sorted_trades = sorted(trades, key=lambda t: t.get('buy_timestamp', ''))
    curve = []
    cumulative_pnl = 0
    for t in sorted_trades:
        cumulative_pnl += t.get('pnl', 0)
        curve.append({
            'date': t.get('buy_timestamp', '')[:10],
            'pnl': round(cumulative_pnl, 2)
        })
    return curve

def compute_heatmap_hour(trades: List[Dict[str, Any]]) -> Dict[int, float]:
    heatmap = defaultdict(float)
    for t in trades:
        try:
            hour = datetime.fromisoformat(t.get('buy_timestamp')).hour
            heatmap[hour] += t.get('pnl', 0)
        except ValueError:
            continue
    return {k: round(v, 2) for k, v in heatmap.items()}

def compute_heatmap_day(trades: List[Dict[str, Any]]) -> Dict[int, float]:
    heatmap = defaultdict(float)
    for t in trades:
        try:
            day = datetime.fromisoformat(t.get('buy_timestamp')).weekday()
            heatmap[day] += t.get('pnl', 0)
        except ValueError:
            continue
    return {k: round(v, 2) for k, v in heatmap.items()}