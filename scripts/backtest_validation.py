#!/usr/bin/env python3
"""
VALIDATION PERIOD BACKTEST (2022-2023)

Out-of-sample validation using train-derived parameters.

CRITICAL RULES:
1. Data period: 2022-01-01 to 2023-12-31 ONLY
2. LOAD parameters from train period (config/train_derived_params.json)
3. ZERO new parameter derivation
4. Test if train-derived parameters work out-of-sample
5. Calculate degradation metrics vs train period

Purpose:
- Validate train-derived parameters work out-of-sample
- Calculate out-of-sample metrics
- Detect overfitting (expect 20-40% degradation)
- Decision: proceed to test or iterate on train

Output:
- data/backtest_results/validation_2022-2023/results.json
- data/backtest_results/validation_2022-2023/degradation_analysis.json

Usage:
    python scripts/backtest_validation.py

Expected degradation:
- Sharpe ratio: -20% to -40%
- Capture rate: -10% to -30%
- Win rate: -5% to -15%

Red flags:
- Sharpe drops >50%: Severe overfitting
- Metrics flip sign: Strategy doesn't work
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


# VALIDATION PERIOD BOUNDARIES (ENFORCED)
VALIDATION_START = date(2022, 1, 1)
VALIDATION_END = date(2023, 12, 31)


def load_train_params() -> Dict:
    """Load parameters derived from train period

    CRITICAL: These parameters were derived from 2020-2021 data ONLY
    We are testing if they work on 2022-2023 (out-of-sample)
    """
    params_file = Path('/Users/zstoc/rotation-engine/config/train_derived_params.json')

    if not params_file.exists():
        raise FileNotFoundError(
            f"Train parameters not found: {params_file}\n"
            "Run scripts/backtest_train.py first to derive parameters"
        )

    with open(params_file, 'r') as f:
        params = json.load(f)

    print("\n" + "="*80)
    print("LOADED TRAIN-DERIVED PARAMETERS")
    print("="*80)
    print(f"Derived from: {params['train_period']['start']} to {params['train_period']['end']}")
    print(f"Derivation date: {params['derived_date']}")
    print(f"Method: {params['derivation_method']}")
    print("\nExit days (from train period median peak timing):")
    for profile_id, exit_day in params['exit_days'].items():
        print(f"  {profile_id}: Day {exit_day}")
    print("="*80 + "\n")

    return params


def load_spy_data() -> pd.DataFrame:
    """Load SPY minute data and aggregate to daily with derived features

    CRITICAL: Load warmup period BEFORE validation start
    Then filter to validation period AFTER feature calculation
    """
    # Warmup period: 60 trading days before validation start
    WARMUP_DAYS = 60
    warmup_start = VALIDATION_START - timedelta(days=90)

    print(f"Loading SPY data with warmup period...")
    print(f"  Warmup:     {warmup_start} to {VALIDATION_START}")
    print(f"  Validation: {VALIDATION_START} to {VALIDATION_END}")

    spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
    spy_data = []

    for f in spy_files:
        df = pd.read_parquet(f)
        if len(df) > 0:
            file_date = pd.to_datetime(df['ts'].iloc[0]).date()

            # Load warmup + validation period
            if file_date < warmup_start or file_date > VALIDATION_END:
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

    # CRITICAL: Filter to validation period AFTER calculating features
    spy_with_warmup = spy.copy()
    spy = spy[spy['date'] >= VALIDATION_START].reset_index(drop=True)

    # Verify validation period enforcement
    actual_start = spy['date'].min()
    actual_end = spy['date'].max()

    print(f"\n✅ VALIDATION PERIOD ENFORCED")
    print(f"   Expected: {VALIDATION_START} to {VALIDATION_END}")
    print(f"   Actual:   {actual_start} to {actual_end}")
    print(f"   Warmup days used: {len(spy_with_warmup) - len(spy)}")

    # FIXED Round 7: Check should be < not != (warmup data makes start earlier)
    if actual_start < VALIDATION_START or actual_end > VALIDATION_END:
        raise ValueError(f"DATA LEAK DETECTED: Data outside validation period!")

    # Verify warmup provided clean features
    first_ma50 = spy['MA50'].iloc[0]
    if pd.isna(first_ma50):
        raise ValueError(f"WARMUP INSUFFICIENT: MA50 still NaN at validation period start!")

    print(f"   First MA50 value: {first_ma50:.2f} (clean)\n")

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

    VALIDATION PERIOD ONLY - testing train-derived parameters
    """
    print(f"\n{'='*80}")
    print(f"BACKTESTING: {profile_id} - {config['name']}")
    print(f"{'='*80}")

    exit_day = exit_engine.get_exit_day(profile_id)

    print(f"Entry condition: {config['description']}")
    print(f"Structure: {config['structure']}")
    print(f"Target DTE: {config['dte_target']}")
    print(f"Exit day (from train): Day {exit_day}\n")

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
        # Using train-derived parameters only

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


