#!/usr/bin/env python3
"""
Step 4: checks every open paper position against its stop-loss/take-profit,
closes it via a paper order if triggered, and logs the outcome (P&L, hold
time). Run frequently (every 30-60 min) during market hours per Step 5.

Also refreshes unrealized_pnl_usd on every open position on every run (used by
risk.py's daily-drawdown circuit breaker), even when nothing closes.
"""
import json
import sys
from datetime import datetime, timezone
from beacon import config, sense, execute, state, logger


def current_price_for(symbol: str) -> float:
    """Cross-asset proxy positions (execute.CROSS_ASSET_PROXY, e.g. "BTC") are
    real crypto, not equities -- sense.get_quote() calls Finnhub's stock-quote
    endpoint, which doesn't have a "BTC" ticker. Route those through Bitget's
    own public price endpoint instead; everything else keeps using Finnhub."""
    if symbol == execute.CROSS_ASSET_PROXY:
        return execute.get_public_price(execute.to_bitget_symbol(symbol))
    return sense.get_quote(symbol)["current_price"]


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
    base_qty = None
    if pos["direction"] == "long" and not dry_run:
        # Sell the quantity this position actually bought, never more than the
        # account holds. size_usd / current_price is wrong for a losing long:
        # at the stop-loss price it asks for MORE coin than the entry buy
        # received, which either gets rejected (43012 Insufficient balance) or
        # silently eats into unrelated holdings of the same coin.
        held = execute.get_spot_available(execute.base_coin_for(pos["symbol"]))
        base_qty = min(held, pos["size_usd"] / pos["entry_price"])
    order = execute.place_paper_order(
        symbol=pos["symbol"], direction=close_direction, size_usd=pos["size_usd"],
        entry_price=current_price, stop_loss_pct=0, take_profit_pct=0, dry_run=dry_run,
        base_qty=base_qty,
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
        try:
            current_price = current_price_for(pos["symbol"])
        except Exception as e:
            # Right after the laptop wakes, DNS/VPN often isn't up yet -- keep
            # the position exactly as it was and retry next cycle rather than
            # crashing the whole run (which also skipped export + publish).
            print(f"PRICE UNAVAILABLE for {pos['symbol']} ({e}) -- keeping last known state.", file=sys.stderr)
            still_open.append(pos)
            continue
        pnl_pct = unrealized_pnl_pct(pos["direction"], pos["entry_price"], current_price)
        pos["unrealized_pnl_usd"] = round(pos["size_usd"] * pnl_pct / 100.0, 2)
        pos["current_price"] = current_price

        trigger = check_position(pos, current_price)
        if trigger:
            try:
                closed = close_position(pos, current_price, trigger, dry_run)
            except Exception as e:
                print(f"CLOSE ATTEMPT FAILED for {pos['symbol']} ({trigger}): {e} -- still open, will retry.",
                      file=sys.stderr)
                still_open.append(pos)
                continue
            status = closed["close_order"].get("status")
            record = {
                "symbol": pos["symbol"], "trigger_type": "position_management",
                "category": pos.get("category"), "order": closed["close_order"],
                "judgment": None, "risk_result": None, "close_reason": trigger,
            }
            if pos.get("is_test_fixture"):
                record["is_test_fixture"] = True
            if status != "SENT":
                # Same class of bug as the old PGR record: never book a close
                # (or a realized P&L) that the exchange didn't actually accept.
                record["outcome"] = f"close_failed_{(status or 'unknown').lower()}"
                logger.log_decision(record)
                still_open.append(pos)
                print(f"CLOSE NOT FILLED for {pos['symbol']} ({trigger}): {status} -- still open, will retry.",
                      file=sys.stderr)
                continue
            portfolio_state.setdefault("closed_positions", []).append(closed)
            record.update({
                "outcome": f"closed_{trigger}",
                "realized_pnl_pct": closed["realized_pnl_pct"],
                "realized_pnl_usd": closed["realized_pnl_usd"],
                "hold_time_hours": closed["hold_time_hours"],
            })
            logger.log_decision(record)
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
