#!/usr/bin/env python3
"""
Intraday Profile Backtesting with 15-Minute Bar Tracking

Extends the daily backtest framework to track trades with 15-minute granularity.
Uses the same 604 trades from daily backtest but tracks intraday P&L paths.

Purpose:
- Identify when peaks occur during the day (morning vs afternoon vs EOD)
- Measure how long peaks last (minutes vs hours)
- Analyze intraday patterns by profile
- Design intelligent exit rules based on intraday timing

Usage:
    python scripts/backtest_intraday_15min.py
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta, time
import json
from pathlib import Path
import glob
from typing import Dict, List, Optional

from src.data.polygon_options import PolygonOptionsLoader


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

    Same as daily backtest - reusing validated entry conditions
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
    """Calculate appropriate expiry date for target DTE (3rd Friday)"""
    target_date = entry_date + timedelta(days=dte_target)

    # Find first day of target month
    first_day = date(target_date.year, target_date.month, 1)

    # Find first Friday (weekday 4)
    days_to_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=days_to_friday)

    # Third Friday is 14 days after first Friday
    third_friday = first_friday + timedelta(days=14)

    return third_friday


def track_trade_intraday(
    entry_date: date,
    strike: float,
    expiry: date,
    legs: List[Dict],
    polygon: PolygonOptionsLoader,
    max_days: int = 14
) -> Optional[Dict]:
    """
    Track a single trade with 15-minute bar granularity

    Args:
        entry_date: Date trade was entered
        strike: Strike price
        expiry: Option expiry date
        legs: List of option legs [{'type': 'call'/'put', 'qty': ±1}]
        polygon: PolygonOptionsLoader instance
        max_days: Maximum tracking window (14 days)

    Returns:
        Dict with intraday path data or None if data unavailable
    """

    # Build tracking window
    tracking_dates = []
    current_date = entry_date
    for _ in range(max_days):
        tracking_dates.append(current_date)
        current_date += timedelta(days=1)

    # Track intraday path
    intraday_path = []

    for trade_date in tracking_dates:
        # Load minute bars for all legs on this date
        leg_bars = {}

        for i, leg in enumerate(legs):
            minute_bars = polygon.load_minute_bars(
                trade_date=trade_date,
                strike=strike,
                expiry=expiry,
                option_type=leg['type']
            )

            if minute_bars.empty:
                # No data for this date - skip
                break

            # Resample to 15-minute bars
            bars_15min = polygon.resample_to_15min(minute_bars)

            if bars_15min.empty:
                break

            leg_bars[i] = bars_15min

        # If any leg missing data, skip this date
        if len(leg_bars) != len(legs):
            continue

        # Process each 15-minute bar
        # All legs should have same timestamps after resampling
        timestamps = leg_bars[0]['timestamp'].tolist()

        for ts in timestamps:
            # Calculate position value at this timestamp
            position_value = 0.0

            for i, leg in enumerate(legs):
                bars = leg_bars[i]
                bar_data = bars[bars['timestamp'] == ts]

                if bar_data.empty:
                    continue

                # Use midpoint for mark-to-market
                mid_price = (bar_data['high'].iloc[0] + bar_data['low'].iloc[0]) / 2.0
                leg_value = mid_price * leg['qty'] * 100  # 100 multiplier
                position_value += leg_value

            # Record this 15-minute bar
            intraday_path.append({
                'timestamp': ts,
                'date': trade_date,
                'time': ts.time(),
                'position_value': position_value
            })

    if not intraday_path:
        return None

    # Convert to DataFrame for analysis
    path_df = pd.DataFrame(intraday_path)

    # Entry value (first bar)
    entry_value = path_df['position_value'].iloc[0]

    # Calculate P&L at each bar
    path_df['pnl'] = path_df['position_value'] - entry_value

    # Find peak P&L
    peak_idx = path_df['pnl'].idxmax()
    peak_pnl = path_df['pnl'].iloc[peak_idx]
    peak_timestamp = path_df['timestamp'].iloc[peak_idx]
    peak_date = path_df['date'].iloc[peak_idx]
    peak_time = path_df['time'].iloc[peak_idx]

    # Exit P&L (last bar)
    exit_pnl = path_df['pnl'].iloc[-1]

    # Time to peak (number of 15-minute bars)
    bars_to_peak = peak_idx
    hours_to_peak = bars_to_peak * 0.25  # 15 minutes = 0.25 hours

    # Days to peak
    days_to_peak = (peak_date - entry_date).days

    return {
        'entry_date': entry_date,
        'strike': strike,
        'expiry': expiry,
        'entry_value': entry_value,
        'peak_pnl': peak_pnl,
        'peak_timestamp': peak_timestamp,
        'peak_date': peak_date,
        'peak_time': peak_time,
        'peak_time_of_day': peak_time.strftime('%H:%M'),
        'bars_to_peak': int(bars_to_peak),
        'hours_to_peak': round(hours_to_peak, 2),
        'days_to_peak': days_to_peak,
        'exit_pnl': exit_pnl,
        'capture_rate': exit_pnl / peak_pnl if peak_pnl > 0 else 0.0,
        'intraday_path': path_df.to_dict('records')
    }


def run_profile_backtest_intraday(
    profile_id: str,
    config: Dict,
    spy: pd.DataFrame,
    polygon: PolygonOptionsLoader,
    min_days_between_trades: int = 7
) -> List[Dict]:
    """
    Run backtest for a single profile with intraday (15-minute) tracking

    Same entry logic as daily backtest, but tracks with 15-minute bars
    """
    print(f"\n{'='*80}")
    print(f"INTRADAY BACKTEST: {profile_id} - {config['name']}")
    print(f"{'='*80}")
    print(f"Entry condition: {config['description']}")
    print(f"Structure: {config['structure']}")
    print(f"Target DTE: {config['dte_target']}")
    print(f"Tracking: 15-minute bars for 14 days\n")

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
            continue

        # DISASTER FILTER (same as daily backtest)
        if row.get('RV5', 0) > 0.22:
            continue

        # Entry triggered
        spot = row['close']
        strike = round(spot)

        # Adjust strike for OTM positions
        if 'OTM' in config['structure']:
            if 'Put' in config['structure']:
                strike = round(spot * 0.95)  # 5% OTM put
            elif 'Call' in config['structure']:
                strike = round(spot * 1.05)  # 5% OTM call

        # Get expiry date
        expiry = get_expiry_for_dte(entry_date, config['dte_target'])

        # Verify expiry is in future
        if expiry <= entry_date:
            continue

        print(f"Entry {len(trades)+1}: {entry_date} | Spot=${spot:.2f} | Strike=${strike} | Expiry={expiry}")

        # Track trade with 15-minute bars
        trade_record = track_trade_intraday(
            entry_date=entry_date,
            strike=strike,
            expiry=expiry,
            legs=config['legs'],
            polygon=polygon,
            max_days=14
        )

        if trade_record:
            trade_record['profile'] = profile_id
            trade_record['profile_name'] = config['name']
            trades.append(trade_record)

            print(f"  → Peak: ${trade_record['peak_pnl']:.2f} at {trade_record['peak_time_of_day']} "
                  f"(Day {trade_record['days_to_peak']}, {trade_record['hours_to_peak']:.1f}h)")
            print(f"  → Exit: ${trade_record['exit_pnl']:.2f} "
                  f"(Capture: {trade_record['capture_rate']*100:.1f}%)\n")
        else:
            print(f"  → No intraday data available\n")

        last_entry_date = entry_date

    return trades


def analyze_intraday_patterns(all_trades: List[Dict]) -> Dict:
    """
    Analyze intraday peak timing patterns across all trades

    Returns:
        Dict with pattern analysis
    """
    print(f"\n{'='*80}")
    print("INTRADAY PEAK TIMING ANALYSIS")
    print(f"{'='*80}\n")

    if not all_trades:
        return {}

    df = pd.DataFrame([{
        'profile': t['profile'],
        'profile_name': t['profile_name'],
        'peak_pnl': t['peak_pnl'],
        'peak_time': t['peak_time'],
        'peak_time_of_day': t['peak_time_of_day'],
        'hours_to_peak': t['hours_to_peak'],
        'days_to_peak': t['days_to_peak'],
        'exit_pnl': t['exit_pnl'],
        'capture_rate': t['capture_rate']
    } for t in all_trades])

    # Overall statistics
    print(f"Total Trades Analyzed: {len(df)}")
    print(f"Average Peak P&L: ${df['peak_pnl'].mean():.2f}")
    print(f"Average Time to Peak: {df['hours_to_peak'].mean():.1f} hours ({df['days_to_peak'].mean():.1f} days)")
    print(f"Average Capture Rate: {df['capture_rate'].mean()*100:.1f}%\n")

    # Peak timing distribution
    print("Peak Timing Distribution:")
    print(f"  Day 0 (entry day): {(df['days_to_peak'] == 0).sum()} trades ({(df['days_to_peak'] == 0).sum()/len(df)*100:.1f}%)")
    print(f"  Day 1-3: {((df['days_to_peak'] >= 1) & (df['days_to_peak'] <= 3)).sum()} trades")
    print(f"  Day 4-7: {((df['days_to_peak'] >= 4) & (df['days_to_peak'] <= 7)).sum()} trades")
    print(f"  Day 8-14: {(df['days_to_peak'] >= 8).sum()} trades\n")

    # Time of day analysis (for Day 0 peaks)
    day0_peaks = df[df['days_to_peak'] == 0]
    if len(day0_peaks) > 0:
        print(f"Day 0 Peak Timing (Entry Day) - {len(day0_peaks)} trades:")

        # Extract hour from peak_time
        day0_peaks['peak_hour'] = day0_peaks['peak_time'].apply(lambda t: t.hour)

        morning = (day0_peaks['peak_hour'] < 12).sum()
        afternoon = ((day0_peaks['peak_hour'] >= 12) & (day0_peaks['peak_hour'] < 16)).sum()
        close = (day0_peaks['peak_hour'] >= 16).sum()

        print(f"  Morning (9:30-12:00): {morning} trades ({morning/len(day0_peaks)*100:.1f}%)")
        print(f"  Afternoon (12:00-16:00): {afternoon} trades ({afternoon/len(day0_peaks)*100:.1f}%)")
        print(f"  Close (16:00+): {close} trades ({close/len(day0_peaks)*100:.1f}%)\n")

    # Profile-specific analysis
    print("Profile-Specific Peak Timing:")
    for profile in df['profile'].unique():
        profile_df = df[df['profile'] == profile]
        profile_name = profile_df['profile_name'].iloc[0]

        avg_hours = profile_df['hours_to_peak'].mean()
        avg_days = profile_df['days_to_peak'].mean()
        avg_capture = profile_df['capture_rate'].mean()

        print(f"  {profile} ({profile_name}):")
        print(f"    Trades: {len(profile_df)}")
        print(f"    Avg time to peak: {avg_hours:.1f}h ({avg_days:.1f}d)")
        print(f"    Avg capture rate: {avg_capture*100:.1f}%")

    return {
        'total_trades': len(df),
        'avg_peak_pnl': df['peak_pnl'].mean(),
        'avg_hours_to_peak': df['hours_to_peak'].mean(),
        'avg_days_to_peak': df['days_to_peak'].mean(),
        'avg_capture_rate': df['capture_rate'].mean(),
        'day0_peaks': len(day0_peaks) if len(day0_peaks) > 0 else 0,
        'profiles': df.groupby('profile').agg({
            'hours_to_peak': 'mean',
            'days_to_peak': 'mean',
            'capture_rate': 'mean'
        }).to_dict()
    }


def main():
    """Run intraday backtest for all 6 profiles"""

    print("="*80)
    print("INTRADAY BACKTEST - 15-MINUTE BAR TRACKING")
    print("="*80)
    print("Objective: Analyze peak timing patterns with intraday granularity")
    print("Method: Same 604 trades, tracked with 15-minute bars\n")

    # Load SPY data
    spy = load_spy_data()

    # Initialize Polygon loader with minute bar support
    print("Initializing Polygon options loader with minute bar support...")
    polygon = PolygonOptionsLoader()

    if not polygon.has_minute_data:
        print("ERROR: Minute bar data not available")
        print(f"Expected location: {polygon.minute_data_root}")
        return

    print(f"✅ Minute bar data available at: {polygon.minute_data_root}\n")

    # Get profile configs
    profiles = get_profile_configs()

    # Run backtest for each profile
    all_trades = []

    for profile_id, config in profiles.items():
        trades = run_profile_backtest_intraday(
            profile_id=profile_id,
            config=config,
            spy=spy,
            polygon=polygon,
            min_days_between_trades=7
        )

        all_trades.extend(trades)

        print(f"Completed {profile_id}: {len(trades)} trades tracked\n")

    # Analyze intraday patterns
    analysis = analyze_intraday_patterns(all_trades)

    # Save results
    output_dir = Path('data/backtest_results/intraday')
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / 'intraday_15min_results.json'

    # Serialize (convert datetime/date objects to strings)
    def serialize_trade(trade):
        serialized = trade.copy()
        for key in ['entry_date', 'expiry', 'peak_date']:
            if key in serialized and serialized[key]:
                serialized[key] = str(serialized[key])
        if 'peak_timestamp' in serialized:
            serialized['peak_timestamp'] = str(serialized['peak_timestamp'])
        if 'peak_time' in serialized:
            serialized['peak_time'] = str(serialized['peak_time'])
        # Don't serialize full intraday path (too large) - just summary
        if 'intraday_path' in serialized:
            serialized['intraday_bars_count'] = len(serialized['intraday_path'])
            del serialized['intraday_path']
        return serialized

    output_data = {
        'metadata': {
            'backtest_date': str(date.today()),
            'total_trades': len(all_trades),
            'tracking_method': '15-minute bars',
            'tracking_window': '14 days'
        },
        'analysis': analysis,
        'trades': [serialize_trade(t) for t in all_trades]
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'='*80}")
    print(f"RESULTS SAVED: {output_file}")
    print(f"{'='*80}\n")

    print(f"Total trades tracked: {len(all_trades)}")
    print(f"Average time to peak: {analysis.get('avg_hours_to_peak', 0):.1f} hours")
    print(f"Day 0 peaks: {analysis.get('day0_peaks', 0)} trades "
          f"({analysis.get('day0_peaks', 0)/len(all_trades)*100:.1f}% if trades else 0%)")
    print(f"Average capture rate: {analysis.get('avg_capture_rate', 0)*100:.1f}%\n")


if __name__ == '__main__':
    main()
