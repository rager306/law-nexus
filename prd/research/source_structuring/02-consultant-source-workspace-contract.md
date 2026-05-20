# M031 S02 — ConsultantPlus Source Workspace and CLI Contract

## Status

- Milestone: `M031-oqgiow — Consultant XML Source Structuring CLI Foundation`
- Slice: `S02 — Source Workspace Layout and CLI Contract`
- Contract status: `draft_for_s02_verification`
- Upstream evidence: `prd/research/source_structuring/01-law-parser-prior-art-assessment.md`
- Decision context: `D063` chose the ConsultantPlus source workspace layout and lifecycle CLI interface.

## Purpose

This contract defines how ConsultantPlus WordML XML documents move through the source-structuring lifecycle before any parser, graph, retrieval, or LLM proof resumes.

The goal is to separate:

1. raw source files;
2. working processed data;
3. safe durable registries and review artifacts;
4. operational run state and logs.

This contract also defines how the CLI identifies document source families, document roles, revisions, parser routes, and failure states without making legal correctness claims.

## Proof pause boundary

Further same-fixture retrieval and descriptor proof cycles remain paused until this source workspace produces safe structural artifacts that can support renewed evidence work.

This contract provides no R035 validation and does not claim parser completeness, legal correctness, product retrieval quality, graph-vector behavior, production ETL readiness, pilot readiness, or LLM legal authority.

## Accepted workspace layout

The ConsultantPlus lifecycle workspace is:

```text
law-source/consultant/
  README.md
  fixtures/
  inbox/
  raw/
  registry/
  processed/
  schemas/
  runs/
```

The GSD and research summary surface is separate:

```text
prd/research/source_structuring/
```

### Directory responsibilities

| Directory | Role | May contain raw legal text? | Intended persistence |
| --- | --- | --- | --- |
| `law-source/consultant/fixtures/` | Small controlled examples used by tests and smoke runs. | yes, if explicitly reviewed as fixtures | tracked only when intentionally small and stable |
| `law-source/consultant/inbox/` | Batch intake area where a user drops document pools. | yes | usually local or temporary |
| `law-source/consultant/raw/` | Immutable content-addressed raw source store by SHA-256. | yes | usually ignored/local unless explicitly approved |
| `law-source/consultant/registry/` | Safe lifecycle metadata for artifacts, revisions, batches, and identity candidates. | no | durable safe metadata |
| `law-source/consultant/processed/` | Parser and source-structuring outputs. Default mode should be safe; debug mode may be local-only. | no in durable safe mode | durable only for safe outputs |
| `law-source/consultant/schemas/` | Source lifecycle schemas and route registry. | no | durable contract |
| `law-source/consultant/runs/` | Run envelopes, events, errors, metrics, outputs, and review packs. | no in durable outputs | durable safe run evidence |
| `prd/research/source_structuring/` | GSD research summaries and milestone contracts. | no | durable human-readable summaries |

### Migration note for current files

The current project has tracked ConsultantPlus XML files directly under `law-source/consultant/`. Until S03 implements the lifecycle CLI, those files are treated as **existing tracked fixtures**. S03 should migrate or copy them into `law-source/consultant/fixtures/` only through an explicit reviewed change.

Parser and CLI code must not glob `law-source/consultant/` directly. It must read a batch manifest or registry.

## Batch intake

A batch has this shape:

```text
law-source/consultant/inbox/<batch_id>/
  incoming/
    *.xml
  batch.manifest.json
```

### `batch.manifest.json` sketch

