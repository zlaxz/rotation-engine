# HARM-AWARE RULE SEARCH - BUG FIXES

**Date**: 2025-11-18
**File**: `/Users/zstoc/rotation-engine/scripts/harm_aware_structural_rule_search.py`

---

## BUG FIX #1: Division by Zero - Line 294

**Original** (Line 294):
```python
print(f"    Net benefit: {(conf['TP']-conf['FP'])/(conf['TP']+conf['FP'])*100:.1f}%")
```

**Fixed**:
```python
net_pct = (conf['TP']-conf['FP'])/max(1, conf['TP']+conf['FP'])*100
print(f"    Net benefit: {net_pct:.1f}%")
```

---

## BUG FIX #2: Division by Zero - Line 295

**Original** (Line 295):
```python
print(f"    New peakless rate: {conf['FN']/(conf['FN']+conf['TN'])*100:.1f}% (was {df['peakless'].sum()/len(df)*100:.1f}%)")
```

**Fixed**:
```python
remaining = conf['FN'] + conf['TN']
if remaining > 0:
    new_peakless_rate = conf['FN'] / remaining * 100
    old_peakless_rate = df['peakless'].sum() / len(df) * 100
    print(f"    New peakless rate: {new_peakless_rate:.1f}% (was {old_peakless_rate:.1f}%)")
else:
    print(f"    New peakless rate: N/A (all trades removed)")
```

---

## BUG FIX #3: Implement Gate 4 (Coarseness Check)

**Step 1**: Add coarseness check function after `check_year_robustness()` (after line 210):

```python
def check_coarseness(df, feature, pct, direction, label_col, percentile_grid, net_threshold):
    """
    G4: Coarseness - neighboring percentiles must also pass G1 and maintain net benefit direction

    Ensures rule is robust to threshold variation, not overfitted to specific percentile.
    """
    try:
        idx = percentile_grid.index(pct)
    except ValueError:
        # Percentile not in grid (shouldn't happen)
        return True, "PASS (not in grid)"

    # Get neighbors
    neighbors = []
    if idx > 0:
        neighbors.append(percentile_grid[idx-1])
    if idx < len(percentile_grid) - 1:
        neighbors.append(percentile_grid[idx+1])

    # Base rule metrics
    base_conf = test_1d_rule(df, feature, pct, direction, label_col)
    base_net = base_conf['TP'] - base_conf['FP']

    # Test each neighbor
    for neighbor_pct in neighbors:
        neighbor_conf = test_1d_rule(df, feature, neighbor_pct, direction, label_col)

        # Must pass G1 (TP >= FP)
        if neighbor_conf['TP'] < neighbor_conf['FP']:
            return False, f"G4_FAIL: Neighbor {neighbor_pct}th percentile fails G1 (TP={neighbor_conf['TP']}, FP={neighbor_conf['FP']})"

        # Net benefit should maintain direction (both positive or both negative)
        neighbor_net = neighbor_conf['TP'] - neighbor_conf['FP']
        if base_net > 0 and neighbor_net <= 0:
            return False, f"G4_FAIL: Net benefit flips at {neighbor_pct}th (base={base_net}, neighbor={neighbor_net})"
        if base_net < 0 and neighbor_net >= 0:
            return False, f"G4_FAIL: Net benefit flips at {neighbor_pct}th (base={base_net}, neighbor={neighbor_net})"

        # Optional: Neighbor should also pass G2 (net benefit threshold)
        neighbor_nb = neighbor_net / max(1, neighbor_conf['TP'] + neighbor_conf['FP'])
        if neighbor_nb < net_threshold * 0.7:  # Allow 30% degradation in neighbors
            return False, f"G4_FAIL: Neighbor {neighbor_pct}th has weak net benefit ({neighbor_nb:.1%} < {net_threshold*0.7:.1%})"

    return True, f"PASS (tested {len(neighbors)} neighbors)"
```

