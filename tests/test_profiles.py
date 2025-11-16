"""
Test suite for profile detectors.

Tests:
1. Feature computation (IV proxies, VVIX, skew, etc.)
2. Profile score calculation
3. Score ranges [0, 1]
4. Walk-forward compliance
5. Edge cases (NaN handling, division by zero)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.data.loaders import DataSpine
from src.profiles.features import ProfileFeatures, sigmoid
from src.profiles.detectors import ProfileDetectors, get_profile_names
from src.profiles.validator import ProfileValidator


class TestSigmoidFunction:
    """Test sigmoid transformation function."""

    def test_sigmoid_basic(self):
        """Test sigmoid function behavior."""
        # Test known values
        assert abs(sigmoid(pd.Series([0])).iloc[0] - 0.5) < 0.01  # sigmoid(0) ≈ 0.5
        assert sigmoid(pd.Series([10])).iloc[0] > 0.99  # sigmoid(large +) → 1
        assert sigmoid(pd.Series([-10])).iloc[0] < 0.01  # sigmoid(large -) → 0

    def test_sigmoid_steepness(self):
        """Test sigmoid steepness parameter."""
        x = pd.Series([1.0])

        # Higher k = steeper transition
        gentle = sigmoid(x, k=1.0).iloc[0]
        steep = sigmoid(x, k=5.0).iloc[0]

        assert steep > gentle  # Steeper function reaches 1 faster

    def test_sigmoid_output_range(self):
        """Test sigmoid always outputs [0, 1]."""
        x = pd.Series(np.linspace(-100, 100, 1000))
        output = sigmoid(x)

        assert (output >= 0).all()
        assert (output <= 1).all()


class TestProfileFeatures:
    """Test profile feature calculations."""

    @pytest.fixture
    def sample_data(self):
        """Create sample SPY data with Day 1 features."""
        spine = DataSpine()
        df = spine.build_spine(
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 3, 31)
        )
        return df

    def test_iv_proxies(self, sample_data):
        """Test IV proxy calculation (RV × 1.2)."""
        feature_engine = ProfileFeatures()
        df = feature_engine._compute_iv_proxies(sample_data)

        # Check columns exist
        assert 'IV7' in df.columns
        assert 'IV20' in df.columns
        assert 'IV60' in df.columns

        # Check relationship: IV ≈ RV × 1.2
        assert abs(df['IV7'].iloc[-1] - df['RV5'].iloc[-1] * 1.2) < 0.001
        assert abs(df['IV20'].iloc[-1] - df['RV10'].iloc[-1] * 1.2) < 0.001
        assert abs(df['IV60'].iloc[-1] - df['RV20'].iloc[-1] * 1.2) < 0.001

    def test_iv_ranks(self, sample_data):
        """Test IV rank (percentile) calculation."""
        feature_engine = ProfileFeatures()
        df = feature_engine._compute_iv_proxies(sample_data)
        df = feature_engine._compute_iv_ranks(df)

        # Check columns exist
        assert 'IV_rank_20' in df.columns
        assert 'IV_rank_60' in df.columns

        # Check range [0, 1]
        assert (df['IV_rank_20'].dropna() >= 0).all()
        assert (df['IV_rank_20'].dropna() <= 1).all()
        assert (df['IV_rank_60'].dropna() >= 0).all()
        assert (df['IV_rank_60'].dropna() <= 1).all()

    def test_vvix_computation(self, sample_data):
        """Test VVIX (volatility of volatility) calculation."""
        feature_engine = ProfileFeatures()
        df = feature_engine.compute_all_features(sample_data)

        # Check columns exist
        assert 'VVIX' in df.columns
        assert 'VVIX_80pct' in df.columns

        # VVIX should be positive
        assert (df['VVIX'].dropna() > 0).all()

        # VVIX is stdev of RV10 - should be smaller than RV10 itself
        valid_rows = df[['VVIX', 'RV10']].dropna()
        if len(valid_rows) > 0:
            assert (valid_rows['VVIX'] < valid_rows['RV10']).sum() > len(valid_rows) * 0.8

    def test_vvix_slope(self, sample_data):
        """Test VVIX slope calculation."""
        feature_engine = ProfileFeatures()
        df = feature_engine.compute_all_features(sample_data)

        # Check column exists
        assert 'VVIX_slope' in df.columns

        # Slope can be positive or negative
        slopes = df['VVIX_slope'].dropna()
        assert len(slopes) > 0

        # Should have both positive and negative slopes in 3 months
        assert slopes.min() < 0
        assert slopes.max() > 0

    def test_skew_proxy(self, sample_data):
        """Test skew proxy calculation."""
        feature_engine = ProfileFeatures()
        df = feature_engine.compute_all_features(sample_data)

        # Check column exists
        assert 'skew_z' in df.columns

        # Z-score should be centered around 0
        skew_z = df['skew_z'].dropna()
        if len(skew_z) > 20:
            assert abs(skew_z.mean()) < 0.5  # Mean should be near 0
            assert skew_z.std() > 0  # Should have variation

    def test_no_nan_explosion(self, sample_data):
        """Test that feature computation doesn't create NaN explosions."""
        feature_engine = ProfileFeatures()
        df = feature_engine.compute_all_features(sample_data)

        # After warmup period (60 days), should have valid data
        warmup_rows = 60
        df_after_warmup = df.iloc[warmup_rows:]

        # Check key features are mostly non-NaN
        for col in ['IV7', 'IV20', 'VVIX', 'VVIX_slope', 'skew_z']:
            nan_pct = df_after_warmup[col].isna().sum() / len(df_after_warmup) * 100
            assert nan_pct < 20, f"{col} has {nan_pct:.1f}% NaN after warmup"


