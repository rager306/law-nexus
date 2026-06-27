# Onion Migration Contract

**Milestone:** M076-f3zxm8  
**Status:** [bounded] migration control artifact  
**Decision:** D099  
**Architecture basis:** ADR-0001 onion package structure for `src/law_nexus`

## Purpose

This document controls the long-horizon migration from script-heavy proof flows
to the accepted onion and hexagonal package architecture:

```text
src/law_nexus/
├── domain/          # pure legal and source models
├── ports/           # Protocol contracts
├── application/     # deterministic use cases
├── adapters/        # infrastructure and IO
└── composition.py   # explicit wiring, not a DI framework
```

The goal is not a big-bang rewrite. The goal is a wrapper-first migration where
existing `scripts/*.py` remain stable CLI proof surfaces while reusable logic
moves wave by wave into `src/law_nexus`.

## Current baseline

Current repository shape from M076 inventory:

| Area | Python files | Role today |
|---|---:|---|
| `src/law_nexus` | 21 | Accepted onion package skeleton with first parser adapter and use case |
| `scripts` | 140 | Main proof, fixture, governance, retrieval, graph, and smoke workflows |
| `tests` | 161 | Primary regression and proof surface |

Current architecture gates:

```bash
uv run lint-imports
# Contracts: 4 kept, 0 broken

uv run basedpyright src/
# 0 errors, 0 warnings, 0 notes
```

Current full pytest baseline is not green. The tracked debt baseline is:

```text
28 failed, 1919 passed
```

This is documented in `prd/architecture/test-debt.md`. M076 slices must not
smooth this debt into success. If a slice changes the failure count, it must
update the debt register or close failures with evidence.

## Wrapper-first rule

For every migrated script flow:

1. Keep the original script path and CLI arguments stable.
2. Move reusable business logic into `src/law_nexus`.
3. Make the script a thin wrapper that parses arguments, calls a package use
   case, formats output, and returns an exit code.
4. Preserve existing JSON schemas, fixture hashes, and check-mode semantics
   unless a slice explicitly regenerates fixtures with proof.
5. Do not retire a script in the same slice that first extracts its package
   logic.

Allowed wrapper shape:

```python
from law_nexus.composition import make_named_use_case


def main() -> int:
    args = parse_args()
    result = make_named_use_case().run(args)
    print_json(result)
    return result.exit_code
```

Not allowed:

- Moving CLI-only path parsing into `domain`.
- Calling concrete adapters directly from `application`.
- Importing `scripts` from `src/law_nexus`.
- Treating projections, ACP records, RDF, SHACL, dashboards, or GitNexus output
  as product source truth.

## Dependency direction

The import direction remains:

```text
composition -> application -> ports -> domain
composition -> adapters -> ports -> domain
```

Rules:

- `domain` imports no other `law_nexus` layer except intra-domain modules.
- `ports` may depend on `domain`, not on `application`, `adapters`, or
  `composition`.
- `application` may depend on `domain` and `ports`, not on concrete adapters.
- `adapters` may depend on `domain` and `ports`, not on `application`.
- `composition.py` wires concrete adapters into use cases with explicit factory
  functions. It is not a DI framework.

These rules are enforced by `import-linter` in `pyproject.toml`.

## Lifecycle and proof boundaries

M076 must preserve D098 lifecycle language:

- The package structure claim is `[validated]` by ADR-0001 and boundary gates.
- Domain forms remain `[proposed]` until hardened by real parser data.
- Port contracts remain `[proposed]` until more than one adapter or use case
  exercises them with tests.
- Parser, retrieval, FalkorDB, and embedding migrations are `[bounded]` unless
  runtime and source evidence prove stronger claims.

Special boundaries:

- R035 is not validated by documentation, projections, ACP, GitNexus, or package
  movement alone.
- R037 is not validated by a `GraphStore` port alone. It requires FalkorDB
  runtime ingest evidence with counts, cleanup, constraints, and error handling.
- Embedding compatibility is not Russian legal retrieval quality.
- LLM output is candidate-only and never legal authority.

## GitNexus baseline

M076 planning used GitNexus repo `law-nexus`.

Current GitNexus observations:

