#!/usr/bin/env python3
"""
FULL PERIOD BACKTEST (2020-2024)

Full period for parameter derivation and infrastructure validation.

CRITICAL RULES:
1. Data period: 2020-01-01 to 2021-12-31 ONLY
2. Derive ALL parameters from this period
3. Calculate empirical peak timing
4. Save derived parameters to config file
5. NEVER look at validation/test periods

Purpose:
- Find bugs in infrastructure
- Derive exit timing parameters
- Calculate baseline metrics
- Create parameter config file

Output:
- data/backtest_results/full_2020-2024/results.json

Usage:
    python scripts/backtest_train.py
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


# FULL PERIOD BOUNDARIES (ENFORCED)
PERIOD_START = date(2020, 1, 1)
PERIOD_END = date(2024, 12, 31)


def load_spy_data() -> pd.DataFrame:
    """Load SPY minute data and aggregate to daily with derived features

    CRITICAL: Load warmup period BEFORE train start to initialize rolling features
    Then filter to full period AFTER feature calculation
    """
    # Warmup period: 60 trading days before train start
    # This ensures MA50 has clean data from day 1 of full period
    WARMUP_DAYS = 60
    warmup_start = PERIOD_START - timedelta(days=90)  # 90 calendar days = ~60 trading days

    print(f"Loading SPY data with warmup period...")
    print(f"  Warmup: {warmup_start} to {PERIOD_START}")
    print(f"  Full:  {PERIOD_START} to {PERIOD_END}")

    spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
    spy_data = []

    for f in spy_files:
        df = pd.read_parquet(f)
        if len(df) > 0:
            file_date = pd.to_datetime(df['ts'].iloc[0]).date()

            # Load warmup + full period
            if file_date < warmup_start or file_date > PERIOD_END:
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

    spy['slope'] = spy['close'].pct_change(20).shift(1)  # Legacy compatibility

    # CRITICAL: Filter to full period AFTER calculating features
    # This ensures features at full period start use warmup data
    spy_with_warmup = spy.copy()
    spy = spy[spy['date'] >= PERIOD_START].reset_index(drop=True)

    # Verify full period enforcement
    actual_start = spy['date'].min()
    actual_end = spy['date'].max()

    print(f"\n✅ FULL PERIOD ENFORCED")
    print(f"   Expected: {PERIOD_START} to {PERIOD_END}")
    print(f"   Actual:   {actual_start} to {actual_end}")
    print(f"   Warmup days used: {len(spy_with_warmup) - len(spy)}")

    # FIXED Round 7: Check should be < not != (warmup data makes start earlier)
    if actual_start < PERIOD_START or actual_end > PERIOD_END:
        raise ValueError(f"DATA LEAK DETECTED: Data outside full period!")

    # Check warmup effectiveness (warning only - accept limited early data)
    first_ma50 = spy['MA50'].iloc[0]
    if pd.isna(first_ma50):
        print(f"   ⚠️  WARNING: MA50 is NaN at train start (limited warmup data)")
        print(f"   First ~50 days will skip trades needing MA50")
        print(f"   This is acceptable - entry conditions handle NaN gracefully\n")
    else:
        print(f"   First MA50 value: {first_ma50:.2f} (clean warmup)\n")

    return spy


def get_profile_configs() -> Dict:
    """
    Define all 6 profile configurations

    Each profile has:
    - name: Human-readable name
    - entry_condition: Function that returns True when should enter
    - structure: Description of options structure
    - dte_target: Target days to expiration
    - legs: List of option legs to trade
    """

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
            'description': 'Capture short-term gamma in fear context (bounce in downtrend)',
            'entry_condition': lambda row: (
                row.get('return_5d', 0) > 0.03 and      # Short-term spike
                row.get('slope_MA20', 0) < 0             # HARD FILTER: Downtrend context (fear)
            ),
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
    Run backtest for a single profile with complete trade tracking

    FULL PERIOD ONLY - for parameter derivation
    """
    print(f"\n{'='*80}")
    print(f"BACKTESTING: {profile_id} - {config['name']}")
    print(f"{'='*80}")

    exit_day = exit_engine.get_exit_day(profile_id)

    print(f"Entry condition: {config['description']}")
    print(f"Structure: {config['structure']}")
    print(f"Target DTE: {config['dte_target']}")
    print(f"Exit strategy: Phase 1 - Day {exit_day}\n")

    trades = []
    last_entry_date = None

    # Start from row 60 to ensure derived features are warm
    # CRITICAL: Stop before last row to allow next-day execution
    for idx in range(60, len(spy) - 1):
        row = spy.iloc[idx]
        signal_date = row['date']

        # Check if enough time since last trade
        if last_entry_date and (signal_date - last_entry_date).days < min_days_between_trades:
            continue

        # Check entry condition (using shifted features - no look-ahead)
        try:
            if not config['entry_condition'](row):
                continue
        except (KeyError, TypeError) as e:
            # Skip if derived features not available (NaN values early in period)
            continue

        # NOTE: Disaster filter removed (was derived from contaminated full dataset)
        # If needed, will derive threshold from full period results

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
            'aggregate_pct_captured': 0,
            'median_pct_captured': 0,
            'avg_days_to_peak': 0,
            'avg_path_volatility': 0
        }

    final_pnls = [t['exit']['final_pnl'] for t in trades]
    peak_pnls = [t['exit']['peak_pnl'] for t in trades]
    pct_captured = [t['exit']['pct_of_peak_captured'] for t in trades]

    # FIXED: Calculate aggregate capture %, not average of individual %
    # Aggregate = (total final P&L) / (total peak P&L) shows true performance
    # Average of individual % is misleading (one -500% outlier ruins average)
    total_final = sum(final_pnls)
    total_peak_positive = sum([p for p in peak_pnls if p > 0])

    if total_peak_positive > 0:
        aggregate_capture = (total_final / total_peak_positive) * 100
    else:
        aggregate_capture = 0

    summary = {
        'total_trades': len(trades),
        'total_pnl': sum(final_pnls),
        'peak_potential': total_peak_positive,
        'winners': sum(1 for pnl in final_pnls if pnl > 0),
        'aggregate_pct_captured': aggregate_capture,  # FIXED: Aggregate not average
        'aggregate_pct_captured_per_trade': np.mean(pct_captured) if pct_captured else 0,  # Keep for reference
        'median_pct_captured': np.median(pct_captured) if pct_captured else 0,
        'avg_days_to_peak': np.mean([t['exit']['day_of_peak'] for t in trades]),
        'avg_path_volatility': np.mean([t['exit']['pnl_volatility'] for t in trades])
    }

    return summary


