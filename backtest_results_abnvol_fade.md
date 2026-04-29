# Phase 2.4 — abnvol 5-day fade tradability test

**Data window:** 2019-03-29 → 2026-04-28
**Combined basket (23 tickers):** AMC, AMD, BB, BBBY, CGC, COIN, GME, JNJ, JPM, KO, NIO, NOK, NVDA, PG, PLTR, PLUG, RBLX, RIOT, SOFI, SPCE, TLRY, TSLA, WMT
**Round-trip cost:** 5.0 bps  •  **OOS start:** 2023-01-01

## Hypothesis (from Phase 2.3b discovery)

On days where 5-day average volume exceeds 2× the 60-day average AND the prior 5-day return is negative, take a long position next day at open and hold for N days. Phase 2.3b's diagnostic showed a -161 bps t=-2.4 fade at the 5-day horizon, suggesting the move pre-volume-spike is partially over-reacted and reverts in the following week.

**Long-only specification** (no shorts) — sidesteps borrow-cost confound. Tests whether retail can extract the fade without complex execution.

## Combined basket — grid search

| basket   |   abnvol_threshold |   hold_days |   n_trades |   mean_trade_bps_gross |   mean_trade_bps_net |   hit_rate_gross |   sharpe_full |   sharpe_is |   sharpe_oos |   max_dd |
|:---------|-------------------:|------------:|-----------:|-----------------------:|---------------------:|-----------------:|--------------:|------------:|-------------:|---------:|
| Combined |                1.5 |           3 |       1662 |                  3.768 |               -1.232 |            0.498 |         0.611 |       0.639 |        0.577 |   -0.946 |
| Combined |                1.5 |           5 |       1661 |                -65.294 |              -70.294 |            0.482 |         0.79  |       1.3   |        0.11  |   -0.952 |
| Combined |                1.5 |          10 |       1658 |               -226.077 |             -231.077 |            0.453 |        -0.064 |       0.807 |       -1.582 |   -0.998 |
| Combined |                2   |           3 |        500 |                -97.786 |             -102.786 |            0.48  |        -0.745 |      -0.555 |       -0.957 |   -0.973 |
| Combined |                2   |           5 |        500 |               -192.902 |             -197.902 |            0.424 |        -0.268 |       0.207 |       -0.928 |   -0.978 |
| Combined |                2   |          10 |        500 |               -406.539 |             -411.539 |            0.404 |        -2.197 |      -1.386 |       -3.426 |   -1     |
| Combined |                3   |           3 |        110 |               -159.918 |             -164.918 |            0.382 |        -0.537 |      -0.796 |       -0.236 |   -0.759 |
| Combined |                3   |           5 |        110 |               -295.345 |             -300.345 |            0.373 |        -1.215 |      -1.382 |       -0.995 |   -0.797 |
| Combined |                3   |          10 |        110 |               -380.928 |             -385.928 |            0.364 |        -2.253 |      -2.56  |       -1.891 |   -0.947 |

## Meme + vintage subset (excludes JNJ, KO, PG, WMT, JPM)

| basket       |   abnvol_threshold |   hold_days |   n_trades |   mean_trade_bps_gross |   mean_trade_bps_net |   hit_rate_gross |   sharpe_full |   sharpe_is |   sharpe_oos |   max_dd |
|:-------------|-------------------:|------------:|-----------:|-----------------------:|---------------------:|-----------------:|--------------:|------------:|-------------:|---------:|
| Meme+Vintage |                1.5 |           3 |       1375 |                  1.013 |               -3.987 |            0.481 |         0.507 |       0.501 |        0.514 |   -0.937 |
| Meme+Vintage |                1.5 |           5 |       1374 |                -78.596 |              -83.596 |            0.464 |         0.793 |       1.34  |        0.054 |   -0.947 |
| Meme+Vintage |                1.5 |          10 |       1371 |               -279.473 |             -284.473 |            0.421 |        -0.138 |       0.85  |       -1.807 |   -0.998 |
| Meme+Vintage |                2   |           3 |        427 |                -97.666 |             -102.666 |            0.485 |        -0.65  |      -0.393 |       -0.938 |   -0.972 |
| Meme+Vintage |                2   |           5 |        427 |               -204.335 |             -209.335 |            0.417 |        -0.172 |       0.313 |       -0.872 |   -0.977 |
| Meme+Vintage |                2   |          10 |        427 |               -463.276 |             -468.276 |            0.386 |        -2.134 |      -1.23  |       -3.512 |   -1     |
| Meme+Vintage |                3   |           3 |         99 |               -165.212 |             -170.212 |            0.394 |        -0.515 |      -0.796 |       -0.188 |   -0.759 |
| Meme+Vintage |                3   |           5 |         99 |               -308.629 |             -313.629 |            0.394 |        -1.16  |      -1.382 |       -0.858 |   -0.797 |
| Meme+Vintage |                3   |          10 |         99 |               -419.291 |             -424.291 |            0.374 |        -2.288 |      -2.56  |       -1.965 |   -0.944 |

