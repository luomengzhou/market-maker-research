"""Synthetic smoke tests for the --lag signal-timing option.

No network or yfinance needed: 03_backtest.py is loaded as a module and the
lag helpers are exercised on a fake return series and fake position series.
"""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_signals"))

_spec = spec_from_file_location("backtest_lib", ROOT / "03_backtest.py")
_bt = module_from_spec(_spec)
_spec.loader.exec_module(_bt)

N = 300
# spans the 2021-01-01 IS/OOS boundary so both splits are non-empty
IDX = pd.date_range("2020-06-01", periods=N, freq="B")


def _fake_data(seed: int = 0):
    rng = np.random.default_rng(seed)
    ret = pd.Series(rng.normal(0.0003, 0.01, N), index=IDX)
    fwd_ret = ret.shift(-1)
    pos = pd.Series(rng.choice([0.0, 0.5, 1.0], size=N), index=IDX)
    return ret, fwd_ret, pos


def test_lag0_equals_old_computation():
    _, fwd_ret, pos = _fake_data()
    assert _bt.apply_lag(pos, 0) is pos
    old = _bt.apply_costs(pos, fwd_ret, _bt.TXN_COST_BPS)
    new = _bt.apply_costs(_bt.apply_lag(pos, 0), fwd_ret, _bt.TXN_COST_BPS)
    pd.testing.assert_series_equal(old, new)


def test_lag1_equals_shifted_position_times_fwd_ret():
    _, fwd_ret, pos = _fake_data()
    lagged = _bt.apply_lag(pos, 1)
    # the first day is flat, afterwards it is exactly pos.shift(1)
    assert lagged.iloc[0] == 0.0
    pd.testing.assert_series_equal(lagged.iloc[1:], pos.shift(1).iloc[1:])
    # with zero cost the strategy return is pos.shift(1) * fwd_ret
    ret_lag1 = _bt.apply_costs(lagged, fwd_ret, cost_bps=0.0)
    expected = (pos.shift(1) * fwd_ret).iloc[1:]
    pd.testing.assert_series_equal(ret_lag1.iloc[1:], expected, check_names=False)
    # and it differs from the unlagged version (the look-ahead actually matters)
    ret_lag0 = _bt.apply_costs(pos, fwd_ret, cost_bps=0.0)
    assert not np.allclose(ret_lag0.iloc[1:-1], ret_lag1.iloc[1:-1])


def test_lag_n_general_and_negative_rejected():
    _, _, pos = _fake_data()
    lag3 = _bt.apply_lag(pos, 3)
    assert (lag3.iloc[:3] == 0.0).all()
    pd.testing.assert_series_equal(lag3.iloc[3:], pos.shift(3).iloc[3:])
    with pytest.raises(ValueError):
        _bt.apply_lag(pos, -1)


def test_buy_and_hold_unaffected_other_strategies_lagged():
    _, _, pos = _fake_data()
    bah = pd.Series(1.0, index=IDX)
    positions = {_bt.BUY_AND_HOLD: bah, "GEX-only": pos, "Vol-targeted": pos * 0.7}
    out = _bt.lag_positions(positions, lag=1)
    assert out[_bt.BUY_AND_HOLD] is bah  # untouched, no leading flat day
    pd.testing.assert_series_equal(out["GEX-only"], _bt.apply_lag(pos, 1))
    pd.testing.assert_series_equal(out["Vol-targeted"], _bt.apply_lag(pos * 0.7, 1))
    assert set(out) == set(positions)
    # lag=0 is the identity on the whole dict
    out0 = _bt.lag_positions(positions, lag=0)
    for k in positions:
        assert out0[k] is positions[k]


def test_run_backtest_one_lag_matches_manual_shift():
    """End-to-end through the Phase 2.1 pipeline on a synthetic GEX series."""
    rng = np.random.default_rng(1)
    ret = pd.Series(rng.normal(0.0003, 0.01, N), index=IDX)
    df = pd.DataFrame({
        "gex": rng.normal(0, 1e9, N),
        "ret": ret,
        "fwd_ret": ret.shift(-1),
    }).dropna()
    r0 = _bt.run_backtest_one(df, method="sign", strategy="defensive-tilt", lag=0)
    r1 = _bt.run_backtest_one(df, method="sign", strategy="defensive-tilt", lag=1)
    pos0 = r0["positions"]
    pd.testing.assert_series_equal(r1["positions"], pos0.shift(1).fillna(0.0))
    pd.testing.assert_series_equal(
        r1["strat_ret"], _bt.apply_costs(pos0.shift(1).fillna(0.0), df["fwd_ret"], _bt.TXN_COST_BPS)
    )
    # buy-and-hold figures are the same in both runs
    assert r0["spy_sharpe_full"] == r1["spy_sharpe_full"]
    assert r0["spy_max_dd_full"] == r1["spy_max_dd_full"]


def test_output_naming_and_header():
    assert _bt.lag_suffix(0) == ""
    assert _bt.lag_suffix(1) == "_lag1"
    assert _bt.lag_suffix(2) == "_lag2"
    assert "lag:** 1" in "".join(_bt.lag_header_lines(1))
    assert "lag:** 0" in "".join(_bt.lag_header_lines(0))
