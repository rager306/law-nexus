# M031 S05 — LLM Worker and DSPy Protocol

## Status

- Milestone: `M031-oqgiow — Consultant XML Source Structuring CLI Foundation`
- Slice: `S05 — LLM Worker and DSPy Protocol Design`
- Protocol status: `draft_t01_role_and_input_boundary`
- Upstream evidence:
  - `prd/research/source_structuring/03-deterministic-source-cli-proof.md`
  - `prd/research/source_structuring/04-overnight-run-review-pack-proof.md`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## Purpose

This protocol defines how future LLM workers may propose structural hypotheses from deterministic ConsultantPlus XML source lifecycle artifacts without becoming legal authorities.

The protocol is deterministic-first and non-authoritative by design:

1. S03/S04 produce safe lifecycle artifacts.
2. A worker may propose a bounded structural hypothesis from safe refs only.
3. A deterministic verifier must accept, reject, or route the hypothesis to review.
4. No hypothesis becomes adopted evidence until deterministic verifier output exists.

S05 does not call MiniMax, GPT-5.5, DSPy, RLM, embeddings, FalkorDB, or any provider API. S05 defines the protocol only.

## Actors

| Actor | Allowed role | Not allowed |
| --- | --- | --- |
| `MiniMax worker` | Non-authoritative structural hypothesis proposer or reviewer over safe source lifecycle refs. | Legal interpretation, legal-answer drafting, parser-completeness assertion, source-of-truth decision, raw provider payload persistence. |
| `GPT-5.5 worker` | Non-authoritative structural hypothesis proposer or protocol reviewer over safe source lifecycle refs. | Legal authority, legal-answer generation, direct adoption of hypotheses, raw prompt/completion persistence. |
| `DSPy candidate program` | Deferred orchestration candidate for optimizing structural-hypothesis prompts after deterministic schemas and verifier metrics stabilize. | Runtime dependency for S05, legal reasoning authority, bypass of deterministic verifier, provider payload persistence. |
| `RLM router` | Deferred routing/selection candidate for choosing structural hypothesis workers after safe metrics exist. | Runtime dependency for S05, legal authority, claim promotion, hidden routing over raw text. |
| `Deterministic verifier` | Sole acceptance gate for proposed structural hypotheses. It checks closed schemas, source refs, run refs, output refs, constraints, and rejection reasons. | Generating new legal claims, accepting free-form LLM prose, accepting raw text/provider payloads, validating R035 by itself. |
| `Human reviewer` | Reviews verifier evidence and rejected/needs_review queues. | Treating unverified worker output as legal truth or parser completeness proof. |

## Allowed inputs

Workers may receive only safe references and aggregate metadata from S03/S04 outputs:

- `source_artifact_id`
- `source_revision_id`
- `run_id`
- `corpus_id`
- `output_refs`
- `parser_route`
- `source_family`
- `document_role`
- `metrics.safe.json` aggregate counts
- `diagnostics.safe.jsonl` bounded diagnostic categories
- `review_pack.json` summary fields
- `review_pack.md` summary sections that contain no raw legal text
- `workspace_tracking.status` warning state

Workers may not receive or persist raw source files, raw XML snippets, paragraph text, article text, legal-answer prose, provider payloads, secrets, raw vectors, or absolute host paths.

## Forbidden durable payload classes

Durable worker, proposal, review, and verifier artifacts must exclude:

- raw legal text;
- raw XML;
- raw filenames that may contain legal title text;
- absolute paths;
- raw LLM prompts;
- raw LLM completions;
- raw provider payloads;
- provider headers;
- credentials or secret names;
- raw vectors or embedding arrays;
- legal-answer prose;
- parser-completeness claims;
- product retrieval-quality claims;
- R035 validation claims.

## Non-authoritative boundary

Every worker artifact must include:

