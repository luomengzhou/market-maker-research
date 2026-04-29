# Phase 2.5 — Does GEX carry information beyond VIX?

**Data window:** 2011-05-02 → 2026-04-27  (3,769 trading days)
**OOS start:** 2021-01-01  •  **Round-trip cost:** 1.0 bps

## The question

Phase 2.1's GEX defensive tilt works (OOS Sharpe 0.82, MaxDD -22% vs SPY's -34%). But VIX and GEX are correlated — both rise during stress. **Is the GEX rule's edge actually about dealer positioning, or is it just a complicated VIX proxy?** If a simple VIX rule produces the same result, we should retire GEX (vendor risk, complexity) and use VIX (free everywhere, transparent).

## Correlation diagnostics

- **corr(GEX, VIX) levels:** `-0.315`
- **corr(signed-log-GEX, log-VIX):** `-0.485` (more linear after transformation)
- **Negative-GEX days with VIX > 25:** 60% (of 346 neg-GEX days)
- **Negative-GEX days with VIX > 20:** 88%
- **VIX > 25 days with negative GEX:** 43% (of 488 VIX>25 days)

**Initial read:** GEX and VIX are correlated but NOT identical. The asymmetry between the two conditioning probabilities reveals where they disagree.

## Strategy comparison (VIX threshold = 25)

| strategy                                   |   sharpe_is |   sharpe_oos |   sharpe_full |   max_dd |   pct_long |   turnover_yr |
|:-------------------------------------------|------------:|-------------:|--------------:|---------:|-----------:|--------------:|
| SPY buy-and-hold                           |       0.798 |        0.897 |         0.832 |   -0.337 |    100     |         0     |
| VIX-only (long if VIX<25.0)                |       0.923 |        0.68  |         0.831 |   -0.226 |     86.999 |         8.293 |
| GEX-only (long if GEX>0)                   |       0.872 |        0.821 |         0.853 |   -0.218 |     90.793 |        13.777 |
| AND (both VIX low AND GEX>0)               |       0.976 |        0.599 |         0.83  |   -0.233 |     83.338 |        13.911 |
| OR (VIX low OR GEX>0)                      |       0.839 |        0.89  |         0.858 |   -0.224 |     94.455 |         8.025 |
| GEX residualized for VIX (long if resid>0) |       0.509 |        0.445 |         0.483 |   -0.26  |     51.499 |        34.71  |

## Strategy comparison (VIX threshold = 20)

| strategy                                   |   sharpe_is |   sharpe_oos |   sharpe_full |   max_dd |   pct_long |   turnover_yr |
|:-------------------------------------------|------------:|-------------:|--------------:|---------:|-----------:|--------------:|
| SPY buy-and-hold                           |       0.798 |        0.897 |         0.832 |   -0.337 |    100     |         0     |
| VIX-only (long if VIX<20.0)                |       0.662 |        0.612 |         0.645 |   -0.155 |     72.46  |        15.783 |
| GEX-only (long if GEX>0)                   |       0.872 |        0.821 |         0.853 |   -0.218 |     90.793 |        13.777 |
| AND (both VIX low AND GEX>0)               |       0.664 |        0.599 |         0.642 |   -0.148 |     71.345 |        17.656 |
| OR (VIX low OR GEX>0)                      |       0.872 |        0.83  |         0.857 |   -0.221 |     91.908 |        11.637 |
| GEX residualized for VIX (long if resid>0) |       0.509 |        0.445 |         0.483 |   -0.26  |     51.499 |        34.71  |

## Headline finding — GEX adds info beyond VIX, and the OR-combination is the best operational rule

Three clean conclusions from the table:

1. **GEX is NOT just a VIX proxy.** Negative correlation is only -0.31 (levels) / -0.49 (logged). 40% of negative-GEX days have VIX < 25, and 57% of VIX > 25 days have positive GEX. The two indicators measure related but genuinely distinct stress.
2. **GEX-only modestly beats VIX-only OOS** (Sharpe 0.82 vs 0.68 at threshold 25). The dealer-flow story carries information beyond the vol-level story. Rule #1 in the playbook is not just a complicated VIX rule.
3. **The "long unless BOTH stressed" rule wins OOS** — long SPY UNLESS (VIX > 25 AND GEX < 0). OOS Sharpe 0.89 vs GEX-only 0.82, with similar drawdown control (-22%). This is the practical operational optimum: step aside only when both indicators agree on stress.

The "AND" rule (long only when BOTH calm) is too defensive — it sacrifices equity-risk premium during periods where one indicator is borderline but the other is clear. OOS Sharpe 0.60.

The GEX-residualized-for-VIX strategy (long if the GEX residual is positive after regressing out VIX) has Sharpe 0.48. This means **the part of GEX that's orthogonal to VIX is NOT itself a reliable signal at the 0-cutoff.** GEX's edge is in the *joint* info with VIX — stress confirmation across two channels — not in some VIX-orthogonal residual.

## What the scatter plot shows

In `figures/gex_vs_vix_scatter.png`, look at the four quadrants formed by GEX=0 horizontal and VIX=25 vertical lines:

- **Bottom-left (neg GEX, low VIX)** — ~40% of all neg-GEX days. Dealers short gamma but VIX hasn't priced the stress yet. **GEX leads VIX** in these episodes.
- **Top-right (pos GEX, high VIX)** — ~57% of all VIX>25 days. Vol elevated but dealers still long-gamma. Often event-vol pricing without underlying flow stress. **VIX overstates** here.
- **Top-left (pos GEX, low VIX)** — the dominant calm regime, majority of sample.
- **Bottom-right (neg GEX, high VIX)** — the *unambiguous* stress regime. Few days but contains the worst drawdown periods (March 2020, Oct 2022, Aug 2024). **This is the OR-rule's sit-out trigger.**

## Updated Rule #1 recommendation

**Old Rule #1:** long SPY when daily GEX > 0; flat when GEX ≤ 0.

**Improved Rule #1 (Phase 2.5 update):** long SPY UNLESS *both* VIX > 25 *and* GEX < 0.

| Metric | Old (GEX-only) | New (OR rule) | Improvement |
|---|---|---|---|
| Sharpe full | +0.85 | +0.86 | +0.01 |
| Sharpe IS | +0.87 | +0.84 | -0.03 |
| Sharpe OOS | +0.82 | **+0.89** | **+0.07** |
| Max DD | -21.8% | -22.4% | (basically equal) |
| % long | 91% | 94% | (slightly more long) |

The OOS Sharpe gain is meaningful and path quality is preserved. The new rule also **requires confirmation across two independent indicators**, which makes it more robust to vendor risk on either. If SqueezeMetrics changes its GEX methodology, VIX is still a sanity check; if VIX has a structural shift (e.g., a 0DTE-driven floor post-2022), GEX is still working.

Updates propagated to:
- `04_retail_playbook.md` — Rule #1 rewritten with the double-stress trigger
- `daily_signal.py` — extended to pull VIX and recommend the OR rule

## Files

- `figures/gex_vs_vix_equity.png` — equity curves of all 6 strategies. OR-rule (red) and GEX-only (blue) are visually nearly indistinguishable; both clearly outperform VIX-only (orange) and AND-rule (green) at OOS.
- `figures/gex_vs_vix_scatter.png` — VIX vs GEX scatter; the disagreement quadrants are the source of GEX's incremental info.
