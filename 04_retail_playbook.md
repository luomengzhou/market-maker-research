# Retail Playbook — What to Borrow from Market-Maker / Dealer-Flow Mechanics

*Phase 3 deliverable. Built on the [theory primer](01_theory_primer.md) and the empirical results in [backtest_results.md](backtest_results.md) and [backtest_results_dix.md](backtest_results_dix.md). Read those first for the why; this file is the so-what.*

---

## TL;DR — three rules that survived the data

1. **Tilt SPY exposure based on dealer GEX regime.** Long when daily GEX > 0; flat when GEX < 0. Almost matches SPY's risk-adjusted return (OOS Sharpe 0.82 vs 0.90) while cutting max drawdown from -34% to -22%. ~14 trades per year. **This is the highest-quality finding.**
2. **Stop fading aggregate retail.** The "MMs fade retail" meme is empirically wrong at the SPY index level. High-DIX (high retail buying) days predict *positive* forward returns at every horizon, with t-stats up to 10. The contrarian alpha lives in *single-name attention extremes*, not aggregate index flow.
3. **Don't try to outrun MMs intraday.** The Dim/Eraker/Vilkov intraday gamma-reflexivity result does *not* survive translation to daily-frequency trading. Without intraday option-chain access (Polygon/CBOE DataShop) you can't directly trade their finding, and the naive daily proxies lose money cleanly.

The rest of this document is the operational layer: position sizing, order types, when to override, what to skip.

---

## What's actionable, in priority order

### Rule #1 — Defensive GEX tilt on SPY core position

**Setup:**
- Pull daily GEX from SqueezeMetrics free CSV: [https://squeezemetrics.com/monitor/static/DIX.csv](https://squeezemetrics.com/monitor/static/DIX.csv)
- Updated each evening after market close. The signal is for the *next* day.

**Rule:**
- If GEX(today) > 0 → hold full SPY position tomorrow
- If GEX(today) ≤ 0 → reduce to 0% SPY (cash or short-duration Treasuries) tomorrow
- If GEX flips back positive → re-enter at next-day open

**Implementation in IBKR/Schwab/Fidelity retail:**
- SPY shares (not options) for the core
- Limit-order entries near the prior close to avoid spread drag — daily SPY spread is ~1bp on liquid hours
- Approximately **14 round-trips per year** based on backtest. Costs on $50k position: ~$0 commission (free at most retail brokers) + ~$7 spread/year. Negligible.

**Sizing:**
- This rule operates on the timing of full-equity exposure. It does *not* increase risk vs buy-and-hold. Use whatever your normal SPY allocation is.
- Don't lever it up. The "stepping aside" gain is path quality, not extra return — adding leverage destroys the path-quality benefit.

**Expected behavior:**
- ~91% of days you're long SPY (calm-regime days)
- ~9% of days you're flat (negative-GEX stress days)
- **Most of the win is concentrated in 1-2 episodes per decade** (March 2020 was the dominant example in our 15-year sample). In any given year, the strategy may underperform SPY by a few percent. **You only see the value in tail events.**
- ⚠️ This is a feature, not a bug. The same caveat applies to any defensive overlay: pension-fund endowments accept it; short-horizon retail traders often don't.

**When to override the rule:**
- If you're already net-defensive for other reasons (e.g., you've raised cash for a planned house purchase), don't double up.
- If the GEX print is borderline (-0.5 to +0.5 std dev around the rolling 1-yr mean), the noise dominates the signal; sit on hands.
- Don't use this rule near major positioning events (earnings season for retail-heavy single names, FOMC) on individual stocks — it's calibrated for SPY only.

---

### Rule #2 — Stop fading aggregate retail; do fade *individual-name attention extremes*

**Why aggregate retail isn't dumb (Phase 2.2 finding):**
- DIX quintile sort: high-DIX days have *higher* forward 20-day returns than low-DIX days, monotonically.
- t-stat on the spread is 8-10. This is a real effect, not noise.
- Mechanism: aggregate retail buying tracks risk-appetite improvement, which is itself predictive of equity returns.

