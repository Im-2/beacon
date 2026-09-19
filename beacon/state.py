"""Local portfolio/state tracking for the paper-trading agent. Single source
of truth for open positions, daily P&L, and which triggers have already been
processed (so repeated cron runs don't re-fire on the same event)."""
import json
from datetime import datetime, timezone
from beacon import config

STATE_FILE = config.DATA_DIR / "portfolio_state.json"
PROCESSED_FILE = config.DATA_DIR / "processed_triggers.json"


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {
            "capital_usd": config.RISK["allocated_capital_usd"],
            "open_positions": [],   # list of {symbol, direction, entry_price, size_usd, stop_loss, take_profit, opened_at, category}
            "closed_positions": [],
            "daily_pnl": {},        # date -> realized+unrealized pnl usd, refreshed on each check
        }
    return json.loads(STATE_FILE.read_text())


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def load_processed() -> set:
    if not PROCESSED_FILE.exists():
        return set()
    return set(json.loads(PROCESSED_FILE.read_text()))


def mark_processed(trigger_key: str):
    processed = load_processed()
    processed.add(trigger_key)
    PROCESSED_FILE.write_text(json.dumps(sorted(processed), indent=2))


def today_realized_pnl(state: dict) -> float:
    today = _today()
    total = 0.0
    for p in state.get("closed_positions", []):
        if p.get("closed_at", "").startswith(today):
            total += p.get("realized_pnl_usd", 0.0)
    return total
