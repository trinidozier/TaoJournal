import csv
from datetime import datetime
def parse_tradovate_csv(file_path):
    trades = []
    with open(file_path, newline='') as csvfile:
        # Auto-detect delimiter
        sample = csvfile.read(1024)
        csvfile.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel  # fallback to comma

        reader = csv.DictReader(csvfile, dialect=dialect)

        for row in reader:
            try:
                trade = {
                    "Instrument": row["symbol"],
                    "BuyPrice": float(row["buyPrice"]),
                    "SellPrice": float(row["sellPrice"]),
                    "BuyTimestamp": parse_timestamp(row["boughtTimestamp"]),
                    "SellTimestamp": parse_timestamp(row["soldTimestamp"]),
                    "PnL": parse_pnl(row["pnl"]),
                    "Duration": row.get("duration", ""),
                    "Qty": int(row["qty"])
                }
                trades.append(trade)
            except Exception as e:
                print(f"Error parsing row: {row}\n{e}")
    return trades
def parse_pnl(pnl_str):
    pnl_str = pnl_str.replace('$', '').replace('(', '-').replace(')', '').strip()
    return float(pnl_str)

def parse_timestamp(ts_str):
    try:
        return datetime.strptime(ts_str.strip(), "%m/%d/%Y %H:%M")
    except ValueError:
        return datetime.strptime(ts_str.strip(), "%m/%d/%Y %H:%M:%S")

import csv
from datetime import datetime
def parse_tradovate_csv(file_path):
    trades = []
    with open(file_path, newline='') as csvfile:
        # Auto-detect delimiter
        sample = csvfile.read(1024)
        csvfile.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel  # fallback to comma

        reader = csv.DictReader(csvfile, dialect=dialect)

        for row in reader:
            try:
                trade = {
                    "Instrument": row["symbol"],
                    "BuyPrice": float(row["buyPrice"]),
                    "SellPrice": float(row["sellPrice"]),
                    "BuyTimestamp": parse_timestamp(row["boughtTimestamp"]),
                    "SellTimestamp": parse_timestamp(row["soldTimestamp"]),
                    "PnL": parse_pnl(row["pnl"]),
                    "Duration": row.get("duration", ""),
                    "Qty": int(row["qty"])
                }
                trades.append(trade)
            except Exception as e:
                print(f"Error parsing row: {row}\n{e}")
    return trades
def parse_pnl(pnl_str):
    pnl_str = pnl_str.replace('$', '').replace('(', '-').replace(')', '').strip()
    return float(pnl_str)

def parse_timestamp(ts_str):
    try:
        return datetime.strptime(ts_str.strip(), "%m/%d/%Y %H:%M")
    except ValueError:
        return datetime.strptime(ts_str.strip(), "%m/%d/%Y %H:%M:%S")

