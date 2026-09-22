#!/usr/bin/env python3
"""One-off manual test: places a real small BTC paper order via the actual
beacon/execute.py code path, to confirm Bitget's Demo Trading account can
genuinely fill crypto trades (Cross-Asset Execution Agent, Step 1). Run this
yourself from a terminal in this folder; delete it afterward if you like."""
import json
from beacon import execute

order = execute.place_paper_order(
    symbol="BTC",
    direction="long",
    size_usd=20.0,
    entry_price=0,
    stop_loss_pct=3.0,
    take_profit_pct=5.0,
    dry_run=False,
)
print(json.dumps(order, indent=2))
