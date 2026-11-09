"""
Phase 2.6 — Does a continuous version of Rule #1 beat the binary OR rule?

Phase 2.5 settled on binary OR: long 100% UNLESS (VIX>25 AND GEX<0).
OOS Sharpe 0.89, MaxDD -22%, turnover ~8/yr.

Possible refinements:
    A. Three-state: 100% if both calm, 50% if exactly one stress, 0% if double stress
    B. Smooth logistic: position = sigmoid(linear combo of -vix_z and gex_z)
    C. Vol-targeted: scale position inversely with realized vol (10d), capped 0-1

If any of these beats binary on a clear metric (Sharpe, MaxDD, or turnover/whipsaw)
without losing on others, update Rule #1 + daily_signal.py. Otherwise document
the result and stick with binary (simpler to execute).

Output: figures/continuous_rule1_comparison.png, backtest_results_continuous_rule1.md

Run: python 03_backtest_continuous_rule1.py [--lag N]
    --lag 1 (default): realistic timing -- every variant's position (including
             the vol-targeted one) is delayed one extra day because GEX is
             published after the close (see 03_backtest.py). Writes
             backtest_results_continuous_rule1_lag1.md + figures/*_lag1.png.
    --lag 0: reproduces the committed backtest_results_continuous_rule1.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_signals"))
from gex import load_gex  # noqa: E402

from importlib.util import spec_from_file_location, module_from_spec  # noqa: E402

_spec_bt = spec_from_file_location("backtest_lib", ROOT / "03_backtest.py")
_bt = module_from_spec(_spec_bt)
_spec_bt.loader.exec_module(_bt)
sharpe = _bt.sharpe
max_drawdown = _bt.max_drawdown
load_spy_returns = _bt.load_spy_returns
apply_costs = _bt.apply_costs
lag_positions = _bt.lag_positions
lag_suffix = _bt.lag_suffix
lag_header_lines = _bt.lag_header_lines
add_lag_arg = _bt.add_lag_arg
BUY_AND_HOLD = _bt.BUY_AND_HOLD

_spec_vix = spec_from_file_location("gv_lib", ROOT / "03_backtest_gex_vs_vix.py")
_gv = module_from_spec(_spec_vix)
_spec_vix.loader.exec_module(_gv)
load_vix = _gv.load_vix
merge_all = _gv.merge_all

FIG_DIR = ROOT / "figures"
OOS_START = "2021-01-01"
TXN_COST_BPS = 1.0
VIX_THRESHOLD = 25.0


def position_binary_or(df: pd.DataFrame) -> pd.Series:
    """The Phase 2.5 winner — long unless (VIX>25 AND GEX<0)."""
    return (~((df["vix"] > VIX_THRESHOLD) & (df["gex"] < 0))).astype(float)


def position_three_state(df: pd.DataFrame) -> pd.Series:
    """100% calm, 50% single-stress, 0% double-stress."""
    vix_stress = df["vix"] > VIX_THRESHOLD
    gex_stress = df["gex"] < 0
    pos = pd.Series(1.0, index=df.index)
    pos[vix_stress ^ gex_stress] = 0.5  # XOR — exactly one stressed
    pos[vix_stress & gex_stress] = 0.0
    return pos


def position_smooth_logistic(df: pd.DataFrame, k: float = 1.5) -> pd.Series:
    """Combine vix_z and gex_z into a single stress score, then sigmoid.

    Lower score = more stressed = lower position. k controls sharpness.
    Calibrated using rolling 1y stats to avoid lookahead.
    """
    vix_roll = df["vix"].rolling(252, min_periods=60)
    gex_roll = df["gex"].rolling(252, min_periods=60)
    vix_z = (df["vix"] - vix_roll.mean()) / vix_roll.std()
    gex_z = (df["gex"] - gex_roll.mean()) / gex_roll.std()
    # Stress score: high when VIX is high OR GEX is low (signs aligned with "calmness")
    calm_score = -vix_z + gex_z  # higher = more calm
    pos = 1 / (1 + np.exp(-k * calm_score))
    return pos.fillna(1.0).clip(0.0, 1.0)


def position_vol_targeted(df: pd.DataFrame, target_vol: float = 0.10) -> pd.Series:
    """Scale exposure inversely to realized vol, with hard floor at 0 in double-stress.

    Position = min(1, target_vol / realized_vol_10d_annualized), zeroed if double stress.
    """
    realized_vol = df["ret"].rolling(10, min_periods=5).std() * np.sqrt(252)
    pos = (target_vol / realized_vol).clip(0, 1).fillna(1.0)
    double_stress = (df["vix"] > VIX_THRESHOLD) & (df["gex"] < 0)
    pos[double_stress] = 0.0
    return pos


def evaluate(positions: dict[str, pd.Series], df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    is_mask = df.index < OOS_START
    oos_mask = df.index >= OOS_START
    for name, pos in positions.items():
        ret = apply_costs(pos, df["fwd_ret"], TXN_COST_BPS)
        eq = (1 + ret).cumprod()
        # turnover: average daily position change
        daily_change = pos.diff().abs()
        rows.append({
            "strategy": name,
            "sharpe_is":   sharpe(ret.loc[is_mask]),
            "sharpe_oos":  sharpe(ret.loc[oos_mask]),
            "sharpe_full": sharpe(ret),
            "max_dd":      max_drawdown(eq),
            "avg_pos":     pos.mean(),
            "pos_std":     pos.std(),
            "turnover_yr": daily_change.mean() * 252,
            "n_changes":   int((daily_change > 0.01).sum()),
        })
    return pd.DataFrame(rows)


def plot_equity(positions: dict[str, pd.Series], df: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})

    colors = {
        "SPY buy-and-hold": "tab:gray",
        "Binary OR (Rule #1)": "tab:blue",
        "Three-state (1 / 0.5 / 0)": "tab:green",
        "Smooth logistic (k=1.5)": "tab:purple",
        "Vol-targeted (10% target)": "tab:orange",
    }
    for name, pos in positions.items():
        ret = apply_costs(pos, df["fwd_ret"], TXN_COST_BPS)
        eq = (1 + ret).cumprod()
        col = colors.get(name, "k")
        lw = 1.6 if name == "Binary OR (Rule #1)" else 1.2
        axes[0].plot(eq.index, eq, label=f"{name} (Sh {sharpe(ret):.2f}, DD {max_drawdown(eq):.0%})",
                     color=col, lw=lw, alpha=0.85)
    axes[0].axvline(pd.Timestamp(OOS_START), color="k", ls="--", lw=0.8, alpha=0.5)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Cumulative return (log)")
    axes[0].set_title("Continuous variants of Rule #1 vs SPY buy-and-hold")
    axes[0].legend(loc="upper left", fontsize=9)

    # Position trace for the smooth logistic so user sees the dynamic
    smooth = positions.get("Smooth logistic (k=1.5)")
    if smooth is not None:
        axes[1].plot(smooth.index, smooth, color="tab:purple", lw=0.8, alpha=0.7,
                     label="Smooth logistic position (0-1)")
    binary = positions.get("Binary OR (Rule #1)")
    if binary is not None:
        axes[1].plot(binary.index, binary, color="tab:blue", lw=0.8, alpha=0.5,
                     label="Binary OR position (0/1)")
    axes[1].set_ylabel("Position weight")
    axes[1].set_ylim(-0.05, 1.1)
    axes[1].axhline(1.0, color="k", lw=0.4)
    axes[1].axhline(0.0, color="k", lw=0.4)
    axes[1].axvline(pd.Timestamp(OOS_START), color="k", ls="--", lw=0.8, alpha=0.5)
    axes[1].legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main(lag: int = 1) -> None:
    sfx = lag_suffix(lag)
    print(f"Loading GEX, SPY, VIX...  (signal lag = {lag} day(s))")
    gex = load_gex()
    spy = load_spy_returns()
    vix = load_vix()
    df = merge_all(gex, spy, vix)
    print(f"Merged: {len(df):,} rows, {df.index.min().date()} -> {df.index.max().date()}")

    positions = {
        BUY_AND_HOLD:               pd.Series(1.0, index=df.index),
        "Binary OR (Rule #1)":      position_binary_or(df),
        "Three-state (1 / 0.5 / 0)": position_three_state(df),
        "Smooth logistic (k=1.5)":  position_smooth_logistic(df, k=1.5),
        "Vol-targeted (10% target)": position_vol_targeted(df, target_vol=0.10),
    }
    # The timing lag enters the pipeline here and only here: every variant
    # (vol-targeted included, buy-and-hold excluded) is shifted `lag` days
    # before evaluate()/plot_equity multiply it by fwd_ret.
    positions = lag_positions(positions, lag)

    print("\n=== Comparison ===\n")
    res = evaluate(positions, df)
    print(res.round(3).to_string(index=False))

    plot_equity(positions, df, FIG_DIR / f"continuous_rule1_comparison{sfx}.png")

    md = [
        "# Phase 2.6 — Continuous variants of Rule #1",
        "",
        f"**Data window:** {df.index.min().date()} → {df.index.max().date()}  ({len(df):,} trading days)",
        f"**OOS start:** {OOS_START}  •  **Round-trip cost:** {TXN_COST_BPS} bps",
        *lag_header_lines(lag),
        "## Question",
        "",
        "Phase 2.5's binary OR rule (long unless VIX>25 AND GEX<0) is the playbook headline at OOS Sharpe 0.89 and MaxDD -22%. Can a continuous variant — three-state, smooth-logistic, or vol-targeted — improve on Sharpe, drawdown, OR turnover (whipsaw) without losing the others?",
        "",
        "Operational tradeoff: binary is trivial to execute (buy or sell SPY in full). Continuous requires fractional sizing each day (extra discretion + rounding to share counts). Continuous wins only if the stat improvement is worth the extra discipline cost.",
        "",
        "## Variants tested",
        "",
        "1. **Binary OR (Rule #1)** — long 1.0 unless double-stress, then 0.0. The Phase 2.5 winner.",
        "2. **Three-state** — long 1.0 if both calm, 0.5 if exactly one signal stresses, 0.0 if both. Operationally manageable (only three position levels).",
        "3. **Smooth logistic (k=1.5)** — position = sigmoid(k · (-vix_z + gex_z)). Fully continuous; rolling 1y z-scores.",
        "4. **Vol-targeted (10% target)** — position = min(1, 10% / realized_vol_10d), zeroed in double-stress.",
        "",
        "## Results",
        "",
        res.round(3).to_markdown(index=False),
        "",
        "## Files",
        "",
        f"- `figures/continuous_rule1_comparison{sfx}.png` — equity curves (top) + position traces (bottom) for binary vs smooth logistic",
        "",
        "## Reading and decision",
        "",
        "Compare on three axes:",
        "- **OOS Sharpe** — does it beat binary's 0.89?",
        "- **Max DD** — does it beat binary's -22%?",
        "- **Turnover** — does it cut binary's ~8/yr (which is already very low)?",
        "",
        "If any continuous variant clearly dominates, update Rule #1 + `daily_signal.py`. If they tie or lose on stats while complicating execution, **stick with binary** — KISS principle for retail.",
    ]
    out = ROOT / f"backtest_results_continuous_rule1{sfx}.md"
    out.write_text("\n".join(md) + "\n")
    print(f"\nWrote {out}")
    print("Done.")


if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description="Phase 2.6 continuous Rule #1 variants")
    add_lag_arg(_parser)
    main(lag=_parser.parse_args().lag)