```json
{
  "non_authoritative": true,
  "non_claims": [
    "worker output is a structural hypothesis only",
    "worker output does not claim legal correctness",
    "worker output does not claim parser completeness",
    "worker output does not validate R035",
    "worker output must be accepted or rejected by deterministic verifier evidence"
  ]
}
```

## Closed payload schemas

The schemas below are sketches for future implementation. They are intentionally closed: fields not listed here are rejected by the deterministic verifier skeleton.

### `structural_hypothesis_proposal`

```json
{
  "schema_version": "legalgraph-structural-hypothesis-proposal/v1",
  "proposal_id": "SHP-<hash12>",
  "worker_attempt_id": "WA-<hash12>",
  "source_artifact_id": "SA-CONSULTANT-<hash12>",
  "source_revision_id": "SR-CONSULTANT-<document-key>-<hash12>",
  "run_id": "RUN-<hash12>",
  "output_refs": ["processed/consultant-wordml-v1/<corpus_id>/source_inventory.safe.jsonl"],
  "source_family": "consultant_wordml",
  "document_role": "full_normative_act",
  "parser_route": "full_act",
  "hypothesis_kind": "structural_marker_rule",
  "hypothesis_payload": {
    "selector": "root:wordDocument:namespace_sha256:<hash12>",
    "safe_rule_id": "RULE-<hash12>",
    "confidence_bucket": "low|medium|high",
    "evidence_refs": ["metrics.safe.json", "diagnostics.safe.jsonl", "review_pack.json"]
  },
  "verifier_status": "pending",
  "non_authoritative": true,
  "non_claims": [
    "proposal is a structural hypothesis only",
    "proposal does not claim legal correctness",
    "proposal does not claim parser completeness",
    "proposal does not validate R035"
  ]
}
```

Allowed `hypothesis_kind` values:

- `structural_marker_rule`
- `document_role_routing_hint`
- `safe_section_boundary_hint`
- `diagnostic_bucket_hint`

Allowed `confidence_bucket` values:

- `low`
- `medium`
- `high`

The `hypothesis_payload` must not contain raw legal text, raw XML, raw filenames, absolute paths, raw LLM prompts, raw LLM completions, raw provider payloads, provider headers, secrets, raw vectors, legal-answer prose, parser-completeness claims, product retrieval-quality claims, or R035 validation claims.

### `worker_attempt_summary`

```json
{
  "schema_version": "legalgraph-worker-attempt-summary/v1",
  "worker_attempt_id": "WA-<hash12>",
  "worker_kind": "minimax|gpt55|dspy_candidate|rlm_router",
  "input_ref_hashes": ["sha256:<hash>"],
  "source_artifact_ids": ["SA-CONSULTANT-<hash12>"],
  "run_id": "RUN-<hash12>",
  "proposal_ids": ["SHP-<hash12>"],
  "attempt_status": "proposed|rejected_before_verification|needs_review",
  "redaction_status": "passed",
  "non_authoritative": true,
  "non_claims": [
    "worker attempt summary excludes raw prompt and completion payloads",
    "worker attempt summary is not legal authority",
    "worker attempt summary does not validate R035"
  ]
}
```

Allowed `worker_kind` values:

- `minimax`
- `gpt55`
- `dspy_candidate`
- `rlm_router`

Allowed `attempt_status` values:

- `proposed`
- `rejected_before_verification`
- `needs_review`

### `verifier_decision`

```json
{
  "schema_version": "legalgraph-verifier-decision/v1",
  "proposal_id": "SHP-<hash12>",
  "verifier_id": "deterministic-source-structure-verifier/v1",
  "verifier_status": "pending|accepted|rejected|needs_review",
  "checked_refs": ["processed/consultant-wordml-v1/<corpus_id>/metrics.safe.json"],
  "acceptance_evidence_refs": ["runs/<run_id>/review_pack.json"],
  "rejection_reasons": [],
  "decision_notes": ["closed schema accepted and safe refs resolved"],
  "non_authoritative": true,
  "non_claims": [
    "verifier decision accepts or rejects a structural hypothesis only",
    "verifier decision does not claim legal correctness",
    "verifier decision does not claim parser completeness",
    "verifier decision does not validate R035"
  ]
}
```

