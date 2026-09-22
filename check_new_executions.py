#!/usr/bin/env python3
"""Checks logs/decisions.jsonl for new real executions (direct rToken fill or
cross-asset proxy fill) since the last check, and reports them clearly. Used
by a scheduled task to surface real trades as soon as they happen, without
the user having to manually watch the log. Tracks progress in
data/last_execution_check.json (just a line-count marker)."""
import json
from beacon import config

LOG_FILE = config.LOG_DIR / "decisions.jsonl"
MARKER_FILE = config.DATA_DIR / "last_execution_check.json"
REAL_EXECUTION_OUTCOMES = {"executed_direct_rtoken", "executed_cross_asset_proxy"}


def check():
    if not LOG_FILE.exists():
        print("No decisions log yet.")
        return []

    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    last_seen = 0
    if MARKER_FILE.exists():
        last_seen = json.loads(MARKER_FILE.read_text()).get("last_seen_line_count", 0)

    new_lines = lines[last_seen:]
    new_executions = []
    for line in new_lines:
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("outcome") in REAL_EXECUTION_OUTCOMES:
            new_executions.append(record)

    MARKER_FILE.write_text(json.dumps({"last_seen_line_count": len(lines)}))

    if new_executions:
        print(f"*** {len(new_executions)} NEW REAL EXECUTION(S) since last check ***")
        for r in new_executions:
            leg = r.get("execution_leg", "?")
            symbol = r.get("symbol")
            judgment = r.get("judgment") or {}
            if leg == "cross_asset_proxy":
                order = r.get("cross_asset_order") or {}
                note = r.get("cross_asset_note", "")
                print(f"  {symbol} -> CROSS-ASSET PROXY: {note}")
            else:
                order = r.get("rtoken_order") or {}
                print(f"  {symbol} -> DIRECT rToken execution")
            print(f"    direction={judgment.get('decision')} conviction={judgment.get('conviction_score')} "
                  f"size_pct={judgment.get('position_size_pct_of_capital')}")
            resp = (order.get("response") or {})
            print(f"    Bitget orderId={resp.get('data', {}).get('orderId') if isinstance(resp.get('data'), dict) else None} "
                  f"timestamp={r.get('timestamp_utc')}")
    else:
        print(f"No new executions since last check ({len(new_lines)} new decision(s) reviewed, none were real fills).")

    return new_executions


if __name__ == "__main__":
    check()
