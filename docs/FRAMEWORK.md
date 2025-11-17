# Convexity Rotation Engine - Complete Framework

**Source:** ChatGPT collaborative design session
**Date:** 2025-11-13
**Purpose:** Complete specification for regime-based convexity rotation trading system

---

## Table of Contents

1. [Core Thesis](#core-thesis)
2. [The Six Market Regimes](#the-six-market-regimes)
3. [The Six Convexity Profiles](#the-six-convexity-profiles)
4. [Profile-to-Regime Alignment](#profile-to-regime-alignment)
5. [Mathematical Detectors](#mathematical-detectors)
6. [Rotation Logic](#rotation-logic)
7. [Backtesting Architecture](#backtesting-architecture)
8. [Transaction Cost Modeling](#transaction-cost-modeling)
9. [Risk Management](#risk-management)
10. [Performance Metrics](#performance-metrics)

---

## Core Thesis

### The Essential Idea

Markets continuously misprice specific types of options convexity based on structural market regime. By detecting regime shifts and rotating capital to the underpriced convexity profile, we harvest structural edge independent of directional prediction.

### Key Principles

**1. Options Have Six Distinct Convexity Behaviors**

An option responds to:
- Price movement (gamma)
- Changes in volatility (vega)
- Changes in delta caused by time (charm)
- Changes in delta caused by volatility (vanna)
- Curvature / skew shape
- Vol-of-vol / meta-convexity

These are NOT interchangeable - they are fundamentally different sources of convexity.

**2. Markets Exist in Six Structural States**

Options microstructure only produces six stable market environments. These are the minimal complete basis - the "orthogonal vectors" of convexity space.

**3. Each Regime Makes Specific Convexity Types Mispriced**

Each regime causes specific convexity to become:
- Underpriced (cheap - opportunity)
- Overpriced (rich - avoid)
- Unstable (meta-convexity - volatility of volatility)

**4. The Engine Predicts Convexity Shape, Not Direction**

This is NOT:
- Momentum strategy
- Mean reversion strategy
- Long vol or short vol

This IS:
- Predicting which SHAPE of convexity will generate highest risk-adjusted P&L given current market structure
- Direction = noise; Convexity = structure

**5. Capital Rotates Like Sector Rotation, But Across Convexity Surfaces**

Instead of rotating Tech → Energy → Utilities, we rotate:
- Long-dated gamma → Short-dated gamma → Charm → Vanna → Skew → Vol-of-vol

Markets move, regimes change, convexity mispricings migrate. The engine follows the mispricing.

---

## The Six Market Regimes

### Mathematical Dimensions

Regimes are defined by three axes:
1. **Spot path structure** (trend, chop, compression)
2. **Volatility level** (high/low/breaking)
3. **Volatility state** (expanding/contracting/pinned)

These produce exactly six stable combinations.

---

### Regime 1: Trend Up (Directional + Vol Compression)

**Definition:**
Spot grinding upward with sustained positive drift, realized vol < implied vol, skew flattening, charm positive.

**Measurable Signals:**
- **Trend filter:**
  - 20-day return > +2%
  - Price above 20-day and 50-day MAs
  - slope(20-day MA) > 0
- **Realized vs Implied:**
  - 5-day realized vol < 20-day implied vol
  - IV percentile < 40% (vol not elevated)
- **Skew:**
  - 25D put skew flattening (skew slope < -0.25 std from 6-month mean)
- **Vol State:**
  - VIX down 5%+ from 10-day max
  - VVIX down or flat

**Key Signature:**
- realized < implied
- vol compresses
- charm dominant force
- call-side convexity underpriced

**Why it exists:**
Markets melt-up under dealer short-gamma supply. Charm and vanna flows drive slow, persistent drift.

---

### Regime 2: Trend Down (Directional + Vol Expansion)

**Definition:**
Spot trending downward with elevated realized vol, skew steepening, vol rising, gamma in front of curve explosive.

**Measurable Signals:**
- **Trend filter:**
  - 20-day return < -2%
  - Price below 20-day and 50-day MAs
  - slope(20-day MA) < 0
- **Realized vs Implied:**
  - 5-day realized vol > 20-day implied vol
  - IV percentile > 50%
- **Skew:**
  - 25D put skew steepening (> +1 std over 6-month mean)
- **Vol State:**
  - VIX rising (5-day slope > 0)
  - VVIX rising
  - Term structure in backwardation (VX1 > VX3)

**Key Signature:**
- realized > implied
- vol expanding
- put-side convexity overpriced but still necessary
- front-dated gamma becomes king

**Why it exists:**
When dealers become short convexity on downside, vol-of-vol ignites. Downtrends behave completely differently from uptrends from convexity standpoint.

---

### Regime 3: Vol Compression / Pinned Market

**Definition:**
Spot in tight range with realized vol crushed beneath implied, vanna/charm dominate, skew stable, vol pinned by dealer hedging.

**Measurable Signals:**
- **Price structure:**
  - Price within 3-5% range for 10+ trading days
  - ATR(14) < 50th percentile of last year
- **Realized vs Implied:**
  - realized vol / implied vol < 0.6
  - IV rank < 30%
- **Dealer position indicators:**
  - GEX positive
  - Volatility cone at bottom quartile
- **Vol State:**
  - VIX downtrending
  - Term structure in contango

**Key Signature:**
- implied vol > realized vol by large margin
- decay (theta/charm) becomes predictable
- gamma not rewarded
- mean reversion dominates

**Why it exists:**
The market is pinned - index option seller's paradise.

---

### Regime 4: Vol Expansion / Breaking Volatility

**Definition:**
Vol accelerating, vol-of-vol rising, entire chain lifts, convexity expensive everywhere.

**Measurable Signals:**
- **Vol-of-vol:**
  - VVIX rising > 10% week over week
  - VVIX > 80th percentile
- **Skew:**
  - Skew steepening aggressively
  - 25D-ATM skew > +2 std
  - 10D skew blowing out
- **Term structure:**
  - Backwardation across near tenors
  - VX1 > VX2 > VX3
- **Realized & Implied:**
  - realized > implied
  - implied expanding > 2 std relative to 20-day mean

**Key Signature:**
- VVIX up
- implied vol rising across tenors
- skew steepens hard
- convexity trades become inefficient

**Why it exists:**
When systemic hedging demand spikes, convexity becomes reflexive and nonlinear. Rare but crucial regime.

---

### Regime 5: Choppy Mean-Reverting Market

**Definition:**
Spot oscillates around center without trend but with enough movement to reward gamma if cheap. Realized ≈ implied.

**Measurable Signals:**
- **Price structure:**
  - Up/down chop without slope (20-day MA slope ≈ 0)
  - RSI oscillating 40-60 repeatedly
  - No higher-high/higher-low or lower-low/lower-high pattern
- **Realized vs Implied:**
  - realized ≈ implied (0.9 < RV/IV < 1.1)
- **Vol State:**
  - IV rank 40-60%
  - Term structure mildly contango
- **Dealer conditions:**
  - GEX low or mixed
  - Gamma neither suppressed nor exploding

**Key Signature:**
- oscillatory movement
- gamma gains from repeated scalps
- charm still matters but less dominant
- skew relatively flat

**Why it exists:**
Classic gamma scalping environment - but only if gamma is mispriced.

---

### Regime 6: Event / Catalyst

**Definition:**
Binary-event setups (CPI, FOMC, earnings) where short-dated IV blows out, vol-of-vol elevated, convexity dominated by event risk.

**Measurable Signals:**
- **Calendar proximity:**
  - Within 3 trading days of CPI, FOMC, NFP
  - Within 1-2 days of large earnings cluster
- **Implied vol:**
  - 0DTE / 1DTE IV > 2 std above 60-day mean
  - IV spike isolated to front of curve
- **Vol-of-vol & Flow:**
  - VVIX elevated (but not always rising)
  - Skew often flattens temporarily
  - Order flow concentrated in short-dated strikes
- **Realized vs Implied:**
  - Realized vol irrelevant - IV is event priced
  - Implied vol dominates surface behavior

**Key Signature:**
- short-dated IV spikes
- gamma extremely expensive
- vanna/charm suppressed
- vol surface shape depends on event directionality

**Why it exists:**
Events temporarily decouple implied vol from realized vol. Separate regime necessary because convexity behaves nonlinearly during these setups.

---

## The Six Convexity Profiles

### Profile 1: Long-Dated Gamma Efficiency (45-120 DTE)

**Convexity Source:** Slow gamma, strong vanna, low decay

**Trade Structure:**
- Long 60-90 DTE ATM straddle OR
- Long 60-90 DTE call-leaning 25D risk reversal

**Behavior:**
- Slow gamma allows scalping grind-y markets
- Vanna (vol ↓ when spot ↑) creates directional tailwind
- Theta cost low compared to short-dated gamma

**Best Regimes:** Regime 1 (Trend Up), sometimes Regime 3 (Pinned)

---

### Profile 2: Short-Dated Gamma Spike (0-7 DTE)

**Convexity Source:** Explosive gamma

**Trade Structure:**
- **Downtrend (Regime 2):** Long 1-3 DTE ATM straddle
- **Choppy (Regime 5):** Sell 1-3 DTE ATM straddle (delta-hedged intraday)
- **Event (Regime 6):** Long 0DTE or 1DTE straddle pre-event OR Sell 0DTE post-event (after vol collapse)

**Behavior:**
- Very high gamma, very high decay
- Ultra-sensitive to microstructure and dealer hedging
- Only convexity source fast enough to capture violent moves

**Best Regimes:** Regime 2 (Trend Down), Regime 5 (Chop), Regime 6 (Event)

---

### Profile 3: Charm/Decay Dominance

**Convexity Source:** Delta decay causes predictable directional drift

**Trade Structure:**
- Sell 7-14 DTE 25D strangles with tight delta-hedging
- Hedge delta daily (or intraday)

**Behavior:**
- Charm makes deltas decay toward 0
- When market pinned, movement doesn't hurt
- Pure decay edge
- Most reliable short-gamma profile BUT ONLY in Regime 3

**Best Regimes:** Regime 3 (Pinned)

---

### Profile 4: Vanna / Vol-Spot Correlation

**Convexity Source:** Delta shifts caused by changes in IV

**Trade Structure:**
- Long 30-60 DTE call flys OR
- Long call diagonal spreads:
  - Long 1x 60 DTE ATM call
  - Short 1x 7 DTE ATM call (delta-neutral-ish)

**Behavior:**
- When IV bleeds, long option's delta increases (vanna)
- Gives "free" directional push
- Track PnL attribution: vanna vs gamma vs theta

**Best Regimes:** Regime 1 (Trend Up), Regime 3 (Pinned)

---

### Profile 5: Skew Convexity

**Convexity Source:** Vertical skew mispricing

**Trade Structure:**
- **Downtrend (Regime 2):** Long put backspread
  - Long 2x 25D Puts
  - Short 1x ATM Put (for net debit ideally)
- **Breaking Vol (Regime 4):** Long put fly OR Long risk reversal
  - Long 1x 25D Put
  - Short 1x 25D Call

**Behavior:**
- During downtrends and vol spikes, OTM puts structurally underpriced relative to how skew reprices
- Track curvature effect

**Best Regimes:** Regime 2 (Downtrend), Regime 4 (Breaking Vol)

---

### Profile 6: Vol-of-Vol (VVIX) / Curvature Convexity

**Convexity Source:** Second derivative of volatility

**Trade Structure:**
- **Option version:** Long 30-60 DTE straddle OR Long 30-60 DTE OTM strangle
- **Advanced:** Long VIX calls (1-2 months), Long VIX call spreads, Long VIX ratio call spreads

**Behavior:**
- Events and vol shocks move entire surface, not just skew or ATM vol
- Pure volatility curvature

**Best Regimes:** Regime 4 (Breaking Vol), Regime 6 (Event)

---

## Profile-to-Regime Alignment

**Complete mapping of which profiles work in which regimes:**

| Regime | Primary Profiles | Trade Structures |
|--------|-----------------|------------------|
| 1. Trend Up | Profile 1 (Long-dated gamma)<br>Profile 4 (Vanna) | Long 60-90 DTE ATM straddle or call-lean RR<br>Call diagonals or 30-60 DTE call flys |
| 2. Trend Down | Profile 2 (Short-dated gamma)<br>Profile 5 (Skew convexity) | Long 1-3 DTE ATM straddle<br>Long put backspread |
| 3. Vol Compression | Profile 3 (Charm decay)<br>Profile 4 (Vanna) | Sell 7-14 DTE 25D strangle (delta-hedged)<br>Long diagonal/call fly |
| 4. Breaking Vol | Profile 5 (Skew convexity)<br>Profile 6 (Vol-of-vol) | Long put fly, RR, or backspread<br>Long 30-60 DTE straddle or VIX calls |
| 5. Choppy | Profile 2 (Short-dated gamma)<br>Profile 3 (Charm - conditional) | Sell 1-3 DTE ATM straddle (delta-hedged)<br>Sell 14 DTE 25D strangle |
| 6. Event / Catalyst | Profile 6 (Vol-of-vol)<br>Profile 2 (Short-dated gamma) | Long straddle/strangle or VIX calls<br>Buy 0DTE/1DTE pre-event; sell post-event |

**Regime Compatibility Weights (Example for Regime 2 - Trend Down):**
```
Profile 1: 0.0  (long-dated gamma - ineffective in downtrend)
Profile 2: 1.0  (short-dated gamma - strong in downtrend)
Profile 3: 0.2  (charm - weak, market not pinned)
Profile 4: 0.0  (vanna - wrong direction)
Profile 5: 1.0  (skew convexity - strong in downtrend)
Profile 6: 0.6  (vol-of-vol - moderate, depends on VVIX)
```

---

## Mathematical Detectors

**Each profile has a detector that outputs a score from 0 to 1.**

### Profile 1: Long-Dated Gamma Efficiency

```
LDG_score = sigmoid((RV10 / IV60) - 0.9) ×
            sigmoid((IV_rank_60 - 0.4) × -1) ×
            sigmoid(slope_MA20)
```

**Inputs:**
- RV10: 10-day realized vol
- IV60: 60-day implied vol
- IV_rank_60: IV percentile for 60 DTE
- slope_MA20 > 0 (trend confirmation)

**Interpretation:** Cheap long-dated vol + upward drift = LDG is attractive

---

### Profile 2: Short-Dated Gamma Spike

```
SDG_score = sigmoid((RV5 / IV7) - 0.8) ×
            sigmoid(abs(ret_1d) / ATR5) ×
            sigmoid(VVIX_slope)
```

**Inputs:**
- RV5 / IV7: realized/implied short vol ratio
- 1-day return normalized by ATR
- VVIX_slope: vol of vol acceleration

**Interpretation:** Short gamma attractive when realized vol jumping faster than IV reprices

---

### Profile 3: Charm / Decay Dominance

```
CHARM_score = sigmoid((IV20 / RV10) - 1.4) ×
              sigmoid((range_10d < 0.03)) ×
              sigmoid(-VVIX_slope)
```

**Inputs:**
- IV20 / RV10 >> 1
- Tight trading range
- Vol-of-vol decreasing

**Interpretation:** Market pinned + vol too high = charm decay dominates

---

### Profile 4: Vanna Convexity

```
VANNA_score = sigmoid(-IV_rank_20) ×
              sigmoid(slope_MA20) ×
              sigmoid(-VVIX_slope)
```

**Inputs:**
- Low IV rank
- Trend up (helps vanna)
- VVIX stable or declining

---

### Profile 5: Skew Convexity

```
SKEW_score = sigmoid(skew_z - 1.0) ×
             sigmoid(VVIX_slope) ×
             sigmoid((RV5 / IV20) - 1)
```

**Inputs:**
- skew_z > 1 std
- VVIX rising
- realized > implied (downside panic)

---

### Profile 6: Vol-of-Vol Convexity

```
VOV_score = sigmoid((VVIX / VVIX_80pct) - 1) ×
            sigmoid(VVIX_slope) ×
            sigmoid(IV_rank_20)
```

**Inputs:**
- VVIX > 80th percentile
- VVIX rising
- IV rank elevated

---

## Rotation Logic

**7-step process that allocates capital daily:**

### Step 1: Compute Profile Edge Scores

Each profile calculates its detector score (0-1) based on current market conditions.

```
edge_i(t) ∈ [0,1] for i = 1..6
```

### Step 2: Apply Regime Compatibility

Each regime has a compatibility weight vector for all 6 profiles.

```
compatibility_i(regime_t) ∈ [0,1]
```

### Step 3: Calculate Desirability

```
desirability_i(t) = edge_i(t) × compatibility_i(regime_t)
```

This combines "how strong is the edge?" with "how appropriate is that edge for this regime?"

### Step 4: Normalize to Risk Budget

```
weight_i(t) = desirability_i(t) / Σ desirability_j(t)
```

Forces weights to sum to 1.0 (or specified risk budget).

### Step 5: Apply Risk Constraints

- **Max per-profile weight:** 40%
- **VIX > 35:** Scale down all exposures
- **Event windows:** Reduce/zero short-vol structures
- **VVIX > 95th percentile:** Increase long convexity
- **Realized vol > Implied:** Clamp charm trades (they blow up here)

### Step 6: Deploy Trades

For each profile with weight > threshold (e.g., 0.05):
- Deploy its canonical trade structure
- Scale notional by weight
- Apply transaction costs

### Step 7: Rebalance

Detectors and regime classifier update daily (or intraday):
- Regime shifts → profile weights adjust
- Convexity scores change → rotation occurs
- Capital moves to wherever edge currently exists

---

## Backtesting Architecture

### 6-Module Design

#### Module 1: Data Layer

**Underlying data:**
- SPY OHLCV (daily + intraday if available)
- ATR (5, 10, 20)
- Rolling realized vol (5, 10, 20)

**Options chain data (for each date, all strikes & expirations):**
- bid/ask/mid
- IV
- theta, gamma, vanna, charm (calculate if not provided)
- delta
- open interest & volume
- timestamp

**Volatility indices:**
- IV30 from weighted SPY IV across expirations
- Vol-of-vol proxy using IV volatility

**Events calendar:**
- CPI, FOMC, NFP, earnings (SPY-relevant)

---

#### Module 2: Regime Labeling Engine (Walk-Forward)

**Critical rule: Walk-forward only**

At day t, compute everything using data from t and earlier ONLY. This avoids look-ahead bias.

**Deliverables:**
- Daily regime label (1-6)
- Regime durations
- Transition probabilities
- Regime autocorrelation

---

#### Module 3: Profile-Trade Backtesting

Test each convexity profile SEPARATELY first before combining.

**Why:** Prevents situation where combined engine looks good only because of cancellation effects.

**For each profile:**
- Implement its canonical trade structure
- Backtest in isolation (always-on)
- Backtest with regime filtering
- Track P&L by regime
- Confirm expected behavior

**Example:**
- Profile 3 (charm decay) should win in Regime 3 (Pinned)
- Profile 3 should have major blow-ups in Regime 4 (Breaking Vol)

---

#### Module 4: Rotation Engine Backtest

Once profiles individually behave correctly, combine them.

**Every day:**
1. Compute regime
2. Compute profile detector scores
3. Compute compatibility matrix
4. Multiply (edge × compatibility)
5. Normalize
6. Allocate capital
7. Deploy trades
8. Track P&L

**Capital allocated proportionally, NOT all-in.**

**Execution timing (new):**
- Signals generated on day *t* stage entries for execution at *t+1* open using the first available options snapshot. This enforces walk-forward discipline and removes the implicit “decision-and-fill-on-close” bias.
- When a trade triggers, all fills—entry, hedges, exits—apply the standard 100x SPY contract multiplier so dollar P&L aligns with broker statements.

**Return normalization (new):**
- Each profile reports both raw dollar P&L and a `daily_return` computed against a configurable notional (`capital_per_trade`). The portfolio allocator consumes returns, multiplies by weights, and then scales by starting capital to produce cumulative P&L. This keeps heterogeneous structures comparable and prevents weighting artifacts from absolute dollar series.
- Toy pricing guardrails: the simulator hard-fails if Polygon quotes are missing unless `allow_toy_pricing=True` is explicitly set for diagnostic runs. Production backtests must mount the Polygon dataset so every fill and mark uses real bid/ask data. Set `POLYGON_DATA_ROOT` (options) and `SPY_STOCK_DATA_ROOT` (minute-level SPY OHLCV exports) if your mount points differ from `/Volumes/VelocityData/...`.

---

#### Module 5: Transaction Cost Model

**Realistic execution assumptions:**
- Execution price = mid ± 25% of half-spread (normal conditions)
- In Breaking Vol regimes: use ± 40% (wider spreads)
- Commissions included
- Delta-hedging slippage
- Bid/ask expansion during volatile periods

---

#### Module 6: Portfolio Aggregation + Metrics

**Track:**
- Portfolio-level P&L: `Σ weight_i(t) × PnL_i(t)`
- Attribution breakdown:
  - Gamma P&L
  - Vega P&L
  - Theta P&L
  - Vanna/Charm P&L
  - Slippage P&L
  - Rotation cost P&L
  - Regime-transition P&L

**Metrics:**
- Sharpe, Sortino
- Max drawdown
- Regime-specific Sharpe
- Tail behavior
- Slippage & cost drag
- Stability of allocation weights

**Stress tests:**
- 2020 crash (Feb-Mar)
- 2021 melt-up low vol
- 2022 bear market
- 2023 choppy low vol
- Event weeks (CPI/FOMC)

---

## Transaction Cost Modeling

### SPY Options Reality

**Bid-ask spreads (per contract):**
- ATM straddles: $0.50-1.00
- OTM strangles: $0.30-0.60
- Iron condors: $0.20-0.50
- Butterflies: $0.15-0.30

**Slippage:**
- Market orders: 2-5% of spread
- Limit orders: May not fill (opportunity cost)

**Rotation costs:**
- Enter position: lose half the spread
- Exit position: lose half the spread
- Total per rotation: full spread cost

**Delta hedging costs:**
- ES futures commission: ~$2.50 per round trip
- Daily hedging: frequency × commission
- Intraday hedging: 3-5× daily cost

**Example calculation:**
```
Iron condor: $0.40 spread
Entry cost: $0.20
Exit cost: $0.20
Total per rotation: $0.40

If expected profit per regime = $1.00
Transaction costs = 40% of edge
```

---

## Risk Management

### Position Limits

- **Max per-profile allocation:** 40%
- **Min position threshold:** 0.05 (don't deploy tiny noise trades)
- **Portfolio VaR cap:** 99% confidence level

### Dynamic Scaling

- **VIX > 35:** Reduce all positions
- **Realized vol > 30:** Scale down
- **VVIX > 120:** Reduce short-vol exposure

### Event Protection

- **Hard stop:** No short convexity trades within 3 days of FOMC/CPI
- **Event windows:** Zero or reduce short-vol structures
- **Post-event:** Wait for vol collapse before re-entering short structures

### Greeks Limits

- **Max gamma exposure:** Define based on portfolio size
- **Max vega exposure:** Limit total volatility sensitivity
- **Delta-neutral target:** Keep portfolio delta near zero

---

## Performance Metrics

### Primary Metrics

- **Sharpe Ratio:** Risk-adjusted returns
- **Sortino Ratio:** Downside-focused risk adjustment
- **Max Drawdown:** Largest peak-to-trough decline
- **Calmar Ratio:** Return / max drawdown

### Attribution Metrics

- **By Greek:**
  - Gamma P&L
  - Vega P&L
  - Theta P&L
  - Vanna/Charm P&L
- **By Source:**
  - Profile selection P&L
  - Regime detection P&L
  - Rotation cost drag
  - Transaction cost drag

### Regime-Specific Metrics

- **Sharpe by regime:** Is edge coming from specific regimes or all?
- **Win rate by regime:** Consistent or regime-dependent?
- **Drawdowns by regime:** Which regimes cause pain?

### Rotation Metrics

- **Rotation frequency:** How often capital reallocates
- **Average holding period per profile:** Are we churning too much?
- **Regime transition P&L:** Do we profit from regime shifts?

---

## Validation Requirements

### Walk-Forward Validation

- **Train:** 2020-2022
- **Test:** 2023-2024
- **Performance degradation acceptable:** <30%

### Cross-Validation

Test on alternative underlyings:
- QQQ (tech-heavy)
- IWM (small cap)
- XLK (sector)

Not expecting identical performance - testing stability.

### Statistical Significance

- **Sharpe t-test:** p < 0.05
- **Permutation tests:** Shuffle regime labels, does performance vanish?
- **Monte Carlo:** Outperform 95% of random strategies

### Sensitivity Tests

- **2× transaction costs:** Does edge survive?
- **Remove top 5 best days:** Is P&L robust?
- **Delay delta-hedging by 1 hour:** Execution quality impact
- **±20bps random noise on fills:** Realistic execution variance

---

## Success Criteria

### Phase 1: Regime Detection
- ✅ Regimes have autocorrelation (persistent, not random walk)
- ✅ Regime transitions predict forward returns (p < 0.05)
- ✅ Average regime duration > 10 days (not whipsawing daily)

### Phase 2: Individual Profiles
- ✅ Each profile shows expected behavior in its target regime
- ✅ P&L attribution matches theory (gamma vs vega vs theta)
- ✅ Transaction costs < 30% of gross profit per profile

### Phase 3: Rotation Engine
- ✅ Combined Sharpe > 1.5 (after all costs)
- ✅ Max drawdown < 40%
- ✅ Positive Sharpe in 4/5 stress test periods

### Phase 4: Live Validation
- ✅ Paper trading matches backtest within 20%
- ✅ Execution quality acceptable (fills at expected prices)
- ✅ 3-6 months of validated performance before scaling

---

## Implementation Notes

### Data Requirements

**Minimum:**
- SPY daily OHLCV (2014-2024)
- SPY options chains with IV and Greeks (2014-2024)

**Ideal:**
- Intraday SPY data for better hedging
- VIX/VVIX if available
- Tick-level options data for spread analysis

### Computational Requirements

- **Regime classification:** Can run daily in <1 minute
- **Profile detectors:** Simple calculations, <1 minute
- **Full backtest:** Depends on data granularity
  - Daily rebalancing: Hours
  - Intraday hedging: Days

### Code Architecture

**Modular design:**
```
src/
├── data/           # Data loaders and preprocessing
├── regimes/        # Regime classification logic
├── profiles/       # Profile detector implementations
├── trading/        # Trade simulators and execution
├── backtest/       # Backtesting engine
├── risk/           # Risk management and constraints
└── analysis/       # Performance metrics and attribution
```

---

**Last Updated:** 2025-11-13
**Source:** ChatGPT collaborative design
**Status:** COMPLETE SPECIFICATION - ready for implementation