Allowed `verifier_status` values:

- `pending`
- `accepted`
- `rejected`
- `needs_review`

A proposal may be `accepted` only if all of these are true:

1. the proposal schema is closed and valid;
2. every source/run/output ref resolves to a safe S03/S04 artifact ref;
3. no forbidden durable payload class is present;
4. the proposal has at least one deterministic evidence ref;
5. the verifier records an explicit status and non-claim set.

Allowed `rejection_reasons` values:

- `schema_violation`
- `missing_safe_ref`
- `forbidden_payload_class`
- `raw_text_detected`
- `absolute_path_detected`
- `provider_payload_detected`
- `legal_answer_prose_detected`
- `insufficient_deterministic_evidence`
- `parser_completeness_overclaim`
- `r035_validation_overclaim`

### `review_queue_item`

```json
{
  "schema_version": "legalgraph-review-queue-item/v1",
  "queue_item_id": "RQ-<hash12>",
  "proposal_id": "SHP-<hash12>",
  "worker_attempt_id": "WA-<hash12>",
  "verifier_status": "needs_review",
  "review_reason": "insufficient_deterministic_evidence",
  "safe_summary": "bounded structural hypothesis requires reviewer decision",
  "evidence_refs": ["runs/<run_id>/review_pack.json"],
  "non_authoritative": true,
  "non_claims": [
    "review queue item is not legal authority",
    "review queue item does not claim parser completeness",
    "review queue item does not validate R035"
  ]
}
```

The `safe_summary` field is bounded operational prose only. It must not contain legal-answer prose, raw legal text, raw filenames, provider payloads, secrets, raw vectors, or absolute paths.

## Deterministic acceptance workflow

Future worker loops must follow this sequence:

1. `prepare_safe_context`
   - Read only S03/S04 safe artifacts: registry rows, processed safe inventory, diagnostics, metrics, run envelope, and review pack summaries.
   - Refuse raw XML, raw legal text, raw filenames, absolute paths, provider payloads, secrets, and vectors.
2. `propose_structural_hypothesis`
   - A MiniMax worker, GPT-5.5 worker, DSPy candidate program, or RLM router may emit only `structural_hypothesis_proposal` plus `worker_attempt_summary`.
   - The proposal begins with `verifier_status: "pending"`.
3. `pre_verification_safety_scan`
   - Deterministic code checks closed schema fields, safe refs, non-claims, and forbidden payload classes before any semantic acceptance check.
   - Failure here produces `verifier_status: "rejected"` and a rejection reason such as `schema_violation` or `forbidden_payload_class`.
4. `deterministic_evidence_check`
   - Deterministic code resolves source refs, run refs, output refs, metrics refs, diagnostics refs, and review pack refs.
   - The verifier checks whether the proposal is supported by structural counts, route metadata, or diagnostic buckets.
5. `decision_record`
   - The verifier writes one `verifier_decision` with exactly one status: `accepted`, `rejected`, or `needs_review`.
   - `accepted` means only that a structural hypothesis passed deterministic checks. It does not mean legal correctness, parser completeness, retrieval quality, or R035 validation.
6. `review_queue`
   - `needs_review` decisions create `review_queue_item` records with safe summaries and evidence refs.
   - Human reviewers inspect verifier evidence, not raw LLM prose as authority.

## Failure-state taxonomy

