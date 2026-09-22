#!/usr/bin/env python3
"""Polls Bitget's Demo Trading symbol status for Beacon's 5-ticker universe on
every cron cycle, independent of whether any trigger exists to process. This
exists so a halt->online transition is detected and LOGGED automatically --
zero manual checking, zero "someone has to notice and flip a switch."

This does NOT change how EXECUTE decides tradability: beacon/execute.py's
check_tradable() already re-queries Bitget fresh on every process invocation
(its cache is per-process, and each cron run is a fresh python process), so a
real trigger reaching EXECUTE already picks up current status automatically
with no code change needed. This script is the explicit, standalone
observability layer for that same fact -- so the transition itself is
visible in the log and state file even during cycles with zero triggers.
"""
import json
import sys
from datetime import datetime, timezone

from beacon import config, execute

STATE_FILE = config.DATA_DIR / "tradability_status.json"

TICKERS = ["EQT", "GOOGL", "MU", "NVDA", "ECHO"]


def load_previous():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def check():
    previous = load_previous()
    now = datetime.now(timezone.utc).isoformat()
    current = {}
    transitions = []

    for symbol in TICKERS:
        result = execute.check_tradable(symbol)
        current[symbol] = {
            "tradable": result["tradable"],
            "bitget_symbol": result["bitget_symbol"],
            "reason": result.get("reason"),
            "checked_at": now,
        }
        prev_tradable = (previous.get(symbol) or {}).get("tradable")
        if prev_tradable is False and result["tradable"] is True:
            transitions.append(symbol)

    STATE_FILE.write_text(json.dumps(current, indent=2))

    print(json.dumps(current, indent=2))
    if transitions:
        print(f"\n*** TRADABILITY CHANGED: {', '.join(transitions)} came OFF HALT — "
              f"EXECUTE will pick this up automatically on the next qualifying trigger. ***",
              file=sys.stderr)
    else:
        still_halted = [s for s in TICKERS if not current[s]["tradable"]]
        print(f"\nNo change. Still not tradable: {', '.join(still_halted) or 'none'}.", file=sys.stderr)

    return current, transitions


if __name__ == "__main__":
    check()
