"""
DIX retail-flow signal — SqueezeMetrics' Dark Index as a retail-positioning proxy.

Definition (SqueezeMetrics): DIX is a volume-weighted measure of off-exchange
short volume / total volume across S&P 500 names. Practically:

    HIGH DIX (>~0.45)  -> less off-exchange shorting  -> retail buying dominates -> bullish
    LOW  DIX (<~0.40)  -> more off-exchange shorting  -> retail selling/short    -> bearish

This is the cleanest free-tier proxy for "what retail flow is doing right now"
that we have access to. It's neither perfect nor manipulation-proof — but
SqueezeMetrics has published it daily since 2011, so it's our best historical
retail-positioning indicator.

Key reading: SqueezeMetrics 2017 white paper, sections on DIX construction.
   https://squeezemetrics.com/monitor/download/pdf/white_paper.pdf

This module shares load_gex() with gex.py — the source CSV has both columns.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gex import load_gex  # noqa: F401  re-export for caller convenience


def compute_dix_signal(
    df: pd.DataFrame,
    method: str = "level",
    threshold: float = 0.45,
    window: int = 252,
) -> pd.Series:
    """Convert raw DIX values into a {-1, 0, +1} signal.

    method='level'        : +1 if dix > threshold, -1 if dix < threshold - 0.02, else 0
                           Default threshold=0.45 splits roughly at the median.
    method='zscore'       : +1 if z-score > +1, -1 if z-score < -1, else 0
    method='quantile'     : +1 if dix in top tercile of rolling window, -1 if bottom, else 0
    method='ema-cross'    : +1 if dix > 5d EMA, -1 otherwise (a momentum-of-DIX rule)

    Returns a Series of signals aligned to df.index.
    """
    dix = df["dix"]

    if method == "level":
        # Simple binary: above threshold = retail-bullish, below = retail-bearish
        sig = pd.Series(0, index=dix.index, dtype=int)
        sig[dix > threshold] = 1
        sig[dix < threshold - 0.02] = -1
        return sig

    if method == "zscore":
        rolling = dix.rolling(window, min_periods=60)
        z = (dix - rolling.mean()) / rolling.std()
        sig = pd.Series(0, index=dix.index, dtype=int)
        sig[z > 1.0] = 1
        sig[z < -1.0] = -1
        return sig

    if method == "quantile":
        rolling = dix.rolling(window, min_periods=60)
        upper = rolling.quantile(2 / 3)
        lower = rolling.quantile(1 / 3)
        sig = pd.Series(0, index=dix.index, dtype=int)
        sig[dix >= upper] = 1
        sig[dix <= lower] = -1
        return sig

    if method == "ema-cross":
        ema = dix.ewm(span=5, min_periods=5).mean()
        sig = pd.Series(0, index=dix.index, dtype=int)
        sig[dix > ema] = 1
        sig[dix < ema] = -1
        return sig

    raise ValueError(f"unknown method: {method}")


def _toy_test() -> None:
    idx = pd.date_range("2024-01-01", periods=8, freq="B")
    toy = pd.DataFrame(
        {
            "price": np.linspace(100, 105, 8),
            "dix": [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.42, 0.38],
            "gex": [0] * 8,
        },
        index=idx,
    )
    sig = compute_dix_signal(toy, method="level", threshold=0.45)
    expected = [-1, -1, -1, 0, 1, 1, -1, -1]
    assert list(sig) == expected, sig.tolist()
    print("toy test OK:", sig.tolist())


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        _toy_test()
    else:
        df = load_gex()
        print(f"Rows: {len(df):,}, {df.index.min().date()} -> {df.index.max().date()}")
        print(f"\nDIX summary:")
        print(df["dix"].describe().round(3))
        print(f"\nDIX > 0.45: {(df['dix'] > 0.45).mean():.1%}")
        print(f"DIX < 0.40: {(df['dix'] < 0.40).mean():.1%}")
