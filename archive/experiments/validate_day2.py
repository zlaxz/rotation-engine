#!/usr/bin/env python3
"""Regime classification validation script.

Run this to verify regime classification is working correctly.
"""

import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data import DataSpine
from regimes import RegimeClassifier
from regimes.validator import RegimeValidator


def main():
    print("="*80)
    print("REGIME CLASSIFICATION VALIDATION")
    print("="*80)

    # Load data
    from datetime import datetime, timedelta
    spine = DataSpine()
    stock_cov = spine.loader.get_spy_stock_coverage()
    start_dt = datetime.combine(stock_cov['start'], datetime.min.time())
    end_dt = datetime.combine(stock_cov['end'], datetime.min.time())

    print(f"\n[1/5] Loading SPY data ({stock_cov['start']} to {stock_cov['end']})...")
    spy_data = spine.build_spine(
        start_date=start_dt,
        end_date=end_dt
    )
    print(f"      Loaded {len(spy_data)} days of SPY data")

    # Classify regimes
    print("\n[2/5] Classifying regimes (walk-forward)...")
    classifier = RegimeClassifier()
    df_classified = classifier.classify_period(spy_data)
    print(f"      Classified {len(df_classified)} days")
    print(f"      Unique regimes: {df_classified['regime_label'].nunique()}")

    # Compute statistics
    print("\n[3/5] Computing regime statistics...")
    stats = classifier.compute_regime_statistics(df_classified)

    validator = RegimeValidator()
    validator.print_regime_statistics(stats)

    # Historical validation
    print("\n[4/5] Validating historical regimes...")
    validation = classifier.validate_historical_regimes(df_classified)
    validator.print_validation_report(validation)

    # Sanity checks
    print("\n[5/5] Running sanity checks...")
    checks = validator.sanity_check_regimes(df_classified)
    validator.print_sanity_check_report(checks)

    # Summary
    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)

    total_validations = len(validation)
    validation_passed = sum(1 for v in validation.values() if v['passed'])
    total_sanity = len(checks)
    sanity_passed = sum(1 for c in checks.values() if c['passed'])

    print(f"\nHistorical Validation: {validation_passed}/{total_validations} passed")
    print(f"Sanity Checks: {sanity_passed}/{total_sanity} passed")

    if validation_passed == len(validation) and sanity_passed == len(checks):
        print("\n✅ ALL VALIDATIONS PASSED - Regime layer complete!")
    else:
        print("\n⚠️  Some validations failed - review results above")

    # Offer to create plots
    print("\n" + "="*80)
    if sys.stdin.isatty():
        response = input("\nCreate validation plots? (y/n): ").lower().strip()
    else:
        response = 'n'

    if response == 'y':
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt

        print("\nGenerating plots...")

        # Plot 1: Regime bands full coverage
        print("  - Regime bands (full period)...")
        fig1 = validator.plot_regime_bands(df_classified,
                                           start_date=str(stock_cov['start']),
                                           end_date=str(stock_cov['end']))
        fig1.savefig('regime_bands_full.png', dpi=150, bbox_inches='tight')
        plt.close(fig1)

        # Plot 2: First-year window
        print("  - Regime bands (first trading year)...")
        mid_window_end = stock_cov['start'] + timedelta(days=252)
        fig2 = validator.plot_regime_bands(df_classified,
                                           start_date=str(stock_cov['start']),
                                           end_date=str(min(mid_window_end, stock_cov['end'])))
        fig2.savefig('regime_bands_first_year.png', dpi=150, bbox_inches='tight')
        plt.close(fig2)

        # Plot 3: Regime statistics
        print("  - Regime statistics...")
        fig3 = validator.plot_regime_statistics(stats)
        fig3.savefig('regime_statistics.png', dpi=150, bbox_inches='tight')
        plt.close(fig3)

        print("\n✅ Plots saved:")
        print("   - regime_bands_full.png")
        print("   - regime_bands_first_year.png")
        print("   - regime_statistics.png")

    print("\n" + "="*80)


if __name__ == '__main__':
    main()
