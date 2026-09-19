#!/usr/bin/env python3
"""
Step 6: reads logs/decisions.jsonl + the portfolio state and prints a clean
markdown metrics table for the hackathon submission — cumulative P&L, win
rate, annualized Sharpe, max drawdown, trade count, breakdown by trigger
type, and conviction-vs-outcome correlation. Clearly labels the actual date
range covered so the submission is transparent about log duration.

Test-fixture records (is_test_fixture: true) are always excluded.
"""
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from beacon import config, state

JSONL_LOG = config.LOG_DIR / "decisions.jsonl"


def load_records():
    if not JSONL_LOG.exists():
        return []
    records = []
    for line in JSONL_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("is_test_fixture"):
            continue
        records.append(r)
    return records


def sharpe_ratio(daily_returns_pct):
    if len(daily_returns_pct) < 2:
        return None
    mean = sum(daily_returns_pct) / len(daily_returns_pct)
    variance = sum((r - mean) ** 2 for r in daily_returns_pct) / (len(daily_returns_pct) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return None
    return (mean / std) * math.sqrt(252)


def max_drawdown_pct(equity_curve):
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        peak = max(peak, v)
        dd = (v - peak) / peak * 100 if peak else 0
        max_dd = min(max_dd, dd)
    return max_dd


def conviction_outcome_correlation(closed):
    pairs = [(c["judgment_conviction"], c["realized_pnl_usd"]) for c in closed if c.get("judgment_conviction") is not None]
    if len(pairs) < 2:
        return None
    xs, ys = zip(*pairs)
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    cov = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    return cov / math.sqrt(var_x * var_y)


def main():
    records = load_records()
    portfolio_state = state.load_state()
    closed_positions = [p for p in portfolio_state.get("closed_positions", [])]

    if not records and not closed_positions:
        print("# Beacon Metrics Report\n\nNo decisions logged yet. Nothing to report.")
        return

    timestamps = [r.get("timestamp_utc") for r in records if r.get("timestamp_utc")]
    date_range = (min(timestamps), max(timestamps)) if timestamps else (None, None)

    outcomes = defaultdict(int)
    by_trigger_type = defaultdict(lambda: {"triggers": 0, "trades": 0, "wins": 0, "pnl_usd": 0.0})
    for r in records:
        outcomes[r.get("outcome", "unknown")] += 1
        tt = r.get("trigger_type", "unknown")
        by_trigger_type[tt]["triggers"] += 1

    capital = config.RISK["allocated_capital_usd"]
    realized_pnl_total = sum(p.get("realized_pnl_usd", 0) for p in closed_positions)
    wins = [p for p in closed_positions if p.get("realized_pnl_usd", 0) > 0]
    win_rate = (len(wins) / len(closed_positions) * 100) if closed_positions else None

    for p in closed_positions:
        tt = p.get("trigger_type", "unknown")
        d = by_trigger_type[tt]
        d["trades"] += 1
        d["pnl_usd"] += p.get("realized_pnl_usd", 0)
        if p.get("realized_pnl_usd", 0) > 0:
            d["wins"] += 1

    daily_pnl = defaultdict(float)
    for p in closed_positions:
        day = p.get("closed_at", "")[:10]
        daily_pnl[day] += p.get("realized_pnl_usd", 0)
    daily_returns_pct = [v / capital * 100 for v in daily_pnl.values()]
    sharpe = sharpe_ratio(daily_returns_pct)

    equity_curve = [capital]
    for day in sorted(daily_pnl.keys()):
        equity_curve.append(equity_curve[-1] + daily_pnl[day])
    max_dd = max_drawdown_pct(equity_curve)

    closed_with_conviction = []
    for p in closed_positions:
        matching = [r for r in records if r.get("symbol") == p.get("symbol") and r.get("judgment")]
        conviction = matching[-1]["judgment"].get("conviction_score") if matching else None
        closed_with_conviction.append({**p, "judgment_conviction": conviction})
    conviction_corr = conviction_outcome_correlation(closed_with_conviction)

    lines = []
    lines.append("# Beacon Metrics Report")
    lines.append("")
    lines.append(f"**Log date range:** {date_range[0] or 'n/a'} to {date_range[1] or 'n/a'} "
                  f"(UTC) — {len(set(t[:10] for t in timestamps))} distinct day(s) of live data")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Allocated paper capital | ${capital:,.2f} |")
    lines.append(f"| Cumulative realized P&L | ${realized_pnl_total:,.2f} ({realized_pnl_total/capital*100:+.2f}%) |")
    lines.append(f"| Closed trades | {len(closed_positions)} |")
    lines.append(f"| Open positions | {len(portfolio_state.get('open_positions', []))} |")
    lines.append(f"| Win rate | {f'{win_rate:.1f}%' if win_rate is not None else 'n/a (no closed trades yet)'} |")
    lines.append(f"| Sharpe ratio (annualized) | {f'{sharpe:.2f}' if sharpe is not None else 'n/a (need ≥2 trading days of P&L)'} |")
    lines.append(f"| Max drawdown | {max_dd:.2f}% |")
    lines.append(f"| Conviction-vs-outcome correlation | {f'{conviction_corr:.2f}' if conviction_corr is not None else 'n/a (need ≥2 closed trades with conviction scores)'} |")
    lines.append("")
    lines.append("## Trigger-fired outcomes (all decisions, not just executed trades)")
    lines.append("")
    lines.append("| Outcome | Count |")
    lines.append("|---|---|")
    for outcome, count in sorted(outcomes.items(), key=lambda x: -x[1]):
        lines.append(f"| {outcome} | {count} |")
    lines.append("")
    lines.append("## Breakdown by trigger type")
    lines.append("")
    lines.append("| Trigger type | Triggers seen | Trades executed | Wins | P&L (USD) |")
    lines.append("|---|---|---|---|---|")
    for tt, d in sorted(by_trigger_type.items()):
        lines.append(f"| {tt} | {d['triggers']} | {d['trades']} | {d['wins']} | ${d['pnl_usd']:,.2f} |")
    lines.append("")

    report = "\n".join(lines)
    print(report)
    out_file = config.LOG_DIR / "metrics_report.md"
    out_file.write_text(report, encoding="utf-8")
    print(f"\n[written to {out_file}]", flush=True)


if __name__ == "__main__":
    main()
