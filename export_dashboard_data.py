#!/usr/bin/env python3
"""Flattens logs/decisions.jsonl + data/portfolio_state.json into a single
dashboard_data.json the frontend can fetch() directly, mirroring the
market_data.json pattern (backend computes, frontend just renders).

Honesty rule this script exists to enforce: a record is "mock" (not a real
trading decision) if judgment.mock, gate_result.mock, or the top-level
is_test_fixture flag is set -- this covers both the pre-Qwen-wiring
placeholder decisions (Sept 18, QWEN_API_KEY not yet configured) and this
session's explicitly-authorized synthetic-judgment test fixtures. Every
record is still included in the full decision list (nothing hidden from the
audit trail), but summary stats (win rate, cumulative P&L) only count real
ones, and every record carries is_mock so the frontend can badge it clearly.
"""
import json
from datetime import datetime, timezone
from beacon import config, state, execute, news, judge

NEWS_EXPORT_LIMIT = 400
EXECUTION_LABELS = {
    "executed_direct_rtoken": "Direct rToken",
    "executed_cross_asset_proxy": "BTC proxy",
    "cross_asset_fallback_unavailable_for_short_direction": "Short unavailable",
    "rejected_by_risk_controls": "Rejected by risk",
    "cross_asset_proxy_rejected_by_risk": "Rejected by risk",
}

DECISIONS_LOG = config.LOG_DIR / "decisions.jsonl"
HEARTBEAT_FILE = config.DATA_DIR / "last_cycle.json"
OUT_FILE = config.ROOT / "dashboard_data.json"

# Mirrors the Beacon_ScanAndLive Task Scheduler trigger (StartBoundary
# 2026-09-18 15:33 machine-local, repeating every 3h). Keep in sync if the
# task's schedule changes.
SCAN_SCHEDULE_ANCHOR = datetime(2026, 9, 18, 15, 33).astimezone()
SCAN_SCHEDULE_INTERVAL_HOURS = 3

STATUS_MAP = {
    "trigger_fired_filtered_non_substantive": "filtered",
    "no_trade_llm_decision": "notrade",
    "rejected_by_risk_controls": "rejected",
    "cross_asset_proxy_rejected_by_risk": "rejected",
    "cross_asset_proxy_price_unavailable": "rejected",
    "preview_pending_approval_not_executed": "pending",
    "executed_direct_rtoken": "approved",
    "executed_cross_asset_proxy": "approved",
    "cross_asset_fallback_unavailable_for_short_direction": "skipped",
    "closed_stop_loss": "closed",
    "closed_take_profit": "closed",
    "test_fixture_dry_run": "filtered",
}


def status_for(outcome: str) -> str:
    if outcome in STATUS_MAP:
        return STATUS_MAP[outcome]
    if outcome and (outcome.startswith("cross_asset_proxy_not_sent_") or outcome.startswith("execute_not_sent_")
                    or outcome.startswith("close_failed_")):
        return "rejected"
    return "other"


def trigger_label(record: dict) -> str:
    items = record.get("matched_items") or []
    if "2.02" in items:
        return "2.02 Earnings"
    if "7.01" in items:
        return "7.01 Guidance"
    ttype = record.get("trigger_type") or ""
    if ttype == "anticipatory_earnings_positioning":
        return "Anticipatory"
    if ttype == "position_management":
        return "Position Mgmt"
    if ttype == "TEST_FIXTURE":
        return "Test Fixture"
    if ttype == "finnhub_earnings_news":
        return "News"
    return ttype or "—"


def is_mock_record(record: dict) -> bool:
    j = record.get("judgment") or {}
    g = record.get("gate_result") or {}
    return bool(j.get("mock")) or bool(g.get("mock")) or bool(record.get("is_test_fixture"))


def is_cross_asset_record(record: dict) -> bool:
    if record.get("execution_leg") == "cross_asset_proxy":
        return True
    outcome = record.get("outcome") or ""
    return outcome.startswith("cross_asset_proxy_") or outcome == "cross_asset_fallback_unavailable_for_short_direction"


