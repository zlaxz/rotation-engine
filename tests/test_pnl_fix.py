#!/usr/bin/env python3
"""
Test script for BUG-C01 fix: P&L sign convention
Tests that P&L calculations produce correct signs for various option strategies.

CORRECT BEHAVIOR:
- Long positions: profit when exit_price > entry_price → positive P&L
- Short positions: profit when entry_price > exit_price → positive P&L
"""

from datetime import datetime, timedelta
from src.trading.trade import Trade, TradeLeg, create_straddle_trade, create_strangle_trade, create_spread_trade


def test_long_call_profit():
    """Test Case 1: Long call that profits"""
    print("\n" + "="*70)
    print("TEST 1: LONG CALL - PROFITABLE")
    print("="*70)

    entry_date = datetime(2024, 1, 1)
    expiry = entry_date + timedelta(days=30)

    # Create long call
    legs = [TradeLeg(strike=400.0, expiry=expiry, option_type='call', quantity=1, dte=30)]
    trade = Trade(
        trade_id="test_001",
        profile_name="test",
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: 2.50}  # Buy call @ $2.50
    )

    print(f"Entry: BUY 1 Call @ $2.50")
    print(f"Entry cost: ${trade.entry_cost:.2f}")

    # Close at profit
    exit_date = entry_date + timedelta(days=10)
    trade.close(exit_date=exit_date, exit_prices={0: 4.00}, reason="profit_target")  # Sell @ $4.00

    print(f"Exit:  SELL 1 Call @ $4.00")
    print(f"Exit proceeds: ${trade.exit_proceeds:.2f}")
    print(f"Realized P&L: ${trade.realized_pnl:.2f}")

    expected_pnl = 1.50  # 1 × ($4.00 - $2.50) = +$1.50
    print(f"\nExpected P&L: ${expected_pnl:.2f}")

    assert trade.realized_pnl > 0, "❌ FAIL: Long call profit should be POSITIVE!"
    assert abs(trade.realized_pnl - expected_pnl) < 0.01, f"❌ FAIL: P&L should be ${expected_pnl:.2f}, got ${trade.realized_pnl:.2f}"
    print("✅ PASS: Long call profit is positive")


def test_long_call_loss():
    """Test Case 2: Long call that loses"""
    print("\n" + "="*70)
    print("TEST 2: LONG CALL - LOSS")
    print("="*70)

    entry_date = datetime(2024, 1, 1)
    expiry = entry_date + timedelta(days=30)

    legs = [TradeLeg(strike=400.0, expiry=expiry, option_type='call', quantity=1, dte=30)]
    trade = Trade(
        trade_id="test_002",
        profile_name="test",
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: 3.00}  # Buy call @ $3.00
    )

    print(f"Entry: BUY 1 Call @ $3.00")
    print(f"Entry cost: ${trade.entry_cost:.2f}")

    # Close at loss
    exit_date = entry_date + timedelta(days=10)
    trade.close(exit_date=exit_date, exit_prices={0: 1.50}, reason="stop_loss")  # Sell @ $1.50

    print(f"Exit:  SELL 1 Call @ $1.50")
    print(f"Exit proceeds: ${trade.exit_proceeds:.2f}")
    print(f"Realized P&L: ${trade.realized_pnl:.2f}")

    expected_pnl = -1.50  # 1 × ($1.50 - $3.00) = -$1.50
    print(f"\nExpected P&L: ${expected_pnl:.2f}")

    assert trade.realized_pnl < 0, "❌ FAIL: Long call loss should be NEGATIVE!"
    assert abs(trade.realized_pnl - expected_pnl) < 0.01, f"❌ FAIL: P&L should be ${expected_pnl:.2f}, got ${trade.realized_pnl:.2f}"
    print("✅ PASS: Long call loss is negative")


