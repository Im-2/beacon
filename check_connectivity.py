#!/usr/bin/env python3
"""Cheap, explicit pre-flight check: is Bitget's API actually reachable right
now? Run first in every cron cycle so a connectivity failure is loud and
visible in the log immediately, rather than discovered later as a confusing
half-failure partway through tradability/market-data/live. Always exits 0
(this must never abort the rest of the cron chain -- SENSE/JUDGE/RISK
reasoning should still run even when Bitget itself is unreachable) -- it
only prints a warning banner.

Context: this session hit a real, confirmed case of this -- api.bitget.com
was unreachable (TLS handshake hangs/resets) from this project's own
sandboxed dev environment AND from the machine actually running the cron job
(both home Wi-Fi and mobile data), resolved only by connecting through a
VPN. If you see the warning below in a cron log, check that the VPN is
still connected before assuming something else is broken.
"""
import sys
from beacon import execute

result = execute.verify_bitget_reachable()

if result["reachable"]:
    print("Bitget connectivity: OK")
else:
    print("!" * 70, file=sys.stderr)
    print("!!! BITGET UNREACHABLE -- check that your VPN is connected.", file=sys.stderr)
    print(f"!!! Reason: {result['reason']}", file=sys.stderr)
    print("!!! SENSE/JUDGE/RISK reasoning will still run, but EXECUTE will", file=sys.stderr)
    print("!!! not be able to place or check real orders this cycle.", file=sys.stderr)
    print("!" * 70, file=sys.stderr)

sys.exit(0)