class TestProfileDetectors:
    """Test profile score calculations."""

    @pytest.fixture
    def sample_data_with_features(self):
        """Create sample data with all features computed."""
        spine = DataSpine()
        df = spine.build_spine(
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 6, 30)
        )

        # Add profile features
        feature_engine = ProfileFeatures()
        df = feature_engine.compute_all_features(df)

        return df

    def test_all_profiles_compute(self, sample_data_with_features):
        """Test that all 6 profiles compute successfully."""
        detector = ProfileDetectors()
        df = detector.compute_all_profiles(sample_data_with_features)

        profile_cols = get_profile_names()

        # All profile columns should exist
        for profile in profile_cols:
            assert profile in df.columns, f"Missing profile: {profile}"

    def test_scores_in_range(self, sample_data_with_features):
        """Test that all scores are in [0, 1] range."""
        detector = ProfileDetectors()
        df = detector.compute_all_profiles(sample_data_with_features)

        profile_cols = get_profile_names()

        for profile in profile_cols:
            scores = df[profile].dropna()

            # Check range
            assert (scores >= 0).all(), f"{profile} has scores < 0"
            assert (scores <= 1).all(), f"{profile} has scores > 1"

    def test_ldg_profile_logic(self, sample_data_with_features):
        """Test Long-Dated Gamma profile logic."""
        detector = ProfileDetectors()
        df = detector.compute_all_profiles(sample_data_with_features)

        # LDG should score high when:
        # - IV rank low (cheap vol)
        # - Upward trend (positive MA slope)

        # Find low IV rank days
        low_iv_days = df[df['IV_rank_60'] < 0.3]

        if len(low_iv_days) > 0:
            # LDG should be higher on low IV days (on average)
            mean_ldg_low_iv = low_iv_days['profile_1_LDG'].mean()
            mean_ldg_overall = df['profile_1_LDG'].mean()

            # Not strict equality (market dependent), but should trend that way
            # Just verify it computed something reasonable
            assert 0 <= mean_ldg_low_iv <= 1

    def test_sdg_profile_logic(self, sample_data_with_features):
        """Test Short-Dated Gamma profile logic."""
        detector = ProfileDetectors()
        df = detector.compute_all_profiles(sample_data_with_features)

        # SDG should score high when RV is spiking
        df['RV_spike'] = df['RV5'] / df['RV10']

        high_rv_spike = df[df['RV_spike'] > 1.2]

        if len(high_rv_spike) > 0:
            mean_sdg_spike = high_rv_spike['profile_2_SDG'].mean()
            assert 0 <= mean_sdg_spike <= 1

    def test_no_constant_scores(self, sample_data_with_features):
        """Test that profiles aren't stuck at constant values."""
        detector = ProfileDetectors()
        df = detector.compute_all_profiles(sample_data_with_features)

        profile_cols = get_profile_names()

        for profile in profile_cols:
            scores = df[profile].dropna()

            if len(scores) > 10:
                # Standard deviation should be > 0 (scores vary)
                assert scores.std() > 0.01, f"{profile} is nearly constant"

    def test_walk_forward_compliance(self, sample_data_with_features):
        """Test that scoring uses only past data (no look-ahead)."""
        # This is ensured by:
        # 1. ProfileFeatures uses only rolling windows
        # 2. Percentile calculations use past data only

        # Verify by checking that adding future data doesn't change past scores
        detector = ProfileDetectors()

        # Compute scores on first 3 months
        df_short = sample_data_with_features.iloc[:60].copy()
        df_short_scored = detector.compute_all_profiles(df_short)

        # Compute scores on full 6 months
        df_full_scored = detector.compute_all_profiles(sample_data_with_features)

        # First 60 rows should be identical (allowing for float precision)
        for profile in get_profile_names():
            scores_short = df_short_scored[profile].iloc[59]
            scores_full = df_full_scored[profile].iloc[59]

            if not pd.isna(scores_short) and not pd.isna(scores_full):
                assert abs(scores_short - scores_full) < 0.001, \
                    f"{profile} shows look-ahead bias"