def test_short_put_profit():
    """Test Case 3: Short put that profits (expires worthless)"""
    print("\n" + "="*70)
    print("TEST 3: SHORT PUT - PROFITABLE")
    print("="*70)

    entry_date = datetime(2024, 1, 1)
    expiry = entry_date + timedelta(days=30)

    # Create short put (negative quantity)
    legs = [TradeLeg(strike=390.0, expiry=expiry, option_type='put', quantity=-1, dte=30)]
    trade = Trade(
        trade_id="test_003",
        profile_name="test",
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: 2.00}  # Sell put @ $2.00
    )

    print(f"Entry: SELL 1 Put @ $2.00")
    print(f"Entry cost: ${trade.entry_cost:.2f} (negative = credit received)")

    # Close at profit (buy back cheaper)
    exit_date = entry_date + timedelta(days=10)
    trade.close(exit_date=exit_date, exit_prices={0: 0.50}, reason="profit_target")  # Buy @ $0.50

    print(f"Exit:  BUY 1 Put @ $0.50")
    print(f"Exit proceeds: ${trade.exit_proceeds:.2f}")
    print(f"Realized P&L: ${trade.realized_pnl:.2f}")

    expected_pnl = 1.50  # -1 × ($0.50 - $2.00) = -1 × (-$1.50) = +$1.50
    print(f"\nExpected P&L: ${expected_pnl:.2f}")

    assert trade.realized_pnl > 0, "❌ FAIL: Short put profit should be POSITIVE!"
    assert abs(trade.realized_pnl - expected_pnl) < 0.01, f"❌ FAIL: P&L should be ${expected_pnl:.2f}, got ${trade.realized_pnl:.2f}"
    print("✅ PASS: Short put profit is positive")


def test_short_put_loss():
    """Test Case 4: Short put that loses (stock crashes)"""
    print("\n" + "="*70)
    print("TEST 4: SHORT PUT - LOSS")
    print("="*70)

    entry_date = datetime(2024, 1, 1)
    expiry = entry_date + timedelta(days=30)

    legs = [TradeLeg(strike=390.0, expiry=expiry, option_type='put', quantity=-1, dte=30)]
    trade = Trade(
        trade_id="test_004",
        profile_name="test",
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: 2.00}  # Sell put @ $2.00
    )

    print(f"Entry: SELL 1 Put @ $2.00")
    print(f"Entry cost: ${trade.entry_cost:.2f} (negative = credit received)")

    # Close at loss (buy back more expensive)
    exit_date = entry_date + timedelta(days=10)
    trade.close(exit_date=exit_date, exit_prices={0: 8.00}, reason="stop_loss")  # Buy @ $8.00

    print(f"Exit:  BUY 1 Put @ $8.00")
    print(f"Exit proceeds: ${trade.exit_proceeds:.2f}")
    print(f"Realized P&L: ${trade.realized_pnl:.2f}")

    expected_pnl = -6.00  # -1 × ($8.00 - $2.00) = -1 × $6.00 = -$6.00
    print(f"\nExpected P&L: ${expected_pnl:.2f}")

    assert trade.realized_pnl < 0, "❌ FAIL: Short put loss should be NEGATIVE!"
    assert abs(trade.realized_pnl - expected_pnl) < 0.01, f"❌ FAIL: P&L should be ${expected_pnl:.2f}, got ${trade.realized_pnl:.2f}"
    print("✅ PASS: Short put loss is negative")