def date_label(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return "—"
    return f"{dt:%b} {dt.day}"


def build_sense_text(record: dict) -> str:
    lines = []
    ttype = record.get("trigger_type") or ""
    if ttype == "anticipatory_earnings_positioning":
        lines.append("Anticipatory earnings positioning (pre-report, no filing trigger yet).")
    elif ttype == "position_management":
        lines.append("Open-position check against stop-loss/take-profit (30-min cycle).")
    elif ttype == "TEST_FIXTURE":
        lines.append("Manual pipeline test fixture, not a real SEC filing trigger.")
    elif ttype == "finnhub_earnings_news":
        n = record.get("news") or {}
        lines.append(f"Finnhub news ({n.get('source')}, {n.get('published_utc')}):")
        lines.append(n.get("headline") or "")
        if n.get("url"):
            lines.append(f"Source: {n['url']}")
    else:
        items = record.get("matched_items") or []
        if items:
            lines.append(f"SEC Form 8-K, item(s) {', '.join(items)}.")
        if record.get("filed_date"):
            lines.append(f"Filed: {record['filed_date']}")
    if record.get("edgar_url"):
        lines.append(f"Source: {record['edgar_url']}")
    return "\n".join(lines) if lines else "No additional Sense detail recorded."


def build_judge_block(record: dict) -> dict:
    j = record.get("judgment") or {}
    g = record.get("gate_result") or {}
    if j:
        heading = "Judge"
        text = j.get("rationale") or j.get("tone_assessment") or "(no rationale recorded)"
        if j.get("mock"):
            text = "[MOCK / TEST FIXTURE — not a real LLM output] " + text
        return {"heading": heading, "text": text, "neutral": False}
    if g:
        heading = "Judge (Gate Check)"
        text = g.get("reason") or "(no gate reason recorded)"
        if g.get("mock"):
            text = "[MOCK gate check — no real LLM call] " + text
        return {"heading": heading, "text": text, "neutral": False}
    return {"heading": "Judge", "text": "Not reached.", "neutral": True}


def build_risk_lines(record: dict) -> list:
    r = record.get("risk_result") or {}
    checks = r.get("checks") or {}
    if not checks:
        return []
    j = record.get("judgment") or {}
    lines = []
    if "position_size_cap" in checks:
        lines.append(f"Position size cap: {'passed' if checks['position_size_cap'] else 'failed'} "
                      f"({j.get('position_size_pct_of_capital', '—')}% of {config.RISK['max_position_pct_per_trade']}% cap)")
    if "max_concurrent_positions" in checks:
        lines.append(f"Concurrent positions: {'passed' if checks['max_concurrent_positions'] else 'failed'} "
                      f"(cap {config.RISK['max_concurrent_positions']})")
    if "daily_drawdown_circuit_breaker" in checks:
        lines.append(f"Daily drawdown breaker: {'passed' if checks['daily_drawdown_circuit_breaker'] else 'failed'} "
                      f"({r.get('daily_pnl_pct', 0)}% of {config.RISK['max_daily_drawdown_pct']}% limit)")
    if "no_averaging_into_loser" in checks:
        lines.append(f"No averaging into losers: {'passed' if checks['no_averaging_into_loser'] else 'failed'}")
    return lines


def order_reject_reason(order: dict) -> str | None:
    return order.get("reason") or (order.get("response") or {}).get("msg")


def build_execute_block(record: dict) -> dict:
    outcome = record.get("outcome") or ""
    symbol = record.get("symbol")
    status = status_for(outcome)
    order = record.get("rtoken_order") or record.get("cross_asset_order") or record.get("order") or {}
    if outcome == "executed_direct_rtoken":
        return {"text": f"Direct rToken execution: {symbol} — order {order.get('status')}.", "kind": "ok"}
    if outcome == "executed_cross_asset_proxy":
        return {"text": record.get("cross_asset_note") or "Cross-asset proxy order executed.", "kind": "ok"}
    if status == "filtered":
        return {"text": "No order placed — filtered before a directional judgment was made.", "kind": "neutral"}
    if status == "notrade":
        return {"text": "No order placed — Judge decision was no-trade.", "kind": "neutral"}
    if status == "pending":
        return {"text": "Risk-approved but not yet executed (preview mode).", "kind": "neutral"}
    if status == "closed":
        pnl = record.get("realized_pnl_usd")
        pnl_txt = f"${pnl:.2f}" if isinstance(pnl, (int, float)) else "—"
        return {"text": f"Position closed ({outcome.replace('closed_', '')}). Realized P&L: {pnl_txt}.", "kind": "ok"}
    if outcome == "cross_asset_fallback_unavailable_for_short_direction":
        return {"text": record.get("cross_asset_note") or "Cross-asset fallback unavailable for short direction.", "kind": "neutral"}
    if status == "rejected":
        reason = order_reject_reason(order)
        return {"text": f"No order placed — {outcome}." + (f" ({reason})" if reason else ""), "kind": "blocked"}
    return {"text": f"Outcome: {outcome}", "kind": "neutral"}


def normalize_decision(record: dict) -> dict:
    j = record.get("judgment") or {}
    r = record.get("risk_result") or {}
    outcome = record.get("outcome") or ""
    is_cross_asset = is_cross_asset_record(record)
    judge_block = build_judge_block(record)
    execute_block = build_execute_block(record)

    return {
        "timestamp_utc": record.get("timestamp_utc"),
        "date_label": date_label(record.get("timestamp_utc") or ""),
        "symbol": record.get("symbol"),
        "trigger_label": trigger_label(record),
        "category": record.get("category"),
        "decision": j.get("decision"),
        "conviction": j.get("conviction_score"),
        "risk_approved": r.get("approved"),
        "risk_reason": r.get("reason"),
        "status": status_for(outcome),
        "outcome": outcome,
        "is_mock": is_mock_record(record),
        "is_cross_asset": is_cross_asset,
        "cross_asset_symbol": execute.CROSS_ASSET_PROXY if is_cross_asset else None,
        "cross_asset_note": record.get("cross_asset_note"),
        "sense_text": build_sense_text(record),
        "judge_heading": judge_block["heading"],
        "judge_text": judge_block["text"],
        "judge_neutral": judge_block["neutral"],
        "risk_lines": build_risk_lines(record),
        "execute_text": execute_block["text"],
        "execute_kind": execute_block["kind"],
        "edgar_url": record.get("edgar_url"),
        "realized_pnl_usd": record.get("realized_pnl_usd"),
        "realized_pnl_pct": record.get("realized_pnl_pct"),
        "correction_note": record.get("correction_note"),
        "no_averaging_blocked": (r.get("checks") or {}).get("no_averaging_into_loser") is False,
    }


def build_news() -> tuple[list, dict]:
    latest = {}
    if news.NEWS_LOG.exists():
        for line in news.NEWS_LOG.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                latest[r["news_key"]] = r   # later verdict (queued -> judged) wins
    items = sorted(latest.values(), key=lambda r: r.get("published_utc") or "", reverse=True)
    stats = {"seen": len(items), "skipped": 0, "queued": 0, "judged_no_trade": 0, "judged_trade": 0}
    for r in items:
        v = r.get("verdict")
        if v == "skipped_not_earnings_related":
            stats["skipped"] += 1
        elif v in stats:
            stats[v] += 1
        if r.get("outcome"):
            r["execution_label"] = EXECUTION_LABELS.get(r["outcome"], "Not filled" if v == "judged_trade" else None)
    stats["exported"] = min(len(items), NEWS_EXPORT_LIMIT)
    return items[:NEWS_EXPORT_LIMIT], stats


def build_qwen_usage() -> dict:
    if not judge.QWEN_USAGE_FILE.exists():
        return {"by_day": [], "tracking_since": None}
    usage = json.loads(judge.QWEN_USAGE_FILE.read_text())
    by_day = [{"date": d, **v} for d, v in sorted(usage.items())]
    return {
        "by_day": by_day,
        "tracking_since": by_day[0]["date"] if by_day else None,
        "total_calls": sum(d["calls"] for d in by_day),
        "total_tokens": sum(d["tokens"] for d in by_day),
    }


def build():
    portfolio = state.load_state()
    capital = portfolio.get("capital_usd", config.RISK["allocated_capital_usd"])
    open_positions = portfolio.get("open_positions", [])
    closed_positions = portfolio.get("closed_positions", [])

    decisions = []
    if DECISIONS_LOG.exists():
        for line in DECISIONS_LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            decisions.append(normalize_decision(json.loads(line)))
    decisions.sort(key=lambda d: d["timestamp_utc"] or "", reverse=True)

    # P&L sums every closed position (a test-fixture position's fill is still a
    # real Bitget fill with real P&L, and its unrealized P&L already counts
    # while open -- dropping it on close would make Cumulative P&L jump back
    # to zero). Win rate stays real-decision-only: a synthetic judgment's
    # outcome says nothing about Beacon's judgment quality.
    real_closed = [p for p in closed_positions if not p.get("is_test_fixture")]
    realized_pnl_usd = round(sum(p.get("realized_pnl_usd", 0.0) for p in closed_positions), 2)
    wins = [p for p in real_closed if p.get("realized_pnl_usd", 0.0) > 0]
    win_rate_pct = round(len(wins) / len(real_closed) * 100, 1) if real_closed else None

    total_exposure = round(sum(p.get("size_usd", 0.0) for p in open_positions), 2)
    unrealized_pnl = round(sum(p.get("unrealized_pnl_usd", 0.0) for p in open_positions), 2)
    # Cumulative P&L is realized (closed, real trades only) + unrealized (every
    # currently open position, same total the Positions tab's own "Unrealized
    # P&L" card shows) -- until a position closes, its P&L only ever shows up
    # here as unrealized. Previously this only counted realized trades, so it
    # sat at $0.00 and visibly contradicted a real, non-zero open position on
    # the Positions tab. realized_pnl_usd is exposed separately so the
    # frontend can recombine it with a freshly live-fetched unrealized figure
    # without having to back it out of the combined total.
    cumulative_pnl_usd = round(realized_pnl_usd + unrealized_pnl, 2)
    largest_position_pct = round(max((p.get("size_usd", 0.0) for p in open_positions), default=0.0) / capital * 100, 2)

    today_realized = state.today_realized_pnl(portfolio)
    daily_pnl_pct = round((today_realized + unrealized_pnl) / capital * 100, 2)
    no_averaging_blocked_count = sum(1 for d in decisions if d["no_averaging_blocked"])
    news_items, news_stats = build_news()
    news_stats["queue_length"] = len(news.load_queue())

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "capital_usd": capital,
        "summary": {
            "cumulative_pnl_usd": cumulative_pnl_usd,
            "realized_pnl_usd": realized_pnl_usd,
            "win_rate_pct": win_rate_pct,
            "real_closed_count": len(real_closed),
            "open_positions_count": len(open_positions),
            "total_exposure_usd": total_exposure,
            "total_exposure_pct": round(total_exposure / capital * 100, 2) if capital else 0,
            "unrealized_pnl_usd": unrealized_pnl,
            "concurrent_positions_used": len(open_positions),
            "concurrent_positions_cap": config.RISK["max_concurrent_positions"],
            "position_size_used_pct": largest_position_pct,
            "position_size_cap_pct": config.RISK["max_position_pct_per_trade"],
            "daily_drawdown_pct": daily_pnl_pct,
            "daily_drawdown_cap_pct": config.RISK["max_daily_drawdown_pct"],
            "no_averaging_blocked_count": no_averaging_blocked_count,
        },
        "open_positions": open_positions,
        "closed_positions": closed_positions,
        "decisions": decisions,
        "news_signals": news_items,
        "news_stats": news_stats,
        "qwen_usage": build_qwen_usage(),
        "last_cycle": json.loads(HEARTBEAT_FILE.read_text()) if HEARTBEAT_FILE.exists() else None,
        "scan_schedule": {
            "anchor_utc": SCAN_SCHEDULE_ANCHOR.astimezone(timezone.utc).isoformat(),
            "interval_hours": SCAN_SCHEDULE_INTERVAL_HOURS,
        },
    }
    OUT_FILE.write_text(json.dumps(out, indent=2, default=str))
    print(f"Wrote {OUT_FILE} — {len(decisions)} decisions, {len(open_positions)} open position(s).")


if __name__ == "__main__":
    build()
