# M055 S03 ACP Shaped Shadow Backend Runtime

## Status

Finalized for `M055-dbt65v / S03 / T03`.

S03 proves the L1 shadow diagnostic/projection backend over ACP-shaped synthetic records in an isolated runtime workspace. It consumes the S02 adapter and preserves the same authority boundary: git-lex diagnostics are non-authoritative, ACP-native records remain source truth, and no main repository `.lex`, `Squad`, or `Raw` state may be created.

## Purpose

S02 proved the adapter contract and normalization layer. S03 must now prove that the adapter can run a bounded runtime matrix over ACP-shaped synthetic fixtures rather than generic M054 task-only fixtures.

S03 target:

```text
backend_level: L1-shadow-diagnostic-projection
authority: non-authoritative-diagnostic
source_truth: ACP-native records
runtime_scope: isolated shadow workspace only
payload_scope: synthetic ACP-shaped records only
main_repo_state: no .lex, no Squad, no Raw
```

S03 does not prove production readiness, source-truth migration, main `.lex` adoption, legal evidence correctness, FalkorDB behavior, Garant ODT parser completeness, or R035/R037/R038 validation.

## Evidence inputs

S03 consumes these prior artifacts:

```text
prd/architecture/acp/M055-S01-GIT-LEX-BACKEND-ADOPTION-CUTLINE.md
prd/architecture/acp/M055-S02-INTERNAL-DIAGNOSTIC-BACKEND-ADAPTER.md
scripts/acp_git_lex_backend.py
scripts/git_lex_diagnostic_adapter.py
tests/test_acp_git_lex_backend.py
tests/test_git_lex_diagnostic_adapter.py
prd/architecture/acp/M054-S03-ISOLATED-RUNTIME-DIAGNOSTIC-MATRIX.md
prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl
```

M054 runtime proof established the practical git-lex shape path:

```text
kit: squad
shape anchor: .lex/ontology/squad/squad-shapes.ttl
positive runtime class: Squad/Task
task status enum: blocked, cancelled, done, in-progress, todo
negative validation trigger: invalid taskStatus enum value
```

S03 keeps that runtime-compatible `squad` path but changes fixture semantics to ACP-shaped records by encoding ACP source-record concepts in synthetic task records.

## No-real-payload statement

S03 fixtures must be synthetic and sanitized.

Prohibited payloads:

```text
real legal documents
Russian legal text excerpts
ODT/XML provider source text
Claude/session logs
provider payloads
raw model inputs or outputs
vectors or embeddings
secrets or credentials
personal data
main repository .lex state
main repository Squad state
main repository Raw state
```

Allowed payloads:

```text
small synthetic ACP-shaped markdown/frontmatter fixtures
fake source_record_id values
fake lifecycle states
fake evidence anchor paths that point to synthetic/tracked artifacts only
short placeholder prose such as "Synthetic ACP fixture only"
```

## Fixture model

S03 models ACP records as synthetic `Squad/Task` fixtures because M054 already proved `squad` task validation behavior and bounded queries. The ACP semantics are carried in safe synthetic frontmatter/body text and mirrored into adapter metadata fields (`source_record_id`, `source_record_type`, `source_record_lifecycle`).

### Common runtime file shape

Every positive fixture should be a markdown file under the isolated workspace:

```text
Squad/Task/<FixtureName>.md
```

Each positive fixture should include:

```yaml
---
title: <synthetic ACP record title>
squad.Task.taskId: <ACP fixture id>
squad.Task.taskStatus: todo
---

Synthetic ACP fixture only. No legal text, no session logs, no provider payloads.
```

The `squad.Task.taskStatus: todo` value is intentionally chosen because M054 proved it validates against the generated squad task shape.

Adapter metadata for each operation should include:

```text
source_record_id: <fixture id>
source_record_type: <ACP fixture type>
source_record_lifecycle: synthetic-fixture
```

## Positive fixture cases

