#!/usr/bin/env python3
"""Run a SINGLE trade with full debug logging."""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date
from src.pricing.greeks import calculate_all_greeks
from scipy.stats import norm

print("=" * 80)
print("SINGLE TRADE SIMULATION - FULL DEBUG LOGGING")
print("=" * 80)

# Trade setup
entry_date = date(2020, 5, 20)
entry_spy = 296.83
strike = 297.0
dte = 75
entry_iv = 0.28
risk_free = 0.05

# Calculate entry (single call for simplicity)
T = dte / 365.0
d1 = (np.log(entry_spy / strike) + (risk_free + 0.5 * entry_iv**2) * T) / (entry_iv * np.sqrt(T))
d2 = d1 - entry_iv * np.sqrt(T)
call_price_mid = entry_spy * norm.cdf(d1) - strike * np.exp(-risk_free * T) * norm.cdf(d2)

# Entry Greeks
call_greeks = calculate_all_greeks(
    S=entry_spy,
    K=strike,
    T=T,
    r=risk_free,
    sigma=entry_iv,
    option_type='call'
)

# Entry execution (with bugs)
half_spread = 0.375  # Half of $0.75 ATM
slippage_bug = call_price_mid * 0.0025
entry_price_with_bugs = call_price_mid + half_spread + slippage_bug
entry_cost_with_bugs = entry_price_with_bugs * 100
commission = 0.65

print(f"\nENTRY (Day 1):")
print(f"  SPY: ${entry_spy:.2f}")
print(f"  Call mid: ${call_price_mid:.2f}")
print(f"  Entry price: ${entry_price_with_bugs:.2f} (mid + spread + slippage bug)")
print(f"  Entry cost: ${entry_cost_with_bugs:.2f}")
print(f"  Delta: {call_greeks['delta']*100:.2f}")

# Day 1 P&L
day1_pnl = -half_spread*100 - slippage_bug*100 - commission - commission
print(f"  Day 1 P&L: ${day1_pnl:.2f}")

# Simulate 12 days
print(f"\n{'Day':>3} {'SPY':>8} {'IV':>6} {'Delta':>7} {'Hedge':>7} {'Cost':>8} {'DailyP&L':>10} {'CumP&L':>10}")
print("-" * 80)

spy_path = np.linspace(entry_spy, 319.15, 13)[1:]
iv_path = np.linspace(entry_iv, entry_iv - 0.006, 13)[1:]

cumulative_pnl = day1_pnl
total_hedge_cost = 0.0

print(f"{1:>3} ${entry_spy:>7.2f} {entry_iv:>5.1%} {call_greeks['delta']*100:>6.2f} {'No':>7} ${0.00:>7.2f} ${day1_pnl:>9.2f} ${cumulative_pnl:>9.2f}")

for day in range(2, 13):
    current_spy = spy_path[day-1]
    current_iv = iv_path[day-1]
    current_dte = dte - day
    T_curr = current_dte / 365.0

    # Current Greeks
    d1_curr = (np.log(current_spy / strike) + (risk_free + 0.5 * current_iv**2) * T_curr) / (current_iv * np.sqrt(T_curr))
    d2_curr = d1_curr - current_iv * np.sqrt(T_curr)
    call_price_curr = current_spy * norm.cdf(d1_curr) - strike * np.exp(-risk_free * T_curr) * norm.cdf(d2_curr)

    curr_greeks = calculate_all_greeks(
        S=current_spy,
        K=strike,
        T=T_curr,
        r=risk_free,
        sigma=current_iv,
        option_type='call'
    )

    # Delta hedge check
    net_delta = curr_greeks['delta'] * 100
    hedge_needed = abs(net_delta) > 20

    if hedge_needed:
        es_contracts = abs(net_delta) / 50
        hedge_cost = es_contracts * 15  # Bug: $15 per ES contract
        total_hedge_cost += hedge_cost
    else:
        hedge_cost = 0.0

    # Daily P&L = change in option value - hedge cost
    current_value = call_price_curr * 100
    daily_change = current_value - (cumulative_pnl + entry_cost_with_bugs + 2*commission)
    daily_pnl = daily_change - hedge_cost
    cumulative_pnl += daily_pnl

    print(f"{day:>3} ${current_spy:>7.2f} {current_iv:>5.1%} {net_delta:>6.2f} "
          f"{'Yes' if hedge_needed else 'No':>7} ${hedge_cost:>7.2f} ${daily_pnl:>9.2f} ${cumulative_pnl:>9.2f}")

print("-" * 80)
print(f"\nSUMMARY:")
print(f"  Total hedge cost: ${total_hedge_cost:.2f}")
print(f"  Final P&L: ${cumulative_pnl:.2f}")
print(f"\nFor comparison (straddle = 2 calls equivalent):")
print(f"  Straddle would be ~2x these numbers")
print(f"  Expected straddle P&L: ${cumulative_pnl * 2:.2f}")
print(f"  Backtest shows: $140.60")
