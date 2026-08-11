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

**Numbering gaps (intentional):** ADR-0001, 0002, 0003, 0006 are **not present**.
They belonged to the Python-onion / MADR-gate / library-boundary / PyO3-bridge era
and were retired with the Rust-only transition. Living docs must not cite them as
active authority. Historical mentions (e.g. “Historical library boundary ADR-0003”)
are narrative only.

## 2. Cross-surface citation matrix (active)

| ADR | ARCHITECTURE | README | adr/README | REQUIREMENTS | PROJECT | DECISIONS (D-rows) |
|-----|--------------|--------|------------|--------------|---------|---------------------|
| 0004–0005 | yes + LC | yes | yes | partial | partial | historical D-rows |
| 0007 | yes + LC | yes | yes | yes | weak | yes |
| 0008 | yes + LC | yes | yes | weak | weak | sparse |
| 0009–0011 | yes + LC | yes | yes | partial | partial | sparse |
| 0012 | yes + LC | yes | yes | weak | weak | sparse |
| 0013–0015 | yes + LC | yes | yes | partial | partial | yes |
| 0016–0022 | yes + LC | yes | yes | yes (R074) | yes | sparse |

Governor enforcement:

| Check | Severity | Covers |
|-------|----------|--------|
| `adr-truth-oracle-sync` | error on mismatch | ARCHITECTURE LC pairing for all present ADRs |
| `adr-index-completeness` | warn | every `doc/adr/0*.md` listed in `doc/adr/README.md` |
| `adr-doc-matrix-coverage` | warn | ontology 0016–0022 in REQUIREMENTS + PROJECT |
| `adr-structure-hygiene` | warn | Status LC + MADR sections |
| `adr-cross-surface-matrix` | warn | every ADR cited in ARCHITECTURE + README + adr/README |
| `archive-path-policy` | warn | historical vaults gitignored + untracked |

## 3. Deviations / gaps / noise (classified)

### P0 — logical / authority gaps

1. **Missing ADR files 0001/0002/0003/0006** still referenced in residual prose
   (`onion-migration-contract` was archived; ARCHITECTURE still names “Historical
   library boundary (ADR-0003)”). Action: keep as historical narrative **or** add
   a one-line “superseded/retired” stub ADR if agents keep treating the ID as live.
2. **DECISIONS.md** is append-only M001 FalkorDB/skill history; it does **not**
   mirror modern ADR index. Not a bug (D0xx ≠ ADR), but agents over-read early
   D-rows as current architecture. Action: point agents at ADR index first;
   optional future “active decision window” projection.
3. **Derived architecture registry** (`architecture_items/edges/report`) still
   contains dense FalkorDB/ACP vocabulary. CI still consumes it. Action: regenerate
   or mark derived surfaces non-authoritative (already policy); do not treat as
   truth oracle.

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

- `prd/architecture/acp` symlink → archive fixtures for CI architecture tests
- `prd/migration/acp-git-lex-decommission-roadmap.md` + decommission manifests

### P3 — still-on-active-tree but mention-heavy

- `prd/architecture/claims_ledger.md`, `product_readiness_blockers.md`,
  `architecture_graph_report.json` — derived / CI-bound; rewrite later, not delete.
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
5. **Ontology weave** — L1–L7 additionally required on REQUIREMENTS/PROJECT.
6. **Vault policy** — historical trees may exist on disk but must be gitignored
   and untracked so GitNexus/search do not treat them as active truth.
7. **Advisory vs blocking** — structure/matrix/index/doc-matrix are warn until
   the surface is considered launch-critical; truth-oracle LC mismatch is error.

Suggested CLI UX (current + next):

```text
uv run python -m law_nexus_harness governor
# findings include:
#   adr-truth-oracle-sync
#   adr-index-completeness
#   adr-doc-matrix-coverage
#   adr-structure-hygiene
#   adr-cross-surface-matrix
#   archive-path-policy
```

Future optional checks (not implemented in this wave):

- `adr-retired-id-ban`: fail if active docs cite ADR-0001/0002/0003/0006 as current.
- `adr-decisions-link`: require each ADR References to list governing D-row when one exists.
- `active-surface-era-noise`: warn on high-density FalkorDB/ACP tokens outside allowlist.
- `derived-registry-staleness`: warn if architecture_items lifecycle disagrees with ADR Status.

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
