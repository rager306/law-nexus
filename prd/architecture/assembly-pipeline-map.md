# Assembly Pipeline Map — One Consultant Act (XML → Events → Temporal AST)

> Tracked audit artifact of M173 (pipeline audit package), slice S01.
> Canonical authority: `prd/architecture/kb-ontology.yaml` (`assembly_fsm`).
> This file is a human-readable mirror: it does not override the YAML, does not
> edit ADRs or the promotion board, and does not raise any lifecycle (D098).
> Every claim below carries a lifecycle tag and a repo-relative tracked
> evidence anchor.

## 1. Scope and canonical source

- **Scope:** the assembly pipeline of a single Consultant act document, from
  raw source bytes to a bounded Temporal AST edition — exactly the surface the
  YAML `assembly_fsm` models.
- **Canonical FSM (quoted from `kb-ontology.yaml`):**
  - `name: temporal-ast-assembly`
  - `initial: S_ingest`
  - `current: S_ready_bounded`
  - `meaning: process model for XML to events to AST; not readiness O-state`
- **Executed proof surfaces:**
  - tracked same-file fixture 402-FZ (git-tracked XML under
    `law-source/consultant/`) — the fixture the YAML `non_claims` names for
    `S_ready_bounded`;
  - real-corpus 44-FZ runs on local `consru_export/` — `[smoke]`, gitignored,
    skip-capable in CI, never a durable promotion proof (M168/D180 boundary).
- **Cross-check provenance:** every row below was verified against
  `kb-ontology.yaml` `assembly_fsm` and the M168–M171 closeouts
  (M168 final `21286a7`; M170 verified at `82e53d6`; M171 final `db8d1db`).
- **Drift control:** `tests/test_assembly_pipeline_map.py` pins this map to the
  YAML states (delivered by the remainder of S01, task T03).
- Document-group profiles (§5), the three L2 canons (§6), and the explicit
  non-goals (§7) were appended to this map by S01 T02; the FSM state table
  (§2) and the readiness distinction (§3) are the T01 deliverable.

## 2. State table: `assembly_fsm` (S_design … S_ready_bounded)

