import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from typing import List, Dict
from grouping import group_trades_by_entry_exit
import logging

logger = logging.getLogger(__name__)

def parse_smart_csv(content: BytesIO) -> List[Dict]:
    """Smart CSV parser for broker trade history.
    Auto-detects and maps columns from various brokers (Tradovate, Schwab, Alpaca, etc.).
    Cleans data (dates, prices with $, etc.) and returns list of trade dicts compatible with TradeIn schema.
    """
    try:
        df = pd.read_csv(content)
        if df.empty:
            logger.info("CSV is empty, returning empty list.")
            return []

        # Case-insensitive column detection
        lower_cols = df.columns.str.lower()

        # Comprehensive column mapping (broker-agnostic, includes your CSV headers)
        mapping = {
            'instrument': ['symbol', 'instrument', 'ticker', 'contract', 'underlying', 'instrument'],
            'buy_timestamp': ['boughttimestamp', 'buytimestamp', 'entrytime', 'opentime', 'tradetime', 'date', 'timestamp', 'buy_timestamp', 'buy time'],
            'sell_timestamp': ['soldtimestamp', 'selltimestamp', 'exittime', 'closetime', 'filltime', 'sell_timestamp', 'sell time'],
            'buy_price': ['buyprice', 'entryprice', 'openprice', 'avgentryprice', 'price', 'filledavgprice', 'buy_price', 'buy price'],
            'sell_price': ['sellprice', 'exitprice', 'closeprice', 'avgexitprice', 'sell_price', 'sell price'],
            'qty': ['qty', 'quantity', 'size', 'contracts', 'shares', 'lots', 'qty'],
            'pnl': ['pnl', 'profitloss', 'p&l', 'netpnl'],
            'direction': ['side', 'action', 'type', 'buy/sell'],
            'strategy': ['strategy', 'tag', 'notes', 'strategy'],
            'fees': ['fees', 'commission', 'cost'],
            'confidence': ['confidence', 'confidence'],
            'target': ['target', 'target'],
            'stop': ['stop', 'stop'],
            'notes': ['notes', 'notes'],
            'goals': ['goals', 'goals'],
            'preparedness': ['preparedness', 'preparedness'],
            'what_i_learned': ['what_i_learned', 'what_i_learned'],
            'changes_needed': ['changes_needed', 'changes_needed'],
            'trade_type': ['trade_type', 'trade type', 'type', 'trade_type'],
        }

        # Map columns
        mapped_df = pd.DataFrame()
        unmapped_columns = set(df.columns)
        for key, aliases in mapping.items():
            found_col = None
            for alias in aliases:
                if alias.lower() in lower_cols.values:
                    found_col = df.columns[lower_cols.tolist().index(alias.lower())]
                    mapped_df[key] = df[found_col]
                    unmapped_columns.discard(found_col)
                    break
            if not found_col:
                logger.debug(f"No column found for '{key}', setting default.")
                if key == 'instrument':
                    mapped_df[key] = 'UNKNOWN'
                elif key == 'qty':
                    mapped_df[key] = 1
                elif key == 'buy_price':
                    mapped_df[key] = 0.0
                elif key == 'sell_price':
                    mapped_df[key] = 0.0
                elif key == 'pnl':
                    mapped_df[key] = 0.0
                elif key == 'stop':
                    mapped_df[key] = 0.0
                elif key == 'direction':
                    mapped_df[key] = 'Long'
                elif key == 'buy_timestamp':
                    mapped_df[key] = datetime.utcnow().isoformat()
                elif key == 'sell_timestamp':
                    mapped_df[key] = datetime.utcnow().isoformat()
                elif key == 'trade_type':
                    mapped_df[key] = 'Stock'
                else:
                    mapped_df[key] = ''

        # Log unmapped columns for debugging
        if unmapped_columns:
            logger.warning(f"Unmapped columns in CSV: {unmapped_columns}")

        # Clean data
        # Timestamps: Parse multiple date formats to ISO
        date_formats = ['%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y']
        for col in ['buy_timestamp', 'sell_timestamp']:
            if col in mapped_df.columns:
                for fmt in date_formats:
                    mapped_df[col] = pd.to_datetime(mapped_df[col], format=fmt, errors='coerce')
                    if mapped_df[col].notnull().any():
                        break
                mapped_df[col] = mapped_df[col].apply(lambda x: x.isoformat() if pd.notnull(x) else datetime.utcnow().isoformat())

        # Prices: Strip $ and convert to float
        price_cols = ['buy_price', 'sell_price', 'pnl', 'target', 'stop', 'fees']
        for col in price_cols:
            if col in mapped_df.columns:
                mapped_df[col] = pd.to_numeric(mapped_df[col].astype(str).str.replace('$', '').str.replace('(', '-').str.replace(')', '').str.strip(), errors='coerce').fillna(0).astype(float)

        # Qty and confidence to int
        int_cols = ['qty', 'confidence']
        for col in int_cols:
            if col in mapped_df.columns:
                mapped_df[col] = pd.to_numeric(mapped_df[col].astype(str).str.strip(), errors='coerce').fillna(1 if col == 'qty' else 0).astype(int)

        # String optional fields
        str_cols = ['strategy', 'notes', 'goals', 'preparedness', 'what_i_learned', 'changes_needed', 'trade_type']
        for col in str_cols:
            if col in mapped_df.columns:
                mapped_df[col] = mapped_df[col].astype(str).fillna('')

        # Direction: Map BUY/SELL to Long/Short if present
        if 'direction' in mapped_df.columns:
            mapped_df['direction'] = mapped_df['direction'].str.upper().map({'BUY': 'Long', 'SELL': 'Short', 'LONG': 'Long', 'SHORT': 'Short'}).fillna('Long')
        else:
            mapped_df['direction'] = mapped_df.apply(lambda row: 'Long' if row.get('sell_price', 0) > row.get('buy_price', 0) else 'Short', axis=1)

        # Group unpaired trades if needed
        if 'direction' not in mapped_df.columns or 'buy_timestamp' not in mapped_df.columns:
            raw_trades = mapped_df.to_dict('records')
            grouped = group_trades_by_entry_exit(raw_trades)
        else:
            grouped = mapped_df.to_dict('records')

        # Convert to TradeIn format
        trades = []
        for trade in grouped:
            buy_price = float(trade.get('buy_price', 0))
            sell_price = float(trade.get('sell_price', 0))
            qty = int(trade.get('qty', 1))
            direction = str(trade.get('direction', 'Long'))
            stop = float(trade.get('stop', buy_price * (0.9 if direction == 'Long' else 1.1)))
            multiplier = qty * 100 if trade.get('trade_type', 'Stock') in ("Call", "Put", "Straddle", "Covered Call", "Cash Secured Put") else qty
            pnl = round((sell_price - buy_price) * multiplier - trade.get('fees', 0), 2) if direction == 'Long' else round((buy_price - sell_price) * multiplier - trade.get('fees', 0), 2)
            r_multiple = 0 if not stop else (
                (sell_price - buy_price) / (buy_price - stop) if direction == 'Long' else
                (buy_price - sell_price) / (stop - buy_price)
            )
            r_multiple = round(r_multiple, 2)

            trades.append({
                "instrument": str(trade.get('instrument', 'UNKNOWN')),
                "buy_timestamp": trade.get('buy_timestamp', datetime.utcnow().isoformat()),
                "sell_timestamp": trade.get('sell_timestamp', datetime.utcnow().isoformat()),
                "buy_price": buy_price,
                "sell_price": sell_price,
                "qty": qty,
                "direction": direction,
                "trade_type": str(trade.get('trade_type', 'Stock')),
                "strategy_id": int(trade.get('strategy_id', 0)) if trade.get('strategy_id') else None,
                "confidence": int(trade.get('confidence', 0)),
                "target": float(trade.get('target', 0)),
                "stop": stop,
                "notes": str(trade.get('notes', '')),
                "goals": str(trade.get('goals', '')),
                "preparedness": str(trade.get('preparedness', '')),
                "what_i_learned": str(trade.get('what_i_learned', '')),
                "changes_needed": str(trade.get('changes_needed', '')),
                "rule_adherence": [],
                "fees": float(trade.get('fees', 0)),
                "pnl": pnl,
                "r_multiple": r_multiple,
            })

        logger.debug(f"Parsed {len(trades)} trades from CSV")
        return trades
    except pd.errors.EmptyDataError:
        logger.error("CSV is empty or invalid")
        raise ValueError("CSV is empty or invalid.")
    except Exception as e:
        logger.error(f"CSV parsing error: {str(e)}")
        raise ValueError(f"CSV parsing error: {str(e)}. Check format and try again.")