# BUG-CRIT-002: Profile Detectors Look-Ahead Bias

**Severity:** 🔴 CRITICAL
**Component:** Profile Detectors
**File:** `src/profiles/detectors.py`
**Lines:** Multiple (Profiles 3, 4, 6)
**Found By:** Agent #3 (DeepSeek Reasoner)
**Status:** 🔴 UNFIXED

---

## Description

3 of 6 profile scoring functions contain look-ahead bias in feature engineering. This explains suspicious out-of-sample performance (+1094% for Profile 4 VANNA).

## Affected Profiles

### Profile 3: CHARM (Line 179-210)
**Suspicious Symptom:** Flipped from best to worst between train/test

**Bug:**
```python
# Line 196-197
df['charm_score'] = df['Charm'] / (df['Spot'] + 1e-4)
# Missing: Time normalization without walk-forward consideration
```

### Profile 4: VANNA (Line 212-244)
**Suspicious Symptom:** +1094% improvement out-of-sample (impossible without bias)

**Bug:**
```python
# Line 228-230
df['vanna_norm'] = rolling_stats_calculation  # ← Look-ahead in rolling calc
```

**Problem:** Rolling statistics computed without proper shift - includes current bar.

### Profile 6: VOV (Line 278-314)
**Suspicious Symptom:** Complex feature engineering with questionable timing

**Bug:**
```python
# Line 295-302
df['vov_norm'] = complex_feature_engineering  # ← Leak in normalization
```

## Additional Issue: Missing NaN Handling

**ALL 6 profiles missing `fillna(0)` in return statements:**
- Profile 1 (LDG): Line 143
- Profile 2 (SDG): Line 176
- Profile 3 (CHARM): Line 209
- Profile 4 (VANNA): Line 243
- Profile 5 (SKEW): Line 275
- Profile 6 (VOV): Line 313

**Impact:** System crashes on bad data instead of handling gracefully.

## The Fix

### Profile 3 (CHARM) Fix:
```python
def _compute_charm_score(self, df: pd.DataFrame) -> pd.Series:
    df = df.copy()
    # Remove time normalization or ensure walk-forward
    df['charm_score'] = df['Charm'] / (df['Spot'] + 1e-4)
    df['charm_score'] = df['charm_score'].fillna(0)

    score = 2 / (1 + np.exp(-df['charm_score'] * 1000)) - 1
    return score.fillna(0)  # ← Add NaN handling
```

### Profile 4 (VANNA) Fix:
```python
def _compute_vanna_score(self, df: pd.DataFrame) -> pd.Series:
    df = df.copy()
    # Remove rolling operations OR use .shift(1) for walk-forward
    df['vanna_score'] = df['Vanna'] / (df['Spot'] + 1e-4)
    df['vanna_score'] = df['vanna_score'].fillna(0)

    score = 2 / (1 + np.exp(-df['vanna_score'] * 100)) - 1
    return score.fillna(0)  # ← Add NaN handling
```

### Profile 6 (VOV) Fix:
```python
def _compute_vov_score(self, df: pd.DataFrame) -> pd.Series:
    df = df.copy()
    # Simplify - remove complex normalization
    df['vov_score'] = df['Vov'] / (df['IV30'] + 1e-4)
    df['vov_score'] = df['vov_score'].fillna(0)

    score = 2 / (1 + np.exp(-df['vov_score'] * 10)) - 1
    return score.fillna(0)  # ← Add NaN handling
```

### Add NaN Handling to ALL Profiles:
```python
# At end of each profile scoring function
return score.fillna(0)  # Prevent crashes on bad data
```

## Validation

After fixing:
1. ✅ Profile 4 (VANNA) OOS performance becomes realistic (not +1094%)
2. ✅ Profile 3 (CHARM) train/test consistency improves
3. ✅ No NaN crashes during backtest execution
4. ✅ Walk-forward test shows proper degradation
5. ✅ Unit test: profile scores at time t use only data ≤ t-1

## Files to Fix

- [ ] `src/profiles/detectors.py:179-210` - Profile 3 CHARM
- [ ] `src/profiles/detectors.py:212-244` - Profile 4 VANNA
- [ ] `src/profiles/detectors.py:278-314` - Profile 6 VOV
- [ ] `src/profiles/detectors.py` - Add fillna(0) to ALL 6 profiles
- [ ] Add unit tests: `tests/test_profile_detectors.py`

## Priority

**PRIORITY #2 - MUST FIX BEFORE VALIDATING PROFILES**

Blocks validation of profile-based strategies. Cannot trust any profile scores until this is resolved.
