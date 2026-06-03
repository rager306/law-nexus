# M054 S03 Isolated Runtime Diagnostic Matrix

## Status

In progress for `M054-63ujns / S03`.

S03 runs the proof-only adapter wrapper against real pinned git-lex commands in an isolated workspace. It does not approve production adoption, release/bundled binaries, main `.lex`, or ACP authority transfer.

## Guardrails

- Use only `scripts/git_lex_diagnostic_adapter.py` for git-lex runtime operations.
- Runtime workspace must be isolated under `/tmp`.
- Main repository `.lex`, `Squad`, and `Raw` must remain absent.
- Fixtures must be synthetic/sanitized; no real legal text, Claude/session logs, provider payloads, or raw evidence.
- Runtime diagnostics are non-authoritative and cannot validate R035/R037/R038.

## T01: Isolated runtime fixture workspace

### Evidence anchor

```text
.gsd/exec/654abe82-10dd-40a2-829e-623cfc7f212d.stdout
```

Earlier superseded prep evidence:

```text
.gsd/exec/920029e9-05c2-4f91-a151-d45e531a6e51.stdout
```

The earlier prep run found a wrapper bug: `list_json` parsed the truncated stdout digest. S02 was reopened, fixed, and reclosed. The authoritative S03/T01 prep evidence is the rerun `654abe82-...`.

### Workspace

```text
workspace: /tmp/m054-s03-runtime-twnrqpjm/repo
git_init_exit: 0
wrapper_init_classification: pass
wrapper_list_json_classification: pass
wrapper_list_json_result_count: 12
```

### Generated shape and class anchors

Shape path:

```text
.lex/ontology/squad/squad-shapes.ttl
```

Generated class folders:

```text
Squad/Brief
Squad/Bug
Squad/Decision
Squad/Discovery
Squad/Freeform
Squad/Message
Squad/Pod
Squad/Proclamation
Squad/Project
Squad/Situation
Squad/Squaddie
Squad/Task
```

`list_json` reported 12 classes and emitted a bounded digest; the wrapper parsed the full raw stdout internally and did not emit private raw fields.

### Task fixture shape plan

Generated template inspected:

```text
/tmp/m054-s03-runtime-twnrqpjm/repo/Squad/Task/__Task.md
```

Relevant frontmatter:

```yaml
squad.Task.assignedTo: # optional, IRI
squad.Task.blockedBy: # optional, IRI
squad.Task.blocks: # optional, IRI
squad.Task.relatedDecision: # optional, IRI
squad.Task.taskId: # optional, str
squad.Task.taskStatus: # required, enum: blocked, cancelled, done, in-progress, todo
```

S03/T02 fixture plan:

| Fixture | Path | Expected validation |
|---|---|---|
| Positive task | `Squad/Task/M054PositiveTask.md` | `taskStatus: todo`; wrapper should classify `pass` if git-lex counts expected file. |
| Negative task | `Squad/Task/M054NegativeTask.md` | `taskStatus: impossible`; wrapper should classify `git-lex-fail` only if raw git-lex emits SHACL violation rather than setup/skip ambiguity. |

### T01 classification

```text
S03/T01 disposition: workspace-prep-ready
init through wrapper: pass
list_json through wrapper: pass
shape anchor found: yes
synthetic fixture plan: ready
main repo residue: none
```

T01 confirms S03 can proceed to the full allowed wrapper matrix in the same isolated workspace.

## T02: Runtime matrix through proof-only wrapper

### Evidence anchors

Superseded first matrix attempt:

```text
.gsd/exec/bcd25651-b17e-4b47-a5af-cdef46e3c632.stdout
```

The first attempt classified the wrapper operations correctly, but the positive fixture `git commit` failed because the git hook could not find `git-lex` on `PATH`. The corrected run below sets `PATH=/root/vendor-source/git-lex/target/debug:$PATH` for the workspace commit.

Authoritative corrected matrix:

```text
.gsd/exec/88de8075-695d-4149-982e-46ab64a5b8c8.stdout
prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl
```

### Corrected commit setup

