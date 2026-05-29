# M048 S04 git-lex Isolated Proof Report

**Status:** S04 bounded proof report for `M048-q4x62e / S04`.

## Verdict

The S04 proof is **partially proven**.

The deterministic ACP fixture mechanics are proven inside the bounded harness: typed source records, validation, deterministic extraction/projection, query/recovery, lifecycle/proof-gate semantics, profile-boundary separation, blocked-action visibility, and main-repo mutation guards all passed.

Runtime git-lex mechanics are **blocked**, not proven. The harness did not find an existing `git lex` subcommand or `git-lex` executable, and it intentionally did not clone, install, download, build, or persist any git-lex acquisition artifact from the `law-nexus` checkout. This report therefore supports S05 as evidence for ACP-compatible mechanics and guardrails, not as evidence that git-lex is adopted, installed, runtime-compatible, or safe to initialize in the main repository.

## Proof Scope

This report covers only the isolated proof harness and tracked S04 fixture pack:

- Harness: `scripts/run-m048-s04-git-lex-proof.py`
- Fixture pack: `prd/architecture/acp/fixtures/git-lex-isolated-proof/`
- Source-record model input: `prd/architecture/acp/M048-S02-SOURCE-RECORD-MODEL.md`
- Lifecycle and health input: `prd/architecture/acp/M048-S03-LIFECYCLE-HEALTH-MODEL.md`
- Prior mechanics research: `prd/research/architecture/git-lex-mechanics-for-architecture-control-plane.md`
- Contract tests: `tests/test_m048_s04_git_lex_isolated_fixtures.py` and `tests/test_m048_s04_git_lex_isolated_proof.py`

The proof does not validate product readiness, parser completeness, legal correctness, FalkorDB ingestion, graph-vector retrieval, runtime git-lex adoption, or requirements `R035`, `R037`, or `R038`.

## Harness Result Summary

Command summarized for this report:

```bash
uv run python scripts/run-m048-s04-git-lex-proof.py --check
```

Observed top-level result:

| Field | Value |
| --- | --- |
| Overall status | `blocked` |
| Fatal failures | none |
| Blocked/deferred reason | `git-lex executable unavailable; runtime git-lex mechanics are blocked, deterministic fixture checks still ran` |
| Runtime telemetry introduced | `false` |
| Main-repo mutation checked | `true` |

The `blocked` top-level status is intentional and accurate: deterministic fixture checks passed, but runtime git-lex acquisition/build/use was unavailable and not attempted.

## Acquisition and Build Status

**Status:** `blocked`.

The harness probed both expected local runtime surfaces:

| Probe | Result |
| --- | --- |
| `git lex --help` | failed because `git` has no `lex` subcommand in this environment |
| `git-lex --help` | failed because no `git-lex` executable exists in this environment |

The safe acquisition policy is: **no clone, install, download, durable build, or cache mutation from `law-nexus`**. Because no existing executable was available, S04 does not prove git-lex binary behavior. It proves that the ACP proof path reports the block honestly while still running deterministic source-record checks.

## Typed-Record Coverage

**Status:** `pass`.

The fixture pack contains 11 typed records, one per required reusable ACP or profile-boundary category:

| Record kind | Record id |
| --- | --- |
| `requirement_binding` | `RB-ACP-0001` |
| `architecture_decision` | `AD-ACP-0001` |
| `architecture_prompt_record` | `APR-ACP-0001` |
| `architecture_proposal` | `AP-ACP-0001` |
| `decision_candidate` | `DC-ACP-0001` |
| `proof_gate` | `PG-ACP-0001` |
| `evidence_anchor` | `EA-ACP-0001` |
| `architecture_health_finding` | `AHF-ACP-0001` |
| `derived_projection_reference` | `DPR-ACP-0001` |
| `profile_constraint` | `PC-LN-0001` |
| `blocked_action` | `BA-ACP-0001` |

This coverage is proof of the S04 fixture taxonomy and record relationship mechanics only. It is not product, legal, parser, FalkorDB, or requirement-validation proof.

## Validation Status

**Status:** `pass` for deterministic fixture validation.

The harness validated:

- required taxonomy and record ids;
- unique typed records;
- relationship references between fixture records;
- safety flags that keep product, parser, FalkorDB, legal, and requirement-validation claims false;
- safe repository-relative evidence anchors;
- rejection of unsafe durable proof anchors such as absolute paths, `.gsd/exec/*`, `.lex/*`, provider payloads, raw vectors, and secrets;
- lifecycle and proof-gate consistency.

The validation result must not be read as validation of `R035`, `R037`, or `R038`. Those requirements remain outside this S04 proof boundary.

## Extraction and Projection Status

**Status:** `pass` for deterministic isolated projection.

The harness copied only the tracked fixture pack into a Python temporary workspace and built a deterministic derived projection containing the 11 fixture records. The projection authority status is **non-authoritative**.

This projection is a rebuildable diagnostic and recovery view. It may help S05 inspect source-record mechanics, but it must not serve as source truth, override source records, validate requirements, validate legal/parser/runtime behavior, or justify main-repo adoption state.

## Query and Recovery Status

**Status:** `pass`.

The harness recovered the typed architecture decision and proof-gate relationships from the temporary projection:

- architecture decision: `AD-ACP-0001`;
- proof-gate edges: `BA-ACP-0001`, `DC-ACP-0001`, and `EA-ACP-0001`.

