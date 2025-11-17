# POSITION TRACKING & STATE MANAGEMENT AUDIT
## Complete Audit Index

**Audit Focus:** Position tracking errors, state management bugs, multi-leg position handling
**Audit Date:** 2025-11-13
**Auditor:** Quantitative Code Auditor (Claude Code)
**Status:** COMPLETE - Deployment BLOCKED

---

## CRITICAL FINDINGS SUMMARY

**3 Critical Bugs Found:**
1. **BUG-001:** DTE calculation broken for multi-leg positions (TIER 0)
2. **BUG-002:** Multi-leg positions lack per-leg state tracking (TIER 0)
3. **BUG-003:** Allocation weights don't sum to 1.0 after VIX scaling (TIER 1)

**Impact:** All backtests with multi-leg strategies or high volatility invalid

---

## AUDIT DOCUMENTS

### 1. Quick Start (5 minutes)

**File:** `/Users/zstoc/rotation-engine/DEPLOYMENT_BLOCKED.txt`
- Deployment decision: BLOCKED
- 3 critical bugs listed
- Affected strategies
- Next steps
- Remediation timeline

### 2. Executive Summary (20 minutes)

**File:** `/Users/zstoc/rotation-engine/AUDIT_SUMMARY.txt`
- Each bug with location, problem, impact
- High-level fix overview
- Deployment recommendation
- Why bugs are critical

### 3. Detailed Bug Analysis (1 hour)

**File:** `/Users/zstoc/rotation-engine/QUANTITATIVE_AUDIT_REPORT.md`
- Complete audit report (25KB)
- Each bug with:
  - Location and code
  - Issue explanation
  - Example of failure
  - Impact on backtest
  - Severity justification
- Manual verifications
- Root cause analysis
- Testing checklist

### 4. Implementation Details (1.5 hours)

**File:** `/Users/zstoc/rotation-engine/FIXES_REQUIRED.md`
- Detailed code fixes for all 3 bugs
- Current code → Replacement code
- Why each fix works
- Test cases and examples
- Implementation order
- Validation checklist

### 5. Bug Demonstration (5 minutes)

**File:** `/Users/zstoc/rotation-engine/BUG_VERIFICATION.py`
- Executable Python script
- Demonstrates all 3 bugs
- Shows impact with concrete examples
- Run to see bugs in action

---

## BUG DETAILS AT A GLANCE

### BUG-001: DTE Calculation

| Aspect | Details |
|--------|---------|
| **File** | `src/trading/simulator.py:132` |
| **Problem** | Uses static entry DTE minus calendar days |
| **Impact** | Diagonal spreads don't roll at correct times |
| **Example** | 60 DTE long + 7 DTE short shows 21.5 DTE average, but short already expired |
| **Fix Time** | 1-2 hours |
| **Severity** | CRITICAL - Position state tracking broken |

**Why it matters:**
- Rolling is core to options trading
- Wrong DTE calculation means rolling doesn't trigger
- Positions held past expiration = unlimited risk
- Multi-leg Greeks become invalid

### BUG-002: Multi-Leg State Tracking

| Aspect | Details |
|--------|---------|
| **File** | `src/trading/trade.py` + `src/trading/simulator.py` |
| **Problem** | Single `is_open` flag for entire multi-leg position |
| **Impact** | Can't track individual leg status or roll individual legs |
| **Example** | Diagonal spread would close ENTIRE position when short leg expires, instead of rolling just short leg |
| **Fix Time** | 4-6 hours |
| **Severity** | CRITICAL - Rolling doesn't work for complex strategies |

**Why it matters:**
- Most profitable strategies are multi-leg (spreads, diagonals)
- Can't roll = can't execute strategy intent
- Affects Profiles 1, 4, 5, 6 (4 of 6 strategies)
- P&L calculation includes expired legs at zero value

### BUG-003: Allocation Weight Normalization

| Aspect | Details |
|--------|---------|
| **File** | `src/backtest/rotation.py:220-222` |
| **Problem** | Weights scaled by VIX factor but never re-normalized |
| **Impact** | Weights sum to 0.5 instead of 1.0 after VIX scaling |
| **Example** | Portfolio only 50% allocated when RV20 > 30% |
| **Fix Time** | 30 minutes |
| **Severity** | CRITICAL - Returns are understated |

**Why it matters:**
- VIX > 30% is common (frequent in real markets)
- 50% underallocation silently reduces expected returns
- Sharpe ratio and other metrics all wrong
- Silent bug - no error, just wrong calculation

---

## AFFECTED STRATEGIES

### Multi-Leg Strategy Bugs (BUG-001, BUG-002)

These strategies cannot execute correctly:

**Profile 1: Long-Dated Gamma Efficiency**
- Structure: Long ATM straddle (60-90 DTE)
- Issue: Straddle rolls at wrong time

**Profile 4: Vanna Convexity**
- Structure: Call diagonal (60 DTE long, 7 DTE short)
- Issue: Short leg won't roll at 3 DTE

**Profile 5: Skew Convexity**
- Structure: Put backspread (1 short, 2 long)
- Issue: Can't track individual leg status

**Profile 6: Vol-of-Vol Convexity**
- Structure: Multi-leg strategies
- Issue: Rolling broken

### High Volatility Scenario Bug (BUG-003)