**Step 2**: Update the 1D rule testing loop to include G4 check (around line 258):

**Original** (Lines 252-280):
```python
for pct in PERCENTILE_GRID:
    for direction in ['below', 'above']:
        # Test rule
        conf = test_1d_rule(df, feature, pct, direction, 'peakless')

        # Check basic gates
        passes, reason = check_gates(conf, NET_BENEFIT_THRESHOLD[profile_id])

        if passes:
            # Check year robustness
            def rule_func(sub_df):
                return test_1d_rule(sub_df, feature, pct, direction, 'peakless')

            year_pass, year_results = check_year_robustness(df, rule_func, 'peakless')

            if year_pass:
                # Test on different winner thresholds (sensitivity)
                conf_50 = test_1d_rule(df, feature, pct, direction, 'convex_winner_50')
                conf_100 = test_1d_rule(df, feature, pct, direction, 'convex_winner_100')

                hard_rules.append({
                    'type': '1D',
                    'feature': feature,
                    'percentile': pct,
                    'direction': direction,
                    'threshold': conf['threshold'],
                    'conf_base': conf,
                    'conf_50': conf_50,
                    'conf_100': conf_100,
                    'year_results': year_results
                })
```

**Fixed** (add G4 check):
```python
for pct in PERCENTILE_GRID:
    for direction in ['below', 'above']:
        # Test rule
        conf = test_1d_rule(df, feature, pct, direction, 'peakless')

        # Check basic gates (G1, G2)
        passes, reason = check_gates(conf, NET_BENEFIT_THRESHOLD[profile_id])

        if not passes:
            continue

        # G3: Year robustness
        def rule_func(sub_df):
            return test_1d_rule(sub_df, feature, pct, direction, 'peakless')

        year_pass, year_results = check_year_robustness(df, rule_func, 'peakless')

        if not year_pass:
            continue

        # G4: Coarseness (NEW!)
        coarse_pass, coarse_reason = check_coarseness(
            df, feature, pct, direction, 'peakless',
            PERCENTILE_GRID, NET_BENEFIT_THRESHOLD[profile_id]
        )

        if not coarse_pass:
            continue

        # All gates passed - test on different winner thresholds
        conf_50 = test_1d_rule(df, feature, pct, direction, 'convex_winner_50')
        conf_100 = test_1d_rule(df, feature, pct, direction, 'convex_winner_100')

        hard_rules.append({
            'type': '1D',
            'feature': feature,
            'percentile': pct,
            'direction': direction,
            'threshold': conf['threshold'],
            'conf_base': conf,
            'conf_50': conf_50,
            'conf_100': conf_100,
            'year_results': year_results,
            'coarseness': coarse_reason  # Document that G4 passed
        })
```

---

## BUG FIX #4: Empty Array Protection (Lines 147, 165)

**Add to `test_1d_rule()` function** (after line 147):

**Original**:
```python
def test_1d_rule(df, feature, percentile, direction, label_col='peakless'):
    """Test a 1D rule: feature <= threshold or feature >= threshold"""
    threshold = np.percentile(df[feature].dropna(), percentile)
```

**Fixed**:
```python
def test_1d_rule(df, feature, percentile, direction, label_col='peakless'):
    """Test a 1D rule: feature <= threshold or feature >= threshold"""

    # Protect against empty array
    valid_values = df[feature].dropna()
    if len(valid_values) == 0:
        # No valid data for this feature - cannot create rule
        return {'TP': 0, 'FP': 0, 'FN': 0, 'TN': 0, 'threshold': None}

    threshold = np.percentile(valid_values, percentile)
```

**Same fix for `test_2d_rule()`** (Lines 165-166):

**Original**:
```python
def test_2d_rule(df, feat1, pct1, dir1, feat2, pct2, dir2, label_col='peakless'):
    """Test a 2D AND rule"""

    thresh1 = np.percentile(df[feat1].dropna(), pct1)
    thresh2 = np.percentile(df[feat2].dropna(), pct2)
```

