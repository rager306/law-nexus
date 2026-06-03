# M055 S02 Internal Diagnostic Backend Adapter

## Status

Finalized for `M055-dbt65v / S02 / T03`.

This artifact defines the ACP-facing contract for the first internal git-lex diagnostic backend adapter. It promotes M054 wrapper behavior toward an internal adapter interface, but it does **not** promote git-lex to ACP source truth, main-repository `.lex` state, production runtime, release/plugin-bundled binary trust, or LegalGraph requirement validation.

## Purpose

M055 accelerates ACP backend work by reusing the M054 proof-only git-lex wrapper as an L1 shadow diagnostic/projection backend.

The S02 adapter contract exists to make that acceleration safe:

```text
backend_level: L1-shadow-diagnostic-projection
authority: non-authoritative-diagnostic
source_truth: ACP-native records
runtime_scope: isolated backend workspace only
main_repo_state: no .lex, no Squad, no Raw
```

The adapter may help ACP produce diagnostics, projections, and implementation-readiness evidence. It may not decide requirements, migrate authority, ingest real legal payloads, or mutate the main repository's git-lex state.

## Evidence baseline

The adapter must build from these prior anchors:

```text
prd/architecture/acp/M054-S01-PINNED-SOURCE-ADAPTER-CONTRACT.md
scripts/git_lex_diagnostic_adapter.py
tests/test_git_lex_diagnostic_adapter.py
prd/architecture/acp/M054-S03-ISOLATED-RUNTIME-DIAGNOSTIC-MATRIX.md
prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl
prd/architecture/acp/M054-S04-PROOF-ONLY-ADAPTER-SPIKE-SYNTHESIS.md
prd/architecture/acp/M055-S01-GIT-LEX-BACKEND-ADOPTION-CUTLINE.md
```

M054 proved only this narrow claim:

```text
A pinned source-built proof-only wrapper can run the minimal git-lex diagnostic subset in an isolated synthetic workspace and emit bounded non-authoritative JSON diagnostics while keeping the main checkout free of .lex/Squad/Raw residue.
```

S02 may reuse that claim. S02 must not widen it.

## Backend role

| Field | Contract |
|---|---|
| Backend level | `L1-shadow-diagnostic-projection` |
| Backend status | internal diagnostic backend, not production backend |
| Authority | `non-authoritative-diagnostic` |
| Source truth | ACP-native records remain authoritative |
| Workspace | isolated adapter-managed workspace outside `/root/law-nexus` |
| Main repository state | `.lex`, `Squad`, and `Raw` must remain absent |
| Payload class | synthetic ACP-shaped records first; no real legal text/session/provider payloads |
| Requirement validation | cannot validate R035/R037/R038 |
| Production status | blocked |

## ACP-facing diagnostic record schema

The S02 adapter must emit bounded ACP-facing records. It may consume M054 records internally, but durable ACP-facing records must not leak private raw fields.

### Required top-level fields

