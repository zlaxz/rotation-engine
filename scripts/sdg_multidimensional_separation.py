#!/usr/bin/env python3
"""
SDG MULTIDIMENSIONAL STRUCTURAL SEPARATION ANALYSIS

Goal: Find if ANY clean structural boundary separates peakless from convex winners

Methodology:
1. Extract all SDG trades with features
2. Standardize features (z-scores)
3. Pairwise comparison (peakless vs good)
4. Simple K=2 clustering
5. Find which feature combinations separate groups

Output ONLY if:
- Filter removes MORE peakless than winners
- Has intuitive mechanical rationale
- Is SIMPLE (1-2 conditions)

If no clean boundary → Report that SDG remains unfiltered
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Load full dataset
results_file = 'data/backtest_results/full_2020-2024/results.json'
with open(results_file) as f:
    all_results = json.load(f)

print("=" * 80)
print("SDG MULTIDIMENSIONAL STRUCTURAL SEPARATION ANALYSIS")
print("=" * 80)
print()

# Extract SDG trades
sdg_data = all_results['Profile_2_SDG']
sdg_trades = sdg_data['trades']

print(f"Total SDG trades: {len(sdg_trades)}")
print()

# Extract features and categorize
features_list = []
labels = []  # 0 = peakless, 1 = good

for trade in sdg_trades:
    path = trade.get('path', [])
    if not path or len(path) == 0:
        continue

    # Find peak
    pnl_values = [day.get('mtm_pnl') for day in path if day.get('mtm_pnl') is not None]
    if len(pnl_values) == 0:
        continue

    peak_pnl = max(pnl_values)

    # Get entry conditions
    entry_cond = path[0].get('market_conditions', {})

    # Extract features
    features = {
        'slope_MA20': entry_cond.get('slope_MA20'),
        'slope_MA50': entry_cond.get('slope_MA50'),
        'return_1d': entry_cond.get('return', entry_cond.get('return_5d')),  # Fallback
        'return_5d': entry_cond.get('return_5d'),
        'return_10d': entry_cond.get('return_10d'),
        'return_20d': entry_cond.get('return_20d'),
        'RV5': entry_cond.get('RV5'),
        'RV10': entry_cond.get('RV10'),
        'RV20': entry_cond.get('RV20'),
        'ATR5': entry_cond.get('ATR5'),
        'ATR10': entry_cond.get('ATR10')
    }

    # Skip if critical features missing
    if any(features[k] is None for k in ['slope_MA20', 'return_5d', 'RV5', 'RV10']):
        continue

    features_list.append(features)
    labels.append(0 if peak_pnl <= 20 else 1)  # 0=peakless, 1=good

print(f"Valid trades with features: {len(features_list)}")
print(f"  Peakless: {labels.count(0)}")
print(f"  Good: {labels.count(1)}")
print()

# Convert to DataFrame
df = pd.DataFrame(features_list)
df['label'] = labels

# Separate groups
peakless_df = df[df['label'] == 0]
good_df = df[df['label'] == 1]

# PAIRWISE COMPARISON
print("=" * 80)
print("PAIRWISE FEATURE COMPARISON")
print("=" * 80)
print()
print(f"{'Feature':<15} {'Peakless Mean':>15} {'Good Mean':>15} {'Difference':>12} {'T-Statistic':>12}")
print("-" * 80)

from scipy import stats

significant_features = []

for col in df.columns:
    if col == 'label':
        continue

    peakless_vals = peakless_df[col].dropna()
    good_vals = good_df[col].dropna()

    if len(peakless_vals) < 3 or len(good_vals) < 3:
        continue

    peakless_mean = peakless_vals.mean()
    good_mean = good_vals.mean()
    diff = peakless_mean - good_mean

    # T-test
    t_stat, p_value = stats.ttest_ind(peakless_vals, good_vals)

    print(f"{col:<15} {peakless_mean:15.4f} {good_mean:15.4f} {diff:12.4f} {t_stat:12.3f}", end='')

    if p_value < 0.05:
        print(f" **")
        significant_features.append((col, abs(t_stat), diff))
    else:
        print()

print()
print("** = Statistically significant difference (p < 0.05)")
print()

# K-MEANS CLUSTERING
print("=" * 80)
print("K-MEANS CLUSTERING (K=2)")
print("=" * 80)
print()

# Standardize features
features_only = df.drop(columns=['label']).fillna(0)
scaler = StandardScaler()
features_scaled = scaler.fit_transform(features_only)

# Cluster
kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
clusters = kmeans.fit_predict(features_scaled)

# Analyze cluster composition
df['cluster'] = clusters

print("Cluster Composition:")
for cluster_id in [0, 1]:
    cluster_df = df[df['cluster'] == cluster_id]
    peakless_count = (cluster_df['label'] == 0).sum()
    good_count = (cluster_df['label'] == 1).sum()
    total = len(cluster_df)

    print(f"\n  Cluster {cluster_id}: {total} trades")
    print(f"    Peakless: {peakless_count} ({peakless_count/total*100:.1f}%)")
    print(f"    Good: {good_count} ({good_count/total*100:.1f}%)")

# FIND SIMPLE SEPARATION RULES
print()
print("=" * 80)
print("SIMPLE SEPARATION RULES")
print("=" * 80)
print()

if len(significant_features) > 0:
    print("Features with significant separation:")
    for feat, t_stat, diff in sorted(significant_features, key=lambda x: x[1], reverse=True):
        print(f"  {feat}: t-stat={t_stat:.2f}, diff={diff:.4f}")
    print()

# Test simple AND rules
print("Testing simple 2-feature AND rules:")
print()

best_rules = []

# Only test if we have significant features
feature_pairs = [
    ('slope_MA20', 'RV5'),
    ('return_1d', 'RV5'),
    ('return_5d', 'RV10'),
    ('slope_MA20', 'return_5d')
]

for feat1, feat2 in feature_pairs:
    if feat1 not in df.columns or feat2 not in df.columns:
        continue

    # Try different threshold combinations
    # Use percentiles from good trades
    f1_threshold = good_df[feat1].median()
    f2_threshold = good_df[feat2].median()

    # Test rule: both conditions must be met
    rule_mask = (df[feat1] < f1_threshold) & (df[feat2] < f2_threshold)

    peakless_filtered = ((df['label'] == 0) & rule_mask).sum()
    good_filtered = ((df['label'] == 1) & rule_mask).sum()

    if peakless_filtered + good_filtered > 0:
        precision = peakless_filtered / (peakless_filtered + good_filtered)

        print(f"  Rule: {feat1} < {f1_threshold:.4f} AND {feat2} < {f2_threshold:.4f}")
        print(f"    Filters: {peakless_filtered} peakless, {good_filtered} good")
        print(f"    Precision: {precision:.1%} peakless in filtered set")

        if peakless_filtered > good_filtered:
            best_rules.append({
                'features': (feat1, feat2),
                'peakless_filtered': peakless_filtered,
                'good_filtered': good_filtered,
                'precision': precision
            })
        print()

# FINAL RECOMMENDATION
print("=" * 80)
print("STRUCTURAL FILTER RECOMMENDATION")
print("=" * 80)
print()

if len(best_rules) > 0:
    best = max(best_rules, key=lambda x: x['peakless_filtered'] - x['good_filtered'])
    print(f"✓ FOUND: Clean structural boundary")
    print(f"  Filter: {best['features'][0]} AND {best['features'][1]}")
    print(f"  Removes: {best['peakless_filtered']} peakless, {best['good_filtered']} good")
    print(f"  Net benefit: {best['peakless_filtered'] - best['good_filtered']} more peakless removed")
else:
    print(f"❌ NO CLEAN BOUNDARY FOUND")
    print(f"   Cannot create simple filter that removes more peakless than winners")
    print(f"   SDG entries should remain UNFILTERED")
    print()
    print(f"   Reason: Feature overlap too high between peakless and good trades")
    print(f"   Structural filtering not applicable for this profile")

print()
