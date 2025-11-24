#!/usr/bin/env python3
"""
Profile Backtesting with Complete Trade Tracking

Production-grade backtest that captures complete trade lifecycle:
- All 6 profiles
- 14-day tracking windows
- Daily path with Greeks and market conditions
- Output: Structured JSON ready for exit strategy development

Usage:
    python scripts/backtest_with_full_tracking.py
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, timedelta
import json
from pathlib import Path
import glob
from typing import Dict, List

from src.data.polygon_options import PolygonOptionsLoader
from src.analysis.trade_tracker import TradeTracker
from src.trading.exit_engine import ExitEngine


def load_spy_data() -> pd.DataFrame:
    """Load SPY minute data and aggregate to daily with derived features"""
    print("Loading SPY data...")

    spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
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

    # Realized volatility (annualized)
    spy['RV5'] = spy['return_1d'].rolling(5).std() * np.sqrt(252)
    spy['RV10'] = spy['return_1d'].rolling(10).std() * np.sqrt(252)
    spy['RV20'] = spy['return_1d'].rolling(20).std() * np.sqrt(252)

    # Average True Range
    spy['HL'] = spy['high'] - spy['low']
    spy['ATR5'] = spy['HL'].rolling(5).mean()
    spy['ATR10'] = spy['HL'].rolling(10).mean()

    spy['slope'] = spy['close'].pct_change(20)  # Legacy compatibility

    print(f"Loaded {len(spy)} days from {spy['date'].min()} to {spy['date'].max()}\n")

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
            'entry_condition': lambda row: row.get('return_20d', 0) > 0.02,  # Enter on +2% 20-day move
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
            'entry_condition': lambda row: row.get('return_5d', 0) > 0.03,  # Enter on +3% 5-day move
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
            'entry_condition': lambda row: abs(row.get('return_20d', 0)) < 0.01,  # Enter when flat
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
            'entry_condition': lambda row: row.get('return_20d', 0) > 0.02,  # Enter on uptrend
            'structure': 'Long ATM Call',
            'dte_target': 60,
            'legs': [
                {'type': 'call', 'qty': 1}
            ]
        },

        'Profile_5_SKEW': {
            'name': 'Skew Convexity',
            'description': 'Capture downside skew - dips in uptrends, not falling knives',
            'entry_condition': lambda row: (
                row.get('return_10d', 0) < -0.02 and  # Down move
                row.get('slope_MA20', 0) > 0.005       # But in uptrend (FIXED: was missing)
            ),
            'structure': 'Long OTM Put (5% OTM)',
            'dte_target': 45,
            'legs': [
                {'type': 'put', 'qty': 1}
            ]
        },

        'Profile_6_VOV': {
            'name': 'Vol-of-Vol Convexity',
            'description': 'Capture volatility regime changes - buy in compression',
            'entry_condition': lambda row: row.get('RV10', 0) < row.get('RV20', 0),  # FIXED: Buy compressed vol (was >)
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

    Uses monthly expiration cycle (3rd Friday)
    """
    target_date = entry_date + timedelta(days=dte_target)

    # Find first day of target month
    first_day = date(target_date.year, target_date.month, 1)

    # Find first Friday (weekday 4)
    days_to_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=days_to_friday)

    # Third Friday is 14 days after first Friday
    third_friday = first_friday + timedelta(days=14)

    return third_friday


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

    Args:
        profile_id: Profile identifier (e.g., 'Profile_1_LDG')
        config: Profile configuration dict
        spy: SPY DataFrame with derived features
        tracker: TradeTracker instance
        min_days_between_trades: Minimum days between entries (prevents over-trading)

    Returns:
        List of complete trade records
    """
    print(f"\n{'='*80}")
    print(f"BACKTESTING: {profile_id} - {config['name']}")
    print(f"{'='*80}")
    # Phase 1: Get profile-specific exit day
    exit_day = exit_engine.get_exit_day(profile_id)

    print(f"Entry condition: {config['description']}")
    print(f"Structure: {config['structure']}")
    print(f"Target DTE: {config['dte_target']}")
    print(f"Exit strategy: Phase 1 - Day {exit_day} (empirical peak timing)\n")

    trades = []
    last_entry_date = None

    # Start from row 60 to ensure derived features are warm
    for idx in range(60, len(spy)):
        row = spy.iloc[idx]
        entry_date = row['date']

        # Check if enough time since last trade
        if last_entry_date and (entry_date - last_entry_date).days < min_days_between_trades:
            continue

        # Check entry condition
        try:
            if not config['entry_condition'](row):
                continue
        except Exception as e:
            # Skip if derived features not available
            continue

        # DISASTER FILTER: Skip high-vol environments (data-driven from agent analysis)
        # Agent 4 found: RV5 > 0.22 eliminates 31.8% of worst losers vs 15.2% of winners
        if row.get('RV5', 0) > 0.22:
            continue

        # Entry triggered - set up position
        spot = row['close']
        strike = round(spot)

        # Adjust strike for OTM positions
        if 'OTM' in config['structure']:
            if 'Put' in config['structure']:
                strike = round(spot * 0.95)  # 5% OTM put

        expiry = get_expiry_for_dte(entry_date, config['dte_target'])

        position = {
            'profile': profile_id,
            'structure': config['structure'],
            'strike': strike,
            'expiry': expiry,
            'legs': config['legs']
        }

        # Track complete trade (using profile-specific exit day)
        trade_record = tracker.track_trade(
            entry_date=entry_date,
            position=position,
            spy_data=spy,
            max_days=exit_day
        )

        if trade_record:
            trades.append(trade_record)
            last_entry_date = entry_date

            # Progress update every 10 trades
            if len(trades) % 10 == 0:
                print(f"  {len(trades)} trades tracked...")

    print(f"\n✅ Complete: {len(trades)} trades tracked with full path data")

    return trades


def analyze_trades(trades: List[Dict]) -> Dict:
    """Calculate summary statistics from tracked trades"""

    if not trades:
        return {
            'total_trades': 0,
            'total_pnl': 0,
            'peak_potential': 0,
            'avg_pct_captured': 0
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


def main():
    """Main execution"""

    print("\n" + "="*80)
    print("PROFILE BACKTESTING WITH COMPLETE TRADE TRACKING")
    print("="*80)
    print("Chief Quant Mode: Production-grade tracking system")
    print("- 14-day tracking windows")
    print("- Daily Greeks calculation")
    print("- Market conditions at each point")
    print("- Peak timing and capture analytics\n")

    # Load data
    spy = load_spy_data()
    polygon = PolygonOptionsLoader()
    tracker = TradeTracker(polygon)

    # Phase 1: Initialize Exit Engine with empirical peak timing
    exit_engine = ExitEngine(phase=1)
    print(f"\n✅ Using Exit Engine Phase 1 (time-based exits)")
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

    # Save results
    output_dir = Path('/Users/zstoc/rotation-engine/data/backtest_results')
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / 'full_tracking_results.json'

    # Convert dates to strings for JSON serialization
    print(f"\nSaving results to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"✅ Saved: {output_file}")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY - ALL PROFILES")
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
            print(f"  Avg Days to Peak: {summary['avg_days_to_peak']:.1f}")
            print(f"  Avg Path Volatility: ${summary['avg_path_volatility']:.0f}")

            total_trades += summary['total_trades']
            total_pnl += summary['total_pnl']
            total_peak += summary['peak_potential']

    print("\n" + "="*80)
    print(f"TOTAL: {total_trades} trades")
    print(f"Final P&L: ${total_pnl:.0f}")
    print(f"Peak Potential: ${total_peak:.0f}")
    print(f"Opportunity: ${total_peak - total_pnl:.0f} left on table")
    print("="*80)

    print(f"\n✅ Complete trade tracking data ready for exit strategy development")
    print(f"📊 Next step: Analyze path patterns to design dynamic exits\n")


if __name__ == '__main__':
    main()
