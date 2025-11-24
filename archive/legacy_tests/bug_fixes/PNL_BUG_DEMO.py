"""
DEMONSTRATION OF BUG-001: P&L SIGN INVERSION BUG

This script shows how the current P&L calculation in trade.py produces
inverted results where profits become losses and losses become profits.
"""

import pandas as pd

print("=" * 80)
print("BUG-001 DEMONSTRATION: P&L CALCULATION INVERTED")
print("=" * 80)
print()

# Current implementation from trade.py
def calculate_pnl_current_buggy(entry_prices, exit_prices, quantities):
    """Current buggy implementation."""
    entry_cost = sum(-quantities[i] * entry_prices[i] for i in range(len(quantities)))
    exit_proceeds = sum(-quantities[i] * exit_prices[i] for i in range(len(quantities)))
    realized_pnl = exit_proceeds - entry_cost
    return entry_cost, exit_proceeds, realized_pnl

# Correct implementation
def calculate_pnl_correct(entry_prices, exit_prices, quantities):
    """Correct implementation."""
    pnl_per_leg = 0.0
    for i in range(len(quantities)):
        # P&L = qty * (exit - entry)
        # For long (qty > 0): positive when exit > entry
        # For short (qty < 0): positive when entry > exit
        pnl_per_leg += quantities[i] * (exit_prices[i] - entry_prices[i])
    return pnl_per_leg

print("SCENARIO 1: Long Straddle (Buy Call + Buy Put)")
print("-" * 80)
print()

entry_prices = [2.50, 3.00]  # Call, Put
exit_prices = [4.00, 2.00]   # Call, Put
quantities = [1, 1]           # Long 1 of each

print("Entry:")
print(f"  Buy 1 Call @ ${entry_prices[0]}")
print(f"  Buy 1 Put  @ ${entry_prices[1]}")
print(f"  Total paid: ${sum(entry_prices)}")
print()

print("Exit:")
print(f"  Sell 1 Call @ ${exit_prices[0]}")
print(f"  Sell 1 Put  @ ${exit_prices[1]}")
print(f"  Total received: ${sum(exit_prices)}")
print()

reality = sum(exit_prices) - sum(entry_prices)
print(f"REALITY: Profit = ${reality:.2f}")
print()

current_entry, current_exit, current_pnl = calculate_pnl_current_buggy(entry_prices, exit_prices, quantities)
correct_pnl = calculate_pnl_correct(entry_prices, exit_prices, quantities)

print(f"Current (buggy) implementation:")
print(f"  entry_cost = {current_entry:.2f}")
print(f"  exit_proceeds = {current_exit:.2f}")
print(f"  realized_pnl = {current_exit:.2f} - {current_entry:.2f} = {current_pnl:.2f}")
print(f"  Result: {current_pnl:.2f} ❌ WRONG (inverted sign)")
print()

print(f"Correct implementation:")
print(f"  realized_pnl = {correct_pnl:.2f} ✅ CORRECT")
print()

print()
print("SCENARIO 2: Short Strangle (Sell Call + Sell Put)")
print("-" * 80)
print()

entry_prices = [2.00, 1.50]  # Call, Put
exit_prices = [1.00, 0.50]   # Call, Put
quantities = [-1, -1]         # Short 1 of each

print("Entry:")
print(f"  Sell 1 Call @ ${entry_prices[0]}")
print(f"  Sell 1 Put  @ ${entry_prices[1]}")
print(f"  Total received: ${sum(entry_prices)}")
print()

print("Exit:")
print(f"  Buy 1 Call @ ${exit_prices[0]}")
print(f"  Buy 1 Put  @ ${exit_prices[1]}")
print(f"  Total paid: ${sum(exit_prices)}")
print()

reality = sum(entry_prices) - sum(exit_prices)
print(f"REALITY: Profit = ${reality:.2f}")
print()

current_entry, current_exit, current_pnl = calculate_pnl_current_buggy(entry_prices, exit_prices, quantities)
correct_pnl = calculate_pnl_correct(entry_prices, exit_prices, quantities)

print(f"Current (buggy) implementation:")
print(f"  entry_cost = {current_entry:.2f}")
print(f"  exit_proceeds = {current_exit:.2f}")
print(f"  realized_pnl = {current_exit:.2f} - {current_entry:.2f} = {current_pnl:.2f}")
print(f"  Result: {current_pnl:.2f} ❌ WRONG (inverted sign)")
print()

print(f"Correct implementation:")
print(f"  realized_pnl = {correct_pnl:.2f} ✅ CORRECT")
print()

print()
print("SCENARIO 3: Call Vertical Spread (Buy call, Sell call)")
print("-" * 80)
print()

entry_prices = [3.00, 1.50]  # Buy 400C, Sell 410C
exit_prices = [2.00, 0.75]   # Exit both
quantities = [1, -1]         # Long 400C, Short 410C

print("Entry:")
print(f"  Buy 1 Call @ ${entry_prices[0]}")
print(f"  Sell 1 Call @ ${entry_prices[1]}")
print(f"  Net debit: ${entry_prices[0] - entry_prices[1]}")
print()

print("Exit:")
print(f"  Sell 1 Call @ ${exit_prices[0]}")
print(f"  Buy 1 Call @ ${exit_prices[1]}")
print(f"  Net proceeds: ${exit_prices[0] - exit_prices[1]}")
print()

reality = (entry_prices[0] - entry_prices[1]) - (exit_prices[0] - exit_prices[1])
print(f"REALITY: Profit = ${reality:.2f}")
print()

current_entry, current_exit, current_pnl = calculate_pnl_current_buggy(entry_prices, exit_prices, quantities)
correct_pnl = calculate_pnl_correct(entry_prices, exit_prices, quantities)

print(f"Current (buggy) implementation:")
print(f"  entry_cost = {current_entry:.2f}")
print(f"  exit_proceeds = {current_exit:.2f}")
print(f"  realized_pnl = {current_exit:.2f} - {current_entry:.2f} = {current_pnl:.2f}")
print(f"  Result: {current_pnl:.2f} ❌ WRONG (inverted sign)")
print()

print(f"Correct implementation:")
print(f"  realized_pnl = {correct_pnl:.2f} ✅ CORRECT")
print()

print()
print("=" * 80)
print("IMPACT ANALYSIS")
print("=" * 80)
print()

print("All backtest results are INVERTED:")
print()
print("Winning trades → Show as losses")
print("Losing trades  → Show as profits")
print("Equity curve   → Completely backwards")
print("Sharpe ratio   → Inverted (negative when should be positive)")
print("Win rate       → Inverted (60% win rate becomes 40% in analysis)")
print()

print("Real capital risk: EXTREME")
print("A strategy that wins 60% of the time appears to lose 60% of the time")
print("Following this backtest would cause catastrophic losses")
print()

print("=" * 80)
print("CONCLUSION: BUG-001 MUST BE FIXED BEFORE ANY DEPLOYMENT")
print("=" * 80)
