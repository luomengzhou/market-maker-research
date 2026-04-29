"""
Phase 2.3 — Barber-Odean attention-fade reproduction on a meme-stock basket.

Tests whether single-stock attention extremes predict forward underperformance,
which is the academic-literature basis for Rule #2 in the retail playbook.

Three attention proxies, each tested for fwd-return effect at 5d/21d/63d:
    1. mom_21d_extreme: top-decile trailing 21d return  (high prior-period winner)
    2. abnvol_spike:    5d avg vol > 2x 60d avg vol     (volume attention spike)
    3. one_day_shock:   |yesterday return| > 3 sigma    (extreme one-day move)

For each: compare forward returns of "attention-extreme" group vs the rest.
Run separately on:
    - Meme basket (NVDA, TSLA, GME, AMC, ...) — where the effect should be strong
    - Control basket (JNJ, KO, PG, ...)        — where it should be weak/absent

Outputs:
    figures/attention_fade_grid.png      bar chart by proxy x horizon x basket
    backtest_results_attention.md        narrative writeup
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

FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(exist_ok=True)
HORIZONS = [5, 21, 63]


def conditional_returns(
    panel: pd.DataFrame,
    proxy_col: str,
    threshold_fn,
    label: str,
) -> pd.DataFrame:
    """For each horizon, compute mean forward return of:
        - attention-extreme rows (threshold_fn returns True)
        - rest (threshold_fn returns False)
    plus n, t-stat of the difference.
    """
    rows = []
    panel = panel.copy()
    panel["is_extreme"] = threshold_fn(panel[proxy_col])
    for h in HORIZONS:
        col = f"fwd_ret_{h}d"
        df = panel.dropna(subset=[col, "is_extreme"])
        ext = df.loc[df["is_extreme"], col]
        rest = df.loc[~df["is_extreme"], col]
        if len(ext) < 30 or len(rest) < 30:
            rows.append({"horizon": h, "proxy": label, "n_ext": len(ext), "n_rest": len(rest),
                         "ext_bps": np.nan, "rest_bps": np.nan, "diff_bps": np.nan, "tstat": np.nan})
            continue
        # Welch t-stat for ext vs rest
        m_ext, m_rest = ext.mean(), rest.mean()
        v_ext, v_rest = ext.var(), rest.var()
        n_ext, n_rest = len(ext), len(rest)
        se = np.sqrt(v_ext / n_ext + v_rest / n_rest)
        tstat = (m_ext - m_rest) / se if se > 0 else np.nan
        rows.append({
            "horizon": h,
            "proxy": label,
            "n_ext": n_ext,
            "n_rest": n_rest,
            "ext_bps": m_ext * 1e4,
            "rest_bps": m_rest * 1e4,
            "diff_bps": (m_ext - m_rest) * 1e4,
            "tstat": tstat,
        })
    return pd.DataFrame(rows)


def run_basket(panel: pd.DataFrame, basket_name: str) -> pd.DataFrame:
    print(f"\n=== {basket_name} basket ===")
    print(f"  Tickers: {panel['ticker'].nunique()}  Rows: {len(panel):,}")

    results = []
    # Proxy 1: top-decile trailing 21d return per ticker (i.e., big winners get faded)
    threshold_mom = lambda s: s > s.quantile(0.9)  # 90th percentile within basket
    results.append(conditional_returns(panel, "mom_21d", threshold_mom, "mom_21d_top10pct"))
    # Proxy 2: abnvol > 2x
    results.append(conditional_returns(panel, "abnvol_5d", lambda s: s > 2.0, "abnvol_5d_>2x"))
    # Proxy 3: |yesterday's return| > 3 sigma
    results.append(conditional_returns(panel, "extreme_1d", lambda s: s > 3.0, "extreme_1d_>3sigma"))

    out = pd.concat(results, ignore_index=True)
    out["basket"] = basket_name
    print(out.to_string(index=False))
    return out


def plot_results(meme_res: pd.DataFrame, ctrl_res: pd.DataFrame, out: Path) -> None:
    proxies = meme_res["proxy"].unique()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)

    width = 0.35
    x_pos = np.arange(len(HORIZONS))
    for ax, proxy in zip(axes, proxies):
        m = meme_res[meme_res["proxy"] == proxy].set_index("horizon")
        c = ctrl_res[ctrl_res["proxy"] == proxy].set_index("horizon")
        ax.bar(x_pos - width / 2, m.loc[HORIZONS, "diff_bps"], width, color="tab:red",
               label="Meme basket", alpha=0.85)
        ax.bar(x_pos + width / 2, c.loc[HORIZONS, "diff_bps"], width, color="tab:gray",
               label="Control basket", alpha=0.85)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([f"{h}d" for h in HORIZONS])
        ax.set_title(proxy)
        ax.set_ylabel("Forward return: extreme - rest (bps)" if proxy == proxies[0] else "")
        for j, h in enumerate(HORIZONS):
            t_m = m.loc[h, "tstat"]
            t_c = c.loc[h, "tstat"]
            ax.text(x_pos[j] - width / 2, m.loc[h, "diff_bps"], f"t={t_m:.1f}",
                    ha="center", va="bottom" if m.loc[h, "diff_bps"] > 0 else "top", fontsize=8)
            ax.text(x_pos[j] + width / 2, c.loc[h, "diff_bps"], f"t={t_c:.1f}",
                    ha="center", va="bottom" if c.loc[h, "diff_bps"] > 0 else "top", fontsize=8)

    axes[0].legend(loc="lower right")
    fig.suptitle("Attention-fade test: forward return spread (extreme group − rest), by proxy and horizon\n"
                 "Negative bars support the fade hypothesis; meme basket should show stronger effect than control",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fmt_results(df: pd.DataFrame) -> str:
    out = df.copy()
    for c in ["ext_bps", "rest_bps", "diff_bps"]:
        out[c] = out[c].round(1)
    out["tstat"] = out["tstat"].round(2)
    return out.to_markdown(index=False)


def main() -> None:
    print("Loading meme + control panel...")
    all_tickers = MEME_BASKET + CONTROL_BASKET
    panel = load_panel(all_tickers)
    panel = add_attention_proxies(panel)
    panel = add_forward_returns(panel, HORIZONS)

    meme_panel = panel[panel["ticker"].isin(MEME_BASKET)].dropna(subset=["mom_21d", "fwd_ret_21d"])
    ctrl_panel = panel[panel["ticker"].isin(CONTROL_BASKET)].dropna(subset=["mom_21d", "fwd_ret_21d"])

    meme_results = run_basket(meme_panel, "Meme")
    ctrl_results = run_basket(ctrl_panel, "Control")

    plot_results(meme_results, ctrl_results, FIG_DIR / "attention_fade_grid.png")

    md = [
        "# Phase 2.3 — Attention-fade reproduction (Barber & Odean style)",
        "",
        f"**Data window:** {panel['date'].min().date()} → {panel['date'].max().date()}",
        f"**Meme basket:** {', '.join(MEME_BASKET)}",
        f"**Control basket:** {', '.join(CONTROL_BASKET)}",
        f"**Horizons:** {HORIZONS} trading days  •  **Source:** yfinance daily OHLCV",
        "",
        "## Hypothesis",
        "",
        "Stocks at attention extremes — high prior-period winners, abnormal volume, extreme one-day moves — should exhibit forward UNDERperformance over 1-3 months (Barber & Odean 2008, *All That Glitters*, RFS 21:785). The effect should be stronger in attention-prone retail-favorite names (meme basket) than in stable large-caps (control basket).",
        "",
        "**Test statistic:** `forward_return(extreme_group) − forward_return(rest)`. Negative = attention-fade (consistent with Barber-Odean). Positive = attention-momentum (would falsify).",
        "",
        "## Meme basket results",
        "",
        fmt_results(meme_results),
        "",
        "## Control basket results",
        "",
        fmt_results(ctrl_results),
        "",
        "## Reading",
        "",
        "- **diff_bps**: forward-return mean of the extreme group minus the rest (bps over the horizon)",
        "- **tstat**: Welch's t-stat. |t|>2 ≈ p<0.05, |t|>2.6 ≈ p<0.01",
        "- **Negative diff_bps** is the Barber-Odean fade prediction. Positive diff_bps would *falsify* it.",
        "",
        "## Caveats",
        "",
        "- Small basket (10 meme + 5 control). Real Barber-Odean used 80k+ retail accounts. Power is limited.",
        "- yfinance daily-OHLCV only — no intraday attention proxies (option flow, social-media spike).",
        "- Survivorship bias in the meme basket — these are tickers that *survived* and stayed retail-relevant. A truer test would include 2021's GME-era meme stocks that have since collapsed (BBBY, etc.) and the 2024-2025 wave separately.",
        "- No transaction-cost / borrow-cost model. The implied strategy (short the attention-extreme group) needs single-stock borrow availability, which is often unavailable or expensive precisely when the attention spike happens.",
        "",
        "## Files",
        "",
        "- `figures/attention_fade_grid.png` — 3×2 grid of forward-return spreads by proxy and horizon",
        "",
        "## How this informs the retail playbook",
        "",
        "If meme-basket diffs are negative (especially at 21d/63d) and stronger than control, the playbook's Rule #2 (\"fade single-name attention extremes, don't fade aggregate retail\") is empirically supported on free data. Magnitude of the effect determines actionability: a -100 bps over 21 days fade is meaningful given typical retail account sizes; a -10 bps fade is noise.",
    ]
    out = ROOT / "backtest_results_attention.md"
    out.write_text("\n".join(md) + "\n")
    print(f"\nWrote {out}")
    print("Done.")


if __name__ == "__main__":
    main()