```json
{
  "schema_version": "legalgraph-source-batch/v1",
  "batch_id": "batch-YYYY-MM-DD-a",
  "source_family_hint": "consultant_wordml",
  "input_policy": {
    "raw_text_allowed_in_input": true,
    "raw_text_allowed_in_durable_outputs": false,
    "absolute_paths_allowed_in_outputs": false
  },
  "artifacts": [
    {
      "submitted_name_hash": "sha256:<hash>",
      "declared_role_hint": "full_normative_act",
      "declared_identity_hint": {
        "jurisdiction": "RU",
        "act_type": "federal_law",
        "act_number": "44-FZ",
        "edition_label": "2026"
      }
    }
  ],
  "non_authoritative": true,
  "non_claims": [
    "declared hints are parser-routing hints only",
    "batch manifest does not claim legal correctness",
    "batch manifest does not claim parser completeness"
  ]
}
```

`submitted_name_hash` is used instead of raw filenames in durable outputs because filenames can contain legal text.

## Raw source store

Raw files are stored by content hash:

```text
law-source/consultant/raw/sha256/<first2>/<next2>/<sha256>.xml
```

Rules:

- same SHA-256 means idempotent replay;
- duplicate submitted names are irrelevant to identity;
- raw storage refs in durable metadata are repository-relative logical refs, never absolute host paths;
- raw store contents are not proof outputs.

## Registry files

### `source_artifacts.jsonl`

One row per raw artifact:

```json
{
  "schema_version": "legalgraph-source-artifact/v1",
  "source_artifact_id": "SA-CONSULTANT-<hash12>",
  "source_family": "consultant_wordml",
  "raw_sha256": "<sha256>",
  "raw_size_bytes": 5235817,
  "media_type": "application/xml",
  "raw_storage_ref": "law-source/consultant/raw/sha256/<first2>/<next2>/<sha256>.xml",
  "detected_shape": {
    "container": "plain_xml",
    "root_local_name": "wordDocument",
    "root_namespace": "http://schemas.microsoft.com/office/word/2003/wordml",
    "well_formed": true
  },
  "non_authoritative": true,
  "non_claims": [
    "artifact record does not claim legal correctness",
    "artifact record does not claim parser completeness"
  ]
}
```

### `source_revisions.jsonl`

One row per source revision candidate:

```json
{
  "schema_version": "legalgraph-source-revision/v1",
  "source_revision_id": "SR-CONSULTANT-<document-key>-<hash12>",
  "source_artifact_id": "SA-CONSULTANT-<hash12>",
  "source_family": "consultant_wordml",
  "legal_document_key": {
    "jurisdiction": "RU",
    "act_type": "federal_law",
    "act_number": "44-FZ"
  },
  "edition": {
    "edition_date": null,
    "edition_label": "2026",
    "detected_from": "manifest_or_metadata_hint",
    "confidence": "bounded"
  },
  "status": "registered",
  "non_authoritative": true
}
```

### `batches.jsonl`

One row per batch:

```json
{
  "schema_version": "legalgraph-source-batch-run/v1",
  "batch_id": "batch-YYYY-MM-DD-a",
  "source_family_hint": "consultant_wordml",
  "registered_count": 0,
  "duplicate_count": 0,
  "failed_count": 0,
  "status": "registered",
  "non_authoritative": true
}
```

### `document_identity_candidates.jsonl`

Candidate identity rows, not legal truth:

```json
{
  "schema_version": "legalgraph-document-identity-candidate/v1",
  "source_revision_id": "SR-CONSULTANT-<document-key>-<hash12>",
  "candidate_key": {
    "jurisdiction": "RU",
    "act_type": "federal_law",
    "act_number": "44-FZ"
  },
  "signals": ["manifest_hint", "metadata_shape", "filename_hash_context"],
  "confidence": "bounded",
  "requires_review": true,
  "non_authoritative": true
}
```

## Source family versus document role

The CLI must separate **source format/provenance** from **document role**.

### `source_family`

Examples:

```text
consultant_wordml
garant_odt
official_html
court_pdf
unknown
```

For M031 MVP, only `consultant_wordml` is implemented. Future source families may be registered as planned or shape-only, but must not silently process.

### `document_role`

Examples:

```text
full_normative_act
government_resolution
ministry_order
fas_decision
court_act
review
document_list
amendment_act
unknown
unsupported
```

