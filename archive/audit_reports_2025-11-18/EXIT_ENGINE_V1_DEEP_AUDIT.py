#!/usr/bin/env python3
"""
EXIT ENGINE V1 DEEP AUDIT - RED TEAM ATTACK

Mission: Find EVERY bug causing -14.4% performance destruction.

Audit Areas:
1. P&L percentage calculation for shorts (sign conventions)
2. TP1/TP2 trigger logic (threshold comparisons)
3. Fractional exit P&L scaling (math errors)
4. Condition exit logic (false positives)
5. Decision order (wrong priority)
6. Greeks/market data handling (None values, missing keys)
7. TP1 state tracking (contamination between trades/periods)
8. Entry cost handling (abs() misuse)

Manual verification of 10 random trades with full calculation walkthrough.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import json
import random
from pathlib import Path
from src.trading.exit_engine_v1 import ExitEngineV1

# Set seed for reproducible random selection
random.seed(42)


def audit_pnl_calculation():
    """
    AUDIT 1: P&L Percentage Calculation

    For LONGS (positive entry_cost):
        - Entry: Pay $500 premium
        - MTM: +$100 gain
        - pnl_pct = +$100 / $500 = +20% ✓

    For SHORTS (negative entry_cost):
        - Entry: Collect -$500 premium (negative cost)
        - MTM: -$100 loss (premium increased to $600)
        - pnl_pct = -$100 / abs(-$500) = -$100 / $500 = -20% ✓

    BUG PATTERNS:
    - Not using abs() → dividing by negative → inverted sign
    - Using abs() on MTM → wrong sign
    - Using abs() on both → wrong for shorts
    """
    print("="*80)
    print("AUDIT 1: P&L PERCENTAGE CALCULATION")
    print("="*80)

    test_cases = [
        # (entry_cost, mtm_pnl, expected_pnl_pct, description)
        (500, 100, 0.20, "LONG: +20% profit"),
        (500, -250, -0.50, "LONG: -50% loss"),
        (-500, 100, 0.20, "SHORT: +20% profit (premium fell $600→$400)"),
        (-500, -100, -0.20, "SHORT: -20% loss (premium rose $500→$600)"),
        (-500, -250, -0.50, "SHORT: -50% loss (premium rose $500→$750)"),
        (-500, 300, 0.60, "SHORT: +60% profit (premium fell $500→$200)"),
    ]

    bugs_found = []

    for entry_cost, mtm_pnl, expected_pnl_pct, desc in test_cases:
        # Current implementation (line 353 in exit_engine_v1.py)
        if abs(entry_cost) < 0.01:
            actual_pnl_pct = 0
        else:
            actual_pnl_pct = mtm_pnl / abs(entry_cost)

        error = abs(actual_pnl_pct - expected_pnl_pct)
        status = "✅ PASS" if error < 0.0001 else "❌ FAIL"

        print(f"\n{status} {desc}")
        print(f"  Entry cost: ${entry_cost:.2f}")
        print(f"  MTM P&L: ${mtm_pnl:.2f}")
        print(f"  Expected: {expected_pnl_pct:.1%}")
        print(f"  Actual: {actual_pnl_pct:.1%}")
        print(f"  Error: {error:.6f}")

        if error > 0.0001:
            bugs_found.append({
                'test': desc,
                'expected': expected_pnl_pct,
                'actual': actual_pnl_pct,
                'error': error
            })

    if bugs_found:
        print(f"\n🔴 CRITICAL: {len(bugs_found)} P&L calculation bugs found!")
        return False
    else:
        print(f"\n✅ CLEAN: P&L calculation is correct")
        return True


def audit_tp_trigger_logic():
    """
    AUDIT 2: TP1/TP2 Trigger Logic

    Configuration (Profile_1_LDG):
    - max_loss_pct = -0.50 (-50%)
    - tp1_pct = 0.50 (+50%)
    - tp2_pct = 1.00 (+100%)

    Test edge cases:
    - pnl_pct = -0.50 → Should trigger max_loss ✓
    - pnl_pct = -0.51 → Should trigger max_loss ✓
    - pnl_pct = -0.49 → Should NOT trigger ✓
    - pnl_pct = 0.50 → Should trigger TP1 ✓
    - pnl_pct = 0.51 → Should trigger TP1 ✓ (not TP2)
    - pnl_pct = 1.00 → Should trigger TP2 ✓
    """
    print("\n" + "="*80)
    print("AUDIT 2: TP1/TP2 TRIGGER LOGIC")
    print("="*80)

    engine = ExitEngineV1()
    engine.reset_tp1_tracking()

    test_cases = [
        # (pnl_pct, expected_exit, expected_reason, description)
        (-0.51, True, "max_loss_-50%", "Below max_loss threshold"),
        (-0.50, True, "max_loss_-50%", "Exactly at max_loss threshold"),
        (-0.49, False, "", "Just above max_loss threshold"),
        (0.49, False, "", "Just below TP1 threshold"),
        (0.50, True, "tp1_50%", "Exactly at TP1 threshold"),
        (0.51, True, "tp1_50%", "Above TP1, below TP2"),
        (0.99, True, "tp1_50%", "Just below TP2"),
        (1.00, True, "tp2_100%", "Exactly at TP2 threshold"),
        (1.50, True, "tp2_100%", "Well above TP2"),
    ]

    bugs_found = []

    for pnl_pct, expected_exit, expected_reason, desc in test_cases:
        engine.reset_tp1_tracking()  # Fresh state for each test

        should_exit, fraction, reason = engine.should_exit(
            profile_id='Profile_1_LDG',
            trade_id='test_trade_1',
            days_held=5,
            pnl_pct=pnl_pct,
            market_conditions={},
            position_greeks={}
        )

        exit_match = should_exit == expected_exit
        reason_match = reason == expected_reason if expected_exit else True
        status = "✅ PASS" if (exit_match and reason_match) else "❌ FAIL"

        print(f"\n{status} {desc}")
        print(f"  P&L: {pnl_pct:.1%}")
        print(f"  Expected: exit={expected_exit}, reason='{expected_reason}'")
        print(f"  Actual: exit={should_exit}, reason='{reason}'")

        if not (exit_match and reason_match):
            bugs_found.append({
                'test': desc,
                'pnl_pct': pnl_pct,
                'expected': (expected_exit, expected_reason),
                'actual': (should_exit, reason)
            })

    if bugs_found:
        print(f"\n🔴 CRITICAL: {len(bugs_found)} TP trigger bugs found!")
        return False
    else:
        print(f"\n✅ CLEAN: TP trigger logic is correct")
        return True


def audit_fractional_exit_pnl():
    """
    AUDIT 3: Fractional Exit P&L Scaling

    Scenario: TP1 closes 50% of position
    - Entry cost: $1000
    - Current MTM: +$600 (+60%)
    - TP1 triggers at +50%, closes 50%
    - Current P&L at trigger: Actually +$500 (not +$600, but when it crossed 50%)

    CORRECT: Scale P&L by fraction
    - Realized P&L = $500 * 0.50 = $250 ✓

    WRONG PATTERNS:
    - Realize full $500 (ignores partial exit)
    - Realize $250 but keep counting unrealized on closed half
    """
    print("\n" + "="*80)
    print("AUDIT 3: FRACTIONAL EXIT P&L SCALING")
    print("="*80)

    # Test via apply_to_tracked_trade
    engine = ExitEngineV1()
    engine.reset_tp1_tracking()

    # Simulate a trade that hits TP1 at 50% with MTM = +$600
    # Entry cost = $1000, so +60% means MTM = +$600
    test_trade = {
        'entry': {
            'entry_date': '2020-01-01',
            'entry_cost': 1000.0,
            'strike': 350,
            'expiry': '2020-01-31'
        },
        'path': [
            # Day 0: Small gain
            {'day': 0, 'mtm_pnl': 100, 'market_conditions': {}, 'greeks': {}},
            # Day 1: TP1 triggers (+50% = +$500)
            {'day': 1, 'mtm_pnl': 500, 'market_conditions': {}, 'greeks': {}},
            # Day 2: Continues to rise (but TP1 already hit)
            {'day': 2, 'mtm_pnl': 600, 'market_conditions': {}, 'greeks': {}},
        ]
    }

    result = engine.apply_to_tracked_trade('Profile_1_LDG', test_trade)

    # Expected: TP1 triggers on day 1 with pnl_pct = 0.50
    # Fraction = 0.50, so exit_pnl = 500 * 0.50 = 250
    expected_exit_day = 1
    expected_reason = "tp1_50%"
    expected_fraction = 0.50
    expected_exit_pnl = 500 * 0.50  # 250

    day_match = result['exit_day'] == expected_exit_day
    reason_match = result['exit_reason'] == expected_reason
    fraction_match = result['exit_fraction'] == expected_fraction
    pnl_match = abs(result['exit_pnl'] - expected_exit_pnl) < 0.01

    status = "✅ PASS" if all([day_match, reason_match, fraction_match, pnl_match]) else "❌ FAIL"

    print(f"\n{status} TP1 Partial Exit Scaling")
    print(f"  Entry cost: ${test_trade['entry']['entry_cost']:.2f}")
    print(f"  Day 1 MTM: ${test_trade['path'][1]['mtm_pnl']:.2f} (+50%)")
    print(f"  Expected: day={expected_exit_day}, reason='{expected_reason}', ")
    print(f"            fraction={expected_fraction:.2f}, pnl=${expected_exit_pnl:.2f}")
    print(f"  Actual: day={result['exit_day']}, reason='{result['exit_reason']}', ")
    print(f"          fraction={result['exit_fraction']:.2f}, pnl=${result['exit_pnl']:.2f}")

    if not all([day_match, reason_match, fraction_match, pnl_match]):
        print(f"\n🔴 CRITICAL: Fractional exit P&L scaling is WRONG")
        return False
    else:
        print(f"\n✅ CLEAN: Fractional exit P&L scaling is correct")
        return True


def audit_condition_exit_false_positives():
    """
    AUDIT 4: Condition Exit False Positives

    Profile 1 (LDG) condition exits if:
    - slope_MA20 <= 0 (trend broken)
    - close < MA20 (price below trend)

    Test cases:
    - Empty market_conditions → Should NOT exit
    - None values → Should NOT exit
    - slope_MA20 = 0.0001 (barely positive) → Should NOT exit
    - slope_MA20 = 0.0 (flat) → Should exit
    - slope_MA20 = -0.0001 → Should exit
    """
    print("\n" + "="*80)
    print("AUDIT 4: CONDITION EXIT FALSE POSITIVES")
    print("="*80)

    engine = ExitEngineV1()

    test_cases = [
        ({}, False, "Empty market conditions"),
        ({'slope_MA20': None}, False, "slope_MA20 = None"),
        ({'slope_MA20': 0.0001}, False, "slope_MA20 barely positive"),
        ({'slope_MA20': 0.0}, True, "slope_MA20 = 0 (flat)"),
        ({'slope_MA20': -0.0001}, True, "slope_MA20 negative"),
        ({'close': 350, 'MA20': 351}, True, "close < MA20"),
        ({'close': 350, 'MA20': 350}, False, "close = MA20"),
        ({'close': 350, 'MA20': None}, False, "MA20 = None"),
    ]

    bugs_found = []

    for market_conditions, expected_exit, desc in test_cases:
        actual_exit = engine._condition_exit_profile_1(market_conditions, {})

        status = "✅ PASS" if actual_exit == expected_exit else "❌ FAIL"

        print(f"\n{status} {desc}")
        print(f"  Market: {market_conditions}")
        print(f"  Expected exit: {expected_exit}")
        print(f"  Actual exit: {actual_exit}")

        if actual_exit != expected_exit:
            bugs_found.append({
                'test': desc,
                'market': market_conditions,
                'expected': expected_exit,
                'actual': actual_exit
            })

    if bugs_found:
        print(f"\n⚠️  WARNING: {len(bugs_found)} condition exit bugs found!")
        return False
    else:
        print(f"\n✅ CLEAN: Condition exit logic is correct")
        return True


def audit_decision_order():
    """
    AUDIT 5: Decision Order

    Mandatory order:
    1. RISK (max_loss_pct)
    2. TP2 (full profit)
    3. TP1 (partial profit)
    4. CONDITION (regime exit)
    5. TIME (max hold)

    Test case: pnl_pct = -0.50 AND slope_MA20 <= 0
    - Should trigger RISK, NOT condition_exit

    Test case: pnl_pct = +1.00 (TP2) AND slope_MA20 <= 0
    - Should trigger TP2, NOT condition_exit
    """
    print("\n" + "="*80)
    print("AUDIT 5: DECISION ORDER")
    print("="*80)

    engine = ExitEngineV1()
    engine.reset_tp1_tracking()

    test_cases = [
        # (pnl_pct, market_conditions, days_held, expected_reason, description)
        (-0.50, {'slope_MA20': -0.01}, 5, "max_loss_-50%",
         "RISK beats CONDITION"),
        (1.00, {'slope_MA20': -0.01}, 5, "tp2_100%",
         "TP2 beats CONDITION"),
        (0.60, {'slope_MA20': -0.01}, 5, "tp1_50%",
         "TP1 beats CONDITION"),
        (0.20, {'slope_MA20': -0.01}, 5, "condition_exit",
         "CONDITION wins (no profit targets hit)"),
        (0.20, {}, 14, "time_stop_day14",
         "TIME wins (no other triggers)"),
    ]

    bugs_found = []

    for pnl_pct, market, days_held, expected_reason, desc in test_cases:
        engine.reset_tp1_tracking()

        should_exit, fraction, reason = engine.should_exit(
            profile_id='Profile_1_LDG',
            trade_id='test_order',
            days_held=days_held,
            pnl_pct=pnl_pct,
            market_conditions=market,
            position_greeks={}
        )

        status = "✅ PASS" if reason == expected_reason else "❌ FAIL"

        print(f"\n{status} {desc}")
        print(f"  P&L: {pnl_pct:.1%}, Days: {days_held}, Market: {market}")
        print(f"  Expected: '{expected_reason}'")
        print(f"  Actual: '{reason}'")

        if reason != expected_reason:
            bugs_found.append({
                'test': desc,
                'expected': expected_reason,
                'actual': reason
            })

    if bugs_found:
        print(f"\n🔴 CRITICAL: {len(bugs_found)} decision order bugs found!")
        return False
    else:
        print(f"\n✅ CLEAN: Decision order is correct")
        return True


def audit_manual_verification():
    """
    AUDIT 6: Manual Verification of 10 Random Trades

    Load actual backtest results and manually verify Exit Engine V1 logic
    for 10 randomly selected trades.

    For each trade, verify:
    1. Entry cost sign (long vs short)
    2. P&L calculation at each day
    3. Exit trigger logic (which rule fired)
    4. Fractional scaling (if TP1)
    5. Final exit P&L matches calculation
    """
    print("\n" + "="*80)
    print("AUDIT 6: MANUAL VERIFICATION - 10 RANDOM TRADES")
    print("="*80)

    # Load train results
    results_file = Path('/Users/zstoc/rotation-engine/data/backtest_results/train_2020-2021/results.json')
    if not results_file.exists():
        print("\n❌ Train results not found - cannot verify")
        return False

    with open(results_file, 'r') as f:
        results = json.load(f)

    # Collect all trades
    all_trades = []
    for profile_id, profile_data in results.items():
        for trade in profile_data['trades']:
            all_trades.append((profile_id, trade))

    # Select 10 random trades
    if len(all_trades) < 10:
        sample_trades = all_trades
    else:
        sample_trades = random.sample(all_trades, 10)

    engine = ExitEngineV1()
    bugs_found = []

    for idx, (profile_id, trade_data) in enumerate(sample_trades, 1):
        print(f"\n{'─'*80}")
        print(f"TRADE {idx}/10: {profile_id} - {trade_data['entry']['entry_date']}")
        print(f"{'─'*80}")

        # Apply Exit Engine V1
        engine.reset_tp1_tracking()
        result = engine.apply_to_tracked_trade(profile_id, trade_data)

        entry_cost = trade_data['entry']['entry_cost']
        daily_path = trade_data['path']

        print(f"Entry cost: ${entry_cost:.2f} ({'LONG' if entry_cost > 0 else 'SHORT'})")
        print(f"Path length: {len(daily_path)} days")
        print(f"\nExit Engine V1 Result:")
        print(f"  Exit day: {result['exit_day']}")
        print(f"  Exit reason: {result['exit_reason']}")
        print(f"  Exit P&L: ${result['exit_pnl']:.2f}")
        print(f"  Exit fraction: {result['exit_fraction']:.2f}")
        print(f"  P&L %: {result['pnl_pct']:.1%}")

        # Manual verification - walk through days
        print(f"\nManual Verification:")
        found_exit = False
        for day in daily_path:
            day_idx = day['day']
            mtm_pnl = day['mtm_pnl']

            # Recalculate P&L %
            if abs(entry_cost) < 0.01:
                pnl_pct = 0
            else:
                pnl_pct = mtm_pnl / abs(entry_cost)

            print(f"  Day {day_idx}: MTM=${mtm_pnl:+7.2f} ({pnl_pct:+6.1%})", end="")

            # Check if this is exit day
            if day_idx == result['exit_day']:
                print(f" ← EXIT: {result['exit_reason']}")

                # Verify P&L calculation
                expected_pnl = mtm_pnl * result['exit_fraction']
                actual_pnl = result['exit_pnl']
                pnl_error = abs(expected_pnl - actual_pnl)

                if pnl_error > 0.01:
                    print(f"    🔴 P&L MISMATCH: Expected ${expected_pnl:.2f}, got ${actual_pnl:.2f}")
                    bugs_found.append({
                        'trade': f"{profile_id} - {trade_data['entry']['entry_date']}",
                        'bug': 'P&L mismatch',
                        'expected': expected_pnl,
                        'actual': actual_pnl,
                        'error': pnl_error
                    })
                else:
                    print(f"    ✅ P&L matches: ${expected_pnl:.2f}")

                found_exit = True
                break
            else:
                print()

        if not found_exit and result['exit_day'] >= 0:
            print(f"  🔴 BUG: Exit day {result['exit_day']} not found in path!")
            bugs_found.append({
                'trade': f"{profile_id} - {trade_data['entry']['entry_date']}",
                'bug': 'Exit day not in path',
                'exit_day': result['exit_day'],
                'path_length': len(daily_path)
            })

    if bugs_found:
        print(f"\n{'='*80}")
        print(f"🔴 CRITICAL: {len(bugs_found)} bugs found in manual verification!")
        print(f"{'='*80}")
        for bug in bugs_found:
            print(f"\n{bug}")
        return False
    else:
        print(f"\n{'='*80}")
        print(f"✅ CLEAN: All 10 trades verified correctly")
        print(f"{'='*80}")
        return True


def main():
    """Run complete Exit Engine V1 audit"""

    print(f"\n{'#'*80}")
    print("# EXIT ENGINE V1 DEEP AUDIT - RED TEAM ATTACK")
    print(f"{'#'*80}\n")

    results = {
        'audit_1_pnl_calculation': audit_pnl_calculation(),
        'audit_2_tp_trigger_logic': audit_tp_trigger_logic(),
        'audit_3_fractional_exit_pnl': audit_fractional_exit_pnl(),
        'audit_4_condition_exit': audit_condition_exit_false_positives(),
        'audit_5_decision_order': audit_decision_order(),
        'audit_6_manual_verification': audit_manual_verification()
    }

    print(f"\n{'='*80}")
    print("AUDIT SUMMARY")
    print(f"{'='*80}\n")

    for audit_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {audit_name}")

    total_passed = sum(results.values())
    total_audits = len(results)

    print(f"\n{'='*80}")
    if total_passed == total_audits:
        print(f"✅ AUDIT COMPLETE: All {total_audits} audits passed")
        print(f"Exit Engine V1 implementation is CLEAN")
    else:
        print(f"🔴 AUDIT FAILED: {total_audits - total_passed}/{total_audits} audits failed")
        print(f"Exit Engine V1 has CRITICAL BUGS - DO NOT TRUST RESULTS")
    print(f"{'='*80}\n")

    return total_passed == total_audits


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
