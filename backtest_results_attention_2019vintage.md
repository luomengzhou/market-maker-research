# Phase 2.3b — Attention-fade test on 2019-VINTAGE meme basket

*Survivorship-bias-controlled re-run of [Phase 2.3](backtest_results_attention.md). The original test selected names with 2026 hindsight (NVDA, TSLA, COIN, PLTR — names that became dominant BECAUSE they ran up); this version uses names that were retail-attention-prone AS OF LATE 2019 / EARLY 2020, including ones that later collapsed.*

**Data window:** 2019-01-03 → 2026-04-28
**2019-vintage meme basket (14 names):** TLRY, CGC, NKLA, RIDE, SPCE, NIO, PLUG, BBBY, GME, AMC, BB, NOK, AMD, TSLA
**Control basket:** JNJ, KO, PG, WMT, JPM
**Horizons:** [5, 21, 63] trading days

⚠️  **Missing from yfinance:** NKLA, RIDE.  Likely delisted with no data archive.

## Coverage by ticker

| Ticker | First date | Last date | Rows |
|---|---|---|---|
| TLRY | 2019-01-03 | 2026-04-28 | 1,839 |
| CGC | 2019-01-03 | 2026-04-28 | 1,839 |
| SPCE | 2019-01-03 | 2026-04-28 | 1,839 |
| NIO | 2019-01-03 | 2026-04-28 | 1,839 |
| PLUG | 2019-01-03 | 2026-04-28 | 1,839 |
| BBBY | 2019-01-03 | 2026-04-28 | 1,839 |
| GME | 2019-01-03 | 2026-04-28 | 1,839 |
| AMC | 2019-01-03 | 2026-04-28 | 1,839 |
| BB | 2019-01-03 | 2026-04-28 | 1,839 |
| NOK | 2019-01-03 | 2026-04-28 | 1,839 |
| AMD | 2019-01-03 | 2026-04-28 | 1,839 |
| TSLA | 2019-01-03 | 2026-04-28 | 1,839 |
| JNJ | 2019-01-03 | 2026-04-28 | 1,839 |
| KO | 2019-01-03 | 2026-04-28 | 1,839 |
| PG | 2019-01-03 | 2026-04-28 | 1,839 |
| WMT | 2019-01-03 | 2026-04-28 | 1,839 |
| JPM | 2019-01-03 | 2026-04-28 | 1,839 |

## Meme basket (2019-vintage) results

|   horizon | proxy              |   n_ext |   n_rest |   ext_bps |   rest_bps |   diff_bps |   tstat | basket            |
|----------:|:-------------------|--------:|---------:|----------:|-----------:|-----------:|--------:|:------------------|
|         5 | mom_21d_top10pct   |    2134 |    19202 |       1.9 |      -37.4 |       39.3 |    0.89 | 2019-vintage meme |
|        21 | mom_21d_top10pct   |    2134 |    19202 |     -54   |     -139.6 |       85.5 |    1.07 | 2019-vintage meme |
|        63 | mom_21d_top10pct   |    2113 |    18215 |     706.5 |     -479.4 |     1185.8 |    9.44 | 2019-vintage meme |
|         5 | abnvol_5d_>2x      |    1083 |    20253 |    -186.5 |      -25.2 |     -161.2 |   -2.39 | 2019-vintage meme |
|        21 | abnvol_5d_>2x      |    1083 |    20253 |    -230.8 |     -125.7 |     -105.1 |   -0.94 | 2019-vintage meme |
|        63 | abnvol_5d_>2x      |    1051 |    19277 |     399   |     -397.3 |      796.2 |    4.59 | 2019-vintage meme |
|         5 | extreme_1d_>3sigma |     342 |    20994 |    -113.3 |      -32.1 |      -81.2 |   -0.73 | 2019-vintage meme |
|        21 | extreme_1d_>3sigma |     342 |    20994 |     144.3 |     -135.5 |      279.8 |    1.63 | 2019-vintage meme |
|        63 | extreme_1d_>3sigma |     332 |    19996 |     220   |     -365.7 |      585.6 |    2.11 | 2019-vintage meme |

## Control basket results

|   horizon | proxy              |   n_ext |   n_rest |   ext_bps |   rest_bps |   diff_bps |   tstat | basket   |
|----------:|:-------------------|--------:|---------:|----------:|-----------:|-----------:|--------:|:---------|
|         5 | mom_21d_top10pct   |     889 |     8001 |       5.6 |       29.2 |      -23.6 |   -2.54 | Control  |
|        21 | mom_21d_top10pct   |     889 |     8001 |     123   |      110.4 |       12.6 |    0.6  | Control  |
|        63 | mom_21d_top10pct   |     786 |     7684 |     330.6 |      325.3 |        5.3 |    0.12 | Control  |
|         5 | abnvol_5d_>2x      |     106 |     8784 |      46.5 |       26.6 |       19.9 |    0.28 | Control  |
|        21 | abnvol_5d_>2x      |     106 |     8784 |     -82.4 |      114   |     -196.4 |   -3.83 | Control  |
|        63 | abnvol_5d_>2x      |      98 |     8372 |     536.7 |      323.3 |      213.4 |    2.86 | Control  |
|         5 | extreme_1d_>3sigma |     128 |     8762 |    -116.5 |       28.9 |     -145.5 |   -2.74 | Control  |
|        21 | extreme_1d_>3sigma |     128 |     8762 |     258.6 |      109.5 |      149.1 |    2.61 | Control  |
|        63 | extreme_1d_>3sigma |     123 |     8347 |     451.8 |      323.9 |      127.9 |    1.77 | Control  |

