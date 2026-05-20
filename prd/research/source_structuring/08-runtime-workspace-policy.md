# M032 S01 — Runtime Workspace and Persistence Policy

## Status

- Milestone: `M032-hy6i8r — MiniMax Assisted Source Discovery CLI`
- Slice: `S01 — Runtime Workspace and Persistence Policy`
- Policy status: `draft_t01_artifact_roots`
- Upstream foundation: `prd/research/source_structuring/07-foundation-assessment.md`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## Purpose

M032 moves from deterministic ConsultantPlus XML inventory toward MiniMax-assisted source discovery. The CLI should discover regularities, artifacts, structures, relationships, and graph-context signals. It should not merely process XML files.

This policy defines where runtime artifacts live and how much detail they should preserve.

The source data is open legal data. The policy should not over-redact useful source context. The trajectory log must be detailed enough to reconstruct and analyze the discovery path. Practical hygiene still applies for secrets, API keys, irrelevant local absolute paths, raw provider transport payloads, and reproducibility noise.

## Artifact roots

The M032 runtime workspace is rooted under:

```text
law-source/consultant/runtime/
```

Runtime subdirectories:

```text
law-source/consultant/runtime/
  inbox/
  raw/
  registry/
  processed/
  runs/
  trajectory/
  discovery/
  minimax-attempts/
  verifier/
  external-review/
```

Durable research summaries remain outside the runtime workspace:

```text
prd/research/source_structuring/
```

## Directory responsibilities

| Directory | Responsibility | Persistence default | Notes |
| --- | --- | --- | --- |
| `runtime/inbox/` | Operator-supplied source batches and manifests. | local or ignored | May contain open legal source files. |
| `runtime/raw/` | Content-addressed raw source store. | local or ignored | Raw source is open, but may be bulky and should not be accidentally staged. |
| `runtime/registry/` | Source artifact, revision, batch, and identity metadata. | candidate for selective tracking | Metadata may become durable if useful and reviewed. |
| `runtime/processed/` | Deterministic processed inventory and structural outputs. | candidate for selective tracking | Safe processed outputs may be promoted when useful. |
| `runtime/runs/` | Run envelopes, inputs, outputs, metrics, event logs, and review packs. | local by default | Selected summaries may be promoted. |
| `runtime/trajectory/` | Detailed discovery trajectory logs. | local by default, summarized into research | Should preserve enough context for analysis. |
| `runtime/discovery/` | Normalized discovery candidates and graph-context signals. | candidate for selective tracking | Candidate records are not accepted graph truth until verified. |
| `runtime/minimax-attempts/` | MiniMax attempt summaries, prompt summaries, response summaries, hashes, and attempt metadata. | local by default, selected summaries promoted | Do not persist raw provider transport payloads unless explicitly needed and reviewed. |
| `runtime/verifier/` | Deterministic verifier decisions, review queue items, and rejection reasons. | candidate for selective tracking | Useful for audit and candidate lifecycle. |
| `runtime/external-review/` | GPT-5.5 external review packs and external review summaries. | candidate for selective tracking after review | GPT-5.5 remains external control over CLI outputs, not embedded runtime judge. |
| `prd/research/source_structuring/` | Human-readable contracts, proofs, promoted summaries, and assessments. | tracked durable research | Contains curated conclusions and bounded evidence. |

## Open legal data logging policy

Open legal/source context may be preserved in trajectory logs when it helps analyze discovery. This includes bounded excerpts, visible structural markers, source headings, repeated phrases, article/section markers, and other context needed to understand a discovered pattern or relationship.

Do not remove useful legal/source context merely because it is text. Over-redaction is a failure mode because it prevents later analysis of why MiniMax or the deterministic pipeline proposed a structure.

## Practical hygiene exclusions

The CLI should avoid persisting:

- API keys and secrets;
- local absolute host paths when repo-relative or workspace-relative refs are enough;
- raw provider transport payloads, headers, and low-level HTTP dumps;
- irrelevant runtime noise;
- accidental binary blobs or bulky intermediate files in durable research artifacts.

These exclusions are practical reproducibility and hygiene rules, not a claim that the open legal source data is sensitive.

## Tracking defaults

The default tracking policy is conservative about bulky/generated runtime files but not hostile to open legal content.

| Path | Default | Reason |
| --- | --- | --- |
| `runtime/inbox/` | ignored/local | Operator input area; may contain arbitrary batch drops. |
| `runtime/raw/` | ignored/local | Raw source files are open legal data but may be bulky and should not be accidentally committed. |
| `runtime/registry/` | selectively tracked after review | Safe metadata can become durable evidence when useful. |
| `runtime/processed/` | selectively tracked after review | Safe structural outputs may support graph-context work. |
| `runtime/runs/` | ignored/local by default | Run envelopes can be numerous; promote summaries instead of every run. |
| `runtime/trajectory/` | ignored/local by default, curated excerpts promoted | Detailed logs are useful but may be large. Preserve detail locally, summarize durably. |
| `runtime/discovery/` | selectively tracked after review | Candidate records may be durable if they are compact and useful. |
| `runtime/minimax-attempts/` | ignored/local by default, summarized durably | Attempt details may include provider internals; keep normalized summaries. |
| `runtime/verifier/` | selectively tracked after review | Verifier decisions and review queues are useful audit evidence. |
| `runtime/external-review/` | selectively tracked after review | External GPT-5.5 review outputs can be durable after curation. |
| `prd/research/source_structuring/` | tracked | Durable contracts, proofs, summaries, and assessments. |

## Promotion categories

Runtime outputs can move through these categories:

