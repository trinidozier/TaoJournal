# journal.py — updated with manual add/delete and robust data protection

import os
import json
import shutil
import datetime
import tempfile
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import datetime
from tkcalendar import DateEntry


from analytics import show_dashboard, show_summary_stats
from import_trades import parse_tradovate_csv
from grouping import group_trades_by_entry_exit
from export_tools import export_to_excel, export_to_pdf

# Configuration for backups
BACKUP_DIR = "backups"
MAX_BACKUPS = 10


def atomic_write_json(path, data):
    """
    Atomically write `data` to JSON file at `path`,
    using a temp file + fsync + os.replace to avoid half-written files.
    """
    dirpath = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dirpath, text=True)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, default=str, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        os.remove(tmp_path)
        raise


def rotate_backups(src_path):
    """
    Copy existing JSON at `src_path` into BACKUP_DIR with timestamp,
    then prune oldest backups beyond MAX_BACKUPS.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_name = f"trades-{timestamp}.json"
    dst = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(src_path, dst)

    # Prune oldest backups
    backups = sorted(os.listdir(BACKUP_DIR))
    while len(backups) > MAX_BACKUPS:
        old = backups.pop(0)
        os.remove(os.path.join(BACKUP_DIR, old))


class JournalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tao Trader Journal")

        self.save_file = "annotated_trades.json"
        self.image_folder = "trade_images"
        os.makedirs(self.image_folder, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)

        self.annotated_trades = []
        self.load_saved_trades()

        columns = (
            "Instrument", "Timestamp", "Direction", "Qty", "Strategy", "Confidence",
            "Target", "Stop", "R-Multiple", "PnL", "Notes", "Goals", "Preparedness",
            "What I Learned", "Changes Needed"
        )
        self.tree = ttk.Treeview(root, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        for wide_col in ("Notes", "Goals", "Preparedness", "What I Learned", "Changes Needed"):
            self.tree.column(wide_col, width=300)
        self.tree.pack(pady=10)

        self.tree.bind("<Double-1>", self.edit_cell)
        self.tree.tag_configure("long", background="#e0ffe0")
        self.tree.tag_configure("short", background="#ffe0e0")

        btns = [
            ("📥 Import CSV", self.import_csv),
            ("➕ Add Trade", self.add_trade),
            ("🗑️ Delete Trade", self.delete_trade),
            ("📊 Summary Stats", self.show_stats),
            ("📤 Export to Excel", self.export_excel),
            ("📄 Export to PDF", self.export_pdf),
            ("📊 Dashboard", self.show_dashboard),
            ("🖼️ Review Image", self.review_image),
        ]
        frame = tk.Frame(root)
        frame.pack(pady=10)
        for i, (txt, cmd) in enumerate(btns):
            tk.Button(frame, text=txt, command=cmd).grid(row=0, column=i, padx=5)

        self.refresh_tree()
        self.show_eula()

    def load_saved_trades(self):
        """
        Load trades JSON, recover from latest backup if file is corrupted.
        """
        if not os.path.exists(self.save_file):
            self.annotated_trades = []
            return

        try:
            with open(self.save_file, "r") as f:
                self.annotated_trades = json.load(f)
        except json.JSONDecodeError:
            resp = messagebox.askyesno(
                "Data Corrupted",
                "Your trades file looks corrupted. Restore from the latest backup?"
            )
            if resp:
                backups = sorted(os.listdir(BACKUP_DIR))
                if not backups:
                    messagebox.showerror("No Backups", "No backups available to restore.")
                    self.annotated_trades = []
                    return

                latest = backups[-1]
                backup_path = os.path.join(BACKUP_DIR, latest)
                with open(backup_path, "r") as bf:
                    data = json.load(bf)
                # overwrite corrupted file atomically and load
                atomic_write_json(self.save_file, data)
                self.annotated_trades = data
            else:
                self.annotated_trades = []
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load trades:\n{e}")
            self.annotated_trades = []

    def save_trades(self):
        """
        Before writing fresh data, rotate current file into backups,
        then perform an atomic write.
        """
        try:
            if os.path.exists(self.save_file):
                rotate_backups(self.save_file)
            atomic_write_json(self.save_file, self.annotated_trades)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save trades:\n{e}")

    def show_eula(self):
        eula = (
            "Tao Trader Journal is provided as-is for personal use.\n"
            "By using this software, you agree to take full responsibility for your trading decisions.\n"
            "No warranties or guarantees are provided.\n\n"
            "Do not distribute or modify without permission from Tao Trader LLC."
        )
        messagebox.showinfo("End User License Agreement", eula)

    def import_csv(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt")]
        )
        if not file_path:
            return

        raw = parse_tradovate_csv(file_path)
        grouped = group_trades_by_entry_exit(raw)

        existing = {
            (
                t.get("Instrument"), t.get("BuyTimestamp"), t.get("SellTimestamp"),
                t.get("Qty"), t.get("BuyPrice"), t.get("SellPrice")
            )
            for t in self.annotated_trades
        }

        added = 0
        for trade in grouped:
            key = (
                trade.get("Instrument"), trade.get("BuyTimestamp"),
                trade.get("SellTimestamp"), trade.get("Qty"),
                trade.get("BuyPrice"), trade.get("SellPrice")
            )
            if key in existing:
                continue

            direction = "Long" if trade["SellPrice"] > trade["BuyPrice"] else "Short"
            trade.update({
                "Direction": direction,
                "Strategy": "",
                "Confidence": 0,
                "Target": 0.0,
                "Stop": 0.0,
                "R-Multiple": 0.0,
                "PnL": round(trade["PnL"], 2),
                "Notes": "",
                "Goals": "",
                "Preparedness": "",
                "What I Learned": "",
                "Changes Needed": "",
                "ImagePath": ""
            })
            self.annotated_trades.append(trade)
            added += 1

        msg = (
            "No new trades were added (all were duplicates)."
            if added == 0 else f"{added} new trades added."
        )
        messagebox.showinfo("Import Complete", msg)
        self.save_trades()
        self.refresh_tree()

    def add_trade(self):
        instrument = simpledialog.askstring("Instrument", "Enter instrument symbol:")
        if not instrument:
            return

        buy_ts_str = simpledialog.askstring("Buy Timestamp", "Enter buy datetime (YYYY-MM-DD HH:MM:SS):")
        sell_ts_str = simpledialog.askstring("Sell Timestamp", "Enter sell datetime (YYYY-MM-DD HH:MM:SS):")
        try:
            buy_ts = datetime.datetime.strptime(buy_ts_str, "%Y-%m-%d %H:%M:%S")
            sell_ts = datetime.datetime.strptime(sell_ts_str, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            messagebox.showerror("Parse Error", f"Invalid timestamp:\n{e}")
            return

        buy_price = simpledialog.askfloat("Buy Price", "Enter buy price:")
        sell_price = simpledialog.askfloat("Sell Price", "Enter sell price:")
        qty = simpledialog.askinteger("Quantity", "Enter quantity:")
        if None in (buy_price, sell_price, qty):
            return

        direction = "Long" if sell_price > buy_price else "Short"
        strategy = simpledialog.askstring("Strategy", "Enter strategy name:", initialvalue="")
        confidence = simpledialog.askinteger("Confidence", "Confidence level (1–5):", minvalue=1, maxvalue=5)
        target = simpledialog.askfloat("Target Price", "Enter target price:")
        stop = simpledialog.askfloat("Stop Loss", "Enter stop loss price:")

        pnl = (sell_price - buy_price) if direction == "Long" else (buy_price - sell_price)
        risk = abs(buy_price - stop) if stop is not None else 0
        r_mult = round(pnl / risk, 2) if risk else 0.0

        trade = {
            "Instrument": instrument,
            "BuyTimestamp": buy_ts,
            "SellTimestamp": sell_ts,
            "BuyPrice": buy_price,
            "SellPrice": sell_price,
            "Qty": qty,
            "Direction": direction,
            "Strategy": strategy or "",
            "Confidence": confidence or 0,
            "Target": target or 0.0,
            "Stop": stop or 0.0,
            "R-Multiple": r_mult,
            "PnL": round(pnl, 2),
            "Notes": "",
            "Goals": "",
            "Preparedness": "",
            "What I Learned": "",
            "Changes Needed": "",
            "ImagePath": ""
        }

        self.annotated_trades.append(trade)
        self.save_trades()
        self.refresh_tree()

    def delete_trade(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("No Trade Selected", "Please select a trade first.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected trade?"):
            return

        idx = int(selected)
        self.annotated_trades.pop(idx)
        self.save_trades()
        self.refresh_tree()

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, trade in enumerate(self.annotated_trades):
            tag = "long" if trade["Direction"] == "Long" else "short"
            ts = trade.get("BuyTimestamp")
            if isinstance(ts, datetime.datetime):
                ts = ts.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(ts, str):
                ts = ts[:19]
            self.tree.insert(
                "", "end", iid=str(i), tags=(tag,),
                values=(
                    trade["Instrument"],
                    ts,
                    trade["Direction"],
                    trade["Qty"],
                    trade["Strategy"],
                    trade["Confidence"],
                    trade["Target"],
                    trade["Stop"],
                    trade["R-Multiple"],
                    trade["PnL"],
                    trade.get("Notes", ""),
                    trade.get("Goals", ""),
                    trade.get("Preparedness", ""),
                    trade.get("What I Learned", ""),
                    trade.get("Changes Needed", "")
                )
            )

    def edit_cell(self, event):
        selected = self.tree.focus()
        if not selected:
            return

        col = self.tree.identify_column(event.x)
        idx = int(col.replace("#", "")) - 1
        field = self.tree["columns"][idx]
        trade = self.annotated_trades[int(selected)]
        old = trade.get(field, "")

        new = simpledialog.askstring("Edit", f"{field}:", initialvalue=str(old))
        if new is None:
            return

        try:
            if field in ("Confidence", "Qty"):
                trade[field] = int(new)
            elif field in ("BuyPrice", "SellPrice", "Stop", "Target", "PnL", "R-Multiple"):
                trade[field] = float(new)
            else:
                trade[field] = new

            # Recompute only when price, stop, or PnL change
            if field in ("BuyPrice", "SellPrice"):
                entry = float(trade["BuyPrice"])
                exitp = float(trade["SellPrice"])
                direction = trade["Direction"]
                pnl = (exitp - entry) if direction == "Long" else (entry - exitp)
                trade["PnL"] = round(pnl, 2)

                stop = float(trade.get("Stop", 0))
                risk = abs(entry - stop)
                trade["R-Multiple"] = round(pnl / risk, 2) if risk else 0.0

            elif field == "Stop":
                entry = float(trade["BuyPrice"])
                pnl   = float(trade.get("PnL", 0))
                stop  = float(trade["Stop"])
                risk  = abs(entry - stop)
                trade["R-Multiple"] = round(pnl / risk, 2) if risk else 0.0

            elif field == "PnL":
                entry = float(trade["BuyPrice"])
                stop  = float(trade.get("Stop", 0))
                pnl   = float(trade["PnL"])
                risk  = abs(entry - stop)
                trade["R-Multiple"] = round(pnl / risk, 2) if risk else 0.0

            self.save_trades()
            self.refresh_tree()

        except Exception as e:
            messagebox.showerror("Error", f"Invalid input:\n{e}")

    def review_image(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("No Trade Selected", "Please select a trade first.")
            return

        trade = self.annotated_trades[int(selected)]
        current = trade.get("ImagePath", "")
        if current and os.path.exists(current):
            try:
                os.startfile(current)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open image:\n{e}")
        else:
            file_path = filedialog.askopenfilename(
                filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")]
            )
            if not file_path:
                return
            ext = os.path.splitext(file_path)[1]
            dest = os.path.join(self.image_folder, f"trade_{selected}{ext}")
            try:
                shutil.copy(file_path, dest)
                trade["ImagePath"] = dest
                self.save_trades()
                messagebox.showinfo("Image Saved", "Image successfully attached to trade.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image:\n{e}")

    def show_stats(self):
        if not self.annotated_trades:
            messagebox.showwarning("No Trades", "Please import or add trades first.")
            return

        for t in self.annotated_trades:
            try:
                t["PnL"] = float(t.get("PnL", 0))
            except:
                t["PnL"] = 0.0

        total_pnl = sum(t["PnL"] for t in self.annotated_trades)
        show_summary_stats(self.annotated_trades, total_pnl)

    def show_dashboard(self):
        if not self.annotated_trades:
            messagebox.showwarning("No Trades", "Please import or add trades first.")
            return
        show_dashboard(self.annotated_trades)

    def export_excel(self):
        if not self.annotated_trades:
            messagebox.showwarning("No Trades", "Please import or add trades first.")
            return
        try:
            export_to_excel(self.annotated_trades)
            messagebox.showinfo("Export Complete", "Trades exported to Excel.")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export to Excel:\n{e}")

    def export_pdf(self):
        if not self.annotated_trades:
            messagebox.showwarning("No Trades", "Please import or add trades first.")
            return

        # ——— 1) Ask for date range via calendar pickers ———
        dlg = tk.Toplevel(self.root)
        dlg.title("Select Date Range")

        # holder for the picked dates
        date_vars = {}

        tk.Label(dlg, text="Start Date:").grid(row=0, column=0, padx=5, pady=5)
        start_cal = DateEntry(
            dlg,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            year=datetime.datetime.now().year
        )
        start_cal.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(dlg, text="End Date:").grid(row=1, column=0, padx=5, pady=5)
        end_cal = DateEntry(
            dlg,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            year=datetime.datetime.now().year
        )
        end_cal.grid(row=1, column=1, padx=5, pady=5)

        def on_ok():
            date_vars['sd'] = start_cal.get_date()
            date_vars['ed'] = end_cal.get_date()
            dlg.destroy()

        def on_cancel():
            dlg.destroy()

        btnf = tk.Frame(dlg)
        btnf.grid(row=2, columnspan=2, pady=10)
        tk.Button(btnf, text="OK", command=on_ok).pack(side="left", padx=5)
        tk.Button(btnf, text="Cancel", command=on_cancel).pack(side="left", padx=5)

        dlg.grab_set()
        dlg.wait_window()

        # if user cancelled or never picked dates, bail out
        if 'sd' not in date_vars or 'ed' not in date_vars:
            return

        sd = date_vars['sd']
        ed = date_vars['ed']
        if sd > ed:
            messagebox.showerror("Invalid Range", "Start date must be on or before End date.")
            return

        # ——— 2) Filter trades by date only (ignore time) ———
        filtered = []
        for t in self.annotated_trades:
            ts = t.get("BuyTimestamp")
            if isinstance(ts, datetime.datetime):
                d = ts.date()
            else:
                try:
                    d = datetime.datetime.strptime(str(ts)[:10], "%Y-%m-%d").date()
                except:
                    continue
            if sd <= d <= ed:
                filtered.append(t)

        if not filtered:
            messagebox.showinfo("No Trades", "No trades found in that date range.")
            return

        # ——— 3) Ask for save path ———
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not file_path:
            return

        # ——— 4) Build PDF with images ———
        from fpdf import FPDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Trade Report", ln=True, align="C")
        pdf.ln(5)

        for idx, trade in enumerate(filtered, 1):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, f"Trade #{idx}", ln=True)
            pdf.set_font("Arial", size=10)

            # write all fields except "OriginalTrades" and "ImagePath"
            for key, val in trade.items():
                if key in ("OriginalTrades", "ImagePath"):
                    continue
                pdf.cell(0, 6, f"{key}: {val}", ln=True)

            # embed image if present
            img = trade.get("ImagePath", "")
            if img and os.path.exists(img):
                try:
                    pdf.image(img, w=100)
                    pdf.ln(5)
                except Exception as e:
                    pdf.cell(0, 6, f"[Could not embed image: {e}]", ln=True)

            pdf.ln(4)

        # ——— 5) Save PDF ———
        try:
            pdf.output(file_path)
            messagebox.showinfo("Export Complete", f"PDF saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save PDF:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = JournalApp(root)
    root.mainloop()