A ConsultantPlus WordML file may have any of these roles. Therefore `consultant_wordml` must not be treated as equivalent to `federal_law`.

## Classification rows

`source_classification.safe.jsonl` row sketch:

```json
{
  "schema_version": "legalgraph-source-classification/v1",
  "source_revision_id": "SR-CONSULTANT-<document-key>-<hash12>",
  "source_family": "consultant_wordml",
  "document_role": "full_normative_act",
  "parser_route": "consultant_wordml_full_act_v1",
  "confidence": "bounded_deterministic",
  "classification_signals": {
    "wordml_namespace": true,
    "paragraph_count_bucket": "1000_plus",
    "hyperlink_count_bucket": "1000_plus",
    "table_count_bucket": "1_plus",
    "style_count_bucket": "10_plus"
  },
  "requires_review": false,
  "non_authoritative": true,
  "non_claims": [
    "classification is parser routing only",
    "classification does not claim legal correctness",
    "classification does not claim parser completeness"
  ]
}
```

## Routes

`law-source/consultant/schemas/routes.yaml` sketch:

```yaml
schema_version: legalgraph-source-routes/v1

routes:
  consultant_wordml_full_act_v1:
    source_family: consultant_wordml
    document_roles:
      - full_normative_act
      - government_resolution
      - ministry_order
    emits:
      - document_record
      - source_block_pointer
      - hierarchy_candidate
    non_authoritative: true

  consultant_wordml_relation_list_v1:
    source_family: consultant_wordml
    document_roles:
      - document_list
    emits:
      - document_record
      - relation_candidate
    non_authoritative: true

  consultant_wordml_inventory_only_v1:
    source_family: consultant_wordml
    document_roles:
      - unknown
      - unsupported
      - review
    emits:
      - source_inventory
      - diagnostics
    non_authoritative: true
```

Ambiguous inputs route to `consultant_wordml_inventory_only_v1` or `needs_review`. They must not be forced into a full-act parser.

## Revision policy

```json
{
  "same_sha": "idempotent_replay",
  "changed_sha_same_document": "new_source_revision",
  "same_edition_conflicting_sha": "needs_review",
  "new_edition_date": "new_act_edition_candidate",
  "unknown_edition": "registered_not_downstream_ready"
}
```

Important distinction:

- `source_artifact` is one raw file;
- `source_revision` is one source revision candidate;
- future `ActEdition` is a legal-document model and must not be inferred as legal truth during M031;
- legal validity periods are not the same as file export dates.

## Lifecycle states

Allowed states:

```text
discovered
registered
classified
queued
processing
processed
needs_review
accepted_for_downstream
superseded
rejected
archived
```

| State | Meaning |
| --- | --- |
| `discovered` | File found in inbox, not registered. |
| `registered` | Hash, size, media type, and storage ref recorded. |
| `classified` | Source family, document role, and parser route assigned. |
| `queued` | Included in a run plan. |
| `processing` | CLI is processing it. |
| `processed` | Safe outputs emitted. |
| `needs_review` | Warning, ambiguity, or conflict requires review. |
| `accepted_for_downstream` | Can feed the next bounded step. Not legal truth. |
| `superseded` | Replaced by newer source revision. |
| `rejected` | Unsupported, malformed, unsafe, or wrong source family. |
| `archived` | Preserved for reproducibility but inactive. |

## Processed outputs

Default processed outputs are safe:

```text
law-source/consultant/processed/consultant-wordml-v1/<corpus_id>/
  documents.safe.jsonl
  source_blocks.safe.jsonl
  hierarchy_candidates.safe.jsonl
  relation_candidates.safe.jsonl
  diagnostics.safe.jsonl
  metrics.safe.json
```

For M031, source block outputs should prefer pointers over excerpts:

