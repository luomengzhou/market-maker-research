"""
daily_signal.py — operational entry point for Rule #1 (double-stress defensive tilt).

Run this each evening after US market close (~16:30 ET) to get tomorrow's
SPY position recommendation. Single command, no setup, ~3 seconds.

Usage:
    python daily_signal.py            # print today's signal
    python daily_signal.py --log      # also append to decision_log.csv
    python daily_signal.py --quiet    # JSON-only output (for piping)
    python daily_signal.py --history N  # print last N days of signals
    python daily_signal.py --refresh  # force fresh data download

The rule (from backtest_results_gex_vs_vix.md, Phase 2.5):
    Long SPY UNLESS  (VIX > 25)  AND  (GEX < 0)
    Step aside ONLY when BOTH stress signals fire (rare — ~6% of days)

Backtest: OOS Sharpe 0.89 (vs SPY 0.90), Max DD -22% (vs SPY -34%).
Calibrated 2011-2026 daily on SqueezeMetrics free CSV + yfinance VIX. See:
    backtest_results_gex_vs_vix.md  -> the GEX-vs-VIX comparison
    backtest_results.md             -> the original GEX-only validation
    04_retail_playbook.md           -> operational rules + when to override
    01_theory_primer.md             -> theoretical basis

Designed to be cron-friendly. Example crontab entry (5:30pm ET weekdays):
    30 17 * * 1-5  cd "$HOME/Documents/Market Maker" && python daily_signal.py --log
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_signals"))
from gex import load_gex, SQUEEZE_URL  # noqa: E402

LOG_PATH = ROOT / "decision_log.csv"
VIX_THRESHOLD = 25.0


def load_vix(refresh: bool = False) -> pd.DataFrame:
    cache = ROOT / "data" / "cache" / "vix.parquet"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists() and not refresh:
        return pd.read_parquet(cache)
    vix = yf.download("^VIX", start="2010-01-01", auto_adjust=True, progress=False)
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
    vix.index.name = "date"
    vix.to_parquet(cache)
    return vix


def evaluate_signal(gex_df: pd.DataFrame, vix_df: pd.DataFrame) -> dict:
    """Pull today's row + rolling context, classify regime using double-stress rule."""
    gex_df = gex_df.sort_index()
    vix_df = vix_df.sort_index()

    # Align on dates — use latest common date
    common = gex_df.index.intersection(vix_df.index)
    if len(common) == 0:
        raise RuntimeError("No overlapping dates between GEX and VIX data")
    latest_date = common.max()

    today_gex = gex_df.loc[latest_date]
    today_vix = float(vix_df.loc[latest_date, "Close"])

    # Yesterday's full state for transition detection
    prev_dates = common[common < latest_date]
    if len(prev_dates) > 0:
        prev_date = prev_dates.max()
        prev_gex = gex_df.loc[prev_date, "gex"]
        prev_vix = float(vix_df.loc[prev_date, "Close"])
        prev_stress = (prev_vix > VIX_THRESHOLD) and (prev_gex < 0)
    else:
        prev_stress = None

    # 1y context for GEX
    rolling_1y_gex = gex_df["gex"].iloc[-252:]
    z_1y_gex = (today_gex["gex"] - rolling_1y_gex.mean()) / rolling_1y_gex.std() if rolling_1y_gex.std() > 0 else 0.0
    pct_1y_gex = (rolling_1y_gex < today_gex["gex"]).mean() * 100

    # 1y context for VIX
    vix_1y = vix_df["Close"].loc[vix_df.index >= (latest_date - pd.Timedelta(days=380))].iloc[-252:]
    z_1y_vix = (today_vix - vix_1y.mean()) / vix_1y.std() if vix_1y.std() > 0 else 0.0
    pct_1y_vix = (vix_1y < today_vix).mean() * 100

    gex_stress = today_gex["gex"] < 0
    vix_stress = today_vix > VIX_THRESHOLD
    double_stress = gex_stress and vix_stress

    if double_stress:
        regime = "DOUBLE-STRESS  (both VIX>25 AND GEX<0)"
        position = "STEP ASIDE  (cash / short-duration Treasuries)"
        position_weight = 0.0
    elif gex_stress and not vix_stress:
        regime = "GEX-only stress  (dealers short gamma but VIX calm)"
        position = "LONG SPY  (single-signal, override per OR rule)"
        position_weight = 1.0
    elif vix_stress and not gex_stress:
        regime = "VIX-only stress  (vol elevated but dealers calm)"
        position = "LONG SPY  (single-signal, override per OR rule)"
        position_weight = 1.0
    else:
        regime = "CALM  (both signals benign)"
        position = "LONG SPY  (full target weight)"
        position_weight = 1.0

    transition_note = None
    if prev_stress is not None:
        if double_stress and not prev_stress:
            transition_note = "↘ entered DOUBLE-STRESS today — step aside tomorrow"
        elif not double_stress and prev_stress:
            transition_note = "↗ exited DOUBLE-STRESS today — re-enter SPY tomorrow"

    flags = []
    if abs(z_1y_gex) < 0.3:
        flags.append("GEX borderline (|z|<0.3)")
    if 23 <= today_vix <= 27:
        flags.append("VIX near threshold (23–27)")

    return {
        "as_of": str(latest_date.date()),
        "spx_price": float(today_gex["price"]),
        "dix": float(today_gex["dix"]),
        "gex": float(today_gex["gex"]),
        "gex_z_1y": float(z_1y_gex),
        "gex_pct_1y": float(pct_1y_gex),
        "vix": today_vix,
        "vix_z_1y": float(z_1y_vix),
        "vix_pct_1y": float(pct_1y_vix),
        "vix_threshold": VIX_THRESHOLD,
        "gex_stress": bool(gex_stress),
        "vix_stress": bool(vix_stress),
        "double_stress": bool(double_stress),
        "regime": regime,
        "position": position,
        "position_weight": position_weight,
        "transition_note": transition_note,
        "flags": flags,
    }