```text
workspace: /tmp/m054-s03-runtime-twnrqpjm/repo
positive_fixture: Squad/Task/M054PositiveTask.md
commit_exit: 0
commit_message: M054 positive synthetic task fixture
hook_validation: Validated 2 files in 44.9ms — all pass ✓
```

The commit created:

```text
Squad/Task/M054PositiveTask.md
.lex/extract/Squad/Task/M054PositiveTask.md.fm.spo
```

This sidecar exists only in the isolated `/tmp` workspace, not the main repository.

### Matrix results

| Operation | Classification | Expected result | Evidence |
|---|---|---|---|
| `sync` | `pass` | Store sync after committed positive fixture. | Incremental sync over 1 new commit; 12 quads. |
| `list_json` | `pass` | Shape class discovery. | `result_count: 12`. |
| `query graph_inventory` | `pass` | Bounded graph inventory query. | 14 graph results. |
| `query_json negative_empty` | `pass` | Bounded empty JSON query. | `result_count: 0`. |
| `validate_wrapped` positive | `pass` | Positive fixture counted and valid. | `observed_validated_count: 2`. |
| `validate_wrapped` negative | `git-lex-fail` | Negative fixture produces real SHACL violation. | Invalid enum `impossible`; `observed_validated_count: 3`. |
| `reject_denied nuke` | `rejected` | Denied command not executed. | `exit_code: null`; `command denied by M054 policy: nuke`. |

### Diagnostic JSONL contract check

The tracked JSONL contains one record per matrix operation. Each record includes:

```text
schema_version: m054.git_lex_diagnostic.v1
authority: non-authoritative-diagnostic
git_lex_source_commit: eaa4b24d144a78a8b8e4969404d74cf22267df1f
binary_sha256: 40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c
raw_payload_touched: false
main_lex_absent_before/after: true
main_squad_absent_before/after: true
main_raw_absent_before/after: true
workspace_is_main_repo: false
```

The JSONL intentionally contains bounded stdout/stderr digests only. It does not contain private full raw stdout fields, real legal text, session logs, provider payloads, secrets, or production binary claims.

### T02 classification

```text
S03/T02 disposition: runtime-matrix-passed
allowed wrapper matrix: pass
positive validate wrapper: pass
negative validate wrapper: git-lex-fail as expected
nuke denylist: rejected without execution
main repo residue: none
production/adoption status: unchanged no adoption
```

## T03: Final runtime classification and cleanup

### Evidence anchor

```text
.gsd/exec/64fff99c-586e-4209-9d85-c5c6a51849cc.stdout
```

### Cleanup

```text
workspace_removed: /tmp/m054-s03-runtime-twnrqpjm
cleanup_status: clean
```

The tracked JSONL diagnostics remain in the repository:

```text
prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl
```

The tracked diagnostics are bounded, non-authoritative, and safe to keep as proof artifacts. The isolated `.lex`, `Squad`, `.git/lex`, and extraction sidecars were removed with the `/tmp` workspace.

### Final verification

```text
uv run pytest tests/test_git_lex_diagnostic_adapter.py: 7 passed
runtime diagnostics matrix classification: pass
main .lex absent: pass
main Squad absent: pass
main Raw absent: pass
git diff --check: pass
```

### Final S03 classification

```text
S03 final disposition: isolated-runtime-matrix-passed
wrapper usefulness: proven for proof-only diagnostics
allowed operations proven: sync, list_json, query, query_json, validate_wrapped positive, validate_wrapped negative, reject_denied
known setup caveat: workspace commits that trigger git-lex hooks need PATH to include /root/vendor-source/git-lex/target/debug
cleanup status: clean
adoption status: unchanged no adoption
```

### S04 input

S04 should treat S03 as proof that the tiny wrapper can safely run the minimal diagnostic subset in isolation. It should not treat S03 as proof of:

```text
production readiness
main .lex adoption
release or plugin-bundled binary trust
ACP source truth transfer
R035/R037/R038 validation
real legal evidence quality
JSON-LD runtime support
broad SPARQL-star parity
```