**Where the contrarian alpha lives (from theory, not yet tested in this project):**
- Single-name attention extremes (Barber & Odean 2008): a stock that's #1 on r/wallstreetbets, has 10× normal volume, and is +50% over 5 days is statistically a forward fade for 1-3 weeks.
- This is **not** the same signal as DIX. DIX is broad-index retail positioning (mildly bullish-predictive). Attention-driven single-name buying is concentrated, parabolic, and contrarian-predictive.

**Operational version:**
- Maintain a watchlist of stocks at attention extremes (e.g., Reddit "ticker mentions today / 30-day average" > 5×).
- For each, **avoid being long**, and consider small short-volatility positions (covered calls, cash-secured puts) to monetize the elevated implied vol that attention-stocks always carry.
- Position sizing: ≤ 2% of NAV per name. Attention-driven moves can extend much further than fundamentals justify (GME 2021).

**Why we didn't backtest this in this project:**
- Free Reddit Pushshift archive is offline since 2023; getting clean historical r/wsb mention data costs effort.
- StockTwits API only returns the most recent 30 messages per ticker — fine for live monitoring, useless for backtest.
- This rule is therefore "supported by literature, not yet by our own backtest." Phase 2.3 (optional) would test it.

---

### Rule #3 — Avoid the 0DTE / opex-Friday playground

**What's real:**
- Option dealers do hedge their books, and that hedging does cause measurable price effects (Ni/Pearson/Poteshman 2005, Dim/Eraker/Vilkov 2024).
- 0DTE options on SPX have grown to ~50% of total SPX volume; their gamma can move SPX measurably during the day.
- These effects are **intraday and require institutional-quality data** to trade.

**What this means for retail:**
- ✋ Don't trade 0DTE options based on GEX/dealer-positioning intuitions. The data lag and execution slippage between retail and the actual MM book is ~minutes — by the time you act, the MM has already re-hedged.
- ✋ Don't try to "front-run dealer hedging" on opex Friday. Pin levels are well-known (every options-flow service publishes the strike with maximum gamma); they're priced in by Tuesday.
- ✓ Do *avoid* trading directional options on opex Friday morning — bid/ask widens and the path is dominated by mechanical flows you can't anticipate. Wait for Friday afternoon if you must trade.
- ✓ Do *factor in* the asymmetry: for retail covered-call writers, opex Friday is your friend (charm decay accelerates). For retail call buyers, it's your enemy.

---

### Rule #4 — Don't trade based on dark-pool / off-exchange flow services

**Why:**
- FINRA ATS data is **2-4 weeks lagged**. Anything based on it is not actionable in real-time.
- "Unusual whales" / dark-pool-tape services *infer* retail vs institutional flow from price-improvement patterns; the inference accuracy is unverified.
- Even if you could see real-time wholesaler internalizer flow (you can't — it's bilateral), the half-life of that information at the price level is tens of seconds. Too fast for retail.

**The exception:** weekly off-exchange % can flag durable institutional accumulation in single names (FINRA tier-1 names). This is slow, fundamental-aligned, and doesn't require fast execution. A possible Phase 2.4 follow-up — but it's not where the alpha is.

---

## Position-sizing framework

Combining Rule #1 with normal asset allocation:

```
target SPY exposure = base_alloc × gex_tilt × earnings_screen × moves_screen
where:
  base_alloc       = your normal SPY weight (e.g., 60% of NAV in core)
  gex_tilt         = 1.0 if GEX(yesterday) > 0 else 0.0
  earnings_screen  = 0.7 if SPY-component-weight earnings cluster this week else 1.0
  moves_screen     = 0.5 if SPY moved >3% yesterday else 1.0   (bridge through chaos)
```