| Failure state | Meaning | Required observable artifact |
| --- | --- | --- |
| `schema_violation` | Payload includes missing, extra, or invalid fields. | `verifier_decision` with `rejected` and schema error category. |
| `missing_safe_ref` | A referenced S03/S04 artifact ref cannot be resolved. | `verifier_decision` with missing ref category. |
| `forbidden_payload_class` | Payload contains forbidden class such as raw text, provider payload, secret, vector, absolute path, or legal-answer prose. | `verifier_decision` with redaction/safety category. |
| `raw_text_detected` | Raw legal or XML text appears in a durable artifact. | `verifier_decision` plus safety scan evidence. |
| `absolute_path_detected` | Host path appears in durable artifact. | `verifier_decision` plus path safety evidence. |
| `provider_payload_detected` | Prompt, completion, headers, request, or response payload appears in durable artifact. | `verifier_decision` plus payload safety evidence. |
| `legal_answer_prose_detected` | Artifact attempts to answer a legal question instead of proposing structure. | `verifier_decision` plus boundary evidence. |
| `insufficient_deterministic_evidence` | Proposal may be plausible but lacks deterministic support. | `needs_review` or `rejected` decision with evidence refs. |
| `parser_completeness_overclaim` | Artifact claims parser completeness. | `rejected` decision and non-claim repair requirement. |
| `r035_validation_overclaim` | Artifact claims R035 validation. | `rejected` decision and requirement-boundary repair requirement. |

## DSPy and RLM deferral rules

DSPy and RLM remain deferred candidates in S05:

- No DSPy runtime dependency is added in S05.
- No RLM runtime dependency is added in S05.
- No optimizer, router, or training loop runs in S05.
- DSPy may later optimize structural-hypothesis prompts only after S06 has deterministic verifier metrics.
- RLM may later route among worker strategies only after safe run/review metrics exist.
- Neither DSPy nor RLM may bypass the deterministic verifier.
- Neither DSPy nor RLM may process raw legal text, raw XML, raw provider payloads, secrets, raw vectors, absolute paths, or legal-answer prose in durable artifacts.

## S06 verifier skeleton handoff

S06 should implement executable validation without calling any LLM:

- Load sample `structural_hypothesis_proposal` payloads.
- Validate closed schema fields and enum values.
- Resolve safe refs syntactically against S03/S04 artifact conventions.
- Reject forbidden payload classes.
- Require `non_authoritative: true` and non-claim markers.
- Emit `verifier_decision` records with `accepted`, `rejected`, or `needs_review`.
- Emit `review_queue_item` records for unresolved but safe hypotheses.
- Test negative cases for raw legal text, provider payloads, absolute paths, legal-answer prose, parser-completeness overclaim, and R035 validation overclaim.

Rejected hypotheses remain auditable as safe verifier decisions. They do not become legal claims, parser claims, retrieval claims, architecture promotions, or accepted product evidence.

## Safe handoff to S06

S06 should implement a deterministic verifier skeleton against this protocol. It should not call an LLM. It should validate closed proposal payloads, safe refs, verifier statuses, rejection reasons, non-claims, and forbidden payload exclusions.

## T01 verification markers

This T01 draft intentionally contains the actor names `MiniMax`, `GPT-5.5`, `DSPy`, `RLM`, and `Deterministic verifier`, safe input refs such as `source_artifact_id`, `run_id`, `output_refs`, `metrics.safe.json`, `diagnostics.safe.jsonl`, and `review_pack.json`, and forbidden payload classes such as raw legal text, raw provider payloads, secrets, raw vectors, absolute paths, and legal-answer prose.

## S05 proof summary

S05 passes for protocol-design scope.

Fresh verification:

```bash
uv run pytest tests/test_source_structuring_protocol.py -q
uv run ruff check tests/test_source_structuring_protocol.py
```

Observed result:

```text
5 passed
All checks passed.
```

The focused tests verify:

- required actor and input-boundary markers;
- closed schema names and status contract;
- failure taxonomy and S06 handoff markers;
- DSPy/RLM deferral and non-claim boundaries;
- absence of concrete forbidden payload examples such as temporary paths, repository absolute paths, raw legal text examples, fake leak markers, and secret-like names.

This proof advances `R039` by specifying how future LLM/MiniMax/GPT-5.5/DSPy/RLM workers may propose structural hypotheses against deterministic source lifecycle artifacts. It does not validate `R035` or `R038`.
