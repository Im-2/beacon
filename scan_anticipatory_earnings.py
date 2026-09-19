#!/usr/bin/env python3
"""
Anticipatory-positioning track: tickers with a CONFIRMED upcoming earnings date
(not yet reported) that the agent may position ahead of, using current consensus
estimates as SENSE data. Logged in a separate category from post-event reactive
trades per the user's instruction — pre-earnings positioning is a distinct,
clearly-labeled thing, not disguised as a post-event reaction.

Currently hardcoded to the two tickers confirmed via live Finnhub earnings-calendar
discovery on 2026-09-18 (AIR, EBF) — both real, dated, liquid (AIR) or moderately
liquid (EBF) names with actual analyst coverage. EBF has no Bitget tokenized-stock
pair (verified in beacon/execute.py's tradability check) — it stays in this file so
it's logged as "trigger valid, non-executable on Bitget" rather than silently
dropped, per explicit instruction.
"""
import json
from beacon import config, sense

CANDIDATES = ["AIR", "EBF"]
REPORT_DATE = "2026-09-21"

OUTPUT_FILE = config.DATA_DIR / "anticipatory_triggers.json"


def build():
    triggers = []
    for symbol in CANDIDATES:
        estimate = sense.get_earnings_estimate(symbol, REPORT_DATE)
        triggers.append({
            "symbol": symbol,
            "trigger_type": "anticipatory_earnings_positioning",
            "category": "anticipatory_positioning",
            "matched_items": None,
            "report_date": REPORT_DATE,
            "consensus_eps_estimate": estimate.get("epsEstimate"),
            "consensus_revenue_estimate": estimate.get("revenueEstimate"),
            "filed_date": None,
            "accession_number": None,
            "edgar_url": None,
        })
    OUTPUT_FILE.write_text(json.dumps({"triggers": triggers}, indent=2))
    print(json.dumps(triggers, indent=2))
    return triggers


if __name__ == "__main__":
    build()
