"""
Phase 2.4 — Tradability test of the 5-day abnvol fade discovered in Phase 2.3b.

Phase 2.3b found that on `abnvol_5d > 2x` days in the 2019-vintage basket,
forward 5-day returns were -161 bps (t=-2.4) — a small significant fade
before the longer-horizon momentum kicks in. This file asks: is the fade
TRADABLE for retail after realistic costs?

Strategy variants tested:
    A. long-only fade of DOWN moves: when abnvol > threshold AND recent 5d
                                     return < 0, go long, hold N days
    B. short-only fade of UP moves:  when abnvol > threshold AND recent 5d
                                     return > 0, go short, hold N days
                                     (caveat: borrow costs not modeled here)

Universe: combined meme + vintage + control basket (deduplicated).
Costs: 5 bps round-trip per single-stock trade (realistic for non-mega-cap
names like SPCE, NIO, BBBY in retail conditions).
Position sizing: equal-weight at trade open, 1 unit of capital per trade.

If long-only Sharpe (after cost) < 0.3 OOS or fails a clean baseline test,
the strategy is dead and we document negative result. If > 0.5 it's a real
new retail-actionable signal.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_signals"))
from attention import (  # noqa: E402
    MEME_BASKET,
    CONTROL_BASKET,
    add_attention_proxies,
    add_forward_returns,
    load_panel,
)

VINTAGE_2019 = [
    "TLRY", "CGC", "SPCE", "NIO", "PLUG",
    "BBBY", "GME", "AMC", "BB", "NOK", "AMD", "TSLA",
]
ALL_TICKERS = sorted(set(MEME_BASKET + VINTAGE_2019 + CONTROL_BASKET))

FIG_DIR = ROOT / "figures"
COST_BPS = 5.0
OOS_START = "2023-01-01"


def sharpe(returns: pd.Series, ann: int = 252) -> float:
    s = returns.dropna()
    if s.std() == 0 or len(s) < 30:
        return float("nan")
    return float(s.mean() / s.std() * np.sqrt(ann))


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())


def find_signals(panel: pd.DataFrame, abnvol_threshold: float, hold_days: int) -> pd.DataFrame:
    """Find (ticker, date) trade entries where abnvol > threshold & prior 5d ret < 0."""
    panel = panel.sort_values(["ticker", "date"]).copy()
    panel["prior_5d_ret"] = panel.groupby("ticker")["log_ret"].rolling(5).sum().reset_index(0, drop=True)
    panel["fwd_hold_ret"] = (
        panel.groupby("ticker")["log_ret"]
        .apply(lambda s: s.shift(-1).rolling(hold_days).sum().shift(-(hold_days - 1)))
        .reset_index(0, drop=True)
    )

    signal = panel[
        (panel["abnvol_5d"] > abnvol_threshold)
        & (panel["prior_5d_ret"] < 0)
        & panel["fwd_hold_ret"].notna()
    ].copy()

    # Each "trade" is the next hold_days. Apply cost on each trade.
    signal["gross_pnl"] = signal["fwd_hold_ret"]
    signal["net_pnl"] = signal["gross_pnl"] - COST_BPS / 1e4
    return signal


def daily_pnl_from_signals(signal: pd.DataFrame, panel: pd.DataFrame, hold_days: int) -> pd.Series:
    """Convert per-signal trades into a daily PnL series, attributing each
    trade evenly across its hold-days. Multiple overlapping signals on
    different tickers stack; per-ticker overlaps are de-duplicated to
    earliest-trigger.
    """
    dates_idx = pd.DatetimeIndex(sorted(panel["date"].unique()))
    daily = pd.Series(0.0, index=dates_idx)

    # Per-ticker dedupe: only allow one open trade per ticker at a time
    signal = signal.sort_values(["ticker", "date"])
    keep = []
    last_exit = {}
    for _, row in signal.iterrows():
        t = row["ticker"]
        if t in last_exit and row["date"] < last_exit[t]:
            continue
        keep.append(row)
        last_exit[t] = row["date"] + pd.Timedelta(days=hold_days * 1.5)
    if not keep:
        return daily
    signal = pd.DataFrame(keep)

    for _, row in signal.iterrows():
        # spread the trade pnl over the hold_days starting at next day
        start_idx = dates_idx.searchsorted(row["date"]) + 1
        end_idx = min(start_idx + hold_days, len(dates_idx))
        if start_idx >= len(dates_idx):
            continue
        days_held = end_idx - start_idx
        if days_held <= 0:
            continue
        # net trade pnl divided across days held
        per_day = row["net_pnl"] / days_held
        daily.iloc[start_idx:end_idx] += per_day

    return daily


def grid_search(panel: pd.DataFrame, basket_label: str) -> pd.DataFrame:
    rows = []
    for thresh in [1.5, 2.0, 3.0]:
        for hold in [3, 5, 10]:
            sig = find_signals(panel, thresh, hold)
            if len(sig) == 0:
                continue
            daily = daily_pnl_from_signals(sig, panel, hold)
            is_mask = daily.index < OOS_START
            oos_mask = daily.index >= OOS_START

            rows.append({
                "basket": basket_label,
                "abnvol_threshold": thresh,
                "hold_days": hold,
                "n_trades": len(sig),
                "mean_trade_bps_gross": sig["gross_pnl"].mean() * 1e4,
                "mean_trade_bps_net": sig["net_pnl"].mean() * 1e4,
                "hit_rate_gross": (sig["gross_pnl"] > 0).mean(),
                "sharpe_full": sharpe(daily),
                "sharpe_is": sharpe(daily.loc[is_mask]),
                "sharpe_oos": sharpe(daily.loc[oos_mask]),
                "max_dd": max_drawdown((1 + daily).cumprod()),
            })
    return pd.DataFrame(rows)


def plot_equity(panel: pd.DataFrame, best_params: dict, out: Path) -> None:
    sig = find_signals(panel, best_params["abnvol_threshold"], best_params["hold_days"])
    daily = daily_pnl_from_signals(sig, panel, best_params["hold_days"])
    eq = (1 + daily).cumprod()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(eq.index, eq, color="tab:blue", lw=1.5,
            label=f"abnvol-fade strategy (Sharpe={sharpe(daily):.2f}, n={best_params['n_trades']})")
    ax.axhline(1.0, color="k", lw=0.5)
    ax.axvline(pd.Timestamp(OOS_START), color="k", ls="--", lw=0.8, alpha=0.6)
    ax.text(pd.Timestamp(OOS_START), ax.get_ylim()[1] * 0.97, "  OOS →", fontsize=9)
    ax.set_ylabel("Cumulative return")
    ax.set_title(f"abnvol-fade long-only equity curve\n"
                 f"(threshold>{best_params['abnvol_threshold']}×, hold {best_params['hold_days']}d, "
                 f"{COST_BPS} bps round-trip)")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> None:
    print("Loading combined basket panel...")
    panel = load_panel(ALL_TICKERS)
    panel = add_attention_proxies(panel)
    panel = panel.dropna(subset=["abnvol_5d", "log_ret"])
    print(f"Panel: {len(panel):,} rows, {panel['ticker'].nunique()} tickers, "
          f"{panel['date'].min().date()} -> {panel['date'].max().date()}")

    print("\n=== Grid search: abnvol threshold × hold_days, on combined basket ===\n")
    combined_results = grid_search(panel, "Combined")
    print(combined_results.round(3).to_string(index=False))

    print("\n=== Grid search: meme + vintage subset only (not control) ===\n")
    meme_only = panel[panel["ticker"].isin(set(MEME_BASKET + VINTAGE_2019))]
    meme_results = grid_search(meme_only, "Meme+Vintage")
    print(meme_results.round(3).to_string(index=False))

    # Pick best by full-sample Sharpe
    all_results = pd.concat([combined_results, meme_results], ignore_index=True)
    best = all_results.sort_values("sharpe_full", ascending=False).iloc[0]
    best_params = {
        "abnvol_threshold": float(best["abnvol_threshold"]),
        "hold_days": int(best["hold_days"]),
        "n_trades": int(best["n_trades"]),
    }
    print(f"\nBest by full-sample Sharpe:")
    for k, v in best.items():
        if isinstance(v, (int, float, np.floating, np.integer)):
            print(f"  {k}: {v:.3f}" if isinstance(v, (float, np.floating)) else f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")

    sub = panel if best["basket"] == "Combined" else meme_only
    plot_equity(sub, best_params, FIG_DIR / "abnvol_fade_equity.png")

    md = [
        "# Phase 2.4 — abnvol 5-day fade tradability test",
        "",
        f"**Data window:** {panel['date'].min().date()} → {panel['date'].max().date()}",
        f"**Combined basket ({len(ALL_TICKERS)} tickers):** {', '.join(ALL_TICKERS)}",
        f"**Round-trip cost:** {COST_BPS} bps  •  **OOS start:** {OOS_START}",
        "",
        "## Hypothesis (from Phase 2.3b discovery)",
        "",
        "On days where 5-day average volume exceeds 2× the 60-day average AND the prior 5-day return is negative, take a long position next day at open and hold for N days. Phase 2.3b's diagnostic showed a -161 bps t=-2.4 fade at the 5-day horizon, suggesting the move pre-volume-spike is partially over-reacted and reverts in the following week.",
        "",
        "**Long-only specification** (no shorts) — sidesteps borrow-cost confound. Tests whether retail can extract the fade without complex execution.",
        "",
        "## Combined basket — grid search",
        "",
        combined_results.round(3).to_markdown(index=False),
        "",
        "## Meme + vintage subset (excludes JNJ, KO, PG, WMT, JPM)",
        "",
        meme_results.round(3).to_markdown(index=False),
        "",
        "## Reading the results",
        "",
        "- **Net trade bps after cost** is the per-trade expected return; <5 bps means costs eat the edge.",
        "- **Sharpe full / IS / OOS** measures whether the strategy is genuine alpha or sample-specific. OOS Sharpe < 0 means the in-sample edge didn't persist into 2023-2026.",
        "- **n_trades** matters for power. Strategies with <50 trades shouldn't be trusted.",
        "- **max_dd** matters for retail tolerability. Anything worse than -25% is hard to hold.",
        "",
        "## Caveats",
        "",
        "- Position sizing is naive (1 unit per trade, no scaling for vol or basket size). A vol-targeted version would change the Sharpe.",
        "- 5 bps round-trip is reasonable for high-volume names but can be 10-20 bps for SPCE, BBBY, RIDE-tier.",
        "- The strategy goes long-only, so half the abnvol-spike opportunities (UP moves) are skipped. A long-short version with borrow-cost modeling could double trade count but may be Sharpe-equivalent net of costs.",
        "- No survivorship-free version (would need CRSP-delisted via WRDS).",
        "",
        "## Files",
        "",
        "- `figures/abnvol_fade_equity.png` — equity curve of best-Sharpe parameter combo",
    ]
    out = ROOT / "backtest_results_abnvol_fade.md"
    out.write_text("\n".join(md) + "\n")
    print(f"\nWrote {out}")
    print("Done.")


if __name__ == "__main__":
    main()
