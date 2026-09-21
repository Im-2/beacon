#!/usr/bin/env python3
"""
Anticipatory-positioning track: tickers with a CONFIRMED upcoming earnings date
(not yet reported) that the agent may position ahead of, using current consensus
estimates as SENSE data. Logged in a separate category from post-event reactive
trades per the user's instruction — pre-earnings positioning is a distinct,
clearly-labeled thing, not disguised as a post-event reaction.

Re-scoped 2026-09-21 to the corrected 5-ticker Bitget-demo-tradable universe
(EQT, GOOGL, MU, NVDA, ECHO — see scan_8k_filings.py for why). Re-ran live
Finnhub earnings-calendar discovery against just these 5 for confirmed dates
in the next 35 days: MU (2026-09-30) and EQT (2026-10-19) have one; GOOGL,
NVDA, and ECHO do not yet. The previous AIR/EBF candidates are dropped along
with the rest of the old 21-ticker universe — neither has a Bitget demo pair.
"""
import json
from beacon import config, sense

# symbol -> confirmed report date, from live Finnhub earnings-calendar discovery
CANDIDATES = {
    "MU": "2026-09-30",
    "EQT": "2026-10-19",
}

OUTPUT_FILE = config.DATA_DIR / "anticipatory_triggers.json"


def build():
    triggers = []
    for symbol, report_date in CANDIDATES.items():
        estimate = sense.get_earnings_estimate(symbol, report_date)
        triggers.append({
            "symbol": symbol,
            "trigger_type": "anticipatory_earnings_positioning",
            "category": "anticipatory_positioning",
            "matched_items": None,
            "report_date": report_date,
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