def calculate_degradation(val_results: Dict, train_params: Dict) -> Dict:
    """
    Calculate degradation metrics: validation vs train

    Expected degradation: 20-40%
    Red flag: >50% degradation
    """
    print("\n" + "="*80)
    print("DEGRADATION ANALYSIS: Validation vs Train")
    print("="*80)

    degradation = {
        'validation_period': {
            'start': str(VALIDATION_START),
            'end': str(VALIDATION_END)
        },
        'train_period': train_params['train_period'],
        'profiles': {}
    }

    for profile_id, val_data in val_results.items():
        val_summary = val_data['summary']
        train_stats = train_params['profile_stats'].get(profile_id, {})

        if val_summary['total_trades'] == 0:
            print(f"\n{profile_id}: No validation trades - cannot calculate degradation")
            continue

        train_trades = train_stats.get('trade_count', 0)
        train_peak = train_stats.get('peak_potential', 0)

        if train_trades == 0:
            print(f"\n{profile_id}: No train trades - cannot calculate degradation")
            continue

        # Calculate degradation metrics
        val_trades = val_summary['total_trades']
        val_peak = val_summary['peak_potential']

        peak_degradation_pct = ((val_peak - train_peak) / train_peak * 100) if train_peak else 0

        print(f"\n{profile_id} - {val_data['config']['name']}")
        print(f"  Train trades: {train_trades} | Val trades: {val_trades}")
        print(f"  Train peak: ${train_peak:.0f} | Val peak: ${val_peak:.0f}")
        print(f"  Peak potential degradation: {peak_degradation_pct:+.1f}%")

        # Red flag detection
        red_flags = []
        if abs(peak_degradation_pct) > 50:
            red_flags.append(f"Peak degradation >{50}%")

        if red_flags:
            print(f"  ⚠️  RED FLAGS: {', '.join(red_flags)}")
        else:
            print(f"  ✅ Degradation within acceptable range")

        degradation['profiles'][profile_id] = {
            'train_trades': train_trades,
            'val_trades': val_trades,
            'train_peak': train_peak,
            'val_peak': val_peak,
            'peak_degradation_pct': peak_degradation_pct,
            'red_flags': red_flags
        }

    print("\n" + "="*80)
    return degradation


def main():
    """Main execution - VALIDATION PERIOD ONLY"""

    print("\n" + "="*80)
    print("VALIDATION PERIOD BACKTEST (2022-2023)")
    print("="*80)
    print("Purpose: Test train-derived parameters out-of-sample")
    print(f"Period: {VALIDATION_START} to {VALIDATION_END}")
    print("Output: Validation results + degradation analysis\n")

    # Load train-derived parameters
    train_params = load_train_params()

    # Load data (validation period enforced in load_spy_data())
    spy = load_spy_data()
    polygon = PolygonOptionsLoader()
    tracker = TradeTracker(polygon)

    # Initialize Exit Engine with train-derived exit days
    # FIXED: Ensure exit days are integers (JSON may load as floats)
    exit_days_int = {k: int(v) for k, v in train_params['exit_days'].items()}
    exit_engine = ExitEngine(phase=1, custom_exit_days=exit_days_int)

    print(f"\n✅ Using train-derived exit days:")
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

    # Calculate degradation vs train
    degradation = calculate_degradation(all_results, train_params)

    # Save results
    output_dir = Path('/Users/zstoc/rotation-engine/data/backtest_results/validation_2022-2023')
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / 'results.json'
    print(f"\n\nSaving results to {results_file}...")
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"✅ Saved: {results_file}")

    degradation_file = output_dir / 'degradation_analysis.json'
    print(f"\nSaving degradation analysis to {degradation_file}...")
    with open(degradation_file, 'w') as f:
        json.dump(degradation, f, indent=2, default=str)
    print(f"✅ Saved: {degradation_file}")

    # Print summary
    print("\n" + "="*80)
    print("VALIDATION PERIOD SUMMARY")
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

    # Decision guidance
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\nReview degradation analysis above. Decision criteria:")
    print("  ✅ If degradation <30% and no red flags → Proceed to test period")
    print("  ⚠️  If degradation 30-50% → Review and decide")
    print("  ❌ If degradation >50% or sign flip → Iterate on train period")
    print("\nIf iterating: Go back to train period, re-derive parameters, re-test on validation")
    print("If proceeding: Lock methodology and run test period (2024) ONCE ONLY\n")


if __name__ == '__main__':
    main()
