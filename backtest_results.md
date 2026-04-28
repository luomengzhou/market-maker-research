# Phase 2.1 — GEX regime backtest on SPY

**Data window:** 2011-05-02 → 2026-04-27  (3,769 trading days)
**OOS start:** 2021-01-01  •  **Round-trip cost:** 1.0 bps  •  **Negative-GEX days:** 346 (9.2%)

## Headline result

The **defensive-tilt** rule (long SPY when daily GEX > 0; flat when GEX < 0) achieves
OOS Sharpe **0.82** vs SPY buy-and-hold **0.90** —
i.e. essentially the same risk-adjusted return — while cutting full-sample max drawdown
to **-22%** vs SPY's **-34%**.

The naive intraday→daily translation of the Dim/Eraker/Vilkov hypothesis ("fade in positive GEX, ride in negative GEX") **loses money cleanly** at daily frequency (Sharpe -0.49 to -0.72). The intraday gamma-reflexivity result does not survive a daily horizon, but GEX *as a stress-regime indicator* does add value via path improvement.

## All strategy variants tested

| Strategy | Regime method | IS Sharpe | OOS Sharpe | Full Sharpe | Max DD | Turnover/yr |
|---|---|---:|---:|---:|---:|---:|
| intraday-translation | sign | -0.64 | -0.21 | -0.49 | -78.6% | 254.1 |
| intraday-translation | zscore {'threshold': 1.0} | -0.60 | -0.97 | -0.72 | -77.8% | 113.6 |
| defensive-tilt | sign | +0.87 | +0.82 | +0.85 | -21.8% | 13.6 |
| defensive-tilt | zscore {'threshold': 0.5} | +0.49 | +1.01 | +0.69 | -19.7% | 29.7 |
| defensive-tilt | zscore {'threshold': 1.0} | +0.80 | +0.86 | +0.82 | -24.8% | 20.6 |
| defensive-tilt | quantile | +0.54 | +0.91 | +0.68 | -20.2% | 33.3 |
| aggressive-tilt | sign | +0.52 | +0.45 | +0.50 | -31.2% | 27.3 |
| aggressive-tilt | zscore {'threshold': 1.0} | +0.34 | +0.47 | +0.39 | -36.7% | 41.2 |
| **SPY buy-and-hold** | — | +0.80 | +0.90 | +0.83 | -33.7% | — |
| **Random baseline** | coin-flip | — | — | +0.25 | — | — |

## Conditional next-day return stats by GEX regime

**Full sample (2011-2026):**

|   regime |    n |   mean_fwd_ret_bps |   median_fwd_ret_bps |   fwd_vol_bps |   hit_rate_up |   autocorr_lag1 |
|---------:|-----:|-------------------:|---------------------:|--------------:|--------------:|----------------:|
|       -1 |  346 |              11.88 |                 7.97 |           223 |          53.5 |          -0.328 |
|        1 | 3422 |               5.08 |                 6.58 |            89 |          55.3 |          -0.02  |

**OOS only (2021-2026):**

|   regime |    n |   mean_fwd_ret_bps |   median_fwd_ret_bps |   fwd_vol_bps |   hit_rate_up |   autocorr_lag1 |
|---------:|-----:|-------------------:|---------------------:|--------------:|--------------:|----------------:|
|       -1 |  161 |              11.76 |                -9.39 |           175 |          49.1 |          -0.073 |
|        1 | 1173 |               5.25 |                 7.86 |            94 |          55.3 |          -0.086 |

## Interpretation

1. **Mean returns are POSITIVE in both regimes** — negative-GEX days even have higher mean (+11.9 bps vs +5.1 bps full-sample). The regime is not directional; it's about **dispersion and tail risk**, not drift.
2. **Volatility is ~2.5× higher** on negative-GEX days (223 vs 89 bps next-day stdev). Defensive tilt captures most of the equity-risk premium while sidestepping the high-vol regime.
3. **Autocorrelation in the negative-GEX regime is strongly negative (-0.33 full sample)** — these stress days tend to mean-revert at daily frequency, not trend. This is the OPPOSITE of Dim/Eraker/Vilkov's intraday finding, and explains why the naive intraday→daily translation fails.
4. **OOS Sharpe is slightly higher than IS** for several defensive variants — a mild flag, but explainable: the OOS window (2021-2026) contains the COVID recovery, 2022 inflation drawdown, and 2025 vol episodes, all of which had negative-GEX clusters that the strategy successfully avoided.

## Caveats / known weaknesses

- **Vendor dependency**: SqueezeMetrics could change their GEX methodology. Independent replication via `jensolson/SPX-Gamma-Exposure` (open source) on CBOE delayed quotes is a Phase 2 follow-up.
- **No intraday testing**: this is daily-close to daily-close. The Dim/Eraker/Vilkov result is intraday and is *not* falsified by these results — it's just non-actionable for retail without intraday option-chain access.
- **Regime breakdown**: 2018-Q4 vol spike was a small-but-real GEX strategy underperformance window (visible in drawdown chart). The defensive rule can be early on "step aside" decisions when GEX flips negative briefly mid-month.
- **Random baseline Sharpe ≈ +0.25** (not zero) reflects the long equity-drift bias of the underlying. Acceptable but means we should weight Sharpe spread (defensive_tilt - random) > 0.5 as the meaningful margin.

## Reading the figures

- `figures/gex_regime_returns.png` — clear visual of the **dispersion difference**: negative-GEX (red) is visibly wider and more bimodal than positive-GEX (blue). Both are roughly centered at zero with positive drift.
- `figures/gex_strategy_equity.png` — defensive-tilt (blue) tracks SPY (gray) closely until each major drawdown, where it lags less. Random baseline (orange) drifts modestly upward from the long-bias.
- `figures/gex_drawdown.png` — the COVID-2020 episode is the standout: SPY hit -34%, defensive-tilt capped at ~-12%. Most of the strategy's value is concentrated in tail events.

## What this implies for the project's main question

The folk claim "market makers fade retail trends" doesn't survive translation into a daily-frequency tradable signal in the obvious way. But dealer-gamma data **is** useful to retail — as a stress regime indicator that shrinks drawdowns without sacrificing much risk-adjusted return. This is a less exciting story than the meme version, but it's the actual edge.