def format_human(sig: dict) -> str:
    emoji = "🔴" if sig["position_weight"] == 0.0 else "🟢"
    gex_emoji = "🔴" if sig["gex_stress"] else "🟢"
    vix_emoji = "🔴" if sig["vix_stress"] else "🟢"
    lines = [
        "",
        f"  Market Maker Daily Signal — Rule #1 (double-stress tilt)",
        f"  ──────────────────────────────────────────────────────────",
        f"  Data as of:           {sig['as_of']}",
        f"  SPX close:            {sig['spx_price']:,.2f}",
        f"",
        f"  {gex_emoji} GEX:                ${sig['gex']/1e9:+.2f}B  (z={sig['gex_z_1y']:+.2f}σ, pct {sig['gex_pct_1y']:.0f}%)  "
        f"{'→ STRESS' if sig['gex_stress'] else '→ calm'}",
        f"  {vix_emoji} VIX:                {sig['vix']:.2f}  (z={sig['vix_z_1y']:+.2f}σ, pct {sig['vix_pct_1y']:.0f}%)  "
        f"{'→ STRESS' if sig['vix_stress'] else '→ calm'}",
        f"  DIX (retail flow):    {sig['dix']:.3f}",
        f"",
        f"  {emoji} REGIME:  {sig['regime']}",
        f"  ➤ TOMORROW'S POSITION:  {sig['position']}",
    ]
    if sig.get("transition_note"):
        lines.append(f"  {sig['transition_note']}")
    for f in sig.get("flags", []):
        lines.append(f"  ⚠ {f}")
    lines += [
        "",
        f"  Sources: SqueezeMetrics ({SQUEEZE_URL}) + yfinance ^VIX",
        f"  Decision rule: long SPY UNLESS (VIX > {VIX_THRESHOLD:.0f} AND GEX < 0)",
        f"  Backtest: OOS Sharpe 0.89 (vs SPY 0.90), Max DD -22% (vs SPY -34%)",
        "",
    ]
    return "\n".join(lines)


def append_to_log(sig: dict, log_path: Path) -> None:
    row = {
        "logged_at": datetime.now().isoformat(timespec="seconds"),
        "as_of": sig["as_of"],
        "spx_price": sig["spx_price"],
        "gex": sig["gex"],
        "gex_z_1y": sig["gex_z_1y"],
        "vix": sig["vix"],
        "vix_z_1y": sig["vix_z_1y"],
        "double_stress": sig["double_stress"],
        "regime": sig["regime"],
        "position_weight": sig["position_weight"],
    }
    df_new = pd.DataFrame([row])
    if log_path.exists():
        existing = pd.read_csv(log_path)
        if not existing.empty and existing["as_of"].iloc[-1] == sig["as_of"]:
            print(f"  (note: log already has entry for {sig['as_of']}; not duplicating)")
            return
        df_new = pd.concat([existing, df_new], ignore_index=True)
    df_new.to_csv(log_path, index=False)
    print(f"  ✓ logged to {log_path.relative_to(ROOT)}")


def show_history(log_path: Path, n: int) -> None:
    if not log_path.exists():
        print(f"No log file at {log_path}. Run with --log first.")
        return
    df = pd.read_csv(log_path).tail(n)
    print(f"\nLast {len(df)} signal entries:\n")
    for _, r in df.iterrows():
        emoji = "🟢" if r["position_weight"] == 1.0 else "🔴"
        vix_str = f"VIX={r['vix']:.1f}" if "vix" in r and pd.notna(r.get("vix")) else "VIX=NA"
        print(f"  {emoji} {r['as_of']}  GEX={r['gex']/1e9:+5.2f}B  {vix_str}  →  weight={r['position_weight']:.0%}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--log", action="store_true", help="append to decision_log.csv")
    parser.add_argument("--quiet", action="store_true", help="JSON-only output")
    parser.add_argument("--refresh", action="store_true", help="force re-download data")
    parser.add_argument("--history", type=int, default=0, help="print last N decisions from log")
    args = parser.parse_args()

    if args.history > 0:
        show_history(LOG_PATH, args.history)
        return

    gex_df = load_gex(refresh=args.refresh)
    vix_df = load_vix(refresh=args.refresh)
    sig = evaluate_signal(gex_df, vix_df)

    if args.quiet:
        print(json.dumps(sig, indent=2, default=str))
    else:
        print(format_human(sig))

    if args.log:
        append_to_log(sig, LOG_PATH)


if __name__ == "__main__":
    main()