| Field | Required | Meaning |
|---|---:|---|
| `schema_version` | yes | Use `m055.acp_git_lex_backend_diagnostic.v1` unless explicitly versioned later. |
| `record_id` | yes | Stable UUID or deterministic diagnostic id. |
| `backend_level` | yes | Always `L1-shadow-diagnostic-projection` for S02. |
| `backend_name` | yes | `git-lex` or a narrower adapter name. |
| `adapter_version` | yes | Internal adapter schema/implementation version. |
| `source_record_id` | yes when applicable | ACP source/fixture record id that triggered the operation. |
| `source_record_type` | yes when applicable | ACP source category such as `decision`, `evidence_anchor`, `proof_gate`, or `diagnostic_record`. |
| `source_record_lifecycle` | yes when applicable | ACP lifecycle state if known; otherwise `synthetic-fixture`. |
| `operation` | yes | ACP-facing operation name from the allowed mapping below. |
| `operation_class` | yes | `read-only`, `projection`, `validation-diagnostic`, or `policy-rejection`. |
| `classification` | yes | Normalized outcome classification. |
| `authority` | yes | Always `non-authoritative-diagnostic`. |
| `can_validate_requirement` | yes | Always `false` in S02. |
| `can_mutate_source_truth` | yes | Always `false` in S02. |
| `workspace_path` | yes | Isolated backend workspace or `null` for read-only help. |
| `workspace_is_main_repo` | yes | Must be `false`. |
| `main_lex_absent_before` | yes | Safety field from wrapper or direct check. |
| `main_lex_absent_after` | yes | Safety field from wrapper or direct check. |
| `main_squad_absent_before` | yes | Safety field from wrapper or direct check. |
| `main_squad_absent_after` | yes | Safety field from wrapper or direct check. |
| `main_raw_absent_before` | yes | Safety field from wrapper or direct check. |
| `main_raw_absent_after` | yes | Safety field from wrapper or direct check. |
| `git_lex_source_commit` | yes | Must preserve D077 pin unless a later decision changes it. |
| `binary_sha256` | yes | Must preserve the pinned binary identity unless a later decision changes it. |
| `wrapper_schema_version` | yes | M054 wrapper schema version consumed. |
| `wrapper_operation_id` | yes when derived | Original M054 wrapper operation id. |
| `result_count` | optional | Bounded count from list/query operations. |
| `observed_validated_count` | validation only | Parsed validation count if present. |
| `query_id` | query only | Predefined bounded query id. |
| `diagnostic_summary` | yes | Bounded, redacted human-readable summary. |
| `error_class` | when non-pass | Normalized error class from the table below. |
| `cleanup_status` | yes | `not-needed`, `clean`, `residue-recorded`, or `failed`. |
| `created_at` | yes | ISO-8601 timestamp. |

### Prohibited durable fields

The S02 ACP-facing record must not include:

```text
_stdout_raw
_stderr_raw
raw stdout blobs
raw stderr blobs
raw legal text
provider payloads
Claude/session logs
vectors
secrets
absolute paths as proof anchors, except ephemeral workspace diagnostics
```

Bounded digests or summaries are allowed only when redacted and non-authoritative.

## Allowed operation mapping

S02 may expose only these ACP-facing operations.

| ACP operation | M054 wrapper operation | Underlying git-lex surface | Operation class | Contract |
|---|---|---|---|---|
| `backend_help` | `help` | `git-lex --help` | `read-only` | Identity/help diagnostic only. |
| `workspace_init` | `init` | `git-lex init --kit <kit> <workspace>` | `projection` | Controlled isolated backend workspace only. |
| `workspace_sync` | `sync` | `git-lex sync` | `projection` | Isolated backend workspace only; fixtures must be controlled. |
| `class_inventory` | `list_json` | `git-lex list --json` | `projection` | Shape/class inventory diagnostic, not ontology/source truth. |
| `bounded_query` | `query` | predefined `git-lex query` | `projection` | No arbitrary SPARQL pass-through. |
| `bounded_query_json` | `query_json` | predefined `git-lex query --json` | `projection` | Parse full stdout internally, emit bounded ACP record. |
| `validation_diagnostic` | `validate_wrapped` | `git-lex validate` behind gates | `validation-diagnostic` | Fail-closed diagnostic only; cannot validate ACP requirements. |
| `reject_denied` | `reject_denied` | no execution | `policy-rejection` | Denied surfaces rejected before git-lex execution. |

The initial bounded query IDs remain inherited from M054 unless S02 explicitly adds tests and contract text for a new predefined query:

```text
graph_inventory
frontmatter_fixture
negative_empty
history_reifies_ask
```

## Blocked and rejected surfaces

The S02 adapter must reject these surfaces without executing git-lex:

```text
save
create
raw
raw backfill
join
kit-update
nuke
display
serve
viz
listen
history-verify
dump
parse
```

Rationale:

- `save`, `create`, `raw`, `raw backfill`, `join`, `kit-update`, and `nuke` are mutating, broad-staging, network-dependent, raw-payload, or destructive surfaces.
- `display`, `serve`, `viz`, and `listen` are server/browser surfaces outside the L1 adapter.
- `history-verify`, `dump`, and `parse` are optional diagnostics that were deliberately excluded from the initial backend track to keep S02 narrow.

If any blocked surface is needed later, it requires a new proof gate, updated contract, tests, and explicit adoption decision where appropriate.

## Normalized classifications

The adapter must normalize M054 wrapper classifications into ACP-facing classifications without hiding the original wrapper classification.

