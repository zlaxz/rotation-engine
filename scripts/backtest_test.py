#!/usr/bin/env python3
"""
TEST PERIOD BACKTEST (2024)

FINAL HOLDOUT VALIDATION - RUN ONCE ONLY

CRITICAL RULES:
1. Data period: 2024-01-01 to 2024-12-31 ONLY
2. LOAD locked parameters from train/validation
3. RUN ONCE ONLY - no iterations after seeing results
4. Accept results (good or bad)
5. This is what we present to investors

Purpose:
- Final out-of-sample validation
- True performance estimate
- Investor-ready results
- Decision: deploy or abandon

Output:
- data/backtest_results/test_2024/results.json
- data/backtest_results/test_2024/final_analysis.json

⚠️  WARNING ⚠️
This script should be run ONCE ONLY after methodology is locked.
Looking at test results contaminates the holdout set.
NO ITERATIONS allowed after running this script.

Expected behavior:
- Test metrics within 20-30% of validation metrics
- No sign flips
- Consistent degradation pattern

Decision criteria:
- If test passes: Lock methodology, prepare for deployment
- If test fails: Methodology doesn't work, abandon or restart research

Usage:
    python scripts/backtest_test.py

    Only run after:
    1. Train period completed
    2. Validation period passed
    3. Methodology locked
    4. Ready to accept final results
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import glob
from typing import Dict, List

from src.data.polygon_options import PolygonOptionsLoader
from src.analysis.trade_tracker import TradeTracker
from src.trading.exit_engine import ExitEngine


# TEST PERIOD BOUNDARIES (ENFORCED)
TEST_START = date(2024, 1, 1)
TEST_END = date(2024, 12, 31)


def load_locked_params() -> Dict:
    """Load locked parameters from train period

    CRITICAL: These parameters were:
    1. Derived from train period (2020-2021)
    2. Validated on validation period (2022-2023)
    3. Now being tested on final holdout (2024)

    This is the FINAL test - no iterations allowed after this
    """
    params_file = Path('/Users/zstoc/rotation-engine/config/train_derived_params.json')

    if not params_file.exists():
        raise FileNotFoundError(
            f"Locked parameters not found: {params_file}\n"
            "Run scripts/backtest_train.py and backtest_validation.py first"
        )

    with open(params_file, 'r') as f:
        params = json.load(f)

    print("\n" + "="*80)
    print("LOADED LOCKED PARAMETERS (FINAL TEST)")
    print("="*80)
    print(f"⚠️  WARNING: This is the FINAL HOLDOUT TEST")
    print(f"⚠️  NO ITERATIONS allowed after seeing these results\n")
    print(f"Derived from: {params['train_period']['start']} to {params['train_period']['end']}")
    print(f"Derivation date: {params['derived_date']}")
    print(f"Method: {params['derivation_method']}")
    print("\nLocked exit days:")
    for profile_id, exit_day in params['exit_days'].items():
        print(f"  {profile_id}: Day {exit_day}")
    print("="*80 + "\n")

    return params


def load_spy_data() -> pd.DataFrame:
    """Load SPY minute data and aggregate to daily with derived features

    CRITICAL: Load warmup period BEFORE test start
    Then filter to test period AFTER feature calculation
    """
    # Warmup period: 60 trading days before test start
    WARMUP_DAYS = 60
    warmup_start = TEST_START - timedelta(days=90)

    print(f"Loading SPY data with warmup period...")
    print(f"  Warmup: {warmup_start} to {TEST_START}")
    print(f"  Test:   {TEST_START} to {TEST_END}")

    spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
    spy_data = []

    for f in spy_files:
        df = pd.read_parquet(f)
        if len(df) > 0:
            file_date = pd.to_datetime(df['ts'].iloc[0]).date()

            # Load warmup + test period
            if file_date < warmup_start or file_date > TEST_END:
                continue

            spy_data.append({
                'date': file_date,
                'open': df['open'].iloc[0],
                'high': df['high'].max(),
                'low': df['low'].min(),
                'close': df['close'].iloc[-1],
                'volume': df['volume'].sum()
            })

    spy = pd.DataFrame(spy_data)

    # Validate data loaded successfully
    if len(spy) == 0:
        raise ValueError(
            "CRITICAL: No SPY data loaded!\n"
            "Check:\n"
            "1. Data drive mounted: /Volumes/VelocityData/\n"
            "2. Path exists: /Volumes/VelocityData/velocity_om/parquet/stock/SPY/\n"
            "3. Date range has data: Need data from warmup period onwards"
        )

    spy = spy.sort_values('date').reset_index(drop=True)

    # Calculate derived features
    # CRITICAL: Shift by 1 to avoid look-ahead bias
    # At market open on day T, we only know day T-1's close
    # Entry conditions evaluate features, then enter at day T open (simulated as close)

    spy['return_1d'] = spy['close'].pct_change().shift(1)
    spy['return_5d'] = spy['close'].pct_change(5).shift(1)
    spy['return_10d'] = spy['close'].pct_change(10).shift(1)
    spy['return_20d'] = spy['close'].pct_change(20).shift(1)

    spy['MA20'] = spy['close'].shift(1).rolling(20).mean()
    spy['MA50'] = spy['close'].shift(1).rolling(50).mean()
    # MA already shifted, so pct_change is backward-looking (no extra shift needed)
    spy['slope_MA20'] = spy['MA20'].pct_change(20)
    spy['slope_MA50'] = spy['MA50'].pct_change(50)

    # Realized volatility (annualized)
    # Use shifted returns so RV doesn't include today's move
    spy['RV5'] = spy['return_1d'].rolling(5).std() * np.sqrt(252)
    spy['RV10'] = spy['return_1d'].rolling(10).std() * np.sqrt(252)
    spy['RV20'] = spy['return_1d'].rolling(20).std() * np.sqrt(252)

    # Average True Range
    spy['HL'] = spy['high'] - spy['low']
    spy['ATR5'] = spy['HL'].shift(1).rolling(5).mean()
    spy['ATR10'] = spy['HL'].shift(1).rolling(10).mean()

    spy['slope'] = spy['close'].pct_change(20).shift(1)

    # CRITICAL: Filter to test period AFTER calculating features
    spy_with_warmup = spy.copy()
    spy = spy[spy['date'] >= TEST_START].reset_index(drop=True)

    # Verify test period enforcement
    actual_start = spy['date'].min()
    actual_end = spy['date'].max()

    print(f"\n✅ TEST PERIOD ENFORCED")
    print(f"   Expected: {TEST_START} to {TEST_END}")
    print(f"   Actual:   {actual_start} to {actual_end}")
    print(f"   Warmup days used: {len(spy_with_warmup) - len(spy)}")

    # FIXED Round 7: Check should be < not != (warmup data makes start earlier)
    if actual_start < TEST_START or actual_end > TEST_END:
        raise ValueError(f"DATA LEAK DETECTED: Data outside test period!")

    # Check warmup effectiveness (warning only)
    first_ma50 = spy['MA50'].iloc[0]
    if pd.isna(first_ma50):
        print(f"   ⚠️  WARNING: MA50 is NaN at test start")
        print(f"   First ~50 days will skip trades needing MA50\n")
    else:
        print(f"   First MA50 value: {first_ma50:.2f} (clean warmup)\n")

    return spy


def get_profile_configs() -> Dict:
    """Define all 6 profile configurations"""

    profiles = {
        'Profile_1_LDG': {
            'name': 'Long-Dated Gamma',
            'description': 'Long gamma in uptrends with extended DTE',
            'entry_condition': lambda row: row.get('return_20d', 0) > 0.02,
            'structure': 'Long ATM Straddle',
            'dte_target': 75,
            'legs': [
                {'type': 'call', 'qty': 1},
                {'type': 'put', 'qty': 1}
            ]
        },

        'Profile_2_SDG': {
            'name': 'Short-Dated Gamma Spike',
            'description': 'Capture short-term gamma in momentum',
            'entry_condition': lambda row: row.get('return_5d', 0) > 0.03,
            'structure': 'Long ATM Straddle',
            'dte_target': 7,
            'legs': [
                {'type': 'call', 'qty': 1},
                {'type': 'put', 'qty': 1}
            ]
        },

        'Profile_3_CHARM': {
            'name': 'Charm/Decay Dominance',
            'description': 'Sell premium in sideways markets',
            'entry_condition': lambda row: abs(row.get('return_20d', 0)) < 0.01,
            'structure': 'Short ATM Straddle',
            'dte_target': 30,
            'legs': [
                {'type': 'call', 'qty': -1},
                {'type': 'put', 'qty': -1}
            ]
        },

        'Profile_4_VANNA': {
            'name': 'Vanna (Vol-Spot Correlation)',
            'description': 'Long calls in uptrends (positive vanna exposure)',
            'entry_condition': lambda row: row.get('return_20d', 0) > 0.02,
            'structure': 'Long ATM Call',
            'dte_target': 60,
            'legs': [
                {'type': 'call', 'qty': 1}
            ]
        },

        'Profile_5_SKEW': {
            'name': 'Skew Convexity',
            'description': 'Capture downside skew - dips in uptrends',
            'entry_condition': lambda row: (
                row.get('return_10d', 0) < -0.02 and
                row.get('slope_MA20', 0) > 0.005
            ),
            'structure': 'Long OTM Put (5% OTM)',
            'dte_target': 45,
            'legs': [
                {'type': 'put', 'qty': 1}
            ]
        },

        'Profile_6_VOV': {
            'name': 'Vol-of-Vol Convexity',
            'description': 'Capture volatility regime changes',
            'entry_condition': lambda row: row.get('RV10', 0) < row.get('RV20', 0),
            'structure': 'Long ATM Straddle',
            'dte_target': 30,
            'legs': [
                {'type': 'call', 'qty': 1},
                {'type': 'put', 'qty': 1}
            ]
        }
    }

    return profiles


def get_expiry_for_dte(entry_date: date, dte_target: int) -> date:
    """
    Calculate appropriate expiry date for target DTE

    SPY has weekly expirations (every Friday).
    Find Friday closest to entry_date + dte_target days.
    """
    target_date = entry_date + timedelta(days=dte_target)

    # Find next Friday from target date
    days_to_friday = (4 - target_date.weekday()) % 7
    if days_to_friday == 0:
        # Target is Friday
        expiry = target_date
    else:
        # Find nearest Friday (could be before or after target)
        next_friday = target_date + timedelta(days=days_to_friday)
        prev_friday = next_friday - timedelta(days=7)

        # Choose Friday closer to target
        if abs((next_friday - target_date).days) < abs((prev_friday - target_date).days):
            expiry = next_friday
        else:
            expiry = prev_friday

    return expiry


def run_profile_backtest(
    profile_id: str,
    config: Dict,
    spy: pd.DataFrame,
    tracker: TradeTracker,
    exit_engine: ExitEngine,
    min_days_between_trades: int = 7
) -> List[Dict]:
    """
    Run backtest for a single profile

    TEST PERIOD ONLY - final holdout validation
    """
    print(f"\n{'='*80}")
    print(f"BACKTESTING: {profile_id} - {config['name']}")
    print(f"{'='*80}")

    exit_day = exit_engine.get_exit_day(profile_id)

    print(f"Entry condition: {config['description']}")
    print(f"Structure: {config['structure']}")
    print(f"Target DTE: {config['dte_target']}")
    print(f"Exit day (locked from train): Day {exit_day}\n")

    trades = []
    last_entry_date = None

    # CRITICAL: Stop before last row to allow next-day execution
    for idx in range(60, len(spy) - 1):
        row = spy.iloc[idx]
        signal_date = row['date']

        if last_entry_date and (signal_date - last_entry_date).days < min_days_between_trades:
            continue

        try:
            if not config['entry_condition'](row):
                continue
        except (KeyError, TypeError) as e:
            # Skip if derived features not available
            continue

        # NOTE: Disaster filter removed (was derived from contaminated full dataset)
        # Using locked parameters from train period only

        # Entry triggered at end of day idx
        # Execute at open of next day (idx + 1)
        next_day = spy.iloc[idx + 1]
        entry_date = next_day['date']
        spot = next_day['open']  # FIXED: Use next day's open, not current close
        expiry = get_expiry_for_dte(entry_date, config['dte_target'])

        # Calculate strike based on profile structure
        if profile_id == 'Profile_5_SKEW':
            # 5% OTM put: strike below spot
            strike = round(spot * 0.95)
        else:
            # ATM for all other profiles
            strike = round(spot)

        print(f"ENTRY: {entry_date} | SPY={spot:.2f} | Strike={strike} | Expiry={expiry}")

        # Build position dict matching TradeTracker API
        position = {
            'profile': profile_id,
            'structure': config['structure'],
            'strike': strike,
            'expiry': expiry,
            'legs': config['legs']
        }

        # Track trade for 14 days (pass spy_data as required by TradeTracker)
        trade_data = tracker.track_trade(
            entry_date=entry_date,
            position=position,
            spy_data=spy,
            max_days=14,
            regime_data=None
        )

        if trade_data:
            trade_data['profile_id'] = profile_id
            trade_data['profile_name'] = config['name']
            trades.append(trade_data)
            last_entry_date = entry_date

    print(f"✅ Completed: {len(trades)} trades\n")
    return trades


def analyze_trades(trades: List[Dict]) -> Dict:
    """Calculate summary statistics for trades"""
    if not trades:
        return {
            'total_trades': 0,
            'total_pnl': 0,
            'peak_potential': 0,
            'winners': 0,
            'avg_pct_captured': 0,
            'median_pct_captured': 0,
            'avg_days_to_peak': 0,
            'avg_path_volatility': 0
        }

    final_pnls = [t['exit']['final_pnl'] for t in trades]
    peak_pnls = [t['exit']['peak_pnl'] for t in trades]
    pct_captured = [t['exit']['pct_of_peak_captured'] for t in trades]

    summary = {
        'total_trades': len(trades),
        'total_pnl': sum(final_pnls),
        'peak_potential': sum([p for p in peak_pnls if p > 0]),
        'winners': sum(1 for pnl in final_pnls if pnl > 0),
        'avg_pct_captured': np.mean(pct_captured) if pct_captured else 0,
        'median_pct_captured': np.median(pct_captured) if pct_captured else 0,
        'avg_days_to_peak': np.mean([t['exit']['day_of_peak'] for t in trades]),
        'avg_path_volatility': np.mean([t['exit']['pnl_volatility'] for t in trades])
    }

    return summary


def calculate_final_analysis(test_results: Dict, locked_params: Dict) -> Dict:
    """
    Final analysis: Test vs Train

    This is the FINAL verdict on the methodology
    """
    print("\n" + "="*80)
    print("FINAL ANALYSIS: Test vs Train")
    print("="*80)

    analysis = {
        'test_period': {
            'start': str(TEST_START),
            'end': str(TEST_END)
        },
        'train_period': locked_params['train_period'],
        'methodology_locked': locked_params['derived_date'],
        'profiles': {},
        'verdict': None
    }

    total_test_trades = 0
    total_train_trades = 0

    for profile_id, test_data in test_results.items():
        test_summary = test_data['summary']
        train_stats = locked_params['profile_stats'].get(profile_id, {})

        if test_summary['total_trades'] == 0:
            print(f"\n{profile_id}: No test trades")
            continue

        train_trades = train_stats.get('trade_count', 0)
        train_peak = train_stats.get('peak_potential', 0)

        test_trades = test_summary['total_trades']
        test_peak = test_summary['peak_potential']

        peak_change_pct = ((test_peak - train_peak) / train_peak * 100) if train_peak else 0

        print(f"\n{profile_id} - {test_data['config']['name']}")
        print(f"  Train trades: {train_trades} | Test trades: {test_trades}")
        print(f"  Train peak: ${train_peak:.0f} | Test peak: ${test_peak:.0f}")
        print(f"  Change: {peak_change_pct:+.1f}%")

        total_test_trades += test_trades
        total_train_trades += train_trades

        analysis['profiles'][profile_id] = {
            'train_trades': train_trades,
            'test_trades': test_trades,
            'train_peak': train_peak,
            'test_peak': test_peak,
            'change_pct': peak_change_pct
        }

    # Overall verdict
    print("\n" + "="*80)
    print("FINAL VERDICT")
    print("="*80)

    if total_test_trades == 0:
        verdict = "INSUFFICIENT DATA - No test trades executed"
    elif total_test_trades < total_train_trades * 0.3:
        verdict = "INSUFFICIENT SAMPLE - Test period too sparse"
    else:
        verdict = "TEST COMPLETE - Results accepted (no further iterations allowed)"

    print(f"\n{verdict}\n")
    print("⚠️  REMINDER: NO ITERATIONS allowed after viewing test results")
    print("⚠️  These results are FINAL\n")

    analysis['verdict'] = verdict
    analysis['total_test_trades'] = total_test_trades
    analysis['total_train_trades'] = total_train_trades

    print("="*80)
    return analysis


def main():
    """Main execution - TEST PERIOD ONLY (FINAL HOLDOUT)"""

    print("\n" + "="*80)
    print("⚠️  FINAL HOLDOUT TEST (2024) ⚠️")
    print("="*80)
    print("⚠️  WARNING: This is the FINAL TEST")
    print("⚠️  NO ITERATIONS allowed after seeing results")
    print("⚠️  Results must be accepted (good or bad)\n")
    print(f"Period: {TEST_START} to {TEST_END}")
    print("Output: Final test results + verdict\n")

    input("Press Enter to continue with FINAL TEST (or Ctrl+C to abort)...")

    # Load locked parameters
    locked_params = load_locked_params()

    # Load data (test period enforced in load_spy_data())
    spy = load_spy_data()
    polygon = PolygonOptionsLoader()
    tracker = TradeTracker(polygon)

    # Initialize Exit Engine with locked exit days
    # FIXED: Ensure exit days are integers (JSON may load as floats)
    exit_days_int = {k: int(v) for k, v in locked_params['exit_days'].items()}
    exit_engine = ExitEngine(phase=1, custom_exit_days=exit_days_int)

    print(f"\n✅ Using locked exit days:")
    for profile_id, exit_day in exit_engine.exit_days.items():
        print(f"   {profile_id}: Day {exit_day}")
    print()

    # Get profile configs
    profiles = get_profile_configs()

    # Run backtests
    all_results = {}

    for profile_id, config in profiles.items():
        trades = run_profile_backtest(profile_id, config, spy, tracker, exit_engine)
        summary = analyze_trades(trades)

        all_results[profile_id] = {
            'config': {k: v for k, v in config.items() if k != 'entry_condition'},
            'summary': summary,
            'trades': trades
        }

    # Calculate final analysis
    final_analysis = calculate_final_analysis(all_results, locked_params)

    # Save results
    output_dir = Path('/Users/zstoc/rotation-engine/data/backtest_results/test_2024')
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / 'results.json'
    print(f"\n\nSaving results to {results_file}...")
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"✅ Saved: {results_file}")

    analysis_file = output_dir / 'final_analysis.json'
    print(f"\nSaving final analysis to {analysis_file}...")
    with open(analysis_file, 'w') as f:
        json.dump(final_analysis, f, indent=2, default=str)
    print(f"✅ Saved: {analysis_file}")

    # Print summary
    print("\n" + "="*80)
    print("TEST PERIOD SUMMARY (FINAL)")
    print("="*80)

    total_trades = 0
    total_pnl = 0
    total_peak = 0

    for profile_id, results in all_results.items():
        summary = results['summary']
        name = results['config']['name']

        if summary['total_trades'] > 0:
            print(f"\n{profile_id} - {name}")
            print(f"  Trades: {summary['total_trades']}")
            print(f"  Final P&L: ${summary['total_pnl']:.0f}")
            print(f"  Peak Potential: ${summary['peak_potential']:.0f}")
            print(f"  Winners: {summary['winners']} ({summary['winners']/summary['total_trades']*100:.1f}%)")
            print(f"  Avg % of Peak Captured: {summary['avg_pct_captured']:.1f}%")

            total_trades += summary['total_trades']
            total_pnl += summary['total_pnl']
            total_peak += summary['peak_potential']

    print("\n" + "="*80)
    print(f"TOTAL: {total_trades} trades")
    print(f"Final P&L: ${total_pnl:.0f}")
    print(f"Peak Potential: ${total_peak:.0f}")
    print("="*80)

    # Final decision guidance
    print("\n" + "="*80)
    print("⚠️  FINAL REMINDER ⚠️")
    print("="*80)
    print("\nYou have now viewed the TEST PERIOD results.")
    print("NO FURTHER ITERATIONS are allowed.")
    print("\nThese results must be accepted as-is.")
    print("\nDecision options:")
    print("  1. Deploy methodology if results acceptable")
    print("  2. Abandon methodology if results unacceptable")
    print("  3. Start completely new research (fresh train/val/test)")
    print("\nDO NOT iterate on test period.")
    print("DO NOT adjust parameters based on test results.")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
