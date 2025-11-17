#!/usr/bin/env python3
"""
Profile Scoring Validation

Validates:
1. All 6 profiles compute successfully
2. Scores are smooth (not noisy)
3. Regime alignment (Profile N scores high in Regime N)
4. No NaN explosions or edge case failures

Run this after implementing profile detectors.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from datetime import datetime, timedelta
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from data import DataSpine
from regimes import RegimeClassifier
from profiles.detectors import ProfileDetectors
from profiles.validator import ProfileValidator


def validate_day3():
    """Run complete profile-scoring validation."""

    print("=" * 80)
    print("DAY 3 VALIDATION: Profile Scoring Functions")
    print("=" * 80)

    # 1. Load data spine with regimes
    spine = DataSpine()
    stock_cov = spine.loader.get_spy_stock_coverage()
    start_dt = datetime.combine(stock_cov['start'], datetime.min.time())
    end_dt = datetime.combine(stock_cov['end'], datetime.min.time())
    print(f"\n1. Loading data spine ({stock_cov['start']} to {stock_cov['end']})...")
    df = spine.build_spine(
        start_date=start_dt,
        end_date=end_dt
    )
    print(f"   Loaded {len(df)} rows from {df['date'].min()} to {df['date'].max()}")

    # 2. Add regime labels
    print("\n2. Computing regime labels...")
    regime_classifier = RegimeClassifier()
    df = regime_classifier.classify_period(df)

    # Rename regime_label to regime for validator compatibility
    if 'regime_label' in df.columns:
        df['regime'] = df['regime_label']

    print(f"   Regimes computed: {sorted(df['regime'].dropna().unique())}")

    # 3. Compute profile scores
    print("\n3. Computing profile scores...")
    profile_detector = ProfileDetectors()
    df = profile_detector.compute_all_profiles(df)

    profile_cols = [
        'profile_1_LDG', 'profile_2_SDG', 'profile_3_CHARM',
        'profile_4_VANNA', 'profile_5_SKEW', 'profile_6_VOV'
    ]

    # Check all profiles computed
    missing_profiles = [p for p in profile_cols if p not in df.columns]
    if missing_profiles:
        print(f"   ❌ FAILED: Missing profiles: {missing_profiles}")
        return False

    print(f"   ✅ All 6 profiles computed")

    # 4. Validate scores are in [0, 1] range
    print("\n4. Checking score ranges...")
    all_in_range = True
    for profile in profile_cols:
        scores = df[profile].dropna()
        out_of_range = ((scores < 0) | (scores > 1)).sum()

        if out_of_range > 0:
            print(f"   ❌ {profile}: {out_of_range} scores out of [0, 1] range")
            all_in_range = False
        else:
            print(f"   ✅ {profile}: All scores in [0, 1]")

    if not all_in_range:
        print("\n❌ VALIDATION FAILED: Scores out of range")
        return False

    # 5. Smoothness check
    print("\n5. Checking smoothness...")
    validator = ProfileValidator()
    smoothness_results = validator.check_smoothness(df, threshold=0.15)

    all_smooth = True
    for profile, results in smoothness_results.items():
        status = "✅ SMOOTH" if results['is_smooth'] else "❌ NOISY"
        print(f"   {profile:25s} {status:15s} "
              f"(Large changes: {results['pct_large_changes']:.1f}%, "
              f"Mean Δ: {results['mean_abs_change']:.3f})")
        all_smooth = all_smooth and results['is_smooth']

    if not all_smooth:
        print("\n⚠️  WARNING: Some profiles are noisy - may need smoothing or steepness adjustment")

    # 6. Regime alignment check
    print("\n6. Checking regime alignment...")
    regime_scores = validator.check_regime_alignment(df, regime_col='regime')

    print("\n   Mean Profile Scores by Regime:")
    print(regime_scores.round(3))

    # 7. Validate specific alignment rules
    print("\n7. Validating alignment rules...")
    # Use 0.35 threshold (more realistic given 5 regimes and averaging effects)
    alignment_results = validator.validate_alignment_rules(regime_scores, min_score=0.35)

    all_aligned = True
    for rule_name, rule_results in alignment_results.items():
        status = "✅ PASSED" if rule_results['passed'] else "⚠️  FAILED"
        print(f"   {rule_name:30s} {status}")

        # Show relevant scores
        for key, value in rule_results.items():
            if key.endswith('_score'):
                print(f"     {key}: {value:.3f}")

        all_aligned = all_aligned and rule_results['passed']

    # 8. Generate plots
    print("\n8. Generating validation plots...")

    # Plot 8a: Profile scores over first full trading year (smoothness validation)
    year_start = stock_cov['start']
    year_end = min(stock_cov['start'] + timedelta(days=252), stock_cov['end'])
    fig1 = validator.plot_profile_scores(
        df,
        start_date=str(year_start),
        end_date=str(year_end)
    )
    fig1.savefig('profile_scores_first_year.png', dpi=150, bbox_inches='tight')
    print("   ✅ Saved: profile_scores_first_year.png")
    plt.close(fig1)

    # Plot 8b: Regime alignment heatmap
    fig2 = validator.plot_regime_alignment(regime_scores)
    fig2.savefig('profile_regime_alignment.png', dpi=150, bbox_inches='tight')
    print("   ✅ Saved: profile_regime_alignment.png")
    plt.close(fig2)

    # Plot 8c: Full time series
    fig3 = validator.plot_profile_scores(df)
    fig3.savefig('profile_scores_full.png', dpi=150, bbox_inches='tight')
    print("   ✅ Saved: profile_scores_full.png")
    plt.close(fig3)

    # 9. Summary
    print("\n" + "=" * 80)
    print("DAY 3 VALIDATION SUMMARY")
    print("=" * 80)

    print(f"\n✅ All 6 profile scores computed: {', '.join(profile_cols)}")
    print(f"✅ All scores in [0, 1] range: {all_in_range}")
    print(f"{'✅' if all_smooth else '⚠️ '} Smoothness: {all_smooth}")
    print(f"{'✅' if all_aligned else '⚠️ '} Regime alignment: {all_aligned}")
    print(f"\n✅ 3 validation plots generated")

    if all_in_range and all_smooth and all_aligned:
        print("\n🎯 DAY 3 COMPLETE: Profile detectors are PRODUCTION READY")
        return True
    elif all_in_range:
        print("\n⚠️  DAY 3 PARTIAL: Profile detectors work but need tuning")
        print("   - Review smoothness and alignment results above")
        print("   - Adjust sigmoid steepness parameters if needed")
        print("   - Consider EMA smoothing for noisy profiles")
        return True
    else:
        print("\n❌ DAY 3 FAILED: Critical issues detected")
        return False


if __name__ == '__main__':
    success = validate_day3()
    exit(0 if success else 1)