| ACP classification | M054 source classification | Meaning |
|---|---|---|
| `pass` | `pass` | Operation completed and safety fields passed. |
| `diagnostic-fail` | `git-lex-fail` | git-lex returned a meaningful diagnostic failure, such as concrete SHACL violation. |
| `adapter-fail` | `wrapper-fail` | Adapter/wrapper setup, parsing, expected-count, shape, fixture, or safety gate failed. |
| `blocked` | `blocked` | Operation was not allowed to run because a required precondition failed. |
| `rejected` | `rejected` | Denied or unsupported operation was rejected before execution. |
| `not-run` | `not-run` | Planned diagnostic was not executed. |

The original M054 classification should remain available as `wrapper_classification` for debugging.

## Error classification contract

Non-pass records should include one of these `error_class` values when applicable:

| Error class | Use when |
|---|---|
| `denied-surface` | Requested operation is blocked by the S02 denylist. |
| `unsupported-operation` | Requested operation is not in the allowed ACP operation mapping. |
| `workspace-policy-violation` | Workspace is the main repository or a child of it. |
| `binary-identity-failed` | Pinned binary is missing or hash does not match. |
| `source-pin-mismatch` | Reported source commit differs from D077 pin without later decision. |
| `missing-shape` | Expected validation shape is absent. |
| `missing-fixture` | Expected validation fixture is absent. |
| `validation-count-mismatch` | `Validated N files` does not match expected count. |
| `validation-setup-ambiguous` | Output indicates skipped/setup/load/parse/schema/compile/processor ambiguity. |
| `concrete-validation-violation` | Negative validation produced concrete SHACL violation evidence. |
| `json-parse-failed` | JSON output could not be parsed from private full stdout. |
| `query-id-rejected` | Query id is not one of the predefined bounded IDs. |
| `main-state-residue` | Main `.lex`, `Squad`, or `Raw` appeared before/after operation. |
| `cleanup-failed` | Isolated workspace cleanup failed or residue was recorded. |
| `unknown-adapter-error` | Last-resort adapter error; should include bounded diagnostic summary. |

## M054 normalization rules

The S02 adapter should treat M054 records as raw backend diagnostics and normalize them into ACP-facing records as follows:

1. Preserve `git_lex_source_commit`, `binary_sha256`, operation id, operation type, classification, result counts, query id, validation counts, workspace path, cleanup status, and main-state safety fields.
2. Add ACP-facing `backend_level`, `source_record_id`, `source_record_type`, `source_record_lifecycle`, `operation_class`, `can_validate_requirement: false`, and `can_mutate_source_truth: false`.
3. Convert `operation_type` into the ACP operation mapping above.
4. Convert M054 `classification` into the normalized ACP classification table above.
5. Preserve M054 `authority` only if it equals `non-authoritative-diagnostic`; otherwise classify as `adapter-fail` with `error_class: source-pin-mismatch` or another precise class.
6. Strip `_stdout_raw`, `_stderr_raw`, and any private/raw payload fields before returning or persisting ACP-facing records.
7. Use full private stdout only inside parsing functions, never as durable proof output.
8. Bound `stdout_digest`, `stderr_digest`, and `diagnostic_summary`; redact secrets if encountered.
9. Treat any main-state safety failure as `adapter-fail` with `error_class: main-state-residue`, even if the wrapper operation otherwise passed.
10. Treat setup/skipped/parse/load/schema/compile/processor diagnostics during validation as adapter failures, not requirement or validation proof.

## Validation diagnostic rules

`validation_diagnostic` may produce `pass` only when all of these are true:

1. workspace is isolated and not the main repository;
2. expected shape paths exist;
3. expected fixture paths exist;
4. pinned binary identity passes;
5. `git-lex validate` exits `0`;
6. `Validated N files` is parsed;
7. parsed count equals expected count;
8. setup/skipped/load/parse/schema/compile/processor diagnostics are absent;
9. main `.lex`, `Squad`, and `Raw` remain absent before and after;
10. output remains `non-authoritative-diagnostic`.

For negative fixtures, `diagnostic-fail` is acceptable only when git-lex exits non-zero with a concrete SHACL violation and without setup ambiguity. That is useful diagnostic evidence, not ACP requirement-validation evidence.

