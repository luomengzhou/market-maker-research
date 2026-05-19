# Phase 2.6 — Continuous variants of Rule #1

**Data window:** 2011-05-02 → 2026-04-27  (3,769 trading days)
**OOS start:** 2021-01-01  •  **Round-trip cost:** 1.0 bps

## Question

Phase 2.5's binary OR rule (long unless VIX>25 AND GEX<0) is the playbook headline at OOS Sharpe 0.89 and MaxDD -22%. Can a continuous variant — three-state, smooth-logistic, or vol-targeted — improve on Sharpe, drawdown, OR turnover (whipsaw) without losing the others?

Operational tradeoff: binary is trivial to execute (buy or sell SPY in full). Continuous requires fractional sizing each day (extra discretion + rounding to share counts). Continuous wins only if the stat improvement is worth the extra discipline cost.

## Variants tested

1. **Binary OR (Rule #1)** — long 1.0 unless double-stress, then 0.0. The Phase 2.5 winner.
2. **Three-state** — long 1.0 if both calm, 0.5 if exactly one signal stresses, 0.0 if both. Operationally manageable (only three position levels).
3. **Smooth logistic (k=1.5)** — position = sigmoid(k · (-vix_z + gex_z)). Fully continuous; rolling 1y z-scores.
4. **Vol-targeted (10% target)** — position = min(1, 10% / realized_vol_10d), zeroed in double-stress.

## Results

| strategy                  |   sharpe_is |   sharpe_oos |   sharpe_full |   max_dd |   avg_pos |   pos_std |   turnover_yr |   n_changes |
|:--------------------------|------------:|-------------:|--------------:|---------:|----------:|----------:|--------------:|------------:|
| SPY buy-and-hold          |       0.798 |        0.897 |         0.832 |   -0.337 |     1     |     0     |         0     |           0 |
| Binary OR (Rule #1)       |       0.839 |        0.89  |         0.858 |   -0.224 |     0.945 |     0.229 |         8.025 |         120 |
| Three-state (1 / 0.5 / 0) |       0.951 |        0.786 |         0.888 |   -0.215 |     0.889 |     0.266 |        10.901 |         298 |
| Smooth logistic (k=1.5)   |       0.621 |        0.771 |         0.677 |   -0.136 |     0.59  |     0.363 |        27.683 |        2946 |
| Vol-targeted (10% target) |       0.832 |        0.871 |         0.846 |   -0.133 |     0.753 |     0.285 |        10.691 |        1631 |

## Files

- `figures/continuous_rule1_comparison.png` — equity curves (top) + position traces (bottom) for binary vs smooth logistic

## Headline finding — binary OR remains the winner. No update to Rule #1.

| Variant | OOS Sharpe | Full Sharpe | MaxDD | Turnover/yr | Verdict |
|---|---:|---:|---:|---:|---|
| SPY buy-and-hold | 0.90 | 0.83 | -34% | 0 | reference |
| **Binary OR (Rule #1)** | **0.89** | 0.86 | -22% | **8** | **stays as the rule** |
| Three-state | 0.79 | 0.89 | -22% | 11 | overfits in-sample, drops 0.10 OOS |
| Smooth logistic | 0.77 | 0.68 | -14% | 28 | gives up too much equity premium |
| Vol-targeted (10%) | 0.87 | 0.85 | **-13%** | 11 | best MaxDD; small Sharpe loss; honorable mention |

**Three takeaways:**

1. **None of the continuous variants beats binary on OOS Sharpe.** The best is vol-targeted at 0.87 (binary is 0.89). Three-state overfits — strong full-sample Sharpe (0.89) collapses to 0.79 OOS.
2. **Smooth logistic is too conservative.** It gives up the equity-risk premium in exchange for path quality, ending with ~12% lower OOS Sharpe than binary. The position trace (figure bottom panel) shows it's constantly at 0.3–0.9, never running fully long even in clearly calm regimes. Over-smoothed.
3. **Vol-targeted is the honorable mention** — best MaxDD (-13% vs binary's -22%) at the cost of 0.02 OOS Sharpe and ~14× more rebalancing days (1,631 daily position changes vs binary's 120). Operationally infeasible for retail without an automated execution layer.

## Decision: stick with binary OR

Reasons:
- **OOS Sharpe is the binding constraint** for a research-validated rule, and binary wins.
- **Operational simplicity matters for retail discipline**: binary requires ~8 trades a year in SPY shares (no fractional sizing decisions, no rounding to lots, no "what if I'm at 73% — do I rebalance to 75% or wait?"). Continuous rules introduce friction that compounds errors over time.
- **The gap binary-vs-vol-targeted is small**: ~0.02 Sharpe and 9pp MaxDD. Not worth giving up daily-decision simplicity.
- **Future-self can revisit**: if you ever automate execution (e.g., IBKR API + daily-trigger script), the vol-targeted variant becomes effectively free to run, and the slightly better MaxDD might be worth it. Until then, binary.

**No update to playbook Rule #1 or `daily_signal.py`.** Phase 2.6 is a documented null finding — the simpler rule survives the refinement test.

## What this also confirms

The binary OR rule's edge comes from a small number of acute regime shifts (BOTH stress signals firing simultaneously, ~6% of days) — not from continuously-varying exposure based on a stress score. This is consistent with the dealer-flow story: GEX < 0 AND VIX > 25 marks a *qualitatively different* regime (forced dealer selling + elevated implied vol), not a quantitative position on a smooth stress continuum. Binary thresholding is the right structural choice for the underlying mechanism.
