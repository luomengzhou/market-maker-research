"""
Phase 2.2 — DIX (retail-positioning) signal backtest.

Tests two competing interpretations of DIX:
    (a) FOLLOW-RETAIL  : high DIX -> retail bullish -> go long
                         low DIX  -> retail bearish -> go short / flat
    (b) FADE-RETAIL    : the contrarian inverse, motivated by the meme version
                         of the project: "retail is dumb, fade them"

Tests at horizons of 1, 5, 20 trading days forward.

Key question: is there enough information in retail-positioning to overcome
~1 bp transaction costs at any horizon? And does following retail beat
fading retail (the SqueezeMetrics claim) or vice versa (the meme claim)?

Outputs:
    figures/dix_horizon_grid.png    forward-return mean by DIX bucket and horizon
    figures/dix_strategy_equity.png best-strategy equity curve vs SPY
    backtest_results_dix.md         narrative writeup
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_signals"))
from gex import load_gex  # noqa: E402
from dix import compute_dix_signal  # noqa: E402

# Reuse helpers from 03_backtest
from importlib.util import spec_from_file_location, module_from_spec  # noqa: E402

_spec = spec_from_file_location("backtest_lib", ROOT / "03_backtest.py")
_bt = module_from_spec(_spec)
_spec.loader.exec_module(_bt)
sharpe = _bt.sharpe
max_drawdown = _bt.max_drawdown
load_spy_returns = _bt.load_spy_returns
apply_costs = _bt.apply_costs

FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(exist_ok=True)
OOS_START = "2021-01-01"
TXN_COST_BPS = 1.0


def merge(gex_df: pd.DataFrame, spy: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    df = gex_df.join(spy[["Close", "ret"]], how="inner", rsuffix="_spy").dropna(subset=["ret"])
    log_ret = np.log(spy["Close"] / spy["Close"].shift(1))
    for h in horizons:
        # h-day forward log-return ending at T+h, observable as of T (no leakage:
        # signal at T uses T-end DIX, predicts cumulative return from T's close to T+h's close)
        df[f"fwd_ret_{h}d"] = log_ret.shift(-h).rolling(h).sum().reindex(df.index)
    return df.dropna()


def horizon_grid(df: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    """For each (horizon, DIX-quintile) bin, compute mean forward return + n + t-stat."""
    rows = []
    for h in horizons:
        col = f"fwd_ret_{h}d"
        df_h = df.dropna(subset=[col]).copy()
        df_h["dix_q"] = pd.qcut(df_h["dix"], q=5, labels=["Q1-low", "Q2", "Q3", "Q4", "Q5-high"])
        for q, g in df_h.groupby("dix_q", observed=True):
            mean_bps = g[col].mean() * 1e4
            n = len(g)
            stderr_bps = g[col].std() / np.sqrt(n) * 1e4
            tstat = mean_bps / stderr_bps if stderr_bps > 0 else np.nan
            rows.append({"horizon": h, "dix_q": q, "n": n, "mean_bps": mean_bps, "tstat": round(tstat, 2)})
    return pd.DataFrame(rows)


def run_strategy(df: pd.DataFrame, signal: pd.Series, horizon: int, sign: int = +1) -> pd.Series:
    """sign=+1 -> follow-retail; sign=-1 -> fade-retail.

    Strategy holds position 'sign * signal' from close(T) to close(T+horizon).
    Position changes only when signal changes -> we approximate this with daily
    rebalance using next-day return scaled by horizon for a per-day equivalent.
    Concretely: position(T) = sign * signal(T-1); pnl(T) = position(T) * ret(T).
    Costs charged on position changes.
    """
    pos = (sign * signal).shift(1).fillna(0).astype(float)
    pnl = pos * df["ret"]
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * (TXN_COST_BPS / 1e4)
    return pnl - cost


def plot_horizon_grid(grid: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    pivot = grid.pivot(index="dix_q", columns="horizon", values="mean_bps")
    pivot.plot(kind="bar", ax=ax, width=0.8)
    ax.set_ylabel("Mean forward log-return (bps)")
    ax.set_xlabel("DIX quintile (Q1=lowest retail buying ↔ Q5=highest)")
    ax.set_title("Mean forward SPY return by DIX quintile, across horizons\n(2011-2026, n≈3,750 days)")
    ax.axhline(0, color="k", lw=0.5)
    ax.legend(title="Horizon (days)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_strategy_equity(strategies: dict[str, pd.Series], spy_ret: pd.Series, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot((1 + spy_ret).cumprod(), label=f"SPY buy-and-hold (Sh {sharpe(spy_ret):.2f})", color="tab:gray", lw=1.5)
    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]
    for (name, ret), color in zip(strategies.items(), colors):
        ax.plot((1 + ret).cumprod(), label=f"{name} (Sh {sharpe(ret):.2f})", color=color, lw=1.5)
    ax.axvline(pd.Timestamp(OOS_START), color="k", ls="--", lw=0.8, alpha=0.6)
    ax.set_yscale("log")
    ax.set_ylabel("Cumulative return (log)")
    ax.set_title("DIX strategy variants vs SPY buy-and-hold")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> None:
    print("Loading data...")
    gex = load_gex()
    spy = load_spy_returns()
    horizons = [1, 5, 20]
    df = merge(gex, spy, horizons)
    print(f"Merged: {len(df):,} rows, {df.index.min().date()} -> {df.index.max().date()}")

    print("\n=== Horizon grid: mean fwd return (bps) by DIX quintile ===\n")
    grid = horizon_grid(df, horizons)
    print(grid.pivot(index="dix_q", columns="horizon", values="mean_bps").round(1))
    print("\n=== Same grid, t-stats ===\n")
    print(grid.pivot(index="dix_q", columns="horizon", values="tstat"))
    print(f"  (|t| > 2 ≈ p < 0.05 ; |t| > 2.6 ≈ p < 0.01)")

    print("\n=== Backtests ===")
    is_mask = df.index < OOS_START
    oos_mask = df.index >= OOS_START

    methods = [
        ("level th=0.45", "level", {"threshold": 0.45}),
        ("zscore", "zscore", {}),
        ("quantile", "quantile", {}),
        ("ema-cross", "ema-cross", {}),
    ]

    results = []
    print(f"\n  {'Strategy':30s} {'Direction':12s}  {'IS Sh':>7s} {'OOS Sh':>7s} {'Full Sh':>7s} {'MaxDD':>7s} {'Trn/yr':>7s}")
    print(f"  {'-'*30} {'-'*12}  {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7}")
    for label, method, kwargs in methods:
        sig = compute_dix_signal(df, method=method, **kwargs)
        for direction, sign_ in [("follow-retail", +1), ("fade-retail", -1)]:
            ret = run_strategy(df, sig, horizon=1, sign=sign_)
            sh_full = sharpe(ret)
            sh_is = sharpe(ret.loc[is_mask])
            sh_oos = sharpe(ret.loc[oos_mask])
            dd = max_drawdown((1 + ret).cumprod())
            turn = (sign_ * sig).shift(1).fillna(0).diff().abs().mean() * 252
            results.append((label, direction, sh_is, sh_oos, sh_full, dd, turn, ret))
            print(
                f"  {label:30s} {direction:12s}  "
                f"{sh_is:+7.2f} {sh_oos:+7.2f} {sh_full:+7.2f} "
                f"{dd:+7.1%} {turn:7.1f}"
            )

    spy_ret = df["ret"]
    spy_dd = max_drawdown((1 + spy_ret).cumprod())
    print(f"\n  {'SPY buy-and-hold':30s} {'-':12s}  "
          f"{sharpe(spy_ret.loc[is_mask]):+7.2f} {sharpe(spy_ret.loc[oos_mask]):+7.2f} {sharpe(spy_ret):+7.2f} "
          f"{spy_dd:+7.1%}")

    print("\nWriting figures + summary...")
    plot_horizon_grid(grid, FIG_DIR / "dix_horizon_grid.png")
    # Pick best strategies for plot: best follow-retail and best fade-retail
    follow = max([r for r in results if r[1] == "follow-retail"], key=lambda r: r[4])
    fade = max([r for r in results if r[1] == "fade-retail"], key=lambda r: r[4])
    plot_strategy_equity(
        {f"{follow[0]} (follow)": follow[7], f"{fade[0]} (fade)": fade[7]},
        spy_ret,
        FIG_DIR / "dix_strategy_equity.png",
    )

    # Markdown writeup
    out = ROOT / "backtest_results_dix.md"
    grid_pivot = grid.pivot(index="dix_q", columns="horizon", values="mean_bps").round(1)
    tstat_pivot = grid.pivot(index="dix_q", columns="horizon", values="tstat")
    md = [
        "# Phase 2.2 — DIX (retail-positioning) backtest on SPY",
        "",
        f"**Data window:** {df.index.min().date()} → {df.index.max().date()}  ({len(df):,} trading days)",
        f"**OOS start:** {OOS_START}  •  **Round-trip cost:** {TXN_COST_BPS} bps",
        "",
        "## What is DIX?",
        "",
        "SqueezeMetrics' Dark Index (DIX) is a volume-weighted measure of off-exchange short volume / total volume across S&P 500 names. **Higher DIX → less off-exchange shorting → retail buying pressure dominates.** SqueezeMetrics has historically claimed DIX is *bullish* predictive (follow-retail). The internet-meme version is the opposite (fade-retail). We test both.",
        "",
        "## Mean forward SPY return by DIX quintile",
        "",
        "| DIX quintile | 1d (bps) | 5d (bps) | 20d (bps) |",
        "|---|---:|---:|---:|",
    ]
    for q in grid_pivot.index:
        md.append(f"| {q} | {grid_pivot.loc[q, 1]:.1f} | {grid_pivot.loc[q, 5]:.1f} | {grid_pivot.loc[q, 20]:.1f} |")
    md += [
        "",
        "**t-stats (rough significance — |t|>2 is p<0.05, |t|>2.6 is p<0.01):**",
        "",
        "| DIX quintile | 1d | 5d | 20d |",
        "|---|---:|---:|---:|",
    ]
    for q in tstat_pivot.index:
        md.append(f"| {q} | {tstat_pivot.loc[q, 1]:.2f} | {tstat_pivot.loc[q, 5]:.2f} | {tstat_pivot.loc[q, 20]:.2f} |")

    md += [
        "",
        "## Strategy backtest results",
        "",
        "| Signal method | Direction | IS Sharpe | OOS Sharpe | Full Sharpe | Max DD | Turnover/yr |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        label, direction, sh_is, sh_oos, sh_full, dd, turn, _ = r
        md.append(f"| {label} | {direction} | {sh_is:+.2f} | {sh_oos:+.2f} | {sh_full:+.2f} | {dd:+.1%} | {turn:.1f} |")
    md.append(f"| **SPY buy-and-hold** | — | {sharpe(spy_ret.loc[is_mask]):+.2f} | {sharpe(spy_ret.loc[oos_mask]):+.2f} | {sharpe(spy_ret):+.2f} | {spy_dd:+.1%} | — |")

    md += [
        "",
        "## Reading the results",
        "",
        "1. **Direction of effect:** see horizon-grid table above. The pattern of mean returns across DIX quintiles tells us *which interpretation* — follow vs fade — is empirically supported. A monotonic increase Q1→Q5 supports follow; a decrease supports fade.",
        "2. **Statistical significance:** t-stats below ~2 mean the quintile-level effect is indistinguishable from zero. DIX has been heavily marketed by SqueezeMetrics — be skeptical of the level-method backtests if t-stats are weak.",
        "3. **20-day horizon** is most likely to show signal, because retail-flow effects on prices are slow.",
        "4. **Compare against Phase 2.1 GEX result:** if DIX produces equivalent or weaker risk-adjusted returns, the marginal information in retail-flow is captured by the GEX regime indicator alone — no point trading both.",
        "",
        "## Caveats",
        "",
        "- DIX is a SqueezeMetrics-proprietary construction and could have look-ahead in their methodology that we can't audit. The fact that it's free *for free* should make us suspicious of historical curation.",
        "- The follow-retail interpretation is what SqueezeMetrics sells on. If their claim is right, we'd expect a positive Q5-Q1 spread. If retail-fading is right, the opposite.",
        "- Single-asset (SPY) and single-rebalance (daily) — limits how much edge we can extract.",
        "",
        "## Files",
        "",
        "- `figures/dix_horizon_grid.png` — bar chart of mean fwd return by quintile and horizon",
        "- `figures/dix_strategy_equity.png` — best follow + best fade strategy equity vs SPY",
    ]
    out.write_text("\n".join(md) + "\n")
    print(f"  wrote {out}")
    print("Done.")


if __name__ == "__main__":
    main()
