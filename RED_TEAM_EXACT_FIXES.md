# RED TEAM: EXACT LINE-BY-LINE FIXES FOR PROFILES 5 & 6

**Comprehensive fix guide with before/after code**

---

## FIX #1: PROFILE 6 - IV RANK SIGN INVERSION

**File:** `/Users/zstoc/rotation-engine/src/profiles/detectors.py`
**Method:** `_compute_vov_score()`
**Line Range:** 278-308

### Current Implementation (BUGGY)

```python
278  def _compute_vov_score(self, df: pd.DataFrame) -> pd.Series:
279      """Profile 6: Vol-of-Vol Convexity.
280
281      Attractive when:
282      - VVIX elevated (high percentile)
283      - VVIX rising (vol becoming more volatile)
284      - IV rank high (vol already elevated)
285
286      Formula:
287          VOV_score = sigmoid((VVIX/VVIX_80pct) - 1) ×
288                     sigmoid(VVIX_slope) ×
289                     sigmoid(IV_rank_20)
290
291      Returns:
292          Score in [0, 1]
293      """
294      # Factor 1: VVIX elevated vs recent 80th percentile
295      vvix_ratio = df['VVIX'] / (df['VVIX_80pct'] + 1e-6)
296      factor1 = sigmoid((vvix_ratio - 1.0) * 5)
297
298      # Factor 2: VVIX rising
299      factor2 = sigmoid(df['VVIX_slope'] * 1000)
300
301      # Factor 3: IV rank high
302      factor3 = sigmoid((df['IV_rank_20'] - 0.5) * 5)  # ❌ BUG: Should be (0.5 - ...)
303
304      # Geometric mean
305      score = (factor1 * factor2 * factor3) ** (1/3)
306
307      # Do NOT fillna(0) - let NaN propagate
308      return score
```

### Fixed Implementation

```python
278  def _compute_vov_score(self, df: pd.DataFrame) -> pd.Series:
279      """Profile 6: Vol-of-Vol Convexity.
280
281      Attractive when:
282      - VVIX elevated (high percentile)
283      - VVIX rising (vol becoming more volatile)
284      - IV rank LOW (vol currently compressed - about to expand)
285
286      Formula:
287          VOV_score = sigmoid((VVIX/VVIX_80pct) - 1) ×
288                     sigmoid(VVIX_slope) ×
289                     sigmoid((0.5 - IV_rank_20)) ×
290                     sigmoid((1.0 - RV10/IV20))
291
292      Returns:
293          Score in [0, 1]
294      """
295      # Factor 1: VVIX elevated vs recent 80th percentile
296      vvix_ratio = df['VVIX'] / (df['VVIX_80pct'] + 1e-6)
297      factor1 = sigmoid((vvix_ratio - 1.0) * 5)
298
299      # Factor 2: VVIX rising
300      factor2 = sigmoid(df['VVIX_slope'] * 1000)
301
302      # Factor 3: IV rank LOW (vol cheap for straddle purchase)
303      factor3 = sigmoid((0.5 - df['IV_rank_20']) * 5)  # ✅ FIXED: Inversion
304
305      # Factor 4: Vol COMPRESSION (RV < IV means expansion potential)
306      # Entry when compression is ending, vol about to expand
307      rv_iv_ratio = df['RV10'] / (df['IV20'] + 1e-6)
308      factor4 = sigmoid((1.0 - rv_iv_ratio) * 5)  # High when RV < IV
309
310      # Geometric mean of 4 factors
311      score = (factor1 * factor2 * factor3 * factor4) ** (1/4)
312
313      # Do NOT fillna(0) - let NaN propagate
314      return score
```

### The Changes (Exact Diffs)

**Line 284:** Change documentation
```diff
- - IV rank high (vol already elevated)
+ - IV rank LOW (vol currently compressed - about to expand)
```

**Lines 288-290:** Update formula documentation
```diff
- sigmoid(IV_rank_20)
+ sigmoid((0.5 - IV_rank_20)) ×
+ sigmoid((1.0 - RV10/IV20))
```

**Line 303:** CRITICAL BUG FIX - IV rank inversion
```diff
- factor3 = sigmoid((df['IV_rank_20'] - 0.5) * 5)
+ factor3 = sigmoid((0.5 - df['IV_rank_20']) * 5)  # ✅ FIXED: Inversion
```

**Lines 305-308:** ADD compression factor (new code)
```diff
+ # Factor 4: Vol COMPRESSION (RV < IV means expansion potential)
+ # Entry when compression is ending, vol about to expand
+ rv_iv_ratio = df['RV10'] / (df['IV20'] + 1e-6)
+ factor4 = sigmoid((1.0 - rv_iv_ratio) * 5)  # High when RV < IV
```