This proves bounded recovery over the deterministic fixture projection. It does not prove SPARQL/Oxigraph/git-lex query runtime behavior, because no git-lex executable was available or invoked.

## Lifecycle and Proof-Gate Status

**Status:** `pass`.

The harness checked lifecycle and proof-gate records for the expected non-overclaiming states:

- prompt/proposal/candidate/decision records expose linked, candidate, or requires-proof state rather than implicit adoption;
- `PG-ACP-0001` remains `pending_evidence` and does not self-satisfy;
- health and blocked-action records preserve blocked status and allowed next actions;
- accepted doctrine and proof satisfaction remain separate concepts.

The proof gate definition is not proof satisfaction. S04 keeps runtime git-lex adoption and product/legal/runtime requirements behind future evidence.

## Profile-Boundary Status

**Status:** `pass`.

The reusable ACP core fixture records stay generic. The law-nexus-specific boundaries are confined to `PC-LN-0001` and cover project-profile restrictions such as Russian legal evidence, FalkorDB, parser completeness, LLM authority, GSD operational quirks, and `R035`/`R037`/`R038` proof boundaries.

S04 therefore supports the reusable-core versus law-nexus-profile split. It does not move law-nexus constraints into the generic ACP core.

## Blocked and Allowed Action Visibility

**Status:** `pass`.

The fixture pack includes an explicit blocked action, `BA-ACP-0001`, for `main-repo-git-lex-state`. The allowed path is continued isolated proof and decision work; the blocked path is initializing or treating `.lex` state in the main repository as adopted before a separate proof and decision exists.

The block is visible as first-class ACP state rather than hidden in transient logs.

## Main-Repo Mutation Guard Result

**Status:** `pass`.

The harness checked the main repository before and after execution:

| Check | Result |
| --- | --- |
| Main `.lex` before harness | absent |
| Main `.lex` after harness | absent |

S04 did not create `.lex` state in the main `law-nexus` repository. This is a guard result, not an adoption claim.

## S05 Integration Decision Inputs

S05 may use this report as the following decision input:

1. **ACP typed-record mechanics are viable enough to continue integration design.** The isolated fixture taxonomy, references, safety flags, and lifecycle/proof-gate model passed deterministic checks.
2. **Derived projections must remain non-authoritative.** S04 proves recovery visibility only through a temporary, rebuildable projection.
3. **Runtime git-lex remains blocked.** No executable was available, and safe acquisition/build was intentionally not attempted.
4. **Main-repo `.lex` adoption remains blocked.** S05 must not infer adoption readiness from S04.
5. **Profile boundaries are required.** law-nexus-specific legal/FalkorDB/parser/LLM/requirement constraints must remain in a profile layer, not in reusable ACP core.
6. **Requirement validation remains out of scope.** S04 provides no validation evidence for `R035`, `R037`, or `R038`.

Recommended S05 decision framing: proceed with ACP integration planning only if it preserves source/projection separation, keeps git-lex runtime adoption behind a future acquisition/build proof gate, and keeps law-nexus proof boundaries profile-owned.

## Failure Modes

External dependencies and failure paths considered by this task:

| Dependency | Failure path | Handling/evidence |
| --- | --- | --- |
| Filesystem fixture reads/writes | missing fixture pack, malformed Markdown frontmatter, duplicate/missing record ids, unsafe evidence paths | Harness and tests fail closed with validation errors; negative tests cover malformed frontmatter and unsafe anchors. |
| Subprocess probes for `git lex` and `git-lex` | executable missing, non-zero probe response, timeout, `OSError` | Harness reports acquisition as `blocked` with structured probe details instead of crashing or attempting installation. |
| Temporary workspace projection | projection generation from copied fixture records could produce source/projection confusion | Projection is marked `non_authoritative`; tests assert derived projection cannot override source records or validate requirements. |
| Main repository mutation guard | pre-existing or newly created `.lex` state | Harness checks before and after execution and fails closed if main-repo `.lex` exists. |

Network acquisition is deliberately not attempted. That path remains blocked by policy rather than retried or hidden.

## Load Profile

No production runtime load profile applies to S04. The task adds a deterministic report and document assertions over a small tracked fixture pack; it does not add a server, queue, API, database pool, telemetry stream, or production background process.

The relevant bounded-resource expectation is that the harness scales with the number of tracked fixture records and uses a temporary workspace. At 10x the current fixture pack, the first saturated resource would likely be local filesystem and YAML/JSON parsing time, not an external service. No pooling, rate limiting, or pagination is required for this proof report.

## Negative Tests

Negative coverage is provided by `tests/test_m048_s04_git_lex_isolated_proof.py` and reinforced by `tests/test_m048_s04_proof_report.py`:

- missing git-lex executable reports structured `blocked` status without crashing;
- main-repo `.lex` state fails closed;
- malformed YAML frontmatter is rejected;
- unsafe durable anchors are rejected, including absolute paths, parent traversal, `.gsd/exec/*`, `.lex/*`, provider payloads, raw vectors, and secrets;
- derived projections and requirement bindings cannot become source truth;
- proof gates do not self-satisfy;
- law-nexus-specific proof claims remain false;
- this report must preserve required sections, non-authoritative projection language, no requirement-validation overclaim, and no main-repo `.lex` adoption claim.

## Observability Impact

This report is the durable inspection surface for S05. It replaces transient command output with explicit phase statuses, blocked/deferred reasons, source/projection boundary status, main-repo mutation guard results, and integration decision inputs. No runtime telemetry is introduced.
