import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from typing import List, Dict
from grouping import group_trades_by_entry_exit
import logging
import io

logger = logging.getLogger(__name__)

def parse_smart_csv(content: str) -> List[Dict]:
    """Smart CSV parser for broker trade history.
    Auto-detects and maps columns, parsing timestamps to datetime objects.
    """
    try:
        df = pd.read_csv(io.StringIO(content))
        if df.empty:
            logger.info("CSV is empty, returning empty list.")
            return []

        # Case-insensitive column detection
        lower_cols = df.columns.str.lower()

        # Column mapping
        mapping = {
            'buy_price': ['buyprice', 'entryprice', 'openprice', 'avgentryprice', 'price', 'filledavgprice', 'buy_price', 'buy price'],
            'sell_price': ['sellprice', 'exitprice', 'closeprice', 'avgexitprice', 'sell_price', 'sell price'],
            'qty': ['qty', 'quantity', 'size', 'contracts', 'shares', 'lots', 'qty'],
            'buy_timestamp': ['boughttimestamp', 'buytimestamp', 'entrytime', 'opentime', 'tradetime', 'date', 'timestamp', 'buy_timestamp', 'buy time'],
            'sell_timestamp': ['soldtimestamp', 'selltimestamp', 'exittime', 'closetime', 'filltime', 'sell_timestamp', 'sell time'],
            'direction': ['side', 'action', 'type', 'buy/sell'],
            'stop': ['stop', 'stop'],
            'fees': ['fees', 'commission', 'cost'],
            'instrument': ['symbol', 'ticker', 'instrument', 'asset']
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
                if key == 'qty':
                    mapped_df[key] = 1
                elif key == 'buy_price':
                    mapped_df[key] = 0.0
                elif key == 'sell_price':
                    mapped_df[key] = 0.0
                elif key == 'stop':
                    mapped_df[key] = 0.0
                elif key == 'direction':
                    mapped_df[key] = 'Long'
                elif key == 'buy_timestamp':
                    mapped_df[key] = datetime.utcnow()
                elif key == 'sell_timestamp':
                    mapped_df[key] = datetime.utcnow()
                elif key == 'fees':
                    mapped_df[key] = 0.0
                elif key == 'instrument':
                    mapped_df[key] = 'Unknown'

        # Log unmapped columns
        if unmapped_columns:
            logger.warning(f"Unmapped columns in CSV: {unmapped_columns}")

        # Parse timestamps to datetime
        date_formats = ['%Y-%m-%dT%H:%M:%S', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y']
        for col in ['buy_timestamp', 'sell_timestamp']:
            if col in mapped_df.columns:
                for fmt in date_formats:
                    try:
                        mapped_df[col] = pd.to_datetime(mapped_df[col], format=fmt, errors='coerce')
                        if mapped_df[col].notnull().any():
                            break
                    except ValueError:
                        continue
                mapped_df[col] = mapped_df[col].apply(lambda x: x if pd.notnull(x) else datetime.utcnow())

        # Clean prices
        price_cols = ['buy_price', 'sell_price', 'stop', 'fees']
        for col in price_cols:
            if col in mapped_df.columns:
                mapped_df[col] = pd.to_numeric(
                    mapped_df[col].astype(str)
                    .str.replace('$', '')
                    .str.replace('(', '-')
                    .str.replace(')', '')
                    .str.strip(),
                    errors='coerce'
                ).fillna(0).astype(float)

        # Clean qty
        if 'qty' in mapped_df.columns:
            mapped_df['qty'] = pd.to_numeric(mapped_df['qty'].astype(str).str.strip(), errors='coerce').fillna(1).astype(int)

        # Clean direction
        if 'direction' in mapped_df.columns:
            mapped_df['direction'] = mapped_df['direction'].astype(str).str.upper().map({
                'BUY': 'Long',
                'SELL': 'Short',
                'LONG': 'Long',
                'SHORT': 'Short'
            }).fillna('Long')
        else:
            mapped_df['direction'] = mapped_df.apply(
                lambda row: 'Long' if row.get('sell_price', 0) > row.get('buy_price', 0) else 'Short',
                axis=1
            )

        # Group trades if needed
        grouped = mapped_df.to_dict('records') if 'direction' in mapped_df.columns and 'buy_timestamp' in mapped_df.columns else group_trades_by_entry_exit(mapped_df.to_dict('records'))

        # Convert to TradeIn format
        trades = []
        for trade in grouped:
            buy_price = float(trade.get('buy_price', 0))
            sell_price = float(trade.get('sell_price', 0))
            qty = int(trade.get('qty', 1))
            direction = str(trade.get('direction', 'Long'))
            stop = float(trade.get('stop', buy_price * (0.9 if direction == 'Long' else 1.1)))
            trades.append({
                "instrument": trade.get("instrument", "Unknown"),  # ✅ Added field
                "buy_price": buy_price,
                "sell_price": sell_price,
                "qty": qty,
                "buy_timestamp": trade.get('buy_timestamp', datetime.utcnow()),
                "sell_timestamp": trade.get('sell_timestamp', datetime.utcnow()),
                "direction": direction,
                "stop": stop,
                "fees": float(trade.get('fees', 0))
            })

        logger.debug(f"Parsed {len(trades)} trades from CSV")
        return trades

    except pd.errors.EmptyDataError:
        logger.error("CSV is empty or invalid")
        raise ValueError("CSV is empty or invalid.")
    except Exception as e:
        logger.error(f"CSV parsing error: {str(e)}")
        raise ValueError(f"CSV parsing error: {str(e)}. Check format and try again.")
