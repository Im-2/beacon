#!/usr/bin/env python3
"""
Dev-only test fixture: exercises RISK -> EXECUTE -> LOG with a synthetic,
realistically-shaped judgment (NOT the safety-forced always-no-trade mock from
judge.py). This is how EXECUTE's request-construction logic gets validated
before a real LLM key exists. Never invoked by the actual cron pipeline.
"""
import json
from beacon import config, risk, state, execute, logger, sense

SYNTHETIC_JUDGMENT = {
    "surprise_classification": "bullish",
    "surprise_confidence": 72,
    "tone_assessment": "TEST FIXTURE, not a real LLM output — synthetic judgment for pipeline testing.",
    "decision": "long",
    "conviction_score": 65,
    "rationale": "TEST FIXTURE — synthetic rationale to exercise RISK/EXECUTE/LOG with a realistic "
                 "non-no-trade shape, since judge.py's real mock always forces no-trade for safety.",
    "position_size_pct_of_capital": 4.0,
    "stop_loss_pct": 3.0,
    "take_profit_pct": 6.0,
    "mock": True,
    "synthetic_test_fixture": True,
}


def main():
    symbol = "VLO"
    print(f"=== Synthetic judgment (test fixture, not real LLM output) ===")
    print(json.dumps(SYNTHETIC_JUDGMENT, indent=2))

    portfolio_state = state.load_state()
    print(f"\n=== RISK evaluate ===")
    risk_result = risk.evaluate(SYNTHETIC_JUDGMENT, symbol, portfolio_state)
    print(json.dumps(risk_result, indent=2))

    quote = sense.get_quote(symbol)
    entry_price = quote["current_price"]
    capital = config.RISK["allocated_capital_usd"]
    size_usd = capital * SYNTHETIC_JUDGMENT["position_size_pct_of_capital"] / 100.0

    print(f"\n=== EXECUTE (dry_run, since risk_result.approved={risk_result['approved']}) ===")
    order = execute.place_paper_order(
        symbol=symbol,
        direction=SYNTHETIC_JUDGMENT["decision"],
        size_usd=size_usd,
        entry_price=entry_price,
        stop_loss_pct=SYNTHETIC_JUDGMENT["stop_loss_pct"],
        take_profit_pct=SYNTHETIC_JUDGMENT["take_profit_pct"],
        dry_run=True,   # always dry-run in this test fixture, regardless of credentials
    )
    print(json.dumps(order, indent=2))

    print(f"\n=== LOG (writing test record — clearly tagged as a test fixture) ===")
    record = {
        "symbol": symbol, "trigger_type": "TEST_FIXTURE", "category": "test",
        "judgment": SYNTHETIC_JUDGMENT, "risk_result": risk_result, "order": order,
        "outcome": "test_fixture_dry_run", "is_test_fixture": True,
    }
    logger.log_decision(record)
    print(f"Logged to {logger.JSONL_LOG} (tagged is_test_fixture=true — filter these out of real metrics)")


if __name__ == "__main__":
    main()
