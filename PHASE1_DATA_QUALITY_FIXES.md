# PHASE 1 DATA QUALITY FIXES
## Bugs Fixed From quant-code-review Validation

**Date:** 2025-11-13 23:15
**Agent:** quant-repair-agent
**Status:** COMPLETE - All fixes validated with tests

---

## BUG-001: Inverted bid/ask spreads on penny options

**Severity:** TIER 0 (Data Flow)
**Impact:** 6.28% of deep OTM options had invalid markets (244/3,885 records)

### Problem

Floor of $0.01 on bid prices caused bid >= mid for very cheap options:

```python
# BROKEN CODE:
df['bid'] = np.maximum(df['mid'] - half_spread, 0.01)  # Floor too high
```

When `mid - half_spread < 0.01`, bid gets forced to $0.01, creating inverted markets where bid >= mid.

**Example:** Option priced at $0.01 mid with 2% spread:
- Calculated bid: $0.01 - $0.0001 = $0.0099
- Forced bid: $0.01 (due to floor)
- Result: bid == mid (INVALID MARKET)

### Fix

Lower floor to $0.005 (half a penny):

```python
# FIXED CODE:
df['bid'] = (df['mid'] - half_spread).clip(lower=0.005)
```

This allows proper spreads on penny options while maintaining positive prices.

### Validation

**Before fix:**
- Inverted spreads: 244/3,885 (6.28%)
- Affected: Deep OTM options priced < $0.02

**After fix:**
- Inverted spreads: 0/3,885 (0.00%)
- All penny options: bid < mid < ask ✅

**Test added:**
```python
def test_no_inverted_spreads():
    """Verifies 0 records have bid >= mid across multiple days."""
```

**File:** `/Users/zstoc/rotation-engine/src/data/polygon_options.py:157`

---

## BUG-002: Missing garbage filter in get_option_price()

**Severity:** TIER 1 (Data Quality)
**Impact:** Bad quotes (zero volume, inverted spreads) could reach simulator

### Problem

`get_option_price()` method used by simulator didn't filter garbage quotes:

```python
# BROKEN CODE:
def get_option_price(self, ...):
    df = self.load_day(trade_date)

    if df.empty:
        return None

    # MISSING: Garbage filtering
    # Filter for exact match...
```

Meanwhile, `get_chain()` method HAD garbage filtering:
```python
def get_chain(self, ...):
    df = self.load_day(trade_date)
    if filter_garbage:
        df = self._filter_garbage(df)  # This was missing in get_option_price()
```

### Fix

Added garbage filtering before lookup:

```python
# FIXED CODE:
def get_option_price(self, ...):
    df = self.load_day(trade_date)

    if df.empty:
        return None

    # Filter garbage quotes before lookup
    df = self._filter_garbage(df)

    # Filter for exact match...
```

### What _filter_garbage() removes:
- Zero/negative prices
- Zero volume (stale quotes)
- Inverted markets (ask < bid)

### Validation

**Test added:**
```python
def test_garbage_filtering_in_lookup():
    """Verifies get_option_price() filters zero-volume options."""
```

**Impact:**
- Simulator now only receives clean quotes
- Consistent data quality across all lookup methods
- Prevents corrupt data from affecting backtest

**File:** `/Users/zstoc/rotation-engine/src/data/polygon_options.py:205`

---

## Test Results

**All polygon loader tests PASSING:**

```bash
$ pytest tests/test_polygon_loader.py -v

tests/test_polygon_loader.py::test_polygon_loader_basic PASSED           [ 14%]
tests/test_polygon_loader.py::test_get_option_price PASSED               [ 28%]
tests/test_polygon_loader.py::test_bulk_lookup PASSED                    [ 42%]
tests/test_polygon_loader.py::test_chain_filtering PASSED                [ 57%]
tests/test_polygon_loader.py::test_caching PASSED                        [ 71%]
tests/test_polygon_loader.py::test_no_inverted_spreads PASSED            [ 85%]
tests/test_polygon_loader.py::test_garbage_filtering_in_lookup PASSED    [100%]

============================== 7 passed in 1.45s ===============================
```

**Data quality verification:**

```
Total options: 3,885
Penny options (mid < $0.10): 680
Inverted spreads: 0 ✅
All bid < mid: True ✅
All bid < ask: True ✅
All ask > mid: True ✅
```

---

## Files Modified

1. `/Users/zstoc/rotation-engine/src/data/polygon_options.py`
   - Line 157: Fixed bid floor (0.01 → 0.005)
   - Line 205: Added garbage filtering

2. `/Users/zstoc/rotation-engine/tests/test_polygon_loader.py`
   - Added `test_no_inverted_spreads()`
   - Added `test_garbage_filtering_in_lookup()`

---

## Infra Status Assessment

**Data loading infrastructure:**
- ✅ SAFE: Bid/ask spreads now valid for all options
- ✅ SAFE: Garbage filtering applied consistently
- ✅ SAFE: All tests passing

**Next steps:**
1. Re-run quant-code-review on simulator code
2. Verify fixes propagated to backtest correctly
3. Continue Phase 1 validation of other components

**Status:** Data quality layer HARDENED. Safe for research use.
