"""
GEX regime signal — daily SPX/SPY dealer gamma exposure as a regime indicator.

Hypothesis (Dim, Eraker, Vilkov 2024 SSRN 4692190):
    - Dealer net gamma POSITIVE -> intraday/short-horizon mean-reversion regime.
    - Dealer net gamma NEGATIVE -> momentum / trend-amplifying regime.

Data: SqueezeMetrics free historical CSV
    https://squeezemetrics.com/monitor/static/DIX.csv
    Columns: date, price, dix, gex   (gex in $ per 1% spot move)
    History: 2011-05-02 to present (daily, NYSE trading days)

Public construction reference: SqueezeMetrics 2017 white paper
    https://squeezemetrics.com/monitor/download/pdf/white_paper.pdf

This module exposes load_gex(), compute_gex_regime(), and a small CLI
for ad-hoc inspection. The backtest itself lives in 03_backtest.ipynb.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_PATH = DATA_DIR / "raw" / "squeezemetrics_dix_gex.csv"
SQUEEZE_URL = "https://squeezemetrics.com/monitor/static/DIX.csv"


def load_gex(refresh: bool = False) -> pd.DataFrame:
    """Load SqueezeMetrics daily GEX/DIX series.

    refresh=True re-downloads from squeezemetrics.com. Otherwise reads cached file.
    Returns a DataFrame indexed by date with columns ['price', 'dix', 'gex'].
    """
    if refresh or not RAW_PATH.exists():
        RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        df = pd.read_csv(SQUEEZE_URL, parse_dates=["date"])
        df.to_csv(RAW_PATH, index=False)
    else:
        df = pd.read_csv(RAW_PATH, parse_dates=["date"])
    df = df.set_index("date").sort_index()
    return df


def compute_gex_regime(
    df: pd.DataFrame,
    method: str = "sign",
    threshold: float | None = None,
    rolling_window: int = 252,
) -> pd.Series:
    """Classify each day into a GEX regime.

    method='sign'      : +1 if gex>0, -1 if gex<0  (simplest)
    method='zscore'    : +1 if z>+threshold, -1 if z<-threshold, 0 otherwise
                         (z computed on a rolling window)
    method='quantile'  : +1 if gex >= top tercile of rolling window,
                         -1 if <= bottom tercile, 0 otherwise

    Returns a Series of regimes aligned to df.index.
    """
    gex = df["gex"]

    if method == "sign":
        return np.sign(gex).astype(int).rename("regime")

    if method == "zscore":
        thresh = threshold if threshold is not None else 0.5
        rolling = gex.rolling(rolling_window, min_periods=60)
        z = (gex - rolling.mean()) / rolling.std()
        regime = pd.Series(0, index=gex.index, dtype=int)
        regime[z > thresh] = 1
        regime[z < -thresh] = -1
        return regime.rename("regime")

    if method == "quantile":
        rolling = gex.rolling(rolling_window, min_periods=60)
        upper = rolling.quantile(2 / 3)
        lower = rolling.quantile(1 / 3)
        regime = pd.Series(0, index=gex.index, dtype=int)
        regime[gex >= upper] = 1
        regime[gex <= lower] = -1
        return regime.rename("regime")

    raise ValueError(f"unknown method: {method}")


def _toy_test() -> None:
    """Sanity-check on a synthetic series. Run via `python gex.py --test`."""
    idx = pd.date_range("2024-01-01", periods=10, freq="B")
    toy = pd.DataFrame(
        {
            "price": np.linspace(100, 110, 10),
            "dix": np.linspace(0.4, 0.5, 10),
            "gex": [-3e9, -2e9, -1e9, 0, 1e9, 2e9, 3e9, 2e9, -1e9, -3e9],
        },
        index=idx,
    )
    sign_regime = compute_gex_regime(toy, method="sign")
    expected = [-1, -1, -1, 0, 1, 1, 1, 1, -1, -1]
    assert list(sign_regime) == expected, sign_regime.tolist()
    print("toy test OK:", sign_regime.tolist())


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        _toy_test()
    else:
        df = load_gex()
        print(f"Loaded {len(df)} rows, {df.index.min().date()} -> {df.index.max().date()}")
        print(df.tail(5))
        print(f"\nGEX summary (USD per 1% spot move):")
        print(df["gex"].describe().apply(lambda x: f"{x:,.0f}"))
        print(f"\nNegative-GEX days: {(df['gex'] < 0).sum()} / {len(df)} ({(df['gex'] < 0).mean():.1%})")
