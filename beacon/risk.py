"""RISK: deterministic, non-LLM gate. The JUDGE step's output must pass every
check here before an order is ever placed. Any violation REJECTS the trade
outright (no silent clipping/adjustment) so the log stays fully transparent
about what the LLM proposed vs what was actually allowed to execute."""
from beacon import config, state


def evaluate(judgment: dict, symbol: str, portfolio_state: dict) -> dict:
    """Returns {"approved": bool, "reason": str, "checks": {...}}"""
    checks = {}
    decision = judgment.get("decision", "no-trade")

    if decision == "no-trade":
        return {"approved": False, "reason": "LLM decision was no-trade.", "checks": checks}

    size_pct = float(judgment.get("position_size_pct_of_capital", 0) or 0)
    checks["position_size_cap"] = size_pct <= config.RISK["max_position_pct_per_trade"]

    open_positions = portfolio_state.get("open_positions", [])
    checks["max_concurrent_positions"] = len(open_positions) < config.RISK["max_concurrent_positions"]

    daily_pnl = state.today_realized_pnl(portfolio_state)
    daily_pnl_pct = (daily_pnl / config.RISK["allocated_capital_usd"]) * 100 if config.RISK["allocated_capital_usd"] else 0
    checks["daily_drawdown_circuit_breaker"] = daily_pnl_pct > -config.RISK["max_daily_drawdown_pct"]

    existing_same_symbol = [p for p in open_positions if p["symbol"] == symbol]
    averaging_into_loser = False
    if config.RISK["no_averaging_into_loser"] and existing_same_symbol:
        for p in existing_same_symbol:
            if p.get("unrealized_pnl_usd", 0) < 0 and p.get("direction") == decision:
                averaging_into_loser = True
    checks["no_averaging_into_loser"] = not averaging_into_loser

    failed = [name for name, passed in checks.items() if not passed]
    approved = len(failed) == 0
    reason = "All risk checks passed." if approved else f"Rejected: failed {', '.join(failed)}"
    return {"approved": approved, "reason": reason, "checks": checks, "daily_pnl_pct": round(daily_pnl_pct, 3)}