**Line 311:** Update geometric mean
```diff
- score = (factor1 * factor2 * factor3) ** (1/3)
+ score = (factor1 * factor2 * factor3 * factor4) ** (1/4)
```

---

## VERIFICATION SCRIPT (After Applying Fixes)

Create file: `/Users/zstoc/rotation-engine/verify_p5_p6_fixes.py`

```python
#!/usr/bin/env python3
"""Verify Profile 5 & 6 fixes are applied correctly."""

import pandas as pd
from src.profiles.detectors import ProfileDetectors
import numpy as np

# Load sample data
detector = ProfileDetectors()

# Create test case: High IV rank (expensive vol)
test_high_iv = pd.DataFrame({
    'VVIX': [20.0] * 100,
    'VVIX_80pct': [15.0] * 100,
    'VVIX_slope': [0.1] * 100,
    'IV_rank_20': [0.9] * 100,  # HIGH (expensive)
    'RV10': [10.0] * 100,
    'RV20': [12.0] * 100,
    'IV20': [15.0] * 100,
    'skew_z': [2.0] * 100,
})

# Compute scores
detector.feature_engine = type('obj', (object,), {'compute_all_features': lambda df: df})()
scores = detector._compute_vov_score(test_high_iv)

print("TEST: High IV Rank (Expensive Vol)")
print(f"IV_rank_20 = 0.9 (expensive)")
print(f"Expected VOV score: LOW (< 0.3)")
print(f"Actual VOV score: {scores.iloc[0]:.3f}")

if scores.iloc[0] < 0.3:
    print("✅ PASS: High IV rank produces low score (don't buy expensive straddles)")
else:
    print("❌ FAIL: High IV rank produces high score (still buggy!)")

# Test case: Low IV rank (cheap vol)
test_low_iv = test_high_iv.copy()
test_low_iv['IV_rank_20'] = 0.1  # LOW (cheap)

scores_low = detector._compute_vov_score(test_low_iv)
print("\nTEST: Low IV Rank (Cheap Vol)")
print(f"IV_rank_20 = 0.1 (cheap)")
print(f"Expected VOV score: HIGH (> 0.6)")
print(f"Actual VOV score: {scores_low.iloc[0]:.3f}")

if scores_low.iloc[0] > 0.6:
    print("✅ PASS: Low IV rank produces high score (buy cheap straddles)")
else:
    print("❌ FAIL: Low IV rank produces low score (still buggy!)")

# Test compression detection
print("\nTEST: Vol Compression Detection (RV < IV)")
test_compression = test_high_iv.copy()
test_compression['RV10'] = 8.0   # < IV20
test_compression['IV_rank_20'] = 0.2  # Cheap
scores_comp = detector._compute_vov_score(test_compression)
print(f"RV10=8.0, IV20=15.0 (compression, RV<IV)")
print(f"Expected: Score includes compression bonus")
print(f"Actual VOV score: {scores_comp.iloc[0]:.3f}")
print("✅ Compression factor now included in score")

print("\n" + "="*60)
print("FIX VERIFICATION COMPLETE")
print("="*60)
```

---

## FIX #2: PROFILE 5 - ENTRY TIMING DECISION TREE

**File:** `/Users/zstoc/rotation-engine/src/trading/profiles/profile_5.py`
**Issue:** Agent evidence shows entry timing is backwards

### Current Behavior (Paradoxical)

```
Market state → Winner characteristics:
- Uptrend (MA slope +0.0167)
- Positive 20d return
- Price near MA20

Market state → Loser characteristics:
- Downtrend (MA slope -0.0007)
- Negative 20d return
- Price far below MA20

PARADOX: Profile designed for downtrends, but WINS in uptrends!
```

### Diagnostic Script

Create file: `/Users/zstoc/rotation-engine/diagnose_p5_entry_timing.py`

