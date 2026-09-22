#!/usr/bin/env bash
# Manual trigger for any Beacon step. Usage: ./run_now.sh <step>
set -e
cd "$(dirname "$0")"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

step="${1:-help}"

case "$step" in
  connectivity)
    python3 check_connectivity.py
    ;;
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
  export-data)
    echo "=== Dashboard data export (decisions.jsonl + portfolio_state.json -> dashboard_data.json) ==="
    python3 export_dashboard_data.py
    ;;
  publish-data)
    echo "=== Publish market_data.json + dashboard_data.json to GitHub ==="
    # dashboard.html fetches these two files straight from GitHub's raw
    # content CDN (not a same-origin relative path), so once the static site
    # is deployed (Vercel etc.) this git push IS the "publish live data" step
    # -- no redeploy needed for data-only changes, since the HTML/JS never
    # changes. Only pushes when these two files actually changed, and a
    # failed/unreachable push must not abort the rest of an unattended cron
    # cycle (same reasoning as check_connectivity.py), so this never
    # propagates a non-zero exit.
    if git diff --quiet -- market_data.json dashboard_data.json 2>/dev/null \
       && git diff --cached --quiet -- market_data.json dashboard_data.json 2>/dev/null; then
      echo "No data changes to publish."
    else
      git add market_data.json dashboard_data.json
      git commit -m "Auto-refresh market_data.json + dashboard_data.json" --quiet \
        && git push origin master --quiet \
        && echo "Published." \
        || echo "git commit/push failed -- will retry next cycle." >&2
    fi
    ;;
  metrics)
    python3 metrics_report.py
    ;;
  all)
    "$0" connectivity
    "$0" scan
    "$0" tradability
    "$0" market-data
    "$0" live
    "$0" positions
    "$0" export-data
    "$0" publish-data
    ;;
  *)
    echo "Usage: ./run_now.sh {connectivity|scan|tradability|market-data|preview|live|positions|export-data|publish-data|metrics|all}"
    echo "  connectivity - check Bitget is actually reachable; warns loudly (never aborts) if not"
    echo "  scan         - refresh 8-K + anticipatory-earnings trigger data"
    echo "  tradability  - poll Bitget demo-trading symbol status for the 5-ticker universe;"
    echo "                 logs a halt->online transition automatically, independent of triggers"
    echo "  market-data  - refresh market_data.json (prices + candles) for the dashboard frontend"
    echo "  preview      - run SENSE->GATE->JUDGE->RISK on the next unprocessed trigger, no execution"
    echo "  live         - process all unprocessed triggers, execute risk-approved trades"
    echo "  positions    - check open positions against stop-loss/take-profit"
    echo "  export-data  - refresh dashboard_data.json (positions + decision history) for the dashboard frontend"
    echo "  publish-data - git commit + push market_data.json/dashboard_data.json so the deployed"
    echo "                 site's raw.githubusercontent.com fetch picks up the change"
    echo "  metrics      - print the submission metrics table"
    echo "  all          - connectivity + scan + tradability + market-data + live + positions + export-data + publish-data, in order"
    ;;
esac