| Area | Current indexed pattern | Migration implication |
|---|---|---|
| Parser and source | `Main -> Build_fixture_hygiene`, `Candidate_references -> Sha256_bytes`, `Run_proof` variants | Extract named parser inventory, hierarchy, and source proof use cases |
| Retrieval and citation | `Build_payload -> Relative`, `Candidate_references` variants | Replace generic builders with named retrieval application services |
| FalkorDB graph | Many `Run_proof` variants for query, client connection, CSV rows, graph selection, bounded paths | Put runtime-specific behavior behind graph ports and adapters |
| Architecture and ACP | `Main -> Main_state`, `Dispatch -> Main_state`, SHA and path helpers | Keep governance projections outside product domain unless explicitly classified |

Known ambiguity targets:

- `main`
- `build_payload`
- `run_proof`
- `candidate_references`

New migrated package symbols should be specific and GitNexus-addressable, for
example:

- `build_parser_fixture_inventory`
- `build_source_hierarchy_records`
- `build_offline_citation_retrieval_cases`
- `build_real_artifact_retrieval_cases`
- `build_representative_retrieval_manifest`
- `run_falkordb_csv_ingest_proof`
- `validate_generated_cypher_safety`

## Stop conditions

Stop and replan the slice if any of these occur:

1. A moved flow changes fixture hashes, JSON schemas, or output order without an
   explicit regeneration plan.
2. A migrated use case requires importing `adapters` from `application`.
3. A domain model needs filesystem, network, FalkorDB, embedding, or LLM imports.
4. GitNexus impact reports HIGH or CRITICAL risk for a symbol planned for edit.
5. A runtime proof becomes dependent on unavailable secrets or external services.
6. A slice would validate R035, R037, or retrieval quality from documentation or
   projection evidence alone.
7. The full pytest failure count changes without updating `test-debt.md` or
   closing failures with evidence.

## Verification Matrix

| Wave | Slices | Required gates |
|---|---|---|
| Safety and baseline | S01 | `uv run lint-imports`; `uv run basedpyright src/`; GitNexus baseline; GSD doctor clean |
| Parser and source | S02 to S05 | Parser and inventory targeted pytest; wrapper CLI tests; import-linter; basedpyright; GitNexus detect changes |
| Legal domain | S06 to S08 | Domain model tests; import-linter; no infrastructure imports; lifecycle wording review |
| Retrieval and citation | S09 to S13 | Retrieval builder tests; citation-safe validator tests; fixture comparison; test-debt audit |
| FalkorDB graph | S14 to S16 | Graph port contract tests; FalkorDB smoke when available; generated Cypher policy tests; R037 boundary review |
| Embeddings | S17 | Fake embedder tests; optional local smoke; no managed GigaChat API path |
| Governance boundary | S18 to S19 | Architecture and ACP targeted tests; matrix review; source-truth boundary review |
| CLI consolidation | S20 to S21 | CLI compatibility tests; wrapper inventory; no premature script deletion |
| Traceability closure | S22 | `npx gitnexus analyze --force`; GitNexus queries find package use cases; `gitnexus_detect_changes` reviewed |

## Per-slice execution checklist

Before editing a symbol:

1. Run GitNexus impact for the specific symbol or document why it is not
   addressable yet.
2. Prefer extracting to a uniquely named package use case instead of moving a
   generic `main`, `build_payload`, or `run_proof` function as-is.
3. Add or update package-level tests before changing the wrapper.
4. Keep old script behavior compatible.

After edits:

1. Run `uv run lint-imports`.
2. Run `uv run basedpyright src/`.
3. Run targeted pytest for affected scripts and package tests.
4. Run GitNexus detect changes or re-index when the graph needs refresh.
5. Update `prd/architecture/test-debt.md` if failure counts or classifications
   change.

## Script categories for migration

| Category | Examples | Target |
|---|---|---|
| Parser and source | inventory, Consultant parser proof, hierarchy builders | `domain`, `ports.parser`, `application.parser_*`, parser adapters |
| Retrieval and citation | offline and real artifact retrieval, representative corpus manifest, evidence spans | retrieval ports, citation validator, retrieval application services |
| FalkorDB graph | CSV ingest, bulk loader, graph filtered retrieval, Cypher safety | graph ports, FalkorDB adapters, Cypher policy use cases |
| Embeddings | S09 and S10 local embedding probes | `Embedder` port and local adapter boundary |
| Architecture and ACP | architecture graph, RDF, ACP records, git-lex proof | governance scripts unless explicitly classified |
| CLI boilerplate | JSON IO, exit codes, path confinement | shared CLI utilities after several wrappers prove the pattern |

## Downstream readiness

S02 may start when S01 has verified:

- This contract exists.
- GitNexus ambiguity has been recorded.
- Boundary gates pass.
- GSD doctor is clean.
- No code movement occurred in S01.
