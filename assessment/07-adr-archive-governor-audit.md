# ADR, archive and governor repeat audit

**Assessment class:** repository architecture/process audit
**Status:** `[bounded]` process evidence; no product lifecycle promotion
**Reviewed baseline:** `bfe2ee6b6462c137c8fdb05a5dd88491ca2678a5` plus the uncommitted D7/archive hygiene wave
**Review date:** 2026-08-11

## 1. Coverage

The repeat audit covered all 19 present ADRs (`0004`, `0005`, `0007`–`0023`) and these corroborating surfaces:

- `prd/ARCHITECTURE.md`, `prd/PRODUCT.md`, `prd/REQUIREMENTS.md`;
- `prd/temporal-legal-model.md`, project-state roadmap and JSON;
- Rust, forward, ACP/git-lex decommission and external-assessment roadmaps;
- `assessment/00`–`06` and known defects;
- root and ADR READMEs;
- `doc/adr-architecture-cross-matrix.md`;
- governor, preflight, ADR conformance, CI/pre-commit and archive policy.

## 2. Architecture verdict

No unresolved P0 contradiction was found between ADR Status lifecycle and the living oracle. All present ADRs remain at their recorded ceilings:

- ADR-0004/0005 and ADR-0008–0013/0015: `[bounded]`;
- ADR-0007 repository harness: `[validated]` process boundary only;
- ADR-0014 and ADR-0016–0023: `[proposed]`;
- ADR-0023 runtime capability: `[deferred]`.

The full per-ADR matrix and remediation list lives in `doc/adr-architecture-cross-matrix.md`.

## 3. Deviations found

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| AA-01 | P1 | ADR index omitted per-entry lifecycle for ADR-0008–0023 | corrected; governor now verifies it |
| AA-02 | P1 | truth-oracle map omitted ADR-0023 and depended on a static list | corrected; present ADRs discovered from disk/Status |
| AA-03 | P1 | EA-03 open TQ wording could be mistaken for current state after EA-04 | frozen-snapshot notice added |
| AA-04 | P1 | project-state described the superseded ADR-0005 topology as if the ADR lifecycle were deferred | clarified |
| AA-05 | P1 | historical Rust roadmap R6 presented FalkorDB work as active-looking tasks | rewritten as superseded historical plan |
| AA-06 | P1 | tracked `prd/architecture/acp` symlink re-exposed ignored archive content | active alias removed; governor denylist added |
| AA-07 | P1 | five tracked ACP/git-lex proof scripts remained on active path | byte-preserved under ignored `archive/scripts/`; active copies removed |
| AA-08 | P1 | optional dependency group and lock retained FalkorDB | dependency removed; lock refreshed |
| AA-09 | P2 | default ADR conformance scanned local retired Python ADRs | active default now scans `doc/adr` only |
| AA-10 | P2 | cross-matrix described implemented checks as future work | corrected |
| AA-11 | WARN | D7 derived graph remains stale and verifier red | explicitly retained as EA-06 WARN |
| AA-12 | P1 | four active pytest modules depended exclusively on missing archived Python parser/retrieval/research artifacts | byte-preserved under ignored `archive/tests/`; active copies and collection debt removed |

Archived test hashes:

- `test_consultant_parser_proof.py`: `8800f548c5607ca47e68f4a2b6a7fb2e84d39b6e04bf85bd858a7bd875c71cb4`;
- `test_hierarchy_metadata_completeness.py`: `9bd0a91ddabcbbae911a158647908e10e2079e33874a32b310f5187bf6f9a612`;
- `test_local_retrieval_runtime_check_cli.py`: `44219ffd86ee499724ac2a165ebd7107ebb7fb032d0e5dab996ee19f22ca814e`;
- `test_source_structuring_protocol.py`: `4f6baa7d4d418aba0b3236b62c2bad20f2f82b8ed5a93e042bb2d61eb9c6043b`.

## 4. Archive/index boundary

`.gitignore` cannot hide files already tracked by Git. Therefore the applied policy is:

1. active Rust and `src/law_nexus_harness` remain tracked;
2. historical vault bodies remain on disk, ignored and untracked;
3. tracked aliases and executable copies that expose vault content are removed from the active index;
4. exact retired script/symlink paths are ignored and checked by governor;
5. decommission manifests retain source hashes and archive destinations;
6. GitNexus must be reindexed after the change is committed; until then the existing index may still contain retired aliases and is not closure evidence.

The Python harness is intentionally not archived: ADR-0007 defines it as the active repository-control boundary. Python product/domain code remains archive-only.

## 5. Governor direction

The implemented MVP is deliberately small:

- dynamic ADR inventory and Status-derived lifecycle pairing;
- per-entry ADR index lifecycle check;
- retired active-alias denylist;
- active-only default claim scan.

The next design is documented in `prd/architecture/adr-governor-verification-design.md`: additive evidence citations, explain/filter modes, derived machine matrix, link/supersession checks and non-blocking semantic review input.

## 6. Non-claims

- The audit does not prove legal correctness or product readiness.
- A green governor does not validate ontology, RuVector, retrieval, citation or applicability runtime.
- Archive material remains prior art, not evidence for current requirement closure.
- LLM review remains advisory and cannot block, accept or promote architecture by itself.
