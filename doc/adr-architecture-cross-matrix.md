# ADR × architecture document cross-matrix

Lifecycle: `[bounded]` process analysis (2026-08-11). Not product readiness.
Authority for live direction remains `prd/ARCHITECTURE.md` + `doc/adr/**`.

## 1. Present ADR inventory

| ADR | Status LC | Required sections | Era mentions (historical wording only) | Role |
|-----|-----------|-------------------|----------------------------------------|------|
| 0004 | bounded | complete | FalkorDB, PyO3 (rejected) | Rust product transition |
| 0005 | bounded | complete | ACP/git-lex/falkordb historical | Rust target architecture |
| 0007 | validated | complete | FalkorDB/PyO3 forbidden in harness | Python control-plane harness |
| 0008 | bounded | complete | — | Promotion/publication authority |
| 0009 | bounded | complete | — | Five-clock temporal model |
| 0010 | bounded | complete | — | Evidence kernel gates |
| 0011 | bounded | complete | — | KOF-DA ownership |
| 0012 | bounded | complete | FalkorDB historical | Consequential evidence protocol |
| 0013 | bounded | complete | Python product prior art | Universal multi-source parser |
| 0014 | proposed | complete | FalkorDB superseded | RuVector infrastructure |
| 0015 | bounded | complete | — | Hexagonal verification |
| 0016–0022 | proposed each | complete | — | Temporal legal ontology L1–L7 |
| 0023 | proposed | complete | — | Applicability protocol ownership; runtime absent |
| 0024 | proposed | complete | — | Review Case intake/disposition; non-authoritative projection and runtime absent |

**Numbering gaps (intentional):** ADR-0001, 0002, 0003, 0006 are **not present**.
They belonged to the Python-onion / MADR-gate / library-boundary / PyO3-bridge era
and were retired with the Rust-only transition. Living docs must not cite them as
active authority. Historical mentions (e.g. “Historical library boundary ADR-0003”)
are narrative only.

## 2. Cross-surface citation matrix (active)

`PRODUCT` and tracked `REQUIREMENTS` are `[proposed]` D2 drafts. Their `yes` entries mean citation/trace presence, not EA-02 acceptance or product proof. `ASSESSMENT` is A6 process evidence only. Local `.gsd/PROJECT.md` and decision rows are workflow context, never canonical substitutes.

| ADR | ARCHITECTURE | README | adr/README | PRODUCT draft | tracked REQUIREMENTS draft | ASSESSMENT/process | Local GSD context |
|-----|--------------|--------|------------|---------------|----------------------------|--------------------|-------------------|
| 0004–0005 | yes + LC | yes | yes | yes | yes | authority boundary | historical/partial |
| 0007 | yes + LC | yes | yes | yes | yes | authority boundary | workflow context |
| 0008 | yes + LC | yes | yes | yes | yes | role separation | sparse |
| 0009–0011 | yes + LC | yes | yes | yes | yes | temporal/authority boundary | sparse |
| 0012 | yes + LC | yes | yes | yes | yes | evidence boundary | sparse |
| 0013–0015 | yes + LC | yes | yes | yes | yes | proof/non-claim boundary | workflow context |
| 0016–0022 | yes + LC | yes | yes | yes, `[proposed]` | yes, `[proposed]`/`[deferred]` | O1–O7 design ceiling | historical R074/local weave |
| 0023 | yes + LC | yes | yes | yes, ownership `[proposed]`/runtime `[deferred]` | yes, ownership `[proposed]`/runtime `[deferred]` | D148 + EA-04 decision boundary | local D148 workflow record only |
| 0024 | yes + LC | yes | yes | no product trace; process contour only | no product trace; process contour only | D151/D152 authority and adapter boundary | local execution references only; no state mirror |

Governor enforcement:

| Check | Severity | Covers |
|-------|----------|--------|
| `adr-truth-oracle-sync` | error on mismatch | ARCHITECTURE LC pairing for all present ADRs |
| `adr-index-completeness` | warn | every `doc/adr/0*.md` listed in `doc/adr/README.md` |
| `adr-doc-matrix-coverage` | warn | current harness checks ontology 0016–0022 in local REQUIREMENTS + PROJECT; D2 adds tracked Product/requirements traces without treating local bodies as publication authority |
| `adr-structure-hygiene` | warn | Status LC + MADR sections |
| `adr-cross-surface-matrix` | warn | every ADR cited in ARCHITECTURE + README + adr/README |
| `archive-path-policy` | warn | historical vaults gitignored + untracked; active symlinks into vaults rejected |
| `published-trace-contract` | warn | 11 consequential PC→RQ→ADR chains plus assessment process-only boundary; structure only, not requirement/product proof |
| `document-freshness-triggers` | warn | non-authoritative dirty-tree change→companion catalog; a PASS is change-impact coverage, not semantic freshness |
| `adr-link-integrity` | warn | relative ADR Markdown target/fragment resolution; repository structure only |
| `adr-supersession-graph` | warn | scoped supersession target/reciprocity/DAG integrity; does not amend ADR authority |
| `adr-matrix-freshness` | warn | tracked `law-nexus-adr-matrix/v1` derivation freshness; matrix is explicitly non-authoritative |

## 3. Deviations / gaps / noise (classified)

### P0 — logical / authority gaps

No unresolved P0 lifecycle contradiction was found in the 2026-08-11 repeat
review: all 20 present ADR Status lifecycles match the foundation map in
`prd/ARCHITECTURE.md`.

1. **Retired IDs 0001/0002/0003/0006** remain absent by design. Living prose may
   name them only with an explicit retired/archive qualifier; no stub ADR should
   be added because that would re-create an active-looking index surface.
2. **DECISIONS.md** is workflow history and does not mirror the ADR index. Agents
   must read the living oracle and ADR index first.
3. **Derived architecture registry** is under D7 quarantine: IDs are preserved,
   authority-like edges are demoted and missing-anchor rows are blocked. Its
   stale graph report remains a visible WARN, not architecture authority.

### P1 — process / matrix gaps (governor now covers)

1. README previously omitted explicit `ADR-0008` / `ADR-0012` strings → fixed.
2. Truth-oracle table previously omitted 0008/0011/0012 → governor expectations expanded.
3. No machine check for MADR section completeness → `adr-structure-hygiene`.
4. No machine check for full ADR×README/ARCHITECTURE citation → `adr-cross-surface-matrix`.

### P2 — residual noise (archived this wave)

| Cluster | Destination | Note |
|---------|-------------|------|
| FalkorDB skills + LegalGraph routers | `archive/agent-skills/` | not discoverable |
| ACP/git-lex/FalkorDB/MiniMax scripts+tests | `archive/scripts|tests/` | not in CI suite |
| ACP research / source_structuring / GraphRAG notes | `prd/archive/research-era/` | gitignored |
| M001–M003 proofs | `prd/archive/milestone-proofs-era/` | gitignored |
| project-state ACP projections | `prd/archive/project-state-era/` | keep live `roadmap.md` + `data/roadmap.json` |
| onion/ACP residual architecture process docs | `prd/archive/architecture-era/` | keep registry + baseline |

**Intentionally tracked era names (policy, not noise):**

- `prd/migration/acp-git-lex-decommission-roadmap.md` + decommission manifests;
- qualified historical/non-claim wording in the oracle, ADRs and governor tests.

The former tracked `prd/architecture/acp` symlink and five ACP/git-lex proof
scripts were active-plane leaks, not required CI fixtures; they are removed from
the active index in the archive hygiene wave.

### P3 — still-on-active-tree but mention-heavy

- `prd/architecture/claims_ledger.md`, `product_readiness_blockers.md`,
  `architecture_graph_report.json` — derived / CI-bound. Claims/blockers are D7
  quarantined; the graph report is explicitly stale until its retired builder is replaced.
- `prd/parser/README.md`, retrieval contracts — may mention historical FalkorDB;
  keep if still product-relevant; tag lifecycle carefully.
- `historical-test-debt-visibility` warn — remaining tests mention era terms in
  harness/ADR conformance fixtures (expected).

## 4. How governor makes ADRs verifiable

Design principles:

1. **ADR is substance; governor is anti-drift** — never generate ADRs from D-rows.
2. **Status LC is the primary machine signal** — first Status line must carry a
   D098 tag; nested claims may be weaker inline.
3. **Oracle pairing** — ARCHITECTURE may not promote an ADR’s lifecycle.
4. **Cross-surface matrix** — every present ADR ID must be findable on the small
   set of living entrypoints (ARCHITECTURE, root README, adr README).
