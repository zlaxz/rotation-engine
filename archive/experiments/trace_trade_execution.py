#!/usr/bin/env python3
"""
Trace Trade 1 execution to find bugs.
Manually step through entry → MTM → exit with full logging.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

from src.pricing.greeks import calculate_all_greeks
from datetime import date, datetime, timedelta
import numpy as np

print("=" * 80)
print("MANUAL TRADE TRACE - ZERO ASSUMPTIONS")
print("=" * 80)

# FACTS (from backtest data):
entry_date = date(2020, 5, 20)
exit_date = date(2020, 6, 5)
entry_spy = 296.83
exit_spy = 319.15
atm_strike = 297.0  # Rounded from 296.83

# Trade structure (from profile_1.py):
# Long 1 ATM straddle (1 call + 1 put, each qty=1)
target_dte = 75
expiry = entry_date + timedelta(days=target_dte)

print(f"\n TRADE STRUCTURE (from code):")
print(f"  Entry: {entry_date}")
print(f"  Strike: ${atm_strike:.0f}")
print(f"  Expiry: {expiry} ({target_dte} DTE)")
print(f"  Position: Long 1 ATM call + 1 ATM put (qty=1 each)")

# STEP 1: Calculate entry prices using Black-Scholes
print(f"\n" + "=" * 80)
print("STEP 1: ENTRY PRICES (Day 1)")
print("=" * 80)

# Estimate IV from context (post-COVID, May 2020, VIX probably ~28)
entry_iv = 0.28
risk_free = 0.05
T_entry = target_dte / 365.0

print(f"  SPY: ${entry_spy:.2f}")
print(f"  IV estimate: {entry_iv:.1%}")
print(f"  Time to expiry: {T_entry:.4f} years")

# Calculate call and put prices
call_greeks = calculate_all_greeks(
    S=entry_spy,
    K=atm_strike,
    T=T_entry,
    r=risk_free,
    sigma=entry_iv,
    option_type='call'
)

put_greeks = calculate_all_greeks(
    S=entry_spy,
    K=atm_strike,
    T=T_entry,
    r=risk_free,
    sigma=entry_iv,
    option_type='put'
)

# Black-Scholes prices (calculate manually)
from scipy.stats import norm

d1 = (np.log(entry_spy / atm_strike) + (risk_free + 0.5 * entry_iv**2) * T_entry) / (entry_iv * np.sqrt(T_entry))
d2 = d1 - entry_iv * np.sqrt(T_entry)

call_price = entry_spy * norm.cdf(d1) - atm_strike * np.exp(-risk_free * T_entry) * norm.cdf(d2)
put_price = atm_strike * np.exp(-risk_free * T_entry) * norm.cdf(-d2) - entry_spy * norm.cdf(-d1)

print(f"\n  Black-Scholes Prices:")
print(f"    Call mid: ${call_price:.2f}")
print(f"    Put mid: ${put_price:.2f}")
print(f"    Straddle mid: ${call_price + put_price:.2f}")

print(f"\n  Entry Greeks (per contract):")
print(f"    Call delta: {call_greeks['delta']:.4f}")
print(f"    Put delta: {put_greeks['delta']:.4f}")
print(f"    Straddle delta: {call_greeks['delta'] + put_greeks['delta']:.4f} (should be ~0)")
print(f"    Straddle gamma: {call_greeks['gamma'] + put_greeks['gamma']:.6f}")
print(f"    Straddle vega: {call_greeks['vega'] + put_greeks['vega']:.4f}")
print(f"    Straddle theta: {call_greeks['theta'] + put_greeks['theta']:.4f}")

# Apply execution costs (bid/ask + slippage)
straddle_mid = call_price + put_price
half_spread = 0.50  # ATM straddle spread
slippage_bug = straddle_mid * 0.0025  # The bug we found

entry_price_with_bugs = straddle_mid + half_spread + slippage_bug
entry_price_correct = straddle_mid + half_spread

print(f"\n  Entry Execution:")
print(f"    Mid: ${straddle_mid:.2f}")
print(f"    + Half spread: ${half_spread:.2f}")
print(f"    + Slippage (BUG): ${slippage_bug:.2f}")
print(f"    = Entry price (with bug): ${entry_price_with_bugs:.2f}")
print(f"    = Entry price (correct): ${entry_price_correct:.2f}")

entry_cost_with_bugs = entry_price_with_bugs * 100  # 1 straddle
entry_cost_correct = entry_price_correct * 100

print(f"\n  Entry Cost:")
print(f"    With bug: ${entry_cost_with_bugs:.2f}")
print(f"    Correct: ${entry_cost_correct:.2f}")
print(f"    Bug impact: ${entry_cost_with_bugs - entry_cost_correct:.2f}")

# Commission
entry_commission = 2 * 0.65  # 2 contracts @ $0.65
print(f"\n  Entry commission: ${entry_commission:.2f}")

# Day 1 MTM (same day as entry)
day1_mtm = straddle_mid * 100  # Current value at mid
day1_unrealized = day1_mtm - entry_cost_with_bugs

print(f"\n  Day 1 MTM (end of entry day):")
print(f"    Current value (mid): ${day1_mtm:.2f}")
print(f"    Unrealized P&L: ${day1_unrealized:.2f}")
print(f"    - Entry commission: ${entry_commission:.2f}")
print(f"    - Exit commission (BUG - frontloaded): ${entry_commission:.2f}")
print(f"    = Day 1 P&L: ${day1_unrealized - entry_commission - entry_commission:.2f}")

print(f"\n  BACKTEST SHOWS: -$61.40")
print(f"  CALCULATED: ${day1_unrealized - entry_commission - entry_commission:.2f}")
print(f"  Match? {'YES' if abs((day1_unrealized - entry_commission - entry_commission) - (-61.40)) < 5 else 'NO'}")

# STEP 2: Exit day (12 days later)
print(f"\n" + "=" * 80)
print("STEP 2: EXIT PRICES (Day 12)")
print("=" * 80)

days_elapsed = 12
exit_dte = target_dte - days_elapsed
T_exit = exit_dte / 365.0

print(f"  SPY: ${exit_spy:.2f} (moved +${exit_spy - entry_spy:.2f} or +{((exit_spy/entry_spy)-1)*100:.2f}%)")
print(f"  DTE remaining: {exit_dte} days")
print(f"  Time to expiry: {T_exit:.4f} years")

# Assume IV stayed similar (may be wrong - need to check)
exit_iv = 0.28

# Calculate exit prices (manual BS)
d1_exit = (np.log(exit_spy / atm_strike) + (risk_free + 0.5 * exit_iv**2) * T_exit) / (exit_iv * np.sqrt(T_exit))
d2_exit = d1_exit - exit_iv * np.sqrt(T_exit)

call_price_exit = exit_spy * norm.cdf(d1_exit) - atm_strike * np.exp(-risk_free * T_exit) * norm.cdf(d2_exit)
put_price_exit = atm_strike * np.exp(-risk_free * T_exit) * norm.cdf(-d2_exit) - exit_spy * norm.cdf(-d1_exit)

print(f"\n  Black-Scholes Prices:")
print(f"    Call mid: ${call_price_exit:.2f} (was ${call_price:.2f})")
print(f"    Put mid: ${put_price_exit:.2f} (was ${put_price:.2f})")
print(f"    Straddle mid: ${call_price_exit + put_price_exit:.2f} (was ${straddle_mid:.2f})")

straddle_mid_exit = call_price_exit + put_price_exit
straddle_change = straddle_mid_exit - straddle_mid

print(f"\n  Straddle value change: ${straddle_change:.2f}")
print(f"  In dollars (×100): ${straddle_change * 100:.2f}")

# Calculate components
call_change = call_price_exit - call_price
put_change = put_price_exit - put_price

print(f"\n  Component changes:")
print(f"    Call: ${call_change:.2f} (×100 = ${call_change * 100:.2f})")
print(f"    Put: ${put_change:.2f} (×100 = ${put_change * 100:.2f})")

# Exit execution
exit_price_with_bugs = straddle_mid_exit - half_spread - slippage_bug
exit_proceeds_with_bugs = exit_price_with_bugs * 100

print(f"\n  Exit Execution:")
print(f"    Mid: ${straddle_mid_exit:.2f}")
print(f"    - Half spread: ${half_spread:.2f}")
print(f"    - Slippage (BUG): ${(straddle_mid_exit * 0.0025):.2f}")
print(f"    = Exit price (with bug): ${exit_price_with_bugs:.2f}")
print(f"    = Exit proceeds: ${exit_proceeds_with_bugs:.2f}")

# Total P&L
exit_commission = 2 * 0.65
total_pnl = exit_proceeds_with_bugs - entry_cost_with_bugs - entry_commission - exit_commission

print(f"\n  Final P&L Calculation:")
print(f"    Exit proceeds: ${exit_proceeds_with_bugs:.2f}")
print(f"    - Entry cost: ${entry_cost_with_bugs:.2f}")
print(f"    - Entry commission: ${entry_commission:.2f}")
print(f"    - Exit commission: ${exit_commission:.2f}")
print(f"    = Net P&L: ${total_pnl:.2f}")

print(f"\n  BACKTEST SHOWS: $140.60")
print(f"  CALCULATED: ${total_pnl:.2f}")
print(f"  Difference: ${abs(total_pnl - 140.60):.2f}")

if abs(total_pnl - 140.60) < 100:
    print(f"\n  ✓ MATCH (within $100) - calculation seems correct with IV=28%")
else:
    print(f"\n  ✗ MISMATCH - either IV is wrong or there's another bug")
    print(f"\n  Trying different IV values...")
    for test_iv in [0.25, 0.30, 0.35, 0.40]:
        call_test = black_scholes_price(exit_spy, atm_strike, T_exit, risk_free, test_iv, 'call')
        put_test = black_scholes_price(exit_spy, atm_strike, T_exit, risk_free, test_iv, 'put')
        straddle_test = call_test + put_test
        exit_proceeds_test = (straddle_test - half_spread - straddle_test * 0.0025) * 100
        pnl_test = exit_proceeds_test - entry_cost_with_bugs - entry_commission - exit_commission
        print(f"    IV={test_iv:.0%}: Exit straddle=${straddle_test:.2f}, P&L=${pnl_test:.2f}")

EOF
