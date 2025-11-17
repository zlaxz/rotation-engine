#!/usr/bin/env python3
"""
Run Profile 1 (LDG) backtest WITHOUT delta hedging.

Goal: Test if the RAW strategy has edge before adding complexity.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
from datetime import date
from simple_backtester import SimpleBacktester

print("=" * 80)
print("PROFILE 1 (LDG) - SIMPLE BACKTEST (No Hedging)")
print("=" * 80)

# Load data and scores
print("\nLoading data...")
from src.data.loaders import load_spy_data
from src.regimes.classifier import RegimeClassifier
from src.profiles.detectors import ProfileDetectors

# Load SPY data (2020-2024)
spy_data = load_spy_data()
print(f"Loaded {len(spy_data)} days of SPY data")

# Classify regimes
print("\nClassifying regimes...")
classifier = RegimeClassifier()
spy_with_regimes = classifier.classify_period(spy_data)

# Compute profile scores
print("Computing profile scores...")
detector = ProfileDetectors()
full_data = detector.compute_all_profiles(spy_with_regimes)

print(f"Data ready: {full_data['date'].min()} to {full_data['date'].max()}")

# Run simple backtest
print("\n" + "=" * 80)
print("RUNNING BACKTEST")
print("=" * 80)
print("\nStrategy: Profile 1 (Long-Dated Gamma)")
print("Entry: Score > 0.6 AND Regime in [1, 3] (Trend Up, Compression)")
print("Exit: After 14 days OR regime change")
print("Position: ATM straddle, ~75 DTE")
print("NO DELTA HEDGING")
print()

backtester = SimpleBacktester(verbose=True)

results = backtester.run_straddle_strategy(
    data=full_data,
    score_col='profile_1_LDG',
    regime_col='regime',
    score_threshold=0.6,
    regime_filter=[1, 3],
    hold_days=14,
    target_dte=75
)

# Get trade summary
trade_summary = backtester.get_summary()

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)

if len(trade_summary) > 0:
    total_pnl = trade_summary['net_pnl'].sum()
    winners = (trade_summary['net_pnl'] > 0).sum()
    losers = (trade_summary['net_pnl'] < 0).sum()
    win_rate = winners / len(trade_summary) if len(trade_summary) > 0 else 0

    print(f"\nTrades: {len(trade_summary)}")
    print(f"Winners: {winners}")
    print(f"Losers: {losers}")
    print(f"Win rate: {win_rate*100:.1f}%")
    print(f"\nTotal P&L: ${total_pnl:,.2f}")
    print(f"Average P&L per trade: ${total_pnl / len(trade_summary):.2f}")

    # Calculate Sharpe (rough)
    if len(trade_summary) > 1:
        pnl_std = trade_summary['net_pnl'].std()
        avg_pnl = trade_summary['net_pnl'].mean()
        sharpe_estimate = (avg_pnl / pnl_std) * (252 ** 0.5) if pnl_std > 0 else 0
        print(f"Sharpe estimate: {sharpe_estimate:.2f}")

    # Top 5 trades
    print(f"\nTop 5 winning trades:")
    top_5 = trade_summary.nlargest(5, 'net_pnl')[['trade_id', 'entry_date', 'exit_date', 'spot_move_pct', 'net_pnl']]
    print(top_5.to_string(index=False))

    print(f"\nTop 5 losing trades:")
    bottom_5 = trade_summary.nsmallest(5, 'net_pnl')[['trade_id', 'entry_date', 'exit_date', 'spot_move_pct', 'net_pnl']]
    print(bottom_5.to_string(index=False))

    # Save results
    results.to_csv('simple_backtest_profile1_results.csv', index=False)
    trade_summary.to_csv('simple_backtest_profile1_trades.csv', index=False)
    print(f"\nResults saved to CSV files")

    print("\n" + "=" * 80)
    print("COMPARISON TO COMPLEX BACKTEST")
    print("=" * 80)
    print(f"Simple (no hedging):  ${total_pnl:,.2f}")
    print(f"Complex (with hedge): $-6,553.08 (from earlier)")
    print(f"Hedging cost impact: ${total_pnl - (-6553.08):,.2f}")

else:
    print("\n❌ No trades executed!")
    print("Check if data has required columns or if conditions are too strict")
