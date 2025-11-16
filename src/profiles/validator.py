"""Validation tools for profile detectors.

Validates:
1. Smoothness: Scores should evolve gradually, not jump wildly
2. Regime Alignment: Profile N should score high in Regime N
3. Edge Cases: No NaN explosions, division by zero, etc.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Tuple
from .detectors import get_profile_names


class ProfileValidator:
    """Validate profile scoring functions."""

    def __init__(self):
        """Initialize validator."""
        self.profile_names = get_profile_names()

    def check_smoothness(self, df: pd.DataFrame, threshold: float = 0.15) -> dict:
        """Check if profile scores are smooth (not noisy).

        A noisy score jumps around too much between consecutive days.
        We flag if >10% of daily changes exceed threshold.

        Args:
            df: DataFrame with profile scores and date
            threshold: Max acceptable daily change (default 0.15)

        Returns:
            Dict with smoothness results for each profile
        """
        results = {}

        for profile in self.profile_names:
            if profile not in df.columns:
                continue

            # Calculate daily changes
            scores = df[profile].dropna()
            daily_changes = scores.diff().abs()

            # Stats
            large_changes = (daily_changes > threshold).sum()
            total_changes = len(daily_changes) - 1  # Exclude first NaN
            pct_large = (large_changes / total_changes * 100) if total_changes > 0 else 0

            # Smoothness test: <10% of changes should exceed threshold
            is_smooth = pct_large < 10

            results[profile] = {
                'is_smooth': is_smooth,
                'pct_large_changes': float(pct_large),
                'mean_abs_change': float(daily_changes.mean()),
                'max_abs_change': float(daily_changes.max()),
                'std_change': float(daily_changes.std())
            }

        return results

    def check_regime_alignment(
        self,
        df: pd.DataFrame,
        regime_col: str = 'regime'
    ) -> pd.DataFrame:
        """Check if profiles align with regimes.

        Expected high scores:
        - Regime 1 (Trend Up): Profile 1 (LDG), Profile 4 (VANNA)
        - Regime 2 (Trend Down): Profile 2 (SDG), Profile 5 (SKEW)
        - Regime 3 (Compression): Profile 3 (CHARM), Profile 4 (VANNA)
        - Regime 4 (Breaking Vol): Profile 5 (SKEW), Profile 6 (VOV)
        - Regime 5 (Choppy): Profile 2 (SDG) moderate

        Args:
            df: DataFrame with profile scores and regime labels
            regime_col: Name of regime column

        Returns:
            DataFrame with mean profile scores by regime
        """
        if regime_col not in df.columns:
            raise ValueError(f"Regime column '{regime_col}' not found")

        # Group by regime and compute mean scores
        regime_scores = df.groupby(regime_col)[self.profile_names].mean()

        return regime_scores

    def validate_alignment_rules(
        self,
        regime_scores: pd.DataFrame,
        min_score: float = 0.5
    ) -> dict:
        """Validate specific alignment rules.

        Args:
            regime_scores: DataFrame from check_regime_alignment()
            min_score: Minimum score considered "high" (default 0.5)

        Returns:
            Dict with pass/fail for each alignment rule
        """
        results = {}

        # Regime 1 (Trend Up) → Profile 1 (LDG) or Profile 4 (VANNA) should be high
        if 1 in regime_scores.index:
            regime1 = regime_scores.loc[1]
            results['Regime_1_LDG_or_VANNA'] = {
                'expected': 'Profile 1 (LDG) or Profile 4 (VANNA) high',
                'LDG_score': float(regime1['profile_1_LDG']),
                'VANNA_score': float(regime1['profile_4_VANNA']),
                'passed': regime1['profile_1_LDG'] > min_score or regime1['profile_4_VANNA'] > min_score
            }

        # Regime 2 (Trend Down) → Profile 2 (SDG) or Profile 5 (SKEW) should be high
        if 2 in regime_scores.index:
            regime2 = regime_scores.loc[2]
            results['Regime_2_SDG_or_SKEW'] = {
                'expected': 'Profile 2 (SDG) or Profile 5 (SKEW) high',
                'SDG_score': float(regime2['profile_2_SDG']),
                'SKEW_score': float(regime2['profile_5_SKEW']),
                'passed': regime2['profile_2_SDG'] > min_score or regime2['profile_5_SKEW'] > min_score
            }

        # Regime 3 (Compression) → Profile 3 (CHARM) should be high
        if 3 in regime_scores.index:
            regime3 = regime_scores.loc[3]
            results['Regime_3_CHARM'] = {
                'expected': 'Profile 3 (CHARM) high',
                'CHARM_score': float(regime3['profile_3_CHARM']),
                'passed': regime3['profile_3_CHARM'] > min_score
            }

        # Regime 4 (Breaking Vol) → Profile 5 (SKEW) or Profile 6 (VOV) should be high
        if 4 in regime_scores.index:
            regime4 = regime_scores.loc[4]
            results['Regime_4_SKEW_or_VOV'] = {
                'expected': 'Profile 5 (SKEW) or Profile 6 (VOV) high',
                'SKEW_score': float(regime4['profile_5_SKEW']),
                'VOV_score': float(regime4['profile_6_VOV']),
                'passed': regime4['profile_5_SKEW'] > min_score or regime4['profile_6_VOV'] > min_score
            }

        return results

    def plot_profile_scores(
        self,
        df: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        figsize: Tuple[int, int] = (14, 10)
    ) -> plt.Figure:
        """Plot all profile scores over time.

        Args:
            df: DataFrame with profile scores and date
            start_date: Start date for plot (optional)
            end_date: End date for plot (optional)
            figsize: Figure size

        Returns:
            Matplotlib figure
        """
        # Filter date range if specified
        plot_df = df.copy()
        if 'date' in plot_df.columns:
            plot_df['date'] = pd.to_datetime(plot_df['date'])
            if start_date:
                plot_df = plot_df[plot_df['date'] >= start_date]
            if end_date:
                plot_df = plot_df[plot_df['date'] <= end_date]

        # Create subplots
        fig, axes = plt.subplots(3, 2, figsize=figsize, sharex=True)
        axes = axes.flatten()

        profile_labels = [
            'Profile 1: Long-Dated Gamma (LDG)',
            'Profile 2: Short-Dated Gamma (SDG)',
            'Profile 3: Charm/Decay',
            'Profile 4: Vanna Convexity',
            'Profile 5: Skew Convexity',
            'Profile 6: Vol-of-Vol (VOV)'
        ]

        for idx, (profile, label) in enumerate(zip(self.profile_names, profile_labels)):
            ax = axes[idx]

            if profile in plot_df.columns:
                if 'date' in plot_df.columns:
                    ax.plot(plot_df['date'], plot_df[profile], linewidth=1.5)
                else:
                    ax.plot(plot_df.index, plot_df[profile], linewidth=1.5)

                ax.set_ylabel('Score', fontsize=10)
                ax.set_title(label, fontsize=11, fontweight='bold')
                ax.grid(True, alpha=0.3)
                ax.set_ylim(-0.05, 1.05)
                ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, linewidth=0.8)

        plt.tight_layout()
        return fig

    def plot_regime_alignment(
        self,
        regime_scores: pd.DataFrame,
        figsize: Tuple[int, int] = (12, 8)
    ) -> plt.Figure:
        """Plot heatmap of profile scores by regime.

        Args:
            regime_scores: DataFrame from check_regime_alignment()
            figsize: Figure size

        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=figsize)

        # Create heatmap
        im = ax.imshow(regime_scores.T, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)

        # Set ticks and labels
        regime_labels = ['Regime ' + str(int(r)) for r in regime_scores.index]
        profile_labels = [
            'P1: LDG',
            'P2: SDG',
            'P3: CHARM',
            'P4: VANNA',
            'P5: SKEW',
            'P6: VOV'
        ]

        ax.set_xticks(np.arange(len(regime_scores.index)))
        ax.set_yticks(np.arange(len(self.profile_names)))
        ax.set_xticklabels(regime_labels)
        ax.set_yticklabels(profile_labels)

        # Rotate tick labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right', rotation_mode='anchor')

        # Add values to cells
        for i in range(len(self.profile_names)):
            for j in range(len(regime_scores.index)):
                text = ax.text(j, i, f'{regime_scores.iloc[j, i]:.2f}',
                             ha='center', va='center', color='black', fontsize=10)

        # Color bar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Profile Score', rotation=270, labelpad=20)

        ax.set_title('Profile Scores by Regime (Mean)', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Regime', fontsize=12)
        ax.set_ylabel('Profile', fontsize=12)

        plt.tight_layout()
        return fig

    def generate_validation_report(
        self,
        df: pd.DataFrame,
        regime_col: str = 'regime'
    ) -> dict:
        """Generate comprehensive validation report.

        Args:
            df: DataFrame with profile scores and regimes
            regime_col: Name of regime column

        Returns:
            Dict with all validation results
        """
        report = {}

        # 1. Smoothness check
        report['smoothness'] = self.check_smoothness(df)

        # 2. Regime alignment
        regime_scores = self.check_regime_alignment(df, regime_col)
        report['regime_scores'] = regime_scores.to_dict()

        # 3. Alignment rules
        report['alignment_rules'] = self.validate_alignment_rules(regime_scores)

        # 4. Overall stats
        report['overall_stats'] = {}
        for profile in self.profile_names:
            if profile in df.columns:
                scores = df[profile].dropna()
                report['overall_stats'][profile] = {
                    'mean': float(scores.mean()),
                    'std': float(scores.std()),
                    'min': float(scores.min()),
                    'max': float(scores.max()),
                    'median': float(scores.median())
                }

        return report

    def print_validation_summary(self, report: dict) -> None:
        """Print human-readable validation summary.

        Args:
            report: Validation report from generate_validation_report()
        """
        print("=" * 80)
        print("PROFILE VALIDATION REPORT")
        print("=" * 80)

        # Smoothness
        print("\n1. SMOOTHNESS CHECK")
        print("-" * 80)
        all_smooth = True
        for profile, results in report['smoothness'].items():
            status = "✅ SMOOTH" if results['is_smooth'] else "❌ NOISY"
            print(f"{profile:25s} {status:15s} "
                  f"(Large changes: {results['pct_large_changes']:.1f}%, "
                  f"Mean Δ: {results['mean_abs_change']:.3f})")
            all_smooth = all_smooth and results['is_smooth']

        print(f"\n{'Overall Smoothness:':25s} {'✅ PASSED' if all_smooth else '❌ FAILED'}")

        # Regime Alignment
        print("\n2. REGIME ALIGNMENT")
        print("-" * 80)
        if 'alignment_rules' in report:
            all_aligned = True
            for rule_name, rule_results in report['alignment_rules'].items():
                status = "✅ PASSED" if rule_results['passed'] else "❌ FAILED"
                print(f"{rule_name:30s} {status}")
                print(f"  Expected: {rule_results['expected']}")

                # Print relevant scores
                for key, value in rule_results.items():
                    if key.endswith('_score'):
                        print(f"  {key}: {value:.3f}")

                all_aligned = all_aligned and rule_results['passed']

            print(f"\n{'Overall Alignment:':30s} {'✅ PASSED' if all_aligned else '⚠️  PARTIAL'}")

        # Overall Stats
        print("\n3. OVERALL STATISTICS")
        print("-" * 80)
        for profile, stats in report['overall_stats'].items():
            print(f"{profile:25s} Mean: {stats['mean']:.3f}, "
                  f"Std: {stats['std']:.3f}, "
                  f"Range: [{stats['min']:.3f}, {stats['max']:.3f}]")

        print("\n" + "=" * 80)