5. **Ontology weave** — current governor requires L1–L7 in local REQUIREMENTS/PROJECT as workflow anti-drift; tracked D2 publication uses O1–O7 aliases in `prd/PRODUCT.md` and `prd/REQUIREMENTS.md`. Local presence is not external authority or proof.
6. **Vault policy** — historical trees may exist on disk but must be gitignored
   and untracked so GitNexus/search do not treat them as active truth.
7. **Advisory vs blocking** — structure/matrix/index/doc-matrix are warn until
   the surface is considered launch-critical; truth-oracle LC mismatch is error.

Implemented CLI UX:

```text
uv run python -m law_nexus_harness governor
uv run python -m law_nexus_harness governor --only adr
uv run python -m law_nexus_harness governor --only semantic
uv run python -m law_nexus_harness governor --check adr-truth-oracle-sync
uv run python -m law_nexus_harness governor --explain adr-truth-oracle-sync
uv run python -m law_nexus_harness governor --format text
```

Default JSON remains report-v1 compatible. Selector and uncaught check-runner tool failures use exit 2; policy errors use exit 1; warn-only semantic debt uses exit 0. ADR lifecycle mismatches carry both ADR Status and oracle `path:line` evidence without source snippets. Exact evidence for other checks and migration of internally swallowed IO/git failures remain follow-on work.

Implemented deterministic checks:

- `adr-retired-id-ban`: warns on unqualified active references to retired ADR IDs;
- `active-surface-era-noise`: warns on unqualified era vocabulary on living entrypoints;
- `adr-truth-oracle-sync`: derives all present ADR lifecycles from their Status and
  fails on missing/mismatched oracle citations;
- `adr-index-completeness`: warns when an ADR or its per-entry lifecycle is absent;
- `archive-path-policy`: verifies ignored and untracked vault roots.

Follow-on checks, initially warn-only unless a deterministic authority contract is violated:

- `adr-link-integrity` and `adr-supersession-graph`;
- exact evidence-rich `path:line` findings and general tool/parser exit-2 handling (`--explain` is implemented);
- expand the bounded 11-chain `published-trace-contract` only when a new consequential chain is accepted; do not turn it into requirement satisfaction;
- extend the implemented freshness catalog only for proven consequential source classes; milestone/external-assessment/90-day events remain human-owned;
- `derived-registry-staleness` tied to the D7 quarantine contract;
- advisory semantic assessment ingestion that can never set a blocking verdict.

## 5. Archive + gitignore contract

Vaults (must be ignored + untracked; disk retention OK):

```
.lex/
python_archive/
Old_project/
prd/archive/acp-git-lex/
prd/archive/pre-rust-prd/
prd/archive/milestone-proofs-era/
prd/archive/research-era/
prd/archive/project-state-era/
prd/archive/architecture-era/
archive/agent-skills/
archive/scripts/
archive/tests/
```

Force-add only thin README maps: `archive/README.md`, `prd/archive/README.md`.

## 6. Non-claims

- This matrix does not validate legal correctness or product readiness.
- Ontology ADRs remain `[proposed]` design until TDD resolvers + real-corpus proof.
- Derived architecture JSONL/reports are not the truth oracle.
- GSD DECISIONS D001–D031 FalkorDB skill history is not current product direction.

## 7. prd/ residual cleanup (follow-on wave)

Tracked `prd/` reduced from ~279 → ~109 paths. Archived (gitignored vaults):

| Vault | Content |
|-------|---------|
| `prd/archive/research-era/` | Full remaining research tree (ontology fixtures + narrative) |
| `prd/archive/parser-dumps-era/` | Large Consultant dumps, golden_cases, staging graphs |
| `prd/archive/retrieval-era/` | Pre-Rust retrieval contracts/fixtures/proofs |
| `prd/archive/migration-era/` | Superseded matrices/roadmaps (not active decommission policy) |
| `archive/scripts|tests/` | Non-CI research/retrieval/s05–s10 scripts+tests |

**Active `prd/` keep set:** ARCHITECTURE.md, architecture registry+CI surfaces,
migration (roadmaps, rust-evidence, decommission policy, quality-gate), thin
parser contracts/schemas/profiles/examples, project-state roadmap pair.

GitNexus reindex after this wave required for accurate residual-noise queries.

<!-- RC12-F18: ADR citation hygiene rechecked with archive-only prior art remaps -->

<!-- continuity: ADR-0024 three-lifecycle / closure ceilings rechecked -->

<!-- TSG-003/013 S3 apply_industrial_op -->
