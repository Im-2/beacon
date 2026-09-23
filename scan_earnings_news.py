#!/usr/bin/env python3
"""Finnhub earnings-news trigger, stage 1: fetch + keyword pre-filter.

Pulls company news for the 5-ticker universe published in the last
LOOKBACK_HOURS. Each (ticker, article) is handled exactly once:
- no earnings keyword in headline/summary -> logged as skipped, never judged
- keyword match -> logged as queued and appended to data/news_queue.json;
  decision_engine.py --mode live judges up to MAX_JUDGE_PER_CYCLE of them per
  cycle, oldest first.
No LLM calls here.
"""
import sys
import time
from datetime import date, datetime, timedelta, timezone
import requests
from beacon import config, news


def fetch(symbol: str) -> list:
    resp = requests.get(
        "https://finnhub.io/api/v1/company-news",
        params={"symbol": symbol, "from": str(date.today() - timedelta(days=2)),
                "to": str(date.today()), "token": config.finnhub_key()},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json() or []


def main():
    cutoff = time.time() - news.LOOKBACK_HOURS * 3600
    seen = news.load_seen()
    queue = news.load_queue()
    counts = {"new": 0, "skipped": 0, "queued": 0}

    for symbol in news.TICKERS:
        try:
            items = fetch(symbol)
        except Exception as e:
            print(f"{symbol}: news fetch failed ({e}) -- will retry next cycle.", file=sys.stderr)
            continue
        for item in sorted(items, key=lambda i: i.get("datetime", 0)):
            if item.get("datetime", 0) < cutoff:
                continue
            key = news.news_key(symbol, item.get("id"))
            if key in seen:
                continue
            seen.add(key)
            counts["new"] += 1
            base = {
                "news_key": key,
                "symbol": symbol,
                "finnhub_id": item.get("id"),
                "headline": item.get("headline"),
                "source": item.get("source"),
                "url": item.get("url"),
                "published_utc": datetime.fromtimestamp(item.get("datetime", 0), timezone.utc).isoformat(),
            }
            keywords = news.matched_keywords(f"{item.get('headline', '')} {item.get('summary', '')}")
            if not keywords:
                news.append_log({**base, "verdict": "skipped_not_earnings_related"})
                counts["skipped"] += 1
                continue
            if not news.names_company(symbol, item.get("headline")):
                news.append_log({**base, "verdict": "skipped_off_ticker", "matched_keywords": keywords})
                counts["skipped"] += 1
                continue
            entry = {**base, "summary": item.get("summary"), "matched_keywords": keywords}
            queue.append(entry)
            news.append_log({**entry, "verdict": "queued"})
            counts["queued"] += 1

    queue.sort(key=lambda q: q["published_utc"], reverse=True)
    news.save_queue(queue)
    news.save_seen(seen)
    print(f"News scan: {counts['new']} new items in last {news.LOOKBACK_HOURS}h -- "
          f"{counts['skipped']} skipped (not earnings-related or not about the ticker), "
          f"{counts['queued']} queued for JUDGE. "
          f"Queue now {len(queue)}.")


if __name__ == "__main__":
    main()
