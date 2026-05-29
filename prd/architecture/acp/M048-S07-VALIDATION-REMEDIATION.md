# M048 S07 Validation Remediation

## Verdict

M048 validation round 1 should treat the S04-S06 ACP/git-lex evidence as **bounded remediation for ACP governance mechanics**, not as full runtime git-lex adoption and not as validation of law-nexus product, legal, parser, FalkorDB, or graph-vector requirements.

The accepted validation interpretation is:

```text
M048 reconciles requirement coverage boundaries; runtime git-lex adoption remains blocked/deferred; deterministic ACP mechanics and guardrails are evidenced; future law-nexus binding remains future work.
```

This report is a cold-reader remediation artifact. It reconciles `R035`, `R037`, `R038`, `R043`, `R046`, `R047`, and `R048` coverage language against the S04 isolated proof, S05 workflow report, S05 integration decision, and S06 final integration verification. It does not update requirement statuses, introduce runtime proof, initialize git-lex, create `.lex`, or claim that any derived projection is authoritative.

## Remediation Scope

This remediation covers validation-language precision only:

- distinguish `blocked` runtime git-lex diagnostics from failed ACP deterministic mechanics;
- preserve non-validation of `R035`, `R037`, and `R038`;
- explain bounded `R043` coverage from isolated deterministic ACP mechanics;
- preserve `R046` source/projection non-authority;
- preserve `R047` main-repository mutation guard expectations;
- preserve `R048` reusable ACP core versus law-nexus profile separation;
- record future law-nexus architecture binding as future work.

Inputs consumed:

- `prd/architecture/acp/M048-S04-GIT-LEX-ISOLATED-PROOF.md`
- `prd/architecture/acp/M048-S05-GIT-LEX-WORKFLOW-REPORT.md`
- `prd/architecture/acp/M048-S05-GIT-LEX-INTEGRATION-DECISION.md`
- `prd/architecture/acp/M048-S06-FINAL-INTEGRATION-VERIFICATION.md`

Out of scope:

- requirement status changes;
- full runtime git-lex adoption;
- cloning, installing, downloading, building, or initializing git-lex;
- `.lex` state creation in the main `law-nexus` checkout;
- validation of legal correctness, parser completeness, FalkorDB ingestion, graph-vector retrieval quality, generated-Cypher safety, or production readiness.

## Requirement Coverage Matrix

| Requirement | Validation-round interpretation | Covered by S04-S06? | Remediation boundary |
| --- | --- | --- | --- |
| `R035` | Ontology architecture research must become bounded evidence before product-scale ontology, graph-vector, or pilot claims are promoted. | No. | M048 may cite source/projection/proof-boundary guardrails, but it must not claim `R035` validation, ontology correctness, graph-vector quality, or pilot readiness. |
| `R037` | FalkorDB ingestion needs verified CSV loading path, counts, idempotency, source shape, cleanup, and operational constraints before larger claims depend on graph data. | No. | M048 does not load FalkorDB data and must not use ACP/git-lex diagnostics as ingestion proof. |
| `R038` | Proof-heavy milestones need independent review of test substance and result artifacts. | Not newly validated by this report. | S07 records validation-language guardrails; any independent review gate remains a separate validation/review activity, not a claim created by S04-S06. |
| `R043` | git-lex must be checked for ACP mechanics in an isolated workspace outside the main repo. | Bounded partial coverage. | S04/S05 cover deterministic typed records, validation, projection/recovery, lifecycle/proof-gate/profile-boundary mechanics and mutation guards. Runtime git-lex acquisition/adoption remains blocked/deferred. |
| `R046` | Source truth and derived projections must remain separate; projections cannot become requirement-validation proof by themselves. | Yes, as a guardrail. | S04-S06 repeatedly assert non-authoritative projection status. Validation should cite this as a boundary, not as product/runtime proof. |
| `R047` | Do not mutate main repo via git-lex or run blind `git lex init` without isolated proof and explicit adoption decision. | Yes, as a mutation guard. | S04-S06 preserve no-main-`.lex` expectations and defer runtime adoption. This is mutation-safety evidence only. |
| `R048` | Keep reusable ACP core separate from law-nexus profile/adapter constraints. | Yes, as an architecture boundary. | S04-S06 keep Russian legal, FalkorDB, parser, LLM authority, and requirement-specific obligations in the law-nexus profile layer. Full law-nexus binding remains future work. |

