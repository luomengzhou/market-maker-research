"""Smoke tests for the pure helpers used by every backtest script.

Run: pytest -q
No network or yfinance needed: 03_backtest.py is loaded as a module and only
its metric / cost / regime helpers are exercised.
"""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_signals"))

from gex import compute_gex_regime  # noqa: E402
from dix import compute_dix_signal  # noqa: E402

_spec = spec_from_file_location("backtest_lib", ROOT / "03_backtest.py")
_bt = module_from_spec(_spec)
_spec.loader.exec_module(_bt)


def _idx(n):
    return pd.date_range("2020-01-01", periods=n, freq="B")


def test_sharpe_annualises_with_sqrt_252():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.0005, 0.01, 1000), index=_idx(1000))
    expected = r.mean() / r.std() * np.sqrt(252)
    assert _bt.sharpe(r) == pytest.approx(expected)


def test_sharpe_nan_on_short_or_flat_series():
    assert np.isnan(_bt.sharpe(pd.Series([0.01] * 10)))
    assert np.isnan(_bt.sharpe(pd.Series([0.0] * 100)))


def test_max_drawdown_known_path():
    eq = pd.Series([1.0, 1.2, 0.9, 1.0, 1.5, 1.2], index=_idx(6))
    # peak 1.2 -> trough 0.9 is -25%; later 1.5 -> 1.2 is -20%
    assert _bt.max_drawdown(eq) == pytest.approx(-0.25)
    assert _bt.max_drawdown(pd.Series([1.0, 1.1, 1.2])) == 0.0


def test_apply_costs_charges_on_position_changes_only():
    pos = pd.Series([1.0, 1.0, 0.0, 1.0], index=_idx(4))
    fwd = pd.Series([0.01, 0.02, -0.03, 0.01], index=_idx(4))
    out = _bt.apply_costs(pos, fwd, cost_bps=10.0)  # 10 bps = 0.001
    # day0: enter long (cost), day1: no change, day2: exit (cost, flat so no pnl), day3: re-enter
    expected = pd.Series([0.01 - 0.001, 0.02, 0.0 - 0.001, 0.01 - 0.001], index=_idx(4))
    pd.testing.assert_series_equal(out, expected)


def test_gex_sign_regime():
    toy = pd.DataFrame({"gex": [-1e9, 0.0, 2e9]}, index=_idx(3))
    assert compute_gex_regime(toy, method="sign").tolist() == [-1, 0, 1]


def test_dix_level_signal():
    toy = pd.DataFrame({"dix": [0.40, 0.44, 0.46]}, index=_idx(3))
    assert compute_dix_signal(toy, method="level", threshold=0.45).tolist() == [-1, 0, 1]
