#!/usr/bin/env bash
# Manual trigger for any Beacon step. Usage: ./run_now.sh <step>
set -e
cd "$(dirname "$0")"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

step="${1:-help}"

case "$step" in
  scan)
    echo "=== 8-K filing scan (S&P 500, last 3 days) ==="
    python3 scan_8k_filings.py --days-back 3
    echo "=== Anticipatory earnings scan (AIR, EBF) ==="
    python3 scan_anticipatory_earnings.py
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
    "$0" live
    "$0" positions
    ;;
  *)
    echo "Usage: ./run_now.sh {scan|preview|live|positions|metrics|all}"
    echo "  scan      - refresh 8-K + anticipatory-earnings trigger data"
    echo "  preview   - run SENSE->GATE->JUDGE->RISK on the next unprocessed trigger, no execution"
    echo "  live      - process all unprocessed triggers, execute risk-approved trades"
    echo "  positions - check open positions against stop-loss/take-profit"
    echo "  metrics   - print the submission metrics table"
    echo "  all       - scan + live + positions, in order"
    ;;
esac
