import pandas as pd
from io import BytesIO
from grouping import group_trades_by_entry_exit  # Your existing function

def parse_smart_csv(content: BytesIO) -> List[dict]:
    """Smart CSV parser that auto-detects and maps broker-specific columns."""
    df = pd.read_csv(content)
    if df.empty:
        return []

    # Common column mappings (case-insensitive)
    column_map = {
        'instrument': ['Symbol', 'Instrument', 'Ticker', 'Contract'],
        'timestamp': ['DateTime', 'Timestamp', 'TradeDate', 'Time'],
        'buy_timestamp': ['BuyTimestamp', 'EntryTime', 'OpenTime'],
        'sell_timestamp': ['SellTimestamp', 'ExitTime', 'CloseTime'],
        'buy_price': ['BuyPrice', 'EntryPrice', 'OpenPrice', 'AvgPrice'],
        'sell_price': ['SellPrice', 'ExitPrice', 'ClosePrice'],
        'qty': ['Quantity', 'Qty', 'Size', 'Contracts'],
        'side': ['Side', 'Action', 'Type', 'Buy/Sell'],  # For direction
        'pnl': ['PnL', 'ProfitLoss', 'P&L'],
        'fees': ['Fees', 'Commission', 'Cost'],
    }

    # Detect and map columns
    mapped_df = df.copy()
    for key, aliases in column_map.items():
        for alias in aliases:
            if alias.lower() in df.columns.str.lower():
                col_idx = df.columns.str.lower().tolist().index(alias.lower())
                mapped_df[key] = df.iloc[:, col_idx]
                break
        else:
            # Fallback: Warn or use defaults (e.g., empty for optional fields)
            if key in ['instrument', 'qty', 'buy_price', 'sell_price']:  # Required
                raise ValueError(f"Required column for {key} not found. Expected: {aliases}")

    # Handle separate buy/sell rows (common in broker CSVs)
    if 'side' in mapped_df.columns:
        # Group buy/sell pairs
        raw_trades = []
        for _, row in mapped_df.iterrows():
            raw_trades.append({
                "instrument": row.get('instrument', ''),
                "buy_timestamp": row.get('buy_timestamp', row.get('timestamp', '')),
                "sell_timestamp": row.get('sell_timestamp', row.get('timestamp', '')),
                "buy_price": row.get('buy_price', row.get('price', 0)),
                "sell_price": row.get('sell_price', row.get('price', 0)),
                "qty": row.get('qty', 1),
                "side": row.get('side', 'BUY'),
                # Add other fields
            })
        grouped = group_trades_by_entry_exit(raw_trades)  # Your existing grouping
    else:
        # Assume paired rows
        grouped = mapped_df.to_dict('records')

    # Convert to TradeIn format
    trades = []
    for trade in grouped:
        trades.append({
            "instrument": trade.get('instrument', ''),
            "buy_timestamp": pd.to_datetime(trade.get('buy_timestamp', datetime.now())).isoformat(),
            "sell_timestamp": pd.to_datetime(trade.get('sell_timestamp', datetime.now())).isoformat(),
            "buy_price": float(trade.get('buy_price', 0)),
            "sell_price": float(trade.get('sell_price', 0)),
            "qty": int(trade.get('qty', 1)),
            "direction": "Long" if trade.get('side', 'BUY') == 'BUY' else "Short",
            "strategy": trade.get('strategy', ''),
            "confidence": int(trade.get('confidence', 0)),
            "target": float(trade.get('target', 0)),
            "stop": float(trade.get('stop', 0)),
            "notes": trade.get('notes', ''),
            "goals": trade.get('goals', ''),
            "preparedness": trade.get('preparedness', ''),
            "what_i_learned": trade.get('what_i_learned', ''),
            "changes_needed": trade.get('changes_needed', ''),
        })

    return trades