## Authority and proof boundaries

The S02 adapter output may support:

```text
agent diagnostics
architecture verification hints
shadow projection checks
backend feasibility assessment
S03 ACP-shaped synthetic runtime proof
```

The S02 adapter output may not support:

```text
ACP source truth
main repository .lex adoption
production backend adoption
release/plugin-bundled binary trust
R035 validation
R037 validation
R038 validation
Russian legal evidence correctness
FalkorDB runtime behavior
Garant ODT parser completeness
JSON-LD runtime support
broad RDF-star/SPARQL-star parity
real legal payload ingestion
Claude/session log proof anchors
provider payload proof anchors
```

## Implementation expectations for S02/T02

The implementation should be small and boring:

1. add `scripts/acp_git_lex_backend.py`;
2. import or wrap `scripts/git_lex_diagnostic_adapter.py` instead of shelling out to a broader command surface;
3. expose typed functions and/or a narrow CLI for the allowed ACP operations only;
4. keep the M054 denylist effective;
5. normalize records using this contract;
6. add `tests/test_acp_git_lex_backend.py` for schema normalization, allowed dispatch, denied command rejection, raw field stripping, safety fields, and source/binary identity preservation;
7. keep main `.lex`, `Squad`, and `Raw` absent;
8. avoid real legal text, provider payloads, raw session logs, vectors, and secrets.

Before editing existing symbols during S02/T02, run GitNexus impact analysis for those symbols with `repo: "law-nexus"`.

## S03 handoff constraints

S03 should consume this adapter over ACP-shaped synthetic fixtures only.

S03 must preserve:

```text
backend_level: L1-shadow-diagnostic-projection
source_truth: ACP-native records
authority: non-authoritative-diagnostic
main .lex: absent
main Squad: absent
main Raw: absent
payloads: synthetic ACP-shaped records only
real legal text: prohibited
session logs/provider payloads: prohibited
R035/R037/R038 validation: prohibited
```

S03 runtime evidence should be tracked as bounded JSONL diagnostics, not raw git-lex output.

## T01 disposition

```text
S02/T01 disposition: adapter-contract-specified
backend level: L1-shadow-diagnostic-projection
record schema: specified
operation mapping: specified
blocked surfaces: specified
error classifications: specified
M054 normalization rules: specified
S02/T02 readiness: ready for narrow implementation
S03 handoff constraints: specified
```

## T02 implementation summary

S02/T02 implemented the internal ACP-facing git-lex diagnostic backend adapter.

Implemented files:

```text
scripts/acp_git_lex_backend.py
tests/test_acp_git_lex_backend.py
```

Implementation result:

| Surface | Result |
|---|---|
| Adapter module | `scripts/acp_git_lex_backend.py` exists. |
| M054 reuse | Adapter imports/wraps `scripts/git_lex_diagnostic_adapter.py`; it does not shell out to arbitrary git-lex commands. |
| Backend level | ACP-facing records emit `L1-shadow-diagnostic-projection`. |
| Schema | ACP-facing records emit `m055.acp_git_lex_backend_diagnostic.v1`. |
| Authority | Records preserve `non-authoritative-diagnostic`. |
| Requirement validation | Records keep `can_validate_requirement: false`. |
| Source-truth mutation | Records keep `can_mutate_source_truth: false`. |
| Operation allowlist | Adapter exposes only `backend_help`, `workspace_init`, `workspace_sync`, `class_inventory`, `bounded_query`, `bounded_query_json`, `validation_diagnostic`, and `reject_denied`. |
| Denied surfaces | Denied command handling remains delegated to the M054 denylist and rejects without git-lex execution. |
| Raw field handling | Private `_stdout_raw` / `_stderr_raw` fields are not emitted in ACP-facing records; their presence forces an adapter-fail diagnostic. |
| Main-state safety | Main `.lex`, `Squad`, and `Raw` safety fields are preserved and safety failure overrides pass classifications. |
| Diagnostic failures | Concrete validation failures map to `diagnostic-fail`, while remaining non-authoritative. |

Test coverage added:

```text
schema normalization
allowed wrapper dispatch
denied command rejection
private raw field stripping
main-state residue override
validation diagnostic failure mapping
CLI JSON output for denied commands
```

## T03 final verification results

