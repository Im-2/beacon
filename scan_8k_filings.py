#!/usr/bin/env python3
"""
Scan SEC EDGAR's full-text search for 8-K filings in the last N days, restricted
to a fixed liquid universe (default: S&P 500 constituents) and to item codes
2.02 (Results of Operations/Financial Condition) and 7.01 (Reg FD Disclosure,
often guidance) — the "guidance/material update" trigger type defined in the
Beacon earnings-driven agent's trigger taxonomy.

Switched from Finnhub's /stock/filings endpoint after discovering its SEC
mirror lags real time by ~3 weeks (verified against AAPL/MSFT/AMZN/NVDA/JPM).
EDGAR's own full-text search is authoritative and same-day.
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
CONSTITUENTS_FILE = ROOT / "data" / "sp500_constituents.csv"
OUTPUT_FILE = ROOT / "data" / "filing_triggers.json"

PAGE_SIZE = 100
RELEVANT_ITEMS = {"2.02", "7.01"}
SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"

# Corrected tracked universe as of 2026-09-21: the original S&P 500-wide scan
# was chosen purely by SEC filing activity, without first checking Bitget
# Demo Trading's own (separate, undocumented, ~25-symbol) tradable universe --
# every one of the original 21 tracked tickers turned out to have no Bitget
# demo pair at all (confirmed empirically: a real order for RPGRUSDT was
# rejected with code 40034 "Parameter RPGRUSDT does not exist"). Narrowed to
# the domestic, 8-K-filing S&P 500 names that DO have a live rToken pair in
# the demo environment (checked against GET /public/symbols with the
# paptrading header). BILI (Bilibili) has a demo pair but is a foreign
# private issuer that files Form 6-K, not 8-K (confirmed: 0 historical 8-K
# filings, 10 recent 6-K) -- structurally incompatible with this 8-K-only
# scanner, so it's excluded rather than silently producing zero triggers.
TRADABLE_ON_BITGET_DEMO = {"EQT", "GOOGL", "MU", "NVDA", "ECHO"}


def load_env():
    if not ENV_FILE.exists():
        sys.exit(f"Missing {ENV_FILE}")
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def load_sp500_ciks():
    if not CONSTITUENTS_FILE.exists():
        sys.exit(f"Missing {CONSTITUENTS_FILE}")
    cik_to_symbol = {}
    with open(CONSTITUENTS_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cik = row["CIK"].strip()
            symbol = row["Symbol"].strip()
            if cik and symbol in TRADABLE_ON_BITGET_DEMO:
                cik_to_symbol[cik.zfill(10)] = symbol
    return cik_to_symbol


def fetch_page(session, headers, startdt, enddt, offset, retries=3):
    params = {"forms": "8-K", "startdt": startdt, "enddt": enddt,
              "from": offset, "size": PAGE_SIZE}
    last_err = None
    for attempt in range(retries):
        try:
            resp = session.get(SEARCH_URL, params=params, headers=headers, timeout=30)
        except requests.exceptions.RequestException as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code != 200:
            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            time.sleep(2 * (attempt + 1))
            continue
        return resp.json(), None
    return None, last_err


def scan(days_back):
    load_env()
    contact = os.environ.get("SEC_CONTACT_EMAIL")
    if not contact:
        sys.exit("SEC_CONTACT_EMAIL not set in .env")
    headers = {"User-Agent": f"BeaconHackathonAgent {contact}"}

    cik_to_symbol = load_sp500_ciks()
    session = requests.Session()

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days_back)
    startdt, enddt = start.isoformat(), end.isoformat()

    print(f"Querying SEC EDGAR full-text search for 8-K filings {startdt}..{enddt}, "
          f"filtering to S&P 500 CIKs and items {sorted(RELEVANT_ITEMS)}", file=sys.stderr)

    first_page, err = fetch_page(session, headers, startdt, enddt, 0)
    if err:
        sys.exit(f"SEC EDGAR query failed: {err}")
    total = first_page["hits"]["total"]["value"]
    print(f"Total raw hits (all forms/items, all companies): {total}", file=sys.stderr)

    all_hits = list(first_page["hits"]["hits"])
    offset = PAGE_SIZE
    while offset < total:
        page, err = fetch_page(session, headers, startdt, enddt, offset)
        if err:
            print(f"  WARNING: page at offset {offset} failed: {err}", file=sys.stderr)
            break
        hits = page["hits"]["hits"]
        if not hits:
            break
        all_hits.extend(hits)
        offset += PAGE_SIZE
        time.sleep(0.3)

    print(f"Fetched {len(all_hits)} raw hits across all pages", file=sys.stderr)

    seen_accessions = set()
    triggers = []
    for h in all_hits:
        src = h["_source"]
        accession = src.get("adsh")
        if not accession or accession in seen_accessions:
            continue
        ciks = src.get("ciks", [])
        items = set(src.get("items", []))
        matching_ciks = [c for c in ciks if c.zfill(10) in cik_to_symbol]
        if not matching_ciks or not (items & RELEVANT_ITEMS):
            continue
        seen_accessions.add(accession)
        symbol = cik_to_symbol[matching_ciks[0].zfill(10)]
        triggers.append({
            "symbol": symbol,
            "trigger_type": "8-K_guidance_or_earnings_item",
            "matched_items": sorted(items & RELEVANT_ITEMS),
            "all_items": sorted(items),
            "filed_date": src.get("file_date"),
            "display_name": src.get("display_names", [None])[0],
            "cik": matching_ciks[0],
            "accession_number": accession,
            "edgar_url": f"https://www.sec.gov/Archives/edgar/data/{int(matching_ciks[0])}/{accession.replace('-', '')}/{accession}-index.htm",
        })

    result = {
        "scan_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": "SEC EDGAR full-text search (efts.sec.gov)",
        "universe": "sp500_bitget_demo_tradable",
        "universe_size": len(cik_to_symbol),
        "days_back": days_back,
        "date_range": [startdt, enddt],
        "item_filter": sorted(RELEVANT_ITEMS),
        "raw_hits_total": total,
        "trigger_count": len(triggers),
        "triggers": triggers,
    }
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(result, indent=2))
    print(f"\nDone. {len(triggers)} S&P 500 triggers (items 2.02/7.01) out of "
          f"{total} total raw 8-K hits in window. Written to {OUTPUT_FILE}", file=sys.stderr)
    return result


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--days-back", type=int, default=3)
    args = p.parse_args()
    out = scan(args.days_back)
    print(json.dumps(out["triggers"], indent=2))
