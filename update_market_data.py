#!/usr/bin/env python3
"""Fetches real live prices and recent hourly candles from Bitget's public
market-data API (no auth, no API keys -- same public endpoints used
elsewhere in this project) for Beacon's 5-ticker universe, and writes them
to market_data.json at the repo root.

This replaces the earlier Claude-artifact-db-capability relay: the dashboard
now reads this plain JSON file via a normal fetch() call, which works on any
static host (Vercel included) and has zero dependency on Claude-specific
infrastructure. Run on the same cron cycle as the rest of the pipeline (see
run_now.sh's "market-data" step).
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from beacon import execute

ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT / "market_data.json"

TICKERS = ["EQT", "GOOGL", "MU", "NVDA", "ECHO"]
CANDLE_GRANULARITY = "1h"
CANDLE_LIMIT = 120


def fetch_price(bitget_symbol):
    resp = requests.get(
        "https://api.bitget.com/api/v2/spot/market/tickers",
        params={"symbol": bitget_symbol},
        timeout=20,
    )
    resp.raise_for_status()
    j = resp.json()
    if j.get("code") != "00000" or not j.get("data"):
        raise ValueError(f"unexpected payload for {bitget_symbol}: {j}")
    d = j["data"][0]
    return {"price": float(d["lastPr"]), "change24h": float(d["change24h"])}


def fetch_candles(bitget_symbol):
    resp = requests.get(
        "https://api.bitget.com/api/v2/spot/market/candles",
        params={"symbol": bitget_symbol, "granularity": CANDLE_GRANULARITY, "limit": CANDLE_LIMIT},
        timeout=20,
    )
    resp.raise_for_status()
    j = resp.json()
    if j.get("code") != "00000" or not j.get("data"):
        raise ValueError(f"unexpected payload for {bitget_symbol}: {j}")
    return [
        {
            "time": int(row[0]) // 1000,
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
        }
        for row in j["data"]
    ]


def update():
    prices = {}
    candles = {}
    failures = []

    for ticker in TICKERS:
        bitget_symbol = execute.to_bitget_symbol(ticker)
        try:
            prices[ticker] = fetch_price(bitget_symbol)
        except Exception as e:
            failures.append(f"{ticker} price: {e}")
        time.sleep(0.15)
        try:
            candles[ticker] = fetch_candles(bitget_symbol)
        except Exception as e:
            failures.append(f"{ticker} candles: {e}")
        time.sleep(0.15)

    if not prices and not candles:
        # Loud warning, but NEVER exit nonzero: run_now.sh's `all` chain uses
        # `set -e`, so exiting 1 here used to abort the rest of the cron cycle
        # -- including `live` (SENSE/JUDGE/RISK), which must keep running
        # regardless of Bitget/market-data connectivity. Confirmed as the real
        # cause of a silently-skipped automated run on 2026-09-22 (VPN was
        # down; market-data failed; live never ran; LastTaskResult was 1 and
        # the cron log wasn't touched at all that cycle).
        print("All fetches failed -- leaving market_data.json untouched. "
              "(Not treated as fatal -- see run_now.sh.)", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return None

    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "prices": prices,
        "candles": candles,
    }
    OUTPUT_FILE.write_text(json.dumps(payload, separators=(",", ":")))

    print(f"Updated {OUTPUT_FILE}: {len(prices)}/{len(TICKERS)} prices, "
          f"{len(candles)}/{len(TICKERS)} candle sets.")
    if failures:
        print("Failures:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)

    return payload


if __name__ == "__main__":
    update()
