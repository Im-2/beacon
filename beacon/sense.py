"""SENSE: pull real market/filing data. No LLM calls here — pure data retrieval."""
import re
import requests
from beacon import config


def _sec_headers():
    return {"User-Agent": f"BeaconHackathonAgent {config.sec_contact()}"}


def _strip_html(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_filing_text(cik: str, accession: str, max_chars: int = 8000) -> dict:
    """Fetch the primary document (preferring an EX-99 press release, which is
    where 7.01/2.02 substantive content usually lives) for a given filing."""
    acc_nodash = accession.replace("-", "")
    cik_int = str(int(cik))
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{accession}-index.htm"
    resp = requests.get(index_url, headers=_sec_headers(), timeout=30)
    resp.raise_for_status()
    links = re.findall(r'href="([^"]+\.htm)"', resp.text)
    doc_links = [l for l in links if "/Archives/edgar/data/" in l]

    press_release = next((l for l in doc_links if re.search(r"ex.?99", l, re.I)), None)
    primary = press_release or (doc_links[0] if doc_links else None)
    if not primary:
        return {"index_url": index_url, "document_url": None, "text": "", "error": "no document found in index"}

    doc_url = "https://www.sec.gov" + primary if primary.startswith("/") else primary
    doc_resp = requests.get(doc_url, headers=_sec_headers(), timeout=30)
    doc_resp.raise_for_status()
    text = _strip_html(doc_resp.text)
    return {
        "index_url": index_url,
        "document_url": doc_url,
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


def get_quote(symbol: str) -> dict:
    resp = requests.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": symbol, "token": config.finnhub_key()},
        timeout=15,
    )
    resp.raise_for_status()
    d = resp.json()
    return {
        "current_price": d.get("c"),
        "change": d.get("d"),
        "percent_change": d.get("dp"),
        "day_high": d.get("h"),
        "day_low": d.get("l"),
        "day_open": d.get("o"),
        "previous_close": d.get("pc"),
        "quote_timestamp": d.get("t"),
    }


def get_basic_metrics(symbol: str) -> dict:
    resp = requests.get(
        "https://finnhub.io/api/v1/stock/metric",
        params={"symbol": symbol, "metric": "all", "token": config.finnhub_key()},
        timeout=15,
    )
    resp.raise_for_status()
    m = resp.json().get("metric", {})
    return {
        "market_cap_musd": m.get("marketCapitalization"),
        "avg_volume_10d_m": m.get("10DayAverageTradingVolume"),
        "52w_high": m.get("52WeekHigh"),
        "52w_low": m.get("52WeekLow"),
    }


def get_earnings_estimate(symbol: str, target_date: str) -> dict:
    """Consensus EPS/revenue estimate for a specific reporting date, from the
    earnings calendar (used for 2.02 and anticipatory-track triggers)."""
    resp = requests.get(
        "https://finnhub.io/api/v1/calendar/earnings",
        params={"from": target_date, "to": target_date, "token": config.finnhub_key()},
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json().get("earningsCalendar", [])
    for r in rows:
        if r.get("symbol") == symbol:
            return r
    return {}


def sense_for_trigger(trigger: dict) -> dict:
    symbol = trigger["symbol"]
    result = {
        "symbol": symbol,
        "trigger_type": trigger["trigger_type"],
        "matched_items": trigger.get("matched_items"),
        "filed_date": trigger.get("filed_date"),
        "quote": get_quote(symbol),
        "metrics": get_basic_metrics(symbol),
    }
    if trigger.get("accession_number"):
        cik = trigger.get("cik")
        filing = fetch_filing_text(cik, trigger["accession_number"]) if cik else None
        result["filing"] = filing
    if trigger.get("trigger_type") == "finnhub_earnings_news":
        result["news"] = trigger["news"]
    if trigger.get("trigger_type") == "anticipatory_earnings_positioning":
        result["anticipatory"] = {
            "report_date": trigger.get("report_date"),
            "consensus_eps_estimate": trigger.get("consensus_eps_estimate"),
            "consensus_revenue_estimate": trigger.get("consensus_revenue_estimate"),
            "note": "Pre-earnings positioning: no actual EPS/revenue exists yet. Judgment must be based "
                    "on consensus estimate positioning, current price/valuation context, and general risk "
                    "framing ahead of the confirmed report date — not on a surprise that hasn't happened.",
        }
    return result
