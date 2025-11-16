"""6-Regime market classification (walk-forward only).

Implements classification logic for:
1. Trend Up (directional + vol compression)
2. Trend Down (directional + vol expansion)
3. Vol Compression / Pinned
4. Breaking Vol / Vol Expansion
5. Choppy / Mean-Reverting
6. Event / Catalyst

Classification is rule-based using regime signals.
Priority order handles overlapping conditions.
"""

import pandas as pd
import numpy as np
from datetime import date
from typing import Optional, Tuple, List
from .signals import RegimeSignals
from src.data.events import load_event_dates


class RegimeClassifier:
    """Classify market regime based on walk-forward signals."""

    # Regime constants
    REGIME_TREND_UP = 1
    REGIME_TREND_DOWN = 2
    REGIME_COMPRESSION = 3
    REGIME_BREAKING_VOL = 4
    REGIME_CHOPPY = 5
    REGIME_EVENT = 6

    REGIME_NAMES = {
        1: 'Trend Up',
        2: 'Trend Down',
        3: 'Compression',
        4: 'Breaking Vol',
        5: 'Choppy',
        6: 'Event'
    }

    def __init__(self,
                 trend_threshold: float = 0.02,
                 compression_range: float = 0.035,
                 rv_rank_low: float = 0.30,
                 rv_rank_high: float = 0.80,
                 rv_rank_mid_low: float = 0.40,
                 rv_rank_mid_high: float = 0.60,
                 use_default_event_calendar: bool = True,
                 event_dates: Optional[List[date]] = None):
        """Initialize regime classifier.

        Args:
            trend_threshold: Minimum 20-day return for trend detection (2%)
            compression_range: Max range for pinned regime (3.5%)
            rv_rank_low: Low RV percentile threshold (30%)
            rv_rank_high: High RV percentile threshold (80%)
            rv_rank_mid_low: Lower bound of mid RV range (40%)
            rv_rank_mid_high: Upper bound of mid RV range (60%)
        """
        self.trend_threshold = trend_threshold
        self.compression_range = compression_range
        self.rv_rank_low = rv_rank_low
        self.rv_rank_high = rv_rank_high
        self.rv_rank_mid_low = rv_rank_mid_low
        self.rv_rank_mid_high = rv_rank_mid_high

        self.signal_calculator = RegimeSignals()
        if event_dates is not None:
            self.event_dates = event_dates
        elif use_default_event_calendar:
            self.event_dates = load_event_dates()
        else:
            self.event_dates = []

    def classify_period(self,
                       spy_data: pd.DataFrame,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       event_dates: Optional[list] = None) -> pd.DataFrame:
        """Classify regime for entire period.

        Args:
            spy_data: DataFrame with SPY OHLCV and derived features
            start_date: Optional start date filter
            end_date: Optional end date filter
            event_dates: Optional list of event dates (FOMC, CPI, etc.)

        Returns:
            DataFrame with regime_label and regime_name columns added
        """
        # Compute regime signals
        df = self.signal_calculator.compute_all_signals(spy_data)

        event_list = event_dates if event_dates is not None else self.event_dates

        # Add event flags if provided
        if event_list:
            df = self.signal_calculator.add_event_flags(df, event_list)

        # Filter date range if specified
        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['date'] <= pd.to_datetime(end_date)]

        # Classify each row
        df['regime_label'] = df.apply(self._classify_row, axis=1)
        df['regime_name'] = df['regime_label'].map(self.REGIME_NAMES)

        return df

    def _classify_row(self, row: pd.Series) -> int:
        """Classify single row into regime.

        Uses priority order:
        1. Event (highest priority - clear override)
        2. Breaking Vol (violent regime - must detect)
        3. Trend Down (asymmetric - downtrends distinct)
        4. Trend Up
        5. Compression
        6. Choppy (default/fallback)

        Args:
            row: Single row with all signals computed

        Returns:
            Regime label (1-6)
        """
        # Priority 1: Event
        if row.get('is_event', False):
            return self.REGIME_EVENT

        # Priority 2: Breaking Vol
        # Characteristics: RV percentile very high, vol-of-vol rising
        if self._is_breaking_vol(row):
            return self.REGIME_BREAKING_VOL

        # Priority 3: Trend Down
        # Characteristics: negative return, price below MAs, elevated RV
        if self._is_trend_down(row):
            return self.REGIME_TREND_DOWN

        # Priority 4: Trend Up
        # Characteristics: positive return, price above MAs, RV not elevated
        if self._is_trend_up(row):
            return self.REGIME_TREND_UP

        # Priority 5: Compression / Pinned
        # Characteristics: tight range, low RV, not trending
        if self._is_compression(row):
            return self.REGIME_COMPRESSION

        # Priority 6: Choppy (default)
        # Everything else falls here
        return self.REGIME_CHOPPY

    def _is_trend_up(self, row: pd.Series) -> bool:
        """Detect Trend Up regime.

        Criteria:
        - 20-day return > +2%
        - Price above MA20 and MA50
        - MA20 slope positive
        - RV not elevated (percentile < 40%)
        """
        return (
            row['return_20d'] > self.trend_threshold and
            row['price_to_MA20'] > 0 and
            row['price_to_MA50'] > 0 and
            row['slope_MA20'] > 0 and
            row['RV20_rank'] < self.rv_rank_mid_low
        )

    def _is_trend_down(self, row: pd.Series) -> bool:
        """Detect Trend Down regime.

        Criteria:
        - 20-day return < -2%
        - Price below MA20 and MA50
        - MA20 slope negative
        - RV elevated (percentile > 50%)
        """
        return (
            row['return_20d'] < -self.trend_threshold and
            row['price_to_MA20'] < 0 and
            row['price_to_MA50'] < 0 and
            row['slope_MA20'] < 0 and
            row['RV20_rank'] > 0.50
        )

    def _is_compression(self, row: pd.Series) -> bool:
        """Detect Vol Compression / Pinned regime.

        Criteria:
        - Tight price range (< 3.5% over 10 days)
        - Low RV percentile (< 30%)
        - Not in strong trend
        """
        return (
            row['range_10d'] < self.compression_range and
            row['RV20_rank'] < self.rv_rank_low and
            abs(row['slope_MA20']) < 0.005  # Not strongly trending
        )

    def _is_breaking_vol(self, row: pd.Series) -> bool:
        """Detect Breaking Vol regime.

        Criteria:
        - RV percentile very high (> 80%)
        - Vol-of-vol elevated or rising
        - RV spiking (absolute RV level high)
        """
        # Check for high RV percentile
        high_rv = row['RV20_rank'] > self.rv_rank_high

        # Check for very elevated RV (absolute level)
        # RV20 > 40% annualized is clearly breaking vol
        extreme_rv = row['RV20'] > 0.40

        # Check for elevated vol-of-vol
        # Use simple threshold: vol-of-vol > 0.3x the 20-day RV
        # This indicates volatility is volatile
        elevated_vov = row.get('vol_of_vol', 0) > row['RV20'] * 0.3

        # Breaking vol if: high percentile + (extreme level OR elevated vol-of-vol)
        return high_rv and (extreme_rv or elevated_vov)

    def compute_regime_statistics(self, df: pd.DataFrame) -> dict:
        """Compute statistics about regime classifications.

        Args:
            df: DataFrame with regime_label column

        Returns:
            Dictionary with regime statistics
        """
        stats = {}

        # Regime frequency
        regime_counts = df['regime_label'].value_counts()
        total = len(df)

        stats['frequency'] = {
            self.REGIME_NAMES[regime]: count / total
            for regime, count in regime_counts.items()
        }

        # Average regime duration
        stats['duration'] = self._compute_regime_durations(df['regime_label'])

        # Transition matrix
        stats['transitions'] = self._compute_transition_matrix(df['regime_label'])

        # Total regime changes
        stats['total_transitions'] = (df['regime_label'].diff() != 0).sum()

        return stats

    def _compute_regime_durations(self, regime_series: pd.Series) -> dict:
        """Compute average duration of each regime in days.

        Args:
            regime_series: Series of regime labels

        Returns:
            Dictionary mapping regime name to average duration
        """
        durations = {name: [] for name in self.REGIME_NAMES.values()}

        current_regime = None
        current_duration = 0

        for regime in regime_series:
            if regime == current_regime:
                current_duration += 1
            else:
                # Regime changed
                if current_regime is not None:
                    regime_name = self.REGIME_NAMES[current_regime]
                    durations[regime_name].append(current_duration)

                current_regime = regime
                current_duration = 1

        # Add final regime
        if current_regime is not None:
            regime_name = self.REGIME_NAMES[current_regime]
            durations[regime_name].append(current_duration)

        # Compute averages
        avg_durations = {
            regime: np.mean(dur_list) if dur_list else 0
            for regime, dur_list in durations.items()
        }

        return avg_durations

    def _compute_transition_matrix(self, regime_series: pd.Series) -> pd.DataFrame:
        """Compute regime transition probability matrix.

        Args:
            regime_series: Series of regime labels

        Returns:
            DataFrame with transition probabilities
        """
        # Create transition counts
        transitions = pd.DataFrame(
            0,
            index=self.REGIME_NAMES.values(),
            columns=self.REGIME_NAMES.values()
        )

        # Count transitions
        for i in range(len(regime_series) - 1):
            from_regime = self.REGIME_NAMES[regime_series.iloc[i]]
            to_regime = self.REGIME_NAMES[regime_series.iloc[i + 1]]
            transitions.loc[from_regime, to_regime] += 1

        # Convert to probabilities (row-wise)
        transitions = transitions.div(transitions.sum(axis=1), axis=0).fillna(0)

        return transitions

    def validate_historical_regimes(self,
                                    df: pd.DataFrame,
                                    validation_cases: Optional[list] = None) -> dict:
        """Validate regime classifications against known historical periods.

        Args:
            df: DataFrame with regime classifications
            validation_cases: Optional list of dicts with keys:
                name, date (YYYY-MM-DD), expected (list of regimes), description

        Returns:
            Dictionary with validation results
        """
        results = {}

        default_validations = [
            {
                'name': '2023 Bank Contagion Aftermath',
                'date': '2023-03-16',
                'expected': [self.REGIME_TREND_DOWN, self.REGIME_BREAKING_VOL],
                'description': 'Post-SVB stress should map to Breaking Vol / Trend Down'
            },
            {
                'name': '2023 Summer Melt-Up',
                'date': '2023-07-19',
                'expected': [self.REGIME_TREND_UP, self.REGIME_COMPRESSION],
                'description': 'Low-vol trend following the AI rally'
            },
            {
                'name': '2024 Mid-Summer Vol Spike',
                'date': '2024-07-30',
                'expected': [self.REGIME_BREAKING_VOL, self.REGIME_TREND_DOWN, self.REGIME_EVENT],
                'description': 'Late-July vol shock / FOMC window should register as Breaking Vol or Event'
            }
        ]

        validations = validation_cases or default_validations

        for val in validations:
            date_str = val['date']
            # Convert to date object (dates in df are date objects, not Timestamp)
            date = pd.to_datetime(date_str).date()

            # Find regime on this date
            mask = df['date'] == date
            if mask.any():
                regime = df.loc[mask, 'regime_label'].iloc[0]
                regime_name = self.REGIME_NAMES[regime]

                passed = regime in val['expected']

                results[val['name']] = {
                    'date': date_str,
                    'expected': [self.REGIME_NAMES[r] for r in val['expected']],
                    'actual': regime_name,
                    'passed': passed,
                    'description': val['description']
                }
            else:
                results[val['name']] = {
                    'date': date_str,
                    'expected': [self.REGIME_NAMES[r] for r in val['expected']],
                    'actual': 'DATE NOT FOUND',
                    'passed': False,
                    'description': val['description']
                }

        return results
