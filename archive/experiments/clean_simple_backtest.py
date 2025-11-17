#!/usr/bin/env python3
"""
CLEAN SIMPLE BACKTEST - Profile 1 (Long-Dated Gamma)

Built from scratch. Clean data. Real costs. No shortcuts.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader

print("=" * 80)
print("CLEAN SIMPLE BACKTEST - PROFILE 1 (LDG)")
print("=" * 80)

# STEP 1: Load clean data
print("\nSTEP 1: Loading clean data from yfinance...")
spy = yf.download('SPY', start='2020-01-01', end='2024-12-31', progress=False)
vix = yf.download('^VIX', start='2020-01-01', end='2024-12-31', progress=False)

spy['date'] = spy.index.date
vix['date'] = vix.index.date

# Merge
data = pd.DataFrame({
    'date': spy.index.date,
    'open': spy['Open'].values,
    'high': spy['High'].values,
    'low': spy['Low'].values,
    'close': spy['Close'].values,
    'volume': spy['Volume'].values,
    'vix': vix['Close'].values
})

print(f"  Loaded {len(data)} days: {data['date'].min()} to {data['date'].max()}")

# STEP 2: Compute features
print("\nSTEP 2: Computing features...")

# Returns
data['ret_1d'] = data['close'].pct_change()

# Realized volatility
data['RV5'] = data['ret_1d'].rolling(5).std() * np.sqrt(252)
data['RV10'] = data['ret_1d'].rolling(10).std() * np.sqrt(252)
data['RV20'] = data['ret_1d'].rolling(20).std() * np.sqrt(252)

# ATR
data['high_low'] = data['high'] - data['low']
data['ATR5'] = data['high_low'].rolling(5).mean()
data['ATR10'] = data['high_low'].rolling(10).mean()

# Moving averages
data['MA20'] = data['close'].rolling(20).mean()
data['MA50'] = data['close'].rolling(50).mean()

# Slopes
data['slope_MA20'] = (data['MA20'] - data['MA20'].shift(5)) / data['MA20'].shift(5)

# IV from VIX
data['IV20'] = data['vix'] / 100 * 0.95  # VIX is 30-day, scale to 20-day
data['IV60'] = data['vix'] / 100 * 1.08  # Scale to 60-day

print(f"  Features computed")

# STEP 3: Classify regimes (SIMPLE: just Trend Up for now)
print("\nSTEP 3: Classifying regimes...")

# Regime 1 (Trend Up): Positive MA slope, low VIX
data['regime'] = 0
data.loc[(data['slope_MA20'] > 0) & (data['vix'] < 25), 'regime'] = 1

regime_1_days = (data['regime'] == 1).sum()
print(f"  Regime 1 (Trend Up): {regime_1_days} days ({regime_1_days/len(data)*100:.1f}%)")

# STEP 4: Compute Profile 1 score (SIMPLE: RV/IV ratio)
print("\nSTEP 4: Computing Profile 1 scores...")

# Profile 1: Long gamma attractive when vol cheap
# Simple score: RV10/IV60 (higher = cheaper long vol)
data['rv_iv_ratio'] = data['RV10'] / (data['IV60'] + 1e-6)
data['profile_1_score'] = 1 / (1 + np.exp(-5 * (data['rv_iv_ratio'] - 0.9)))  # Sigmoid

high_score_days = (data['profile_1_score'] > 0.6).sum()
print(f"  Days with score > 0.6: {high_score_days} ({high_score_days/len(data)*100:.1f}%)")

# STEP 5: Run backtest
print("\nSTEP 5: Running backtest...")
print(f"  Entry: Score > 0.6 AND Regime = 1")
print(f"  Exit: After 14 days OR regime change")
print(f"  Costs: $0.03 spread, $0.65/contract commission")
print(f"  NO HEDGING")
print()

polygon = PolygonOptionsLoader()
trades = []
position = None

SPREAD = 0.03
COMMISSION_PER_CONTRACT = 0.65
SCORE_THRESHOLD = 0.6
HOLD_DAYS = 14
TARGET_DTE = 75

for idx in range(60, len(data)):  # Skip first 60 days (warmup)
    row = data.iloc[idx]
    trade_date = row['date']
    spot = row['close']
    regime = row['regime']
    score = row['profile_1_score']

    # Exit logic
    if position:
        days_held = (trade_date - position['entry_date']).days

        if days_held >= HOLD_DAYS or regime != 1:
            # Get exit prices
            call_mid = polygon.get_option_price(
                trade_date, position['strike'], position['expiry'], 'call', 'mid'
            )
            put_mid = polygon.get_option_price(
                trade_date, position['strike'], position['expiry'], 'put', 'mid'
            )

            if call_mid and put_mid:
                exit_price = (call_mid - SPREAD/2) + (put_mid - SPREAD/2)
                exit_proceeds = exit_price * 100
                gross = exit_proceeds - position['entry_cost']
                net = gross - (4 * COMMISSION_PER_CONTRACT)

                position['exit_date'] = trade_date
                position['exit_spot'] = spot
                position['net_pnl'] = net
                position['days_held'] = days_held
                trades.append(position)

                reason = "Hold period" if days_held >= HOLD_DAYS else "Regime change"
                spy_move = ((spot / position['entry_spot']) - 1) * 100
                print(f"EXIT  {len(trades):02d} [{trade_date}] {reason:15s} SPY {spy_move:+6.2f}%, "
                      f"{days_held:2d}d, P&L ${net:+8.2f}")

            position = None

    # Entry logic
    if not position and score > SCORE_THRESHOLD and regime == 1:
        strike = round(spot)

        # Third Friday expiry
        target = trade_date + timedelta(days=TARGET_DTE)
        first_day = date(target.year, target.month, 1)
        first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
        expiry = first_friday + timedelta(days=14)

        # Get prices
        call_mid = polygon.get_option_price(trade_date, strike, expiry, 'call', 'mid')
        put_mid = polygon.get_option_price(trade_date, strike, expiry, 'put', 'mid')

        if call_mid and put_mid:
            entry_price = (call_mid + SPREAD/2) + (put_mid + SPREAD/2)
            entry_cost = entry_price * 100
            dte_actual = (expiry - trade_date).days

            position = {
                'trade_id': f"Trade_{len(trades)+1:03d}",
                'entry_date': trade_date,
                'entry_spot': spot,
                'strike': strike,
                'expiry': expiry,
                'dte': dte_actual,
                'entry_cost': entry_cost,
                'score': score
            }

            print(f"ENTER {len(trades)+1:02d} [{trade_date}] SPY ${spot:.2f}, Score {score:.2f}, "
                  f"${strike} strike, {dte_actual}DTE")

# Results
print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)

if trades:
    df = pd.DataFrame(trades)
    total = df['net_pnl'].sum()
    winners = (df['net_pnl'] > 0).sum()

    print(f"\nTrades: {len(trades)}")
    print(f"Winners: {winners} ({winners/len(trades)*100:.1f}%)")
    print(f"Losers: {len(trades) - winners}")
    print(f"\nTotal P&L: ${total:,.2f}")
    print(f"Average: ${total/len(trades):.2f}/trade")

    if total > 0:
        print(f"\n✅ STRATEGY IS PROFITABLE (with real costs, no hedging)")
    else:
        print(f"\n❌ STRATEGY UNPROFITABLE")

    df.to_csv('clean_backtest_results.csv', index=False)
    print(f"\nSaved: clean_backtest_results.csv")
else:
    print("\n❌ NO TRADES")