| Fixture ID | ACP source record type | Runtime path | Runtime status | Purpose |
|---|---|---|---|---|
| `ACP-SRC-DECISION-001` | `decision` | `Squad/Task/ACPDecisionRecord.md` | `todo` | Proves a synthetic ACP decision-like record can be represented as a safe runtime fixture. |
| `ACP-SRC-EVIDENCE-001` | `evidence_anchor` | `Squad/Task/ACPEvidenceAnchorRecord.md` | `todo` | Proves a synthetic evidence-anchor-shaped record can flow through sync/list/query diagnostics without using real proof payloads. |
| `ACP-SRC-PROOF-GATE-001` | `proof_gate` | `Squad/Task/ACPProofGateRecord.md` | `todo` | Proves a synthetic proof-gate-shaped record can be validated as fixture structure while remaining non-authoritative. |
| `ACP-SRC-DIAGNOSTIC-001` | `diagnostic_record` | `Squad/Task/ACPDiagnosticRecord.md` | `todo` | Proves diagnostic-record-shaped metadata can be carried through ACP-facing adapter fields. |

Positive fixtures are expected to support:

```text
workspace_init: pass
workspace_sync: pass
class_inventory: pass
bounded_query graph_inventory: pass
bounded_query_json negative_empty: pass
validation_diagnostic positive: pass
reject_denied nuke: rejected
```

## Negative fixture cases

| Fixture ID | ACP source record type | Runtime path | Negative trigger | Expected adapter classification | Purpose |
|---|---|---|---|---|---|
| `ACP-SRC-BLOCKED-FINDING-NEG-001` | `blocked_finding` | `Squad/Task/ACPBlockedFindingInvalid.md` | `squad.Task.taskStatus: impossible` | `diagnostic-fail` | Proves concrete SHACL violation is surfaced as diagnostic evidence, not hidden. |
| `ACP-SRC-QUERY-NEG-001` | `diagnostic_record` | metadata-only | unknown query id | `rejected` or adapter-level query rejection | Proves bounded query policy rejects unapproved query ids. |
| `ACP-SRC-DENIED-NUKE-001` | `diagnostic_record` | metadata-only | denied `nuke` command | `rejected` | Proves denied destructive surface is not executed. |

The negative validation fixture is useful only as runtime diagnostic evidence. It must not be described as ACP requirement validation.

## Command matrix

All runtime operations must go through `scripts/acp_git_lex_backend.py` or its Python API. Do not call `git-lex` directly from S03 except through the S02/M054 adapter chain.

| Step | ACP adapter operation | Fixture metadata | Expected classification | Durable evidence |
|---|---|---|---|---|
| 1 | `backend_help` | none | `pass` | one bounded ACP-facing diagnostic row |
| 2 | `workspace_init` | `source_record_type: diagnostic_record` | `pass` | isolated workspace path and binary identity |
| 3 | commit positive synthetic fixtures | local setup step, not adapter diagnostic | git commit exit 0 | report setup note only; no raw payload |
| 4 | `workspace_sync` | `source_record_id: ACP-SRC-DECISION-001` | `pass` | sync diagnostic row |
| 5 | `class_inventory` | `source_record_id: ACP-SRC-DIAGNOSTIC-001` | `pass` | result count and class inventory diagnostic row |
| 6 | `bounded_query` with `graph_inventory` | `source_record_id: ACP-SRC-EVIDENCE-001` | `pass` | graph inventory diagnostic row |
| 7 | `bounded_query_json` with `negative_empty` | `source_record_id: ACP-SRC-DIAGNOSTIC-001` | `pass` | result_count 0 diagnostic row |
| 8 | `validation_diagnostic` positive | positive fixture paths | `pass` | observed validated count diagnostic row |
| 9 | create negative fixture | local setup step, not adapter diagnostic | file exists in isolated workspace | report setup note only |
| 10 | `validation_diagnostic` negative | `ACP-SRC-BLOCKED-FINDING-NEG-001` | `diagnostic-fail` | concrete validation violation diagnostic row |
| 11 | `bounded_query_json` with unknown query id | `ACP-SRC-QUERY-NEG-001` | `rejected` | bounded-query policy diagnostic row |
| 12 | `reject_denied --command nuke` | `ACP-SRC-DENIED-NUKE-001` | `rejected` | denylist diagnostic row with `exit_code` absent/null at wrapper layer |

## Expected diagnostics JSONL shape

S03/T02 should write one ACP-facing JSON object per runtime diagnostic to:

```text
prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl
```

Each row must contain at least:

