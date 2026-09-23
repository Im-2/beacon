"""Shared state for the Finnhub earnings-news trigger.

logs/news_signals.jsonl is append-only: one record per verdict. An item that
passes the keyword filter gets a "queued" record first and a "judged_*"
record once JUDGE runs; the dashboard export keeps the latest record per
news_key. Skipped headlines live here rather than in decisions.jsonl, so
~200 irrelevant headlines a day don't bury the real decisions in History.
"""
import json
import re
from datetime import datetime, timezone
from beacon import config

NEWS_LOG = config.LOG_DIR / "news_signals.jsonl"
QUEUE_FILE = config.DATA_DIR / "news_queue.json"
SEEN_FILE = config.DATA_DIR / "news_seen.json"

TICKERS = ["EQT", "GOOGL", "MU", "NVDA", "ECHO"]
LOOKBACK_HOURS = 24
MAX_JUDGE_PER_CYCLE = 5

KEYWORDS = re.compile(
    r"\b(earnings|eps|revenues?|results?|quarter(ly)?|q3|q4|guidance|outlook|forecast(s|ed|ing)?|"
    r"estimates?|consensus|beat(s|ing)?|miss(es|ed)?|previews?|pre-?announce(s|d|ment)?|"
    r"analysts?|upgrade(s|d)?|downgrade(s|d)?|price targets?)\b",
    re.IGNORECASE,
)


def news_key(symbol: str, finnhub_id) -> str:
    # The same article is often filed under several tickers; each ticker gets
    # its own verdict, so the key is per (ticker, article).
    return f"{symbol}:{finnhub_id}"


def matched_keywords(text: str) -> list:
    return sorted({m.group(0).lower() for m in KEYWORDS.finditer(text or "")})


def append_log(record: dict):
    record.setdefault("logged_at_utc", datetime.now(timezone.utc).isoformat())
    with open(NEWS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def load_seen() -> set:
    return set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()


def save_seen(seen: set):
    SEEN_FILE.write_text(json.dumps(sorted(seen)))


def load_queue() -> list:
    return json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []


def save_queue(queue: list):
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))
