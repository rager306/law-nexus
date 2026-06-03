# M054 S04 Proof Only Adapter Spike Synthesis

## Status

In progress for `M054-63ujns / S04`.

S04 synthesizes the proof-only git-lex diagnostic adapter spike. It does **not** approve production adoption, release/bundled binary adoption, main repository `.lex`, ACP authority transfer, R035/R037/R038 validation, JSON-LD runtime support, broad SPARQL-star support, or real legal evidence claims.

## Guardrails

- ACP remains source of truth.
- The adapter output is non-authoritative diagnostics only.
- Main repository `.lex`, `Squad`, and `Raw` must remain absent.
- Runtime proof was isolated under `/tmp` and synthetic only.
- The proof used D077 pinned local source-built debug binary, not release or plugin-bundled binaries.

## T01: Spike synthesis ledger

### Evidence inputs

| Slice | Artifact | Result consumed by S04 |
|---|---|---|
| S01 | `prd/architecture/acp/M054-S01-PINNED-SOURCE-ADAPTER-CONTRACT.md` | D077 source pin, binary identity, command allowlist/denylist, diagnostic schema, validation gates, query boundaries. |
| S02 | `scripts/git_lex_diagnostic_adapter.py`; `tests/test_git_lex_diagnostic_adapter.py` | Proof-only wrapper implementation and contract tests. |
| S03 | `prd/architecture/acp/M054-S03-ISOLATED-RUNTIME-DIAGNOSTIC-MATRIX.md`; `prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl` | Isolated runtime matrix and cleanup proof. |

### Per-slice outcome

| Slice | Outcome | Key evidence | Boundary |
|---|---|---|---|
| S01 | `contract-ready-for-wrapper` | D077 pin, binary sha256, help surfaces, allowlist/denylist, schema, wrapper gates. | Contract only; no implementation or runtime matrix. |
| S02 | `wrapper-ready-after-fix` | Wrapper script, 7 pytest tests, ruff clean. | Runtime matrix deferred to S03; wrapper is proof-only. |
| S03 | `isolated-runtime-matrix-passed` | 7 diagnostics records: sync/list/query/query_json/validate+/validate-/denylist. | Isolated synthetic workspace only; cleanup completed. |

### Defects found and fixed

| Defect | Where found | Resolution | Remaining lesson |
|---|---|---|---|
| `list_json` / `query_json` parsed truncated `stdout_digest`. | S03/T01 prep. | Reopened S02; wrapper now parses private full stdout internally and strips private fields before output. Regression test added. | Structured parsers must parse before digest truncation. |
| Workspace commit hook could not find `git-lex` on PATH. | S03/T02 first matrix. | Corrected matrix set `PATH=/root/vendor-source/git-lex/target/debug:$PATH` for isolated workspace commit. | Runtime fixtures that trigger git-lex hooks must set PATH explicitly. |

### Runtime matrix summary

Tracked diagnostics:

```text
prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl
```

| Operation | Classification | Interpretation |
|---|---|---|
| `sync` | `pass` | The wrapper can run pinned git-lex sync in the isolated workspace after committed synthetic fixture. |
| `list_json` | `pass` | The wrapper can run class discovery and parse full JSON internally; result count 12. |
| `query graph_inventory` | `pass` | The wrapper can run bounded human query diagnostics. |
| `query_json negative_empty` | `pass` | The wrapper can run bounded JSON query diagnostics and parse result count 0. |
| `validate_wrapped` positive | `pass` | Valid synthetic task counted and passed; observed count 2. |
| `validate_wrapped` negative | `git-lex-fail` | Invalid enum generated a concrete SHACL violation; observed count 3. |
| `reject_denied nuke` | `rejected` | Denied destructive command was not executed. |

### What M054 proved

M054 proved this narrow claim:

```text
A tiny proof-only wrapper can safely execute the minimal git-lex diagnostic subset in an isolated synthetic workspace, emit bounded non-authoritative JSON diagnostics, reject denied commands, and keep the main checkout free of .lex/Squad/Raw residue.
```

### What M054 did not prove

```text
production readiness
release or plugin-bundled binary trust
main .lex adoption
ACP source truth transfer
R035/R037/R038 validation
Russian legal evidence correctness
FalkorDB runtime behavior
Garant ODT parser completeness
JSON-LD runtime support
broad RDF-star/SPARQL-star parity
real Claude/session logs safety
real legal payload ingestion
```

### T01 final classification

```text
M054/T01 synthesis classification: useful-proof-only-adapter-spike
adapter wrapper usefulness: proven for isolated diagnostics
implementation readiness: suitable for a future narrow internal diagnostic adapter milestone
adoption readiness: not proven
production readiness: blocked
```

## T02: Durable guidance update

S04 updated project-local git-lex guidance with the M054 result.

Updated files:

| File | Delta |
|---|---|
| `.agents/skills/git-lex/references/runtime-adoption-gates.md` | Added M054 proof-only diagnostic adapter spike update, proven wrapper surfaces, and reusable wrapper lessons. |
| `.agents/skills/git-lex/references/acp-boundaries.md` | Added M054 proof-only adapter boundary and explicit non-authority limits. |

Durable guidance now records this narrow M054 claim:

```text
A pinned source-built proof-only wrapper can run the minimal git-lex diagnostic subset in an isolated synthetic workspace and emit bounded non-authoritative JSON diagnostics while keeping the main checkout free of .lex/Squad/Raw residue.
```

Durable guidance also preserves the blocked/non-authoritative boundaries:

```text
main .lex adoption: blocked
production runtime adoption: blocked
release or plugin-bundled binary trust: blocked
ACP source truth transfer: blocked
R035/R037/R038 validation: blocked
real legal payload/session log evidence: blocked
```

### T02 conclusion

```text
durable guidance update: complete
M054 proof-only wrapper result recorded: yes
adoption status changed: no
```

## T03: Final recommendation and closeout input

### Final recommendation

```text
M054 final classification: proof-only-adapter-spike-passed
next recommended step if continuing: narrow internal ACP diagnostic adapter implementation milestone
safe stop point: keep wrapper/harness as proof artifact and preserve patterns
production/adoption recommendation: no
```

M054 successfully retires the narrow question from M053:

```text
Can the minimal git-lex diagnostic subset be wrapped and run safely in isolation?
Answer: yes, for proof-only diagnostics with synthetic fixtures and pinned source-built binary.
```

### Recommended follow-up implementation scope

If the user wants to continue from M054, the next milestone should implement a narrow internal adapter module around the proven wrapper behavior, still non-production and still isolated-first.

Allowed follow-up scope:

- preserve D077 pin or explicitly choose a new update/recheck decision;
- keep command policy from S01/S02;
- keep `m054.git_lex_diagnostic.v1` or version it explicitly;
- integrate wrapper records into ACP diagnostic/recovery surfaces only;
- keep output non-authoritative;
- add test fixtures around positive/negative validation and bounded queries;
- keep main `.lex` disabled unless a later human adoption decision changes that.

Disallowed follow-up scope:

- production runtime;
- release/plugin-bundled binary trust;
- main repository `.lex`;
- real legal text ingestion;
- real Claude/session logs;
- `save`, `create`, `raw`, `join`, `kit-update`, `nuke`, server/viz/listen;
- R035/R037/R038 validation claims;
- JSON-LD runtime or broad SPARQL-star claims.

### Final readiness matrix

| Capability | M054 result | Readiness after M054 |
|---|---|---|
| Pinned source/binary identity | Recorded and verified. | Ready for internal proof-only adapter use. |
| Wrapper command policy | Implemented and tested. | Ready for narrow adapter implementation. |
| Structured diagnostics | Implemented and runtime-tested. | Ready as non-authoritative diagnostic records. |
| `sync` | Runtime matrix `pass`. | Proof-only ready. |
| `list_json` | Runtime matrix `pass`, regression fixed. | Proof-only ready. |
| bounded `query` | Runtime matrix `pass`. | Proof-only ready. |
| bounded `query_json` | Runtime matrix `pass`. | Proof-only ready. |
| positive `validate_wrapped` | Runtime matrix `pass`. | Proof-only ready. |
| negative `validate_wrapped` | Runtime matrix `git-lex-fail` with concrete SHACL violation. | Proof-only ready for fail-closed diagnostics. |
| denylist | `nuke` rejected without execution; tests cover policy. | Ready; expand tests if more denied commands are exposed. |
| cleanup/no-main residue | Verified. | Ready as required operational gate. |
| production/release/plugin binaries | Not advanced. | Blocked. |
| ACP authority / requirements | Not advanced. | Blocked as proof source. |

### Known caveats

1. The wrapper is a proof harness, not a production package.
2. Runtime matrix used `squad` synthetic fixtures, not ACP real records or legal documents.
3. Git hooks in isolated repos require PATH to include the pinned binary directory.
4. The wrapper currently stores bounded digests; full raw outputs are intentionally not durable proof anchors.
5. Query support is intentionally bounded to predefined query IDs.
6. The source pin is intentionally stale relative to observed remote HEAD; update requires a separate recheck decision.

### Final non-validation boundary

M054 does not validate:

```text
R035
R037
R038
Russian legal evidence correctness
FalkorDB runtime behavior
Garant ODT parser completeness
ACP source truth
production readiness
release or plugin-bundled binary trust
main .lex adoption
JSON-LD runtime support
broad RDF-star/SPARQL-star parity
```

### T03 conclusion

```text
S04 final disposition: spike-synthesis-complete
M054 final disposition: proof-only-adapter-spike-passed
recommended next milestone: narrow internal ACP diagnostic adapter implementation, still non-production
safe alternative: stop here and retain wrapper/harness as proof artifact
adoption status: unchanged no adoption
```