```text
schema_version: m055.acp_git_lex_backend_diagnostic.v1
backend_level: L1-shadow-diagnostic-projection
backend_name: git-lex
operation
operation_class
classification
wrapper_classification
authority: non-authoritative-diagnostic
can_validate_requirement: false
can_mutate_source_truth: false
source_record_id
source_record_type
source_record_lifecycle
workspace_path
workspace_is_main_repo: false
git_lex_source_commit
binary_sha256
wrapper_schema_version
wrapper_operation_id
cleanup_status
diagnostic_summary
created_at
main_lex_absent_before/main_lex_absent_after
main_squad_absent_before/main_squad_absent_after
main_raw_absent_before/main_raw_absent_after
```

Diagnostics JSONL must not contain:

```text
_stdout_raw
_stderr_raw
raw stdout blobs
raw stderr blobs
real legal text
session logs
provider payloads
vectors
secrets
```

## Runtime setup caveats for T02

S03/T02 should use a throwaway workspace such as:

```text
/tmp/m055-s03-acp-shadow-<random>/repo
```

Required setup rules:

1. Initialize a git repository in the isolated workspace.
2. Configure local git author identity inside the isolated workspace.
3. Run adapter `workspace_init` with `kit: squad`.
4. Create positive ACP-shaped synthetic fixtures under `Squad/Task/`.
5. For commits that trigger git-lex hooks, set:

```text
PATH=/root/vendor-source/git-lex/target/debug:$PATH
```

6. Run all diagnostic operations through `scripts/acp_git_lex_backend.py` or its Python API.
7. Write bounded ACP-facing diagnostics JSONL only after stripping private raw fields.
8. Remove the throwaway workspace in T03, not before T02 evidence is recorded.
9. Verify `/root/law-nexus/.lex`, `/root/law-nexus/Squad`, and `/root/law-nexus/Raw` remain absent before and after.

## Pass and failure interpretation

S03 passes only if:

```text
positive runtime operations classify as pass
negative validation classifies as diagnostic-fail with concrete validation violation
unknown query id or denied command classifies as rejected/blocked without broad command execution
diagnostics are bounded ACP-facing records
main .lex/Squad/Raw remain absent
workspace cleanup is recorded in T03
```

S03 should classify, not hide, unexpected failures:

```text
adapter-fail: wrapper/setup/parse/safety failure
blocked: precondition or workspace policy failure
rejected: denied unsupported operation
not-run: explicitly skipped planned operation
```

Any failure is still useful adoption evidence, but it must reduce readiness rather than be reframed as success.

## S04 handoff expectation

S03 should hand S04 a runtime matrix with:

```text
fixture IDs
source record types
operation classifications
diagnostic row count
workspace path
cleanup status
binary identity
no-main-state proof
known setup caveats
remaining blocked surfaces
```

S04 should use that evidence to decide remaining gates for stronger adoption beyond L1. S03 evidence must not be used to validate R035/R037/R038 or approve production/main `.lex` adoption.

## T01 disposition

```text
S03/T01 disposition: acp-shaped-fixture-matrix-designed
fixture model: specified
positive cases: specified
negative cases: specified
command matrix: specified
diagnostics JSONL contract: specified
no-real-payload statement: specified
T02 readiness: ready to run isolated ACP-shaped shadow backend matrix
```

## T02 runtime execution

S03/T02 executed the ACP-shaped shadow backend matrix through the S02 adapter.

Runtime workspace:

```text
base_tmp: /tmp/m055-s03-acp-shadow-wx5bp894
workspace: /tmp/m055-s03-acp-shadow-wx5bp894/repo
```

Tracked diagnostics:

```text
prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl
```

Setup results:

| Setup step | Result |
|---|---|
| `git init` in isolated workspace | exit 0 |
| local git author config | exit 0 |
| adapter `workspace_init` with `kit: squad` | `pass` |
| positive fixture `git add` | exit 0 |
| positive fixture `git commit` | exit 0 |
| hook setup caveat | commit environment used `PATH=/root/vendor-source/git-lex/target/debug:$PATH` |
| hook validation | `Validated 5 files ... all pass` |

Positive synthetic fixtures created in the isolated workspace:

| Fixture ID | Source record type | Runtime path |
|---|---|---|
| `ACP-SRC-DECISION-001` | `decision` | `Squad/Task/ACPDecisionRecord.md` |
| `ACP-SRC-EVIDENCE-001` | `evidence_anchor` | `Squad/Task/ACPEvidenceAnchorRecord.md` |
| `ACP-SRC-PROOF-GATE-001` | `proof_gate` | `Squad/Task/ACPProofGateRecord.md` |
| `ACP-SRC-DIAGNOSTIC-001` | `diagnostic_record` | `Squad/Task/ACPDiagnosticRecord.md` |

Negative synthetic fixture created in the isolated workspace:

| Fixture ID | Source record type | Runtime path | Negative trigger |
|---|---|---|---|
| `ACP-SRC-BLOCKED-FINDING-NEG-001` | `blocked_finding` | `Squad/Task/ACPBlockedFindingInvalid.md` | `squad.Task.taskStatus: impossible` |

### Runtime diagnostics matrix

| # | ACP operation | Source record id | Source record type | Classification | Notes |
|---:|---|---|---|---|---|
| 1 | `backend_help` | `ACP-SRC-BACKEND-HELP-001` | `diagnostic_record` | `pass` | Read-only backend identity/help diagnostic. |
| 2 | `workspace_init` | `ACP-SRC-WORKSPACE-INIT-001` | `diagnostic_record` | `pass` | Initialized isolated `squad` workspace. |
| 3 | `workspace_sync` | `ACP-SRC-DECISION-001` | `decision` | `pass` | Synced committed positive ACP-shaped fixtures. |
| 4 | `class_inventory` | `ACP-SRC-DIAGNOSTIC-001` | `diagnostic_record` | `pass` | Shape/class discovery via `list_json`. |
| 5 | `bounded_query` | `ACP-SRC-EVIDENCE-001` | `evidence_anchor` | `pass` | `graph_inventory` bounded query. |
| 6 | `bounded_query_json` | `ACP-SRC-DIAGNOSTIC-001` | `diagnostic_record` | `pass` | `negative_empty` returned `result_count: 0`. |
| 7 | `validation_diagnostic` | `ACP-SRC-PROOF-GATE-001` | `proof_gate` | `pass` | Positive validation observed `Validated 5 files`. |
| 8 | `validation_diagnostic` | `ACP-SRC-BLOCKED-FINDING-NEG-001` | `blocked_finding` | `diagnostic-fail` | Concrete invalid enum validation failure surfaced as diagnostic evidence. |
| 9 | `bounded_query_json` | `ACP-SRC-QUERY-NEG-001` | `diagnostic_record` | `rejected` | Unknown query id rejected by bounded query policy. |
| 10 | `reject_denied` | `ACP-SRC-DENIED-NUKE-001` | `diagnostic_record` | `rejected` | Denied `nuke` command rejected without execution. |

Classification summary:

```text
pass: 7
diagnostic-fail: 1
rejected: 2
row_count: 10
```

### Diagnostics JSONL validation

Observed JSONL contract validation:

```text
rows: 10
operations: backend_help, workspace_init, workspace_sync, class_inventory, bounded_query, bounded_query_json, validation_diagnostic, validation_diagnostic, bounded_query_json, reject_denied
classifications: {"pass": 7, "diagnostic-fail": 1, "rejected": 2}
private raw fields: absent
schema_version: m055.acp_git_lex_backend_diagnostic.v1
backend_level: L1-shadow-diagnostic-projection
authority: non-authoritative-diagnostic
can_validate_requirement: false
can_mutate_source_truth: false
main .lex/Squad/Raw safety fields: true before and after
workspace_is_main_repo: false
```

### T02 verification results

Fresh T02 verification after writing diagnostics:

```text
uv run pytest tests/test_acp_git_lex_backend.py tests/test_git_lex_diagnostic_adapter.py: 14 passed
JSONL validation script: pass, 10 rows
main .lex: absent
main Squad: absent
main Raw: absent
git diff --check: pass
```

### T02 disposition

```text
S03/T02 disposition: acp-shaped-shadow-runtime-matrix-written
runtime matrix: executed through S02 adapter
tracked diagnostics: prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl
row count: 10
classification summary: pass=7, diagnostic-fail=1, rejected=2
positive ACP-shaped fixtures: committed in isolated workspace
negative ACP-shaped fixture: concrete diagnostic failure observed
unknown query id: rejected
nuke denylist: rejected without execution
main repo residue: none
T03 readiness: ready for cleanup proof and final S03 synthesis
```

