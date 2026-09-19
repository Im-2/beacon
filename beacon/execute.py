"""EXECUTE: place (or preview) a Bitget paper-trading order for a risk-approved
decision. This module NEVER has a code path that can omit paper-trading mode —
the `paptrading: 1` header is hardcoded and there is no parameter to disable it.

Two ways to run:
  - dry_run=True (default): builds the exact signed request that would be sent
    and returns it without making a network call. Safe to run with placeholder
    credentials — this is how EXECUTE is built/tested before real Bitget demo
    keys exist.
  - dry_run=False: sends the request to Bitget's live REST endpoint with the
    paptrading header, so fills happen in the Demo Trading environment, not on
    a real account. Requires real (non-placeholder) BITGET_* credentials in
    .env. This path has not yet been exercised against a real demo account —
    verify manually before relying on it for the submission log.
"""
import base64
import hashlib
import hmac
import json
import time
import requests
from beacon import config

BASE_URL = "https://api.bitget.com"
ORDER_PATH = "/api/v2/spot/trade/place-order"
SYMBOLS_PATH = "/api/v2/spot/public/symbols"

_symbols_cache = None


def _load_tradable_symbols() -> dict:
    """Public endpoint, no auth needed. Cached per-process."""
    global _symbols_cache
    if _symbols_cache is None:
        resp = requests.get(BASE_URL + SYMBOLS_PATH, timeout=30)
        resp.raise_for_status()
        _symbols_cache = {s["symbol"]: s for s in resp.json().get("data", [])}
    return _symbols_cache


def check_tradable(symbol: str) -> dict:
    bitget_symbol = to_bitget_symbol(symbol)
    symbols = _load_tradable_symbols()
    info = symbols.get(bitget_symbol)
    if info is None:
        return {"tradable": False, "bitget_symbol": bitget_symbol,
                "reason": f"No '{bitget_symbol}' pair found on Bitget spot market."}
    if info.get("status") != "online":
        return {"tradable": False, "bitget_symbol": bitget_symbol,
                "reason": f"'{bitget_symbol}' exists but status is '{info.get('status')}', not 'online'."}
    return {"tradable": True, "bitget_symbol": bitget_symbol, "min_trade_usdt": info.get("minTradeUSDT")}


def _sign(timestamp: str, method: str, path: str, body: str, secret_key: str) -> str:
    prehash = f"{timestamp}{method.upper()}{path}{body}"
    mac = hmac.new(secret_key.encode(), prehash.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def to_bitget_symbol(symbol: str) -> str:
    """Bitget lists US equities as tokenized-stock spot pairs, prefixed with
    'R' (e.g. VLO -> RVLOUSDT), not as the raw ticker. Verified against
    api.bitget.com/api/v2/spot/public/symbols — most S&P 500 names have a
    live 'R<ticker>USDT' pair, but not all (e.g. VMRK, AXON, EBF were not
    found as of this scan). Callers must check tradability before ordering."""
    return f"R{symbol}USDT"


def build_order_request(symbol: str, direction: str, size_usd: float, entry_price: float) -> dict:
    """Constructs (but does not send) a spot market order. direction: 'long' or 'short'.
    Paper trading only — this function has no way to target the live account."""
    side = "buy" if direction == "long" else "sell"
    body_obj = {
        "symbol": to_bitget_symbol(symbol),
        "side": side,
        "orderType": "market",
        "force": "gtc",
        "size": f"{size_usd:.2f}",
        "clientOid": f"beacon-{symbol}-{int(time.time())}",
    }
    body = json.dumps(body_obj, separators=(",", ":"))
    return {"method": "POST", "path": ORDER_PATH, "body": body, "body_obj": body_obj}


def place_paper_order(symbol: str, direction: str, size_usd: float, entry_price: float,
                       stop_loss_pct: float, take_profit_pct: float, dry_run: bool = True) -> dict:
    tradability = check_tradable(symbol)
    if not tradability["tradable"]:
        return {
            "dry_run": dry_run, "paper_trading": True, "tradability": tradability,
            "status": "SKIPPED_NOT_TRADABLE_ON_BITGET", "reason": tradability["reason"],
        }

    req = build_order_request(symbol, direction, size_usd, entry_price)

    result = {
        "dry_run": dry_run,
        "paper_trading": True,   # hardcoded; there is no code path that unsets this
        "tradability": tradability,
        "request": req,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct,
    }

    if not config.bitget_configured():
        result["status"] = "SKIPPED_NO_CREDENTIALS"
        result["reason"] = "BITGET_API_KEY/SECRET_KEY/PASSPHRASE are still placeholders in .env."
        return result

    if dry_run:
        result["status"] = "DRY_RUN_NOT_SENT"
        return result

    creds = config.bitget_creds()
    timestamp = str(int(time.time() * 1000))
    signature = _sign(timestamp, req["method"], req["path"], req["body"], creds["secret_key"])
    headers = {
        "ACCESS-KEY": creds["api_key"],
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": creds["passphrase"],
        "Content-Type": "application/json",
        "paptrading": "1",   # Bitget Demo Trading flag — hardcoded, not configurable here
    }
    resp = requests.post(BASE_URL + req["path"], headers=headers, data=req["body"], timeout=30)
    result["status"] = "SENT"
    result["http_status"] = resp.status_code
    try:
        result["response"] = resp.json()
    except ValueError:
        result["response"] = resp.text[:500]
    return result