1. `local_only`: useful for debugging or exploratory analysis but not curated.
2. `candidate_durable`: compact and potentially useful; requires review before tracking.
3. `promoted_summary`: curated into `prd/research/source_structuring/` as human-readable or compact JSON evidence.
4. `superseded`: kept only if needed for audit; not the current evidence path.

Promotion should preserve enough analytical context to explain the discovery. Do not strip open legal/source context that is needed to understand a pattern, relationship, or graph signal.

## Runtime to research promotion rule

Runtime artifacts can be promoted into `prd/research/source_structuring/` only when they are curated into a human-readable conclusion or compact machine-readable evidence summary.

Promotion should preserve:

- what was discovered;
- why it matters for graph context;
- which trajectory steps and source refs support it;
- which open legal/source context is needed to understand the discovery;
- which candidates were accepted, rejected, or left as needs_review;
- what remains uncertain.

Promotion should remove or normalize:

- API keys and secrets;
- irrelevant local absolute paths;
- raw provider transport payloads and headers;
- noisy retry/debug dumps that do not help reproduce the discovery;
- bulky duplicate intermediates.

## Cross-slice artifact handoff contract

M032 slices exchange artifacts through stable identifiers, not ad hoc filenames alone. Each downstream artifact should reference upstream `run_id`, `step_id`, `candidate_id`, or `decision_id` where available.

### S02 trajectory contract

S02 defines trajectory schemas and writes the contract for:

- `runtime/trajectory/trajectory.jsonl`
- `runtime/trajectory/discovery_steps.jsonl`
- `runtime/trajectory/filtering_decisions.jsonl`
- `runtime/trajectory/rejected_branches.jsonl`
- `runtime/trajectory/conclusion_trace.json`

Required handoff fields:

- `run_id`
- `step_id`
- `parent_step_id`
- `phase`
- `operation`
- `input_refs`
- `observed_context`
- `decision`
- `decision_reason`
- `output_refs`

### S03 MiniMax inside CLI contract

S03 adds MiniMax-assisted discovery inside the CLI. MiniMax is allowed at this stage as a non-authoritative structural discovery worker. It may propose patterns, artifacts, structures, relationships, and graph-context signals.

S03 writes normalized attempt artifacts under:

- `runtime/minimax-attempts/attempts.jsonl`
- `runtime/minimax-attempts/prompt_summaries.jsonl`
- `runtime/minimax-attempts/response_summaries.jsonl`

Required handoff fields:

- `run_id`
- `attempt_id`
- `source_step_id`
- `prompt_summary`
- `response_summary`
- `candidate_refs`
- `model_name`
- `non_authoritative: true`

Raw provider transport dumps are not the default durable interface. Normalized summaries are the handoff surface.

### S04 candidate contract

S04 normalizes discovery output into graph-context candidates under:

- `runtime/discovery/candidate_hypotheses.jsonl`
- `runtime/discovery/graph_context_signals.jsonl`
- `runtime/discovery/artifact_candidates.jsonl`
- `runtime/discovery/structure_candidates.jsonl`
- `runtime/discovery/relationship_candidates.jsonl`

Candidate records must reference:

- `candidate_id`
- `run_id`
- `source_step_ids`
- `source_refs`
- `candidate_kind`
- `candidate_summary`
- `supporting_context`
- `confidence_bucket`
- `status: proposed`

A candidate is not accepted graph truth until S05 verifier status changes it.

### S05 deterministic verifier contract

S05 integrates deterministic verifier decisions under:

- `runtime/verifier/verifier_decisions.jsonl`
- `runtime/verifier/review_queue_items.jsonl`
- `runtime/verifier/rejection_reasons.jsonl`

Verifier decisions must reference:

- `decision_id`
- `run_id`
- `candidate_id`
- `candidate_kind`
- `status: accepted | rejected | needs_review`
- `decision_reason`
- `checked_refs`
- `trajectory_step_ids`

Deterministic verifier gates candidate adoption. MiniMax output alone is never enough to adopt a graph-context candidate.

### S06 external GPT-5.5 review contract

S06 builds an external review pack under:

- `runtime/external-review/review_pack.json`
- `runtime/external-review/review_pack.md`
- `runtime/external-review/external_review_summary.md`

GPT-5.5 remains external control over CLI outputs. It is not an embedded runtime judge in M032.

The review pack should include:

- trajectory summary;
- MiniMax attempt summaries;
- candidate summaries;
- verifier outcomes;
- rejected branches;
- conclusion trace;
- open questions;
- non-claims.

### S07 assessment contract

S07 promotes curated conclusions into:

- `prd/research/source_structuring/09-discovery-run-assessment.md`

The assessment should explain:

- what was discovered;
- what was useful for graph context;
- which candidates were accepted, rejected, or left as needs_review;
- what trajectory evidence supports the conclusions;
- what external review should inspect;
- what the next milestone should do.

S07 must preserve the same non-claims as this policy.

## Non-claims

This policy does not claim:

- legal correctness;
- parser completeness;
- product retrieval quality;
- ontology validation;
- graph-vector behavior;
- production ETL readiness;
- pilot readiness;
- R035 validation;
- R038 validation.

## T01 verification markers

This draft intentionally names `runtime/inbox`, `runtime/raw`, `runtime/registry`, `runtime/processed`, `runtime/runs`, `runtime/trajectory`, `runtime/discovery`, `runtime/minimax-attempts`, `runtime/verifier`, `runtime/external-review`, `prd/research/source_structuring`, open legal data, detailed trajectory logs, MiniMax attempt summaries, GPT-5.5 external review packs, practical hygiene, and runtime to research promotion.
