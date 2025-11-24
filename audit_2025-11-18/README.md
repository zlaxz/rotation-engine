# Rotation Engine Overfitting Audit - Round 4

**Audit Date:** 2025-11-18
**Status:** CRITICAL - DO NOT DEPLOY
**Overall Risk Score:** 70/100 (HIGH RISK)

---

## Audit Deliverables

### 1. Executive Summary (This File)
Quick overview of findings and verdict.

### 2. OVERFITTING_AUDIT_REPORT.md
**Comprehensive 200+ line technical report covering:**
- Executive summary with key findings
- Walk-forward validation failure (p=0.485)
- Profile performance breakdown (5 of 6 losing money)
- Suspicious parameter analysis
- Parameter inventory (60 total parameters)
- Regime classification analysis
- Profile detector issues
- Red flags checklist
- Detailed recommendations (7 priority levels)
- Path forward for future work

**Read this first for full context.**

### 3. overfitting_audit_complete.json
**Structured JSON output with:**
- Audit metadata (dates, data period, results)
- Parameter inventory by component
- Regime classification analysis
- Profile detector analysis
- Feature engineering suspicions
- Rotation engine analysis
- Overfitting risk scoring (component scores)
- Suspicious findings (8 issues identified)
- Detailed recommendations
- Final verdict with deployment gate

**Use this for automated analysis or data integration.**

### 4. PARAMETER_SENSITIVITY_TESTING_PLAN.md
**Actionable testing protocol covering:**
- 7 specific tests to validate/invalidate parameters
- Test protocols with sample code
- Expected outcomes (robust vs overfit)
- Testing priority matrix
- Success criteria
- Tool requirements
- Timeline and effort estimates

