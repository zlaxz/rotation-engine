#!/usr/bin/env python3
"""
Quick test of intraday tracking on a small sample

Tests the logic on just 2023 data with first 20 trades
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import glob
from typing import Dict, List, Optional

from src.data.polygon_options import PolygonOptionsLoader


def load_spy_data_2023() -> pd.DataFrame:
    """Load SPY data for 2023 only (faster)"""
    print("Loading SPY data for 2023...")

    spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/2023*.parquet'))
    spy_data = []

    for f in spy_files:
        df = pd.read_parquet(f)
        if len(df) > 0:
            spy_data.append({
                'date': pd.to_datetime(df['ts'].iloc[0]).date(),
                'open': df['open'].iloc[0],
                'high': df['high'].max(),
                'low': df['low'].min(),
                'close': df['close'].iloc[-1],
                'volume': df['volume'].sum()
            })

    spy = pd.DataFrame(spy_data)

    # Calculate derived features
    spy['return_1d'] = spy['close'].pct_change()
    spy['return_5d'] = spy['close'].pct_change(5)
    spy['return_10d'] = spy['close'].pct_change(10)
    spy['return_20d'] = spy['close'].pct_change(20)

    spy['MA20'] = spy['close'].rolling(20).mean()
    spy['MA50'] = spy['close'].rolling(50).mean()
    spy['slope_MA20'] = spy['MA20'].pct_change(20)
    spy['slope_MA50'] = spy['MA50'].pct_change(50)

    spy['RV5'] = spy['return_1d'].rolling(5).std() * np.sqrt(252)
    spy['RV10'] = spy['return_1d'].rolling(10).std() * np.sqrt(252)
    spy['RV20'] = spy['return_1d'].rolling(20).std() * np.sqrt(252)

    spy['HL'] = spy['high'] - spy['low']
    spy['ATR5'] = spy['HL'].rolling(5).mean()
    spy['ATR10'] = spy['HL'].rolling(10).mean()

    print(f"Loaded {len(spy)} days from {spy['date'].min()} to {spy['date'].max()}\n")

    return spy


def get_expiry_for_dte(entry_date: date, dte_target: int) -> date:
    """Calculate expiry (3rd Friday)"""
    target_date = entry_date + timedelta(days=dte_target)
    first_day = date(target_date.year, target_date.month, 1)
    days_to_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=days_to_friday)
    third_friday = first_friday + timedelta(days=14)
    return third_friday


def track_trade_intraday_sample(
    entry_date: date,
    strike: float,
    expiry: date,
    leg_type: str,
    leg_qty: int,
    polygon: PolygonOptionsLoader
) -> Optional[Dict]:
    """
    Track a single trade with 15-minute bars (simplified for testing)
    """
    print(f"  Loading minute bars for {entry_date}...")

    # Load minute bars for entry date only (quick test)
    minute_bars = polygon.load_minute_bars(
        trade_date=entry_date,
        strike=strike,
        expiry=expiry,
        option_type=leg_type
    )

    if minute_bars.empty:
        print(f"  ❌ No minute bars available")
        return None

    print(f"  ✅ Loaded {len(minute_bars)} minute bars")

    # Resample to 15-minute
    bars_15min = polygon.resample_to_15min(minute_bars)

    if bars_15min.empty:
        print(f"  ❌ No 15-minute bars after resampling")
        return None

    print(f"  ✅ Resampled to {len(bars_15min)} 15-minute bars")

    # Calculate position value at each bar
    entry_price = bars_15min['close'].iloc[0]
    entry_value = entry_price * leg_qty * 100

    pnls = []
    for _, bar in bars_15min.iterrows():
        bar_price = bar['close']
        bar_value = bar_price * leg_qty * 100
        bar_pnl = bar_value - entry_value
        pnls.append({
            'timestamp': bar['timestamp'],
            'price': bar_price,
            'value': bar_value,
            'pnl': bar_pnl
        })

    # Find peak
    pnl_values = [p['pnl'] for p in pnls]
    peak_idx = np.argmax(pnl_values)
    peak_pnl = pnl_values[peak_idx]
    peak_time = pnls[peak_idx]['timestamp']

    exit_pnl = pnl_values[-1]
    capture_rate = exit_pnl / peak_pnl if peak_pnl > 0 else 0.0

    print(f"  📊 Peak: ${peak_pnl:.2f} at {peak_time.strftime('%H:%M')}")
    print(f"  📊 Exit: ${exit_pnl:.2f} (Capture: {capture_rate*100:.1f}%)")

    return {
        'entry_date': entry_date,
        'strike': strike,
        'expiry': expiry,
        'entry_price': entry_price,
        'peak_pnl': peak_pnl,
        'peak_time': peak_time,
        'exit_pnl': exit_pnl,
        'capture_rate': capture_rate,
        'bars_count': len(bars_15min)
    }


def main():
    """Test intraday tracking on a small sample"""

    print("="*80)
    print("INTRADAY TRACKING TEST - SMALL SAMPLE")
    print("="*80)
    print("Testing on 2023 data with first 20 trades\n")

    # Load SPY data (2023 only)
    spy = load_spy_data_2023()

    # Initialize Polygon loader
    print("Initializing Polygon options loader...")
    polygon = PolygonOptionsLoader()

    if not polygon.has_minute_data:
        print("ERROR: Minute bar data not available")
        return

    print(f"✅ Minute bar data available\n")

    # Find first 20 Profile 1 (LDG) entries in 2023
    print("Finding Profile 1 (LDG) entries in 2023...")

    trades = []
    last_entry_date = None

    for idx in range(60, len(spy)):
        row = spy.iloc[idx]
        entry_date = row['date']

        # Check spacing
        if last_entry_date and (entry_date - last_entry_date).days < 7:
            continue

        # Profile 1 condition: return_20d > 0.02
        if row.get('return_20d', 0) <= 0.02:
            continue

        # Disaster filter
        if row.get('RV5', 0) > 0.22:
            continue

        # Entry triggered
        spot = row['close']
        strike = round(spot)
        expiry = get_expiry_for_dte(entry_date, 75)

        if expiry <= entry_date:
            continue

        print(f"\nTrade {len(trades)+1}: {entry_date} | Spot=${spot:.2f} | Strike=${strike}")

        # Track with 15-minute bars (just call leg for simplicity)
        trade_record = track_trade_intraday_sample(
            entry_date=entry_date,
            strike=strike,
            expiry=expiry,
            leg_type='call',
            leg_qty=1,
            polygon=polygon
        )

        if trade_record:
            trades.append(trade_record)

        last_entry_date = entry_date

        # Stop after 20 trades
        if len(trades) >= 20:
            break

    print(f"\n{'='*80}")
    print(f"COMPLETED: Tracked {len(trades)} trades")
    print(f"{'='*80}\n")

    if trades:
        avg_peak = np.mean([t['peak_pnl'] for t in trades])
        avg_capture = np.mean([t['capture_rate'] for t in trades])

        print(f"Average Peak P&L: ${avg_peak:.2f}")
        print(f"Average Capture Rate: {avg_capture*100:.1f}%")
        print(f"Average 15-min bars per trade: {np.mean([t['bars_count'] for t in trades]):.0f}")


if __name__ == '__main__':
    main()
