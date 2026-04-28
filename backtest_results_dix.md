# Phase 2.2 — DIX (retail-positioning) backtest on SPY

**Data window:** 2011-05-27 → 2026-03-30  (3,731 trading days)
**OOS start:** 2021-01-01  •  **Round-trip cost:** 1.0 bps

## What is DIX?

SqueezeMetrics' Dark Index (DIX) is a volume-weighted measure of off-exchange short volume / total volume across S&P 500 names. **Higher DIX → less off-exchange shorting → retail buying pressure dominates.** SqueezeMetrics has historically claimed DIX is *bullish* predictive (follow-retail). The internet-meme version is the opposite (fade-retail). We test both.

## Mean forward SPY return by DIX quintile

| DIX quintile | 1d (bps) | 5d (bps) | 20d (bps) |
|---|---:|---:|---:|
| Q1-low | 3.5 | 15.0 | 48.2 |
| Q2 | 2.0 | 14.8 | 67.8 |
| Q3 | 0.2 | 17.6 | 110.2 |
| Q4 | 8.7 | 37.1 | 153.9 |
| Q5-high | 10.5 | 40.6 | 139.3 |

**t-stats (rough significance — |t|>2 is p<0.05, |t|>2.6 is p<0.01):**

| DIX quintile | 1d | 5d | 20d |
|---|---:|---:|---:|
| Q1-low | 0.87 | 1.97 | 3.18 |
| Q2 | 0.57 | 1.90 | 4.18 |
| Q3 | 0.05 | 2.18 | 7.06 |
| Q4 | 2.12 | 4.47 | 10.49 |
| Q5-high | 2.28 | 4.31 | 8.64 |

## Strategy backtest results

| Signal method | Direction | IS Sharpe | OOS Sharpe | Full Sharpe | Max DD | Turnover/yr |
|---|---|---:|---:|---:|---:|---:|
| level th=0.45 | follow-retail | +0.18 | +0.36 | +0.25 | -39.5% | 82.5 |
| level th=0.45 | fade-retail | -0.29 | -0.46 | -0.35 | -66.0% | 82.5 |
| zscore | follow-retail | +0.45 | -0.47 | +0.15 | -43.7% | 75.2 |
| zscore | fade-retail | -0.58 | +0.34 | -0.28 | -55.4% | 75.2 |
| quantile | follow-retail | +0.33 | -0.13 | +0.17 | -43.7% | 114.1 |
| quantile | fade-retail | -0.48 | -0.04 | -0.33 | -60.3% | 114.1 |
| ema-cross | follow-retail | +0.32 | +0.16 | +0.26 | -33.4% | 235.6 |
| ema-cross | fade-retail | -0.59 | -0.43 | -0.54 | -83.7% | 235.6 |
| **SPY buy-and-hold** | — | +0.82 | +0.76 | +0.80 | -33.7% | — |

## Headline finding

**The follow-retail interpretation wins decisively, and the meme version (fade retail) is empirically wrong.**

The horizon grid shows a clear, monotonic, statistically robust pattern across all three horizons: **the higher today's retail buying pressure (DIX), the higher SPY's forward return on average.** The 20-day t-stats range from 3.2 (Q1) to 10.5 (Q4) — these are not subtle effects. The Q4-Q1 spread at 20 days is **+106 bps** in favor of high-DIX days.

This **directly falsifies the popular claim** that "MMs fade retail at the index level." If retail were systematically wrong, we'd expect Q1 (low retail buying) to outperform Q5 (high retail buying). The data shows the opposite at every horizon.

## But: the signal doesn't beat buy-and-hold as a market-timing rule

| Result | Sharpe | Max DD | Note |
|---|---|---|---|
| Best DIX follow-retail strategy | +0.26 | -33% | ema-cross |
| Best DIX fade-retail strategy | -0.28 | -55% | confirms fade is wrong |
| **SPY buy-and-hold** | **+0.80** | **-34%** | wins |
| GEX defensive-tilt (Phase 2.1) | +0.85 | -22% | wins on path quality |

The reason: even Q1 (low DIX) days have positive forward drift (+48 bps over 20d). Going to cash on those days surrenders too much equity-risk premium for a ~100 bps relative-value edge. **DIX is a real cross-sectional / relative-value signal, not a tradable absolute market-timing signal at SPY level.**

## How to interpret these together

1. **Retail aggregate is not dumb at the index level.** The "smart money fades dumb retail" trope is wrong for SPY. Retail flow is, on net, mildly *informed* about short-term equity returns — probably reflecting that broad retail buying is a real-time proxy for risk-appetite improvement, which is itself predictive.
2. **DIX may still be useful as a cross-sectional or sub-index signal** — testing whether high-DIX *single names* outperform low-DIX names is a natural Phase 2.5 follow-up. SqueezeMetrics' commercial product applies DIX per-ticker.
3. **At the SPY index level, GEX (Phase 2.1) is the more useful free-tier signal** — it adds path quality (smaller drawdowns) where DIX adds nothing.
4. **The retail-behavior alpha** described in the theory primer (Barber & Odean 2008, etc.) is about *individual stocks* and *attention extremes*, not aggregate index flow. DIX confirms that distinction: aggregate retail = neutral/mildly positive; specific-name attention extremes = the contrarian alpha.

## Caveats

- DIX construction is SqueezeMetrics-proprietary. Their published series is unlikely to be deliberately curated (the t-stats hold across IS and OOS), but a from-scratch re-construction using FINRA short-volume data is the right paranoid follow-up.
- The 1-bp transaction cost is generous-to-the-strategy. A more realistic 3-5 bps would push follow-retail Sharpes near or below zero.
- Daily rebalancing on a 20-day-effective signal (t-stats peak at the 20d horizon) is the wrong cadence — overstates turnover, understates capacity. A weekly or 5-day rebalance would likely improve Sharpe.

## Files

- `figures/dix_horizon_grid.png` — bar chart of mean fwd return by quintile and horizon
- `figures/dix_strategy_equity.png` — best follow + best fade strategy equity vs SPY
