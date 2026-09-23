#!/usr/bin/env python3
"""
Beacon decision engine. Modes:

  --mode preview   Take the next unprocessed trigger, run SENSE -> (GATE) -> JUDGE
                    -> RISK, log and print the full result, but do NOT place any
                    order and do NOT mark the trigger as processed (so it can be
                    re-run for real once reviewed). Use this to sanity-check
                    reasoning quality before going live.

  --mode live       Process ALL unprocessed triggers. Non-substantive 7.01 filings
                    are filtered and logged (no LLM judgment call). Substantive
                    triggers get a full JUDGE + RISK pass; risk-approved trades are
                    then executed via Bitget paper trading. Marks each trigger
                    processed so repeated cron runs don't double-fire.

EXECUTE calls beacon.execute.place_paper_order() for real, real-account writes.
Verified end to end on 2026-09-21 against the funded Bitget Demo Trading account:
PGR real order request was signed, sent, and correctly logged its actual Bitget
response. Note: the Demo Trading environment only lists a small, separate symbol
universe from the live market (confirmed via GET .../public/symbols with the
paptrading header) -- most single-stock S&P 500 rToken pairs (including RPGRUSDT)
are not tradable there, so most trades will legitimately resolve to
"execute_not_sent_skipped_not_tradable_on_bitget" rather than "executed" until
Beacon's tracked universe is narrowed to symbols the demo environment supports.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from beacon import config, sense, judge, risk, state, logger, execute, news

TRIGGERS_FILE = config.DATA_DIR / "filing_triggers.json"
ANTICIPATORY_FILE = config.DATA_DIR / "anticipatory_triggers.json"
HEARTBEAT_FILE = config.DATA_DIR / "last_cycle.json"


def write_heartbeat(total, pending_count, processed_count, news_judged=0, news_queued=0):
    # A live cycle that finds nothing new logs nothing to decisions.jsonl, so
    # without this there's no evidence a check ever happened -- the dashboard's
    # "Last Check" reads this file (via export_dashboard_data.py).
    HEARTBEAT_FILE.write_text(json.dumps({
        "last_live_cycle_utc": datetime.now(timezone.utc).isoformat(),
        "triggers_total": total,
        "triggers_pending_at_start": pending_count,
        "triggers_processed": processed_count,
        "news_judged": news_judged,
        "news_queued_remaining": news_queued,
    }, indent=2))


def load_triggers():
    triggers = []
    if TRIGGERS_FILE.exists():
        data = json.loads(TRIGGERS_FILE.read_text())
        for t in data.get("triggers", []):
            t["category"] = "post_event_reactive"
            triggers.append(t)
    if ANTICIPATORY_FILE.exists():
        data = json.loads(ANTICIPATORY_FILE.read_text())
        triggers.extend(data.get("triggers", []))
    return triggers


def trigger_key(t):
    return f"{t['symbol']}::{t.get('accession_number') or t.get('report_date') or t.get('filed_date')}"


def existing_position_for(ticker, portfolio_state):
    """An open position on this underlying ticker, held directly (rToken) or
    via the cross-asset BTC proxy (symbol "BTC", proxy_for == ticker)."""
    for p in portfolio_state.get("open_positions", []):
        if p.get("symbol") == ticker or p.get("proxy_for") == ticker:
            return p
    return None


def needs_gate(t):
    items = set(t.get("matched_items") or [])
    return "7.01" in items and "2.02" not in items


def process_one(t, portfolio_state, execute_live=False):
    symbol = t["symbol"]
    record = {"symbol": symbol, "trigger_type": t["trigger_type"], "category": t["category"],
              "matched_items": t.get("matched_items"), "filed_date": t.get("filed_date"),
              "accession_number": t.get("accession_number"), "edgar_url": t.get("edgar_url")}
    if t.get("news"):
        record["news"] = t["news"]

    print(f"\n=== SENSE: {symbol} ===")
    sensed = sense.sense_for_trigger(t)
    print(json.dumps(sensed, indent=2, default=str)[:2000])

    if needs_gate(t):
        filing_text = (sensed.get("filing") or {}).get("text", "")
        print(f"\n=== GATE (7.01 substantive-content check): {symbol} ===")
        gate = judge.gate_check_7_01(symbol, filing_text)
        print(json.dumps(gate, indent=2))
        record["gate_result"] = gate
        if not gate.get("substantive"):
            record["outcome"] = "trigger_fired_filtered_non_substantive"
            record["judgment"] = None
            record["risk_result"] = None
            print(f"\n>>> FILTERED: {symbol} — not substantive ({gate.get('reason')}). No position taken.")
            logger.log_decision(record)
            return record

    print(f"\n=== JUDGE: {symbol} ===")
    judgment = judge.judge(sensed, {"symbol": symbol, "category": t["category"],
                                     "matched_items": t.get("matched_items"),
                                     "trigger_type": t["trigger_type"]})
    print(json.dumps(judgment, indent=2))
    record["judgment"] = judgment

    print(f"\n=== RISK: {symbol} ===")
    risk_result = risk.evaluate(judgment, symbol, portfolio_state)
    print(json.dumps(risk_result, indent=2))
    record["risk_result"] = risk_result

    if judgment.get("decision") == "no-trade":
        record["outcome"] = "no_trade_llm_decision"
    elif not risk_result["approved"]:
        record["outcome"] = "rejected_by_risk_controls"
    elif existing_position_for(symbol, portfolio_state):
        # One position per underlying ticker, however it's expressed. RISK's
        # own same-symbol check only blocks averaging into a *losing*
        # position, and a BTC proxy is stored under "BTC" (with proxy_for),
        # so without this a second MU headline would open a second order.
        held = existing_position_for(symbol, portfolio_state)
        record["outcome"] = "already_positioned_not_added"
        record["existing_position"] = {k: held.get(k) for k in
                                       ("symbol", "proxy_for", "direction", "opened_at", "execution_leg")}
    elif not execute_live:
        record["outcome"] = "preview_pending_approval_not_executed"
    else:
        entry_price = (sensed.get("quote") or {}).get("current_price")
        capital = config.RISK["allocated_capital_usd"]
        size_usd = capital * float(judgment["position_size_pct_of_capital"]) / 100.0
        dry_run = not config.bitget_configured()

        order = execute.place_paper_order(
            symbol=symbol,
            direction=judgment["decision"],
            size_usd=size_usd,
            entry_price=entry_price,
            stop_loss_pct=judgment.get("stop_loss_pct", 0),
            take_profit_pct=judgment.get("take_profit_pct", 0),
            dry_run=dry_run,
        )
        record["rtoken_order"] = order

        if order["status"] == "SENT":
            record["outcome"] = "executed_direct_rtoken"
            record["execution_leg"] = "direct_rtoken"
            portfolio_state.setdefault("open_positions", []).append({
                "symbol": symbol, "direction": judgment["decision"], "entry_price": entry_price,
                "size_usd": size_usd, "stop_loss_pct": judgment.get("stop_loss_pct", 0),
                "take_profit_pct": judgment.get("take_profit_pct", 0),
                "opened_at": datetime.now(timezone.utc).isoformat(), "category": t["category"],
                "unrealized_pnl_usd": 0.0, "execution_leg": "direct_rtoken",
            })
            state.save_state(portfolio_state)

        elif order["status"] == "SKIPPED_NOT_TRADABLE_ON_BITGET":
            # Cross-Asset Execution Agent sub-theme: the rToken order was
            # blocked (halted or no pair), but the JUDGE conviction behind it
            # is still real -- re-express it via a Bitget-demo-tradable crypto
            # proxy instead of silently dropping the trigger. This re-runs
            # RISK for the proxy symbol specifically (its own concurrent-
            # position and no-averaging-into-loser checks are per-symbol).
            proxy_symbol = execute.CROSS_ASSET_PROXY

            if judgment["decision"] != "long":
                # Long-only, deliberately, per 2026-09-22 decision: a short/sell
                # proxy order requires the demo account to already hold the base
                # asset (confirmed via a real code 43012 "Insufficient balance"
                # rejection -- Bitget spot has no naked shorting), and the demo
                # account holds USDT + ETH, not BTC. Rather than fund BTC or wire
                # up a second proxy asset just for shorts, this is logged
                # honestly as a known gap instead of forcing a workaround.
                record["outcome"] = "cross_asset_fallback_unavailable_for_short_direction"
                record["cross_asset_note"] = (
                    f"rToken {symbol} halted and JUDGE decision was 'short' -- cross-asset "
                    f"proxy fallback is long-only for now (spot {proxy_symbol} sell orders "
                    f"require an existing balance the demo account doesn't hold), so no "
                    f"proxy order was attempted."
                )
                logger.log_decision(record)
                return record

            proxy_risk_result = risk.evaluate(judgment, proxy_symbol, portfolio_state)
            record["cross_asset_risk_result"] = proxy_risk_result
            capital = config.RISK["allocated_capital_usd"]
            proxy_exposure = sum(p.get("size_usd", 0) for p in portfolio_state.get("open_positions", [])
                                 if p.get("symbol") == proxy_symbol)
            proxy_cap = capital * config.RISK["max_proxy_exposure_pct"] / 100.0

            if not proxy_risk_result["approved"]:
                record["outcome"] = "cross_asset_proxy_rejected_by_risk"
            elif proxy_exposure + size_usd > proxy_cap:
                # Several tickers can each hold their own BTC proxy, but they
                # are all the same asset, so total BTC exposure is capped.
                record["outcome"] = "proxy_exposure_cap_reached_not_added"
                record["cross_asset_note"] = (
                    f"{proxy_symbol} proxy exposure ${proxy_exposure:,.2f} + this ${size_usd:,.2f} would exceed "
                    f"the {config.RISK['max_proxy_exposure_pct']:g}% cap (${proxy_cap:,.2f}); {symbol} not expressed."
                )
            else:
                proxy_bitget_symbol = execute.to_bitget_symbol(proxy_symbol)
                try:
                    proxy_entry_price = execute.get_public_price(proxy_bitget_symbol)
                except Exception as e:
                    record["outcome"] = "cross_asset_proxy_price_unavailable"
                    record["cross_asset_error"] = str(e)
                    logger.log_decision(record)
                    return record

                proxy_order = execute.place_paper_order(
                    symbol=proxy_symbol,
                    direction=judgment["decision"],
                    size_usd=size_usd,
                    entry_price=proxy_entry_price,
                    stop_loss_pct=judgment.get("stop_loss_pct", 0),
                    take_profit_pct=judgment.get("take_profit_pct", 0),
                    dry_run=dry_run,
                )
                record["cross_asset_order"] = proxy_order

                if proxy_order["status"] == "SENT":
                    record["outcome"] = "executed_cross_asset_proxy"
                    record["execution_leg"] = "cross_asset_proxy"
                    record["cross_asset_note"] = (
                        f"Cross-asset proxy execution: rToken {symbol} halted, "
                        f"expressing via {proxy_symbol} instead."
                    )
                    portfolio_state.setdefault("open_positions", []).append({
                        "symbol": proxy_symbol, "direction": judgment["decision"],
                        "entry_price": proxy_entry_price, "size_usd": size_usd,
                        "stop_loss_pct": judgment.get("stop_loss_pct", 0),
                        "take_profit_pct": judgment.get("take_profit_pct", 0),
                        "opened_at": datetime.now(timezone.utc).isoformat(), "category": t["category"],
                        "unrealized_pnl_usd": 0.0, "execution_leg": "cross_asset_proxy",
                        "proxy_for": symbol,
                    })
                    state.save_state(portfolio_state)
                else:
                    record["outcome"] = f"cross_asset_proxy_not_sent_{proxy_order['status'].lower()}"
        else:
            record["outcome"] = f"execute_not_sent_{order['status'].lower()}"

    logger.log_decision(record)
    return record


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["preview", "live"], default="preview")
    args = p.parse_args()

    triggers = load_triggers()
    processed = state.load_processed()
    portfolio_state = state.load_state()

    pending = [t for t in triggers if trigger_key(t) not in processed]
    print(f"{len(pending)}/{len(triggers)} triggers unprocessed.")

    if args.mode == "preview":
        if not pending:
            print("Nothing new to process.")
            return
        t = pending[0]
        record = process_one(t, portfolio_state, execute_live=False)
        print(f"\n{'='*60}\nPREVIEW COMPLETE for {t['symbol']}. Outcome: {record['outcome']}")
        print("Not marked as processed — rerun in --mode live to actually act on it once reviewed.")
    else:
        if not pending:
            print("Nothing new to process.")
        processed_count = 0
        for t in pending:
            try:
                process_one(t, portfolio_state, execute_live=True)
                processed_count += 1
            except Exception as e:
                # One trigger's unexpected failure (a transient SEC/Finnhub/Qwen
                # network error, not a Bitget connectivity issue -- that's
                # already handled gracefully inside process_one) must not kill
                # the rest of this batch or the cron cycle behind it. Left
                # unprocessed so it's retried next cycle rather than silently
                # marked done.
                print(f"\n>>> ERROR processing {t['symbol']}: {e} -- leaving unprocessed, "
                      f"will retry next cycle.", file=sys.stderr)
                continue
            state.mark_processed(trigger_key(t))
            portfolio_state = state.load_state()
        news_judged, news_remaining = process_news_queue()
        write_heartbeat(len(triggers), len(pending), processed_count,
                        news_judged=news_judged, news_queued=news_remaining)


def news_verdict(record: dict) -> str:
    decision = (record.get("judgment") or {}).get("decision")
    return "judged_trade" if decision in ("long", "short") else "judged_no_trade"


def _news_log_base(item: dict) -> dict:
    return {k: item.get(k) for k in ("news_key", "symbol", "finnhub_id", "headline", "source", "url",
                                     "published_utc", "matched_keywords")}


def prune_news_queue() -> list:
    """Re-screen every queued item with the current pre-filter (so items
    queued under older, looser rules get the same treatment) and expire
    anything older than MAX_AGE_HOURS. Every drop is logged. Saves and
    returns the remaining queue, newest first."""
    queue = news.load_queue()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=news.MAX_AGE_HOURS)).isoformat()
    live, dropped = [], {}
    for item in queue:
        skip, keywords = news.screen(item["symbol"], item.get("headline"), item.get("summary"))
        if not skip and item["published_utc"] < cutoff:
            skip = "expired_not_judged"
        if skip:
            news.append_log({**_news_log_base(item), "matched_keywords": keywords, "verdict": skip})
            dropped[skip] = dropped.get(skip, 0) + 1
            continue
        item["matched_keywords"] = keywords
        live.append(item)
    live.sort(key=lambda q: q["published_utc"], reverse=True)
    news.save_queue(live)
    if dropped:
        print(f"News queue re-screen: dropped {dropped}; {len(live)} remain.")
    return live


def process_news_queue():
    """Judge up to MAX_JUDGE_PER_CYCLE queued news items, NEWEST first (old
    news is already priced in). Before that, drop queued items that don't name
    the company in the headline, and expire anything published more than
    MAX_AGE_HOURS ago that was never judged -- both logged, never silently
    removed. Returns (judged, still_queued)."""
    live = prune_news_queue()
    if not live:
        print("News queue empty.")
        return 0, 0
    batch, rest = live[:news.MAX_JUDGE_PER_CYCLE], live[news.MAX_JUDGE_PER_CYCLE:]
    judged = 0
    for item in batch:
        t = {
            "symbol": item["symbol"],
            "trigger_type": "finnhub_earnings_news",
            "category": "news_reactive",
            "news": {k: item.get(k) for k in ("headline", "summary", "source", "url", "published_utc",
                                              "matched_keywords")},
        }
        try:
            record = process_one(t, state.load_state(), execute_live=True)
        except Exception as e:
            print(f"\n>>> ERROR judging news {item['news_key']}: {e} -- kept in queue.", file=sys.stderr)
            rest.append(item)
            continue
        judged += 1
        j = record.get("judgment") or {}
        news.append_log({
            **_news_log_base(item),
            "verdict": news_verdict(record),
            "decision": j.get("decision"),
            "conviction": j.get("conviction_score"),
            "rationale": j.get("rationale"),
            "tone_assessment": j.get("tone_assessment"),
            "is_mock": bool(j.get("mock")),
            "outcome": record.get("outcome"),
            "execution_leg": record.get("execution_leg"),
            "decision_timestamp_utc": record.get("timestamp_utc"),
        })
    rest.sort(key=lambda q: q["published_utc"], reverse=True)
    news.save_queue(rest)
    print(f"News: judged {judged} this cycle (cap {news.MAX_JUDGE_PER_CYCLE}), "
          f"{len(rest)} still queued for next cycle.")
    return judged, len(rest)


if __name__ == "__main__":
    main()
