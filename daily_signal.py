"""
daily_signal.py — operational entry point for Rule #1 (GEX defensive tilt).

Run this each evening after US market close (~16:30 ET) to get tomorrow's
SPY position recommendation. Single command, no setup required, ~3 seconds.

Usage:
    python daily_signal.py            # print today's signal
    python daily_signal.py --log      # also append to decision_log.csv
    python daily_signal.py --quiet    # JSON-only output (for piping)
    python daily_signal.py --history N  # print last N days of signals + actions

The rule (from backtest_results.md):
    GEX > 0  ->  hold full SPY position tomorrow
    GEX <= 0 ->  reduce SPY to 0% (cash or short-duration Treasuries)

Calibrated 2011-2026 daily on SqueezeMetrics free CSV. See:
    backtest_results.md      -> the validated backtest
    04_retail_playbook.md    -> the operational rules + when to override
    01_theory_primer.md      -> the theoretical basis

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

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "02_signals"))
from gex import load_gex, SQUEEZE_URL  # noqa: E402

LOG_PATH = ROOT / "decision_log.csv"


def evaluate_signal(df: pd.DataFrame) -> dict:
    """Pull today's row + rolling context, classify regime."""
    df = df.sort_index()
    today = df.iloc[-1]
    yesterday = df.iloc[-2] if len(df) >= 2 else None

    # rolling 1-year stats for context
    rolling_1y = df["gex"].iloc[-252:]
    z_1y = (today["gex"] - rolling_1y.mean()) / rolling_1y.std() if rolling_1y.std() > 0 else 0.0
    pct_1y = (rolling_1y < today["gex"]).mean() * 100

    # primary regime classification (sign method, the validated rule)
    if today["gex"] > 0:
        regime = "POSITIVE-GEX  /  CALM"
        position = "LONG SPY  (full target weight)"
        position_weight = 1.0
    else:
        regime = "NEGATIVE-GEX  /  STRESSED"
        position = "STEP ASIDE  (cash / short-duration Treasuries)"
        position_weight = 0.0

    # secondary: borderline check
    borderline = abs(z_1y) < 0.3
    flag = "  ⚠ borderline z<0.3 — consider sitting tight" if borderline else ""

    # transition vs yesterday
    transition = ""
    if yesterday is not None:
        if today["gex"] > 0 and yesterday["gex"] <= 0:
            transition = "  ↗ regime FLIPPED to positive today"
        elif today["gex"] <= 0 and yesterday["gex"] > 0:
            transition = "  ↘ regime FLIPPED to negative today"

    return {
        "as_of": str(today.name.date()),
        "spx_price": float(today["price"]),
        "dix": float(today["dix"]),
        "gex": float(today["gex"]),
        "gex_z_1y": float(z_1y),
        "gex_pct_1y": float(pct_1y),
        "regime": regime,
        "position": position,
        "position_weight": position_weight,
        "borderline": bool(borderline),
        "transition_note": transition.strip() or None,
        "flag": flag.strip() or None,
    }


def format_human(sig: dict) -> str:
    arrow_for_regime = "🟢" if sig["position_weight"] == 1.0 else "🔴"
    lines = [
        "",
        f"  Market Maker Daily Signal — Rule #1 (GEX defensive tilt)",
        f"  ──────────────────────────────────────────────────────────",
        f"  Data as of:           {sig['as_of']}",
        f"  SPX close:            {sig['spx_price']:,.2f}",
        f"  Dealer GEX:           ${sig['gex']/1e9:+.2f}B per 1% spot move",
        f"  GEX 1y z-score:       {sig['gex_z_1y']:+.2f}σ  (pct rank {sig['gex_pct_1y']:.0f}%)",
        f"  DIX:                  {sig['dix']:.3f}",
        f"",
        f"  {arrow_for_regime} REGIME:  {sig['regime']}",
        f"  ➤ TOMORROW'S POSITION:  {sig['position']}",
    ]
    if sig.get("transition_note"):
        lines.append(f"  {sig['transition_note']}")
    if sig.get("flag"):
        lines.append(f"  {sig['flag']}")
    lines += [
        "",
        f"  Source: SqueezeMetrics free CSV ({SQUEEZE_URL})",
        f"  Decision rule: long SPY when GEX > 0, flat when GEX ≤ 0",
        f"  See backtest_results.md for OOS performance: Sharpe 0.82, MaxDD -22% vs SPY -34%",
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
        print(f"  {emoji} {r['as_of']}  GEX={r['gex']/1e9:+5.2f}B  z={r['gex_z_1y']:+.2f}σ  →  weight={r['position_weight']:.0%}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--log", action="store_true", help="append to decision_log.csv")
    parser.add_argument("--quiet", action="store_true", help="JSON-only output")
    parser.add_argument("--refresh", action="store_true", help="force re-download SqueezeMetrics CSV")
    parser.add_argument("--history", type=int, default=0, help="print last N decisions from log")
    args = parser.parse_args()

    if args.history > 0:
        show_history(LOG_PATH, args.history)
        return

    df = load_gex(refresh=args.refresh)
    sig = evaluate_signal(df)

    if args.quiet:
        print(json.dumps(sig, indent=2, default=str))
    else:
        print(format_human(sig))

    if args.log:
        append_to_log(sig, LOG_PATH)


if __name__ == "__main__":
    main()
