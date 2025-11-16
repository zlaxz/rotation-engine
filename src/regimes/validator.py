"""Regime classification validation tools.

Visual validation, sanity checks, and diagnostic tools for regime classifications.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Optional, Tuple
import seaborn as sns


class RegimeValidator:
    """Tools for validating regime classifications."""

    # Colors for each regime
    REGIME_COLORS = {
        1: '#2ecc71',  # Trend Up - green
        2: '#e74c3c',  # Trend Down - red
        3: '#3498db',  # Compression - blue
        4: '#e67e22',  # Breaking Vol - orange
        5: '#9b59b6',  # Choppy - purple
        6: '#f1c40f'   # Event - yellow
    }

    REGIME_NAMES = {
        1: 'Trend Up',
        2: 'Trend Down',
        3: 'Compression',
        4: 'Breaking Vol',
        5: 'Choppy',
        6: 'Event'
    }

    def plot_regime_bands(self,
                         df: pd.DataFrame,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         figsize: Tuple[int, int] = (16, 10)) -> plt.Figure:
        """Plot SPY price with colored regime bands.

        Args:
            df: DataFrame with date, close, regime_label columns
            start_date: Optional start date filter
            end_date: Optional end date filter
            figsize: Figure size

        Returns:
            Matplotlib figure
        """
        # Filter date range
        plot_df = df.copy()
        if start_date:
            # Convert to date object for comparison (df dates are date objects)
            start_date_obj = pd.to_datetime(start_date).date()
            plot_df = plot_df[plot_df['date'] >= start_date_obj]
        if end_date:
            # Convert to date object for comparison
            end_date_obj = pd.to_datetime(end_date).date()
            plot_df = plot_df[plot_df['date'] <= end_date_obj]

        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, height_ratios=[3, 1])

        # Plot 1: SPY price with regime background colors
        ax1.plot(plot_df['date'], plot_df['close'], color='black', linewidth=1.5, label='SPY Close')

        # Initialize set to track plotted regimes for legend
        plotted_regimes = set()

        # Add colored bands for each regime
        current_regime = None
        regime_start = None

        for i, row in plot_df.iterrows():
            if row['regime_label'] != current_regime:
                # Regime changed - plot previous regime band
                if current_regime is not None and regime_start is not None:
                    ax1.axvspan(
                        regime_start,
                        row['date'],
                        alpha=0.2,
                        color=self.REGIME_COLORS[current_regime]
                    )

                current_regime = row['regime_label']
                regime_start = row['date']

        # Add final band
        if current_regime is not None and regime_start is not None:
            ax1.axvspan(
                regime_start,
                plot_df['date'].iloc[-1],
                alpha=0.2,
                color=self.REGIME_COLORS[current_regime]
            )

        ax1.set_ylabel('SPY Price ($)', fontsize=12)
        ax1.set_title('SPY Price with Regime Classifications', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', fontsize=10)

        # Plot 2: Regime labels as discrete values
        ax2.scatter(plot_df['date'], plot_df['regime_label'],
                   c=[self.REGIME_COLORS[r] for r in plot_df['regime_label']],
                   s=10, alpha=0.6)

        ax2.set_ylabel('Regime', fontsize=12)
        ax2.set_yticks(range(1, 7))
        ax2.set_yticklabels([self.REGIME_NAMES[i] for i in range(1, 7)], fontsize=9)
        ax2.grid(True, alpha=0.3)
        ax2.set_xlabel('Date', fontsize=12)

        # Format x-axis
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()
        return fig

    def plot_regime_statistics(self, stats: dict, figsize: Tuple[int, int] = (14, 10)) -> plt.Figure:
        """Plot regime statistics (frequency, duration, transitions).

        Args:
            stats: Dictionary from RegimeClassifier.compute_regime_statistics()
            figsize: Figure size

        Returns:
            Matplotlib figure
        """
        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # Plot 1: Regime frequency
        ax1 = fig.add_subplot(gs[0, 0])
        regimes = list(stats['frequency'].keys())
        freqs = [stats['frequency'][r] * 100 for r in regimes]
        colors = [self.REGIME_COLORS[i+1] for i in range(len(regimes))]

        ax1.bar(regimes, freqs, color=colors, alpha=0.7)
        ax1.set_ylabel('Frequency (%)', fontsize=12)
        ax1.set_title('Regime Frequency', fontsize=13, fontweight='bold')
        ax1.set_xticklabels(regimes, rotation=45, ha='right', fontsize=9)
        ax1.grid(True, alpha=0.3, axis='y')

        # Plot 2: Average regime duration
        ax2 = fig.add_subplot(gs[0, 1])
        durations = [stats['duration'][r] for r in regimes]

        ax2.bar(regimes, durations, color=colors, alpha=0.7)
        ax2.set_ylabel('Avg Duration (days)', fontsize=12)
        ax2.set_title('Average Regime Duration', fontsize=13, fontweight='bold')
        ax2.set_xticklabels(regimes, rotation=45, ha='right', fontsize=9)
        ax2.grid(True, alpha=0.3, axis='y')

        # Plot 3: Transition matrix heatmap
        ax3 = fig.add_subplot(gs[1, :])
        transitions = stats['transitions']

        sns.heatmap(transitions, annot=True, fmt='.2f', cmap='YlOrRd',
                   cbar_kws={'label': 'Transition Probability'},
                   ax=ax3, vmin=0, vmax=1)
        ax3.set_title('Regime Transition Probabilities', fontsize=13, fontweight='bold')
        ax3.set_xlabel('To Regime', fontsize=12)
        ax3.set_ylabel('From Regime', fontsize=12)

        plt.suptitle(f'Regime Statistics (Total Transitions: {stats["total_transitions"]})',
                    fontsize=14, fontweight='bold', y=0.995)

        return fig

    def print_validation_report(self, validation_results: dict) -> None:
        """Print validation results in readable format.

        Args:
            validation_results: Dictionary from RegimeClassifier.validate_historical_regimes()
        """
        print("\n" + "="*80)
        print("REGIME CLASSIFICATION VALIDATION REPORT")
        print("="*80 + "\n")

        total = len(validation_results)
        passed = sum(1 for v in validation_results.values() if v['passed'])

        if total == 0:
            print("No validation cases provided.\n")
        else:
            for name, result in validation_results.items():
                status = "✅ PASS" if result['passed'] else "❌ FAIL"
                print(f"{status} | {name} ({result['date']})")
                print(f"      Expected: {', '.join(result['expected'])}")
                print(f"      Actual:   {result['actual']}")
                print(f"      {result['description']}")
                print()

        print("="*80)
        summary = f"{passed}/{total} validations passed" if total else "No validations executed"
        pct = f" ({passed/total*100:.1f}%)" if total else ""
        print(f"SUMMARY: {summary}{pct}")
        print("="*80 + "\n")

    def print_regime_statistics(self, stats: dict) -> None:
        """Print regime statistics in readable format.

        Args:
            stats: Dictionary from RegimeClassifier.compute_regime_statistics()
        """
        print("\n" + "="*80)
        print("REGIME STATISTICS")
        print("="*80 + "\n")

        print("REGIME FREQUENCY:")
        print("-" * 40)
        for regime, freq in stats['frequency'].items():
            print(f"  {regime:20s}: {freq*100:5.1f}%")

        print("\n\nAVERAGE REGIME DURATION:")
        print("-" * 40)
        for regime, duration in stats['duration'].items():
            print(f"  {regime:20s}: {duration:5.1f} days")

        print(f"\n\nTOTAL REGIME TRANSITIONS: {stats['total_transitions']}")
        print("\n" + "="*80 + "\n")

    def sanity_check_regimes(self, df: pd.DataFrame) -> dict:
        """Perform sanity checks on regime classifications.

        Args:
            df: DataFrame with regime classifications

        Returns:
            Dictionary with sanity check results
        """
        checks = {}

        # Check 1: No regime should dominate >60% of time
        regime_counts = df['regime_label'].value_counts(normalize=True)
        max_freq = regime_counts.max()
        checks['no_single_regime_dominates'] = {
            'passed': max_freq < 0.60,
            'max_frequency': max_freq,
            'dominant_regime': self.REGIME_NAMES[regime_counts.idxmax()]
        }

        # Check 2: Average regime duration should be >5 days (not whipsawing)
        regime_changes = (df['regime_label'].diff() != 0).sum()
        avg_duration = len(df) / regime_changes if regime_changes > 0 else len(df)
        checks['reasonable_duration'] = {
            'passed': avg_duration > 5,
            'avg_duration': avg_duration
        }

        # Check 3: Core regimes (1-5) should appear; Event regime optional
        observed_regimes = set(df['regime_label'].dropna().unique())
        core_required = {1, 2, 3, 4, 5}
        unique_regimes = len(observed_regimes)
        checks['all_regimes_present'] = {
            'passed': core_required.issubset(observed_regimes),
            'unique_regimes': unique_regimes,
            'event_present': 6 in observed_regimes
        }

        # Check 4: No NaN values in regime column
        checks['no_nan_regimes'] = {
            'passed': not df['regime_label'].isna().any(),
            'nan_count': df['regime_label'].isna().sum()
        }

        return checks

    def print_sanity_check_report(self, checks: dict) -> None:
        """Print sanity check results.

        Args:
            checks: Dictionary from sanity_check_regimes()
        """
        print("\n" + "="*80)
        print("REGIME SANITY CHECKS")
        print("="*80 + "\n")

        for check_name, result in checks.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{status} | {check_name.replace('_', ' ').title()}")

            # Print details
            for key, value in result.items():
                if key != 'passed':
                    print(f"      {key}: {value}")
            print()

        print("="*80 + "\n")