| State | YAML `name` | Canonical meaning (YAML) | Status | Lifecycle | Tracked evidence | Gap (honest) | Anchor |
|---|---|---|---|---|---|---|---|
| `S_design` | `design_inventory` | Review 4 vocabulary named; no executable stack propose | historical design inventory; superseded by the executable pipeline of M169+ | `[proposed]` | `doc/review/review-13-08-2026.md` (Review 4 verdict for XML → events → AST: designed, no code) | design-only state: at Review 4 no executable stack propose existed; kept for provenance | Review 4 (2026-08-13) |
| `S_ingest` | `classify_bytes` | assign corpus_roles; reject unclassified | executed on real corpus paths (M169); two-factor group detection fail-closed (M171) | `[bounded]` | `crates/ln-kb-ontology/tests/corpus_role.rs`; `crates/ln-kb-ontology/src/registry.rs` (`classify_corpus_role`, `CONSULTANT_EXPORT_DIR`); `crates/ln-decode/src/structural_profile.rs` | grounding depends on the consru_export layout (gitignored → CI SKIP); latin path-needles vs cyrillic filenames stay honest `Unknown`; real-act binding comes from metadata, not filename | M169 S01; M171 S01 (`db8d1db`) |
| `S_decode` | `provider_blocks` | WordML or ODT to ParsedBlock; wrong family fail-closed | tracked e2e on Consultant WordML (435-FZ); malformed input fails atomically | `[bounded]` | `crates/ln-consultant-parser/tests/tracked_pipeline_test.rs`; `crates/ln-decode/tests/consultant_wordml_block_decoder.rs`; `crates/ln-decode/tests/garant_odt_block_decoder.rs` | tracked assembly proof is Consultant WordML only; the Garant ODT decoder is contract-tested but is not part of the Consultant act proof (Consultant ≠ Garant; no shared fixture) | M168 S02 (`16d4b78`) |
| `S_extract` | `snapshot_candidates` | markers mentions phrases; not AST | G1 = 119 markers on tracked 435-FZ; profile-driven article body boundaries | `[bounded]` | `crates/ln-decode/tests/consultant_real_tracer.rs`; `crates/ln-decode/tests/article_body_contract.rs`; `crates/ln-kb-ontology/tests/text_extraction.rs` | candidates are not AST; 44-FZ nested punkt out of scope (D192 flat anchor); recursive walk executed only on subordinate acts (M171 S03) | M168 S01; M170 S01 (`82e53d6`); M171 S01 |
| `S_identify` | `work_expression` | mint identity; bad ISO fail-closed | real Expression ID minting from file paths (44-FZ edition-0118; 402-FZ same-file) | `[bounded]` | `crates/ln-kb-ontology/src/registry.rs` (`load_expression_id_for_path`); `crates/ln-kb-ontology/tests/hierarchy_registry.rs` | file dates are process truth, not legal truth (D116/D117); amendment provenance still pending | M169 S01 |
| `S_bind` | `marker_to_cc` | registry only; Unknown is legal | 102 CC bindings for 44-FZ (8 glava + 94 statya); path-key bindings and recursive ranks (M171) | `[bounded]` | `prd/architecture/kb-hierarchy-registry.yaml`; `crates/ln-kb-ontology/tests/hierarchy_cc_map.rs`; `crates/ln-decode/tests/registry_bindings_generator.rs` | Chast/Punkt/Paragraph of 44-FZ remain `Unknown` (own bounded wave); registry is a design inventory, not store types; YAML patches stay human-gated (D185) | M169 S02; M171 S02 |
| `S_propose` | `stack_attach_drafts` | document-order stack; not committed | document-order stack propose with recursive nesting 4 → 4.1 → 4.1.2 | `[bounded]` | `crates/ln-kb-ontology/tests/membership_propose.rs` | drafts only: nothing attaches until `S_admit`/`S_commit` accept them | M169 S02; M171 S02 |
| `S_admit` | `conflict_quarantine` | two-parent / presence conflict / no provenance stop | conflict gate with quarantine counters; unbound markers quarantined fail-closed | `[bounded]` | `crates/ln-kb-ontology/tests/membership_admit.rs`; `crates/ln-product-cli/tests/cli_contract.rs` (`membership_conflict_quarantined`) | fail-closed stop, no auto-resolution; ConflictResolver product runtime is not claimed | M169 S03; M171 S01 |
| `S_commit` | `append_events` | append-only with evidence_class | append-only commit with evidence classes; 44-FZ edition-0118 commit = 94; 402-FZ committed == admitted | `[bounded]` | `crates/ln-kb-ontology/tests/membership_commit.rs`; `crates/ln-product-cli/tests/cli_contract.rs` | the event log is per-run; a durable event store is an explicit non-goal of this map | M169 S02 |
| `S_fold` | `edition_ast_at` | fold membership then presence at ordinal t | membership fold then presence at ordinal t; 44-FZ roots = 8 / nodes = 102; 402-FZ roots == glava, nodes == bound | `[bounded]` | `crates/ln-kb-ontology/tests/edition_ast.rs`; `crates/ln-temporal/tests/membership_fold.rs`; `crates/ln-product-cli/tests/real_44fz_assembly.rs` | fold is recomputed per run (no fold cache / persistence); 118-edition fold-verify not done | M169 S02 |
| `S_verify` | `replay_and_oracle_diff` | fold replay and EditionOracle checksum | zero-drift replay on tracked 402-FZ and on real pairs 0080 → 0081 (structural, drafts = 81) and 0001 → 0002 (text-only oracle) | `[bounded]` | `crates/ln-kb-ontology/tests/oracle_diff.rs`; `crates/ln-product-cli/tests/cli_contract.rs` (`oracle_drift == 0`); `crates/ln-product-cli/tests/real_44fz_assembly.rs` | verify is bounded to named pairs and single-edition folds; text-facet drafts are observations, not membership records (KBO-R061); no 118-edition verify | M169 S03; M170 S02 (`82e53d6`) |
| `S_heal` | `new_event_or_waiver` | never edit the tree | healing by new events only; census → human-apply → census-to-zero loops | `[bounded]` | `crates/ln-kb-ontology/tests/heal_drift.rs`; `crates/ln-decode/tests/unknown_forms_contract.rs` (StructuralNearMiss census, D194) | waiver / correction ledger (TSG-011) not implemented; YAML patch apply stays human-gated | M169 S04; M171 S03 |
| `S_ready_bounded` | `bounded_fixture_ready` | one fixture replay-ok; not S6 and not Applicable | current FSM head: one tracked fixture passes the full pipeline | `[bounded]` (fixture); real-corpus act `[smoke]` | `crates/ln-product-cli/tests/cli_contract.rs::inspect_402_fz_reports_non_zero_attach_from_yaml_ranks` (proposals > 0, committed == admitted, AST roots/nodes, `oracle_drift == 0`, `ctv_resolved > 0`, real `402-fz` expression id); fixture `law-source/consultant/federalnyi-zakon-ot-06-12-2011-n-402-fz-red-ot-15-12-2025-o-bukhgalterskom-uchete--fcc0b660.xml`; real 44-FZ edition-0118 assembly in `crates/ln-product-cli/tests/real_44fz_assembly.rs` (skip-capable, consru_export) | one fixture plus one real-corpus act; NOT TSG S6, NOT Applicable, not readiness `O6`; no Force/Applicable runtime | M168–M171 closeouts; YAML `assembly_fsm.non_claims` |