```json
{
  "schema_version": "legalgraph-source-block-pointer/v1",
  "source_block_id": "SB-CONSULTANT-<hash12>-000001",
  "source_revision_id": "SR-CONSULTANT-<document-key>-<hash12>",
  "source_family": "consultant_wordml",
  "selector": "wordml/body/p[1]",
  "order_index": 1,
  "text_sha256": "<hash>",
  "text_length_bucket": "100_500",
  "marker": {
    "kind": "unknown_or_structural_candidate",
    "normalized_label": "safe_enum_only"
  },
  "non_authoritative": true
}
```

No excerpt text is persisted in durable M031 outputs by default.

## Run layout

Each run creates:

```text
law-source/consultant/runs/<run_id>/
  run.json
  inputs.json
  outputs.json
  events.jsonl
  errors.jsonl
  metrics.json
  review_pack.md
  review_pack.json
```

### `run.json` sketch

```json
{
  "schema_version": "legalgraph-parser-run/v1",
  "run_id": "YYYY-MM-DDTHHMMSSZ-batch-id",
  "batch_id": "batch-YYYY-MM-DD-a",
  "source_family": "consultant_wordml",
  "operation": "run-batch",
  "status": "completed_with_warnings",
  "started_at": "YYYY-MM-DDTHH:MM:SSZ",
  "finished_at": "YYYY-MM-DDTHH:MM:SSZ",
  "non_authoritative": true
}
```

### `inputs.json` sketch

```json
{
  "schema_version": "legalgraph-run-inputs/v1",
  "batch_id": "batch-YYYY-MM-DD-a",
  "source_artifacts": [
    {
      "source_artifact_id": "SA-CONSULTANT-<hash12>",
      "raw_sha256": "<sha256>",
      "source_family": "consultant_wordml",
      "media_type": "application/xml"
    }
  ]
}
```

### `outputs.json` sketch

```json
{
  "schema_version": "legalgraph-run-outputs/v1",
  "records": {
    "document": {
      "path": "law-source/consultant/processed/consultant-wordml-v1/<corpus_id>/documents.safe.jsonl",
      "count": 0
    },
    "source_block_pointer": {
      "path": "law-source/consultant/processed/consultant-wordml-v1/<corpus_id>/source_blocks.safe.jsonl",
      "count": 0
    },
    "diagnostics": {
      "path": "law-source/consultant/processed/consultant-wordml-v1/<corpus_id>/diagnostics.safe.jsonl",
      "count": 0
    }
  },
  "redaction": {
    "raw_legal_text_persisted": false,
    "raw_xml_persisted": false,
    "absolute_paths_persisted": false,
    "provider_payloads_persisted": false,
    "raw_vectors_persisted": false
  },
  "non_authoritative": true
}
```

### `events.jsonl` event names

Minimum event names:

```text
run_started
document_discovered
document_registered
document_classified
document_queued
document_processing_started
document_processed
document_needs_review
document_failed
run_completed
```

### `errors.jsonl` sketch

```json
{
  "schema_version": "legalgraph-source-error/v1",
  "run_id": "<run_id>",
  "source_artifact_id": "SA-CONSULTANT-<hash12>",
  "severity": "warning",
  "error_class": "unsupported_wordml_shape",
  "diagnostic_code": "source_family_recognized_role_unknown",
  "safe_context": {
    "source_family": "consultant_wordml",
    "document_role": "unknown",
    "paragraph_count_bucket": "0_100"
  },
  "non_authoritative": true
}
```

### `metrics.json` sketch

```json
{
  "schema_version": "legalgraph-source-run-metrics/v1",
  "counts": {
    "inbox_files_seen": 0,
    "registered": 0,
    "duplicates": 0,
    "classified": 0,
    "processed": 0,
    "needs_review": 0,
    "failed": 0
  },
  "document_roles": {
    "full_normative_act": 0,
    "government_resolution": 0,
    "ministry_order": 0,
    "fas_decision": 0,
    "court_act": 0,
    "review": 0,
    "document_list": 0,
    "unknown": 0
  },
  "non_authoritative": true
}
```

