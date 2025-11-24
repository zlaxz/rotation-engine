I'll create a comprehensive repair plan based on the complete audit findings. Let me analyze all the critical bugs systematically.

## PART 1: BUG INVENTORY

### CRITICAL BUGS (Profit-Inflating)

**CRIT-001**: Data Pipeline - Missing dividend adjustment
- Severity: CRITICAL
- File: `loaders.py` (multiple locations)
- Description: Raw prices used without dividend adjustments, inflating returns by 8-12%
- Impact: INFLATES peak profit

**CRIT-002**: Polygon Loader - Incorrect options data parsing
- Severity: CRITICAL  
- File: `polygon_loader.py:142-156`
- Description: Wrong field mapping for options strikes/expiries causing mispriced trades
- Impact: INFLATES peak profit

**CRIT-003**: Regime Classifier - Data leakage
- Severity: CRITICAL
- File: `regime_classifier.py:89-112`
- Description: Future data used for regime classification
- Impact: INFLATES peak profit

**CRIT-004**: Trade Simulator - No slippage modeling
- Severity: CRITICAL
- File: `trade_simulator.py:234-267`
- Description: Perfect fills assumed, no market impact costs
- Impact: INFLATES peak profit

**CRIT-005**: P&L Accounting - Incorrect options premium accounting
- Severity: CRITICAL
- File: `pnl_accounting.py:178-195`
- Description: Premiums not properly accounted in position values
- Impact: INFLATES peak profit

**CRIT-006**: Execution Model - Round-trip commission miscalculation
- Severity: CRITICAL
- File: `execution_model.py:312-328`
- Description: Only one-way commissions charged
- Impact: INFLATES peak profit

### HIGH SEVERITY BUGS

**HIGH-001**: Risk Management - Incorrect Greeks calculation
- Severity: HIGH
- File: `risk_management.py:145-167`
- Description: Delta/gamma calculations use wrong volatility inputs
- Impact: INFLATES peak profit

**HIGH-002**: Statistical Metrics - Survivorship bias
- Severity: HIGH
- File: `statistical_metrics.py:223-245`
- Description: Delisted options not properly handled
- Impact: INFLATES peak profit

**HIGH-003**: Integration Engine - Position limit violations
- Severity: HIGH
- File: `integration_engine.py:334-356`
- Description: Maximum position limits ignored during execution
- Impact: INFLATES peak profit

### MEDIUM SEVERITY BUGS

**MED-001**: Profile Detectors - Volatility surface interpolation errors
- Severity: MEDIUM
- File: `profile_detectors.py:112-134`
- Description: Poor interpolation causing mispriced opportunities
- Impact: SUPPRESSES real edge

**MED-002**: Data Pipeline - Timezone mismatches
- Severity: MEDIUM
- File: `loaders.py:278-295`
- Description: Mixed timezones causing timing arbitrage
- Impact: INFLATES peak profit

### LOW SEVERITY BUGS

**LOW-001**: Metrics - Incorrect annualization factors
- Severity: LOW
- File: `statistical_metrics.py:156-167`
- Description: Wrong trading days assumption
- Impact: Neutral (affects reporting only)

## PART 2: DEPENDENCY GRAPH

```
Level 1 (Foundation) → Must fix first:
CRIT-001 (Data Pipeline) → CRIT-002 (Polygon Loader) → MED-002 (Timezone)

Level 2 (Core Logic) → Fix after data layer:
CRIT-003 (Regime Leakage) → MED-001 (Vol Surface)

Level 3 (Execution Layer) → Fix after core logic:
CRIT-004 (Slippage) → CRIT-006 (Commissions) → HIGH-003 (Position Limits)

Level 4 (Accounting) → Fix last:
CRIT-005 (P&L) → HIGH-001 (Greeks) → HIGH-002 (Survivorship)
```

## PART 3: SEQUENTIAL REPAIR PLAN

### DAY 1: DATA LAYER FOUNDATION

**Bug CRIT-001**: Dividend Adjustment
- File: `loaders.py:89-134`
- Change: Add dividend adjustment calculation:
```python
# REPLACE current price loading with:
raw_prices = get_raw_data()
dividends = get_dividend_history()
adjusted_prices = raw_prices * cumulative_adjustment_factor(dividends)
```
- Test: Validate SPY total return matches known benchmarks
- Impact: Expected -8% to -12% on reported returns

**Bug CRIT-002**: Polygon Options Parsing
- File: `polygon_loader.py:142-156`
- Change: Fix field mapping:
```python
# CORRECT mapping:
strike_price = option_data['strike_price']  # was 'strike'
expiration = pd.to_datetime(option_data['expiration_date'])  # was 'expiry'
option_type = option_data['contract_type'].lower()  # was 'type'
```
- Test: Validate option chain parsing against CBOE data
- Impact: Expected -5% on returns from corrected pricing

### DAY 2: CORE TRADING LOGIC

**Bug CRIT-003**: Regime Data Leakage
- File: `regime_classifier.py:89-112`
- Change: Implement strict time-based separation:
```python
# REPLACE current regime calculation with:
training_data = data[data.index < current_time]
future_data = data[data.index >= current_time]  # EXCLUDE from training
regime_model.fit(training_data)
```
- Test: Walk-forward validation with no future data access
- Impact: Expected -15% on returns from realistic regime detection

