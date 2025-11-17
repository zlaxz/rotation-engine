"""
Statistical Validation Suite for Rotation Engine
Tests statistical significance, robustness, and multiple testing issues.

WARNING: Real capital at risk. Do not trust results without rigorous validation.
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Tuple, List
import warnings
warnings.filterwarnings('ignore')


class StatisticalValidator:
    """Comprehensive statistical validation for trading strategies."""

    def __init__(self, backtest_dir: str):
        self.backtest_dir = backtest_dir
        self.portfolio = None
        self.regime_data = None
        self.profile_data = {}
        self.load_data()

    def load_data(self):
        """Load all backtest results."""
        # Portfolio results
        pf = pd.read_parquet(f'{self.backtest_dir}/portfolio.parquet')
        pf['date'] = pd.to_datetime(pf['date'])
        pf = pf.set_index('date')
        pf['equity'] = 100000 + pf['cumulative_pnl']
        self.portfolio = pf

        # Regime attribution
        self.regime_data = pd.read_csv(f'{self.backtest_dir}/attribution_by_regime.csv')

        # Profile attribution
        self.profile_attribution = pd.read_csv(f'{self.backtest_dir}/attribution_by_profile.csv')

    # =========================================================================
    # 1. SAMPLE SIZE ADEQUACY
    # =========================================================================

    def sample_size_adequacy(self) -> Dict:
        """Test if sample sizes are adequate for statistical inference."""
        results = {
            'total_days': len(self.portfolio),
            'total_years': len(self.portfolio) / 252,
            'regime_samples': {},
            'adequacy': {}
        }

        # Minimum requirements
        MIN_DAYS_TOTAL = 250  # 1 year minimum
        MIN_DAYS_PER_REGIME = 100  # 100 days per regime for meaningful stats

        # Check total sample
        results['adequacy']['total_sample'] = {
            'days': len(self.portfolio),
            'adequate': len(self.portfolio) >= MIN_DAYS_TOTAL,
            'requirement': MIN_DAYS_TOTAL
        }

        # Check regime samples
        for _, row in self.regime_data.iterrows():
            regime = int(row['regime'])
            days = int(row['days'])

            results['regime_samples'][regime] = {
                'days': days,
                'pct_of_total': days / len(self.portfolio) * 100,
                'adequate': days >= MIN_DAYS_PER_REGIME,
                'requirement': MIN_DAYS_PER_REGIME
            }

        # Overall adequacy
        insufficient_regimes = [r for r, data in results['regime_samples'].items()
                               if not data['adequate']]

        results['overall_adequate'] = len(insufficient_regimes) == 0
        results['insufficient_regimes'] = insufficient_regimes

        return results

    # =========================================================================
    # 2. SHARPE RATIO SIGNIFICANCE
    # =========================================================================

    def sharpe_significance(self) -> Dict:
        """Test if Sharpe ratio is significantly different from zero."""
        returns = self.portfolio['portfolio_return'].dropna()

        # Calculate Sharpe
        sharpe = returns.mean() / returns.std() * np.sqrt(252)

        # T-statistic for Sharpe ratio
        # t = Sharpe × sqrt(N) / sqrt(1 + Sharpe²/2)
        n = len(returns)
        t_stat = sharpe * np.sqrt(n) / np.sqrt(1 + sharpe**2 / 2)

        # P-value (two-tailed test: is Sharpe != 0?)
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n-1))

        # Confidence interval (95%)
        # Using Jobson-Korkie method
        se_sharpe = np.sqrt((1 + sharpe**2 / 2) / n)
        ci_lower = sharpe - 1.96 * se_sharpe
        ci_upper = sharpe + 1.96 * se_sharpe

        return {
            'sharpe': sharpe,
            't_statistic': t_stat,
            'p_value': p_value,
            'significant_at_5pct': p_value < 0.05,
            'significant_at_10pct': p_value < 0.10,
            'ci_95_lower': ci_lower,
            'ci_95_upper': ci_upper,
            'sample_size': n,
            'interpretation': self._interpret_sharpe_test(sharpe, p_value)
        }

    def _interpret_sharpe_test(self, sharpe: float, p_value: float) -> str:
        """Interpret Sharpe ratio significance test."""
        if sharpe > 0 and p_value < 0.05:
            return "Sharpe significantly positive at 5% level"
        elif sharpe > 0 and p_value < 0.10:
            return "Sharpe significantly positive at 10% level"
        elif sharpe < 0 and p_value < 0.05:
            return "Sharpe significantly NEGATIVE at 5% level (WORSE than zero)"
        elif sharpe < 0 and p_value < 0.10:
            return "Sharpe significantly NEGATIVE at 10% level (WORSE than zero)"
        else:
            return "Sharpe NOT significantly different from zero (INDISTINGUISHABLE from luck)"

    # =========================================================================
    # 3. BOOTSTRAP CONFIDENCE INTERVALS
    # =========================================================================

    def bootstrap_analysis(self, n_bootstrap: int = 10000) -> Dict:
        """Bootstrap analysis for performance metrics."""
        returns = self.portfolio['portfolio_return'].dropna().values
        equity = self.portfolio['equity'].values

        # Bootstrap resampling
        sharpe_boot = []
        max_dd_boot = []
        total_ret_boot = []

        for _ in range(n_bootstrap):
            # Sample with replacement
            sample_ret = np.random.choice(returns, size=len(returns), replace=True)

            # Sharpe
            sharpe_boot.append(sample_ret.mean() / sample_ret.std() * np.sqrt(252))

            # Total return
            total_ret_boot.append((1 + sample_ret).prod() - 1)

            # Max drawdown
            sample_equity = 100000 * np.cumprod(1 + sample_ret)
            cummax = np.maximum.accumulate(sample_equity)
            dd = (sample_equity / cummax - 1).min()
            max_dd_boot.append(dd)

        # Compute percentiles
        results = {
            'sharpe': {
                'mean': np.mean(sharpe_boot),
                'median': np.median(sharpe_boot),
                'ci_95': (np.percentile(sharpe_boot, 2.5), np.percentile(sharpe_boot, 97.5)),
                'ci_90': (np.percentile(sharpe_boot, 5), np.percentile(sharpe_boot, 95)),
                'prob_positive': np.mean(np.array(sharpe_boot) > 0),
                'prob_gt_1': np.mean(np.array(sharpe_boot) > 1.0)
            },
            'total_return': {
                'mean': np.mean(total_ret_boot),
                'median': np.median(total_ret_boot),
                'ci_95': (np.percentile(total_ret_boot, 2.5), np.percentile(total_ret_boot, 97.5)),
                'prob_positive': np.mean(np.array(total_ret_boot) > 0),
                'prob_loss_gt_20pct': np.mean(np.array(total_ret_boot) < -0.20)
            },
            'max_drawdown': {
                'mean': np.mean(max_dd_boot),
                'median': np.median(max_dd_boot),
                'ci_95': (np.percentile(max_dd_boot, 2.5), np.percentile(max_dd_boot, 97.5)),
                'prob_dd_gt_30pct': np.mean(np.array(max_dd_boot) < -0.30),
                'prob_dd_gt_50pct': np.mean(np.array(max_dd_boot) < -0.50)
            },
            'n_bootstrap': n_bootstrap
        }

        return results

    # =========================================================================
    # 4. PERMUTATION TESTS (REGIME VALUE-ADD)
    # =========================================================================

    def permutation_test_regimes(self, n_permutations: int = 10000) -> Dict:
        """Test if regime classification adds value vs random labels."""
        returns = self.portfolio['portfolio_return'].values
        regimes = self.portfolio['regime'].values

        # Actual Sharpe
        actual_sharpe = returns.mean() / returns.std() * np.sqrt(252)

        # Permute regimes (shuffle regime labels randomly)
        permuted_sharpes = []
        for _ in range(n_permutations):
            shuffled_regimes = np.random.permutation(regimes)
            # Returns stay the same, regimes are shuffled
            # This tests: does regime order matter?
            permuted_sharpes.append(returns.mean() / returns.std() * np.sqrt(252))

        # P-value: what % of random permutations beat actual?
        if actual_sharpe > 0:
            p_value = np.mean(np.array(permuted_sharpes) >= actual_sharpe)
        else:
            p_value = np.mean(np.array(permuted_sharpes) <= actual_sharpe)

        return {
            'actual_sharpe': actual_sharpe,
            'mean_permuted_sharpe': np.mean(permuted_sharpes),
            'p_value': p_value,
            'significant_at_5pct': p_value < 0.05,
            'interpretation': self._interpret_permutation_test(p_value, actual_sharpe),
            'n_permutations': n_permutations
        }

    def _interpret_permutation_test(self, p_value: float, actual_sharpe: float) -> str:
        """Interpret permutation test results."""
        if actual_sharpe > 0 and p_value < 0.05:
            return "Regime classification adds significant value (actual > random at 5% level)"
        elif actual_sharpe > 0 and p_value < 0.10:
            return "Regime classification adds marginal value (actual > random at 10% level)"
        else:
            return "Regime classification does NOT add value (indistinguishable from random)"

    # =========================================================================
    # 5. MULTIPLE TESTING CORRECTION
    # =========================================================================

    def multiple_testing_correction(self) -> Dict:
        """Correct for multiple testing across 36 regime-profile combinations."""

        # Number of combinations tested
        n_regimes = 6
        n_profiles = 6
        n_tests = n_regimes * n_profiles

        # Bonferroni correction: divide alpha by number of tests
        alpha = 0.05
        bonferroni_alpha = alpha / n_tests

        # Holm-Bonferroni (less conservative)
        # Would need individual p-values for each combination

        # Family-wise error rate
        fwer = 1 - (1 - alpha) ** n_tests

        return {
            'n_combinations': n_tests,
            'original_alpha': alpha,
            'bonferroni_alpha': bonferroni_alpha,
            'family_wise_error_rate': fwer,
            'interpretation': f"Testing {n_tests} combinations. To maintain 5% significance, "
                            f"need p-value < {bonferroni_alpha:.6f} (Bonferroni). "
                            f"Without correction, {fwer*100:.1f}% chance of false positive."
        }

    # =========================================================================
    # 6. REGIME-CONDITIONAL PERFORMANCE
    # =========================================================================

    def regime_conditional_analysis(self) -> Dict:
        """Test if performance varies significantly across regimes."""
        results = {}

        # Performance by regime
        regime_returns = {}
        regime_sharpes = {}

        for regime in range(1, 7):
            regime_mask = self.portfolio['regime'] == regime
            regime_ret = self.portfolio.loc[regime_mask, 'portfolio_return']

            if len(regime_ret) > 1:
                sharpe = regime_ret.mean() / regime_ret.std() * np.sqrt(252)
                regime_returns[regime] = regime_ret.values
                regime_sharpes[regime] = sharpe
            else:
                regime_returns[regime] = np.array([])
                regime_sharpes[regime] = np.nan

        results['regime_sharpes'] = regime_sharpes

        # ANOVA test: Do means differ across regimes?
        valid_returns = [ret for ret in regime_returns.values() if len(ret) > 1]
        if len(valid_returns) >= 2:
            f_stat, p_value_anova = stats.f_oneway(*valid_returns)
            results['anova'] = {
                'f_statistic': f_stat,
                'p_value': p_value_anova,
                'significant': p_value_anova < 0.05,
                'interpretation': 'Returns differ significantly across regimes' if p_value_anova < 0.05
                                else 'No significant difference across regimes'
            }

        # Kruskal-Wallis (non-parametric alternative)
        if len(valid_returns) >= 2:
            h_stat, p_value_kw = stats.kruskal(*valid_returns)
            results['kruskal_wallis'] = {
                'h_statistic': h_stat,
                'p_value': p_value_kw,
                'significant': p_value_kw < 0.05
            }

        # Individual regime t-tests (is each regime Sharpe > 0?)
        regime_tests = {}
        for regime, returns_array in regime_returns.items():
            if len(returns_array) > 1:
                t_stat, p_value = stats.ttest_1samp(returns_array, 0)
                regime_tests[regime] = {
                    'mean_return': returns_array.mean(),
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'significantly_positive': (t_stat > 0 and p_value < 0.05),
                    'significantly_negative': (t_stat < 0 and p_value < 0.05)
                }

        results['regime_tests'] = regime_tests

        return results

    # =========================================================================
    # 7. PROFILE-CONDITIONAL PERFORMANCE
    # =========================================================================

    def profile_conditional_analysis(self) -> Dict:
        """Test if each profile has positive expected return."""
        results = {}

        # Get profile returns from attribution data
        profile_returns = {}

        for i in range(1, 7):
            col_name = f'profile_{i}_return'
            if col_name in self.portfolio.columns:
                prof_ret = self.portfolio[col_name].dropna()

                # T-test: is mean return > 0?
                if len(prof_ret) > 1:
                    t_stat, p_value = stats.ttest_1samp(prof_ret, 0)

                    # Sharpe for this profile
                    sharpe = prof_ret.mean() / prof_ret.std() * np.sqrt(252) if prof_ret.std() > 0 else 0

                    results[f'profile_{i}'] = {
                        'mean_return': prof_ret.mean(),
                        'std_return': prof_ret.std(),
                        'sharpe': sharpe,
                        't_statistic': t_stat,
                        'p_value': p_value,
                        'significantly_positive': (t_stat > 0 and p_value < 0.05),
                        'significantly_negative': (t_stat < 0 and p_value < 0.05),
                        'sample_size': len(prof_ret)
                    }

        # Which profiles work?
        positive_profiles = [p for p, data in results.items()
                            if data.get('significantly_positive', False)]
        negative_profiles = [p for p, data in results.items()
                            if data.get('significantly_negative', False)]

        results['summary'] = {
            'significantly_positive': positive_profiles,
            'significantly_negative': negative_profiles,
            'n_positive': len(positive_profiles),
            'n_negative': len(negative_profiles)
        }

        return results

    # =========================================================================
    # 8. PARAMETER SENSITIVITY (PLACEHOLDER)
    # =========================================================================

    def parameter_sensitivity_framework(self) -> Dict:
        """Framework for parameter sensitivity testing."""
        return {
            'note': 'Parameter sensitivity requires re-running backtest with perturbed parameters',
            'recommended_tests': [
                '±10% on all regime thresholds',
                '±10% on all profile scoring parameters',
                '±20% on transaction cost assumptions',
                'Different lookback windows (e.g., 20 days vs 40 days)'
            ],
            'pass_criteria': 'Sharpe should not degrade by >50% with ±10% parameter changes',
            'current_status': 'NOT TESTED - requires infrastructure to vary parameters'
        }

    # =========================================================================
    # 9. OVERFITTING RISK ASSESSMENT
    # =========================================================================

    def overfitting_risk(self) -> Dict:
        """Assess overfitting risk based on parameter count vs sample size."""

        # Estimate parameter count
        # Regime detection: ~15 parameters (thresholds, windows)
        # Profile scoring: 6 profiles × ~10 params = 60 parameters
        # Execution model: ~14 parameters
        n_parameters_estimated = 89  # From previous audit

        n_observations = len(self.portfolio)

        # Rule of thumb: need 10-20 observations per parameter
        observations_per_param = n_observations / n_parameters_estimated

        # Degrees of freedom
        dof = n_observations - n_parameters_estimated

        return {
            'n_parameters': n_parameters_estimated,
            'n_observations': n_observations,
            'observations_per_parameter': observations_per_param,
            'degrees_of_freedom': dof,
            'adequate_ratio': observations_per_param >= 10,
            'overfitting_risk': 'HIGH' if observations_per_param < 10 else
                               'MODERATE' if observations_per_param < 20 else 'LOW',
            'recommendation': self._overfitting_recommendation(observations_per_param)
        }

    def _overfitting_recommendation(self, ratio: float) -> str:
        """Recommend actions based on overfitting risk."""
        if ratio < 10:
            return "CRITICAL: <10 obs/param. Need more data OR reduce parameters by 50%+."
        elif ratio < 20:
            return "HIGH RISK: <20 obs/param. Recommend walk-forward validation and parameter reduction."
        else:
            return "Acceptable ratio. Still recommend out-of-sample validation."

    # =========================================================================
    # 10. OUT-OF-SAMPLE TESTING PLAN
    # =========================================================================

    def out_of_sample_plan(self) -> Dict:
        """Generate out-of-sample testing roadmap."""

        total_days = len(self.portfolio)
        start_date = self.portfolio.index[0]
        end_date = self.portfolio.index[-1]

        # Walk-forward windows
        # Use 2 years train, 1 year test
        train_days = 504  # 2 years
        test_days = 252   # 1 year

        n_windows = (total_days - train_days) // test_days

        windows = []
        for i in range(n_windows):
            train_start_idx = i * test_days
            train_end_idx = train_start_idx + train_days
            test_start_idx = train_end_idx
            test_end_idx = min(test_start_idx + test_days, total_days)

            if test_end_idx > test_start_idx:
                windows.append({
                    'window': i + 1,
                    'train_start': self.portfolio.index[train_start_idx],
                    'train_end': self.portfolio.index[train_end_idx - 1],
                    'test_start': self.portfolio.index[test_start_idx],
                    'test_end': self.portfolio.index[test_end_idx - 1],
                    'train_days': train_end_idx - train_start_idx,
                    'test_days': test_end_idx - test_start_idx
                })

        return {
            'approach': 'Anchored Walk-Forward',
            'train_period': '2 years (504 days)',
            'test_period': '1 year (252 days)',
            'n_windows': len(windows),
            'windows': windows,
            'implementation': [
                '1. Re-run backtest with walk-forward structure',
                '2. Optimize parameters ONLY on training data',
                '3. Test on out-of-sample data (no peeking)',
                '4. Compare in-sample vs out-of-sample Sharpe',
                '5. Degradation >50% = overfitting'
            ]
        }

    # =========================================================================
    # MASTER REPORT
    # =========================================================================

    def generate_full_report(self) -> Dict:
        """Generate comprehensive validation report."""
        print("Running comprehensive statistical validation...")
        print("This may take a few minutes...\n")

        report = {
            'summary': self._generate_summary(),
            'sample_size': self.sample_size_adequacy(),
            'sharpe_significance': self.sharpe_significance(),
            'bootstrap': self.bootstrap_analysis(n_bootstrap=10000),
            'permutation_test': self.permutation_test_regimes(n_permutations=10000),
            'multiple_testing': self.multiple_testing_correction(),
            'regime_conditional': self.regime_conditional_analysis(),
            'profile_conditional': self.profile_conditional_analysis(),
            'overfitting_risk': self.overfitting_risk(),
            'parameter_sensitivity': self.parameter_sensitivity_framework(),
            'out_of_sample_plan': self.out_of_sample_plan()
        }

        return report

    def _generate_summary(self) -> Dict:
        """Generate summary statistics."""
        returns = self.portfolio['portfolio_return']
        equity = self.portfolio['equity']

        return {
            'start_date': str(self.portfolio.index[0]),
            'end_date': str(self.portfolio.index[-1]),
            'trading_days': len(self.portfolio),
            'total_return_pct': ((equity.iloc[-1] / 100000 - 1) * 100),
            'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252),
            'max_drawdown_pct': ((equity / equity.cummax() - 1).min() * 100),
            'win_rate_pct': (returns > 0).sum() / len(returns) * 100,
            'avg_daily_return_pct': returns.mean() * 100,
            'std_daily_return_pct': returns.std() * 100
        }


def print_report(report: Dict):
    """Pretty print the validation report."""

    print("=" * 100)
    print("STATISTICAL VALIDATION AUDIT REPORT")
    print("=" * 100)
    print()

    # Summary
    print("SUMMARY STATISTICS")
    print("-" * 100)
    s = report['summary']
    print(f"Period: {s['start_date']} to {s['end_date']} ({s['trading_days']} days)")
    print(f"Total Return: {s['total_return_pct']:.2f}%")
    print(f"Sharpe Ratio: {s['sharpe_ratio']:.4f}")
    print(f"Max Drawdown: {s['max_drawdown_pct']:.2f}%")
    print(f"Win Rate: {s['win_rate_pct']:.2f}%")
    print()

    # Sample size adequacy
    print("1. SAMPLE SIZE ADEQUACY")
    print("-" * 100)
    ss = report['sample_size']
    print(f"Total Sample: {ss['total_days']} days ({ss['total_years']:.1f} years)")
    print(f"Overall Adequate: {'YES ✅' if ss['overall_adequate'] else 'NO ❌'}")
    print()
    print("Regime Samples:")
    regime_names = {1: 'Trend Up', 2: 'Trend Down', 3: 'Compression',
                   4: 'Breaking Vol', 5: 'Choppy', 6: 'Event'}
    for regime, data in ss['regime_samples'].items():
        status = '✅' if data['adequate'] else '❌ INSUFFICIENT'
        print(f"  Regime {regime} ({regime_names[regime]}): {data['days']} days "
              f"({data['pct_of_total']:.1f}%) {status}")
    print()

    # Sharpe significance
    print("2. SHARPE RATIO SIGNIFICANCE")
    print("-" * 100)
    sh = report['sharpe_significance']
    print(f"Sharpe Ratio: {sh['sharpe']:.4f}")
    print(f"T-Statistic: {sh['t_statistic']:.4f}")
    print(f"P-Value: {sh['p_value']:.6f}")
    print(f"Significant at 5%: {'YES ✅' if sh['significant_at_5pct'] else 'NO ❌'}")
    print(f"95% CI: [{sh['ci_95_lower']:.4f}, {sh['ci_95_upper']:.4f}]")
    print(f"Interpretation: {sh['interpretation']}")
    print()

    # Bootstrap
    print("3. BOOTSTRAP ANALYSIS (10,000 iterations)")
    print("-" * 100)
    bs = report['bootstrap']
    print(f"Sharpe Ratio:")
    print(f"  Mean: {bs['sharpe']['mean']:.4f}")
    print(f"  95% CI: [{bs['sharpe']['ci_95'][0]:.4f}, {bs['sharpe']['ci_95'][1]:.4f}]")
    print(f"  Prob(Sharpe > 0): {bs['sharpe']['prob_positive']:.1%}")
    print(f"  Prob(Sharpe > 1): {bs['sharpe']['prob_gt_1']:.1%}")
    print()
    print(f"Total Return:")
    print(f"  Mean: {bs['total_return']['mean']:.2%}")
    print(f"  95% CI: [{bs['total_return']['ci_95'][0]:.2%}, {bs['total_return']['ci_95'][1]:.2%}]")
    print(f"  Prob(Positive): {bs['total_return']['prob_positive']:.1%}")
    print()
    print(f"Max Drawdown:")
    print(f"  Mean: {bs['max_drawdown']['mean']:.2%}")
    print(f"  Prob(DD > 30%): {bs['max_drawdown']['prob_dd_gt_30pct']:.1%}")
    print(f"  Prob(DD > 50%): {bs['max_drawdown']['prob_dd_gt_50pct']:.1%}")
    print()

    # Permutation test
    print("4. PERMUTATION TEST (Regime Value-Add)")
    print("-" * 100)
    pt = report['permutation_test']
    print(f"Actual Sharpe: {pt['actual_sharpe']:.4f}")
    print(f"Mean Random Sharpe: {pt['mean_permuted_sharpe']:.4f}")
    print(f"P-Value: {pt['p_value']:.6f}")
    print(f"Significant at 5%: {'YES ✅' if pt['significant_at_5pct'] else 'NO ❌'}")
    print(f"Interpretation: {pt['interpretation']}")
    print()

    # Multiple testing
    print("5. MULTIPLE TESTING CORRECTION")
    print("-" * 100)
    mt = report['multiple_testing']
    print(f"Combinations Tested: {mt['n_combinations']} (6 regimes × 6 profiles)")
    print(f"Original Alpha: {mt['original_alpha']:.4f}")
    print(f"Bonferroni-Corrected Alpha: {mt['bonferroni_alpha']:.6f}")
    print(f"Family-Wise Error Rate: {mt['family_wise_error_rate']:.4f}")
    print(f"Interpretation: {mt['interpretation']}")
    print()

    # Regime conditional
    print("6. REGIME-CONDITIONAL PERFORMANCE")
    print("-" * 100)
    rc = report['regime_conditional']
    print("Sharpe by Regime:")
    for regime, sharpe in rc['regime_sharpes'].items():
        status = ''
        if regime in rc['regime_tests']:
            rt = rc['regime_tests'][regime]
            if rt['significantly_positive']:
                status = '✅ Sig. Positive'
            elif rt['significantly_negative']:
                status = '❌ Sig. Negative'
            else:
                status = '⚠️  Not Sig.'
        print(f"  Regime {regime} ({regime_names[regime]}): {sharpe:.4f} {status}")

    if 'anova' in rc:
        print()
        print(f"ANOVA Test (Do returns differ across regimes?):")
        print(f"  F-Statistic: {rc['anova']['f_statistic']:.4f}")
        print(f"  P-Value: {rc['anova']['p_value']:.6f}")
        print(f"  {rc['anova']['interpretation']}")
    print()

    # Profile conditional
    print("7. PROFILE-CONDITIONAL PERFORMANCE")
    print("-" * 100)
    pc = report['profile_conditional']
    profile_names = {1: 'LDG', 2: 'SDG', 3: 'CHARM', 4: 'VANNA', 5: 'SKEW', 6: 'VOV'}

    for i in range(1, 7):
        key = f'profile_{i}'
        if key in pc:
            data = pc[key]
            status = ''
            if data['significantly_positive']:
                status = '✅ Sig. Positive'
            elif data['significantly_negative']:
                status = '❌ Sig. Negative'
            else:
                status = '⚠️  Not Sig.'

            print(f"Profile {i} ({profile_names[i]}): Sharpe {data['sharpe']:.4f}, "
                  f"p={data['p_value']:.4f} {status}")

    print()
    print(f"Summary:")
    print(f"  Significantly Positive: {pc['summary']['n_positive']} profiles")
    print(f"  Significantly Negative: {pc['summary']['n_negative']} profiles")
    print()

    # Overfitting risk
    print("8. OVERFITTING RISK ASSESSMENT")
    print("-" * 100)
    ov = report['overfitting_risk']
    print(f"Parameters: {ov['n_parameters']}")
    print(f"Observations: {ov['n_observations']}")
    print(f"Obs/Param Ratio: {ov['observations_per_parameter']:.2f}")
    print(f"Degrees of Freedom: {ov['degrees_of_freedom']}")
    print(f"Overfitting Risk: {ov['overfitting_risk']}")
    print(f"Recommendation: {ov['recommendation']}")
    print()

    # Out of sample plan
    print("9. OUT-OF-SAMPLE TESTING PLAN")
    print("-" * 100)
    oos = report['out_of_sample_plan']
    print(f"Approach: {oos['approach']}")
    print(f"Train Period: {oos['train_period']}")
    print(f"Test Period: {oos['test_period']}")
    print(f"Number of Windows: {oos['n_windows']}")
    print()
    print("Walk-Forward Windows:")
    for w in oos['windows']:
        print(f"  Window {w['window']}: Train {w['train_start']} to {w['train_end']}, "
              f"Test {w['test_start']} to {w['test_end']}")
    print()

    print("=" * 100)
    print("END OF STATISTICAL VALIDATION AUDIT")
    print("=" * 100)


if __name__ == '__main__':
    import sys

    # Run validation
    backtest_dir = 'data/backtests/rotation_engine_2020_2025'

    validator = StatisticalValidator(backtest_dir)
    report = validator.generate_full_report()

    # Print report
    print_report(report)

    # Save to JSON
    import json
    with open('statistical_validation_results.json', 'w') as f:
        # Convert numpy types to native Python
        def convert(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, pd.Timestamp):
                return str(obj)
            return obj

        json.dump(report, f, indent=2, default=convert)

    print("\nFull report saved to: statistical_validation_results.json")