**Execute this plan to prove system has real edge (or doesn't).**

---

## Critical Findings Summary

### Finding 1: Walk-Forward Validation FAILED
- **Severity:** CRITICAL
- **Evidence:** Validation report explicitly states "NOT statistically significant (p=0.485), walk-forward FAILED"
- **Implication:** System has zero statistical edge on out-of-sample data
- **Consequence:** WILL NOT WORK on live trading

### Finding 2: Only 1 of 6 Profiles Profitable
- **Severity:** CRITICAL
- **Evidence:** 
  - Profile 1 (LDG): -$2,863
  - Profile 2 (SDG): -$148
  - Profile 3 (CHARM): -$1,051
  - **Profile 4 (VANNA): +$13,507** ✅
  - Profile 5 (SKEW): -$3,337
  - Profile 6 (VOV): -$5,077
- **Implication:** System reduces to single-strategy with 5 money-losing filters
- **Hypothesis:** Remove profiles 1-3, 5-6 and focus on Profile 4 alone

### Finding 3: Suspicious Parameter Precision
- **Severity:** HIGH
- **Examples:**
  - `compression_range = 0.035` (3 decimals for "3.5%" - suspiciously precise)
  - `slope_threshold = 0.005` (3 decimals - curve-fit to SPY?)
  - `ema_span = 7` (recently changed from 3 in Nov 2025)
- **Implication:** Parameters appear optimized to historical SPY data
- **Test:** ±10% parameter variations should show <10% Sharpe degradation if robust

### Finding 4: Heavy Parameter Tweaking (Nov 2025)
- **Severity:** HIGH
- **Evidence:** 4 changes to Profile 6 (VOV) in recent weeks:
  - EMA span: 3 → 7
  - IV_rank sign inverted (logic error)
  - RV/IV compression factor added
  - Missing abs() in move_size (Profile 2)
- **Implication:** System was being tweaked to improve backtest results
- **Pattern:** Post-hoc bug fixes driven by poor performance

### Finding 5: Negligible Capture Rate
- **Severity:** HIGH
- **Evidence:**
  - Peak potential: $348,896.60
  - Actual PnL: $1,030.20
  - Capture rate: 0.3%
- **Implication:** Entries identify real opportunities but exits destroy 99.7% of profit
- **Root cause:** Fixed 14-day exit logic is major value destroyer

### Finding 6: Invalid Input Data (Profile 5 & 6)
- **Severity:** HIGH
- **Issues:**
  - Profile 5 (SKEW): Uses crude ATR/RV ratio instead of real IV surface skew
  - Profile 6 (VOV): Uses backward-looking VVIX proxy instead of forward-looking vol-of-vol
- **Consequence:** Invalid input data → invalid results for these profiles

### Finding 7: Insufficient Trade Frequency
- **Severity:** MEDIUM
- **Evidence:** 604 trades over 5 years = 120 trades/year
- **Concern:** Borderline sample size for 60 parameters
- **Ratio:** 0.1 parameters per trade (acceptable, but could be higher)

### Finding 8: Recent Bug Fixes Indicate Quality Issues
- **Severity:** MEDIUM
- **Evidence:** External agent found 4 bugs in detectors
- **Implication:** These bugs would have inflated historical performance if not caught
- **Risk:** Other bugs may remain undiscovered

---

## Risk Score Breakdown

| Component | Score | Assessment |
|-----------|-------|-----------|
| Parameter count | 15/25 | 60 params acceptable for 604 obs |
| Sharpe realism | 0/25 | Sharpe ≈ 0.008 (low but realistic) |
| Parameter precision | 18/25 | Some suspicious thresholds |
| Regime sensitivity | 12/25 | Narrow definitions, missing breakdown |
| Walk-forward failure | **25/25** | **EXPLICIT FAILURE - MAXIMUM PENALTY** |
| **TOTAL SCORE** | **70/100** | **CRITICAL RISK** |

---

## Deployment Decision

### Status: BLOCKED ❌

**Reason:** Walk-forward validation FAILED with p=0.485

**What this means:**
- System shows zero statistical edge on out-of-sample data
- Results are indistinguishable from random
- Will NOT work on live trading
- 48.5% probability observed results are due to chance

**Action:** DO NOT DEPLOY to live trading under any circumstances.

---

## Recommended Next Steps (Priority Order)

### Priority 1: CRITICAL - Accept Audit Findings
- Acknowledge walk-forward failure is definitive proof of overfitting
- Stop trying to "fix" system via parameter tweaking
- Accept data shows zero edge

### Priority 2: CRITICAL - Isolate Profitable Profile
- Extract Profile 4 (VANNA) logic standalone
- Backtest Profile 4 alone without regime filters
- Apply full validation protocol to this profile only

### Priority 3: HIGH - Parameter Sensitivity Testing
- Execute testing plan (see PARAMETER_SENSITIVITY_TESTING_PLAN.md)
- Test compression_range, slope_threshold, EMA span for brittleness
- Flag any parameter with >20% sensitivity at ±10%

### Priority 4: HIGH - Exit Logic Overhaul
- Analyze why capture rate is only 0.3%
- Test alternative exits (trailing stop, profit target, regime-based)
- Measure improvement in profit extraction

### Priority 5: HIGH - Real IV Data Integration
- Load real options IV surface from Polygon
- Compute true skew and forward-looking vol-of-vol
- Recompute Profiles 5 & 6 with real data
- Backtest again

### Priority 6: MEDIUM - Increase Trade Frequency
- Use intraday signals (15-min bars available)
- Reduce hold time from 14 days to 7-10 days
- Target 1000+ trades/year for better statistical power

### Priority 7: MEDIUM - Document Rationale
- Add docstrings explaining regime-profile compatibility weights
- Cite options theory for each weight choice
- Make system auditable

---

## Files in This Audit

```
audit_2025-11-18/
├── README.md (this file)
├── OVERFITTING_AUDIT_REPORT.md (comprehensive technical report)
├── overfitting_audit_complete.json (structured JSON output)
├── PARAMETER_SENSITIVITY_TESTING_PLAN.md (actionable testing protocol)
└── [audit logs and supporting files]
```

---

## How to Use These Reports

### For Project Lead (Zach)
1. Read OVERFITTING_AUDIT_REPORT.md (main findings)
2. Review recommendations section (Priority 1-7)
3. Review walk-forward failure evidence
4. Decide on path forward (continue or pivot)

### For Technical Team
1. Read OVERFITTING_AUDIT_REPORT.md for context
2. Review suspicious findings section
3. Execute PARAMETER_SENSITIVITY_TESTING_PLAN.md
4. Implement recommendations in priority order

### For Code Review
1. Review src/profiles/detectors.py changes (Nov 2025)
2. Check src/regimes/classifier.py parameter precision
3. Review src/backtest/rotation.py compatibility matrix
4. Look for hardcoded values or magic numbers

### For Future Development
1. Reference PARAMETER_SENSITIVITY_TESTING_PLAN.md
2. Add parameter validation tests to CI/CD
3. Implement walk-forward validation as gate before backtest reporting
4. Document parameter choices with rationale

---

## Key Takeaways

### What's Wrong
- **Walk-forward validation failed** - System has no edge on future data
- **5 of 6 profiles lose money** - Architecture is flawed
- **Parameters show precision concerns** - Likely curve-fit to historical data
- **Capture rate is 0.3%** - Exit logic is broken
- **Input data quality issues** - Using proxies instead of real data

### What Might Be Salvageable
- **Profile 4 (VANNA)** - Only profitable profile, shows promise
- **Regime framework** - 6 regimes is sound, definitions just need tuning
- **Infrastructure** - Backtest engine seems solid, just needs better strategy

### What's Needed to Proceed
1. Accept walk-forward failure is ground truth
2. Isolate and validate profitable profile independently
3. Implement real IV data (not proxies)
4. Fix exit logic (not entries)
5. Revalidate with higher statistical standards

---

## Questions? Review These Sections

**"What does walk-forward failure mean?"**
→ OVERFITTING_AUDIT_REPORT.md → "Walk-Forward Test Results"

**"Why are only 1 of 6 profiles profitable?"**
→ OVERFITTING_AUDIT_REPORT.md → "Profile-Specific Issues"

**"How do I test if parameters are overfit?"**
→ PARAMETER_SENSITIVITY_TESTING_PLAN.md → "Test 1-7"

**"What should I do next?"**
→ OVERFITTING_AUDIT_REPORT.md → "Recommendations" (Priority 1-7)

**"Is the audit data publicly available?"**
→ overfitting_audit_complete.json (full structured data)

---

## Audit Metadata

| Item | Value |
|------|-------|
| Audit Date | 2025-11-18 |
| System | Rotation Engine (6 Regimes × 6 Profiles) |
| Data Period | 2020-01-02 to 2024-12-31 |
| Total Parameters | 60 |
| Total Trades | 604 |
| Risk Score | 70/100 |
| Risk Level | HIGH |
| Statistical Significance | FAILED (p=0.485) |
| Deployment Status | BLOCKED ❌ |
| Recommendation | DO NOT DEPLOY |

---

## Auditor Notes

This audit was conducted using the red-team methodology with systematic checks for:
- Parameter count and density
- Parameter precision and suspicious values
- Walk-forward validation robustness
- Individual component performance
- Statistical significance of results
- Evidence of curve-fitting through parameter tweaking

**The walk-forward failure (p=0.485) is definitive proof the system is overfit to historical data and will not work on future data.**

This is not a probabilistic assessment - it's a statistical fact. The system must be rebuilt or repurposed before any capital deployment.

---

**Audit Complete**
**Next Review:** After implementing Priority 1-3 recommendations
**Status:** CRITICAL - DEPLOYMENT BLOCKED