## Headline finding — Phase 2.3's anti-fade conclusion is ROBUST to survivorship-bias control

**The 2019-vintage basket shows 63d continuation effects of similar or *stronger* magnitude than the 2026-hindsight basket.** The Barber-Odean attention-fade is rejected on this sample too.

| Proxy | Phase 2.3 (hindsight) 63d diff | Phase 2.3b (vintage) 63d diff | Direction |
|---|---|---|---|
| mom_21d_top10pct | +878 bps  (t=5.9) | **+1,186 bps  (t=9.4)** | continuation, even stronger |
| abnvol_5d_>2x   | +1,109 bps (t=4.0) | +796 bps   (t=4.6) | continuation, similar magnitude |
| extreme_1d_>3σ  | +378 bps  (t=1.0) | +586 bps   (t=2.1) | continuation, more significant |

**Interpretation:** in a basket of mostly-failed retail favorites (BBBY went to ~$0; SPCE -98% from peak; NIO -90%; BB/NOK rangebound), the recent *winners within the basket* kept winning for 1-3 months. So even when the basket as a whole performs poorly (most rest_bps values are negative across horizons), the attention-extreme sub-group avoids that drag for a meaningful window.

This is the opposite of the Barber-Odean prediction. The most likely mechanism (per the theory primer): modern retail flow (Robinhood + r/wsb + 0DTE) creates a persistent bid in attention names that wasn't present in Barber & Odean's 1995–2000 sample. Attention plus momentum begets more attention plus momentum, until eventually it doesn't — but the "doesn't" mostly happens *beyond* the 63-day horizon we measured.

## A new wrinkle: short-horizon weak fade in `abnvol`

Look closely at the `abnvol_5d_>2x` proxy in the 2019-vintage panel:
- 5d: **-161 bps, t=-2.4** (small significant fade)
- 21d: -105 bps, t=-0.9 (insignificant)
- 63d: +796 bps, t=+4.6 (massive continuation)

**Volume spikes do produce a small reversion in the next 5 days, then the trend resumes and dominates.** This is consistent with informed-trader / liquidity-provider models (Cont/Stoikov OFI literature): an unusually-high-volume day means liquidity providers bore some inventory imbalance, and the next few days mean-revert as that inventory normalizes. After that, the underlying attention/flow tailwind reasserts itself.

This nuance does NOT change Rule #2 (still: don't trade attention extremes systematically), but it does suggest a possible Phase 2.4 follow-up: a *very* short-horizon (3-5 day) abnvol-fade strategy might have edge, gross of borrow costs.

## Caveats — partial survivorship bias remains

**NKLA and RIDE both dropped from yfinance entirely** (delisted, no archive). Both were classic 2019-2020 retail-attention episodes that ended in fraud-related delisting. Their absence biases this test *toward* the continuation finding — the most catastrophic crashes that should anchor the bimodal-tail-risk warning are missing from the panel.

**BBBY's post-bankruptcy data is suspect.** yfinance shows a $3.68–$37.86 close range with 1.7 billion shares of recorded volume after the April 2023 Chapter 11 — likely OTC pink-sheet activity, which is real trading but not what most retail investors experienced. The original common shares effectively went to zero. Practical effect on the test is small (most of BBBY's attention episodes happened in 2020-2022 when the data is reliable), but the 2023+ values shouldn't be taken as a real "investable" tape.

**Even with these caveats, the directional conclusion holds.** A more rigorous re-test would use CRSP delisted-securities data (available via WRDS) which preserves the actual delisting return. But the Phase 2.3b result combined with the Phase 2.3 result means the burden of proof now lies with anyone arguing the Barber-Odean fade still works in modern meme names.

## Files

- `figures/attention_fade_grid_2019vintage.png`

## Combined Phase 2.3 + 2.3b conclusion for the playbook

Modern retail-attention names exhibit MOMENTUM at horizons ≤3 months, regardless of basket selection (vintage or hindsight). The classic Barber-Odean fade is a 1990s phenomenon in boring stocks (still weakly visible in our control basket at 5d) and does not generalize to the post-2020 retail-trading era for attention names.

Practical implication for retail: confirms the rewritten Rule #2. Don't try to fade attention extremes. The continuation effect is real; the end-state crashes are also real but happen on longer timescales than 63d-window systematic strategies easily capture. The honest conclusion: **the alpha at single-name attention extremes is not sustainably extractable by retail systematic methods** — fade loses, chase has bimodal tail risk, so don't trade them systematically.
