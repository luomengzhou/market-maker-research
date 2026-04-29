# Retail Playbook — What to Borrow from Market-Maker / Dealer-Flow Mechanics

*Phase 3 deliverable. Built on the [theory primer](01_theory_primer.md) and three empirical sub-projects: [backtest_results.md](backtest_results.md) (GEX regime), [backtest_results_dix.md](backtest_results_dix.md) (DIX retail-flow), and [backtest_results_attention.md](backtest_results_attention.md) (Barber-Odean attention-fade reproduction). Read those first for the why; this file is the so-what.*

---

## TL;DR — what survived the data

The most important finding is **what didn't survive**. The "MMs fade retail" meme is empirically rejected at *both* levels we tested:

- **Aggregate retail (Phase 2.2 / DIX):** high retail buying predicts *positive* forward SPY returns, t-stats up to 10. Retail in aggregate is mildly informed, not dumb.
- **Single-name attention (Phase 2.3 / Barber-Odean reproduction):** in modern meme-stock data (2019-2026), attention extremes are followed by *more* outperformance, not reversion. The classic Barber-Odean attention-fade is rejected on this basket — t=+5.9 the *wrong* direction.

What survives:

1. **Tilt SPY exposure based on dealer GEX regime.** Long when daily GEX > 0; flat when GEX < 0. Almost matches SPY's risk-adjusted return (OOS Sharpe 0.82 vs 0.90) while cutting max drawdown from -34% to -22%. ~14 trades per year. **This is the highest-quality finding in the project.**
2. **Don't trade attention-extreme single names systematically — in either direction.** Don't fade (the data says you'll lose), don't chase (variance is huge, drawdowns when wrong are -50% to -90%). The retail edge is *not here*; treat these as unhedgeable lottery tickets and size accordingly.
3. **Don't try to outrun MMs intraday.** The Dim/Eraker/Vilkov intraday gamma-reflexivity result does *not* survive translation to daily-frequency trading. Without intraday option-chain access (Polygon/CBOE DataShop) you can't directly trade their finding, and the naive daily proxies lose money cleanly.

The rest of this document is the operational layer: position sizing, order types, when to override, what to skip.

---

## How to actually run this day-to-day — `daily_signal.py`

The repo includes a single-command operational runner:

```bash
python daily_signal.py             # show today's signal
python daily_signal.py --log       # also append to decision_log.csv
python daily_signal.py --history 30  # show last 30 days of decisions
python daily_signal.py --quiet     # JSON output (for piping)
```

**Recommended cadence:** run once each evening after US market close (~5:30pm ET). The script:
1. Pulls the latest [SqueezeMetrics free CSV](https://squeezemetrics.com/monitor/static/DIX.csv) (caches locally; `--refresh` to force re-pull).
2. Reads today's GEX, computes 1-year z-score, classifies regime.
3. Prints tomorrow's recommended SPY position (LONG / STEP ASIDE).
4. Flags borderline cases (|z| < 0.3σ, "consider sitting tight" — noise dominates signal).
5. Flags regime transitions vs yesterday.
6. Optionally logs to `decision_log.csv` for later audit / paper-trade comparison.

**Cron-friendly:**
```
30 17 * * 1-5  cd "$HOME/Documents/Market Maker" && python daily_signal.py --log
```

**Sample output:**
```
  Market Maker Daily Signal — Rule #1 (GEX defensive tilt)
  ──────────────────────────────────────────────────────────
  Data as of:           2026-04-28
  SPX close:            7,138.80
  Dealer GEX:           $+6.25B per 1% spot move
  GEX 1y z-score:       +0.20σ  (pct rank 48%)
  DIX:                  0.447

  🟢 REGIME:  POSITIVE-GEX  /  CALM
  ➤ TOMORROW'S POSITION:  LONG SPY  (full target weight)
  ⚠ borderline z<0.3 — consider sitting tight
```

**Paper-trade phase recommendation:** before committing real capital, run with `--log` for 30+ trading days and review the decision log against actual SPY moves. If the rule is doing what you expect, scale into real allocation. If not, the log will show you why.

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

### Rule #2 — Don't fade retail. Don't chase it either. Just don't trade attention extremes systematically.

**Why aggregate retail isn't dumb (Phase 2.2 finding):**
- DIX quintile sort: high-DIX days have *higher* forward 20-day returns than low-DIX days, monotonically.
- t-stat on the spread is 8-10. This is a real effect, not noise.
- Mechanism: aggregate retail buying tracks risk-appetite improvement, which is itself predictive of equity returns.

**Why single-name attention isn't fadeable either (Phase 2.3 + 2.3b findings — REVISED from earlier draft):**

We tested the Barber-Odean (2008) attention-fade hypothesis on two baskets (Phase 2.3 + Phase 2.3b survivorship-bias control) over 2019–2026, with three attention proxies: top-decile prior 21d return, 5d volume > 2× normal, single-day move > 3σ.

- **Phase 2.3**: 10-name meme basket selected with 2026 hindsight (NVDA, TSLA, COIN, PLTR, ...). Result: extreme group OUTPERFORMS by +878 bps over 63d, t=5.9 (mom_21d proxy).
- **Phase 2.3b**: 12-name basket selected with INFO AVAILABLE PRE-2020 (TLRY, NIO, PLUG, SPCE, GME, AMC, BBBY, BB, NOK, AMD, TSLA, CGC) including BBBY which went to zero. Result: extreme group OUTPERFORMS by **+1,186 bps over 63d, t=9.4** — even *stronger* than the hindsight basket.

**Combined result: the Barber-Odean fade is rejected on the modern meme universe at all horizons that matter, regardless of basket selection.** The fade only weakly survives in the boring control basket at 5-day horizon. The conclusion is robust to survivorship-bias control.

A nuance Phase 2.3b surfaced: `abnvol > 2×` shows a small significant fade at 5d (t=-2.4) before flipping to massive continuation at 63d. **Phase 2.4 tested whether this is tradable for retail and the answer is no** — see [backtest_results_abnvol_fade.md](backtest_results_abnvol_fade.md). Best per-trade gross is +3.8 bps; after a generous 5 bps round-trip cost the net is -1 bps and tighter signal thresholds produce *worse* not better per-trade economics. The statistical effect is real but too small to extract net of friction. No rule added; dead-end documented to prevent future re-testing.

Why the academic finding doesn't translate:
- Modern retail flow (Robinhood, r/wsb, 0DTE) creates a persistent bid in attention names that didn't exist in Barber & Odean's 1995–2000 sample.
- 2020–2025 sustained bull market created momentum tailwinds; attention extremes coincide with momentum extremes.
- The catastrophic-crash side of the bimodal distribution (NKLA fraud, RIDE bankruptcy) is also under-captured because yfinance dropped those tickers entirely after delisting — but the directional conclusion holds even with that bias.

**Bimodal outcomes are the real risk.** Mean is positive, distribution is not:
- Most attention episodes momentum-continue (NVDA Q2 2024, MSTR 2024).
- A meaningful minority crash 80–95% from peak (GME 2021 → -90%, BBBY → 0, RIDE → near-zero).
- The mean disguises the fact that *which* episode you're in determines whether you make 5× or lose 90%.

**Operational version (post-falsification):**
- ✋ **Don't run a systematic short-attention strategy.** Data says it loses; borrow availability fails when you need it (squeeze risk); the academic literature behind the rule has not aged into this regime.
- ✋ **Don't run a systematic chase-attention strategy.** The mean is positive but the variance + bimodality means any leveraged or concentrated implementation is a coin-flip on 80% drawdown.
- ✓ **Position-size single-name attention plays as discretionary lottery tickets, not signal trades.** ≤1% of NAV per name; pre-committed stop loss; no averaging down. Treat them like venture-style returns: most go to zero, the winners pay for them.
- ✓ **For yield-extraction, write covered calls or cash-secured puts on attention-extreme names you'd be willing to own at the strike.** This monetizes their elevated implied vol without requiring a directional view. The vol *is* high here — it's the most reliable feature of attention episodes.
- ✓ **The retail edge is at the index level via GEX (Rule #1), not at the single-name level.** Internalize that and stop scanning unusual-flow lists.

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
6. **Phase 2.3 attention-fade test has survivorship bias.** The 10-name meme basket was selected with 2026 hindsight; replacing NVDA/TSLA/COIN/PLTR with their 2019-vintage equivalents (BBBY/RIDE/NOK/BB) would flatten the +1,100 bps headline. The directional conclusion (no systematic Barber-Odean fade in modern meme names) is robust; the magnitude isn't.

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
| 2.3b | Re-run attention test on 2019-vintage meme basket (BBBY, NOK, BB, RIDE, GME-era) | Removes the survivorship-bias confound in Phase 2.3; would let us state effect-size more honestly | yfinance daily OHLCV (free) |
| 2.4 | Weekly FINRA ATS tilt | Test "dark pool % as institutional accumulation flag" on single names | FINRA ATS public files (free, T+2wk lag) |
| 2.5 | Per-ticker GEX on NVDA/TSLA episodes | Apply Rule #1 logic at single-name level on the names where retail attention is strongest | Per-ticker GEX (paid: SpotGamma $200/mo, or DIY from CBOE chains) |
| 3.1 | Cross-sectional GEX (long high-GEX names, short low-GEX names) | If GEX works as a *cross-sectional* signal in addition to time-series, combined Sharpe could reach 1.5+ | Universe-level GEX (paid only) |
| 3.2 | Sentiment composite — StockTwits + r/wsb live-watching panel | Build a forward-looking attention dashboard (not a backtest signal — a monitoring tool to flag names worth Rule #2 treatment) | StockTwits API (free), Reddit API (free) |
| 4.1 | Paper-trade Rule #1 in IBKR for 4 weeks | Confirm the rule works in live conditions, no implementation gotchas | IBKR paper account (free) |

Pick whichever interests you. **Rule #1 is already actionable today; everything else is icing.** The most valuable next step is probably 4.1 (paper-trade verification) — confirms the daily-CSV pipeline + signal end-to-end before committing real capital.