## R035/R037/R038 Non-Goal Reconciliation

`R035`, `R037`, and `R038` must remain explicit non-goals for M048 validation round 1.

- `R035` is not validated because S04-S06 do not prove ontology architecture correctness, Akoma Ntoso/FRBR/LKIF/RusLegalCore/BFO/GOST/OWL/Common Logic mappings, graph-vector retrieval quality, or pilot-scale behavior. S04-S06 only help enforce that such claims require authoritative evidence before promotion.
- `R037` is not validated because S04-S06 do not perform FalkorDB CSV loading, count reconciliation, idempotent graph loading at meaningful scale, Docker/client-loader policy validation, cleanup, or operational recovery proof.
- `R038` is not newly validated by this report because S07/T01 writes a remediation artifact. It names the independent-review expectation but does not itself replace a review gate or prove test substance by independent inspection.

Validation language should say: **M048 preserves the proof boundary for `R035`, `R037`, and `R038`; it does not validate them.**

## R043 Coverage and Runtime Caveat

`R043` receives bounded partial coverage from S04-S06:

- S04 proves deterministic fixture mechanics in an isolated proof harness: typed source records, validation, temporary projection/recovery, lifecycle/proof-gate checks, profile-boundary checks, blocked-action visibility, and main-repository mutation guard.
- S05 promotes those mechanics into a workflow diagnostic contract and an adopted integration decision: `defer_runtime_adoption_keep_deterministic_acp_mechanics_only`.
- S06 consolidates the final interpretation: ACP foundation verified, runtime git-lex adoption deferred, deterministic mechanics reusable, law-nexus binding future.

The runtime caveat is mandatory: `blocked` means the local `git lex` / `git-lex` runtime surface was unavailable and was not acquired by the harness. It does not mean deterministic ACP mechanics failed when `fatal_failures=[]`, deterministic checks pass, and the mutation guard is safe. It also does not mean runtime git-lex is installed, adopted, safe to initialize, or safe to mutate the main repository.

## S04/S05 Metadata Caveat Resolution

The S04/S05 metadata caveat is resolved by treating S04/S05 status fields as two-layer evidence:

1. **Runtime layer:** `blocked` or `deferred` for git-lex executable acquisition/adoption when probes fail or acquisition is disallowed.
2. **Deterministic ACP layer:** `pass` for source-record validation, isolated projection/recovery, lifecycle/proof-gate/profile-boundary checks, and main-repository mutation guard when the harness reports no fatal failures.

For validation round 1, acceptable wording is:

```text
S04/S05 are blocked for runtime git-lex adoption but pass bounded deterministic ACP mechanics and mutation-safety checks.
```

Unacceptable wording is:

```text
S04/S05 failed M048.
S04/S05 prove full git-lex runtime adoption.
S04/S05 validate R035/R037/R038.
S04/S05 projections are source truth.
```

## Source/Projection and Mutation Boundary

Authoritative evidence remains in tracked source records, accepted requirements/decisions, source code, tests, and durable proof summaries. Derived outputs remain non-authoritative diagnostics:

- ACP recovery views;
- ACP architecture projections;
- RDF/Turtle/SHACL/SPARQL outputs;
- JSONL registry exports;
- dashboards and project-state summaries;
- temporary git-lex-derived views or future `.lex` projections.

Derived projections cannot override source records, validate requirements by themselves, prove legal/parser/FalkorDB/runtime behavior, or turn proof-gate definitions into proof-gate satisfaction.

The mutation boundary remains hard:

- do not run `git lex init` in the main `law-nexus` checkout;
- do not create or mutate main-repository `.lex` state;
- do not clone, install, download, or durably build git-lex from M048 S04-S07 harnesses;
- require a separate explicit adoption decision before any runtime git-lex repository-state mutation.