## 3. Assembly FSM vs readiness FSM (do not merge)

| FSM | YAML key | Initial | Current | Meaning |
|---|---|---|---|---|
| Assembly (this map) | `assembly_fsm` | `S_ingest` | `S_ready_bounded` | process model for XML → events → AST |
| Readiness | `fsm` (`kb-ontology-readiness`) | `O0` | `O2_calendar_ordinal` | ontology surface readiness; terminal states `O6_closed_bounded` / `O6_closed_validated` |

- `O2_calendar_ordinal` means: ISO `legal_act_effect_day` maps to a synthetic
  ordinal; not a legal calendar (`kb-ontology.yaml`).
- `S_ready_bounded` advances **no** O-state: it is not the `O3` exit, not
  `O6`, and `InForce` does not imply `Applicability`.
- Readiness advance past `O2_calendar_ordinal` requires representative
  fixtures; the one-fixture assembly proof does not constitute them.

## 4. `assembly_fsm` non-claims (quoted from YAML)

1. "assembly_fsm is not kb-ontology-readiness and not O3 exit"
2. "current S_ready_bounded: one fixture (402-FZ) passes full pipeline
   (drift=0, ctv_resolved>0, real expression_id); NOT TSG S6, NOT Applicable;
   assembly FSM complete"

These non-claims bound this map: a complete assembly FSM for one fixture is
not product readiness, not legal correctness, and not applicability.

## 5. Document-group profiles (YAML `document_groups`)

> Canonical source: `kb-ontology.yaml` `document_groups` (ADR-0020;
> KBO-R062). The catalog contract (five groups, closed role vocabulary,
> ladder tokens ⊆ decode-token catalog, non-claims declared) is pinned by
> `crates/ln-kb-ontology/tests/document_groups_catalog.rs`; governor coverage
> (`check_document_groups_coverage`, `src/law_nexus_harness/governor.py`) is
> advisory. The `parsed_as` Work→DocumentGroupRef binding (group + catalog
> version, KBO-R064) is a `system_observation` heuristic, never legal
> classification.

| Group | Granularity / ladder | Honest pipeline position | Tracked evidence | Gap |
|---|---|---|---|---|
| `federal_law@v1` | statya; glava(container)→paragraph(container)→statya(unit)→chast(subunit)→punkt(subunit, recursive max_depth 2)→podpunkt(subunit) | the only profile with an executed full FSM run to `S_ready_bounded` | `document_groups_catalog.rs` (`federal_law_v1_*`); `prd/architecture/kb-hierarchy-registry.yaml`; `crates/ln-product-cli/tests/cli_contract.rs` (tracked 402-FZ fixture); `crates/ln-product-cli/tests/real_44fz_text_ctv.rs` / `real_44fz_assembly.rs` (consru_export [smoke]) | registry binds glava+statya only; Chast/Punkt/Paragraph stay `Unknown` (D192); no razdel in this ladder — a РАЗДЕЛ marker fails closed (R8-08); edition-day registry parses only `law_*` paths |
| `code` | statya; razdel(container)→glava(container)→statya(unit) — the only ladder with razdel (R8-08) | catalog-only: declared and contract-tested, never executed | `document_groups_catalog.rs` (5-group + ladder-token contract) | `group("code")` has zero call sites in `crates/`; three kodeks Consultant XMLs exist in `law-source/consultant/` (145-FZ, 195-FZ, 136-FZ) but no decode/extract/bind/fold run uses the `code` profile |
| `government_resolution` | punkt; punkt(unit, recursive max_depth 3, suffix `.`)→podpunkt(subunit)→prilozhenie(container) | punkt unit collection executed on the real Garant ПП corpus (M171 S03): PP_60 primary + bounded breadth; nested sub-markers accumulate into the unit body | `crates/ln-product-cli/tests/real_subordinate_acts.rs` | CCs are fixture-minted, not registry identity; no edition-day registry for ПП; amendment PPs (lettered а/б) honestly yield 0 punkt units; one embedded-image ODT fails decode; depth-ranked recursive walk remains `[proposed]` (KBO-R063) |
| `departmental_order` | punkt; punkt(unit, recursive max_depth 4, suffix `)`)→podpunkt(subunit)→primechanie(subunit-text)→prilozhenie(container) | executed on an inline fixture only (M171 S03): two punkt units resolve text-CTV | `crates/ln-product-cli/tests/real_subordinate_acts.rs` (`order_punkt_units_resolve_via_inline_fixture`) | no real приказ in the corpus — fixture-only proof, not corpus evidence |
| `court_practice` | text-only (empty ladder; practice ≠ AST, ADR-0020) | stops before structure: the probe ignores numbering and statya markers; no `S_bind`/`S_propose`/`S_commit`/`S_fold` for practice documents | `crates/ln-decode/tests/structural_profile_contract.rs` (`probe_ignores_numbering_for_text_only`, `court_practice_ignores_statya_markers`, `court_practice_ignores_depth4_numbering`) | probe-only proof: no decode→bind pipeline run over a real practice document anywhere in M168–M171 |