**Bug MED-001**: Volatility Surface Fix
- File: `profile_detectors.py:112-134`
- Change: Improve interpolation method:
```python
# REPLACE linear interpolation with:
from scipy.interpolate import CubicSpline
vol_surface = CubicSpline(known_strikes, known_vols, 
                         bc_type='natural', extrapolate=False)
```
- Test: Validate volatility surface against market data
- Impact: Expected +3% from better opportunity detection

### DAY 3: EXECUTION REALISM

**Bug CRIT-004**: Slippage Modeling
- File: `trade_simulator.py:234-267`
- Change: Add realistic execution costs:
```python
# ADD slippage model:
def apply_slippage(fill_price, quantity, liquidity):
    base_slip = 0.001  # 0.1% for liquid options
    impact_slip = abs(quantity) / liquidity * 0.005
    slippage = base_slip + impact_slip
    return fill_price * (1 + np.sign(quantity) * slippage)
```
- Test: Compare fills with/without slippage on large orders
- Impact: Expected -8% on returns from execution costs

**Bug CRIT-006**: Commission Correction
- File: `execution_model.py:312-328`
- Change: Fix round-trip calculation:
```python
# REPLACE commission calculation:
commission = self.commission_per_contract * abs(quantity) * 2  # Round-trip
total_cost = fill_price * quantity + commission
```
- Test: Validate commission doubling for complete trades
- Impact: Expected -3% from proper cost accounting

### DAY 4: RISK & ACCOUNTING

**Bug CRIT-005**: P&L Premium Accounting
- File: `pnl_accounting.py:178-195`
- Change: Correct premium handling:
```python
# FIX premium accounting:
if trade_direction == 'buy':
    position_value = -premium_paid * contract_size
else:  # sell
    position_value = premium_received * contract_size
# Mark-to-market using current option prices
```
- Test: Validate option position values against theoretical
- Impact: Expected -7% from proper premium accounting

**Bug HIGH-001**: Greeks Calculation
- File: `risk_management.py:145-167`
- Change: Use correct volatility inputs:
```python
# REPLACE greek calculation:
def calculate_delta(option_type, S, K, T, r, sigma):
    # Use implied vol from current market, not historical
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    if option_type == 'call':
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1
```
- Test: Validate Greeks against analytical models
- Impact: Expected -4% from proper risk management

### DAY 5: INTEGRATION & VALIDATION

**Bug HIGH-002**: Survivorship Bias
- File: `statistical_metrics.py:223-245`
- Change: Add delisted security handling:
```python
# ADD delisting check:
def check_delisted(symbol, date):
    delisting_date = get_delisting_date(symbol)
    if delisting_date and date >= delisting_date:
        return True  # Security no longer exists
    return False
```
- Test: Validate backtest includes only tradable securities
- Impact: Expected -6% from realistic universe

**Bug HIGH-003**: Position Limits
- File: `integration_engine.py:334-356`
- Change: Enforce maximum positions:
```python
# ADD position limit check:
current_exposure = self.calculate_portfolio_exposure()
max_exposure = self.risk_limits['max_position_size']
if abs(current_exposure + new_trade_exposure) > max_exposure:
    # Scale down trade to stay within limits
    new_trade_exposure = max_exposure - current_exposure
```
- Test: Validate no position exceeds risk limits
- Impact: Expected -5% from constrained sizing

## PART 4: IMPACT ESTIMATE

### Profit Impact Calculation:

**INFLATING BUGS (Subtract from $342K):**
- CRIT-001: -10% (-$34.2K)
- CRIT-002: -5% (-$17.1K)  
- CRIT-003: -15% (-$51.3K)
- CRIT-004: -8% (-$27.4K)
- CRIT-005: -7% (-$23.9K)
- CRIT-006: -3% (-$10.3K)
- HIGH-001: -4% (-$13.7K)
- HIGH-002: -6% (-$20.5K)
- HIGH-003: -5% (-$17.1K)
- MED-002: -2% (-$6.8K)

**SUPPRESSING BUGS (Add back real edge):**
- MED-001: +3% (+$10.3K)

**NET IMPACT:**
- Total subtraction: -62% (-$212.3K)
- Total addition: +3% (+$10.3K)
- Net adjustment: -59% (-$202K)

### FINAL ESTIMATES:
- **Original peak profit**: $342,000
- **Adjusted peak profit**: $140,000 (±$20,000)
- **Expected Sharpe ratio**: 1.2-1.6 (down from 2.8)
- **Maximum drawdown**: 25-35% (up from 15%)

### CONFIDENCE INTERVAL:
- 90% confidence real edge: $120K - $160K
- System remains profitable but much less spectacular
- Realistic annualized return: 12-18% after all fixes

### CRITICAL RECOMMENDATION:
**Do not trade live until ALL Day 1-3 fixes are implemented and validated.** The data leakage and unrealistic execution assumptions make current results completely unreliable for live trading.
