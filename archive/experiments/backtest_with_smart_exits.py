#!/usr/bin/env python3
"""
CLEAN BACKTEST with SMART EXITS (from option-machine)

Exit triggers:
1. Runner Trail Stop: Keep 50% of max profit
2. Quick Win: +$200+ in <3 days, exit if momentum stalls
3. Stop Loss: Position loses 10%
4. Max Hold: 14 days (safety)

NO hedging, NO slippage, REAL costs
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
import glob

print("=" * 80)
print("CLEAN BACKTEST - SMART EXITS (option-machine logic)")
print("=" * 80)

# Load SPY
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
spy_daily = []
for f in spy_files:
    df = pd.read_parquet(f)
    if len(df) > 0:
        spy_daily.append({
            'date': pd.to_datetime(df['ts'].iloc[0]).date(),
            'close': df['close'].iloc[-1]
        })

spy_df = pd.DataFrame(spy_daily)

# Features
spy_df['ret'] = spy_df['close'].pct_change()
spy_df['RV10'] = spy_df['ret'].rolling(10).std() * np.sqrt(252)
spy_df['MA20'] = spy_df['close'].rolling(20).mean()
spy_df['slope'] = spy_df['close'].pct_change(20)

# Regime: Uptrend
spy_df['regime'] = 0
spy_df.loc[spy_df['slope'] > 0.02, 'regime'] = 1

# Score
spy_df['score'] = spy_df['slope'].clip(lower=0)

print(f"Loaded {len(spy_df)} days: {spy_df['date'].min()} to {spy_df['date'].max()}")
print(f"Regime 1 days: {(spy_df['regime']==1).sum()} ({(spy_df['regime']==1).sum()/len(spy_df)*100:.1f}%)")

# Backtest with SMART EXITS
print("\nExit Logic (from option-machine):")
print("  1. Runner trail: Keep 50% of max profit")
print("  2. Quick win: +$200 in <3 days")
print("  3. Stop loss: Position -10%")
print("  4. Max hold: 14 days")
print()

polygon = PolygonOptionsLoader()
trades = []
position = None

# Exit params
RUNNER_TRAIL_PCT = 0.50  # Keep 50% of max profit
QUICK_WIN_TARGET = 200  # $200 profit
QUICK_WIN_DAYS = 3
STOP_LOSS_PCT = -0.10  # -10% on position value
MAX_HOLD_DAYS = 14

for idx in range(50, len(spy_df)):
    row = spy_df.iloc[idx]
    d = row['date']
    spot = row['close']
    regime = row['regime']
    score = row['score']

    # Check exits
    if position:
        days_held = (d - position['entry_date']).days

        # Get current prices
        call_mid = polygon.get_option_price(d, position['strike'], position['expiry'], 'call', 'mid')
        put_mid = polygon.get_option_price(d, position['strike'], position['expiry'], 'put', 'mid')

        if call_mid and put_mid:
            straddle_mid = call_mid + put_mid
            exit_price = straddle_mid - 0.03
            proceeds = exit_price * 100
            pnl = proceeds - position['entry_cost'] - 2.60

            # Update peak
            if pnl > position['peak_pnl']:
                position['peak_pnl'] = pnl
                position['peak_day'] = days_held

            # Position value change (for stop loss)
            position_change = (straddle_mid / position['entry_straddle']) - 1

            should_exit = False
            exit_reason = ""

            # Exit 1: Runner trail stop
            if position['peak_pnl'] > 0:
                trail_level = position['peak_pnl'] * RUNNER_TRAIL_PCT
                if pnl < trail_level:
                    should_exit = True
                    exit_reason = f"Trail stop (keep 50% of peak ${position['peak_pnl']:.0f})"

            # Exit 2: Quick win
            if days_held <= QUICK_WIN_DAYS and pnl > QUICK_WIN_TARGET:
                # Check if momentum stalling (SPY not moving much)
                if abs(spy_df.iloc[idx]['ret']) < 0.005:  # <0.5% daily move
                    should_exit = True
                    exit_reason = f"Quick win ${pnl:.0f} in {days_held}d"

            # Exit 3: Stop loss
            if position_change < STOP_LOSS_PCT:
                should_exit = True
                exit_reason = f"Stop loss (position {position_change*100:.1f}%)"

            # Exit 4: Max hold
            if days_held >= MAX_HOLD_DAYS:
                should_exit = True
                exit_reason = f"Max hold {days_held}d"

            # Exit 5: Regime change
            if regime != 1:
                should_exit = True
                exit_reason = "Regime change"

            if should_exit:
                position['exit_date'] = d
                position['exit_pnl'] = pnl
                position['days_held'] = days_held
                position['exit_reason'] = exit_reason
                trades.append(position)

                spy_move = ((spot / position['entry_spot']) - 1) * 100
                peak_info = f"Peak ${position['peak_pnl']:.0f} Day {position['peak_day']}" if position['peak_pnl'] > 0 else ""
                print(f"Exit {len(trades):02d}: {d}, {days_held}d, SPY {spy_move:+.1f}%, "
                      f"P&L ${pnl:+.0f}, {exit_reason}, {peak_info}")

                position = None

    # Entry
    if not position and score > 0.05 and regime == 1:
        strike = round(spot)
        target = d + timedelta(days=75)
        fd = date(target.year, target.month, 1)
        ff = fd + timedelta(days=(4 - fd.weekday()) % 7)
        expiry = ff + timedelta(days=14)

        call_mid = polygon.get_option_price(d, strike, expiry, 'call', 'mid')
        put_mid = polygon.get_option_price(d, strike, expiry, 'put', 'mid')

        if call_mid and put_mid:
            straddle_mid = call_mid + put_mid
            entry_price = straddle_mid + 0.03
            entry_cost = entry_price * 100

            position = {
                'entry_date': d,
                'entry_spot': spot,
                'strike': strike,
                'expiry': expiry,
                'entry_straddle': straddle_mid,
                'entry_cost': entry_cost,
                'peak_pnl': -999999,
                'peak_day': 0
            }

            print(f"Enter {len(trades)+1:02d}: {d}, SPY ${spot:.0f}, Score {score:.2f}")

# Results
print("\n" + "=" * 80)
print("RESULTS - SMART EXITS")
print("=" * 80)

if trades:
    df = pd.DataFrame(trades)
    total = df['exit_pnl'].sum()
    winners = (df['exit_pnl'] > 0).sum()

    print(f"\nTrades: {len(trades)}")
    print(f"Winners: {winners} ({winners/len(trades)*100:.1f}%)")
    print(f"Losers: {len(trades) - winners}")
    print(f"\nTotal P&L: ${total:,.2f}")
    print(f"Average: ${total/len(trades):.2f}/trade")

    # Compare to dumb exits
    print(f"\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print(f"Dumb exits (14 days):        ${-1535:>10,.0f}")
    print(f"Smart exits (trail stop):    ${total:>10,.0f}")
    print(f"Improvement:                 ${total - (-1535):>10,.0f}")

    # Exit reason breakdown
    print(f"\nExit reasons:")
    for reason_type in ['Trail stop', 'Quick win', 'Stop loss', 'Max hold', 'Regime']:
        count = sum(1 for t in trades if reason_type.lower() in t['exit_reason'].lower())
        if count > 0:
            print(f"  {reason_type}: {count}")

    df.to_csv('smart_exit_results.csv', index=False)
    print(f"\nSaved: smart_exit_results.csv")

else:
    print("\nNO TRADES")
