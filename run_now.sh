#!/usr/bin/env bash
# Manual trigger for any Beacon step. Usage: ./run_now.sh <step>
set -e
cd "$(dirname "$0")"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

step="${1:-help}"

case "$step" in
  scan)
    echo "=== 8-K filing scan (5-ticker Bitget-demo-tradable universe, last 3 days) ==="
    python3 scan_8k_filings.py --days-back 3
    echo "=== Anticipatory earnings scan (MU, EQT) ==="
    python3 scan_anticipatory_earnings.py
    ;;
  tradability)
    echo "=== Bitget demo tradability poll (5-ticker universe) ==="
    python3 check_tradability.py
    ;;
  market-data)
    echo "=== Market data refresh (prices + candles -> market_data.json) ==="
    python3 update_market_data.py
    ;;
  preview)
    python3 decision_engine.py --mode preview
    ;;
  live)
    python3 decision_engine.py --mode live
    ;;
  positions)
    python3 position_manager.py
    ;;
  metrics)
    python3 metrics_report.py
    ;;
  all)
    "$0" scan
    "$0" tradability
    "$0" market-data
    "$0" live
    "$0" positions
    ;;
  *)
    echo "Usage: ./run_now.sh {scan|tradability|market-data|preview|live|positions|metrics|all}"
    echo "  scan         - refresh 8-K + anticipatory-earnings trigger data"
    echo "  tradability  - poll Bitget demo-trading symbol status for the 5-ticker universe;"
    echo "                 logs a halt->online transition automatically, independent of triggers"
    echo "  market-data  - refresh market_data.json (prices + candles) for the dashboard frontend"
    echo "  preview      - run SENSE->GATE->JUDGE->RISK on the next unprocessed trigger, no execution"
    echo "  live         - process all unprocessed triggers, execute risk-approved trades"
    echo "  positions    - check open positions against stop-loss/take-profit"
    echo "  metrics      - print the submission metrics table"
    echo "  all          - scan + tradability + market-data + live + positions, in order"
    ;;
esac
