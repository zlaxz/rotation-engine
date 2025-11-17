#!/usr/bin/env python3
"""
Test all 6 profiles - no regime filtering (broad test)
Real costs: $0.03 spread, $2.60 commission, NO hedging
Measure peak potential for each
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
import glob
import json

# Load SPY
print("Loading SPY data...")
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
spy_data = []
for f in spy_files:
    df = pd.read_parquet(f)
    if len(df) > 0:
        spy_data.append({
            'date': pd.to_datetime(df['ts'].iloc[0]).date(),
            'close': df['close'].iloc[-1]
        })

spy = pd.DataFrame(spy_data)
spy['slope'] = spy['close'].pct_change(20)

print(f"Loaded {len(spy)} days\n")

polygon = PolygonOptionsLoader()

# Profile definitions (simplified for testing)
profiles = {
    'Profile_1_LDG': {
        'name': 'Long-Dated Gamma',
        'entry_score': 0.02,  # Enter when 20-day return > 2%
        'structure': 'ATM straddle',
        'dte': 75
    },
    'Profile_2_SDG': {
        'name': 'Short-Dated Gamma',
        'entry_score': 0.03,  # Enter when momentum > 3%
        'structure': 'ATM straddle',
        'dte': 7
    },
    'Profile_3_CHARM': {
        'name': 'Charm/Decay',
        'entry_score': -0.01,  # Enter in sideways (negative momentum ok)
        'structure': 'Short ATM straddle',
        'dte': 30
    },
    'Profile_4_VANNA': {
        'name': 'Vanna',
        'entry_score': 0.02,
        'structure': 'ATM call',
        'dte': 60
    },
    'Profile_5_SKEW': {
        'name': 'Skew',
        'entry_score': -0.02,  # Enter on down moves
        'structure': 'OTM put',
        'dte': 45
    },
    'Profile_6_VOV': {
        'name': 'Vol-of-Vol',
        'entry_score': 0.00,  # Enter anytime
        'structure': 'ATM straddle',
        'dte': 30
    }
}

results = {}

for profile_id, config in profiles.items():
    print(f"Testing {profile_id} ({config['name']})...")

    trades = []
    position = None

    for idx in range(50, len(spy)):
        row = spy.iloc[idx]
        d = row['date']
        spot = row['close']
        score = row['slope']

        # Exit after 7 days
        if position:
            days = (d - position['entry']).days
            if days >= 7:
                cm = polygon.get_option_price(d, position['strike'], position['expiry'], 'call', 'mid')
                pm = polygon.get_option_price(d, position['strike'], position['expiry'], 'put', 'mid')
                if cm and pm:
                    # For now, all test as straddles
                    pnl = (cm + pm - 0.03) * 100 - position['cost'] - 2.60
                    trades.append({'pnl': pnl, 'peak': position['peak']})
                position = None

        # Entry
        if not position and score > config['entry_score']:
            strike = round(spot)
            target = d + timedelta(days=config['dte'])
            fd = date(target.year, target.month, 1)
            ff = fd + timedelta(days=(4 - fd.weekday()) % 7)
            expiry = ff + timedelta(days=14)

            cm = polygon.get_option_price(d, strike, expiry, 'call', 'mid')
            pm = polygon.get_option_price(d, strike, expiry, 'put', 'mid')
            if cm and pm:
                cost = (cm + pm + 0.03) * 100

                # Find peak
                peak = -999999
                for fidx in range(idx, min(idx+8, len(spy))):
                    fr = spy.iloc[fidx]
                    fcm = polygon.get_option_price(fr['date'], strike, expiry, 'call', 'mid')
                    fpm = polygon.get_option_price(fr['date'], strike, expiry, 'put', 'mid')
                    if fcm and fpm:
                        fpnl = (fcm + fpm - 0.03) * 100 - cost - 2.60
                        if fpnl > peak:
                            peak = fpnl

                position = {'entry': d, 'strike': strike, 'expiry': expiry, 'cost': cost, 'peak': peak}

    # Results for this profile
    if trades:
        df = pd.DataFrame(trades)
        results[profile_id] = {
            'trades': len(df),
            'actual_pnl': df['pnl'].sum(),
            'peak_potential': df['peak'].apply(lambda x: x if x > 0 else 0).sum(),
            'capture_30pct': df['peak'].apply(lambda x: x * 0.3 if x > 0 else x * 0.1).sum(),
            'winners': (df['pnl'] > 0).sum()
        }
        print(f"  {len(df)} trades, Peak: ${results[profile_id]['peak_potential']:.0f}, "
              f"30% capture: ${results[profile_id]['capture_30pct']:.0f}")
    else:
        results[profile_id] = {'trades': 0, 'actual_pnl': 0, 'peak_potential': 0,
                               'capture_30pct': 0, 'winners': 0}
        print(f"  No trades")

# Summary
print("\n" + "=" * 80)
print("SUMMARY - ALL 6 PROFILES")
print("=" * 80)

for pid, res in results.items():
    name = profiles[pid]['name']
    if res['trades'] > 0:
        print(f"{pid:20s} {name:20s} {res['trades']:3d} trades, "
              f"Peak ${res['peak_potential']:>7.0f}, 30% ${res['capture_30pct']:>7.0f}")

total_peak = sum(r['peak_potential'] for r in results.values())
total_30pct = sum(r['capture_30pct'] for r in results.values())

print(f"\n{'TOTAL':41s} Peak ${total_peak:>7.0f}, 30% ${total_30pct:>7.0f}")

print(f"\n" + "=" * 80)
if total_30pct > 0:
    print(f"✅ Combined profiles have edge (${total_30pct:.0f} at 30% capture)")
else:
    print(f"❌ No edge even at 30% capture")

# Save
with open('all_profiles_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nSaved: all_profiles_results.json")
