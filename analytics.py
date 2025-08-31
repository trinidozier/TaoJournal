from tkinter import messagebox
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

    messagebox.showinfo("Trade Summary Stats", summary)

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
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def show_dashboard(trades):
    from tkinter import Toplevel

    root = Toplevel()
    root.title("📊 Tao Trader Dashboard")
    root.geometry("1000x600")

    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    fig.tight_layout(pad=4)

    # Confidence P&L
    conf_data = breakdown_by_confidence(trades)
    conf_keys = sorted(conf_data.keys())
    conf_pnl = [conf_data[k]["total_pnl"] for k in conf_keys]

    axs[0].bar(conf_keys, conf_pnl, color="#4caf50")
    axs[0].set_title("Total P&L by Confidence")
    axs[0].set_xlabel("Confidence Level")
    axs[0].set_ylabel("P&L ($)")

    # Instrument Avg R
    instr_data = breakdown_by_instrument(trades)
    instr_keys = sorted(instr_data.keys())
    instr_avg_r = [instr_data[k]["avg_r"] for k in instr_keys]

    axs[1].bar(instr_keys, instr_avg_r, color="#2196f3")
    axs[1].set_title("Avg R-Multiple by Instrument")
    axs[1].set_xlabel("Instrument")
    axs[1].set_ylabel("Avg R")

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack()

    # Summary stats
    total_trades = len(trades)
    total_pnl = sum(t.get("PnL", 0) for t in trades)
    win_rate = round(100 * sum(1 for t in trades if t.get("R-Multiple", 0) > 0) / total_trades, 1) if total_trades else 0

    summary = (
        f"📈 Total Trades: {total_trades}\n"
        f"💰 Total P&L: ${round(total_pnl, 2)}\n"
        f"✅ Win Rate: {win_rate}%"
    )

    tk.Label(root, text=summary, font=("Arial", 12), justify="left").pack(pady=10)
