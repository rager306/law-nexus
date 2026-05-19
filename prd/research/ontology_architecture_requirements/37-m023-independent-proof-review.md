---
milestone: M023-9rfkrs
slice: S04
review_type: independent-proof-review
status: findings-addressed
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-18
---

# M023 Independent Proof Review

This report records the independent proof-review gate required by R038 for M023. The review was read-only and focused on whether M023 remediated M022's self-confirming metrics problem without overstating safe-ID rule retrieval as semantic or product retrieval quality.

## Review scope

Reviewed artifacts included:

- `prd/research/ontology_architecture_requirements/34-observed-retrieval-proof-remediation-contract.md`
- `prd/research/ontology_architecture_requirements/35-observed-retrieval-provenance-proof.md`
- `prd/research/ontology_architecture_requirements/36-observed-retrieval-output-metrics-proof.md`
- `prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_query_provenance_registry.json`
- `prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_source_provenance_manifest.json`
- `prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_outputs.json`
- `scripts/verify-observed-retrieval-provenance.py`
- `scripts/verify-observed-retrieval-output-metrics.py`
- `tests/test_observed_retrieval_provenance.py`
- `tests/test_observed_retrieval_output_metrics.py`

Review agents:

- `reviewer` checked proof strength, observed-output separation, non-claims, and overclaim risk.
- `tester` checked vacuous tests, mocks, hardcodes, fail-closed coverage, and runtime/proof boundaries.

## Review verdict before remediation

The independent review returned `REQUEST_CHANGES` with two medium findings:

1. Residual self-confirming risk remains because `safe_id_provenance_rule_retrieval_v1` is a safe-ID rule proof, not semantic model retrieval.
2. The query provenance registry duplicated expected answer fields, which weakened the separation between query provenance and expected fixture answers.

The review also noted that focused tests and verifiers passed, but passing tests do not by themselves prove semantic retrieval quality.

## Finding 1 — safe-ID rule retrieval remains bounded

Severity: medium.

Finding:

`safe_id_provenance_rule_retrieval_v1` creates observed outputs at the safe-ID artifact-control layer. It remediates M022's direct fixture-derived metric calculation by requiring a separate observed-output artifact and comparing observed IDs/diagnostics to expected fixture answers. However, it does not prove semantic model retrieval, natural-language retrieval quality, legal-answer correctness, or product retrieval quality.

Disposition:

Deferred as an explicit boundary, not a blocker for M023 closeout.

Rationale:

M023's contract was remediation of the self-confirming fixture metrics gap, not full semantic retrieval quality. The artifacts and proof note explicitly state that `safe_id_provenance_rule_retrieval_v1` is not product semantic retrieval proof. The next horizon must decide whether to build real semantic retrieval scoring over safe query/provenance inputs.

Required follow-up:

Future retrieval-quality work must add a semantic observed retrieval proof if it wants to claim model retrieval behavior. That future proof must produce observed rankings from actual query/candidate scoring, not only safe-ID rule outputs.

## Finding 2 — query registry duplicated expected answer fields

Severity: medium.

Finding:

The initial query provenance registry included expected answer fields such as expected candidate IDs, rejected IDs, and diagnostic codes. That blurred the boundary between query provenance and expected fixture answers.

Disposition:

Remediated in S04.

Remediation:

Removed these fields from each query provenance entry:

```text
expected_candidate_ids
expected_rejected_candidate_ids
expected_diagnostic_codes
```

Updated the observed-output artifact's query registry hash reference and updated the S02 proof note wording so the query registry is described as provenance-only rather than answer-bearing.

Remediation evidence:

```text
gsd_exec[4bc2f4a8-186e-47b3-bc88-d49bf207c022]
```

The remediation verification chain passed:

```text
provenance verifier: status=ok
observed-output evaluator: status=passed
focused tests: 17 passed
ruff: All checks passed
query registry expected-answer duplication removed
```

## Test-quality assessment

The focused tests are not empty. They include negative cases for:

- unregistered query hash;
- bogus source case ID / manifest drift;
- bogus source record ID;
- source artifact hash mismatch;
- unsafe payload field;
- missing observed output;
- expected fixture fields appearing inside observed output;
- retrieval mode mismatch;
- missing positive observed ranking;
- diagnostic metric mismatch;
- blocked runtime.

The remaining limitation is conceptual, not test-vacuity: the acceptance proof is a safe-ID rule retrieval proof, not semantic model retrieval quality.

## Runtime-path note

The review noted that direct `python3` execution can differ from the project `uv run` environment. M023 acceptance verification uses `uv run` and real runtime verification passed in the tracked S03/final chains. Unit tests use injected runtime JSON only for fast fail-closed coverage; acceptance proof uses the evaluator command through the project environment.

## What M023 proves after review

M023 proves:

- query hashes are registered in a safe provenance registry without raw query text;
- source candidate provenance checks go beyond path/hash anchoring for source cases and source records;
- observed safe-ID outputs are stored separately from expected fixture fields;
- observed-output metrics are computed by comparing observed IDs/diagnostics to expected fixture fields;
- tests fail closed for selected provenance, observed-output, runtime, and unsafe-payload errors;
- independent proof review is now part of the milestone closeout process.

## What M023 does not prove

M023 does not prove:

- semantic model retrieval quality;
- product retrieval quality;
- legal-answer correctness;
- parser-to-EvidenceSpan materialization;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- R035 validation.

## Closeout recommendation

M023 may close after final verification because the remediable medium finding was fixed and the remaining medium finding is explicitly bounded as a non-goal: safe-ID rule retrieval is not semantic retrieval quality. The next proof horizon should either move to semantic observed retrieval scoring or parser-to-EvidenceSpan materialization, depending on product priority.
