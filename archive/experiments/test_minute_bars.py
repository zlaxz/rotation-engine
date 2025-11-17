#!/usr/bin/env python3
"""
Quick test of minute bar loading functionality
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

from datetime import date
from src.data.polygon_options import PolygonOptionsLoader

# Create loader
polygon = PolygonOptionsLoader()

print(f"Has minute data: {polygon.has_minute_data}")
print(f"Minute data root: {polygon.minute_data_root}")

# Test loading minute bars for a specific option
test_date = date(2023, 1, 3)
strike = 380.0
expiry = date(2023, 2, 17)
option_type = 'call'

print(f"\nLoading minute bars for:")
print(f"  Date: {test_date}")
print(f"  Strike: {strike}")
print(f"  Expiry: {expiry}")
print(f"  Type: {option_type}")

minute_bars = polygon.load_minute_bars(test_date, strike, expiry, option_type)

if not minute_bars.empty:
    print(f"\n✅ Loaded {len(minute_bars)} minute bars")
    print(f"\nFirst 5 bars:")
    print(minute_bars.head())

    # Test 15-minute resampling
    print(f"\n\nResampling to 15-minute bars...")
    bars_15min = polygon.resample_to_15min(minute_bars)
    print(f"✅ Resampled to {len(bars_15min)} 15-minute bars")
    print(f"\nFirst 5 15-minute bars:")
    print(bars_15min.head())
else:
    print("❌ No data found")
