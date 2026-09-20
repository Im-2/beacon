"""JUDGE: the LLM is the actual decision-maker here. This module only builds
prompts, calls the configured LLM, and parses the structured response — it
applies no trading logic of its own (that's risk.py, which is deterministic
code).

Provider is selected via config.JUDGE_PROVIDER ("qwen" or "anthropic"). If the
selected provider's API key is still a placeholder, every call returns a
clearly-labeled MOCK decision instead of crashing or silently faking a real
call, so the rest of the pipeline (RISK, EXECUTE, LOG) can be built and tested
before a real key is available.
"""
import json
import requests
from beacon import config

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-opus-5"

# Bitget AI Base Camp Hackathon S2's sponsored Qwen proxy (OpenAI-compatible),
# not Alibaba Cloud DashScope directly — the hackathon-issued key only
# authenticates against this endpoint. See:
# https://bitget-ai.gitbook.io/bitgetai_hackathons2#qwen-token-subsidy-during-the-hackathon
QWEN_API_URL = "https://hackathon.bitgetops.com/v1/chat/completions"
QWEN_MODEL = "qwen3.8-max"


def _call_anthropic(system: str, user: str, max_tokens: int) -> str:
    resp = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": config.anthropic_key(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(block.get("text", "") for block in data.get("content", []))


def _call_qwen(system: str, user: str, max_tokens: int) -> str:
    resp = requests.post(
        QWEN_API_URL,
        headers={
            "Authorization": f"Bearer {config.qwen_key()}",
            "Content-Type": "application/json",
        },
        json={
            "model": QWEN_MODEL,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        # Bitget's shared hackathon proxy is noticeably slower than calling
        # Qwen directly, especially on longer JUDGE completions (1500 tokens) —
        # 60s produced real ReadTimeouts in testing on a real trigger.
        timeout=150,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_llm(system: str, user: str, max_tokens: int = 1500) -> tuple[str, bool]:
    """Returns (raw_text, was_mock)."""
    if not config.judge_llm_configured():
        return None, True
    if config.JUDGE_PROVIDER == "qwen":
        return _call_qwen(system, user, max_tokens), False
    if config.JUDGE_PROVIDER == "anthropic":
        return _call_anthropic(system, user, max_tokens), False
    raise ValueError(f"Unknown JUDGE_PROVIDER: {config.JUDGE_PROVIDER}")


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in LLM response: {text[:300]}")
    return json.loads(text[start:end + 1])


GATE_SYSTEM = """You are a gatekeeper for a SEC 8-K Item 7.01 (Regulation FD Disclosure) \
filing screener used by a paper-trading research agent. Item 7.01 is a broad-use item code: \
issuers use it for genuine guidance/financial updates AND for unrelated investor-relations \
content (conference presentation slides, routine disclosures, etc). Your only job is to \
classify whether THIS SPECIFIC filing's actual text is substantively relevant to financial \
performance, guidance, or outlook. Do not assess bullish/bearish direction here — only relevance.

Respond with ONLY a JSON object: {"substantive": true|false, "reason": "<one sentence>"}"""

JUDGE_SYSTEM = """You are the autonomous decision-making engine of Beacon, an earnings/guidance-driven \
paper-trading research agent. You are given real, live sensed data about one ticker's trigger event. \
You must produce a directional trading judgment. This is PAPER TRADING ONLY — no real funds are at risk \
— but your reasoning should be as rigorous as if they were, since your output is evaluated as the core \
research artifact of a hackathon submission.

Base your judgment ONLY on the data provided. Do not invent facts not present in the input. If the data \
is insufficient to form a real view, say so and set decision to "no-trade" with low conviction rather than \
guessing.

Two trigger categories exist, and they must be reasoned about differently:
- "post_event_reactive": an event (earnings, 8-K filing) has ALREADY happened. Judge the actual reported \
  surprise/content against expectations.
- "anticipatory_positioning": the sensed data will include an "anticipatory" block — this ticker has a \
  CONFIRMED but NOT YET OCCURRED earnings date. There is no surprise to classify yet, because nothing has \
  been reported. Do not invent one. Set surprise_classification to "neutral" and surprise_confidence low \
  in this case; base surprise_confidence and rationale instead on real pre-event positioning factors that \
  ARE in the data (current price vs. consensus-implied expectations, valuation context) — never a fabricated \
  guess at what the report will say.

Respond with ONLY a JSON object with this exact shape:
{
  "surprise_classification": "bullish" | "bearish" | "neutral",
  "surprise_confidence": <0-100 integer>,
  "tone_assessment": "<one or two sentences on language/tone in the filing or estimate revision>",
  "decision": "long" | "short" | "no-trade",
  "conviction_score": <0-100 integer>,
  "rationale": "<plain-English reasoning, 3-6 sentences, reference the actual numbers/text given>",
  "position_size_pct_of_capital": <0-100 float, 0 if no-trade>,
  "stop_loss_pct": <float, e.g. 3.0 for 3% below entry; 0 if no-trade>,
  "take_profit_pct": <float, e.g. 6.0 for 6% above entry; 0 if no-trade>
}"""


def _mock_gate_result(symbol: str, filing_text: str) -> dict:
    substantive = bool(filing_text and len(filing_text.strip()) > 200)
    return {
        "substantive": substantive,
        "reason": f"MOCK (no real LLM call — {config.JUDGE_PROVIDER.upper()}_API_KEY not configured): "
                  f"heuristic pass/fail on filing text length only ({len(filing_text or '')} chars).",
        "mock": True,
    }


def _mock_judgment(sensed: dict, trigger_meta: dict) -> dict:
    return {
        "surprise_classification": "neutral",
        "surprise_confidence": 0,
        "tone_assessment": f"MOCK DECISION — no real LLM call was made "
                            f"({config.JUDGE_PROVIDER.upper()}_API_KEY not configured). "
                            f"This output exists only to exercise the RISK/EXECUTE/LOG pipeline end-to-end.",
        "decision": "no-trade",
        "conviction_score": 0,
        "rationale": "This is a placeholder decision generated because no real LLM key is configured for "
                     f"JUDGE_PROVIDER={config.JUDGE_PROVIDER}. It intentionally decides no-trade so it can "
                     "never accidentally trigger a real or paper order. Once a real key is set, this ticker's "
                     "trigger should be re-run to get an actual judgment.",
        "position_size_pct_of_capital": 0,
        "stop_loss_pct": 0,
        "take_profit_pct": 0,
        "mock": True,
    }


def gate_check_7_01(symbol: str, filing_text: str) -> dict:
    if not filing_text or not filing_text.strip():
        return {"substantive": False, "reason": "No filing text could be retrieved.", "mock": False}
    user = f"Ticker: {symbol}\n\nFiling text (may be truncated):\n{filing_text}"
    raw, was_mock = _call_llm(GATE_SYSTEM, user, max_tokens=300)
    if was_mock:
        return _mock_gate_result(symbol, filing_text)
    result = _extract_json(raw)
    result["mock"] = False
    return result


def judge(sensed: dict, trigger_meta: dict) -> dict:
    raw, was_mock = _call_llm(
        JUDGE_SYSTEM,
        json.dumps({"trigger_meta": trigger_meta, "sensed_data": sensed}, indent=2, default=str),
        max_tokens=1500,
    )
    if was_mock:
        return _mock_judgment(sensed, trigger_meta)
    result = _extract_json(raw)
    result["mock"] = False
    return result
