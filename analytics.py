import logging
from collections import defaultdict
from datetime import datetime
import statistics  # For stdev in Sharpe
import numpy as np  # For drawdown, etc.

def show_summary_stats(trades, total_pnl=0.0):
    long_trades = [t for t in trades if t.get("Direction") == "Long"]
    short_trades = [t for t in trades if t.get("Direction") == "Short"]

    long_stats = calculate_group_stats(long_trades)
    short_stats = calculate_group_stats(short_trades)

    summary = format_summary("Long", long_stats) + "\n\n" + format_summary("Short", short_stats)
    summary += f"\n\n💰 Total P&L: ${round(total_pnl, 2)}"

    summary += "\n\n📊 Breakdown by Confidence:\n" + format_breakdown(breakdown_by_confidence(trades))
    summary += "\n\n📊 Breakdown by Instrument:\n" + format_breakdown(breakdown_by_instrument(trades))

    logging.info("Trade Summary Stats:\n" + summary)
    return summary  # Now usable in API responses or CLI

def calculate_group_stats(group):
    count = len(group)
    total_r = sum(t.get("R-Multiple", 0) for t in group)
    wins = sum(1 for t in group if t.get("R-Multiple", 0) > 0)
    avg_r = round(total_r / count, 2) if count else 0
    win_rate = round(100 * wins / count, 1) if count else 0
    return {
        "count": count,
        "avg_r": avg_r,
        "win_rate": win_rate
    }

def format_summary(label, stats):
    return (
        f"📊 {label} Trades: {stats['count']}\n"
        f"   Avg R-Multiple: {stats['avg_r']}\n"
        f"   Win Rate: {stats['win_rate']}%"
    )

def breakdown_by_confidence(trades):
    groups = defaultdict(list)
    for t in trades:
        groups[t.get("Confidence", 0)].append(t)
    return summarize_groups(groups)

def breakdown_by_instrument(trades):
    groups = defaultdict(list)
    for t in trades:
        groups[t.get("Instrument", "Unknown")].append(t)
    return summarize_groups(groups)

def summarize_groups(groups):
    summary = {}
    for key, group in groups.items():
        total_r = sum(t.get("R-Multiple", 0) for t in group)
        total_pnl = sum(t.get("PnL", 0) for t in group)
        count = len(group)
        avg_r = round(total_r / count, 2) if count else 0
        summary[key] = {
            "count": count,
            "avg_r": avg_r,
            "total_pnl": round(total_pnl, 2)
        }
    return summary

def format_breakdown(breakdown):
    lines = []
    for key, stats in sorted(breakdown.items()):
        lines.append(
            f"• {key}: {stats['count']} trades | Avg R: {stats['avg_r']} | P&L: ${stats['total_pnl']}"
        )
    return "\n".join(lines)

# Aliases for FastAPI integration
compute_summary_stats = show_summary_stats

# New functions for analytics endpoint
def compute_by_strategy(trades):
    groups = defaultdict(list)
    for t in trades:
        strat = t.get('strategy_id', 'No Strategy')
        groups[strat].append(t)
    return {
        k: {
            'trades': len(v),
            'pnl': sum(t.get('pnl', 0) for t in v),
            'win_rate': round(100 * sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v), 1) if v else 0,
            'avg_r': round(sum(t.get('r_multiple', 0) for t in v) / len(v), 2) if v else 0,
            'avg_risk': round(sum(t.get('qty', 0) * t.get('buy_price', 0) * 0.01 for t in v) / len(v), 2) if v else 0,  # Assume 1% risk
            'expectancy': round((sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v)) * (sum(t.get('r_multiple', 0) for t in v if t.get('r_multiple', 0) > 0) / sum(1 for t in v if t.get('r_multiple', 0) > 0)) - (1 - sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v)), 2) if v else 0
        } for k, v in groups.items()
    }

def compute_by_rule(trades):
    groups = defaultdict(list)
    for t in trades:
        for ra in t.get('rule_adherence', []):
            key = f"Rule{ra['rule_id']}_{'Followed' if ra['followed'] else 'Broken'}"
            groups[key].append(t)
    return {
        k: {
            'trades': len(v),
            'pnl': sum(t.get('pnl', 0) for t in v),
            'win_rate': round(100 * sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v), 1) if v else 0,
            'avg_r': round(sum(t.get('r_multiple', 0) for t in v) / len(v), 2) if v else 0,
            'avg_risk': round(sum(t.get('qty', 0) * t.get('buy_price', 0) * 0.01 for t in v) / len(v), 2) if v else 0,
            'expectancy': round((sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v)) * (sum(t.get('r_multiple', 0) for t in v if t.get('r_multiple', 0) > 0) / sum(1 for t in v if t.get('r_multiple', 0) > 0)) - (1 - sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v)), 2) if v else 0
        } for k, v in groups.items()
    }

