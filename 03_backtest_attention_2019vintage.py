"""
Phase 2.3b — Attention-fade test on a SURVIVORSHIP-BIAS-FREE 2019-vintage basket.

Phase 2.3 used a 2026-hindsight basket (NVDA, TSLA, COIN, PLTR, ...) — names
that became dominant retail favorites BECAUSE they ran up in 2020-2025. That
let momentum dominate and produced a +1,100 bps headline that may not be a
real effect.

This test fixes the basket selection to NAMES THAT WERE RETAIL-ATTENTION-PRONE
AS OF LATE 2019 / EARLY 2020. Some later 100x-ed (NVDA wasn't on the list yet);
some went to zero (BBBY, NKLA's fraud collapse). Crucially, the basket is
selected with INFORMATION AVAILABLE IN 2019, not 2026.

Buckets that defined retail attention pre-COVID:
  - Cannabis hype 2019      : TLRY, CGC, SNDL, ACB
  - SPAC/EV/space hype      : NKLA, RIDE, SPCE, NIO, PLUG
  - Hopeful-turnaround names: BBBY, GME, AMC, BB, NOK
  - High-vol tech retail    : AMD, TSLA  (already retail-favorite by 2019)

Picked 12 names spanning these (mix of survivors and casualties):
    TLRY, NIO, PLUG, SPCE, NKLA, GME, AMC, BBBY, BB, NOK, AMD, TSLA

The same 5-name boring control basket as Phase 2.3.

If the fade-failure from Phase 2.3 (extreme = outperform) ALSO appears in this
basket, the conclusion is robust. If it flips to fade-confirms or no effect,
the original headline was survivorship bias.

Outputs:
    figures/attention_fade_grid_2019vintage.png
    backtest_results_attention_2019vintage.md
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
    CONTROL_BASKET,
    add_attention_proxies,
    add_forward_returns,
    load_panel,
)

# Reuse the conditional-returns helper from the v1 backtest
from importlib.util import spec_from_file_location, module_from_spec  # noqa: E402

_spec = spec_from_file_location("att_lib", ROOT / "03_backtest_attention.py")
_att = module_from_spec(_spec)
_spec.loader.exec_module(_att)
conditional_returns = _att.conditional_returns
fmt_results = _att.fmt_results

FIG_DIR = ROOT / "figures"
HORIZONS = [5, 21, 63]

# 2019-vintage meme basket — selected with INFORMATION AVAILABLE PRE-2020
VINTAGE_2019_BASKET = [
    # cannabis 2019 hype
    "TLRY", "CGC",
    # SPAC / EV / space 2019-2020
    "NKLA", "RIDE", "SPCE", "NIO", "PLUG",
    # hopeful turnaround retail favorites
    "BBBY",  # delisted 2023 — INTENTIONALLY INCLUDED for survivorship-bias control
    "GME", "AMC", "BB", "NOK",
    # high-vol retail tech 2019
    "AMD", "TSLA",
]


def plot_results(meme_res: pd.DataFrame, ctrl_res: pd.DataFrame, out: Path, title_suffix: str = "") -> None:
    proxies = meme_res["proxy"].unique()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)

    width = 0.35
    x_pos = np.arange(len(HORIZONS))
    for ax, proxy in zip(axes, proxies):
        m = meme_res[meme_res["proxy"] == proxy].set_index("horizon")
        c = ctrl_res[ctrl_res["proxy"] == proxy].set_index("horizon")
        ax.bar(x_pos - width / 2, m.loc[HORIZONS, "diff_bps"], width, color="tab:purple",
               label="2019-vintage meme basket", alpha=0.85)
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
    fig.suptitle(f"Attention-fade test: 2019-vintage meme basket{title_suffix}\n"
                 "(survivorship-bias-controlled — basket selected with info available pre-2020, "
                 "incl. delisted BBBY)",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> None:
    print("Loading 2019-vintage panel + control panel...")
    all_tickers = VINTAGE_2019_BASKET + CONTROL_BASKET
    panel = load_panel(all_tickers, refresh=True)  # refresh for delisted BBBY etc.
    print(f"  Panel: {len(panel):,} rows, {panel['ticker'].nunique()} tickers loaded "
          f"of {len(all_tickers)} requested")
    missing = set(all_tickers) - set(panel["ticker"].unique())
    if missing:
        print(f"  Missing from yfinance: {sorted(missing)}")
    by_ticker = panel.groupby("ticker")["date"].agg(["min", "max", "count"])
    print(f"  Coverage by ticker:")
    print(by_ticker.to_string())

    panel = add_attention_proxies(panel)
    panel = add_forward_returns(panel, HORIZONS)

    meme_panel = panel[panel["ticker"].isin(VINTAGE_2019_BASKET)].dropna(subset=["mom_21d", "fwd_ret_21d"])
    ctrl_panel = panel[panel["ticker"].isin(CONTROL_BASKET)].dropna(subset=["mom_21d", "fwd_ret_21d"])

    print(f"\nMeme rows: {len(meme_panel):,} (post-NaN-drop)")
    print(f"Control rows: {len(ctrl_panel):,}")

    print(f"\n=== 2019-vintage meme basket ===")
    meme_results = []
    for label, fn, col in [
        ("mom_21d_top10pct", lambda s: s > s.quantile(0.9), "mom_21d"),
        ("abnvol_5d_>2x",   lambda s: s > 2.0, "abnvol_5d"),
        ("extreme_1d_>3sigma", lambda s: s > 3.0, "extreme_1d"),
    ]:
        meme_results.append(conditional_returns(meme_panel, col, fn, label))
    meme_results = pd.concat(meme_results, ignore_index=True)
    meme_results["basket"] = "2019-vintage meme"
    print(meme_results.to_string(index=False))

    print(f"\n=== Control basket ===")
    ctrl_results = []
    for label, fn, col in [
        ("mom_21d_top10pct", lambda s: s > s.quantile(0.9), "mom_21d"),
        ("abnvol_5d_>2x",   lambda s: s > 2.0, "abnvol_5d"),
        ("extreme_1d_>3sigma", lambda s: s > 3.0, "extreme_1d"),
    ]:
        ctrl_results.append(conditional_returns(ctrl_panel, col, fn, label))
    ctrl_results = pd.concat(ctrl_results, ignore_index=True)
    ctrl_results["basket"] = "Control"
    print(ctrl_results.to_string(index=False))

    plot_results(meme_results, ctrl_results, FIG_DIR / "attention_fade_grid_2019vintage.png")

    md = [
        "# Phase 2.3b — Attention-fade test on 2019-VINTAGE meme basket",
        "",
        "*Survivorship-bias-controlled re-run of [Phase 2.3](backtest_results_attention.md). The original test selected names with 2026 hindsight (NVDA, TSLA, COIN, PLTR — names that became dominant BECAUSE they ran up); this version uses names that were retail-attention-prone AS OF LATE 2019 / EARLY 2020, including ones that later collapsed.*",
        "",
        f"**Data window:** {panel['date'].min().date()} → {panel['date'].max().date()}",
        f"**2019-vintage meme basket ({len(VINTAGE_2019_BASKET)} names):** {', '.join(VINTAGE_2019_BASKET)}",
        f"**Control basket:** {', '.join(CONTROL_BASKET)}",
        f"**Horizons:** {HORIZONS} trading days",
        "",
    ]
    if missing:
        md += [
            f"⚠️  **Missing from yfinance:** {', '.join(sorted(missing))}.  Likely delisted with no data archive.",
            "",
        ]

    md += [
        "## Coverage by ticker",
        "",
        "| Ticker | First date | Last date | Rows |",
        "|---|---|---|---|",
    ]
    for t in panel["ticker"].unique():
        sub = panel[panel["ticker"] == t]
        md.append(f"| {t} | {sub['date'].min().date()} | {sub['date'].max().date()} | {len(sub):,} |")

    md += [
        "",
        "## Meme basket (2019-vintage) results",
        "",
        fmt_results(meme_results),
        "",
        "## Control basket results",
        "",
        fmt_results(ctrl_results),
        "",
        "## Comparison to Phase 2.3 (2026-hindsight basket)",
        "",
        "Phase 2.3 headline was meme-basket diff = **+878 bps over 63d, t=5.9** (mom_21d_top10pct proxy). The question this re-run answers: how much of that was real attention-momentum, and how much was an artifact of choosing the basket *because* it had a 100×-ing winner roster?",
        "",
        "If 2019-vintage results show:",
        "- **Similar magnitude positive diff** → real momentum effect, original headline robust",
        "- **Smaller positive diff** → original was inflated by survivorship bias, but momentum direction holds",
        "- **Diff near zero or negative** → original was mostly survivorship bias; Barber-Odean fade is *consistent* with modern data once you stop cherry-picking the basket",
        "",
        "*See the figure and tables above for the actual answer in this sample.*",
        "",
        "## Files",
        "",
        "- `figures/attention_fade_grid_2019vintage.png`",
    ]
    out = ROOT / "backtest_results_attention_2019vintage.md"
    out.write_text("\n".join(md) + "\n")
    print(f"\nWrote {out}")
    print("Done.")


if __name__ == "__main__":
    main()