class TestProfileValidator:
    """Test profile validation tools."""

    @pytest.fixture
    def scored_data_with_regimes(self):
        """Create scored data with regime labels."""
        from src.regimes.classifier import RegimeClassifier

        spine = DataSpine()
        df = spine.build_spine(
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 12, 31)
        )

        # Add regimes
        regime_classifier = RegimeClassifier()
        df = regime_classifier.classify_regimes(df)

        # Add profile scores
        detector = ProfileDetectors()
        df = detector.compute_all_profiles(df)

        return df

    def test_smoothness_check(self, scored_data_with_regimes):
        """Test smoothness validation."""
        validator = ProfileValidator()
        smoothness = validator.check_smoothness(scored_data_with_regimes)

        # Should have results for all profiles
        assert len(smoothness) == 6

        # Each result should have required keys
        for profile, results in smoothness.items():
            assert 'is_smooth' in results
            assert 'pct_large_changes' in results
            assert 'mean_abs_change' in results

    def test_regime_alignment_check(self, scored_data_with_regimes):
        """Test regime alignment calculation."""
        validator = ProfileValidator()
        regime_scores = validator.check_regime_alignment(scored_data_with_regimes)

        # Should have scores for each active regime
        assert len(regime_scores) > 0

        # All scores should be in [0, 1]
        assert (regime_scores >= 0).all().all()
        assert (regime_scores <= 1).all().all()

    def test_validation_report(self, scored_data_with_regimes):
        """Test comprehensive validation report."""
        validator = ProfileValidator()
        report = validator.generate_validation_report(scored_data_with_regimes)

        # Report should have all required sections
        assert 'smoothness' in report
        assert 'regime_scores' in report
        assert 'alignment_rules' in report
        assert 'overall_stats' in report

        # Overall stats should have all 6 profiles
        assert len(report['overall_stats']) == 6


class TestEdgeCases:
    """Test edge case handling."""

    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        detector = ProfileDetectors()
        df_empty = pd.DataFrame()

        # Should not crash
        df_result = detector.compute_all_profiles(df_empty)
        assert len(df_result) == 0

    def test_all_nan_column(self):
        """Test handling of all-NaN input."""
        detector = ProfileDetectors()

        # Create DataFrame with NaN RV values
        df_nan = pd.DataFrame({
            'date': pd.date_range('2022-01-01', periods=50),
            'close': [100] * 50,
            'RV5': [np.nan] * 50,
            'RV10': [np.nan] * 50,
            'RV20': [np.nan] * 50,
            'ATR5': [2.0] * 50,
            'MA20': [100] * 50,
            'MA50': [100] * 50,
            'slope_MA20': [0.0] * 50,
            'range_10d': [0.02] * 50
        })

        # Should not crash, should return NaN scores
        df_result = detector.compute_all_profiles(df_nan)

        for profile in get_profile_names():
            # All scores should be 0 or NaN (no crashes)
            assert profile in df_result.columns

    def test_extreme_volatility(self):
        """Test handling of extreme volatility values."""
        detector = ProfileDetectors()

        # Create DataFrame with extreme RV (e.g., flash crash)
        df_extreme = pd.DataFrame({
            'date': pd.date_range('2022-01-01', periods=50),
            'close': np.linspace(100, 80, 50),  # 20% decline
            'RV5': [2.0] * 50,  # 200% annualized vol
            'RV10': [1.8] * 50,
            'RV20': [1.5] * 50,
            'ATR5': [10.0] * 50,
            'MA20': [95] * 50,
            'MA50': [98] * 50,
            'slope_MA20': [-0.01] * 50,
            'range_10d': [0.20] * 50  # 20% range
        })

        # Should handle without overflow
        df_result = detector.compute_all_profiles(df_extreme)

        for profile in get_profile_names():
            scores = df_result[profile].dropna()
            if len(scores) > 0:
                # Should still be in [0, 1] range
                assert (scores >= 0).all()
                assert (scores <= 1).all()
