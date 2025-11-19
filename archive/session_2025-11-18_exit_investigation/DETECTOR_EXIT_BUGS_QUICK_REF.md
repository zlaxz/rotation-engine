# DETECTOR EXIT BUGS - QUICK REFERENCE
**CRITICAL - DO NOT TEST UNTIL FIXED**

## 3 CRITICAL BUGS (System Breaking)

### CRITICAL-001: Feature Mismatch
**Location**: exit_engine_v1.py:324-349
**Problem**: market_conditions dict missing required features (vix_close, high, low, return)
**Impact**: Detector score = None for 100% of trades, all exits fall back to time stop
**Fix**: Pre-compute detector scores in regime step, pass as feature

### CRITICAL-002: Silent Failures
**Location**: exit_engine_v1.py:186-198, 210-218, etc.
**Problem**: None detector score silently falls back, no logging
**Impact**: User thinks detector exits work, actually using fallback logic
**Fix**: Add logging when score is None after warmup

### CRITICAL-003: Missing Historical Context
**Location**: exit_engine_v1.py:325
**Problem**: Single-row DataFrame, rolling windows fail
**Impact**: IV_rank, VVIX calculations broken
**Fix**: Pre-compute scores upstream with full context

## 2 HIGH BUGS (Wrong Logic)

### HIGH-001: Threshold Too High
**Location**: exit_engine_v1.py:62
**Problem**: 0.30 threshold may be too low (exits too late)
**Impact**: Gives back profits, worse capture %
**Fix**: Test thresholds 0.20-0.40, find optimal

### HIGH-002: days_held Guards
**Location**: Lines 182, 207, 227, 249, 271, 291
**Problem**: 1-2 day minimum hold prevents quick exits
**Impact**: Miss optimal exits for fast profiles (SDG, SKEW)
**Fix**: Remove guards for fast profiles, test impact

## FIX SEQUENCE

1. Pre-compute detector scores in regime classifier (fixes CRITICAL 1-3)
2. Add logging for None scores (visibility)
3. Test detector exits actually trigger (smoke test)
4. Optimize threshold (0.20-0.40 range)
5. Test with/without days_held guards

## ESTIMATED FIX TIME: 4-7 hours

**DO NOT BACKTEST until CRITICAL bugs fixed - results will be invalid**
