# S08: S08

**Goal:** Produce the final M001 architecture review report and a minimal machine-readable findings artifact/schema that classify PRD and smoke/parser/embedding findings with evidence, impact, owner, resolution path, verification criteria, and roadmap effect, while preserving M001 architecture-only and local/open-weight embedding boundaries.
**Demo:** M001 closes with actionable architecture guidance for M002 and roadmap corrections grounded in smoke/source evidence.

## Must-Haves

- `prd/05_final_architecture_review.md` exists for the cold reader: the M002-M007 implementation planner/future agent, with an executive verdict, evidence inventory, findings matrix, roadmap corrections, machine-readable findings path/schema proposal, and non-goal/overclaim guardrails.
- R001 is directly satisfied: material PRD claims and architecture findings are classified with severity, evidence, impact, recommendation, owner, and roadmap effect.
- R009 is directly satisfied: every material fixed/deferred/bounded/blocked issue consumed from S04/S05/S07/S09/S10 has owner, resolution path, and verification criteria.
- R010 is directly satisfied: `.gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json` and `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json` exist, validate structurally, and the report proposes a future canonical machine-readable path such as `prd/findings/architecture-findings.v1.json`.
- R011 is respected as a compatibility constraint: no task implements product ETL, LegalNexus API, KnowQL parser, hybrid retrieval, production graph schema, production parser, or legal-answering runtime.
- Required deferred S07 handoff items G-005, G-008, G-011, and G-015 remain explicitly classified and mapped to roadmap/proof gates.
- Threat surface/Q3: the report itself is the risk surface; verifier coverage must prevent misleading overclaims, copying sensitive/legal content beyond existing evidence summaries, or treating `.gsd` evidence as product data.
- Requirement impact/Q4: R001/R009/R010 are owned acceptance criteria; R011 and D002 are compatibility constraints that must remain honored.

## Proof Level

- This slice proves: Contract/reporting proof with executable structural verification. This slice proves the final architecture review report, findings rows, schema proposal, and verifier contract are internally consistent and bounded by prior evidence. It does not prove live LegalGraph runtime behavior, production retrieval quality, final ODT extraction, FalkorDB production scale, or future M002-M007 implementation.

## Integration Closure

Consumes upstream evidence from `prd/04_review_findings.md`, S04 FalkorDB smoke artifacts, S05 ODT/parser/Old_project findings, S06 skill refresh, and S09/S10 embedding evidence. Introduces no product runtime wiring; it closes M001 by composing those evidence surfaces into `prd/05_final_architecture_review.md`, `.gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json`, `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json`, and `scripts/verify-s08-final-report.py`. Before M002-M007 are truly usable end-to-end, downstream milestones must implement and verify the deferred proof gates named in the report.

## Verification

- `uv run pytest tests/test_verify_s08_final_report.py`
- `uv run python scripts/verify-s08-final-report.py --report prd/05_final_architecture_review.md --findings .gsd/milestones/M001/slices/S08/S08-FINDINGS.json --schema .gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json`
- Upstream compatibility checks for consumed evidence: run the existing S04, S05, and S10 verifier command shapes before requirement validation.
- `rg -n "G-005|G-008|G-011|G-015|machine-readable|owner|resolution|verification|roadmap" prd/05_final_architecture_review.md`
- `git diff --check`
- `gitnexus_detect_changes({repo:"law-nexus", scope:"all"})` before claiming completion.
- Diagnostics expectation: `scripts/verify-s08-final-report.py` emits precise failures naming missing fields, missing required IDs, invalid schema rows, missing report sections, and overclaim markers.

<tasks>
- [x] **T01**: Defined the S08 findings schema and seeded bounded architecture evidence rows for final M001 review. _(1.5h)_
  Skills expected: `legalgraph-nexus`, `falkordb-legalgraph`, `russian-legal-evidence`, `write-docs`.
  - Files: `.gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json`, `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json`, `prd/04_review_findings.md`, `.gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json`, `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md`, `.gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json`, `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json`
  - Verify: uv run python - <<'PY'
- [x] **T02**: Drafted the M001 final architecture review report with bounded evidence, roadmap gates, and machine-readable findings guidance. _(2h)_
  Skills expected: `write-docs`, `legalgraph-nexus`, `falkordb-legalgraph`, `russian-legal-evidence`.
  - Files: `prd/05_final_architecture_review.md`, `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json`, `.gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json`
  - Verify: test -s prd/05_final_architecture_review.md && rg -n "M002|M003|M004|M005|M006|M007|G-005|G-008|G-011|G-015|machine-readable|owner|verification|roadmap" prd/05_final_architecture_review.md
- [x] **T03**: Added a strict S08 final-report verifier and regression tests that keep findings rows, report prose, evidence paths, and overclaim guardrails synchronized. _(2h)_
  Skills expected: `tdd`, `verify-before-complete`, `legalgraph-nexus`, `falkordb-legalgraph`, `russian-legal-evidence`.
  - Files: `scripts/verify-s08-final-report.py`, `tests/test_verify_s08_final_report.py`, `.gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json`, `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json`, `prd/05_final_architecture_review.md`
  - Verify: uv run pytest tests/test_verify_s08_final_report.py && uv run python scripts/verify-s08-final-report.py --report prd/05_final_architecture_review.md --findings .gsd/milestones/M001/slices/S08/S08-FINDINGS.json --schema .gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json
- [x] **T04**: Validated S08 closure checks and recorded R001/R009/R010 requirement evidence. _(1.5h)_
  Skills expected: `verify-before-complete`, `legalgraph-nexus`, `write-docs`.
  - Files: `scripts/verify-s08-final-report.py`, `tests/test_verify_s08_final_report.py`, `prd/05_final_architecture_review.md`, `.gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json`, `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json`, `.gsd/REQUIREMENTS.md`
  - Verify: uv run pytest tests/test_verify_s08_final_report.py && uv run python scripts/verify-s08-final-report.py --report prd/05_final_architecture_review.md --findings .gsd/milestones/M001/slices/S08/S08-FINDINGS.json --schema .gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json && git diff --check
</tasks>

## Files Likely Touched

- .gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json
- .gsd/milestones/M001/slices/S08/S08-FINDINGS.json
- prd/04_review_findings.md
- .gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json
- .gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md
- .gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json
- .gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json
- prd/05_final_architecture_review.md
- scripts/verify-s08-final-report.py
- tests/test_verify_s08_final_report.py
- .gsd/REQUIREMENTS.md