## Review pack

`review_pack.md` and `review_pack.json` summarize a run for GSD/GPT review.

They must include:

- batch ID and run ID;
- processed counts;
- document role distribution;
- failures and warnings by diagnostic code;
- emitted safe artifact paths;
- next recommended action;
- explicit non-claims.

They must not include:

- raw legal text;
- raw XML;
- prompts containing source text;
- external provider payloads;
- raw vectors;
- secrets;
- absolute host paths;
- generated legal-answer prose.

## CLI surface

The operator-facing CLI is one script:

```text
scripts/source_cli.py
```

Commands:

```text
register
classify
process
status
review-pack
run-batch
```

### `register`

```bash
uv run python scripts/source_cli.py register \
  --batch law-source/consultant/inbox/batch-YYYY-MM-DD-a/batch.manifest.json
```

Responsibilities:

- read batch manifest;
- hash incoming files;
- place or reference raw SHA-addressed files;
- write source artifact and revision registry rows;
- record duplicates and malformed inputs safely.

### `classify`

```bash
uv run python scripts/source_cli.py classify \
  --batch-id batch-YYYY-MM-DD-a
```

Responsibilities:

- detect source family;
- assign document role;
- choose parser route;
- mark ambiguous cases as `needs_review` or `inventory_only`.

### `process`

```bash
uv run python scripts/source_cli.py process \
  --batch-id batch-YYYY-MM-DD-a
```

Responsibilities:

- dispatch by route;
- emit safe processed outputs;
- emit diagnostics and metrics.

### `status`

```bash
uv run python scripts/source_cli.py status \
  --batch-id batch-YYYY-MM-DD-a
```

Responsibilities:

- summarize lifecycle states;
- report latest run state;
- list warnings and failures by diagnostic code.

### `review-pack`

```bash
uv run python scripts/source_cli.py review-pack \
  --run-id YYYY-MM-DDTHHMMSSZ-batch-id
```

Responsibilities:

- generate or refresh run review pack;
- fail if safe artifact checks fail.

### `run-batch`

```bash
uv run python scripts/source_cli.py run-batch \
  --batch law-source/consultant/inbox/batch-YYYY-MM-DD-a/batch.manifest.json \
  --source-family consultant_wordml \
  --profile overnight \
  --no-llm
```

Responsibilities:

- run `register`, `classify`, `process`, `status`, and `review-pack` as one unattended workflow;
- write a run envelope under `law-source/consultant/runs/<run_id>/`;
- preserve enough state for morning review.

## Safety verification contract

Every durable output under these locations must pass safety checks:

```text
law-source/consultant/registry/
law-source/consultant/processed/
law-source/consultant/runs/
prd/research/source_structuring/
```

Forbidden in durable outputs:

```text
raw legal text
raw XML
long excerpts
prompts containing source text
external provider payloads
raw vectors
secrets
absolute host paths
generated legal-answer prose
```

Required in durable outputs:

```text
schema_version
non_authoritative
non_claims where human-readable claims may be inferred
repository-relative logical paths only
source IDs or hashes instead of source filenames when filenames may contain legal text
```

## Verification targets for S03 and S04

S03 implementation should prove:

- `register` creates safe artifact/revision rows;
- `classify` separates `source_family` and `document_role`;
- `process` can emit at least inventory-only safe outputs;
- current tracked ConsultantPlus files can be handled as fixtures or registered inputs without globbing `law-source/consultant/` directly.

S04 implementation should prove:

- `run-batch` creates a run envelope;
- `events.jsonl`, `errors.jsonl`, `metrics.json`, and review packs are generated;
- failure cases remain inspectable after an interrupted or partially failed run;
- safety checks reject forbidden durable payload classes.

## S02 disposition

This contract chooses the workspace and CLI interface for M031. It deliberately does not implement the CLI, move existing files, classify real documents, or validate parser completeness. Those are owned by later slices.
