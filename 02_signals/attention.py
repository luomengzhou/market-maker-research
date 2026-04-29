"""
Attention-fade signal — Barber-Odean (2008) reproduction on a meme-stock basket.

Hypothesis: stocks at attention extremes (extreme prior return, abnormal volume,
extreme one-day move) exhibit forward underperformance over 1-3 months. This is
the contrarian 'fade single-name retail attention' rule referenced in
04_retail_playbook.md but not previously tested in this project.

Three attention proxies, computed daily per ticker:
    1. mom_21d_rank:    cross-sectional rank of trailing 21-day return
                        (high rank = high prior return = high attention)
    2. abnvol_5d:       trailing-5d volume / trailing-60d volume
                        (>2x = attention spike)
    3. extreme_1d:      |yesterday's return| z-scored against trailing 60d vol
                        (>3 = extreme single-day move)

Forward horizons tested: 5, 21, 63 days (1w, 1m, 3m).

This module builds the panel; 03_backtest_attention.py runs the analysis.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE = DATA_DIR / "cache" / "meme_basket.parquet"

# Meme/attention-prone basket — selected for retail interest historically
MEME_BASKET = ["NVDA", "TSLA", "GME", "AMC", "AMD", "COIN", "PLTR", "RBLX", "SOFI", "RIOT"]
# Control basket — boring large-caps with low retail attention churn
CONTROL_BASKET = ["JNJ", "KO", "PG", "WMT", "JPM"]


def load_panel(tickers: list[str], start: str = "2019-01-01", refresh: bool = False) -> pd.DataFrame:
    """Load OHLCV panel for tickers. Cached as parquet keyed by ticker set."""
    cache_key = "_".join(sorted(tickers))
    cache_path = DATA_DIR / "cache" / f"panel_{abs(hash(cache_key)) % 10**8}.parquet"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists() and not refresh:
        return pd.read_parquet(cache_path)

    raw = yf.download(tickers, start=start, auto_adjust=True, progress=False, group_by="ticker")
    frames = []
    for t in tickers:
        if t not in raw.columns.get_level_values(0):
            continue
        df = raw[t].copy()
        df["ticker"] = t
        df["date"] = df.index
        df["log_ret"] = np.log(df["Close"] / df["Close"].shift(1))
        frames.append(df.reset_index(drop=True))
    panel = pd.concat(frames, ignore_index=True).dropna(subset=["log_ret"])
    panel = panel[["date", "ticker", "Close", "Volume", "log_ret"]]
    panel.to_parquet(cache_path, index=False)
    return panel


def add_attention_proxies(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute the three Barber-Odean-style attention proxies per ticker."""
    out = []
    for ticker, g in panel.groupby("ticker", sort=False):
        g = g.sort_values("date").copy()
        g["mom_21d"] = g["log_ret"].rolling(21).sum()
        vol_5d = g["Volume"].rolling(5).mean()
        vol_60d = g["Volume"].rolling(60).mean()
        g["abnvol_5d"] = vol_5d / vol_60d
        ret_60d_std = g["log_ret"].rolling(60).std()
        g["extreme_1d"] = (g["log_ret"].abs() / ret_60d_std).shift(1)
        out.append(g)
    return pd.concat(out, ignore_index=True)


def add_forward_returns(panel: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    out = []
    for ticker, g in panel.groupby("ticker", sort=False):
        g = g.sort_values("date").copy()
        for h in horizons:
            g[f"fwd_ret_{h}d"] = g["log_ret"].shift(-h).rolling(h).sum().shift(-(h - 1))
            # Concretely: fwd_ret_h at row T = sum of log_ret(T+1..T+h)
            # The double-shift makes that explicit: future returns aligned to T.
        out.append(g)
    return pd.concat(out, ignore_index=True)


def add_attention_quintiles(panel: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional quintiles of mom_21d, computed per date across the panel."""
    panel = panel.copy()
    def _qcut(s):
        try:
            return pd.qcut(s, 5, labels=["Q1-low", "Q2", "Q3", "Q4", "Q5-high"], duplicates="drop")
        except ValueError:
            return pd.Series([np.nan] * len(s), index=s.index)
    panel["mom_q"] = panel.groupby("date")["mom_21d"].transform(_qcut)
    return panel


if __name__ == "__main__":
    print("Loading meme + control panel...")
    panel = load_panel(MEME_BASKET + CONTROL_BASKET)
    panel = add_attention_proxies(panel)
    panel = add_forward_returns(panel, [5, 21, 63])
    panel = add_attention_quintiles(panel)
    panel = panel.dropna(subset=["mom_21d", "abnvol_5d", "fwd_ret_21d"])
    print(f"Panel: {len(panel):,} rows, {panel['ticker'].nunique()} tickers, "
          f"{panel['date'].min().date()} -> {panel['date'].max().date()}")
    print("\n=== Attention extremes count by ticker ===")
    counts = pd.DataFrame({
        "abnvol>2x": panel.groupby("ticker").apply(lambda g: (g["abnvol_5d"] > 2).sum()),
        "extreme_1d>3": panel.groupby("ticker").apply(lambda g: (g["extreme_1d"] > 3).sum()),
        "mom_top_q": panel.groupby("ticker").apply(lambda g: (g["mom_q"] == "Q5-high").sum()),
    })
    print(counts)
