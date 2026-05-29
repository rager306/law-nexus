# M048 S05 git-lex Integration Decision

## Status

Adopted for `M048-q4x62e / S05`.

This is an evidence-backed **deferred runtime adoption** decision with **partial ACP-only continuation of deterministic mechanics**.

## Decision

Do **not** adopt git-lex as an ACP runtime dependency for the main `law-nexus` repository in S05.

Adopt the S05 workflow diagnostics as the current integration boundary:

- **Full adoption:** rejected for S05.
- **Partial adoption:** accepted only for deterministic ACP mechanics already proven by S04 and surfaced by S05 workflow diagnostics.
- **Deferred adoption:** accepted for runtime git-lex acquisition, build, executable invocation, and main-repository `.lex` state.

The approved S05 position is:

```text
defer_runtime_adoption_keep_deterministic_acp_mechanics_only
```

If a future environment makes `git lex --help` or `git-lex --help` succeed, that still permits only:

```text
partial_adoption_requires_separate_runtime_git_lex_proof_before_full_adoption
```

It does not permit full ACP git-lex runtime adoption without a later proof-gated decision.

## What is adopted

S05 adopts these bounded mechanics and artifacts:

1. The executable diagnostic contract from:

   ```bash
   uv run python scripts/run-m048-s05-git-lex-workflows.py --check
   ```

2. The human-readable workflow boundary in:

   - `prd/architecture/acp/M048-S05-GIT-LEX-WORKFLOW-REPORT.md`

3. The S04 deterministic ACP mechanics as reusable design evidence only:

   - typed source-record validation;
   - deterministic extraction/projection/query recovery;
   - lifecycle, proof-gate, blocked-action, and profile-boundary diagnostics;
   - main-repository mutation guard checks.

4. The reusable ACP core / law-nexus profile separation:

   - reusable ACP mechanics may stay generic;
   - Russian legal evidence, parser completeness, FalkorDB, LLM authority, and requirement-specific constraints remain law-nexus profile constraints;
   - profile constraints must not be promoted into reusable ACP core as generic git-lex requirements.

## Evidence considered

S05 considered these tracked inputs:

- `prd/architecture/acp/M048-S04-GIT-LEX-ISOLATED-PROOF.md`
- `prd/architecture/acp/M048-S05-GIT-LEX-WORKFLOW-REPORT.md`
- `scripts/run-m048-s05-git-lex-workflows.py`
- `tests/test_m048_s05_git_lex_workflows.py`
- `tests/test_m048_s05_workflow_report.py`
- `prd/architecture/acp/M045-RDF-PROJECTION-DECISION.md`
- `prd/architecture/acp/M046-RDF-PROJECTION-HARDENING-DECISION.md`

The current S05 workflow diagnostic evidence is:

| Field | Current value |
| --- | --- |
| Overall workflow status | `blocked` |
| Runtime acquisition and adoption | `blocked` |
| Typed source-record validation | `pass` |
| Extraction/projection/query recovery | `pass` |
| Lifecycle/proof-gate/profile boundary | `pass` |
| Main-repo mutation guard | `pass` |
| Fatal failures | none |
| Adoption recommendation | `defer_runtime_adoption_keep_deterministic_acp_mechanics_only` |

The block is runtime-specific: no existing `git lex` subcommand or `git-lex` executable responded to local help probes, and S05 intentionally does not clone, install, download, build, initialize, or persist git-lex state from the main `law-nexus` checkout.

## Accepted interpretation

The accepted interpretation is **deferred runtime adoption with partial ACP-only continuation**.

S04 and S05 prove that deterministic ACP mechanics are useful and inspectable. They do not prove git-lex runtime availability, git-lex repository safety, git-lex acquisition policy, rollback behavior, production readiness, parser completeness, FalkorDB ingestion, graph-vector retrieval, legal correctness, or requirement validation.

Derived projections remain non-authoritative diagnostics. Source truth remains tracked source records and evidence anchors. Proof-gate definitions remain definitions, not proof satisfaction.

## Allowed next actions

Future agents may:

- inspect the S05 JSON contract emitted by `scripts/run-m048-s05-git-lex-workflows.py`;
- use the S05 workflow report and this decision as durable ACP handoff evidence;
- reuse S04 deterministic fixture validators and source-record mechanics for ACP design;
- produce temporary non-authoritative projection diagnostics;
- keep runtime git-lex adoption deferred until a separate acquisition/build/runtime proof exists;
- design a future proof gate that explicitly covers runtime executable availability, acquisition policy, repository mutation policy, rollback, and source/projection authority.

## Blocked actions

S05 blocks these actions:

- claiming full ACP git-lex runtime adoption;
- treating fixture-only evidence as runtime git-lex adoption evidence;
- cloning git-lex from the S05 workflow harness;
- installing, downloading, or durably building git-lex from the S05 workflow harness;
- running `git lex init` in the main `law-nexus` repository;
- creating or mutating main-repository `.lex` state;
- treating a derived projection as source truth;
- allowing a derived projection to override source records;
- using S05 git-lex workflow diagnostics to validate `R035`, `R037`, or `R038`;
- treating proof-gate definitions as proof-gate satisfaction;
- moving law-nexus profile constraints into reusable ACP core as generic requirements.

