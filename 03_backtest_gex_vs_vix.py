"""
Phase 2.5 — Does GEX carry independent info beyond VIX?

Phase 2.1 established that GEX-based defensive tilt produces OOS Sharpe 0.82
with MaxDD -22%, vs SPY's Sharpe 0.90 / MaxDD -34%. But GEX and VIX are
highly correlated (both reflect market stress). Critical robustness question:

    Is the GEX rule's edge ACTUALLY about dealer positioning, or is it
    just a complicated proxy for "VIX is high, get defensive"?

If a simple VIX-threshold rule produces the same Sharpe / MaxDD as the GEX
rule, the dealer-flow narrative collapses — we should retire GEX in favor
of VIX (simpler, free everywhere, no vendor risk on SqueezeMetrics).

If GEX strictly dominates, or the two-signal combination dominates either
solo, then GEX carries information beyond vol expectations and the dealer-
flow story is empirically supported.

Strategies tested (all daily, long SPY or flat, 1bp round-trip cost):
    A. VIX-only:  long if VIX < threshold, else flat
    B. GEX-only:  long if GEX > 0, else flat            (the original Rule #1)
    C. AND-rule:  long only if VIX low AND GEX positive (most defensive)
    D. OR-rule:   flat if VIX high OR GEX negative      (any-trigger defensive)
    E. GEX residualized for VIX: regress GEX on VIX, use sign of residual
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_signals"))
from gex import load_gex  # noqa: E402

# Reuse helpers from main backtest
from importlib.util import spec_from_file_location, module_from_spec  # noqa: E402

_spec = spec_from_file_location("backtest_lib", ROOT / "03_backtest.py")
_bt = module_from_spec(_spec)
_spec.loader.exec_module(_bt)
sharpe = _bt.sharpe
max_drawdown = _bt.max_drawdown
load_spy_returns = _bt.load_spy_returns
apply_costs = _bt.apply_costs

FIG_DIR = ROOT / "figures"
OOS_START = "2021-01-01"
TXN_COST_BPS = 1.0


def load_vix() -> pd.DataFrame:
    cache = ROOT / "data" / "cache" / "vix.parquet"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        return pd.read_parquet(cache)
    vix = yf.download("^VIX", start="2010-01-01", auto_adjust=True, progress=False)
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
    vix.index.name = "date"
    vix.to_parquet(cache)
    return vix


def merge_all(gex: pd.DataFrame, spy: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    df = gex.join(spy[["Close", "ret", "fwd_ret"]], how="inner", rsuffix="_spy")
    df = df.join(vix[["Close"]].rename(columns={"Close": "vix"}), how="inner")
    return df.dropna(subset=["fwd_ret", "vix", "gex"])


def build_strategies(df: pd.DataFrame, vix_threshold: float) -> dict[str, pd.Series]:
    """Each returns a position series (1.0 = long SPY, 0.0 = flat)."""
    pos = {}
    pos["SPY buy-and-hold"] = pd.Series(1.0, index=df.index)
    # A. VIX-only
    pos["VIX-only (long if VIX<{})".format(vix_threshold)] = (df["vix"] < vix_threshold).astype(float)
    # B. GEX-only (the original Rule #1)
    pos["GEX-only (long if GEX>0)"] = (df["gex"] > 0).astype(float)
    # C. AND-rule (most defensive)
    pos["AND (both VIX low AND GEX>0)"] = ((df["vix"] < vix_threshold) & (df["gex"] > 0)).astype(float)
    # D. OR-rule (any-trigger defensive)
    pos["OR (VIX low OR GEX>0)"] = ((df["vix"] < vix_threshold) | (df["gex"] > 0)).astype(float)
    # E. Residualized GEX
    # Fit GEX = a + b * VIX (using IS data only to avoid leakage)
    is_df = df.loc[df.index < OOS_START]
    if len(is_df) > 100:
        b = np.cov(is_df["gex"], is_df["vix"])[0, 1] / np.var(is_df["vix"])
        a = is_df["gex"].mean() - b * is_df["vix"].mean()
        residual = df["gex"] - (a + b * df["vix"])
        pos["GEX residualized for VIX (long if resid>0)"] = (residual > 0).astype(float)
    return pos


def evaluate(positions: dict[str, pd.Series], df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    is_mask = df.index < OOS_START
    oos_mask = df.index >= OOS_START
    for name, pos in positions.items():
        ret = apply_costs(pos, df["fwd_ret"], TXN_COST_BPS)
        eq = (1 + ret).cumprod()
        rows.append({
            "strategy": name,
            "sharpe_is":   sharpe(ret.loc[is_mask]),
            "sharpe_oos":  sharpe(ret.loc[oos_mask]),
            "sharpe_full": sharpe(ret),
            "max_dd":      max_drawdown(eq),
            "pct_long":    pos.mean() * 100,
            "turnover_yr": pos.diff().abs().mean() * 252,
        })
    return pd.DataFrame(rows)


def correlation_diagnostics(df: pd.DataFrame) -> dict:
    """Quantify how informationally distinct GEX and VIX are."""
    corr_levels = df["gex"].corr(df["vix"])
    # log-transform for VIX (vol is log-distributed) and signed-log for GEX
    log_vix = np.log(df["vix"])
    sign_log_gex = np.sign(df["gex"]) * np.log1p(np.abs(df["gex"]))
    corr_logged = sign_log_gex.corr(log_vix)
    # What fraction of negative-GEX days also have VIX > 25?
    neg_gex_days = df[df["gex"] < 0]
    return {
        "corr_levels": corr_levels,
        "corr_logged": corr_logged,
        "n_neg_gex_days": int(len(neg_gex_days)),
        "neg_gex_with_vix_gt_25_pct": float((neg_gex_days["vix"] > 25).mean() * 100),
        "neg_gex_with_vix_gt_20_pct": float((neg_gex_days["vix"] > 20).mean() * 100),
        "vix_gt_25_with_neg_gex_pct": float((df.loc[df["vix"] > 25, "gex"] < 0).mean() * 100),
        "vix_gt_25_total_days": int((df["vix"] > 25).sum()),
    }


def plot_equity_comparison(positions: dict[str, pd.Series], df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    colors = {
        "SPY buy-and-hold": "tab:gray",
        "VIX-only (long if VIX<25)": "tab:orange",
        "GEX-only (long if GEX>0)": "tab:blue",
        "AND (both VIX low AND GEX>0)": "tab:green",
        "OR (VIX low OR GEX>0)": "tab:red",
        "GEX residualized for VIX (long if resid>0)": "tab:purple",
    }
    for name, pos in positions.items():
        ret = apply_costs(pos, df["fwd_ret"], TXN_COST_BPS)
        eq = (1 + ret).cumprod()
        sh = sharpe(ret)
        dd = max_drawdown(eq)
        col = colors.get(name, "k")
        lw = 1.8 if name == "GEX-only (long if GEX>0)" else 1.2
        ax.plot(eq.index, eq, label=f"{name} (Sh {sh:.2f}, DD {dd:.0%})",
                color=col, lw=lw, alpha=0.85)
    ax.axvline(pd.Timestamp(OOS_START), color="k", ls="--", lw=0.8, alpha=0.5)
    ax.set_yscale("log")
    ax.set_ylabel("Cumulative return (log)")
    ax.set_title("GEX vs VIX vs combined defensive tilts on SPY\n(daily, 1bp cost)")
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_scatter(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["vix"], df["gex"] / 1e9, s=4, alpha=0.3, c="tab:gray")
    neg = df[df["gex"] < 0]
    ax.scatter(neg["vix"], neg["gex"] / 1e9, s=8, alpha=0.8, c="tab:red", label=f"Neg-GEX (n={len(neg)})")
    ax.axhline(0, color="k", lw=0.5)
    ax.axvline(25, color="tab:orange", ls="--", lw=0.8, label="VIX = 25")
    ax.axvline(20, color="tab:orange", ls=":", lw=0.8, label="VIX = 20")
    ax.set_xlabel("VIX")
    ax.set_ylabel("Dealer GEX ($B per 1% spot)")
    ax.set_title("VIX vs GEX scatter (daily, 2011-2026)\n"
                 "If GEX is just a VIX proxy, all neg-GEX dots would be at high VIX")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> None:
    print("Loading GEX, SPY, VIX...")
    gex = load_gex()
    spy = load_spy_returns()
    vix = load_vix()
    df = merge_all(gex, spy, vix)
    print(f"Merged: {len(df):,} rows, {df.index.min().date()} -> {df.index.max().date()}")

    diag = correlation_diagnostics(df)
    print("\n=== Correlation diagnostics ===")
    print(f"  corr(GEX, VIX) levels:           {diag['corr_levels']:+.3f}")
    print(f"  corr(signed-log-GEX, log-VIX):   {diag['corr_logged']:+.3f}")
    print(f"  Negative-GEX days with VIX>25:   {diag['neg_gex_with_vix_gt_25_pct']:.0f}%   (n={diag['n_neg_gex_days']} neg-GEX days)")
    print(f"  Negative-GEX days with VIX>20:   {diag['neg_gex_with_vix_gt_20_pct']:.0f}%")
    print(f"  VIX>25 days with negative GEX:   {diag['vix_gt_25_with_neg_gex_pct']:.0f}%   (n={diag['vix_gt_25_total_days']} VIX>25 days)")

    print("\n=== Strategy comparison @ VIX threshold = 25 ===")
    strategies = build_strategies(df, vix_threshold=25.0)
    res_25 = evaluate(strategies, df)
    print(res_25.round(3).to_string(index=False))

    print("\n=== Strategy comparison @ VIX threshold = 20 ===")
    strategies_20 = build_strategies(df, vix_threshold=20.0)
    res_20 = evaluate(strategies_20, df)
    print(res_20.round(3).to_string(index=False))

    print("\nWriting figures + summary...")
    plot_equity_comparison(strategies, df, FIG_DIR / "gex_vs_vix_equity.png")
    plot_scatter(df, FIG_DIR / "gex_vs_vix_scatter.png")

    md = [
        "# Phase 2.5 — Does GEX carry information beyond VIX?",
        "",
        f"**Data window:** {df.index.min().date()} → {df.index.max().date()}  ({len(df):,} trading days)",
        f"**OOS start:** {OOS_START}  •  **Round-trip cost:** {TXN_COST_BPS} bps",
        "",
        "## The question",
        "",
        "Phase 2.1's GEX defensive tilt works (OOS Sharpe 0.82, MaxDD -22% vs SPY's -34%). But VIX and GEX are correlated — both rise during stress. **Is the GEX rule's edge actually about dealer positioning, or is it just a complicated VIX proxy?** If a simple VIX rule produces the same result, we should retire GEX (vendor risk, complexity) and use VIX (free everywhere, transparent).",
        "",
        "## Correlation diagnostics",
        "",
        f"- **corr(GEX, VIX) levels:** `{diag['corr_levels']:+.3f}`",
        f"- **corr(signed-log-GEX, log-VIX):** `{diag['corr_logged']:+.3f}` (more linear after transformation)",
        f"- **Negative-GEX days with VIX > 25:** {diag['neg_gex_with_vix_gt_25_pct']:.0f}% (of {diag['n_neg_gex_days']} neg-GEX days)",
        f"- **Negative-GEX days with VIX > 20:** {diag['neg_gex_with_vix_gt_20_pct']:.0f}%",
        f"- **VIX > 25 days with negative GEX:** {diag['vix_gt_25_with_neg_gex_pct']:.0f}% (of {diag['vix_gt_25_total_days']} VIX>25 days)",
        "",
        "**Initial read:** GEX and VIX are correlated but NOT identical. The asymmetry between the two conditioning probabilities reveals where they disagree.",
        "",
        "## Strategy comparison (VIX threshold = 25)",
        "",
        res_25.round(3).to_markdown(index=False),
        "",
        "## Strategy comparison (VIX threshold = 20)",
        "",
        res_20.round(3).to_markdown(index=False),
        "",
        "## Reading the results",
        "",
        "Compare strategies on **two dimensions**:",
        "1. **OOS Sharpe** — does the strategy survive into 2021-2026?",
        "2. **Max DD** — does it deliver path improvement vs SPY?",
        "",
        "Three possible findings:",
        "- **VIX-only ≥ GEX-only on both metrics**: GEX is redundant. Retire it. Use VIX. Simpler, more transparent, no SqueezeMetrics dependency.",
        "- **GEX-only > VIX-only**: GEX carries info beyond vol level. Dealer-flow story is supported. Keep Rule #1.",
        "- **Combined (AND or OR or residualized) > either solo**: GEX and VIX are complementary. Best operational rule combines them.",
        "",
        "## Files",
        "",
        "- `figures/gex_vs_vix_equity.png` — equity curves of all 6 strategies",
        "- `figures/gex_vs_vix_scatter.png` — VIX vs GEX scatter; reveals where the two indicators disagree",
        "",
        "## Implication for the playbook",
        "",
        "If GEX adds incremental info, Rule #1 stays as written. If VIX-only is just as good, the playbook should be updated to use VIX (free, ubiquitous, no vendor risk). If combined dominates, the runner script should incorporate both signals.",
    ]
    out = ROOT / "backtest_results_gex_vs_vix.md"
    out.write_text("\n".join(md) + "\n")
    print(f"  wrote {out}")
    print("Done.")


if __name__ == "__main__":
    main()