def test_long_straddle_profit():
    """Test Case 5: Long straddle that profits (documented bug case)"""
    print("\n" + "="*70)
    print("TEST 5: LONG STRADDLE - PROFITABLE (Original Bug Case)")
    print("="*70)

    entry_date = datetime(2024, 1, 1)
    expiry = entry_date + timedelta(days=30)

    # Create long straddle (call + put at same strike)
    legs = [
        TradeLeg(strike=400.0, expiry=expiry, option_type='call', quantity=1, dte=30),
        TradeLeg(strike=400.0, expiry=expiry, option_type='put', quantity=1, dte=30)
    ]
    trade = Trade(
        trade_id="test_005",
        profile_name="test",
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: 2.50, 1: 3.00}  # Buy call @ $2.50, put @ $3.00
    )

    print(f"Entry: BUY 1 Call @ $2.50, BUY 1 Put @ $3.00")
    print(f"Total entry cost: ${trade.entry_cost:.2f}")

    # Close at profit
    exit_date = entry_date + timedelta(days=10)
    trade.close(exit_date=exit_date, exit_prices={0: 4.00, 1: 2.00}, reason="profit_target")

    print(f"Exit:  SELL 1 Call @ $4.00, SELL 1 Put @ $2.00")
    print(f"Total exit proceeds: ${trade.exit_proceeds:.2f}")
    print(f"Realized P&L: ${trade.realized_pnl:.2f}")

    # Call P&L: 1 × ($4.00 - $2.50) = +$1.50
    # Put P&L:  1 × ($2.00 - $3.00) = -$1.00
    # Total:    +$1.50 - $1.00 = +$0.50
    expected_pnl = 0.50
    print(f"\nExpected P&L: ${expected_pnl:.2f}")

    assert trade.realized_pnl > 0, "❌ FAIL: Long straddle profit should be POSITIVE!"
    assert abs(trade.realized_pnl - expected_pnl) < 0.01, f"❌ FAIL: P&L should be ${expected_pnl:.2f}, got ${trade.realized_pnl:.2f}"
    print("✅ PASS: Long straddle profit is positive (BUG FIXED!)")


def test_short_strangle_profit():
    """Test Case 6: Short strangle that profits (documented bug case)"""
    print("\n" + "="*70)
    print("TEST 6: SHORT STRANGLE - PROFITABLE (Original Bug Case)")
    print("="*70)

    entry_date = datetime(2024, 1, 1)
    expiry = entry_date + timedelta(days=30)

    # Create short strangle (sell OTM call + put)
    legs = [
        TradeLeg(strike=410.0, expiry=expiry, option_type='call', quantity=-1, dte=30),
        TradeLeg(strike=390.0, expiry=expiry, option_type='put', quantity=-1, dte=30)
    ]
    trade = Trade(
        trade_id="test_006",
        profile_name="test",
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: 2.00, 1: 1.50}  # Sell call @ $2.00, put @ $1.50
    )

    print(f"Entry: SELL 1 Call @ $2.00, SELL 1 Put @ $1.50")
    print(f"Total entry cost: ${trade.entry_cost:.2f} (negative = credit received)")

    # Close at profit (buy back cheaper)
    exit_date = entry_date + timedelta(days=10)
    trade.close(exit_date=exit_date, exit_prices={0: 1.00, 1: 0.50}, reason="profit_target")

    print(f"Exit:  BUY 1 Call @ $1.00, BUY 1 Put @ $0.50")
    print(f"Total exit proceeds: ${trade.exit_proceeds:.2f}")
    print(f"Realized P&L: ${trade.realized_pnl:.2f}")

    # Call P&L: -1 × ($1.00 - $2.00) = -1 × (-$1.00) = +$1.00
    # Put P&L:  -1 × ($0.50 - $1.50) = -1 × (-$1.00) = +$1.00
    # Total:    +$1.00 + $1.00 = +$2.00
    expected_pnl = 2.00
    print(f"\nExpected P&L: ${expected_pnl:.2f}")

    assert trade.realized_pnl > 0, "❌ FAIL: Short strangle profit should be POSITIVE!"
    assert abs(trade.realized_pnl - expected_pnl) < 0.01, f"❌ FAIL: P&L should be ${expected_pnl:.2f}, got ${trade.realized_pnl:.2f}"
    print("✅ PASS: Short strangle profit is positive (BUG FIXED!)")