Treat the Rule #1 GEX gate as the dominant defensive lever. Earnings and big-move screens are second-order overlays you can apply if you want even tighter risk control — they're not from this project's backtests, but they're standard sleep-better-at-night additions that don't conflict with the GEX rule.

**Half-Kelly sanity check:** the GEX defensive-tilt OOS Sharpe is 0.82 with vol matched to SPY (~15%). Half-Kelly suggests max leverage = 0.5 × 0.82 / 0.15 ≈ 2.7x. **Don't actually lever it 2.7x** — the strategy's Sharpe is dominated by avoiding 1-2 tail events per decade, and Kelly assumes IID returns. Stay at 1x or below.

---

## Honest limitations of this playbook

1. **Vendor risk on GEX**: SqueezeMetrics is a single source. If they change methodology or shut down their free CSV, the rule breaks. Mitigation: clone `jensolson/SPX-Gamma-Exposure` and run an independent calculation as a sanity check.
2. **Regime risk**: the 15-year backtest covers QE, COVID, inflation, and AI-bubble. It does *not* cover a stagflation/secular-bear backdrop. The "negative GEX → step aside" rule may underperform in slow grinding bears where there's no acute negative-GEX cluster.
3. **Path-improvement, not alpha**: at the level of full-sample Sharpe, the GEX rule slightly *underperforms* SPY (0.85 vs 0.83 — within noise). The actionable improvement is in *drawdown experience*, which has psychological value. If you'd hold SPY through any drawdown without flinching, the rule offers nothing beyond reduced market beta in stress periods.
4. **Single-asset (SPY)**: nothing here has been tested on QQQ, IWM, EFA, EEM, or single names. Same data source applies (SqueezeMetrics tracks both SPX and individual SPY components in their paid product) but our backtest is SPX-specific.
5. **The DIX-based "retail isn't dumb at index level" finding doesn't translate to single names.** Don't assume r/wsb crowd buying NVDA is mildly informed because aggregate retail is mildly informed. Different mechanism.

---

## Things to *stop* doing if you've been doing them

- ❌ Following "unusual options flow" as a retail directional signal — most of it is hedging or vol-trading flow, not directional bets, and the noise-to-signal is brutal.
- ❌ Buying weekly OTM SPY/QQQ calls because "GEX is negative and dealers will be forced to buy" — by the time the data is in your hands the move is already in. Same for "vanna rallies post-FOMC."
- ❌ Using "max-pain" or "call-wall" levels as price targets without context — they are real but already priced into the spot.
- ❌ Trading 0DTE on retail platforms with intent to exploit dealer flow — see Rule #3.
- ❌ Subscribing to dark-pool tracking services for $300+/mo — the lag and inference accuracy don't justify the spend for retail.

---

## What we did NOT test (next-step menu)

If/when you want more depth, these are the natural follow-ups:

| # | What | Why | Data needed |
|---|---|---|---|
| 2.3 | Single-name attention-fade signal | Test the "fade retail at attention extremes" rule on NVDA/TSLA/GME | Reddit Pushshift archive ($), StockTwits scrape, OR Robintrack 2018-2020 holdings |
| 2.4 | Weekly FINRA ATS tilt | Test "dark pool % as institutional accumulation flag" on single names | FINRA ATS public files (free, T+2wk lag) |
| 2.5 | NVDA/TSLA case studies | Apply GEX/DIX rules to specific high-meme names | Per-ticker GEX (paid: SpotGamma $200/mo, or DIY from CBOE) |
| 3.1 | Cross-sectional GEX (long high-GEX names, short low-GEX names) | If GEX works as a *cross-sectional* signal in addition to time-series, combinable Sharpe could reach 1.5+ | Universe-level GEX (paid only) |
| 4.1 | Paper-trade Rule #1 in IBKR for 4 weeks | Confirm the rule works in live conditions, no implementation gotchas | IBKR paper account (free) |

Pick whichever interests you. Rule #1 is already actionable today; the rest is icing.
