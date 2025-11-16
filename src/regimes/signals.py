"""Regime signal calculations (walk-forward only).

Computes all signals needed for regime classification:
- Trend indicators (slopes, positioning)
- RV/IV ratios and percentiles
- Skew metrics
- Compression indicators
- Vol-of-vol measures
- Event flags

CRITICAL: All calculations are walk-forward to prevent look-ahead bias.
"""

import pandas as pd
import numpy as np
from typing import Optional


class RegimeSignals:
    """Compute regime detection signals walk-forward."""

    def __init__(self, lookback_percentile: int = 60):
        """Initialize regime signal calculator.

        Args:
            lookback_percentile: Days for rolling percentile calculations
        """
        self.lookback_percentile = lookback_percentile

    def compute_all_signals(self, spy_data: pd.DataFrame) -> pd.DataFrame:
        """Compute all regime signals from SPY data.

        Args:
            spy_data: DataFrame with OHLCV and derived features from the data spine
                     Expected columns: date, close, RV5, RV10, RV20, ATR5, ATR10,
                                      MA20, MA50, slope_MA20, slope_MA50,
                                      return_5d, return_10d, return_20d,
                                      range_10d, price_to_MA20, price_to_MA50

        Returns:
            DataFrame with additional regime signal columns
        """
        df = spy_data.copy()

        # Trend indicators (already have most from data spine)
        # Just add any missing ones

        # RV/IV ratios - For now use RV20 as IV proxy
        # In production, replace with actual IV from options chain
        df['RV5_RV20_ratio'] = df['RV5'] / df['RV20']
        df['RV10_RV20_ratio'] = df['RV10'] / df['RV20']

        # IV rank using RV20 as proxy (percentile over rolling window)
        # WALK-FORWARD: For each point, compute percentile relative to PAST data only
        df['RV20_rank'] = self._compute_walk_forward_percentile(df['RV20'], window=self.lookback_percentile)

        # Vol-of-vol: rolling stdev of RV10
        # This measures volatility of volatility
        df['vol_of_vol'] = (
            df['RV10']
            .rolling(window=20, min_periods=10)
            .std()
        )

        # Vol-of-vol slope (is vol-of-vol rising or falling?)
        df['vol_of_vol_slope'] = (
            df['vol_of_vol']
            .rolling(window=5, min_periods=3)
            .apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) >= 2 else 0, raw=False)
        )

        # Compression metric: ATR percentile
        df['ATR10_rank'] = self._compute_walk_forward_percentile(df['ATR10'], window=self.lookback_percentile)

        # Range compression flag: is price in tight range?
        df['is_compressed'] = df['range_10d'] < 0.035  # 3.5% range threshold

        # Realized vs Implied proxy (RV20 as IV proxy for now)
        # In regime detection, we'll use this ratio
        df['RV_IV_ratio'] = 1.0  # Placeholder - will be RV/IV when we add actual IV

        # Trend strength: how far from MA?
        df['MA_distance'] = df['price_to_MA20'].abs()

        # Trend consistency: is MA20 > MA50 or MA20 < MA50?
        df['MA20_above_MA50'] = df['MA20'] > df['MA50']

        # Choppy indicator: is slope near zero?
        df['slope_near_zero'] = df['slope_MA20'].abs() < 0.001

        # RSI for mean reversion detection
        df['RSI'] = self._compute_RSI(df['close'], window=14)

        # Event flags (placeholder - will populate with actual event dates)
        df['is_event'] = False

        return df

    def _compute_walk_forward_percentile(self, series: pd.Series, window: int) -> pd.Series:
        """Compute percentile rank walk-forward (no look-ahead).

        For each point, compute its percentile relative to the PAST window,
        not including the current point.

        Args:
            series: Time series to compute percentiles for
            window: Lookback window for percentile calculation

        Returns:
            Series of percentile ranks (0-1)
        """
        result = pd.Series(index=series.index, dtype=float)

        for i in range(len(series)):
            if i < window:
                # Not enough history - use what we have
                lookback = series.iloc[:i]
            else:
                # Use past window
                lookback = series.iloc[i-window:i]

            if len(lookback) == 0:
                result.iloc[i] = 0.5  # Default to middle
            else:
                # Current value's percentile in the lookback
                current_val = series.iloc[i]
                pct = (lookback < current_val).sum() / len(lookback)
                result.iloc[i] = pct

        return result

    def _compute_RSI(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Compute Relative Strength Index.

        Args:
            prices: Price series
            window: RSI window (default 14)

        Returns:
            RSI values (0-100)
        """
        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)

        # Calculate average gains and losses
        avg_gains = gains.rolling(window=window, min_periods=1).mean()
        avg_losses = losses.rolling(window=window, min_periods=1).mean()

        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def add_event_flags(self, df: pd.DataFrame, event_dates: list) -> pd.DataFrame:
        """Add event window flags to regime signals.

        Args:
            df: DataFrame with regime signals
            event_dates: List of event dates (FOMC, CPI, etc.)

        Returns:
            DataFrame with is_event column updated
        """
        df = df.copy()

        # Mark dates within 3 days of events
        event_window = 3

        date_series = pd.to_datetime(df['date'])

        for event_date in event_dates:
            event_ts = pd.to_datetime(event_date)

            # Mark window around event
            mask = (
                (date_series >= event_ts - pd.Timedelta(days=event_window)) &
                (date_series <= event_ts + pd.Timedelta(days=event_window))
            )
            df.loc[mask, 'is_event'] = True

        return df

    def compute_skew_proxy(self, options_data: pd.DataFrame) -> pd.Series:
        """Compute skew metric from options chain.

        For now, returns placeholder. In production, compute:
        - 25D put IV - ATM IV
        - Skew Z-score vs historical

        Args:
            options_data: Options chain data

        Returns:
            Series of skew values
        """
        # TODO: Implement actual skew calculation when IV data is available
        # For now, return zeros as placeholder
        return pd.Series(0.0, index=options_data.index)