def test_vertical_spread_profit():
    """Test Case 7: Bull call spread that profits"""
    print("\n" + "="*70)
    print("TEST 7: BULL CALL SPREAD - PROFITABLE")
    print("="*70)

    entry_date = datetime(2024, 1, 1)
    expiry = entry_date + timedelta(days=30)

    # Bull call spread: Long 400 call, Short 410 call
    legs = [
        TradeLeg(strike=400.0, expiry=expiry, option_type='call', quantity=1, dte=30),   # Long
        TradeLeg(strike=410.0, expiry=expiry, option_type='call', quantity=-1, dte=30)   # Short
    ]
    trade = Trade(
        trade_id="test_007",
        profile_name="test",
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: 5.00, 1: 2.00}  # Buy 400C @ $5, Sell 410C @ $2
    )

    print(f"Entry: BUY 400 Call @ $5.00, SELL 410 Call @ $2.00")
    print(f"Net entry cost: ${trade.entry_cost:.2f} (net debit)")

    # Close at max profit (stock at 410+)
    exit_date = entry_date + timedelta(days=10)
    trade.close(exit_date=exit_date, exit_prices={0: 12.00, 1: 2.00}, reason="profit_target")

    print(f"Exit:  SELL 400 Call @ $12.00, BUY 410 Call @ $2.00")
    print(f"Net exit proceeds: ${trade.exit_proceeds:.2f}")
    print(f"Realized P&L: ${trade.realized_pnl:.2f}")

    # Long 400C P&L:  +1 × ($12.00 - $5.00) = +$7.00
    # Short 410C P&L: -1 × ($2.00 - $2.00) = $0.00
    # Total: +$7.00
    expected_pnl = 7.00
    print(f"\nExpected P&L: ${expected_pnl:.2f}")

    assert trade.realized_pnl > 0, "❌ FAIL: Bull call spread profit should be POSITIVE!"
    assert abs(trade.realized_pnl - expected_pnl) < 0.01, f"❌ FAIL: P&L should be ${expected_pnl:.2f}, got ${trade.realized_pnl:.2f}"
    print("✅ PASS: Bull call spread profit is positive")


def test_mark_to_market_unrealized():
    """Test Case 8: Mark-to-market unrealized P&L"""
    print("\n" + "="*70)
    print("TEST 8: MARK-TO-MARKET - UNREALIZED P&L")
    print("="*70)

    entry_date = datetime(2024, 1, 1)
    expiry = entry_date + timedelta(days=30)

    # Long call
    legs = [TradeLeg(strike=400.0, expiry=expiry, option_type='call', quantity=1, dte=30)]
    trade = Trade(
        trade_id="test_008",
        profile_name="test",
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: 3.00}  # Buy @ $3.00
    )

    print(f"Entry: BUY 1 Call @ $3.00")
    print(f"Position is OPEN")

    # Mark to market at higher price (unrealized gain)
    mtm_pnl_profit = trade.mark_to_market({0: 5.00})
    print(f"\nMark-to-market @ $5.00: ${mtm_pnl_profit:.2f}")
    expected_mtm_profit = 2.00  # 1 × ($5.00 - $3.00) = +$2.00

    assert mtm_pnl_profit > 0, "❌ FAIL: Unrealized profit should be POSITIVE!"
    assert abs(mtm_pnl_profit - expected_mtm_profit) < 0.01, f"❌ FAIL: MTM should be ${expected_mtm_profit:.2f}, got ${mtm_pnl_profit:.2f}"
    print(f"✅ PASS: Unrealized profit is positive (expected ${expected_mtm_profit:.2f})")

    # Mark to market at lower price (unrealized loss)
    mtm_pnl_loss = trade.mark_to_market({0: 1.50})
    print(f"\nMark-to-market @ $1.50: ${mtm_pnl_loss:.2f}")
    expected_mtm_loss = -1.50  # 1 × ($1.50 - $3.00) = -$1.50

    assert mtm_pnl_loss < 0, "❌ FAIL: Unrealized loss should be NEGATIVE!"
    assert abs(mtm_pnl_loss - expected_mtm_loss) < 0.01, f"❌ FAIL: MTM should be ${expected_mtm_loss:.2f}, got ${mtm_pnl_loss:.2f}"
    print(f"✅ PASS: Unrealized loss is negative (expected ${expected_mtm_loss:.2f})")

    # After closing, MTM should return realized P&L
    trade.close(exit_date=entry_date + timedelta(days=10), exit_prices={0: 5.00}, reason="test")
    mtm_after_close = trade.mark_to_market({0: 999.99})  # Price shouldn't matter after close

    print(f"\nAfter closing @ $5.00:")
    print(f"Realized P&L: ${trade.realized_pnl:.2f}")
    print(f"Mark-to-market (should equal realized): ${mtm_after_close:.2f}")

    assert abs(mtm_after_close - trade.realized_pnl) < 0.01, "❌ FAIL: MTM after close should equal realized P&L!"
    print("✅ PASS: MTM after close equals realized P&L")


