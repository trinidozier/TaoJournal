import pandas as pd
from io import BytesIO
from datetime import datetime
from typing import List, Dict
from grouping import group_trades_by_entry_exit  # Your existing function for pairing buys/sells

def parse_smart_csv(content: BytesIO) -> List[Dict]:
    """
    Smart CSV parser for broker trade history.
    Auto-detects and maps columns from various brokers (Tradovate, Schwab, Alpaca, etc.).
    Cleans data (dates, prices with $, etc.) and returns list of trade dicts.
    """
    try:
        df = pd.read_csv(content)
        if df.empty:
            return []

        # Case-insensitive column detection
        lower_cols = df.columns.str.lower()

        # Comprehensive column mapping (broker-agnostic)
        mapping = {
            'instrument': ['symbol', 'instrument', 'ticker', 'contract', 'underlying'],
            'buy_timestamp': ['boughttimestamp', 'buytimestamp', 'entrytime', 'opentime', 'tradetime', 'date', 'timestamp'],
            'sell_timestamp': ['soldtimestamp', 'selltimestamp', 'exittime', 'closetime', 'filltime'],
            'buy_price': ['buyprice', 'entryprice', 'openprice', 'avgentryprice', 'price', 'filledavgprice'],
            'sell_price': ['sellprice', 'exitprice', 'closeprice', 'avgexitprice'],
            'qty': ['qty', 'quantity', 'size', 'contracts', 'shares', 'lots'],
            'pnl': ['pnl', 'profitloss', 'p&l', 'netpnl'],
            'direction': ['side', 'action', 'type', 'buy/sell'],  # 'BUY'/'SELL' or 'Long'/'Short'
            'strategy': ['strategy', 'tag', 'notes'],  # Optional, fallback empty
            'fees': ['fees', 'commission', 'cost'],
        }

        # Map columns
        mapped_df = df.copy()
        for key, aliases in mapping.items():
            found_col = None
            for alias in aliases:
                if alias.lower() in lower_cols.values:
                    found_col = df.columns[lower_cols.tolist().index(alias.lower())]
                    mapped_df[key] = df[found_col]
                    break
            if not found_col and key in ['instrument', 'qty', 'buy_price', 'sell_price']:  # Required
                raise ValueError(f"Required column for '{key}' not found. Expected: {aliases}. CSV headers: {df.columns.tolist()}")

        # Clean data
        # Timestamps: Parse MM/DD/YYYY H:MM to ISO
        if 'buy_timestamp' in mapped_df.columns:
            mapped_df['buy_timestamp'] = pd.to_datetime(mapped_df['buy_timestamp'], format='%m/%d/%Y %H:%M', errors='coerce').dt.isoformat()
        if 'sell_timestamp' in mapped_df.columns:
            mapped_df['sell_timestamp'] = pd.to_datetime(mapped_df['sell_timestamp'], format='%m/%d/%Y %H:%M', errors='coerce').dt.isoformat()

        # Prices: Strip $ and convert to float
        price_cols = ['buy_price', 'sell_price', 'pnl']
        for col in price_cols:
            if col in mapped_df.columns:
                mapped_df[col] = mapped_df[col].astype(str).str.replace('$', '').str.replace('(', '-').str.replace(')', '').astype(float)

        # Qty to int
        if 'qty' in mapped_df.columns:
            mapped_df['qty'] = mapped_df['qty'].astype(int)

        # Direction: Map BUY/SELL to Long/Short if present
        if 'direction' in mapped_df.columns:
            mapped_df['direction'] = mapped_df['direction'].str.upper().map({'BUY': 'Long', 'SELL': 'Short', 'LONG': 'Long', 'SHORT': 'Short'}).fillna('Long')

        # Fill missing optional fields
        optional_fields = ['strategy', 'confidence', 'target', 'stop', 'notes', 'goals', 'preparedness', 'what_i_learned', 'changes_needed']
        for field in optional_fields:
            if field not in mapped_df.columns:
                mapped_df[field] = ''

        # If no side/direction, infer from buy/sell prices (assume Long if sell > buy)
        if 'direction' not in mapped_df.columns:
            mapped_df['direction'] = mapped_df.apply(lambda row: 'Long' if row['sell_price'] > row['buy_price'] else 'Short', axis=1)

        # Group unpaired trades if needed (e.g., separate buy/sell rows)
        if 'side' in mapped_df.columns or len(mapped_df) > 0 and 'buy_timestamp' not in mapped_df.columns:  # Fallback to grouping
            raw_trades = mapped_df.to_dict('records')
            grouped = group_trades_by_entry_exit(raw_trades)  # Your existing function
        else:
            grouped = mapped_df.to_dict('records')

        # Convert to TradeIn format
        trades = []
        for trade in grouped:
            trades.append({
                "instrument": str(trade.get('instrument', '')),
                "buy_timestamp": trade.get('buy_timestamp', datetime.now().isoformat()),
                "sell_timestamp": trade.get('sell_timestamp', datetime.now().isoformat()),
                "buy_price": float(trade.get('buy_price', 0)),
                "sell_price": float(trade.get('sell_price', 0)),
                "qty": int(trade.get('qty', 1)),
                "direction": str(trade.get('direction', 'Long')),
                "trade_type": str(trade.get('trade_type', 'Stock')),
                "strategy": str(trade.get('strategy', '')),
                "confidence": int(trade.get('confidence', 0)),
                "target": float(trade.get('target', 0)),
                "stop": float(trade.get('stop', 0)),
                "notes": str(trade.get('notes', '')),
                "goals": str(trade.get('goals', '')),
                "preparedness": str(trade.get('preparedness', '')),
                "what_i_learned": str(trade.get('what_i_learned', '')),
                "changes_needed": str(trade.get('changes_needed', '')),
            })

        return trades

    except pd.errors.EmptyDataError:
        raise ValueError("CSV is empty or invalid.")
    except Exception as e:
        raise ValueError(f"CSV parsing error: {str(e)}. Check format and try again.")