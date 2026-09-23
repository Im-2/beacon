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
    r"\b(earnings|eps|revenues?|results?|quarterly|q3|q4|guidance|outlook|forecast(s|ed|ing)?|"
    r"estimates?|consensus|previews?|pre-?announce(s|d|ment)?|analysts?|price targets?)\b",
    re.IGNORECASE,
)

# Words that only mean something earnings-related in the right company:
# "beat Meta's Muse", "burned billions this quarter", "nuclear upgrades" all
# got through when these counted on their own. Each needs a context word
# within CONTEXT_WINDOW words (either side) in the headline+summary.
CONTEXT_WINDOW = 8
_EARNINGS_CONTEXT = re.compile(
    r"^(eps|earnings|revenues?|sales|profits?|results?|estimates?|expectations?|consensus|"
    r"guidance|forecasts?|margins?|income)$", re.IGNORECASE)
_RATING_CONTEXT = re.compile(
    r"^(analysts?|ratings?|rated|buy|sell|hold|overweight|underweight|outperform|underperform|"
    r"neutral|target|stock|shares)$", re.IGNORECASE)
CONTEXTUAL = [
    (re.compile(r"^(beat(s|ing)?|miss(es|ed)?|quarters?)$", re.IGNORECASE), _EARNINGS_CONTEXT),
    (re.compile(r"^(upgrade(s|d)?|downgrade(s|d)?)$", re.IGNORECASE), _RATING_CONTEXT),
]


# Company names match case-insensitively; tickers only as uppercase words
# (so "MU"/"ECHO" don't match the ordinary words). Finnhub tags lots of
# off-ticker articles to these symbols (a Sandisk story under MU, an Intel
# story under NVDA), so the headline must actually name the company.
ALIASES = {
    "EQT": (["EQT Corp", "EQT Corporation"], ["EQT"]),
    "GOOGL": (["Alphabet", "Google"], ["GOOGL", "GOOG"]),
    "MU": (["Micron"], ["MU"]),
    "NVDA": (["Nvidia"], ["NVDA"]),
    "ECHO": (["EchoStar"], ["ECHO"]),
}
MAX_AGE_HOURS = 24


def names_company(symbol: str, headline: str) -> bool:
    names, tickers = ALIASES.get(symbol, ([], [symbol]))
    headline = headline or ""
    return (any(re.search(r"\b" + re.escape(n) + r"\b", headline, re.IGNORECASE) for n in names)
            or any(re.search(r"\b" + re.escape(t) + r"\b", headline) for t in tickers))


def news_key(symbol: str, finnhub_id) -> str:
    # The same article is often filed under several tickers; each ticker gets
    # its own verdict, so the key is per (ticker, article).
    return f"{symbol}:{finnhub_id}"


def matched_keywords(text: str) -> list:
    text = text or ""
    found = {m.group(0).lower() for m in KEYWORDS.finditer(text)}
    words = re.findall(r"[A-Za-z0-9'-]+", text)
    for i, w in enumerate(words):
        for word_re, context_re in CONTEXTUAL:
            if word_re.match(w):
                window = words[max(0, i - CONTEXT_WINDOW): i] + words[i + 1: i + 1 + CONTEXT_WINDOW]
                if any(context_re.match(c) for c in window):
                    found.add(w.lower())
    return sorted(found)


def screen(symbol: str, headline: str, summary: str) -> tuple:
    """(verdict_if_skipped_or_None, matched_keywords) -- the full pre-filter."""
    keywords = matched_keywords(f"{headline or ''} {summary or ''}")
    if not keywords:
        return "skipped_not_earnings_related", keywords
    if not names_company(symbol, headline):
        return "skipped_off_ticker", keywords
    return None, keywords


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
