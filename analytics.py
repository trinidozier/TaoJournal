import logging
from collections import defaultdict

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
