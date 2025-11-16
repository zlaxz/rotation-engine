"""
Polygon options data loader with efficient lookup.

Provides fast access to real options bid/ask/mid/close prices from Polygon data.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Dict, Tuple
import gzip
from collections import defaultdict

# Import execution model for realistic spread calculation
# Delay import to avoid circular dependency
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.trading.execution import ExecutionModel


DEFAULT_POLYGON_ROOT = "/Volumes/VelocityData/polygon_downloads/us_options_opra/day_aggs_v1"


class PolygonOptionsLoader:
    """
    Load Polygon options data with efficient lookup by (date, strike, expiry, type).

    Caches data by date to avoid repeated disk reads.
    """

    def __init__(self, data_root: Optional[str] = None, execution_model: Optional["ExecutionModel"] = None):
        resolved_root = data_root or os.environ.get("POLYGON_DATA_ROOT", DEFAULT_POLYGON_ROOT)
        self.data_root = Path(resolved_root).expanduser()
        if not self.data_root.exists():
            raise FileNotFoundError(
                f"Polygon data root not found at {self.data_root}. "
                "Mount the dataset or set POLYGON_DATA_ROOT to the correct path."
            )
        self._date_cache: Dict[date, pd.DataFrame] = {}
        # Execution model for realistic spread calculation (lazy import)
        if execution_model is None:
            from src.trading.execution import ExecutionModel
            execution_model = ExecutionModel()
        self.execution_model = execution_model

    def _parse_option_ticker(self, ticker: str) -> Optional[Dict]:
        """
        Parse Polygon option ticker: O:SPY240119C00450000

        Format: O:[underlying][YYMMDD][C/P][strike*1000]

        Returns:
            dict with: underlying, expiry, strike, option_type
        """
        if not ticker.startswith('O:'):
            return None

        # O:SPY240119C00450000
        parts = ticker[2:]  # Remove 'O:'

        # Extract components
        if len(parts) < 15:
            return None

        # Find where date starts (after underlying symbol)
        # SPY = 3 chars, date = 6 chars, C/P = 1 char, strike = 8 chars
        # Total after 'O:' should be 18 chars minimum for SPY

        # For SPY specifically (3 chars)
        underlying = parts[:3]
        date_str = parts[3:9]  # YYMMDD
        opt_type = parts[9]     # C or P
        strike_str = parts[10:18]  # 8 digits

        if underlying != 'SPY':
            # This loader is SPY-specific
            return None

        if opt_type not in ['C', 'P']:
            return None

        # Parse expiry date
        try:
            expiry = datetime.strptime(date_str, '%y%m%d').date()
        except:
            return None

        # Parse strike (divide by 1000)
        try:
            strike = float(strike_str) / 1000.0
        except:
            return None

        return {
            'underlying': underlying,
            'expiry': expiry,
            'strike': strike,
            'option_type': 'call' if opt_type == 'C' else 'put'
        }

    def _load_day_raw(self, trade_date: date) -> pd.DataFrame:
        """
        Load raw Polygon data for a single day.

        Returns DataFrame with parsed option info + OHLC data.
        """
        year = trade_date.year
        month = f"{trade_date.month:02d}"
        day = f"{trade_date.day:02d}"

        file_path = self.data_root / str(year) / month / f"{year}-{month}-{day}.csv.gz"

        if not file_path.exists():
            return pd.DataFrame()

        # Read compressed CSV
        try:
            with gzip.open(file_path, 'rt') as f:
                df = pd.read_csv(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return pd.DataFrame()

        # Parse tickers
        parsed = df['ticker'].apply(self._parse_option_ticker)

        # Filter valid parsed tickers (SPY options only)
        valid_mask = parsed.notna()

        if not valid_mask.any():
            return pd.DataFrame()

        parsed_series = parsed[valid_mask].reset_index(drop=True)
        df = df[valid_mask].reset_index(drop=True)

        # Convert parsed dicts to DataFrame
        parsed_df = pd.DataFrame(parsed_series.tolist())

        # Merge with price data
        result = pd.concat([df, parsed_df], axis=1)
        result['date'] = trade_date

        return result

    def load_day(self, trade_date: date, spot_price: Optional[float] = None, rv_20: Optional[float] = None) -> pd.DataFrame:
        """
        Load options data for a specific date with caching.

        Args:
            trade_date: Trading date
            spot_price: SPY spot price (required for realistic spread calculation)
            rv_20: 20-day realized volatility (for VIX proxy, optional)

        Returns DataFrame with:
            - date, expiry, strike, option_type
            - open, high, low, close
            - volume, transactions
            - bid, ask, mid (computed using ExecutionModel)
        """
        # Check cache (don't cache if spot_price provided - spreads change with spot)
        cache_key = (trade_date, spot_price, rv_20)
        if cache_key in self._date_cache:
            return self._date_cache[cache_key].copy()

        # Load from disk
        df = self._load_day_raw(trade_date)

        if df.empty:
            self._date_cache[cache_key] = df
            return df

        # Calculate DTE
        df['dte'] = (pd.to_datetime(df['expiry']) - pd.to_datetime(df['date'])).dt.days

        # Use close as theoretical mid price
        df['mid'] = df['close']

        # Calculate realistic bid/ask spreads using ExecutionModel
        if spot_price is not None:
            # Import helper functions (lazy to avoid circular import)
            from src.trading.execution import calculate_moneyness, get_vix_proxy

            # Calculate moneyness for each option
            df['moneyness'] = df['strike'].apply(lambda s: calculate_moneyness(s, spot_price))

            # Get VIX proxy if RV available
            vix_level = get_vix_proxy(rv_20) if rv_20 is not None else 20.0

            # Calculate spread for each option using ExecutionModel
            df['spread_dollars'] = df.apply(
                lambda row: self.execution_model.get_spread(
                    mid_price=row['mid'],
                    moneyness=row['moneyness'],
                    dte=row['dte'],
                    vix_level=vix_level,
                    is_strangle=False  # Conservative: assume straddle spreads (wider)
                ),
                axis=1
            )

            # Apply spreads: bid = mid - half_spread, ask = mid + half_spread
            half_spread = df['spread_dollars'] / 2.0
            df['bid'] = (df['mid'] - half_spread).clip(lower=0.005)
            df['ask'] = df['mid'] + half_spread

        else:
            # Fallback to simple 2% spread if spot_price not provided
            # (preserves backward compatibility but warns)
            import warnings
            warnings.warn(
                f"No spot_price provided for {trade_date}. Using synthetic 2% spreads. "
                "Pass spot_price for realistic spread modeling."
            )
            spread_pct = 0.02
            half_spread = df['mid'] * spread_pct / 2
            df['bid'] = (df['mid'] - half_spread).clip(lower=0.005)
            df['ask'] = df['mid'] + half_spread

        # Select columns
        columns = [
            'date', 'expiry', 'strike', 'option_type', 'dte',
            'open', 'high', 'low', 'close',
            'mid', 'bid', 'ask',
            'volume', 'transactions'
        ]

        df = df[[c for c in columns if c in df.columns]].copy()

        # Cache result
        self._date_cache[cache_key] = df.copy()

        return df

    def get_option_price(
        self,
        trade_date: date,
        strike: float,
        expiry: date,
        option_type: str,
        price_type: str = 'mid',
        spot_price: Optional[float] = None,
        rv_20: Optional[float] = None
    ) -> Optional[float]:
        """
        Get option price for specific contract.

        Args:
            trade_date: Trading date
            strike: Strike price
            expiry: Expiration date
            option_type: 'call' or 'put'
            price_type: 'bid', 'ask', 'mid', or 'close'
            spot_price: SPY spot price (for realistic spreads)
            rv_20: 20-day realized volatility (for VIX proxy)

        Returns:
            Price or None if not found
        """
        df = self.load_day(trade_date, spot_price=spot_price, rv_20=rv_20)

        if df.empty:
            return None

        # Filter garbage quotes before lookup
        df = self._filter_garbage(df)

        # Filter for exact match (use numpy.isclose for float comparison)
        mask = (
            (np.abs(df['strike'] - strike) < 0.01) &  # Within 1 cent
            (df['expiry'] == expiry) &
            (df['option_type'] == option_type)
        )

        matches = df[mask]

        if len(matches) == 0:
            return None

        # Return first match (should be unique)
        return float(matches.iloc[0][price_type])

    def find_closest_contract(
        self,
        trade_date: date,
        strike: float,
        expiry: date,
        option_type: str,
        max_expiry_diff: int = 90,
        max_strike_diff: float = 500.0,
        spot_price: Optional[float] = None,
        rv_20: Optional[float] = None
    ) -> Optional[Dict]:
        """Find the closest-available contract when exact match missing."""
        df = self.load_day(trade_date, spot_price=spot_price, rv_20=rv_20)

        if df.empty:
            return None

        subset = df[df['option_type'] == option_type].copy()
        if subset.empty:
            return None

        subset['expiry_date'] = pd.to_datetime(subset['expiry']).dt.date
        subset['expiry_diff'] = subset['expiry_date'].apply(lambda d: abs((d - expiry).days))
        subset['strike_diff'] = (subset['strike'] - strike).abs()
        subset = subset.sort_values(['expiry_diff', 'strike_diff'])

        best = subset.iloc[0]
        if best['expiry_diff'] > max_expiry_diff or best['strike_diff'] > max_strike_diff:
            return None

        return {
            'strike': float(best['strike']),
            'expiry': best['expiry_date'],
            'bid': float(best['bid']),
            'ask': float(best['ask']),
            'mid': float(best['mid'])
        }

    def get_option_prices_bulk(
        self,
        trade_date: date,
        contracts: list,  # List of (strike, expiry, option_type) tuples
        price_type: str = 'mid',
        spot_price: Optional[float] = None,
        rv_20: Optional[float] = None
    ) -> Dict[Tuple[float, date, str], float]:
        """
        Get prices for multiple contracts at once (more efficient).

        Args:
            trade_date: Trading date
            contracts: List of (strike, expiry, option_type) tuples
            price_type: 'bid', 'ask', 'mid', or 'close'
            spot_price: SPY spot price (for realistic spreads)
            rv_20: 20-day realized volatility (for VIX proxy)

        Returns:
            Dict mapping (strike, expiry, option_type) -> price
        """
        df = self.load_day(trade_date, spot_price=spot_price, rv_20=rv_20)

        if df.empty:
            return {}

        result = {}

        for strike, expiry, option_type in contracts:
            mask = (
                (df['strike'] == strike) &
                (df['expiry'] == expiry) &
                (df['option_type'] == option_type)
            )

            matches = df[mask]

            if len(matches) > 0:
                result[(strike, expiry, option_type)] = matches.iloc[0][price_type]

        return result

    def get_chain(
        self,
        trade_date: date,
        expiry: Optional[date] = None,
        min_dte: Optional[int] = None,
        max_dte: Optional[int] = None,
        filter_garbage: bool = True,
        spot_price: Optional[float] = None,
        rv_20: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Get options chain for a specific date, optionally filtered.

        Args:
            trade_date: Trading date
            expiry: Specific expiry (optional)
            min_dte: Minimum DTE filter
            max_dte: Maximum DTE filter
            filter_garbage: Remove bad quotes
            spot_price: SPY spot price (for realistic spreads)
            rv_20: 20-day realized volatility (for VIX proxy)

        Returns:
            Filtered options chain
        """
        df = self.load_day(trade_date, spot_price=spot_price, rv_20=rv_20)

        if df.empty:
            return df

        # Apply filters
        if expiry is not None:
            df = df[df['expiry'] == expiry].copy()

        if min_dte is not None:
            df = df[df['dte'] >= min_dte].copy()

        if max_dte is not None:
            df = df[df['dte'] <= max_dte].copy()

        if filter_garbage:
            df = self._filter_garbage(df)

        return df

    def _filter_garbage(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove garbage quotes:
        - Negative/zero prices
        - Zero volume
        - Inverted bid/ask
        """
        if df.empty:
            return df

        # Remove zero/negative prices
        df = df[df['close'] > 0].copy()
        df = df[(df['bid'] > 0) & (df['ask'] > 0)].copy()

        # Remove inverted markets
        df = df[df['ask'] >= df['bid']].copy()

        # Remove zero volume (stale quotes)
        df = df[df['volume'] > 0].copy()

        return df

    def clear_cache(self):
        """Clear the date cache."""
        self._date_cache.clear()