## T03 cleanup proof and final synthesis

S03/T03 finalized the runtime evidence and removed the isolated runtime workspace.

Cleanup proof:

```text
removed: /tmp/m055-s03-acp-shadow-wx5bp894
workspace base exists after cleanup: false
workspace repo exists after cleanup: false
tracked diagnostics retained: prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl
main .lex: absent
main Squad: absent
main Raw: absent
```

Final runtime evidence retained in the repository:

```text
prd/architecture/acp/M055-S03-ACP-SHAPED-SHADOW-BACKEND-RUNTIME.md
prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl
```

Final classification:

```text
S03 final disposition: acp-shaped-shadow-runtime-proof-passed
backend level proven: L1-shadow-diagnostic-projection
adapter path: S02 adapter over M054 wrapper
fixture class: synthetic ACP-shaped Squad/Task carrier fixtures
runtime workspace: isolated /tmp workspace, cleaned after proof
tracked diagnostics: 10 bounded ACP-facing JSONL records
classification summary: pass=7, diagnostic-fail=1, rejected=2
main repo residue: none
production/adoption status: unchanged no adoption
```

What S03 proves:

```text
The S02 internal adapter can run the L1 git-lex shadow diagnostic/projection matrix over ACP-shaped synthetic records in an isolated workspace, emit bounded non-authoritative ACP-facing diagnostics, surface a concrete validation failure as diagnostic evidence, reject denied/unbounded surfaces, and leave no main .lex/Squad/Raw residue.
```

What S03 does not prove:

```text
ACP source truth migration
main repository .lex adoption
production runtime readiness
release/plugin-bundled binary trust
real legal payload ingestion
Russian legal evidence correctness
FalkorDB runtime behavior
Garant ODT parser completeness
R035/R037/R038 validation
JSON-LD runtime support
broad RDF-star/SPARQL-star parity
server/viz/listen suitability
save/create/raw/join/kit-update/nuke suitability
```

Known setup caveats:

1. Runtime fixture commits that trigger git-lex hooks need `PATH=/root/vendor-source/git-lex/target/debug:$PATH`.
2. Use `uv run python`, not bare `python`, for local orchestration in this project environment.
3. The runtime-compatible carrier remains `squad` / `Squad/Task`; ACP semantics are represented by synthetic metadata and adapter fields, not by a new git-lex ACP kit.
4. Diagnostics are ACP-facing normalized records; raw M054 wrapper records and private stdout/stderr are not durable proof output.

## S04 handoff

S04 should use S03 as runtime evidence for L1 shadow diagnostic/projection readiness only.

Inputs available to S04:

```text
fixture IDs: ACP-SRC-DECISION-001, ACP-SRC-EVIDENCE-001, ACP-SRC-PROOF-GATE-001, ACP-SRC-DIAGNOSTIC-001, ACP-SRC-BLOCKED-FINDING-NEG-001, ACP-SRC-QUERY-NEG-001, ACP-SRC-DENIED-NUKE-001
operation classifications: pass=7, diagnostic-fail=1, rejected=2
diagnostic row count: 10
workspace path: /tmp/m055-s03-acp-shadow-wx5bp894/repo
cleanup status: clean
binary identity: D077 pinned source-built git-lex binary
no-main-state proof: .lex/Squad/Raw absent in main repo
tracked evidence: prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl
```

S04 should classify remaining adoption gates for:

```text
L1 continuation
L2 operational diagnostic backend candidacy
main .lex rehearsal
source truth migration
production provenance
release/plugin-bundled binary trust
raw/session payload policy
server/viz/listen surfaces
denied mutating surfaces
real legal evidence and R035/R037/R038 boundaries
```

S04 must not treat S03 evidence as proof of ACP source truth, requirement validation, production readiness, main `.lex` safety, or legal evidence correctness.

## T03 disposition

```text
S03/T03 disposition: runtime-evidence-finalized
cleanup status: clean
runtime diagnostics retained: yes
JSONL rows: 10
classification summary: pass=7, diagnostic-fail=1, rejected=2
main repo residue: none
final classification: acp-shaped-shadow-runtime-proof-passed
S04 readiness: ready for backend adoption gate matrix
```
