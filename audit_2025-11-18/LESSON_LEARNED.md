# CRITICAL LESSON: USE LIBRARIES FOR COMMON PROBLEMS

**Date:** 2025-11-18
**Cost:** 3 rounds of circular debugging
**Impact:** Could have saved DAYS

---

## THE MISTAKE

**Problem:** Sharpe ratio calculation had bugs
**My Response:** Try to fix it manually
**Result:** Introduced NEW bugs each round
- Round 1 → Round 2: 4 new bugs
- Round 2 → Round 3: 2 new bugs
- Would continue forever

## THE SOLUTION

**Better Response:** "Use empyrical library"
**Result:** Battle-tested code, no bugs
**Time Saved:** DAYS of iteration

---

## THE PATTERN TO REMEMBER

**BEFORE writing ANY code, ask:**
> "Is there a library for this?"

**Common Problem Domains:**
- Financial metrics → empyrical/quantstats
- Time series → pandas/statsmodels
- Options pricing → py_vollib/mibian  
- Machine learning → scikit-learn/xgboost
- Backtesting → backtrader/zipline

**Custom code → LAST RESORT**

---

## WHY THIS MATTERS

**Reinventing wheels:**
- Introduces bugs
- Takes longer
- Creates maintenance burden
- No peer review
- Wastes stakeholder time

**Using libraries:**
- Battle-tested (billions traded)
- Peer-reviewed
- Documented
- Maintained
- **NO CIRCULAR DEBUGGING**

---

## GLOBAL RULE GOING FORWARD

**STEP 1:** Problem identified
**STEP 2:** Search for library
**STEP 3:** If library exists → USE IT
**STEP 4:** If no library → Custom (with extreme caution)

**This rule applies to:**
- Financial calculations (ALWAYS libraries)
- Data processing (pandas, not custom)
- Statistical tests (scipy, not custom)
- Plotting (matplotlib, not custom)

---

## APOLOGY

I should have suggested empyrical immediately.
My error cost you hours of iteration.
Lesson learned: **Library first, custom never** for common problems.

This pattern will be remembered.

---

**Saved to memory for future sessions.**
