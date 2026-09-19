#!/usr/bin/env python3
"""
Step 4: checks every open paper position against its stop-loss/take-profit,
closes it via a paper order if triggered, and logs the outcome (P&L, hold
time). Run frequently (every 30-60 min) during market hours per Step 5.

Also refreshes unrealized_pnl_usd on every open position on every run (used by
risk.py's daily-drawdown circuit breaker), even when nothing closes.
"""
import json
from datetime import datetime, timezone
from beacon import config, sense, execute, state, logger


def unrealized_pnl_pct(direction: str, entry_price: float, current_price: float) -> float:
    if direction == "long":
        return (current_price - entry_price) / entry_price * 100.0
    return (entry_price - current_price) / entry_price * 100.0


def check_position(pos: dict, current_price: float) -> str | None:
    """Returns 'stop_loss', 'take_profit', or None."""
    pnl_pct = unrealized_pnl_pct(pos["direction"], pos["entry_price"], current_price)
    if pnl_pct <= -abs(pos["stop_loss_pct"]):
        return "stop_loss"
    if pnl_pct >= abs(pos["take_profit_pct"]):
        return "take_profit"
    return None


def close_position(pos: dict, current_price: float, reason: str, dry_run: bool) -> dict:
    close_direction = "short" if pos["direction"] == "long" else "long"  # opposite side to exit
    order = execute.place_paper_order(
        symbol=pos["symbol"], direction=close_direction, size_usd=pos["size_usd"],
        entry_price=current_price, stop_loss_pct=0, take_profit_pct=0, dry_run=dry_run,
    )
    pnl_pct = unrealized_pnl_pct(pos["direction"], pos["entry_price"], current_price)
    pnl_usd = pos["size_usd"] * pnl_pct / 100.0
    opened_at = datetime.fromisoformat(pos["opened_at"])
    hold_time_hours = (datetime.now(timezone.utc) - opened_at).total_seconds() / 3600.0
    return {
        **pos,
        "closed_at": datetime.now(timezone.utc).isoformat(),
        "close_price": current_price,
        "close_reason": reason,
        "realized_pnl_pct": round(pnl_pct, 4),
        "realized_pnl_usd": round(pnl_usd, 2),
        "hold_time_hours": round(hold_time_hours, 2),
        "close_order": order,
    }


def run(dry_run: bool = None):
    portfolio_state = state.load_state()
    open_positions = portfolio_state.get("open_positions", [])
    if not open_positions:
        print("No open positions.")
        return

    if dry_run is None:
        dry_run = not config.bitget_configured()

    still_open = []
    for pos in open_positions:
        quote = sense.get_quote(pos["symbol"])
        current_price = quote["current_price"]
        pnl_pct = unrealized_pnl_pct(pos["direction"], pos["entry_price"], current_price)
        pos["unrealized_pnl_usd"] = round(pos["size_usd"] * pnl_pct / 100.0, 2)

        trigger = check_position(pos, current_price)
        if trigger:
            closed = close_position(pos, current_price, trigger, dry_run)
            portfolio_state.setdefault("closed_positions", []).append(closed)
            logger.log_decision({
                "symbol": pos["symbol"], "trigger_type": "position_management",
                "category": pos.get("category"), "outcome": f"closed_{trigger}",
                "order": closed["close_order"],
                "judgment": None, "risk_result": None,
                "realized_pnl_pct": closed["realized_pnl_pct"],
                "realized_pnl_usd": closed["realized_pnl_usd"],
                "hold_time_hours": closed["hold_time_hours"],
            })
            print(f"CLOSED {pos['symbol']} ({trigger}): {closed['realized_pnl_pct']:.2f}% / "
                  f"${closed['realized_pnl_usd']:.2f} after {closed['hold_time_hours']:.1f}h")
        else:
            still_open.append(pos)
            print(f"OPEN {pos['symbol']}: unrealized {pnl_pct:.2f}% (SL {pos['stop_loss_pct']}% / "
                  f"TP {pos['take_profit_pct']}%)")

    portfolio_state["open_positions"] = still_open
    state.save_state(portfolio_state)


if __name__ == "__main__":
    run()