Fresh S02/T03 verification command set:

```text
uv run pytest tests/test_acp_git_lex_backend.py tests/test_git_lex_diagnostic_adapter.py
uv run ruff check scripts/acp_git_lex_backend.py scripts/git_lex_diagnostic_adapter.py tests/test_acp_git_lex_backend.py tests/test_git_lex_diagnostic_adapter.py
test ! -e .lex
test ! -e Squad
test ! -e Raw
git diff --check
gitnexus_detect_changes({repo:"law-nexus", scope:"all"})
```

Observed acceptance evidence for S02/T03:

```text
pytest: 14 tests passed in 0.54s
ruff: all checks passed
main .lex: absent
main Squad: absent
main Raw: absent
git diff --check: pass
report marker checks: pass
GitNexus scope: low risk, 0 changed symbols, 0 affected processes
```

## Known limitations

S02 intentionally does not prove or enable:

```text
production runtime adoption
release or plugin-bundled binary trust
main repository .lex adoption
ACP source-truth migration
real legal payload ingestion
Claude/session log proof anchors
provider payload proof anchors
R035/R037/R038 validation
Russian legal evidence correctness
FalkorDB runtime behavior
Garant ODT parser completeness
JSON-LD runtime support
broad RDF-star/SPARQL-star parity
server/viz/listen usage
save/create/raw/join/kit-update/nuke usage
```

Additional implementation caveats:

1. Runtime behavior remains inherited from the pinned M054 wrapper and D077 source-built debug binary.
2. S02 tests validate normalization and adapter dispatch boundaries; S03 must still run ACP-shaped synthetic fixture runtime proof.
3. `gitnexus_detect_changes` may report zero changed symbols for current untracked Python files; this is treated as scope evidence, not symbol-level coverage.
4. GitNexus impact lookups for M054 wrapper operation symbols returned target-not-found while those symbols are untracked/unindexed; no existing Python symbols were edited in S02/T02.
5. Durable ACP-facing diagnostics must remain bounded and must not include private raw stdout/stderr.

## S03 handoff

S03 should start from the implemented adapter and prove only the L1 shadow diagnostic/projection backend over ACP-shaped synthetic fixtures.

S03 may use:

```text
scripts/acp_git_lex_backend.py
scripts/git_lex_diagnostic_adapter.py
tests/test_acp_git_lex_backend.py
tests/test_git_lex_diagnostic_adapter.py
```

S03 should create or update:

```text
prd/architecture/acp/M055-S03-ACP-SHAPED-SHADOW-BACKEND-RUNTIME.md
prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl
```

S03 fixture policy:

```text
synthetic ACP-shaped records only
no real legal documents
no raw Claude/session logs
no provider payloads
no vectors
no secrets
no main .lex
no main Squad
no main Raw
```

S03 operation policy:

```text
allowed: backend_help, workspace_init, workspace_sync, class_inventory, bounded_query, bounded_query_json, validation_diagnostic, reject_denied
blocked: save, create, raw, raw backfill, join, kit-update, nuke, display, serve, viz, listen, history-verify, dump, parse
```

S03 evidence policy:

```text
emit bounded ACP-facing diagnostics
track JSONL evidence under prd/architecture/acp/runtime/m055-s03/
record backend_level: L1-shadow-diagnostic-projection
record authority: non-authoritative-diagnostic
preserve can_validate_requirement: false
preserve can_mutate_source_truth: false
record source_record_id/source_record_type/source_record_lifecycle for each synthetic fixture
verify main .lex/Squad/Raw absent before and after
```

S03 must not claim:

```text
ACP source truth
production backend readiness
main repository .lex readiness
R035/R037/R038 validation
Russian legal evidence correctness
FalkorDB runtime proof
Garant ODT parser proof
JSON-LD runtime support
broad RDF-star/SPARQL-star parity
```

## S02 final disposition

```text
S02 final disposition: internal-diagnostic-backend-adapter-ready-for-s03
backend level: L1-shadow-diagnostic-projection
implementation: complete
contract tests: complete
adapter authority: non-authoritative-diagnostic
main .lex adoption: blocked
source-truth migration: blocked
production adoption: blocked
S03 readiness: ready for ACP-shaped synthetic runtime proof
```