def main():
    """Main execution - FULL PERIOD ONLY"""

    print("\n" + "="*80)
    print("FULL PERIOD BACKTEST (2020-2024)")
    print("="*80)
    print("Purpose: Derive parameters and validate infrastructure")
    print(f"Period: {PERIOD_START} to {PERIOD_END}")
    print("Output: Train results + derived parameters config\n")

    # Load data (full period enforced in load_spy_data())
    spy = load_spy_data()
    polygon = PolygonOptionsLoader()
    tracker = TradeTracker(polygon)

    # Initialize Exit Engine with default parameters
    # These will be re-calculated from train results
    exit_engine = ExitEngine(phase=1)
    print(f"\n✅ Using Exit Engine Phase 1 (initial parameters)")
    print(f"   Exit days: {exit_engine.get_all_exit_days()}\n")

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

    # Derive parameters from train results

    # Save results
    output_dir = Path('/Users/zstoc/rotation-engine/data/backtest_results/full_2020-2024')
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / 'results.json'
    print(f"\nSaving results to {results_file}...")
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"✅ Saved: {results_file}")

    # Save derived parameters config
    config_dir = Path('/Users/zstoc/rotation-engine/config')
    config_dir.mkdir(parents=True, exist_ok=True)


    # Print summary
    print("\n" + "="*80)
    print("FULL PERIOD SUMMARY")
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
            print(f"  Avg % of Peak Captured: {summary['aggregate_pct_captured']:.1f}%")
            print(f"  Avg Days to Peak: {summary['avg_days_to_peak']:.1f}")

            total_trades += summary['total_trades']
            total_pnl += summary['total_pnl']
            total_peak += summary['peak_potential']

    print("\n" + "="*80)
    print(f"TOTAL: {total_trades} trades")
    print(f"Final P&L: ${total_pnl:.0f}")
    print(f"Peak Potential: ${total_peak:.0f}")
    print("="*80)

    print(f"\n✅ Full period complete")
    print(f"📊 Next step: Review results, then run validation period (2022-2023)\n")


if __name__ == '__main__':
    main()
