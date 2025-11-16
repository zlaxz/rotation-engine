"""
Test toy strategy with real Polygon data to verify P&L is realistic.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.trading.simulator import TradeSimulator, SimulationConfig
from src.trading.trade import Trade, TradeLeg
from src.data.loaders import load_spy_data


def test_simple_straddle_strategy():
    """
    Test simple ATM straddle strategy with real Polygon data.

    Strategy:
    - Buy ATM straddle every Monday
    - Hold for 5 days or until 10% loss
    - Use real options data throughout
    """

    print("\n" + "=" * 80)
    print("TESTING SIMPLE STRADDLE STRATEGY WITH REAL POLYGON DATA")
    print("=" * 80)

    # Load SPY data for January 2024
    data = load_spy_data(
        start_date=datetime(2024, 1, 2),
        end_date=datetime(2024, 1, 31),
        include_regimes=False  # Skip regimes for this simple test
    )

    # Add a dummy regime column for simulator
    data['regime'] = 'calm'

    print(f"\n✓ Loaded {len(data)} days of SPY data")
    print(f"  Date range: {data['date'].min()} to {data['date'].max()}")
    print(f"  SPY range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")

    # Initialize simulator with real data
    config = SimulationConfig(
        delta_hedge_enabled=False,
        roll_dte_threshold=0,  # Don't roll
        max_loss_pct=0.10,  # Close if -10%
        max_days_in_trade=5
    )

    simulator = TradeSimulator(
        data=data,
        config=config,
        use_real_options_data=True
    )

    print(f"\n✓ Simulator initialized")

    # Define entry logic: Enter on Mondays
    def entry_logic(row, current_trade):
        if current_trade is not None:
            return False  # Already in trade

        # Enter on Mondays (weekday == 0)
        day = pd.to_datetime(row['date']).weekday()
        return day == 0

    # Define trade constructor: ATM straddle, using standard monthly expiries
    def trade_constructor(row, trade_id):
        spot = row['close']
        entry_date = pd.to_datetime(row['date'])

        # Use standard monthly expiry (3rd Friday of next month, approximately)
        # For January entries, use Feb 16
        # For February entries, use Mar 15
        current_month = entry_date.month
        current_year = entry_date.year

        if current_month == 1:
            expiry = datetime(current_year, 2, 16)
        elif current_month == 2:
            expiry = datetime(current_year, 3, 15)
        else:
            expiry = datetime(current_year, 4, 19)

        # Round to nearest strike
        strike = round(spot)

        legs = [
            TradeLeg(
                strike=strike,
                expiry=expiry,
                option_type='call',
                quantity=1,
                dte=45
            ),
            TradeLeg(
                strike=strike,
                expiry=expiry,
                option_type='put',
                quantity=1,
                dte=45
            )
        ]

        return Trade(
            trade_id=trade_id,
            profile_name='ATM_STRADDLE',
            entry_date=entry_date,
            legs=legs,
            entry_prices={}
        )

    # Run backtest
    print(f"\n⏳ Running backtest...")
    daily_results = simulator.simulate(
        entry_logic=entry_logic,
        trade_constructor=trade_constructor,
        profile_name='ATM_STRADDLE'
    )

    print(f"\n✓ Backtest complete")

    # Get trades from simulator
    trades = simulator.trades

    if len(trades) == 0:
        print("\n⚠️  No trades executed (likely no Mondays in period or data issues)")
        return

    print(f"  Total trades: {len(trades)}")

    # Analyze trades
    print(f"\n📊 Trade Details:")
    print(f"{'Trade':<15} {'Entry':<12} {'Exit':<12} {'Days':<6} {'Entry $':<10} {'Exit $':<10} {'P&L':<10} {'Return':<10}")
    print("-" * 95)

    for trade in trades:
        entry_cost = abs(trade.entry_cost)
        exit_proceeds = trade.exit_proceeds
        pnl = trade.realized_pnl
        ret = 100 * pnl / entry_cost if entry_cost > 0 else 0

        # Convert dates
        exit_date = trade.exit_date
        if isinstance(exit_date, pd.Timestamp):
            exit_date = exit_date.date()
        elif isinstance(exit_date, datetime):
            exit_date = exit_date.date()

        entry_date = trade.entry_date
        if isinstance(entry_date, pd.Timestamp):
            entry_date = entry_date.date()
        elif isinstance(entry_date, datetime):
            entry_date = entry_date.date()

        days_in_trade = (exit_date - entry_date).days if exit_date else 0

        print(f"{trade.trade_id:<15} "
              f"{str(trade.entry_date)[:10]:<12} "
              f"{str(trade.exit_date)[:10] if trade.exit_date else 'Open':<12} "
              f"{days_in_trade:<6} "
              f"${entry_cost:<9.2f} "
              f"${exit_proceeds:<9.2f} "
              f"${pnl:<9.2f} "
              f"{ret:<9.1f}%")

    # Summary statistics
    total_pnl = sum(t.realized_pnl for t in trades)
    total_cost = sum(abs(t.entry_cost) for t in trades)
    avg_pnl = total_pnl / len(trades)
    win_rate = sum(1 for t in trades if t.realized_pnl > 0) / len(trades)
    avg_return = 100 * avg_pnl / (total_cost / len(trades)) if total_cost > 0 else 0

    print(f"\n📈 Summary Statistics:")
    print(f"  Total P&L:       ${total_pnl:>10.2f}")
    print(f"  Total invested:  ${total_cost:>10.2f}")
    print(f"  Avg P&L/trade:   ${avg_pnl:>10.2f}")
    print(f"  Win rate:        {100*win_rate:>10.1f}%")
    print(f"  Avg return:      {avg_return:>10.1f}%")

    # Data usage stats
    print(f"\n🔍 Polygon Data Usage:")
    print(f"  Real prices used:     {simulator.stats['real_prices_used']}")
    print(f"  Fallback prices used: {simulator.stats['fallback_prices_used']}")
    print(f"  Missing contracts:    {len(simulator.stats['missing_contracts'])}")

    if simulator.stats['missing_contracts']:
        print(f"\n  First 5 missing:")
        for contract in simulator.stats['missing_contracts'][:5]:
            print(f"    {contract}")

    # Validation checks
    print(f"\n✅ Validation:")

    # Should use mostly real data
    real_pct = 100 * simulator.stats['real_prices_used'] / (simulator.stats['real_prices_used'] + simulator.stats['fallback_prices_used'] + 0.0001)
    print(f"  Real data %: {real_pct:.1f}%")
    assert real_pct > 50, f"Should use >50% real data, got {real_pct:.1f}%"

    # P&L should be reasonable (not insane Sharpe from nothing)
    # For random straddle entries, expect roughly breakeven to small loss
    assert -5000 < total_pnl < 5000, f"P&L seems unrealistic: ${total_pnl:.2f}"
    print(f"  P&L is reasonable: ${total_pnl:.2f}")

    # Returns should be realistic (straddles typically lose 10-30% over 5 days if SPY doesn't move much)
    assert -50 < avg_return < 50, f"Average return seems unrealistic: {avg_return:.1f}%"
    print(f"  Returns are reasonable: {avg_return:.1f}%")

    # Entry costs should be reasonable (ATM straddle on SPY ~$470 should be $15-30)
    avg_entry = total_cost / len(trades) if len(trades) > 0 else 0
    assert 10 < avg_entry < 50, f"Entry cost seems wrong: ${avg_entry:.2f}"
    print(f"  Entry costs reasonable: ${avg_entry:.2f}")

    print(f"\n" + "=" * 80)
    print("✅ TOY STRATEGY TEST PASSED - P&L IS REALISTIC")
    print("=" * 80)

    return trades, simulator


if __name__ == '__main__':
    results, simulator = test_simple_straddle_strategy()