def compute_by_trade_type(trades):
    groups = defaultdict(list)
    for t in trades:
        typ = t.get('trade_type', 'Other')
        groups[typ].append(t)
    return {
        k: {
            'trades': len(v),
            'pnl': sum(t.get('pnl', 0) for t in v),
            'win_rate': round(100 * sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v), 1) if v else 0,
            'avg_r': round(sum(t.get('r_multiple', 0) for t in v) / len(v), 2) if v else 0,
            'avg_risk': round(sum(t.get('qty', 0) * t.get('buy_price', 0) * 0.01 for t in v) / len(v), 2) if v else 0,
            'expectancy': round((sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v)) * (sum(t.get('r_multiple', 0) for t in v if t.get('r_multiple', 0) > 0) / sum(1 for t in v if t.get('r_multiple', 0) > 0)) - (1 - sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v)), 2) if v else 0
        } for k, v in groups.items()
    }

def compute_by_hour(trades):
    groups = defaultdict(list)
    for t in trades:
        hour = datetime.fromisoformat(t['buy_timestamp']).hour
        groups[hour].append(t)
    return {
        k: {
            'trades': len(v),
            'pnl': sum(t.get('pnl', 0) for t in v),
            'win_rate': round(100 * sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v), 1) if v else 0,
            'avg_r': round(sum(t.get('r_multiple', 0) for t in v) / len(v), 2) if v else 0
        } for k, v in groups.items()
    }

def compute_by_day_of_week(trades):
    groups = defaultdict(list)
    for t in trades:
        day = datetime.fromisoformat(t['buy_timestamp']).weekday()
        groups[day].append(t)
    return {
        k: {
            'trades': len(v),
            'pnl': sum(t.get('pnl', 0) for t in v),
            'win_rate': round(100 * sum(1 for t in v if t.get('r_multiple', 0) > 0) / len(v), 1) if v else 0,
            'avg_r': round(sum(t.get('r_multiple', 0) for t in v) / len(v), 2) if v else 0
        } for k, v in groups.items()
    }

def compute_risk_metrics(trades):
    pnls = [t.get('pnl', 0) for t in trades]
    if not pnls:
        return {'max_drawdown': 0, 'sharpe': 0, 'avg_risk_reward': 0, 'max_consecutive_wins': 0, 'max_consecutive_losses': 0}
    cumulative = np.cumsum(pnls)
    max_drawdown = np.max(np.maximum.accumulate(cumulative) - cumulative)
    returns = np.diff(cumulative, prepend=0) / 1  # Simplified returns
    sharpe = np.mean(returns) / np.std(returns) if np.std(returns) != 0 else 0
    avg_risk_reward = sum((t.get('target', 0) - t.get('buy_price', 0)) / (t.get('buy_price', 0) - t.get('stop', 0)) for t in trades if t.get('stop') != t.get('buy_price')) / len(trades) if trades else 0
    max_wins = max_losses = current_wins = current_losses = 0
    for t in trades:
        if t.get('r_multiple', 0) > 0:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        else:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)
    return {
        'max_drawdown': round(max_drawdown, 2),
        'sharpe': round(sharpe, 2),
        'avg_risk_reward': round(avg_risk_reward, 2),
        'max_consecutive_wins': max_wins,
        'max_consecutive_losses': max_losses
    }

def compute_behavioral_insights(trades):
    high_conf = [t for t in trades if t.get('confidence', 0) > 3]
    low_conf = [t for t in trades if t.get('confidence', 0) <= 3]
    high_win_rate = round(100 * sum(1 for t in high_conf if t.get('r_multiple', 0) > 0) / len(high_conf), 1) if high_conf else 0
    low_win_rate = round(100 * sum(1 for t in low_conf if t.get('r_multiple', 0) > 0) / len(low_conf), 1) if low_conf else 0
    overconfidence = 'Potential overconfidence: High confidence trades win ' + str(high_win_rate) + '% vs. low: ' + str(low_win_rate) + '%' if high_win_rate < low_win_rate else ''
    rule_break = [t for t in trades if any(not ra['followed'] for ra in t.get('rule_adherence', []))]
    rule_follow = [t for t in trades if all(ra['followed'] for ra in t.get('rule_adherence', []))]
    break_win_rate = round(100 * sum(1 for t in rule_break if t.get('r_multiple', 0) > 0) / len(rule_break), 1) if rule_break else 0
    follow_win_rate = round(100 * sum(1 for t in rule_follow if t.get('r_multiple', 0) > 0) / len(rule_follow), 1) if rule_follow else 0
    rule_impact = 'Rule break impact: Win rate when broken: ' + str(break_win_rate) + '% vs. followed: ' + str(follow_win_rate) + '%'
    return {
        'overconfidence': overconfidence,
        'ruleBreakImpact': rule_impact,
    }