## Non-claims

This decision does not claim:

- runtime git-lex is available when help probes fail;
- full ACP git-lex adoption;
- main-repository `.lex` state is safe to initialize;
- product readiness;
- parser completeness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- legal correctness;
- `R035` validation;
- `R037` validation;
- `R038` validation;
- RDF, SHACL, SPARQL, Turtle, git-lex, or any projection artifact is architecture source truth;
- reusable ACP core includes law-nexus-specific legal, parser, FalkorDB, or LLM authority constraints.

## Source and projection boundary

| Boundary field | Accepted value |
| --- | --- |
| Source truth | Tracked S04 fixture source records and evidence anchors. |
| Derived projection | Temporary deterministic non-authoritative diagnostic projection. |
| Projection may validate requirements | `false` |
| Projection may override source records | `false` |
| Proof-gate definition equals proof satisfaction | `false` |

This matches M045 and M046: projections can be useful interoperability, recovery, and diagnostic artifacts, but they are not source truth, not product runtime proof, not legal truth, not accepted architecture doctrine, and not requirement-validation evidence.

## Revisit trigger

Revisit this decision only when a future proof-gated milestone provides all of the following evidence:

1. safe git-lex acquisition or a pre-existing approved executable source;
2. successful runtime executable probes and representative git-lex operations;
3. explicit policy for whether, when, and where `.lex` state may be created;
4. rollback and cleanup behavior for repository-state mutation;
5. proof that source/projection separation is preserved under runtime git-lex use;
6. tests that still prevent full-adoption overclaims and requirement-validation leaks;
7. explicit separation between reusable ACP core and law-nexus profile constraints.

Until then, keep runtime adoption deferred and keep main-repository git-lex initialization blocked.

## Closeout verdict

S05 closes with this durable architectural choice:

**Deferred runtime adoption; partial ACP-only continuation of proven deterministic mechanics; no main-repository git-lex initialization; no full-adoption claim; no requirement validation for `R035`, `R037`, or `R038`.**

## Failure Modes

| Dependency | Failure path | Handling/evidence |
| --- | --- | --- |
| Local git-lex executable probes | `git lex --help` or `git-lex --help` missing, non-zero, malformed, or timed out | Runtime adoption stays `blocked` or `deferred`; S05 does not install, clone, download, or claim full adoption. |
| S04 proof report and harness evidence | S04 artifact missing, stale, or inconsistent with S05 diagnostics | This decision remains bounded to tracked S04/S05 evidence and must be revisited rather than broadened silently. |
| S05 workflow JSON contract | Workflow statuses, blocked/deferred reason, adoption recommendation, non-claims, requirement boundary, or mutation guard drift | `tests/test_m048_s05_integration_decision.py` and workflow tests assert the required bounded language and diagnostic references. |
| Main repository filesystem state | `.lex` exists before or after diagnostics, or a workflow tries to create it | Main-repo mutation remains blocked; S05 workflow diagnostics fail closed when `.lex` is present. |
| Human-readable decision drift | Decision text starts claiming full adoption, source-truth projection authority, or `R035`/`R037`/`R038` validation | Bounded doc tests reject full-adoption overclaims, projection authority leaks, and requirement-validation language. |

Network acquisition is deliberately not a dependency of S05. It is a blocked action until a future proof-gated milestone explicitly permits it.

## Load Profile

S05 has no production runtime load dimension. This task adds one static Markdown decision and assertion tests over tracked files; it does not add a server, queue, API endpoint, database pool, background worker, network crawler, telemetry stream, or user-facing runtime path.

At 10x the expected diagnostic size, the first bounded resource would be local file parsing and subprocess probe duration in the existing S04/S05 harnesses. No pool sizing, rate limiting, pagination, caching, autoscaling, or runtime backpressure control is required for this decision document.

Future runtime git-lex adoption would require a separate load and repository-state profile before any operational claim.

## Negative Tests

Negative and boundary coverage for this decision is provided by `tests/test_m048_s05_integration_decision.py`:

- rejects missing required decision sections;
- rejects absence of explicit full/partial/deferred adoption classification;
- rejects full runtime adoption overclaims;
- preserves blocked main-repository `git lex init` and `.lex` mutation language;
- preserves source/projection separation and non-authoritative projection language;
- preserves `R035`, `R037`, and `R038` non-validation;
- preserves reusable ACP core versus law-nexus profile separation;
- requires failure modes, load profile, and negative test sections to remain populated.

The workflow-level negative tests remain in `tests/test_m048_s05_git_lex_workflows.py`, including absent git-lex probes, no full adoption even on successful help probes, fail-closed `.lex` presence, source/projection boundary enforcement, and requirement-boundary enforcement.

## Observability Impact

This decision is the stable human-readable adoption boundary for future agents. It complements the S05 JSON workflow diagnostics by making the integration choice, blocked actions, allowed next actions, non-claims, mutation guard, source/projection boundary, and revisit trigger explicit in a tracked artifact.