**Fixed**:
```python
def test_2d_rule(df, feat1, pct1, dir1, feat2, pct2, dir2, label_col='peakless'):
    """Test a 2D AND rule"""

    # Protect against empty arrays
    valid1 = df[feat1].dropna()
    valid2 = df[feat2].dropna()

    if len(valid1) == 0 or len(valid2) == 0:
        return {'TP': 0, 'FP': 0, 'FN': 0, 'TN': 0, 'thresh1': None, 'thresh2': None}

    thresh1 = np.percentile(valid1, pct1)
    thresh2 = np.percentile(valid2, pct2)
```

---

## BUG FIX #5: Year Robustness - Minimum Sample Size

**Add to `check_year_robustness()`** (after line 202):

**Original**:
```python
def check_year_robustness(df, rule_func, label_col='peakless'):
    """G3: Check if rule works in EVERY year"""

    years = df['year'].unique()
    year_results = {}

    for year in years:
        year_df = df[df['year'] == year]
        conf = rule_func(year_df)

        year_results[year] = conf

        # Must pass G1 in every year
        if conf['TP'] < conf['FP']:
            return False, f"G3_FAIL: Year {year} removes {conf['FP']} winners vs {conf['TP']} peakless"

    return True, year_results
```

**Fixed**:
```python
def check_year_robustness(df, rule_func, label_col='peakless', min_per_class=2):
    """G3: Check if rule works in EVERY year"""

    years = df['year'].unique()
    year_results = {}

    for year in years:
        year_df = df[df['year'] == year]

        # Check minimum sample size per class
        n_positive = (year_df[label_col] == True).sum()
        n_negative = (year_df[label_col] == False).sum()

        if n_positive < min_per_class or n_negative < min_per_class:
            return False, f"G3_FAIL: Year {year} has insufficient data (peakless={n_positive}, winners={n_negative}, min={min_per_class})"

        conf = rule_func(year_df)
        year_results[year] = conf

        # Must pass G1 in every year
        if conf['TP'] < conf['FP']:
            return False, f"G3_FAIL: Year {year} removes {conf['FP']} winners vs {conf['TP']} peakless"

    return True, year_results
```

---

## TESTING CHECKLIST

After applying fixes, test:

1. **Division by Zero Protection**:
   ```python
   # Create synthetic rule that removes all trades
   conf = {'TP': 0, 'FP': 0, 'FN': 10, 'TN': 0}
   # Should not crash on lines 294-295
   ```

2. **Empty Array Protection**:
   ```python
   # Create DataFrame with all NaN for a feature
   df = pd.DataFrame({'return_5d': [None, None], 'peakless': [True, False]})
   conf = test_1d_rule(df, 'return_5d', 50, 'below')
   assert conf['TP'] == 0  # Gracefully returns zeros
   ```

3. **Gate 4 Coarseness**:
   ```python
   # Test that neighboring percentiles are checked
   # Manually verify that a rule passing at 50th also passes at 40th and 60th
   ```

4. **Year Minimum Sample**:
   ```python
   # Create year with only 1 winner
   # Should FAIL G3 with "insufficient data" message
   ```

---

## DEPLOYMENT CHECKLIST

Before deploying fixed version:

- [ ] All 5 bug fixes applied
- [ ] Code runs without crashes on test data
- [ ] At least 1 rule survives all 4 gates (G1, G2, G3, G4)
- [ ] Manual review of surviving rules for sensibility
- [ ] Gate 4 rejection reasons logged and reviewed
- [ ] Re-run on full dataset (2020-2024)
- [ ] Save results with version tag: `structural_rules_v2_all_gates.json`

---

**Estimated total fix time**: 3 hours
**Re-run time**: 5 minutes
**Confidence after fixes**: HIGH (all gates enforced, no crashes)