YAML `document_groups.non_claims` (§4) bound this table verbatim: the
binding is a `system_observation` heuristic, the vocabulary stays in the
catalog, court practice text is not an AST.

## 6. The three L2 canons (`edition_ast_at(t)`)

KBO-R045 (Review 5 R5-03; ADR-0017 §1a): a dated edition view is three pure
folds/filters over event logs — never a stored document AST.

| Canon | Definition | Function | Tracked evidence | Bound |
|---|---|---|---|---|
| CompositionAst | fold(membership ≤ t) | `ln_temporal::domain::fold_membership_at` | `crates/ln-temporal/tests/membership_fold.rs`; `crates/ln-kb-ontology/tests/edition_ast.rs` | structural membership only — presence in the tree is not `InForce` (KBO-R009) |
| EditionAst | filter(CompositionAst, fold_presence ≤ t) | `ln_kb_ontology::domain::edition_ast_at` composing `fold_expression_presence` + `filter_ast_to_expression` | `crates/ln-kb-ontology/tests/edition_ast.rs` (incl. `edition_ast_at_earlier_day_hides_future`); presence surface in `membership_commit.rs`, `component_in_expression.rs` | per-Expression include/exclude at day t; an earlier day hides future events |
| TextAst | resolve_CTV(cc, t) | `ln_kb_ontology::domain::resolve_ctv` over a `TextVersionLog` built by `build_text_log_from_markers` / `build_text_log_from_articles` | `crates/ln-kb-ontology/tests/resolve_ctv.rs`; `crates/ln-product-cli/tests/cli_contract.rs` (tracked 402-FZ fixture, `ctv_resolved > 0`); `crates/ln-product-cli/tests/real_44fz_text_ctv.rs` (consru_export [smoke]: ≥85 statya non-empty text, edition-0118) | text-facet drafts are observations, not membership records (KBO-R061); the real-corpus proof is skip-capable |

All three recompute per run; no canon is cached or persisted (§7).

## 7. Explicit non-goals of this map

Named so later slices cannot silently widen them:

1. **Fold cache / AST persistence** — none: every `fold_membership_at` /
   `fold_expression_presence` / `resolve_ctv` call recomputes from event
   logs; nothing persists an AST between runs.
2. **Schedule / agent runtime** — none: the pipeline executes inside tests
   and CLI invocations; no scheduler, daemon, or autonomous agent drives
   acts through `assembly_fsm` states.
3. **Durable event store** — none: membership and text event logs are
   per-run in-memory structures; a durable event store is out of scope
   (S_commit gap, §2).
4. **Force runtime** — none: this map folds structure and text only and
   never writes or implies a force status; the force↔membership join is
   offline and partial (KBO-R012).
5. **Applicable runtime** — none: `ApplicableDecision` stays a forbidden
   node kind; `InForce` never implies `Applicable` (KBO-R008; RC11-F09),
   and nothing may be derived from `S_ready_bounded` toward
   applicability.

## 8. Pending sections of this map (S01 remainder)

- Pytest drift contract `tests/test_assembly_pipeline_map.py` — T03.
