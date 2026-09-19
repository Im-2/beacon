# Beacon Daily Summary — 2026-09-18

## 2026-09-18T14:19:41.489280+00:00 — VLO (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (3107 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T14:20:09.280753+00:00 — VLO (TEST_FIXTURE, category=test)

- **Outcome:** test_fixture_dry_run
- **LLM judgment:** bullish (confidence 72), decision=long, conviction=65
- **Rationale:** TEST FIXTURE — synthetic rationale to exercise RISK/EXECUTE/LOG with a realistic non-no-trade shape, since judge.py's real mock always forces no-trade for safety.
- **Proposed size/stop/target:** 4.0% / SL 3.0% / TP 6.0%
- **Risk check:** approved=True — All risk checks passed.
- **Order:** {'dry_run': True, 'paper_trading': True, 'request': {'method': 'POST', 'path': '/api/v2/spot/trade/place-order', 'body': '{"symbol":"VLOUSDT","side":"buy","orderType":"market","force":"gtc","size":"400.00","clientOid":"beacon-VLO-1789741209"}', 'body_obj': {'symbol': 'VLOUSDT', 'side': 'buy', 'orderType': 'market', 'force': 'gtc', 'size': '400.00', 'clientOid': 'beacon-VLO-1789741209'}}, 'stop_loss_pct': 3.0, 'take_profit_pct': 6.0, 'status': 'SKIPPED_NO_CREDENTIALS', 'reason': 'BITGET_API_KEY/SECRET_KEY/PASSPHRASE are still placeholders in .env.'}

---

## 2026-09-18T20:33:24.704850+00:00 — VLO (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (3107 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:33:30.142508+00:00 — PM (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** trigger_fired_filtered_non_substantive
- **7.01 substantive-content gate:** {'substantive': False, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (73 chars).', 'mock': True}

---

## 2026-09-18T20:33:34.908807+00:00 — STLD (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (8000 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:33:40.422807+00:00 — PGR (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (8000 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:33:45.568892+00:00 — CRM (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** trigger_fired_filtered_non_substantive
- **7.01 substantive-content gate:** {'substantive': False, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (73 chars).', 'mock': True}

---

## 2026-09-18T20:33:51.839924+00:00 — TXN (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (6173 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:33:57.715673+00:00 — ALL (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** trigger_fired_filtered_non_substantive
- **7.01 substantive-content gate:** {'substantive': False, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (73 chars).', 'mock': True}

---

## 2026-09-18T20:34:03.435403+00:00 — ROST (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** trigger_fired_filtered_non_substantive
- **7.01 substantive-content gate:** {'substantive': False, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (73 chars).', 'mock': True}

---

## 2026-09-18T20:34:08.291261+00:00 — LEN (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:34:13.576736+00:00 — VMRK (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (8000 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:34:19.120619+00:00 — EXE (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (5072 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:34:24.667787+00:00 — CNC (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** trigger_fired_filtered_non_substantive
- **7.01 substantive-content gate:** {'substantive': False, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (73 chars).', 'mock': True}

---

## 2026-09-18T20:34:30.450907+00:00 — NKE (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** trigger_fired_filtered_non_substantive
- **7.01 substantive-content gate:** {'substantive': False, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (73 chars).', 'mock': True}

---

## 2026-09-18T20:34:35.915395+00:00 — HBAN (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** trigger_fired_filtered_non_substantive
- **7.01 substantive-content gate:** {'substantive': False, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (73 chars).', 'mock': True}

---

## 2026-09-18T20:34:43.183495+00:00 — OKE (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (8000 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:34:48.659116+00:00 — PWR (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (2662 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:34:55.247905+00:00 — CTVA (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (8000 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:35:01.587111+00:00 — AXON (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (8000 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:35:10.679779+00:00 — OTIS (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (7637 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:35:16.400634+00:00 — CHTR (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (2174 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:35:22.890539+00:00 — COF (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** trigger_fired_filtered_non_substantive
- **7.01 substantive-content gate:** {'substantive': False, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (73 chars).', 'mock': True}

---

## 2026-09-18T20:35:46.384284+00:00 — COF (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (2034 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:35:51.901006+00:00 — TFC (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** no_trade_llm_decision
- **7.01 substantive-content gate:** {'substantive': True, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (2340 chars).', 'mock': True}
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:35:57.547553+00:00 — AXP (8-K_guidance_or_earnings_item, category=post_event_reactive)

- **Outcome:** trigger_fired_filtered_non_substantive
- **7.01 substantive-content gate:** {'substantive': False, 'reason': 'MOCK (no real LLM call — QWEN_API_KEY not configured): heuristic pass/fail on filing text length only (73 chars).', 'mock': True}

---

## 2026-09-18T20:36:01.235186+00:00 — AIR (anticipatory_earnings_positioning, category=anticipatory_positioning)

- **Outcome:** no_trade_llm_decision
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

## 2026-09-18T20:36:04.133785+00:00 — EBF (anticipatory_earnings_positioning, category=anticipatory_positioning)

- **Outcome:** no_trade_llm_decision
- **LLM judgment:** neutral (confidence 0), decision=no-trade, conviction=0
- **Rationale:** This is a placeholder decision generated because no real LLM key is configured for JUDGE_PROVIDER=qwen. It intentionally decides no-trade so it can never accidentally trigger a real or paper order. Once a real key is set, this ticker's trigger should be re-run to get an actual judgment.
- **Proposed size/stop/target:** 0% / SL 0% / TP 0%
- **Risk check:** approved=False — LLM decision was no-trade.

---

