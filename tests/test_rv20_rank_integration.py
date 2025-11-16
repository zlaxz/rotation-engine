"""Test that RV20_rank column is properly integrated between signals and classifier.

This test validates the fix for the integration bug where RegimeClassifier
expected RV20_rank but RegimeSignals was creating RV20_percentile.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.loaders import load_spy_data
from src.regimes.classifier import RegimeClassifier


def test_rv20_rank_exists_in_signals():
    """Test that RV20_rank is created by signal calculator."""
    print("Test 1: RV20_rank exists in computed signals")

    df = load_spy_data(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        include_regimes=True
    )

    assert 'RV20_rank' in df.columns, "RV20_rank column missing from signals"
    assert len(df) > 0, "No data loaded"
    assert df['RV20_rank'].notna().any(), "RV20_rank has no valid values"

    # Verify values are in [0, 1] range (percentile)
    assert df['RV20_rank'].min() >= 0.0, "RV20_rank has values < 0"
    assert df['RV20_rank'].max() <= 1.0, "RV20_rank has values > 1"

    print(f"  ✅ RV20_rank exists with {len(df)} rows")
    print(f"     Range: [{df['RV20_rank'].min():.3f}, {df['RV20_rank'].max():.3f}]")


def test_classifier_can_access_rv20_rank():
    """Test that classifier can access RV20_rank without KeyError."""
    print("\nTest 2: Classifier can classify regimes without KeyError")

    df = load_spy_data(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 2, 29),
        include_regimes=True
    )

    # If we got here without KeyError, the integration works
    assert 'regime_label' in df.columns, "regime_label not created"
    assert 'regime_name' in df.columns, "regime_name not created"

    # Verify regimes are valid (1-6)
    valid_regimes = df['regime_label'].between(1, 6)
    assert valid_regimes.all(), "Invalid regime labels found"

    regime_counts = df['regime_name'].value_counts()
    print(f"  ✅ Classified {len(df)} days into {len(regime_counts)} regimes")
    print(f"     Regime distribution:")
    for regime, count in regime_counts.items():
        pct = 100 * count / len(df)
        print(f"       {regime}: {count} days ({pct:.1f}%)")


def test_no_rv20_percentile_column():
    """Test that old RV20_percentile column doesn't exist (verify rename)."""
    print("\nTest 3: Old RV20_percentile column removed")

    df = load_spy_data(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        include_regimes=True
    )

    assert 'RV20_percentile' not in df.columns, "Old RV20_percentile column still exists"
    print("  ✅ RV20_percentile column successfully renamed to RV20_rank")


if __name__ == '__main__':
    print("=" * 70)
    print("INTEGRATION TEST: RV20_rank Column")
    print("=" * 70)

    try:
        test_rv20_rank_exists_in_signals()
        test_classifier_can_access_rv20_rank()
        test_no_rv20_percentile_column()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✅")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