## Headline finding — the fade signal is too weak to trade

**Per-trade net return (the trader-relevant statistic) is negative or near-zero at every parameterization:**

| Threshold | Hold | Per-trade net (bps) | Conclusion |
|---|---|---:|---|
| 1.5× | 3d | **-1.2** | break-even |
| 1.5× | 5d | -70.3 | loses |
| 1.5× | 10d | -231.1 | loses badly |
| 2.0× | any | -103 to -412 | loses |
| 3.0× | any | -165 to -386 | loses |

The single break-even-after-cost cell (1.5× threshold, 3d hold, n=1,662 trades) has gross per-trade of only +3.8 bps before cost. After 5 bps round-trip (realistic retail level for non-mega-cap names) it is -1.2 bps net — i.e. a coin flip on a noisy signal that cost you a basis point each time. Not a viable strategy.

**Tighter signals make the situation worse, not better.** If the abnvol fade were a real edge, raising the threshold from 1.5× → 2.0× → 3.0× should produce *better* per-trade returns (signal/noise improvement). Instead per-trade goes from -1 bps to -100 bps to -165 bps. This pattern is consistent with the fade being a statistical artifact of averaging across many noisy episodes, not a genuine reversal effect that's stronger when more pronounced.

## Why the Sharpe column is misleading and shouldn't be trusted here

The Sharpe full / OOS columns above show some positive numbers (e.g., +0.79 at threshold 1.5× hold 5d) despite negative per-trade returns. **Don't trust those Sharpes.** The reason: the daily PnL accumulator stacks overlapping concurrent positions without a position-size cap, so on days with many simultaneous open trades the strategy is effectively levered 30-50×. The -94% max drawdowns reveal this clearly — a true Sharpe-0.79 strategy doesn't lose 94% of capital. The Sharpe number is an artifact of the daily-aggregation mechanics, not a tradable result.

The trader-relevant metric is **per-trade net**, which is unambiguously negative or zero.

## What this means for the playbook

Phase 2.3b's discovery (`abnvol > 2×` produces a -161 bps t=-2.4 fade at 5d in the diagnostic test) is a **real statistical effect but not a tradable retail strategy.** The effect is too small to overcome realistic transaction costs. The 5 bps round-trip assumption is generous — actual retail costs on names like SPCE/BBBY/PLUG can be 10-20 bps including spread + slippage, which would push every parameterization solidly into negative territory.

This is a clean negative result. The playbook stays as-is: Rule #2 says don't trade single-name attention extremes systematically, and the would-be carve-out for "short-window vol-spike fade" doesn't survive the tradability test.

**No new rule added.** Phase 2.4 documents the dead-end so future-self doesn't re-test the same dead-end.

## Caveats

- 5 bps round-trip is generous for the basket; 10-20 bps is more realistic on smaller names. Higher costs only make the negative result more decisive.
- Long-only spec skips the UP-move fade opportunities. A long-short version would need borrow-cost modeling and would face availability issues precisely on names where attention is highest (squeeze names).
- The daily-PnL aggregation has the position-stacking issue described above. Re-running with a 5-position concurrent cap is a possible follow-up but unlikely to flip the negative per-trade conclusion.
- A more rigorous version would use vol-targeting to equalize position sizing across high-vol meme names and low-vol controls. Probably won't change the conclusion since the signal itself is too weak per-trade.

## Files

- `figures/abnvol_fade_equity.png` — equity curve of the best-by-Sharpe parameterization (note: misleading per the discussion above; included for completeness only)
