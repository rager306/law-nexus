---
milestone: M024-eb6mo4
slice: S04
status: independent-review
verdict: PASS_AFTER_REMEDIATION
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-18
---

# M024 Independent Proof Review

## Verdict

```text
PASS_AFTER_REMEDIATION
```

M024 S02/S03 produced useful bounded evidence and, after remediation, no longer has the two High proof-chain issues identified by independent review.

## Review method

Independent review was performed with a reviewer subagent against M024 S02/S03 artifacts. The first review returned `REQUEST_CHANGES` with two High findings:

1. Safe input verifier accepted arbitrary raw/prose/path-like `representation_tokens`.
2. Semantic scoring CLI accepted injected runtime/scores JSON as an acceptance-proof path.

After remediation, the reviewer rechecked the same two findings and returned:

```text
Verdict remains: PASS.
```

## Remediated findings

### High 1 — representation token grammar was too permissive

Status: remediated.

Remediation:

- `scripts/verify-semantic-retrieval-safe-inputs.py` now enforces a strict token grammar.
- Tokens must match a safe `prefix:value` format.
- Prefixes are restricted to the allowed safe vocabulary:
  - `as_of`
  - `candidate`
  - `case_class`
  - `citation`
  - `edition`
  - `evidence_span`
  - `query_hash`
  - `query_kind`
  - `scope`
  - `source_block`
  - `source_record`
- Generic absolute path fragments are rejected.

Regression tests now cover:

- Cyrillic raw-query-like token;
- `/etc/passwd` token;
- generated answer/prose-like `answer:allowed` token;
- Windows path token;
- existing raw text/vector/provider/answer leakage cases.

### High 2 — injected runtime/scores acceptance bypass

Status: remediated.

Remediation:

- `scripts/verify-semantic-observed-retrieval-scoring.py` rejects `--runtime-json` and `--scores-json` unless `--allow-injected-test-inputs` is explicitly set.
- Test-only injected mode cannot write the acceptance proof artifact.
- Unit tests can still use injected data to test metric math and blocked-runtime logic, but acceptance proof generation remains tied to the real runtime path.

Regression tests now cover:

- CLI rejection of injected runtime/scores as acceptance proof;
- CLI rejection of test-only injected mode when writing a proof artifact;
- runtime blocked behavior;
- raw vector persistence rejection;
- expected-answer leakage;
- wrong scoring mode;
- missing score.

## Verified evidence

Remediation focused tests and lint:

```text
gsd_exec[ea647f4b-d0b1-4261-9121-494f5fef365c]
25 passed

gsd_exec[34c682b7-1391-4897-b093-837960099517]
All checks passed
```

Real safe-input verifier and semantic scorer refresh:

```text
gsd_exec[531f0214-3c85-4553-ba6f-db0dbd7499bc]
status: completed
scoring_mode: local_user_bge_m3_safe_token_similarity_v1
```

The refreshed scorer still reports the same honest below-threshold metrics:

```text
mrr: 0.875
recall_at_1: 0.75
recall_at_3: 1.0
positive_with_distractor_relevant_first: 0.0
runtime_boundary_confirmed: 1.0
threshold_failures:
  - mrr
  - recall_at_1
  - positive_with_distractor_relevant_first
```

## Residual findings

No blocking findings remain for M024 closeout.

Residual limitation retained:

- Safe token-bag semantic scoring runs locally but does not meet strict representative fixture thresholds.
- This is a bounded negative/partial result, not a product-quality or R035 validation result.

## Requirement disposition

### R035

R035 must remain active and not validated. M024 adds bounded evidence that local USER-bge-m3 can score safe token-bag representations, but below-threshold metrics prevent any retrieval-quality validation claim.

### R038

R038 remains active and applied. M024 demonstrates the independent proof-review gate catching and remediating proof-chain weaknesses, but future proof-heavy milestones still need their own independent review.

## Non-claims

M024 does not prove:

- R035 validation;
- product retrieval quality;
- legal-answer correctness;
- parser completeness;
- parser-to-EvidenceSpan materialization;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- pilot readiness.