def test_hedge_cost_deduction():
    """Test Case 9: P&L with hedge costs"""
    print("\n" + "="*70)
    print("TEST 9: P&L WITH HEDGE COSTS")
    print("="*70)

    entry_date = datetime(2024, 1, 1)
    expiry = entry_date + timedelta(days=30)

    legs = [TradeLeg(strike=400.0, expiry=expiry, option_type='call', quantity=1, dte=30)]
    trade = Trade(
        trade_id="test_009",
        profile_name="test",
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: 3.00}
    )

    print(f"Entry: BUY 1 Call @ $3.00")

    # Add hedge costs
    trade.add_hedge_cost(0.50)  # First hedge
    trade.add_hedge_cost(0.30)  # Second hedge
    total_hedge_cost = 0.80
    print(f"Cumulative hedge costs: ${total_hedge_cost:.2f}")

    # Close at profit
    trade.close(exit_date=entry_date + timedelta(days=10), exit_prices={0: 5.00}, reason="profit_target")

    print(f"Exit:  SELL 1 Call @ $5.00")
    print(f"Realized P&L (after hedge costs): ${trade.realized_pnl:.2f}")

    # Gross P&L: 1 × ($5.00 - $3.00) = +$2.00
    # Net P&L:   $2.00 - $0.80 = +$1.20
    expected_pnl = 1.20
    print(f"\nExpected P&L (gross $2.00 - hedge $0.80): ${expected_pnl:.2f}")

    assert trade.realized_pnl > 0, "❌ FAIL: P&L after hedge costs should still be POSITIVE!"
    assert abs(trade.realized_pnl - expected_pnl) < 0.01, f"❌ FAIL: P&L should be ${expected_pnl:.2f}, got ${trade.realized_pnl:.2f}"
    print("✅ PASS: Hedge costs properly deducted from P&L")


def main():
    """Run all P&L tests"""
    print("\n" + "="*70)
    print("BUG-C01 FIX VALIDATION: P&L SIGN CONVENTION")
    print("="*70)
    print("\nTesting that P&L calculations produce CORRECT signs:")
    print("- Long positions: profit when exit > entry → POSITIVE P&L")
    print("- Short positions: profit when entry > exit → POSITIVE P&L")

    all_tests = [
        ("Long Call Profit", test_long_call_profit),
        ("Long Call Loss", test_long_call_loss),
        ("Short Put Profit", test_short_put_profit),
        ("Short Put Loss", test_short_put_loss),
        ("Long Straddle Profit (Original Bug)", test_long_straddle_profit),
        ("Short Strangle Profit (Original Bug)", test_short_strangle_profit),
        ("Bull Call Spread Profit", test_vertical_spread_profit),
        ("Mark-to-Market Unrealized", test_mark_to_market_unrealized),
        ("P&L with Hedge Costs", test_hedge_cost_deduction),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in all_tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {test_name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {e}")
            failed += 1

    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"✅ Passed: {passed}/{len(all_tests)}")
    print(f"❌ Failed: {failed}/{len(all_tests)}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! BUG-C01 IS FIXED!")
        print("\nSign Convention Summary:")
        print("- entry_cost = qty × entry_price (positive for long, negative for short)")
        print("- P&L = qty × (exit_price - entry_price)")
        print("- This naturally produces correct signs for all positions")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - BUG NOT FULLY FIXED")
        return 1


if __name__ == "__main__":
    exit(main())