## Future Law-Nexus Binding Handoff

Future law-nexus architecture binding is explicitly future work. A future binding milestone should start with these expectations:

1. Use M048 as ACP governance foundation evidence, not as product/runtime/legal proof.
2. Bind law-nexus architecture only from authoritative source records, accepted decisions, requirements, source code, tests, and durable proof summaries.
3. Keep projections non-authoritative and derived even when fresh.
4. Keep runtime git-lex adoption behind a new proof gate covering executable provenance, acquisition policy, build/install behavior, representative operations, `.lex` creation policy, rollback, cleanup, and source/projection authority under real runtime use.
5. Keep Russian legal evidence, parser completeness, FalkorDB behavior, graph-vector retrieval, LLM authority, and `R035`/`R037`/`R038` proof obligations in the law-nexus profile/adapter layer.
6. Treat any future projection claim that a requirement is validated as a hypothesis until an authoritative proof anchor confirms it.

## Validation Round 1 Evidence

Validation round 1 should cite these evidence commands and artifacts:

| Evidence | Purpose | Accepted interpretation |
| --- | --- | --- |
| `uv run python scripts/run-m048-s04-git-lex-proof.py --check` | S04 isolated proof harness | Runtime git-lex may be `blocked`; deterministic ACP mechanics and mutation guard must pass with no fatal failures. |
| `uv run python scripts/run-m048-s05-git-lex-workflows.py --check` | S05 workflow diagnostic contract | Runtime adoption remains deferred; workflow statuses must keep deterministic mechanics, source/projection boundary, and mutation guard explicit. |
| `test ! -e .lex` | Main-repository mutation guard | Main repository must not contain git-lex state. |
| `prd/architecture/acp/M048-S04-GIT-LEX-ISOLATED-PROOF.md` | Human-readable S04 proof boundary | Cite for blocked-vs-passed interpretation and non-validation of `R035`/`R037`/`R038`. |
| `prd/architecture/acp/M048-S05-GIT-LEX-WORKFLOW-REPORT.md` | Human-readable S05 workflow boundary | Cite for allowed/blocked actions, source/projection separation, mutation guard, and requirement boundary. |
| `prd/architecture/acp/M048-S05-GIT-LEX-INTEGRATION-DECISION.md` | Adopted integration decision | Cite `defer_runtime_adoption_keep_deterministic_acp_mechanics_only`; do not reinterpret as full adoption. |
| `prd/architecture/acp/M048-S06-FINAL-INTEGRATION-VERIFICATION.md` | Final integration closeout | Cite future law-nexus binding handoff and final blocked/deferred runtime semantics. |
| `prd/architecture/acp/M048-S07-VALIDATION-REMEDIATION.md` | This remediation artifact | Cite for cold-reader requirement coverage reconciliation and validation-language guardrails. |

## Failure Modes

| Dependency | Failure path | Handling / validation interpretation |
| --- | --- | --- |
| Tracked input reports | Missing, unreadable, stale, or internally contradictory S04/S05/S06 report | Validation should fail or request remediation. Do not infer coverage from memory or transient logs. |
| Requirement coverage language | Report or validator starts saying `R035`, `R037`, or `R038` are validated by M048 | Treat as audit-language drift. Correct the wording and require authoritative requirement-specific proof before validation. |
| Runtime git-lex probes | `git lex --help` or `git-lex --help` missing, non-zero, malformed, or timed out | Keep runtime adoption `blocked`/`deferred`; do not install, clone, download, initialize, or claim adoption. |
| Deterministic ACP checks | S04/S05 fatal failures, failed typed-record validation, failed projection/recovery, failed lifecycle/profile checks | Treat as ACP mechanics failure, not runtime deferral. Fix the failing deterministic surface before closeout. |
| Main repository mutation guard | `.lex` exists before or after verification, or a workflow attempts `git lex init` | Fail closed. Investigate repository state and do not continue as if M048 validation passed. |
| Source/projection boundary | Derived projection is cited as source truth or requirement-validation proof | Reject the claim. Repair the source/projection pipeline or add authoritative source proof. |
| Future binding scope | Future law-nexus binding is described as already complete in M048 | Reject the claim. Binding remains future work with a separate proof gate. |