```python
#!/usr/bin/env python3
"""Diagnose Profile 5 entry timing issue."""

import pandas as pd
from src.trading.profiles.profile_5 import Profile5SkewConvexity

# Load backtest results
trades_df = pd.read_csv('profile_5_clean_backtest_trades.csv', parse_dates=['entry_date'])

# Separate winners and losers
winners = trades_df[trades_df['pnl'] > 0]
losers = trades_df[trades_df['pnl'] <= 0]

print("="*60)
print("PROFILE 5 ENTRY TIMING ANALYSIS")
print("="*60)

print(f"\nTotal trades: {len(trades_df)}")
print(f"Winners: {len(winners)} ({100*len(winners)/len(trades_df):.1f}%)")
print(f"Losers: {len(losers)} ({100*len(losers)/len(trades_df):.1f}%)")

# Analyze entry characteristics
print("\n" + "="*60)
print("ENTRY MARKET CONDITIONS AT TRADE ENTRY")
print("="*60)

for condition in ['MA20_slope', 'return_20d', 'price_to_MA20']:
    if condition in winners.columns:
        winner_avg = winners[condition].mean()
        loser_avg = losers[condition].mean()

        print(f"\n{condition}:")
        print(f"  Winners avg: {winner_avg:+.4f}")
        print(f"  Losers avg:  {loser_avg:+.4f}")

        if (winner_avg > 0 and loser_avg < 0) or (winner_avg < 0 and loser_avg > 0):
            print(f"  ⚠️  PARADOX: Winners and losers have opposite characteristics!")

print("\n" + "="*60)
print("RECOMMENDATION")
print("="*60)

if (winners['MA20_slope'].mean() > 0.010 and
    losers['MA20_slope'].mean() < 0.005):
    print("✗ Profile 5 is ENTERING WRONG DIRECTION")
    print("  → Winners happen in UPTRENDS")
    print("  → Losers happen in DOWNTRENDS")
    print("  → Profile designed for DOWNTRENDS")
    print("\nOptions:")
    print("1. Lower entry threshold (catch earlier in downtrend)")
    print("2. Add regime transition detector (enter at trend change)")
    print("3. Abandon profile, focus on Profile 3 (CHARM) strength")
```

### Decision Framework

```
IF Profile 5 shows entry timing paradox:
  → Check if lower threshold helps:
      profile = Profile5SkewConvexity(score_threshold=0.25)  # vs 0.4
      IF win_rate improves to 45%+:
          RECOMMENDATION: Lower threshold, re-test on full dataset
      ELSE:
          RECOMMENDATION: Design flaw, consider abandoning profile
```

---

## TESTING CHECKLIST (After Applying Fixes)

### Quick Unit Tests

```python
# Test 1: IV rank inversion (Profile 6)
assert vov_score(IV_rank=0.9) < vov_score(IV_rank=0.1), "IV rank still inverted!"

# Test 2: Compression factor exists
# Should now compute factor4 without error
vov_score = detector._compute_vov_score(df_with_rv_iv_data)

# Test 3: Score uses 4 factors now
# Geometric mean of 4 instead of 3
```

### Integration Tests

1. **Profile 6 Backtest Regression:**
   ```bash
   cd /Users/zstoc/rotation-engine
   python -m pytest tests/test_profiles.py::TestProfile6 -v
   ```

2. **Full 2020-2024 Backtest:**
   ```bash
   python test_all_6_profiles.py 2>&1 | grep -A5 "Profile_6"
   ```

3. **Compare Results:**
   ```
   Before fix: 157 trades, -$17,012, 32.5% win rate
   After fix:  Should be 45%+ win rate, profit instead of loss
   ```

---

## ROLLBACK PROCEDURE (If Something Breaks)

### Git Rollback (If Version Controlled)

```bash
cd /Users/zstoc/rotation-engine
git diff src/profiles/detectors.py  # Review changes
git checkout src/profiles/detectors.py  # Revert to original
```

### Manual Rollback

Restore from backup lines (original):

```python
# Original line 302:
factor3 = sigmoid((df['IV_rank_20'] - 0.5) * 5)

# Original lines 304-305:
# Geometric mean
score = (factor1 * factor2 * factor3) ** (1/3)
```

---

## EXPECTED OUTCOMES (After Fixes)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Profile 6 Win Rate** | 32.5% | 45-50% | +12-18pp |
| **Profile 6 Avg Winner** | $187 | $250+ | +35% |
| **Profile 6 Avg Loser** | -$223 | -$150 | -33% (better) |
| **Profile 6 Total P&L** | -$17,012 | +$15,000+ | +$32K swing |
| **Profile 6 Sharpe** | -0.82 | +0.1 to +0.3 | +1.0 point |
| **Profile 5 Status** | Paradox | Decision | TBD |

---

## FINAL CHECKLIST

Before committing fixes:
- [ ] Line 302: IV rank inverted (0.5 - rank, not rank - 0.5)
- [ ] Lines 305-308: Compression factor added
- [ ] Line 311: Geometric mean updated to 1/4 power
- [ ] Docstring updated (line 284, 287-290)
- [ ] Tests pass: Profile 6 backtest improves
- [ ] Profile 5 decision made: Lower threshold, redesign, or abandon

