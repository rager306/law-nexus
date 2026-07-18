---
id: M008
title: "Parser/Retrieval Golden-Test Proof"
status: complete
completed_at: 2026-05-12T08:08:02.366Z
key_decisions:
  - Exactly five closed-enum case classes (evidence-present, no-answer, candidate-only, unresolved-reference, non-authoritative) rather than open-ended categories — closed-enum semantics enable deterministic test assertions.
  - Separate --write (freshness=not-checked) and --check (emits actual freshness) as independent CLI modes — enables CI pipelines to run generation and verification steps independently.
  - Standalone evaluator CLI (evaluate-parser-golden-cases.py) without modifying generator functions — avoids coupling, enables independent fail-closed behavior test coverage.
  - Cold-reader proof report as non-authoritative inspection surface rather than executable layer — prevents encoding implementation assumptions as facts; preserves all non-claims.
key_files:
  - prd/parser/golden_test_contract.md
  - prd/parser/golden_cases.json
  - prd/parser/golden_cases.md
  - prd/parser/golden_test_proof_report.md
  - prd/parser/README.md
  - scripts/build-parser-golden-cases.py
  - scripts/evaluate-parser-golden-cases.py
  - tests/test_parser_golden_contract.py
  - tests/test_parser_golden_cases.py
  - tests/test_parser_golden_evaluator.py
  - tests/test_parser_golden_proof_report.py
lessons_learned:
  - Source-anchor requirements must be contractual from S01, not retrofitted — requiring anchors in the contract phase meant S02/S03 could assert them without negotiation.
  - Venv Python (.venv/bin/python3) must be used for all verification commands — system Python lacks pydantic and pytest causing ModuleNotFoundError.
  - Non-authoritative boundary must be propagated through every layer (contract → schema → evaluator output → guardrail tests) — any single-layer omission weakens the boundary.
  - Unresolved Consultant endpoint warnings (REL-CONS-0001) were initially ambiguous as failures; classification as expected boundary evidence required explicit rationale in the contract phase rather than being obvious from the start.
---

# M008: Parser/Retrieval Golden-Test Proof

**Implemented bounded executable golden-test harness over tracked M006 parser artifacts with five case classes, write/check-separated generator, fail-closed evaluator CLI, 36 passing pytest tests, and cold-reader proof report.**

## What Happened

Four slices (S01–S04) implemented a complete bounded golden-test proof chain over tracked M006 parser artifacts. S01 established the five-closed-enum case-class contract (evidence-present, no-answer, candidate-only, unresolved-reference, non-authoritative) with source-anchor rules, diagnostic shape, blocked-claims list, and explicit non-claim boundaries. S02 implemented `scripts/build-parser-golden-cases.py` with write/check separation, producing `prd/parser/golden_cases.json` and `prd/parser/golden_cases.md` covering all five case classes with per-case source anchors. S03 implemented `scripts/evaluate-parser-golden-cases.py` as a standalone fail-closed evaluator CLI that exits non-zero on any contract drift (missing anchors, stale hashes, status promotion, fabricated evidence) and emits compact JSON with path-qualified diagnostics without echoing raw legal text; 17 pytest tests cover happy path, negative cases, anchor/hash drift, and non-authoritative boundaries. S04 produced `prd/parser/golden_test_proof_report.md` as a cold-reader inspection surface summarizing command evidence and limitations, `tests/test_parser_golden_proof_report.py` with 6 guardrail tests, updated README handoff with three-surface separation and final command chain, and validated R032 in REQUIREMENTS.md. R032 is validated for bounded executable golden-test scope only; it does not prove parser completeness, product retrieval quality, citation-safe retrieval readiness, legal-answer correctness, relation correctness, FalkorDB loading/runtime readiness, product ETL readiness, or product graph truth.

## Success Criteria Results

1. R032 has a bounded, executable golden-test proof over tracked parser artifacts — PASS: `prd/parser/golden_cases.json` contains 5 cases across all required classes; `evaluate-parser-golden-cases.py --check` returns `status: pass`, `error_count: 0`, `evaluated_case_count: 5`. R032 already validated in REQUIREMENTS.md with executable evidence language.

2. Golden cases include evidence-present, no-answer, candidate-only, unresolved-reference, and non-authoritative examples — PASS: JSON artifact confirms classes `['candidate-only', 'evidence-present', 'no-answer', 'non-authoritative', 'unresolved-reference']`; Markdown artifact confirms 5 `## ` headings.

3. All generator/check/evaluator tests pass with deterministic outputs — PASS: 36 pytest tests pass (`test_parser_golden_contract.py` 6 + `test_parser_golden_cases.py` 7 + `test_parser_golden_evaluator.py` 17 + `test_parser_golden_proof_report.py` 6) in 2.90s; evaluator emits deterministic compact JSON with no raw legal text.

4. M006 parser artifacts are consumed as bounded input evidence; no undocumented source rescans — PASS: Generator consumes only `prd/parser/odt_document_records.jsonl`, `prd/parser/odt_source_block_records.jsonl`, `prd/parser/consultant_relation_candidates.jsonl`, `prd/parser/parser_staging_graph.json`; no `law-source/` directories scanned.

5. Non-claims remain explicit in artifacts and summaries — PASS: `evaluate-parser-golden-cases.py --check` output includes `non_authoritative: true` and `blocked_claims` list; `golden_test_proof_report.md` and `golden_cases.md` both list all non-claim boundaries; S04 guardrail tests assert non-claim labels present.

## Definition of Done Results

- All 4 slices complete (S01, S02, S03, S04) — PASS: gsd_milestone_status confirms all slices status=complete, all 12 tasks done=12, pending=0.
- All slice summaries exist — PASS: S01-SUMMARY.md, S02-SUMMARY.md, S03-SUMMARY.md, S04-SUMMARY.md all read successfully.
- Integrations work — PASS: Generator (`build-parser-golden-cases.py --check`) produces status=pass; Evaluator (`evaluate-parser-golden-cases.py --check`) produces status=pass, error_count=0, evaluated_case_count=5; All 36 pytest tests pass; Ruff clean on new files; R032 validated in REQUIREMENTS.md with executable evidence language.

## Requirement Outcomes

R032 — Status changed from active to validated. Evidence: `evaluate-parser-golden-cases.py --check` returns status=pass, error_count=0, evaluated_case_count=5, severity_counts error:0/warning:1/info:2, non_authoritative=true. 36 pytest tests pass. `golden_test_proof_report.md` documents five case classes, command evidence, and complete non-claims list. R032 validation language in REQUIREMENTS.md cites all M008 artifacts and preserves all non-claim boundaries (parser completeness, retrieval quality, legal-answer correctness, relation correctness, FalkorDB loading/runtime, product ETL, product graph truth).

No other requirements changed status in M008. R031 and R017 remain as separate proof gates; M008 explicitly preserves them as non-claims rather than validating them implicitly.

## Deviations

M008 work was committed to main in a prior auto-mode session; the current closeout session found HEAD==main with all implementation files already present and tests already passing. No git diff relative to main was produced in this session, but files exist and verification evidence confirms the work is complete.

## Follow-ups

M006 owns parser completeness proof. Future milestones must separately prove: retrieval quality, citation-safe answers, FalkorDB runtime loading, generated Cypher/Legal KnowQL safety, and legal correctness. GATE-G008 (parser/retrieval golden tests) is now validated by M008; next G008 gate for citation-safe retrieval remains open. R031 and R017 remain as separate proof gates not validated by M008.