Network acquisition is not a dependency for S07; it remains a blocked action inherited from S04-S06.

## Load Profile

S07/T01 has no production runtime load dimension. It creates one static Markdown remediation artifact and does not add a server, API endpoint, queue, database pool, background worker, browser flow, telemetry stream, crawler, or user-facing runtime path.

At 10x the expected validation-reading load, the first constrained resource is human/agent review clarity, not compute. The protection is explicit sectioning, requirement-ID repetition, evidence-command enumeration, and fail-closed language for source/projection and mutation boundaries. No rate limiting, pagination, pool sizing, caching, autoscaling, or runtime backpressure is required for this artifact.

## Negative Tests

S07/T01 is protected by document-level verification and by existing upstream negative tests from S04/S05. Validation should reject this report or future edits if any of these negative cases occur:

- the report omits `R035`, `R037`, `R038`, `R043`, `R046`, `R047`, or `R048`;
- the report claims `R035`, `R037`, or `R038` are validated by S04-S06;
- the report claims full runtime git-lex adoption;
- the report treats `blocked` runtime diagnostics as deterministic ACP failure when fatal failures are absent;
- the report treats derived projections as source truth;
- the report permits main-repository `.lex` mutation or blind `git lex init`;
- the report presents the future law-nexus binding milestone as already delivered rather than explicitly future work.

Existing executable negative coverage remains upstream:

- `tests/test_m048_s04_git_lex_isolated_proof.py` covers absent git-lex probes, fail-closed `.lex` presence, unsafe anchors, proof-gate non-satisfaction, derived projection non-authority, and law-nexus proof non-claims.
- `tests/test_m048_s04_proof_report.py` protects S04 blocked-runtime, mutation-guard, non-authoritative projection, and requirement non-validation language.
- `tests/test_m048_s05_git_lex_workflows.py` covers absent/successful git-lex probes without full adoption, `.lex` fail-closed behavior, source/projection boundary, and requirement-boundary enforcement.
- `tests/test_m048_s05_workflow_report.py` protects S05 report sections, blocked actions, non-claims, mutation guard, requirement boundary, and S06 handoff.
- `tests/test_m048_s05_integration_decision.py` protects the deferred-runtime adoption decision and rejects full-adoption, projection-authority, and requirement-validation drift.

S07 follow-up executable guardrails may add a report-level pytest that asserts these required phrases and forbidden overclaims directly against this file. This T01 artifact intentionally does not invent runtime stubs or mock runtime git-lex behavior.

## Observability Impact

This report is the durable human-readable diagnostic surface for validation round 1. It helps future validators and agents distinguish:

- blocked/deferred runtime git-lex adoption from deterministic ACP mechanics failures;
- source truth from derived projections;
- mutation-safety evidence from runtime adoption evidence;
- reusable ACP core boundaries from law-nexus profile obligations;
- M048 foundation evidence from future law-nexus architecture binding work.

No runtime telemetry is introduced.

## Closeout Criteria

S07/T01 is complete when:

1. this report exists at `prd/architecture/acp/M048-S07-VALIDATION-REMEDIATION.md`;
2. the report is non-empty and self-contained for a cold reader;
3. it names `R035`, `R037`, `R038`, `R043`, `R046`, `R047`, and `R048`;
4. it preserves non-validation of `R035`, `R037`, and `R038`;
5. it explains bounded `R043` coverage and the blocked/deferred runtime git-lex caveat;
6. it preserves `R046` source/projection non-authority;
7. it preserves `R047` no-main-`.lex` mutation guard;
8. it preserves `R048` reusable ACP core versus law-nexus profile separation;
9. future law-nexus binding is explicitly future work;
10. validation evidence commands are listed for round 1;
11. failure modes, load profile, negative tests, and observability impact are explicit.
