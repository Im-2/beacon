"""LOG: append every decision (executed, rejected, or filtered) to a JSONL
evidence log and a human-readable markdown daily summary."""
import json
from datetime import datetime, timezone
from beacon import config

JSONL_LOG = config.LOG_DIR / "decisions.jsonl"


def log_decision(record: dict):
    record.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    with open(JSONL_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    _append_markdown(record)


def _append_markdown(record: dict):
    today = datetime.now(timezone.utc).date().isoformat()
    md_file = config.LOG_DIR / f"daily_summary_{today}.md"
    is_new = not md_file.exists()
    with open(md_file, "a", encoding="utf-8") as f:
        if is_new:
            f.write(f"# Beacon Daily Summary — {today}\n\n")
        f.write(f"## {record.get('timestamp_utc')} — {record.get('symbol')} "
                f"({record.get('trigger_type')}, category={record.get('category')})\n\n")
        f.write(f"- **Outcome:** {record.get('outcome')}\n")
        if record.get("gate_result") is not None:
            f.write(f"- **7.01 substantive-content gate:** {record['gate_result']}\n")
        if record.get("judgment"):
            j = record["judgment"]
            f.write(f"- **LLM judgment:** {j.get('surprise_classification')} "
                    f"(confidence {j.get('surprise_confidence')}), decision={j.get('decision')}, "
                    f"conviction={j.get('conviction_score')}\n")
            f.write(f"- **Rationale:** {j.get('rationale')}\n")
            f.write(f"- **Proposed size/stop/target:** {j.get('position_size_pct_of_capital')}% / "
                    f"SL {j.get('stop_loss_pct')}% / TP {j.get('take_profit_pct')}%\n")
        if record.get("risk_result"):
            r = record["risk_result"]
            f.write(f"- **Risk check:** approved={r.get('approved')} — {r.get('reason')}\n")
        if record.get("order"):
            f.write(f"- **Order:** {record['order']}\n")
        f.write("\n---\n\n")
