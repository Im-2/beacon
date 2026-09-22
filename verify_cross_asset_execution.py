"""Controlled test, explicitly authorized by the user: verifies the
cross-asset EXECUTE mechanics with a REAL Bitget order, since real JUDGE
genuinely (and correctly) returned no-trade on both real triggers available
today. Only judge.judge() is replaced -- with a clearly-labeled synthetic
decision, same convention as test_execute_pipeline.py (mock: True,
synthetic_test_fixture: True). SENSE, RISK, and EXECUTE (including the real
signed Bitget order for both the rToken attempt and the crypto proxy
fallback) are 100% real, unmocked. The log record is explicitly tagged
is_test_fixture at the top level too, so it's unmistakable in the audit
trail -- this is a mechanics test, not a real trading decision."""
import sys
sys.path.insert(0, r"C:\Users\hp\Beacon")

from unittest.mock import patch
from beacon import state, judge, logger
import decision_engine as de

triggers = de.load_triggers()
target = sys.argv[1] if len(sys.argv) > 1 else "MU"
t = next(x for x in triggers if x["symbol"] == target)
portfolio_state = state.load_state()

SYNTHETIC_JUDGMENT = {
    "surprise_classification": "bearish",
    "surprise_confidence": 60,
    "tone_assessment": "TEST FIXTURE, not a real LLM output — synthetic judgment to verify "
                        "real EXECUTE/cross-asset mechanics, per explicit user authorization "
                        "on 2026-09-22 after real JUDGE genuinely returned no-trade on both "
                        "real triggers available that day.",
    "decision": "long",
    "conviction_score": 55,
    "rationale": "TEST FIXTURE — synthetic rationale, not real reasoning. Real SENSE, RISK, "
                 "and EXECUTE (including the actual Bitget order/fill) are unmocked.",
    "position_size_pct_of_capital": 2.0,
    "stop_loss_pct": 3.0,
    "take_profit_pct": 5.0,
    "mock": True,
    "synthetic_test_fixture": True,
}

def fake_judge(sensed, trigger_meta):
    return dict(SYNTHETIC_JUDGMENT)

real_log_decision = logger.log_decision
def tagged_log_decision(record):
    record["is_test_fixture"] = True
    real_log_decision(record)

with patch.object(judge, "judge", side_effect=fake_judge), \
     patch.object(logger, "log_decision", side_effect=tagged_log_decision):
    record = de.process_one(t, portfolio_state, execute_live=True)

print("\n" + "=" * 60)
print("outcome:", record.get("outcome"))
print("execution_leg:", record.get("execution_leg"))
print("cross_asset_note:", record.get("cross_asset_note"))
print("rtoken_order status:", (record.get("rtoken_order") or {}).get("status"))
print("rtoken_order response:", (record.get("rtoken_order") or {}).get("response"))
print("cross_asset_risk_result:", record.get("cross_asset_risk_result"))
co = record.get("cross_asset_order") or {}
print("cross_asset_order status:", co.get("status"))
print("cross_asset_order http_status:", co.get("http_status"))
print("cross_asset_order response:", co.get("response"))
print("cross_asset_order request:", co.get("request"))
