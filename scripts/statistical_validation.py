"""
Statistical Validation Red Team Attack

This script performs rigorous statistical tests on rotation engine results:
1. Sharpe ratio significance testing
2. Regime transition predictive power
3. Multiple testing corrections
4. Monte Carlo simulation vs random strategies
5. Autocorrelation analysis
6. Profile score predictiveness

MISSION: Prove results are statistically significant, not luck.
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import t as t_dist
import sys
from pathlib import Path
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from backtest import RotationEngine
from analysis import PerformanceMetrics


class StatisticalValidator:
    """Red team statistical validator."""

    def __init__(self):
        self.results = {}

    def run_full_validation(self) -> Dict:
        """Execute complete statistical validation battery."""

        print("=" * 80)
        print("STATISTICAL VALIDATION RED TEAM ATTACK")
        print("=" * 80)
        print()

        # Run rotation engine to get results
        print("Step 0: Running rotation engine backtest...")
        engine = RotationEngine(
            max_profile_weight=0.40,
            min_profile_weight=0.05,
            vix_scale_threshold=30.0,
            vix_scale_factor=0.5
        )

        backtest_results = engine.run(start_date='2020-01-01', end_date='2024-12-31')
        portfolio = backtest_results['portfolio']

        print(f"\n  Loaded {len(portfolio)} days of backtest results")
        print()

        # Extract daily returns
        daily_returns = portfolio['portfolio_pnl'].values

        # Test 1: Sharpe Ratio Significance
        print("\n" + "=" * 80)
        print("TEST 1: SHARPE RATIO SIGNIFICANCE")
        print("=" * 80)
        sharpe_results = self._test_sharpe_significance(daily_returns)
        self.results['sharpe'] = sharpe_results
        self._print_sharpe_results(sharpe_results)

        # Test 2: Regime Predictive Power
        print("\n" + "=" * 80)
        print("TEST 2: REGIME PREDICTIVE POWER")
        print("=" * 80)
        regime_results = self._test_regime_predictiveness(portfolio)
        self.results['regime'] = regime_results
        self._print_regime_results(regime_results)

        # Test 3: Multiple Testing Corrections
        print("\n" + "=" * 80)
        print("TEST 3: MULTIPLE TESTING CORRECTIONS")
        print("=" * 80)
        multiple_test_results = self._test_multiple_testing(backtest_results)
        self.results['multiple_testing'] = multiple_test_results
        self._print_multiple_testing_results(multiple_test_results)

        # Test 4: Monte Carlo vs Random Strategies
        print("\n" + "=" * 80)
        print("TEST 4: MONTE CARLO SIMULATION VS RANDOM STRATEGIES")
        print("=" * 80)
        monte_carlo_results = self._run_monte_carlo(daily_returns, n_simulations=1000)
        self.results['monte_carlo'] = monte_carlo_results
        self._print_monte_carlo_results(monte_carlo_results)

        # Test 5: Autocorrelation Analysis
        print("\n" + "=" * 80)
        print("TEST 5: AUTOCORRELATION ANALYSIS")
        print("=" * 80)
        autocorr_results = self._test_autocorrelation(portfolio)
        self.results['autocorrelation'] = autocorr_results
        self._print_autocorr_results(autocorr_results)

        # Test 6: Profile Score Predictiveness
        print("\n" + "=" * 80)
        print("TEST 6: PROFILE SCORE PREDICTIVENESS")
        print("=" * 80)
        profile_pred_results = self._test_profile_predictiveness(portfolio)
        self.results['profile_predictiveness'] = profile_pred_results
        self._print_profile_pred_results(profile_pred_results)

        # Final Verdict
        print("\n" + "=" * 80)
        print("FINAL STATISTICAL VERDICT")
        print("=" * 80)
        self._print_final_verdict()

        return self.results

    def _test_sharpe_significance(self, returns: np.ndarray) -> Dict:
        """
        Test if Sharpe ratio is statistically different from zero.

        Uses t-test and bootstrap confidence intervals.
        """
        # Remove any NaN values
        returns = returns[~np.isnan(returns)]

        n = len(returns)
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)

        # Sharpe ratio (daily, not annualized for statistical testing)
        sharpe = mean_return / std_return if std_return > 0 else 0

        # Annualized Sharpe (252 trading days)
        sharpe_annual = sharpe * np.sqrt(252)

        # T-statistic for Sharpe != 0
        # Under H0: Sharpe = 0, t-stat = sqrt(n) * Sharpe
        t_stat = np.sqrt(n) * sharpe

        # P-value (two-tailed)
        p_value = 2 * (1 - t_dist.cdf(abs(t_stat), df=n-1))

        # Bootstrap confidence intervals (10,000 simulations)
        print("  Running bootstrap (10,000 simulations)...")
        bootstrap_sharpes = []
        n_bootstrap = 10000

        for _ in range(n_bootstrap):
            # Resample with replacement
            boot_sample = np.random.choice(returns, size=n, replace=True)
            boot_mean = np.mean(boot_sample)
            boot_std = np.std(boot_sample, ddof=1)
            boot_sharpe = boot_mean / boot_std if boot_std > 0 else 0
            bootstrap_sharpes.append(boot_sharpe * np.sqrt(252))  # Annualized

        bootstrap_sharpes = np.array(bootstrap_sharpes)
        ci_95 = np.percentile(bootstrap_sharpes, [2.5, 97.5])
        ci_99 = np.percentile(bootstrap_sharpes, [0.5, 99.5])

        # Minimum sample size (rule of thumb: need n > 100 for Sharpe tests)
        min_sample_adequate = n >= 100

        return {
            'sharpe_daily': sharpe,
            'sharpe_annual': sharpe_annual,
            't_statistic': t_stat,
            'p_value': p_value,
            'ci_95_lower': ci_95[0],
            'ci_95_upper': ci_95[1],
            'ci_99_lower': ci_99[0],
            'ci_99_upper': ci_99[1],
            'sample_size': n,
            'min_sample_adequate': min_sample_adequate,
            'mean_daily_return': mean_return,
            'std_daily_return': std_return
        }

    def _test_regime_predictiveness(self, portfolio: pd.DataFrame) -> Dict:
        """
        Test if regime at time t predicts P&L from t+1 to t+n.

        If regimes are predictive, knowing current regime should predict future returns.
        If only descriptive, regime explains past but not future.
        """
        # Create lagged regime (regime at t-1 predicts return at t)
        portfolio_copy = portfolio.copy()
        portfolio_copy['regime_lag1'] = portfolio_copy['regime'].shift(1)
        portfolio_copy = portfolio_copy.dropna(subset=['regime_lag1'])

        # Test: Does regime at t-1 predict portfolio_pnl at t?
        regime_groups = portfolio_copy.groupby('regime_lag1')['portfolio_pnl'].mean()

        # ANOVA test: Are mean returns different across regimes?
        regime_samples = [
            portfolio_copy[portfolio_copy['regime_lag1'] == regime]['portfolio_pnl'].values
            for regime in portfolio_copy['regime_lag1'].unique()
        ]

        # F-test
        f_stat, p_value_anova = stats.f_oneway(*regime_samples)

        # Also test forward prediction (1-week, 2-week)
        portfolio_copy['forward_5d_pnl'] = portfolio_copy['portfolio_pnl'].rolling(5).sum().shift(-5)
        portfolio_copy['forward_10d_pnl'] = portfolio_copy['portfolio_pnl'].rolling(10).sum().shift(-10)

        # Drop NaN
        forward_test = portfolio_copy.dropna(subset=['forward_5d_pnl', 'forward_10d_pnl'])

        # Does regime predict forward 5-day returns?
        regime_samples_5d = [
            forward_test[forward_test['regime'] == regime]['forward_5d_pnl'].values
            for regime in forward_test['regime'].unique()
        ]
        f_stat_5d, p_value_5d = stats.f_oneway(*regime_samples_5d)

        # Does regime predict forward 10-day returns?
        regime_samples_10d = [
            forward_test[forward_test['regime'] == regime]['forward_10d_pnl'].values
            for regime in forward_test['regime'].unique()
        ]
        f_stat_10d, p_value_10d = stats.f_oneway(*regime_samples_10d)

        # Regime autocorrelation (are regimes persistent?)
        regime_numeric = portfolio['regime'].values
        regime_autocorr_1 = np.corrcoef(regime_numeric[:-1], regime_numeric[1:])[0, 1]

        # Ljung-Box test for regime autocorrelation
        from statsmodels.stats.diagnostic import acorr_ljungbox
        lb_test = acorr_ljungbox(regime_numeric, lags=[5], return_df=True)
        lb_p_value = lb_test['lb_pvalue'].iloc[0]

        return {
            'regime_mean_returns': regime_groups.to_dict(),
            'anova_f_stat': f_stat,
            'anova_p_value': p_value_anova,
            'forward_5d_f_stat': f_stat_5d,
            'forward_5d_p_value': p_value_5d,
            'forward_10d_f_stat': f_stat_10d,
            'forward_10d_p_value': p_value_10d,
            'regime_autocorr_lag1': regime_autocorr_1,
            'ljung_box_p_value': lb_p_value
        }

    def _test_multiple_testing(self, backtest_results: Dict) -> Dict:
        """
        Apply multiple testing corrections.

        We tested:
        - 6 profiles
        - 6 regimes
        - Multiple combinations

        Need to correct for family-wise error rate.
        """
        # Count hypotheses tested
        n_profiles = 6
        n_regimes = 6  # Actually 5 in data but 6 possible

        # Each profile tested in specific regimes
        profile_configs = {
            'profile_1': [1, 3],  # 2 regimes
            'profile_2': [2, 5],  # 2 regimes
            'profile_3': [3],     # 1 regime
            'profile_4': [1],     # 1 regime
            'profile_5': [2],     # 1 regime
            'profile_6': [4]      # 1 regime
        }

        # Total combinations tested
        n_tests = sum(len(regimes) for regimes in profile_configs.values())

        # Also tested profile score thresholds (assume 1 threshold per profile tested)
        n_threshold_tests = n_profiles

        # Total hypotheses
        total_tests = n_tests + n_threshold_tests

        # Bonferroni correction (conservative)
        alpha_original = 0.05
        alpha_bonferroni = alpha_original / total_tests

        # Holm-Bonferroni (less conservative)
        # Would need actual p-values for each test
        # For now, just show what the correction would be

        # False Discovery Rate (Benjamini-Hochberg)
        # Would need sorted p-values

        # Get profile attribution p-values (if we had individual profile Sharpe tests)
        attribution = backtest_results['attribution_by_profile']
        n_positive_profiles = len(attribution[attribution['total_pnl'] > 0])
        n_negative_profiles = len(attribution[attribution['total_pnl'] < 0])

        return {
            'n_profile_regime_tests': n_tests,
            'n_threshold_tests': n_threshold_tests,
            'total_tests': total_tests,
            'alpha_original': alpha_original,
            'alpha_bonferroni': alpha_bonferroni,
            'n_positive_profiles': n_positive_profiles,
            'n_negative_profiles': n_negative_profiles,
            'profile_configs': profile_configs
        }

    def _run_monte_carlo(self, actual_returns: np.ndarray, n_simulations: int = 1000) -> Dict:
        """
        Generate random strategies and compare actual performance.

        Methods:
        1. Permutation test: Shuffle actual returns randomly
        2. Random allocation: Generate random weight strategies
        """
        actual_returns = actual_returns[~np.isnan(actual_returns)]
        n = len(actual_returns)

        # Actual Sharpe
        actual_sharpe = (np.mean(actual_returns) / np.std(actual_returns, ddof=1)) * np.sqrt(252)

        print(f"  Running {n_simulations} permutation tests...")

        # Permutation test: shuffle returns
        permuted_sharpes = []
        for _ in range(n_simulations):
            shuffled = np.random.permutation(actual_returns)
            perm_sharpe = (np.mean(shuffled) / np.std(shuffled, ddof=1)) * np.sqrt(252)
            permuted_sharpes.append(perm_sharpe)

        permuted_sharpes = np.array(permuted_sharpes)

        # Percentile rank
        percentile = stats.percentileofscore(permuted_sharpes, actual_sharpe)

        # P-value: what fraction of random strategies beat us?
        p_value_permutation = np.mean(permuted_sharpes >= actual_sharpe)

        # Distribution stats
        median_random = np.median(permuted_sharpes)
        mean_random = np.mean(permuted_sharpes)

        return {
            'actual_sharpe': actual_sharpe,
            'n_simulations': n_simulations,
            'median_random_sharpe': median_random,
            'mean_random_sharpe': mean_random,
            'percentile_rank': percentile,
            'p_value_vs_random': p_value_permutation,
            'random_sharpe_5th': np.percentile(permuted_sharpes, 5),
            'random_sharpe_95th': np.percentile(permuted_sharpes, 95)
        }

    def _test_autocorrelation(self, portfolio: pd.DataFrame) -> Dict:
        """
        Test for autocorrelation in returns and regimes.

        - Serial correlation inflates Sharpe artificially
        - Check if returns are independent
        """
        returns = portfolio['portfolio_pnl'].dropna().values

        # Autocorrelation at various lags
        acf_lag1 = np.corrcoef(returns[:-1], returns[1:])[0, 1]
        acf_lag5 = np.corrcoef(returns[:-5], returns[5:])[0, 1]

        # Ljung-Box test for autocorrelation
        from statsmodels.stats.diagnostic import acorr_ljungbox
        lb_test = acorr_ljungbox(returns, lags=[1, 5, 10], return_df=True)

        # Durbin-Watson statistic (around 2 = no autocorrelation)
        from statsmodels.stats.stattools import durbin_watson
        dw_stat = durbin_watson(returns)

        return {
            'acf_lag1': acf_lag1,
            'acf_lag5': acf_lag5,
            'ljung_box_lag1_p': lb_test['lb_pvalue'].iloc[0],
            'ljung_box_lag5_p': lb_test['lb_pvalue'].iloc[1],
            'ljung_box_lag10_p': lb_test['lb_pvalue'].iloc[2],
            'durbin_watson': dw_stat
        }

    def _test_profile_predictiveness(self, portfolio: pd.DataFrame) -> Dict:
        """
        Test if profile scores predict forward P&L.

        For each profile, correlate score at t with P&L at t+1.
        """
        # Extract weight columns
        weight_cols = [col for col in portfolio.columns if col.endswith('_weight')]
        pnl_cols = [col for col in portfolio.columns if col.endswith('_pnl') and col not in ['portfolio_pnl', 'cumulative_pnl']]

        # For each profile, test if weight predicts future P&L
        results = {}

        for weight_col in weight_cols:
            profile_name = weight_col.replace('_weight', '')
            pnl_col = f"{profile_name}_pnl"

            if pnl_col not in portfolio.columns:
                continue

            # Create forward P&L
            portfolio_copy = portfolio.copy()
            portfolio_copy['forward_pnl'] = portfolio_copy[pnl_col].shift(-1)

            # Drop NaN
            test_data = portfolio_copy[[weight_col, 'forward_pnl']].dropna()

            if len(test_data) < 10:
                continue

            # Correlation
            corr = test_data[weight_col].corr(test_data['forward_pnl'])

            # T-test for correlation
            n = len(test_data)
            if abs(corr) < 1:
                t_stat = corr * np.sqrt(n - 2) / np.sqrt(1 - corr**2)
                p_value = 2 * (1 - t_dist.cdf(abs(t_stat), df=n-2))
            else:
                t_stat = np.nan
                p_value = np.nan

            results[profile_name] = {
                'correlation': corr,
                't_statistic': t_stat,
                'p_value': p_value,
                'n_samples': n
            }

        return results

    # Print methods
    def _print_sharpe_results(self, results: Dict):
        """Print Sharpe ratio test results."""
        print(f"\nSharpe Ratio (Annualized): {results['sharpe_annual']:.2f}")
        print(f"T-statistic:               {results['t_statistic']:.2f}")
        print(f"P-value:                   {results['p_value']:.4f}")
        print(f"\n95% Confidence Interval:   [{results['ci_95_lower']:.2f}, {results['ci_95_upper']:.2f}]")
        print(f"99% Confidence Interval:   [{results['ci_99_lower']:.2f}, {results['ci_99_upper']:.2f}]")
        print(f"\nSample Size:               {results['sample_size']} days")

        # Significance assessment
        if results['p_value'] < 0.01:
            sig_status = "✅ SIGNIFICANT (p < 0.01)"
        elif results['p_value'] < 0.05:
            sig_status = "⚠️ MARGINAL (p < 0.05)"
        else:
            sig_status = "❌ NOT SIGNIFICANT (p >= 0.05)"

        print(f"\nSignificance:              {sig_status}")

        # Sample size assessment
        if results['min_sample_adequate']:
            size_status = "✅ ADEQUATE (n >= 100)"
        else:
            size_status = "⚠️ SMALL (n < 100)"

        print(f"Sample Size Adequacy:      {size_status}")

        # CI includes zero?
        if results['ci_95_lower'] < 0 < results['ci_95_upper']:
            print("\n⚠️ WARNING: 95% CI includes zero - Sharpe not distinguishable from zero")
        else:
            print("\n✅ 95% CI does not include zero")

    def _print_regime_results(self, results: Dict):
        """Print regime predictiveness results."""
        print("\nRegime Mean Returns (lagged):")
        for regime, mean_return in sorted(results['regime_mean_returns'].items()):
            print(f"  Regime {int(regime)}: ${mean_return:>8.2f}/day")

        print(f"\nANOVA Test (regime predicts next-day return):")
        print(f"  F-statistic: {results['anova_f_stat']:.2f}")
        print(f"  P-value:     {results['anova_p_value']:.4f}")

        print(f"\nForward Prediction (regime predicts future 5-day returns):")
        print(f"  F-statistic: {results['forward_5d_f_stat']:.2f}")
        print(f"  P-value:     {results['forward_5d_p_value']:.4f}")

        print(f"\nForward Prediction (regime predicts future 10-day returns):")
        print(f"  F-statistic: {results['forward_10d_f_stat']:.2f}")
        print(f"  P-value:     {results['forward_10d_p_value']:.4f}")

        print(f"\nRegime Persistence:")
        print(f"  Autocorrelation (lag 1): {results['regime_autocorr_lag1']:.3f}")
        print(f"  Ljung-Box p-value:       {results['ljung_box_p_value']:.4f}")

        # Assessment
        if results['anova_p_value'] < 0.05:
            print("\n✅ Regimes have PREDICTIVE power (p < 0.05)")
        else:
            print("\n❌ Regimes are DESCRIPTIVE only (p >= 0.05)")

    def _print_multiple_testing_results(self, results: Dict):
        """Print multiple testing correction results."""
        print(f"\nTests Conducted:")
        print(f"  Profile-regime combinations: {results['n_profile_regime_tests']}")
        print(f"  Threshold tests:             {results['n_threshold_tests']}")
        print(f"  TOTAL TESTS:                 {results['total_tests']}")

        print(f"\nBonferroni Correction:")
        print(f"  Original α:     {results['alpha_original']:.4f}")
        print(f"  Adjusted α:     {results['alpha_bonferroni']:.6f}")

        print(f"\nProfile Results:")
        print(f"  Positive P&L: {results['n_positive_profiles']}/6 profiles")
        print(f"  Negative P&L: {results['n_negative_profiles']}/6 profiles")

        print("\n⚠️ WARNING: Multiple testing correction required")
        print(f"  Any p-value must be < {results['alpha_bonferroni']:.6f} to be significant")

    def _print_monte_carlo_results(self, results: Dict):
        """Print Monte Carlo results."""
        print(f"\nActual Strategy Sharpe:      {results['actual_sharpe']:.2f}")
        print(f"Random Strategies (n={results['n_simulations']}):")
        print(f"  Median Sharpe:             {results['median_random_sharpe']:.2f}")
        print(f"  Mean Sharpe:               {results['mean_random_sharpe']:.2f}")
        print(f"  5th percentile:            {results['random_sharpe_5th']:.2f}")
        print(f"  95th percentile:           {results['random_sharpe_95th']:.2f}")

        print(f"\nPercentile Rank:             {results['percentile_rank']:.1f}th percentile")
        print(f"P-value vs Random:           {results['p_value_vs_random']:.4f}")

        # Assessment
        if results['percentile_rank'] >= 95:
            print("\n✅ BEATS RANDOM: Strategy in top 5% of random strategies")
        elif results['percentile_rank'] >= 90:
            print("\n⚠️ MARGINAL: Strategy in top 10% (not top 5%)")
        else:
            print("\n❌ DOES NOT BEAT RANDOM: Strategy not in top 10%")

    def _print_autocorr_results(self, results: Dict):
        """Print autocorrelation results."""
        print(f"\nReturn Autocorrelation:")
        print(f"  Lag 1:  {results['acf_lag1']:.3f}")
        print(f"  Lag 5:  {results['acf_lag5']:.3f}")

        print(f"\nLjung-Box Test (autocorrelation):")
        print(f"  Lag 1 p-value:  {results['ljung_box_lag1_p']:.4f}")
        print(f"  Lag 5 p-value:  {results['ljung_box_lag5_p']:.4f}")
        print(f"  Lag 10 p-value: {results['ljung_box_lag10_p']:.4f}")

        print(f"\nDurbin-Watson Statistic:    {results['durbin_watson']:.3f}")
        print("  (2.0 = no autocorrelation, <1.5 or >2.5 is concerning)")

        # Assessment
        if abs(results['acf_lag1']) < 0.1 and results['ljung_box_lag1_p'] > 0.05:
            print("\n✅ No significant autocorrelation detected")
        else:
            print("\n⚠️ WARNING: Autocorrelation detected - may inflate Sharpe")

    def _print_profile_pred_results(self, results: Dict):
        """Print profile predictiveness results."""
        print("\nProfile Weight → Forward P&L Correlations:")

        for profile_name, stats in sorted(results.items()):
            print(f"\n  {profile_name}:")
            print(f"    Correlation: {stats['correlation']:>7.3f}")
            print(f"    P-value:     {stats['p_value']:>7.4f}")

            if stats['p_value'] < 0.05:
                print(f"    Status:      ✅ PREDICTIVE (p < 0.05)")
            else:
                print(f"    Status:      ❌ Not predictive (p >= 0.05)")

    def _print_final_verdict(self):
        """Print overall statistical verdict."""

        # Collect evidence
        sharpe_sig = self.results['sharpe']['p_value'] < 0.05
        sharpe_strong = self.results['sharpe']['p_value'] < 0.01
        ci_excludes_zero = not (self.results['sharpe']['ci_95_lower'] < 0 < self.results['sharpe']['ci_95_upper'])

        regime_predictive = self.results['regime']['anova_p_value'] < 0.05

        monte_carlo_beats = self.results['monte_carlo']['percentile_rank'] >= 90
        monte_carlo_strong = self.results['monte_carlo']['percentile_rank'] >= 95

        no_autocorr = abs(self.results['autocorrelation']['acf_lag1']) < 0.1

        # Count red flags
        red_flags = []

        if not sharpe_sig:
            red_flags.append("Sharpe ratio not statistically significant")

        if not ci_excludes_zero:
            red_flags.append("95% CI includes zero")

        if not regime_predictive:
            red_flags.append("Regimes are descriptive, not predictive")

        if not monte_carlo_beats:
            red_flags.append("Does not beat random strategies at 90th percentile")

        if not no_autocorr:
            red_flags.append("Autocorrelation may inflate Sharpe")

        # Decision logic
        if sharpe_strong and ci_excludes_zero and monte_carlo_strong and no_autocorr:
            verdict = "✅ STATISTICALLY ROBUST"
            recommendation = "Strategy is statistically sound. Results are unlikely due to chance."
        elif sharpe_sig and monte_carlo_beats:
            verdict = "⚠️ MARGINAL SIGNIFICANCE"
            recommendation = "Some evidence of edge, but not overwhelming. Proceed with caution."
        else:
            verdict = "❌ NOT STATISTICALLY SIGNIFICANT"
            recommendation = "Results cannot be distinguished from luck. DO NOT DEPLOY."

        print(f"\n🎯 VERDICT: {verdict}")
        print(f"\n{recommendation}")

        if red_flags:
            print(f"\n⚠️ RED FLAGS FOUND ({len(red_flags)}):")
            for i, flag in enumerate(red_flags, 1):
                print(f"  {i}. {flag}")
        else:
            print("\n✅ NO CRITICAL RED FLAGS")

        # Specific recommendations
        print("\n📋 RECOMMENDATIONS:")

        if not sharpe_sig:
            print("  • Gather more data or refine strategy - current Sharpe not significant")

        if not regime_predictive:
            print("  • Regimes don't predict future returns - reconsider regime-based allocation")

        if not monte_carlo_beats:
            print("  • Strategy barely beats random - likely insufficient edge")

        if red_flags:
            print("  • DO NOT deploy with real capital until statistical issues resolved")
        else:
            print("  • Statistical validation passed - safe to proceed to next validation stage")


if __name__ == '__main__':
    validator = StatisticalValidator()
    results = validator.run_full_validation()