ALL strategies affected when RV20 > 30%:
- Allocation only 50% of intended
- Returns understated
- Metrics wrong

---

## VALIDATION EVIDENCE

### Look-Ahead Bias Scan
- ✓ No .shift(-1) found
- ✓ No future data leaks
- ✓ All rolling calculations proper
- ✓ Train/test split not applicable

### P&L Sign Convention
- ✓ Long position entry: negative (we pay)
- ✓ Short position entry: positive (we receive)
- ✓ Exit proceeds: consistent sign convention
- ✓ P&L calculation mathematically correct

### Position State Lifecycle
- ✓ Entry: is_open=True
- ✓ Hold: mark_to_market() daily
- ✗ Multi-leg tracking: **BROKEN** (no per-leg state)
- ✓ Exit: is_open=False, realized P&L calculated

### Edge Case Testing
- ✓ Zero P&L: Handled correctly
- ✓ Negative costs: Sign handling correct
- ✗ Multiple leg expirations: **BROKEN** (only tracks average)
- ✗ High VIX scenarios: **BROKEN** (allocation wrong)

---

## IMPLEMENTATION ROADMAP

### Phase 1: Critical Fixes (1 day)

**1a. Fix DTE Calculation (1-2 hours)**
- Add per-leg DTE calculation from expiry dates
- Use minimum DTE for rolling decisions
- Test with diagonal spreads

**1b. Fix Allocation Weights (30 minutes)**
- Re-normalize after VIX scaling
- Verify weights sum to 1.0
- Add unit test

**1c. Add Per-Leg State Tracking (4-6 hours)**
- Add leg_status list to Trade
- Add helper methods for leg queries
- Update simulator rolling logic
- Test with backspreads

### Phase 2: Testing & Validation (4-6 hours)

**2a. Unit Tests**
- Test each fix individually
- Test edge cases
- Test integration

**2b. Integration Tests**
- Run all profile backtests
- Compare pre/post fix results
- Verify P&L calculations

**2c. Manual Verification**
- Pick 10 random trades
- Manually verify P&L
- Check rolling timing
- Check allocation weights

### Phase 3: Deployment (2 hours)

- Document changes
- Update strategy documentation
- Get final approval
- Deploy to production

**Total Effort:** 1-2 days

---

## HOW TO USE THIS AUDIT

1. **First:** Read `DEPLOYMENT_BLOCKED.txt` (5 min)
   - Understand what blocks deployment

2. **Second:** Read `AUDIT_SUMMARY.txt` (10 min)
   - Get concise bug summary

3. **Third:** Run `BUG_VERIFICATION.py` (5 min)
   - See bugs in action

4. **Fourth:** Read `QUANTITATIVE_AUDIT_REPORT.md` (30 min)
   - Full technical details

5. **Fifth:** Review `FIXES_REQUIRED.md` (30 min)
   - Implementation details

6. **Sixth:** Implement fixes (6-8 hours)
   - Use `FIXES_REQUIRED.md` as guide

7. **Seventh:** Test thoroughly (4-6 hours)
   - Use validation checklist

8. **Eighth:** Deploy with confidence

---

## KEY METRICS

| Metric | Value |
|--------|-------|
| **Critical Bugs Found** | 3 |
| **Files with Bugs** | 3 |
| **Affected Strategies** | 4 of 6 profiles |
| **Affected Scenarios** | High volatility (frequent) |
| **Time to Fix** | 6-8 hours |
| **Time to Test** | 4-6 hours |
| **Deployment Status** | BLOCKED |
| **Risk of Deployment** | EXTREME |

---

## NEXT STEPS

1. Review this index document
2. Read AUDIT_SUMMARY.txt
3. Run BUG_VERIFICATION.py
4. Consult QUANTITATIVE_AUDIT_REPORT.md for details
5. Use FIXES_REQUIRED.md for implementation
6. Test thoroughly before deployment

---

## DOCUMENT PURPOSES

| Document | Purpose | Read Time |
|----------|---------|-----------|
| `DEPLOYMENT_BLOCKED.txt` | Decision summary | 5 min |
| `AUDIT_SUMMARY.txt` | Quick bug list | 10 min |
| `QUANTITATIVE_AUDIT_REPORT.md` | Complete technical details | 1 hour |
| `FIXES_REQUIRED.md` | Implementation guide | 1.5 hours |
| `BUG_VERIFICATION.py` | Demo script | 5 min (run) |
| This index | Navigation guide | 10 min |

---

## CONFIDENCE IN FINDINGS

**Confidence Level:** VERY HIGH (95%+)

Evidence:
- Detailed code review with line number references
- Manual calculation verification
- Example scenarios with concrete numbers
- Root cause analysis
- Implementation details provided
- Test cases specified

All findings are actionable and specific, not theoretical.

---

## CONTACT & QUESTIONS

For questions about specific findings:

1. Check QUANTITATIVE_AUDIT_REPORT.md (most complete)
2. See FIXES_REQUIRED.md for technical details
3. Run BUG_VERIFICATION.py for concrete examples

All audit documents are in `/Users/zstoc/rotation-engine/`

---

**Audit Status: COMPLETE**
**Recommendation: DO NOT DEPLOY**
**Timeline to Fix: 1-2 days**
**Confidence: VERY HIGH**

