import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"


def load_env():
    if not ENV_FILE.exists():
        raise SystemExit(f"Missing {ENV_FILE}")
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_env()


def _require(name):
    val = os.environ.get(name)
    if not val or val.startswith("REPLACE_WITH_"):
        raise SystemExit(f"{name} is not set (still a placeholder) in .env — fill it in before running this step.")
    return val


def is_configured(name: str) -> bool:
    """True if the named env var is set to something other than a placeholder."""
    val = os.environ.get(name)
    return bool(val) and not val.startswith("REPLACE_WITH_")


def finnhub_key():
    return _require("FINNHUB_API_KEY")


def sec_contact():
    return _require("SEC_CONTACT_EMAIL")


def anthropic_key():
    return _require("ANTHROPIC_API_KEY")


def qwen_key():
    return _require("QWEN_API_KEY")


# Which LLM backs the JUDGE step. "mock" is used automatically whenever no
# real key is configured for the selected provider — see judge.py.
JUDGE_PROVIDER = os.environ.get("JUDGE_PROVIDER", "qwen").strip().lower()


def judge_llm_configured() -> bool:
    if JUDGE_PROVIDER == "qwen":
        return is_configured("QWEN_API_KEY")
    if JUDGE_PROVIDER == "anthropic":
        return is_configured("ANTHROPIC_API_KEY")
    return False


def bitget_creds():
    return {
        "api_key": _require("BITGET_API_KEY"),
        "secret_key": _require("BITGET_SECRET_KEY"),
        "passphrase": _require("BITGET_PASSPHRASE"),
    }


def bitget_configured() -> bool:
    return (is_configured("BITGET_API_KEY") and is_configured("BITGET_SECRET_KEY")
            and is_configured("BITGET_PASSPHRASE"))


# --- Risk controls (deterministic, not LLM-adjustable) ---
# Proposed defaults — confirm/adjust with user before first live execution.
RISK = {
    "allocated_capital_usd": 10_000.0,   # nominal paper-trading capital base for position sizing
    "max_position_pct_per_trade": 5.0,   # max % of allocated capital in a single position
    "max_concurrent_positions": 5,
    "max_daily_drawdown_pct": 3.0,       # halts new entries for the day if realized+unrealized daily P&L drops this much
    "no_averaging_into_loser": True,     # reject new entry on a symbol whose existing open positions are net losing
    "max_proxy_exposure_pct": 10.0,
    "max_holding_hours": 48,             # close at market if neither stop-loss nor take-profit hit by then      # cap on TOTAL cross-asset proxy (BTC) exposure across all originating tickers
}

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
