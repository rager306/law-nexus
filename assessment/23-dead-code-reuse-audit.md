# Dead-code and reuse audit register (DCA)

**Status:** `[bounded]` candidate inventory — **Disposition status: open** (T01 pins the pool; T02/T03 disposition every row)
**Series:** inherits the assessment/21 protocol (frozen revision, tracked evidence, preserved non-claims); bug-dimension precedent assessment/08.
**Milestone:** M195-mdvctn / S03 / T01 (post-queue debt and process gap closure)
**Graph snapshot:** GitNexus repo `law-nexus`, re-indexed this task at HEAD `52314d7`, 12,519 nodes / 24,532 edges / 506 clusters / 257 flows.

## Methodology

Bounded funnel, never bulk cleanup:

1. **Fresh index** — `node .gitnexus/run.cjs analyze --force --name law-nexus`, run to completion (interrupting `analyze` corrupts the KuzuDB graph), then `node .gitnexus/run.cjs status` must show indexed commit == current commit and not stale. All numbers below are from the fresh index; stale-index research numbers (1,961 raw, indexed `c187e4c`) are comparators only, never evidence.
2. **One bounded cypher campaign** (≤15 `gitnexus_cypher` calls per turn; raw Function/Method/Struct/Enum counts → filtered export with hard `LIMIT 300` → reuse query with `LIMIT 50`). Raw cypher output is bookkeeping only; the distilled rows live in this tracked file (KNOWLEDGE Rule 6: durable proof is the tracked artifact, not `.gsd/exec` transcripts).
3. **Three corroboration channels, named but not yet run to confirmation:** (a) graph — zero inbound CALLS/USES/ACCESSES in GitNexus (the only channel exercised so far, in enumeration mode); (b) `cargo check --workspace --offline 2>&1 | rg "never used|never constructed|never read"` (rustc `dead_code`; does not fire for `pub` items in lib crates); (c) `rg -n "\b<symbol>\b" crates/ src/ --type rust`. No candidate is confirmed dead by this file — T02/T03 run channels (b)+(c) plus `gitnexus_impact` upstream spot checks per row.
4. **Disposition** in this file (keep-reason class or removal-slice ref), then **Tier-0 removal only**, small TDD slices, covering suite green *before* removal.

Working zero-inbound recipe (reproducible against the frozen snapshot; Kuzu dialect: use `r.type`, node tables, and materialize counts in `WITH` — no `split()`, no list-comprehension `WHERE`, no arithmetic over aggregates, `labels(n)` empty, `type(r)` invalid):

```cypher
MATCH (s:Function) WHERE s.filePath STARTS WITH 'crates/'
OPTIONAL MATCH (x)-[r:CodeRelation {type:'CALLS'}]->(s)
WITH s, count(r) AS c1
OPTIONAL MATCH (x2)-[r2:CodeRelation {type:'USES'}]->(s)
WITH s, c1, count(r2) AS c2
OPTIONAL MATCH (x3)-[r3:CodeRelation {type:'ACCESSES'}]->(s)
WITH s, c1, c2, count(r3) AS c3
WHERE c1 + c2 + c3 = 0
RETURN count(s);
```

`Method` adds `METHOD_IMPLEMENTS` to the usage set; `Struct`/`Enum` use USES/ACCESSES only. Filtered export = same recipe plus the generic false-positive exclusion below, `ORDER BY filePath, startLine`, hard `LIMIT 300`. Reuse query: same `Function` name in ≥2 distinct files under `crates/`, same exclusions, `LIMIT 50`, grouped per crate client-side (Kuzu has no `split()`).

Generic false-positive names excluded from the filtered export: `new, fmt, clone, default, from, from_str, try_from, into, as_str, as_ref, to_string, main, run, build, drop, hash, eq, cmp, serialize, deserialize, is_empty, len, get, set, is_provisional, authoritative_count`.

Known false-positive classes visible in the pool (each row stays `proposed` until corroborated): `#[test]` harness entry points (invoked by attribute, not by CALLS edges — the bulk of `tests/*.rs` rows); trait-dispatched impls (`Display::fmt` family, already excluded by name); port trait methods mirrored across `ports.rs`/`adapters.rs` (dead in the graph, load-bearing by contract); `pub` getters on domain types; macro/derive/serde-referenced items. Per R038 the graph channel alone never proves deadness.

Vault directories are excluded from the audit entirely — they are not product truth: `python_archive/`, `.lex/`, `Old_project/`, `prd/archive/`, `archive/`.

## Frozen HEAD

- **Full SHA:** `52314d750e1143734cf0d59b7912c3f271d8d471` (branch `main`), pinned before any index or graph work (`git rev-parse HEAD`; `git status --porcelain` → **dirty 0**).
- **Indexed commit after `analyze --force`:** `52314d7` == current commit; `node .gitnexus/run.cjs status` → `Status: up-to-date`; index stats 12,519 nodes / 24,532 edges / 506 clusters / 257 flows.
- The stale snapshot this task replaces: indexed `c187e4c`, raw pool 1,961. Fresh raw pool is 1,985 (+24 drift) — research-era numbers are not current and were not used for any row.
- This file is written *after* the pin; pool numbers describe the pinned tree (dirty 0, product code identical to what was indexed). Re-index after the tracked commit of this register (assessment/21 closeout precedent).

## Candidate pool

Raw zero-inbound counts under `crates/` (fresh index, frozen HEAD):

| Node table | Usage edges required for "inbound" | Raw zero-inbound | Stale comparator |
|---|---|---|---|
| Function | CALLS + USES + ACCESSES | **1,985** | 1,961 (indexed `c187e4c`) |
| Method | CALLS + USES + ACCESSES + METHOD_IMPLEMENTS | **0** | n/a |
| Struct | USES + ACCESSES | **370** | n/a |
| Enum | USES + ACCESSES | **118** | n/a |

Filtered Function pool (generic names excluded): **1,811** rows. The durable DCA table below is the bounded export: first **300** rows of the `ORDER BY filePath, startLine` ordering (hard `LIMIT 300`), IDs **DCA-001 … DCA-300**. `Vis` = `pub`/`private` as reported by the indexer (`isExported`). Every row enters as `proposed`; nothing is removed by this file.

Pool shape: 151 rows in `src/`, 149 in `tests/`; 8 of 47 crates own the whole pool — `ln-accelerate` 16, `ln-admission` 16, `ln-applicability` 67, `ln-citation` 10, `ln-closure` 27, `ln-conformance` 11, `ln-consultant-parser` 85, `ln-decode` 68. At least ~51 rows sit directly in `ports.rs`/`adapters.rs` surfaces (Tier-0 criterion 3 → auto-KEEP class `port-contract-surface`), and the `tests/` half is `#[test]`-entry-point false-dead by construction.

| ID | Path:line | Symbol | Crate | Vis | Status |
|---|---|---|---|---|---|
| DCA-001 | crates/ln-accelerate/src/adapters.rs:51 | has_provisional | ln-accelerate | private | proposed |
| DCA-002 | crates/ln-accelerate/src/adapters.rs:54 | provisional_count | ln-accelerate | private | proposed |
| DCA-003 | crates/ln-accelerate/src/adapters.rs:57 | put | ln-accelerate | private | proposed |
| DCA-004 | crates/ln-accelerate/src/adapters.rs:63 | label_for | ln-accelerate | private | proposed |
| DCA-005 | crates/ln-accelerate/src/application.rs:54 | provisional_count | ln-accelerate | pub | proposed |
| DCA-006 | crates/ln-accelerate/src/domain.rs:19 | parse_id | ln-accelerate | private | proposed |
| DCA-007 | crates/ln-accelerate/src/domain.rs:122 | provisional_outcomes_are_non_authoritative | ln-accelerate | private | proposed |
| DCA-008 | crates/ln-accelerate/src/ports.rs:5 | has_provisional | ln-accelerate | private | proposed |
| DCA-009 | crates/ln-accelerate/src/ports.rs:6 | provisional_count | ln-accelerate | private | proposed |
| DCA-010 | crates/ln-accelerate/src/ports.rs:7 | put | ln-accelerate | private | proposed |
| DCA-011 | crates/ln-accelerate/src/ports.rs:9 | label_for | ln-accelerate | private | proposed |
| DCA-012 | crates/ln-accelerate/tests/hc16_accelerate.rs:20 | normal_acceleration_is_provisional_non_authoritative | ln-accelerate | private | proposed |
| DCA-013 | crates/ln-accelerate/tests/hc16_accelerate.rs:30 | direct_promotion_rejected | ln-accelerate | private | proposed |
| DCA-014 | crates/ln-accelerate/tests/hc16_accelerate.rs:41 | label_mutation_rejected | ln-accelerate | private | proposed |
| DCA-015 | crates/ln-accelerate/tests/hc16_accelerate.rs:51 | hostile_label_mutator_cannot_grant_authority | ln-accelerate | private | proposed |
| DCA-016 | crates/ln-accelerate/tests/hc16_accelerate.rs:60 | app_owned_label_not_mutated_by_hostile_adapter | ln-accelerate | private | proposed |
| DCA-017 | crates/ln-admission/src/adapters.rs:9 | observe | ln-admission | private | proposed |
| DCA-018 | crates/ln-admission/src/adapters.rs:61 | observe | ln-admission | private | proposed |
| DCA-019 | crates/ln-admission/src/domain.rs:19 | parse_id | ln-admission | private | proposed |
| DCA-020 | crates/ln-admission/src/domain.rs:126 | is_unknown | ln-admission | pub | proposed |
| DCA-021 | crates/ln-admission/src/domain.rs:217 | rejects_empty_request_id | ln-admission | private | proposed |
| DCA-022 | crates/ln-admission/src/domain.rs:222 | capacity_unknown_by_default_marker | ln-admission | private | proposed |
| DCA-023 | crates/ln-admission/src/ports.rs:6 | observe | ln-admission | private | proposed |
| DCA-024 | crates/ln-admission/tests/hc13_admission.rs:18 | bound_unknown_pauses_with_capacity_unknown | ln-admission | private | proposed |
| DCA-025 | crates/ln-admission/tests/hc13_admission.rs:32 | saturated_rejects_with_capacity_unknown | ln-admission | private | proposed |
| DCA-026 | crates/ln-admission/tests/hc13_admission.rs:42 | retry_amplification_rejects | ln-admission | private | proposed |
| DCA-027 | crates/ln-admission/tests/hc13_admission.rs:54 | measured_local_bound_can_admit | ln-admission | private | proposed |
| DCA-028 | crates/ln-admission/tests/hc13_admission.rs:72 | legal_delay_and_completeness_claims_are_rejected | ln-admission | private | proposed |
| DCA-029 | crates/ln-admission/tests/hc13_hostile_admission.rs:17 | hostile_vendor_unknown_cannot_force_admit | ln-admission | private | proposed |
| DCA-030 | crates/ln-admission/tests/hc13_hostile_admission.rs:31 | hostile_pretend_measured_with_vendor_numbers_still_rejects | ln-admission | private | proposed |
| DCA-031 | crates/ln-admission/tests/hc13_hostile_admission.rs:46 | hostile_vendor_inferences_are_rejected | ln-admission | private | proposed |
| DCA-032 | crates/ln-admission/tests/hc13_hostile_admission.rs:74 | hostile_retry_amplification_still_rejects_first | ln-admission | private | proposed |
| DCA-033 | crates/ln-applicability/src/adapters.rs:17 | predicate_registry_revision | ln-applicability | private | proposed |
| DCA-034 | crates/ln-applicability/src/adapters.rs:21 | profile_input_revision | ln-applicability | private | proposed |
| DCA-035 | crates/ln-applicability/src/adapters.rs:25 | case_facts_revision | ln-applicability | private | proposed |
| DCA-036 | crates/ln-applicability/src/domain.rs:171 | effective_from | ln-applicability | pub | proposed |
| DCA-037 | crates/ln-applicability/src/domain.rs:175 | effective_to | ln-applicability | pub | proposed |
| DCA-038 | crates/ln-applicability/src/domain.rs:188 | try_new | ln-applicability | pub | proposed |
| DCA-039 | crates/ln-applicability/src/domain.rs:199 | id | ln-applicability | pub | proposed |
| DCA-040 | crates/ln-applicability/src/domain.rs:203 | kind | ln-applicability | pub | proposed |
| DCA-041 | crates/ln-applicability/src/domain.rs:216 | try_new | ln-applicability | pub | proposed |
| DCA-042 | crates/ln-applicability/src/domain.rs:227 | id | ln-applicability | pub | proposed |
| DCA-043 | crates/ln-applicability/src/domain.rs:231 | kind | ln-applicability | pub | proposed |
| DCA-044 | crates/ln-applicability/src/domain.rs:244 | try_new | ln-applicability | pub | proposed |
| DCA-045 | crates/ln-applicability/src/domain.rs:255 | id | ln-applicability | pub | proposed |
| DCA-046 | crates/ln-applicability/src/domain.rs:259 | kind | ln-applicability | pub | proposed |
| DCA-047 | crates/ln-applicability/src/domain.rs:279 | try_new | ln-applicability | pub | proposed |
| DCA-048 | crates/ln-applicability/src/domain.rs:300 | id | ln-applicability | pub | proposed |
| DCA-049 | crates/ln-applicability/src/domain.rs:304 | revision | ln-applicability | pub | proposed |
| DCA-050 | crates/ln-applicability/src/domain.rs:308 | conditions | ln-applicability | pub | proposed |
| DCA-051 | crates/ln-applicability/src/domain.rs:312 | exceptions | ln-applicability | pub | proposed |
| DCA-052 | crates/ln-applicability/src/domain.rs:316 | defeaters | ln-applicability | pub | proposed |
| DCA-053 | crates/ln-applicability/src/domain.rs:320 | temporal_scope | ln-applicability | pub | proposed |
| DCA-054 | crates/ln-applicability/src/domain.rs:373 | empty | ln-applicability | pub | proposed |
| DCA-055 | crates/ln-applicability/src/domain.rs:468 | empty | ln-applicability | pub | proposed |
| DCA-056 | crates/ln-applicability/src/domain.rs:675 | all | ln-applicability | pub | proposed |
| DCA-057 | crates/ln-applicability/src/ports.rs:9 | predicate_registry_revision | ln-applicability | private | proposed |
| DCA-058 | crates/ln-applicability/src/ports.rs:10 | profile_input_revision | ln-applicability | private | proposed |
| DCA-059 | crates/ln-applicability/src/ports.rs:11 | case_facts_revision | ln-applicability | private | proposed |
| DCA-060 | crates/ln-applicability/tests/applicability_capability_boundary.rs:8 | seven_capabilities_are_named | ln-applicability | private | proposed |
| DCA-061 | crates/ln-applicability/tests/applicability_capability_boundary.rs:17 | landed_spines_are_explicit | ln-applicability | private | proposed |
| DCA-062 | crates/ln-applicability/tests/applicability_capability_boundary.rs:30 | product_capabilities_remain_deferred | ln-applicability | private | proposed |
| DCA-063 | crates/ln-applicability/tests/applicability_capability_boundary.rs:47 | algebra_satisfied_cannot_mint_applicable | ln-applicability | private | proposed |
| DCA-064 | crates/ln-applicability/tests/applicability_capability_boundary.rs:61 | norm_rule_ir_is_not_product_runtime_completeness | ln-applicability | private | proposed |
| DCA-065 | crates/ln-applicability/tests/applicability_contract.rs:22 | empty_prerequisites_abstain_missing_ctv_with_trace | ln-applicability | private | proposed |
| DCA-066 | crates/ln-applicability/tests/applicability_contract.rs:46 | missing_normative_state_abstains_before_positive_decision | ln-applicability | private | proposed |
| DCA-067 | crates/ln-applicability/tests/applicability_contract.rs:63 | unresolved_transitional_version_abstains | ln-applicability | private | proposed |
| DCA-068 | crates/ln-applicability/tests/applicability_contract.rs:80 | missing_provenance_abstains | ln-applicability | private | proposed |
| DCA-069 | crates/ln-applicability/tests/applicability_contract.rs:97 | complete_prerequisites_still_abstain_protocol_unimplemented | ln-applicability | private | proposed |
| DCA-070 | crates/ln-applicability/tests/applicability_contract.rs:118 | invalid_rule_id_fails_closed | ln-applicability | private | proposed |
| DCA-071 | crates/ln-applicability/tests/applicability_contract.rs:124 | applicable_and_not_applicable_constructors_are_not_exposed_as_success_paths | ln-applicability | private | proposed |
| DCA-072 | crates/ln-applicability/tests/applicability_hostile.rs:9 | hostile_all_flags_true_cannot_mint_applicable | ln-applicability | private | proposed |
| DCA-073 | crates/ln-applicability/tests/applicability_hostile.rs:30 | first_missing_prerequisite_wins_in_stable_order | ln-applicability | private | proposed |
| DCA-074 | crates/ln-applicability/tests/norm_rule_ir_contract.rs:18 | condition | ln-applicability | private | proposed |
| DCA-075 | crates/ln-applicability/tests/norm_rule_ir_contract.rs:23 | valid_norm_rule_ir_requires_conditions_exceptions_defeaters_and_temporal_scope | ln-applicability | private | proposed |
| DCA-076 | crates/ln-applicability/tests/norm_rule_ir_contract.rs:45 | empty_conditions_fail_closed | ln-applicability | private | proposed |
| DCA-077 | crates/ln-applicability/tests/norm_rule_ir_contract.rs:53 | inverted_temporal_scope_fails_closed | ln-applicability | private | proposed |
| DCA-078 | crates/ln-applicability/tests/norm_rule_ir_contract.rs:60 | blank_condition_id_fails_closed | ln-applicability | private | proposed |
| DCA-079 | crates/ln-applicability/tests/norm_rule_ir_contract.rs:66 | unsupported_condition_kind_fails_closed | ln-applicability | private | proposed |
| DCA-080 | crates/ln-applicability/tests/norm_rule_ir_contract.rs:72 | open_ended_temporal_scope_is_allowed | ln-applicability | private | proposed |
| DCA-081 | crates/ln-applicability/tests/norm_rule_ir_contract.rs:87 | invalid_date_shape_fails_closed | ln-applicability | private | proposed |
| DCA-082 | crates/ln-applicability/tests/norm_rule_ir_hostile.rs:34 | valid_ir_with_complete_prerequisites_still_abstains | ln-applicability | private | proposed |
| DCA-083 | crates/ln-applicability/tests/norm_rule_ir_hostile.rs:73 | evaluate_with_norm_rule_records_ir_and_still_abstains | ln-applicability | private | proposed |
| DCA-084 | crates/ln-applicability/tests/norm_rule_ir_hostile.rs:109 | unsupported_exception_kind_fails_closed | ln-applicability | private | proposed |
| DCA-085 | crates/ln-applicability/tests/norm_rule_ir_hostile.rs:115 | unsupported_defeater_kind_fails_closed | ln-applicability | private | proposed |
| DCA-086 | crates/ln-applicability/tests/norm_rule_ir_hostile.rs:121 | blank_rule_revision_fails_closed | ln-applicability | private | proposed |
| DCA-087 | crates/ln-applicability/tests/norm_rule_ir_hostile.rs:127 | ir_cannot_be_built_from_only_exceptions_without_conditions | ln-applicability | private | proposed |
| DCA-088 | crates/ln-applicability/tests/predicate_algebra_contract.rs:35 | fact_required_satisfied_when_present | ln-applicability | private | proposed |
| DCA-089 | crates/ln-applicability/tests/predicate_algebra_contract.rs:45 | fact_required_abstains_when_missing | ln-applicability | private | proposed |
| DCA-090 | crates/ln-applicability/tests/predicate_algebra_contract.rs:55 | fact_forbidden_unsatisfied_when_present | ln-applicability | private | proposed |
| DCA-091 | crates/ln-applicability/tests/predicate_algebra_contract.rs:65 | compose_all_conditions_satisfied | ln-applicability | private | proposed |
| DCA-092 | crates/ln-applicability/tests/predicate_algebra_contract.rs:77 | compose_propagates_missing_fact_abstention | ln-applicability | private | proposed |
| DCA-093 | crates/ln-applicability/tests/predicate_algebra_contract.rs:91 | exception_can_carve_out_unsatisfied_condition | ln-applicability | private | proposed |
| DCA-094 | crates/ln-applicability/tests/predicate_algebra_contract.rs:109 | defeater_forces_unsatisfied_when_triggered | ln-applicability | private | proposed |
| DCA-095 | crates/ln-applicability/tests/predicate_algebra_contract.rs:125 | evaluate_with_norm_rule_and_facts_still_never_applicable | ln-applicability | private | proposed |
| DCA-096 | crates/ln-applicability/tests/predicate_algebra_hostile.rs:11 | empty_fact_set_does_not_panic_and_abstains | ln-applicability | private | proposed |
| DCA-097 | crates/ln-applicability/tests/predicate_algebra_hostile.rs:29 | invalid_fact_id_fails_closed | ln-applicability | private | proposed |
| DCA-098 | crates/ln-applicability/tests/predicate_algebra_hostile.rs:35 | missing_prerequisite_wins_before_algebra | ln-applicability | private | proposed |
| DCA-099 | crates/ln-applicability/tests/predicate_algebra_hostile.rs:71 | satisfied_algebra_cannot_mint_applicable | ln-applicability | private | proposed |
| DCA-100 | crates/ln-citation/src/adapters.rs:39 | with | ln-citation | pub | proposed |
| DCA-101 | crates/ln-citation/src/adapters.rs:46 | resolve | ln-citation | private | proposed |
| DCA-102 | crates/ln-citation/src/domain.rs:17 | parse_id | ln-citation | private | proposed |
| DCA-103 | crates/ln-citation/src/ports.rs:3 | resolve | ln-citation | private | proposed |
| DCA-104 | crates/ln-citation/tests/hc18_citation.rs:18 | official_source_resolved | ln-citation | private | proposed |
| DCA-105 | crates/ln-citation/tests/hc18_citation.rs:31 | missing_source_returns_missing | ln-citation | private | proposed |
| DCA-106 | crates/ln-citation/tests/hc18_citation.rs:39 | mirror_source_returns_invalid_not_authoritative | ln-citation | private | proposed |
| DCA-107 | crates/ln-citation/tests/hc18_citation.rs:51 | anchor_invention_rejected | ln-citation | private | proposed |
| DCA-108 | crates/ln-citation/tests/hc18_citation.rs:61 | mirror_relabel_rejected | ln-citation | private | proposed |
| DCA-109 | crates/ln-citation/tests/hc18_citation.rs:70 | policy_version_stable | ln-citation | private | proposed |
| DCA-110 | crates/ln-closure/src/adapters.rs:37 | rule_version | ln-closure | private | proposed |
| DCA-111 | crates/ln-closure/src/adapters.rs:52 | progress_count | ln-closure | private | proposed |
| DCA-112 | crates/ln-closure/src/adapters.rs:56 | queue_depth | ln-closure | private | proposed |
| DCA-113 | crates/ln-closure/src/adapters.rs:76 | rule_version | ln-closure | private | proposed |
| DCA-114 | crates/ln-closure/src/adapters.rs:80 | registered_nodes | ln-closure | private | proposed |
| DCA-115 | crates/ln-closure/src/adapters.rs:85 | dependencies_of | ln-closure | private | proposed |
| DCA-116 | crates/ln-closure/src/adapters.rs:90 | progress_count | ln-closure | private | proposed |
| DCA-117 | crates/ln-closure/src/adapters.rs:94 | queue_depth | ln-closure | private | proposed |
| DCA-118 | crates/ln-closure/src/domain.rs:19 | parse_id | ln-closure | private | proposed |
| DCA-119 | crates/ln-closure/src/domain.rs:108 | is_blocked | ln-closure | pub | proposed |
| DCA-120 | crates/ln-closure/src/domain.rs:185 | rejects_empty_node_id | ln-closure | private | proposed |
| DCA-121 | crates/ln-closure/src/domain.rs:190 | complete_is_only_complete_status | ln-closure | private | proposed |
| DCA-122 | crates/ln-closure/src/ports.rs:6 | rule_version | ln-closure | private | proposed |
| DCA-123 | crates/ln-closure/src/ports.rs:8 | registered_nodes | ln-closure | private | proposed |
| DCA-124 | crates/ln-closure/src/ports.rs:10 | dependencies_of | ln-closure | private | proposed |
| DCA-125 | crates/ln-closure/src/ports.rs:13 | progress_count | ln-closure | private | proposed |
| DCA-126 | crates/ln-closure/src/ports.rs:16 | queue_depth | ln-closure | private | proposed |
| DCA-127 | crates/ln-closure/tests/hc11_closure.rs:28 | fully_evidenced_bounded_set_is_complete_and_publication_eligible | ln-closure | private | proposed |
| DCA-128 | crates/ln-closure/tests/hc11_closure.rs:52 | missing_dependency_is_incomplete_and_blocks_publication | ln-closure | private | proposed |
| DCA-129 | crates/ln-closure/tests/hc11_closure.rs:73 | unknown_node_blocks_as_unknown | ln-closure | private | proposed |
| DCA-130 | crates/ln-closure/tests/hc11_closure.rs:92 | unbounded_fanout_blocks_publication | ln-closure | private | proposed |
| DCA-131 | crates/ln-closure/tests/hc11_closure.rs:117 | rule_version_mismatch_blocks_publication | ln-closure | private | proposed |
| DCA-132 | crates/ln-closure/tests/hc11_closure.rs:134 | progress_as_complete_claim_is_rejected | ln-closure | private | proposed |
| DCA-133 | crates/ln-closure/tests/hc11_hostile_closure.rs:27 | hostile_progress_cannot_force_complete_via_claim | ln-closure | private | proposed |
| DCA-134 | crates/ln-closure/tests/hc11_hostile_closure.rs:55 | hostile_invented_edges_for_unregistered_seed_cannot_force_complete | ln-closure | private | proposed |
| DCA-135 | crates/ln-closure/tests/hc11_hostile_closure.rs:76 | hostile_invented_empty_missing_target_still_incomplete | ln-closure | private | proposed |
| DCA-136 | crates/ln-closure/tests/hc11_hostile_closure.rs:98 | hostile_high_progress_does_not_become_completeness_on_honest_complete_path | ln-closure | private | proposed |
| DCA-137 | crates/ln-conformance/src/adapters.rs:27 | case_verdict | ln-conformance | private | proposed |
| DCA-138 | crates/ln-conformance/src/adapters.rs:49 | with | ln-conformance | pub | proposed |
| DCA-139 | crates/ln-conformance/src/adapters.rs:56 | case_verdict | ln-conformance | private | proposed |
| DCA-140 | crates/ln-conformance/src/adapters.rs:61 | all_case_ids | ln-conformance | private | proposed |
| DCA-141 | crates/ln-conformance/src/ports.rs:3 | case_verdict | ln-conformance | private | proposed |
| DCA-142 | crates/ln-conformance/src/ports.rs:4 | all_case_ids | ln-conformance | private | proposed |
| DCA-143 | crates/ln-conformance/tests/hc20_conformance.rs:5 | all_pass_yields_overall_pass | ln-conformance | private | proposed |
| DCA-144 | crates/ln-conformance/tests/hc20_conformance.rs:16 | mixed_verdicts_yield_unsupported | ln-conformance | private | proposed |
| DCA-145 | crates/ln-conformance/tests/hc20_conformance.rs:28 | fail_makes_overall_fail | ln-conformance | private | proposed |
| DCA-146 | crates/ln-conformance/tests/hc20_conformance.rs:38 | hostile_inflator_cannot_trick_app_logic | ln-conformance | private | proposed |
| DCA-147 | crates/ln-conformance/tests/hc20_conformance.rs:52 | policy_version_stable | ln-conformance | private | proposed |
| DCA-148 | crates/ln-consultant-parser/src/catalog.rs:37 | operation | ln-consultant-parser | pub | proposed |
| DCA-149 | crates/ln-consultant-parser/src/catalog.rs:41 | detail | ln-consultant-parser | pub | proposed |
| DCA-150 | crates/ln-consultant-parser/src/catalog.rs:106 | lookup | ln-consultant-parser | private | proposed |
| DCA-151 | crates/ln-consultant-parser/src/catalog_sqlite.rs:44 | is_read_only | ln-consultant-parser | pub | proposed |
| DCA-152 | crates/ln-consultant-parser/src/classifier.rs:286 | sibling_sections_do_not_leak_into_link_classifiers | ln-consultant-parser | private | proposed |
| DCA-153 | crates/ln-consultant-parser/src/classifier.rs:295 | sibling_sections_do_not_leak_into_templates | ln-consultant-parser | private | proposed |
| DCA-154 | crates/ln-consultant-parser/src/document_profile.rs:176 | sibling_section_at_same_indent_is_not_consumed | ln-consultant-parser | private | proposed |
| DCA-155 | crates/ln-consultant-parser/src/document_profile.rs:185 | missing_section_returns_empty | ln-consultant-parser | private | proposed |
| DCA-156 | crates/ln-consultant-parser/src/raw_link.rs:16 | is_internal | ln-consultant-parser | pub | proposed |
| DCA-157 | crates/ln-consultant-parser/src/raw_link.rs:21 | is_external | ln-consultant-parser | pub | proposed |
| DCA-158 | crates/ln-consultant-parser/src/raw_link.rs:26 | consid | ln-consultant-parser | pub | proposed |
| DCA-159 | crates/ln-consultant-parser/tests/c1_484_evidence_battery.rs:77 | parser_hop_pinned_canon_yields_statya_93_hyperlink | ln-consultant-parser | private | proposed |
| DCA-160 | crates/ln-consultant-parser/tests/c1_484_evidence_battery.rs:139 | constructor_hop_484_amends_44fz_statya_93 | ln-consultant-parser | private | proposed |
| DCA-161 | crates/ln-consultant-parser/tests/c1_484_evidence_battery.rs:173 | timeline_hop_empty_timeline_resolves_unknown_not_in_force | ln-consultant-parser | private | proposed |
| DCA-162 | crates/ln-consultant-parser/tests/c1_484_evidence_battery.rs:183 | timeline_hop_unknown_is_rejected_as_transition_status | ln-consultant-parser | private | proposed |
| DCA-163 | crates/ln-consultant-parser/tests/c1_484_evidence_battery.rs:197 | pitfall_guard_derive_edges_on_c1_source_inverts_amends_edge | ln-consultant-parser | private | proposed |
| DCA-164 | crates/ln-consultant-parser/tests/catalog_sqlite_test.rs:40 | path | ln-consultant-parser | private | proposed |
| DCA-165 | crates/ln-consultant-parser/tests/catalog_sqlite_test.rs:148 | sqlite_and_in_memory_share_found_missing_and_latest_contract | ln-consultant-parser | private | proposed |
| DCA-166 | crates/ln-consultant-parser/tests/catalog_sqlite_test.rs:174 | latest_edition_uses_edition_number_then_revision_then_id | ln-consultant-parser | private | proposed |
| DCA-167 | crates/ln-consultant-parser/tests/catalog_sqlite_test.rs:211 | null_edition_rank_falls_back_to_text_edition_id | ln-consultant-parser | private | proposed |
| DCA-168 | crates/ln-consultant-parser/tests/catalog_sqlite_test.rs:249 | missing_file_open_fails | ln-consultant-parser | private | proposed |
| DCA-169 | crates/ln-consultant-parser/tests/catalog_sqlite_test.rs:257 | invalid_database_open_or_query_fails | ln-consultant-parser | private | proposed |
| DCA-170 | crates/ln-consultant-parser/tests/catalog_sqlite_test.rs:276 | malformed_schema_lookup_fails | ln-consultant-parser | private | proposed |
| DCA-171 | crates/ln-consultant-parser/tests/catalog_sqlite_test.rs:292 | locator_without_document_is_decode_failure | ln-consultant-parser | private | proposed |
| DCA-172 | crates/ln-consultant-parser/tests/catalog_sqlite_test.rs:312 | adapter_connection_reports_read_only | ln-consultant-parser | private | proposed |
| DCA-173 | crates/ln-consultant-parser/tests/catalog_test.rs:8 | in_memory_catalog_lookup | ln-consultant-parser | private | proposed |
| DCA-174 | crates/ln-consultant-parser/tests/catalog_test.rs:25 | unknown_consid_returns_none | ln-consultant-parser | private | proposed |
| DCA-175 | crates/ln-consultant-parser/tests/catalog_test.rs:34 | resolve_mixed_consids | ln-consultant-parser | private | proposed |
| DCA-176 | crates/ln-consultant-parser/tests/catalog_test.rs:49 | coverage_summary_counts | ln-consultant-parser | private | proposed |
| DCA-177 | crates/ln-consultant-parser/tests/catalog_test.rs:68 | in_memory_shared_contract_found_missing_and_latest | ln-consultant-parser | private | proposed |
| DCA-178 | crates/ln-consultant-parser/tests/catalog_test.rs:88 | resolve_consids_propagates_adapter_failure | ln-consultant-parser | private | proposed |
| DCA-179 | crates/ln-consultant-parser/tests/catalog_test.rs:92 | lookup | ln-consultant-parser | private | proposed |
| DCA-180 | crates/ln-consultant-parser/tests/catalog_test.rs:104 | catalog_error_is_bounded_and_displayable | ln-consultant-parser | private | proposed |
| DCA-181 | crates/ln-consultant-parser/tests/classifier_recall_test.rs:97 | classifier_recall_on_real_amends_golden_set | ln-consultant-parser | private | proposed |
| DCA-182 | crates/ln-consultant-parser/tests/classifier_test.rs:15 | amendment_context_classified_as_amends | ln-consultant-parser | private | proposed |
| DCA-183 | crates/ln-consultant-parser/tests/classifier_test.rs:29 | citation_context_classified_as_cites | ln-consultant-parser | private | proposed |
| DCA-184 | crates/ln-consultant-parser/tests/classifier_test.rs:41 | implements_context_classified | ln-consultant-parser | private | proposed |
| DCA-185 | crates/ln-consultant-parser/tests/classifier_test.rs:53 | unknown_context_low_confidence | ln-consultant-parser | private | proposed |
| DCA-186 | crates/ln-consultant-parser/tests/classifier_test.rs:66 | classify_multiple_links | ln-consultant-parser | private | proposed |
| DCA-187 | crates/ln-consultant-parser/tests/classifier_test.rs:80 | real_44fz_classification_distribution | ln-consultant-parser | private | proposed |
| DCA-188 | crates/ln-consultant-parser/tests/document_profile_test.rs:5 | profiles_loaded_from_yaml | ln-consultant-parser | private | proposed |
| DCA-189 | crates/ln-consultant-parser/tests/document_profile_test.rs:14 | federal_law_detected | ln-consultant-parser | private | proposed |
| DCA-190 | crates/ln-consultant-parser/tests/document_profile_test.rs:25 | government_resolution_detected | ln-consultant-parser | private | proposed |
| DCA-191 | crates/ln-consultant-parser/tests/document_profile_test.rs:36 | government_directive_detected | ln-consultant-parser | private | proposed |
| DCA-192 | crates/ln-consultant-parser/tests/document_profile_test.rs:51 | departmental_act_detected | ln-consultant-parser | private | proposed |
| DCA-193 | crates/ln-consultant-parser/tests/document_profile_test.rs:62 | court_decision_detected | ln-consultant-parser | private | proposed |
| DCA-194 | crates/ln-consultant-parser/tests/document_profile_test.rs:73 | default_when_no_match | ln-consultant-parser | private | proposed |
| DCA-195 | crates/ln-consultant-parser/tests/document_profile_test.rs:81 | boost_applied | ln-consultant-parser | private | proposed |
| DCA-196 | crates/ln-consultant-parser/tests/document_profile_test.rs:89 | sibling_classifier_templates_do_not_leak_into_profiles | ln-consultant-parser | private | proposed |
| DCA-197 | crates/ln-consultant-parser/tests/edge_deriver_test.rs:4 | cl | ln-consultant-parser | private | proposed |
| DCA-198 | crates/ln-consultant-parser/tests/edge_deriver_test.rs:17 | amends_edge_direction_reversed | ln-consultant-parser | private | proposed |
| DCA-199 | crates/ln-consultant-parser/tests/edge_deriver_test.rs:36 | cites_edge_direction_forward | ln-consultant-parser | private | proposed |
| DCA-200 | crates/ln-consultant-parser/tests/edge_deriver_test.rs:51 | unknown_links_skipped | ln-consultant-parser | private | proposed |
| DCA-201 | crates/ln-consultant-parser/tests/edge_deriver_test.rs:62 | real_44fz_edge_derivation | ln-consultant-parser | private | proposed |
| DCA-202 | crates/ln-consultant-parser/tests/hyperlink_test.rs:23 | extracts_single_internal_link | ln-consultant-parser | private | proposed |
| DCA-203 | crates/ln-consultant-parser/tests/hyperlink_test.rs:37 | extracts_multiple_links_in_sequence | ln-consultant-parser | private | proposed |
| DCA-204 | crates/ln-consultant-parser/tests/hyperlink_test.rs:52 | extracts_external_link | ln-consultant-parser | private | proposed |
| DCA-205 | crates/ln-consultant-parser/tests/hyperlink_test.rs:61 | empty_xml_returns_empty | ln-consultant-parser | private | proposed |
| DCA-206 | crates/ln-consultant-parser/tests/hyperlink_test.rs:67 | link_with_multiple_text_runs | ln-consultant-parser | private | proposed |
| DCA-207 | crates/ln-consultant-parser/tests/hyperlink_test.rs:82 | real_44fz_hyperlinks | ln-consultant-parser | private | proposed |
| DCA-208 | crates/ln-consultant-parser/tests/multi_edition_test.rs:28 | parse_filename_extracts_number_and_date | ln-consultant-parser | private | proposed |
| DCA-209 | crates/ln-consultant-parser/tests/multi_edition_test.rs:37 | parse_filename_initial | ln-consultant-parser | private | proposed |
| DCA-210 | crates/ln-consultant-parser/tests/multi_edition_test.rs:45 | real_44fz_first_vs_last_edition | ln-consultant-parser | private | proposed |
| DCA-211 | crates/ln-consultant-parser/tests/multi_edition_test.rs:110 | process_edition_wrapper_uses_default_profile_path | ln-consultant-parser | private | proposed |
| DCA-212 | crates/ln-consultant-parser/tests/multi_edition_test.rs:121 | process_edition_for_path_classifies_federal_law_source | ln-consultant-parser | private | proposed |
| DCA-213 | crates/ln-consultant-parser/tests/multi_edition_test.rs:136 | process_editions_directory_passes_source_path | ln-consultant-parser | private | proposed |
| DCA-214 | crates/ln-consultant-parser/tests/observation_test.rs:7 | cl | ln-consultant-parser | private | proposed |
| DCA-215 | crates/ln-consultant-parser/tests/observation_test.rs:18 | unknown_links_collected | ln-consultant-parser | private | proposed |
| DCA-216 | crates/ln-consultant-parser/tests/observation_test.rs:32 | known_links_not_collected | ln-consultant-parser | private | proposed |
| DCA-217 | crates/ln-consultant-parser/tests/observation_test.rs:39 | sorted_by_frequency | ln-consultant-parser | private | proposed |
| DCA-218 | crates/ln-consultant-parser/tests/observation_test.rs:53 | yaml_output_contains_observations | ln-consultant-parser | private | proposed |
| DCA-219 | crates/ln-consultant-parser/tests/observation_test.rs:63 | real_44fz_observations | ln-consultant-parser | private | proposed |
| DCA-220 | crates/ln-consultant-parser/tests/scoring_test.rs:16 | and_mode_requires_all_needles | ln-consultant-parser | private | proposed |
| DCA-221 | crates/ln-consultant-parser/tests/scoring_test.rs:33 | or_mode_proportional_score | ln-consultant-parser | private | proposed |
| DCA-222 | crates/ln-consultant-parser/tests/scoring_test.rs:57 | best_score_wins | ln-consultant-parser | private | proposed |
| DCA-223 | crates/ln-consultant-parser/tests/scoring_test.rs:83 | templates_loaded_from_yaml | ln-consultant-parser | private | proposed |
| DCA-224 | crates/ln-consultant-parser/tests/scoring_test.rs:107 | real_44fz_scored_vs_single | ln-consultant-parser | private | proposed |
| DCA-225 | crates/ln-consultant-parser/tests/scoring_test.rs:142 | compatibility_wrapper_matches_empty_path_kinds | ln-consultant-parser | private | proposed |
| DCA-226 | crates/ln-consultant-parser/tests/scoring_test.rs:162 | path_aware_federal_law_boosts_winning_confidence_only | ln-consultant-parser | private | proposed |
| DCA-227 | crates/ln-consultant-parser/tests/scoring_test.rs:184 | tie_order_follows_yaml_even_after_profile_boost | ln-consultant-parser | private | proposed |
| DCA-228 | crates/ln-consultant-parser/tests/scoring_test.rs:212 | morph_variant_classifies_v_redaktsii_as_amends | ln-consultant-parser | private | proposed |
| DCA-229 | crates/ln-consultant-parser/tests/scoring_test.rs:228 | hostile_substring_noise_stays_unknown | ln-consultant-parser | private | proposed |
| DCA-230 | crates/ln-consultant-parser/tests/temporal_graph_test.rs:12 | full_44fz_temporal_evolution | ln-consultant-parser | private | proposed |
| DCA-231 | crates/ln-consultant-parser/tests/tracked_pipeline_test.rs:89 | tracked_435fz_pipeline_is_deterministic_and_bounded | ln-consultant-parser | private | proposed |
| DCA-232 | crates/ln-consultant-parser/tests/tracked_pipeline_test.rs:263 | malformed_consultant_wordml_fails_atomically_in_decode | ln-consultant-parser | private | proposed |
| DCA-233 | crates/ln-decode/src/adapters.rs:363 | decode | ln-decode | private | proposed |
| DCA-234 | crates/ln-decode/src/adapters.rs:383 | decode | ln-decode | private | proposed |
| DCA-235 | crates/ln-decode/src/adapters.rs:425 | record | ln-decode | private | proposed |
| DCA-236 | crates/ln-decode/src/adapters.rs:428 | events | ln-decode | private | proposed |
| DCA-237 | crates/ln-decode/src/adapters.rs:439 | parses_basic_wordml_with_namespaces | ln-decode | private | proposed |
| DCA-238 | crates/ln-decode/src/adapters.rs:462 | skips_non_structural_styles | ln-decode | private | proposed |
| DCA-239 | crates/ln-decode/src/adapters.rs:478 | handles_empty_document | ln-decode | private | proposed |
| DCA-240 | crates/ln-decode/src/adapters.rs:491 | skips_bindata_base64_blobs | ln-decode | private | proposed |
| DCA-241 | crates/ln-decode/src/adapters.rs:507 | style_classification | ln-decode | private | proposed |
| DCA-242 | crates/ln-decode/src/adapters.rs:516 | handles_multiple_text_runs_in_single_paragraph | ln-decode | private | proposed |
| DCA-243 | crates/ln-decode/src/adapters/garant_odt_package.rs:22 | bytes | ln-decode | pub | proposed |
| DCA-244 | crates/ln-decode/src/adapters/garant_odt_package.rs:26 | entry_count | ln-decode | pub | proposed |
| DCA-245 | crates/ln-decode/src/application.rs:43 | execute | ln-decode | pub | proposed |
| DCA-246 | crates/ln-decode/src/application.rs:106 | diagnostics | ln-decode | pub | proposed |
| DCA-247 | crates/ln-decode/src/article_body.rs:21 | level | ln-decode | pub | proposed |
| DCA-248 | crates/ln-decode/src/article_body.rs:25 | number | ln-decode | pub | proposed |
| DCA-249 | crates/ln-decode/src/article_body.rs:29 | title | ln-decode | pub | proposed |
| DCA-250 | crates/ln-decode/src/article_body.rs:35 | body | ln-decode | pub | proposed |
| DCA-251 | crates/ln-decode/src/article_body.rs:94 | number | ln-decode | pub | proposed |
| DCA-252 | crates/ln-decode/src/article_body.rs:98 | title | ln-decode | pub | proposed |
| DCA-253 | crates/ln-decode/src/article_body.rs:104 | text | ln-decode | pub | proposed |
| DCA-254 | crates/ln-decode/src/deontic.rs:22 | kind | ln-decode | pub | proposed |
| DCA-255 | crates/ln-decode/src/deontic.rs:26 | text_span | ln-decode | pub | proposed |
| DCA-256 | crates/ln-decode/src/deontic.rs:33 | negated | ln-decode | pub | proposed |
| DCA-257 | crates/ln-decode/src/domain.rs:19 | parse_id | ln-decode | private | proposed |
| DCA-258 | crates/ln-decode/src/domain.rs:81 | is_structural | ln-decode | pub | proposed |
| DCA-259 | crates/ln-decode/src/domain.rs:240 | phase | ln-decode | pub | proposed |
| DCA-260 | crates/ln-decode/src/domain.rs:244 | kind | ln-decode | pub | proposed |
| DCA-261 | crates/ln-decode/src/domain.rs:248 | byte_offset | ln-decode | pub | proposed |
| DCA-262 | crates/ln-decode/src/domain.rs:273 | try_new | ln-decode | pub | proposed |
| DCA-263 | crates/ln-decode/src/domain.rs:280 | start | ln-decode | pub | proposed |
| DCA-264 | crates/ln-decode/src/domain.rs:284 | end | ln-decode | pub | proposed |
| DCA-265 | crates/ln-decode/src/domain.rs:309 | stream | ln-decode | pub | proposed |
| DCA-266 | crates/ln-decode/src/domain.rs:313 | span | ln-decode | pub | proposed |
| DCA-267 | crates/ln-decode/src/domain.rs:330 | try_new | ln-decode | pub | proposed |
| DCA-268 | crates/ln-decode/src/domain.rs:337 | start | ln-decode | pub | proposed |
| DCA-269 | crates/ln-decode/src/domain.rs:341 | end | ln-decode | pub | proposed |
| DCA-270 | crates/ln-decode/src/domain.rs:384 | try_new | ln-decode | pub | proposed |
| DCA-271 | crates/ln-decode/src/domain.rs:409 | text | ln-decode | pub | proposed |
| DCA-272 | crates/ln-decode/src/domain.rs:413 | provider_style_id | ln-decode | pub | proposed |
| DCA-273 | crates/ln-decode/src/domain.rs:417 | style | ln-decode | pub | proposed |
| DCA-274 | crates/ln-decode/src/domain.rs:421 | source_location | ln-decode | pub | proposed |
| DCA-275 | crates/ln-decode/src/domain.rs:425 | source_format | ln-decode | pub | proposed |
| DCA-276 | crates/ln-decode/src/domain.rs:487 | try_new | ln-decode | pub | proposed |
| DCA-277 | crates/ln-decode/src/domain.rs:515 | level | ln-decode | pub | proposed |
| DCA-278 | crates/ln-decode/src/domain.rs:519 | number | ln-decode | pub | proposed |
| DCA-279 | crates/ln-decode/src/domain.rs:523 | title | ln-decode | pub | proposed |
| DCA-280 | crates/ln-decode/src/domain.rs:527 | text | ln-decode | pub | proposed |
| DCA-281 | crates/ln-decode/src/domain.rs:531 | marker_span | ln-decode | pub | proposed |
| DCA-282 | crates/ln-decode/src/domain.rs:551 | rejects_empty_payload_ref | ln-decode | private | proposed |
| DCA-283 | crates/ln-decode/src/domain.rs:556 | structural_category_is_only_accepted_kind | ln-decode | private | proposed |
| DCA-284 | crates/ln-decode/src/evaluator.rs:61 | layer | ln-decode | pub | proposed |
| DCA-285 | crates/ln-decode/src/evaluator.rs:65 | true_positives | ln-decode | pub | proposed |
| DCA-286 | crates/ln-decode/src/evaluator.rs:69 | false_positives | ln-decode | pub | proposed |
| DCA-287 | crates/ln-decode/src/evaluator.rs:73 | false_negatives | ln-decode | pub | proposed |
| DCA-288 | crates/ln-decode/src/evaluator.rs:77 | precision | ln-decode | pub | proposed |
| DCA-289 | crates/ln-decode/src/evaluator.rs:81 | recall | ln-decode | pub | proposed |
| DCA-290 | crates/ln-decode/src/evaluator.rs:85 | f1 | ln-decode | pub | proposed |
| DCA-291 | crates/ln-decode/src/golden.rs:89 | block_index | ln-decode | pub | proposed |
| DCA-292 | crates/ln-decode/src/golden.rs:98 | span | ln-decode | pub | proposed |
| DCA-293 | crates/ln-decode/src/golden.rs:146 | try_new | ln-decode | pub | proposed |
| DCA-294 | crates/ln-decode/src/golden.rs:172 | path | ln-decode | pub | proposed |
| DCA-295 | crates/ln-decode/src/golden.rs:176 | sha256 | ln-decode | pub | proposed |
| DCA-296 | crates/ln-decode/src/golden.rs:180 | byte_count | ln-decode | pub | proposed |
| DCA-297 | crates/ln-decode/src/golden.rs:184 | runtime_fingerprint | ln-decode | pub | proposed |
| DCA-298 | crates/ln-decode/src/golden.rs:199 | try_new | ln-decode | pub | proposed |
| DCA-299 | crates/ln-decode/src/golden.rs:234 | source | ln-decode | pub | proposed |
| DCA-300 | crates/ln-decode/src/golden.rs:238 | provider | ln-decode | pub | proposed |

*(Export capped at 300 of 1,811 filtered rows; the remainder is regenerable with the same query minus the cap and is deliberately not transcribed.)*

## Reuse candidates

Same-name `Function` query across `crates/` (≥2 distinct files, generic names excluded, `LIMIT 50`, ordered by file count then name). This is a **proposal list, not a merge list**: seams are documented, no code is merged in this milestone. Sanctioned reuse home is `ln-testkit` (already centralizes 25 port-contract suites). Rows touching `ln-hcNN-runner` default to **intentional-shape** (per-HC hostile proofs share shape by design); consolidation there is a planner decision, not an audit finding. Pinned exception: same-named test helpers across the `ln-kb-ontology` suites are individually pinned (MEM1054-class).

| # | Name | Files | Crates (files) | Shape note |
|---|---|---|---|---|
| 1 | cc | 23 | ln-temporal (8), ln-kb-ontology (14), ln-consultant-parser (1) | cross-crate test helper — proposal |
| 2 | request | 21 | ln-decode (11), ln-replay (2), ln-publish (1), ln-query (1), ln-storage (1), ln-testkit (1), ln-applicability (1), ln-hc05-runner (1), ln-hc14-runner (1), ln-hc15-runner (1) | partly hc-runner — intentional-shape there; rest proposal |
| 3 | parse_id | 20 | one per crate: ln-accelerate, ln-admission, ln-applicability, ln-citation, ln-closure, ln-decode, ln-diagnostic, ln-dispose, ln-gate, ln-identity, ln-inventory, ln-observe, ln-projection, ln-promote, ln-publish, ln-query, ln-relation, ln-replay, ln-temporal, ln-work | per-capability domain twin (hexagonal layout) — likely intentional-shape; proposal only if byte-identical |
| 4 | render_verdict | 20 | ln-hc01…ln-hc20-runner (1 each) | intentional-shape (hc-runner) |
| 5 | render_receipt | 15 | ln-hc01…ln-hc15-runner (1 each) | intentional-shape (hc-runner) |
| 6 | req | 12 | ln-admission (2), ln-accelerate (1), ln-citation (1), ln-projection (1), ln-publish (1), ln-query (1), ln-hc12/13/16/17/18-runner (5) | partly hc-runner — intentional-shape there |
| 7 | unknown_scenario_exits_2 | 12 | ln-hc04…ln-hc15-runner `tests/cli_contract.rs` (1 each) | intentional-shape (hc-runner) |
| 8 | block | 11 | ln-decode (10), ln-product-cli (1) | intra-crate test helper — proposal |
| 9 | put | 11 | ln-promote (3), ln-accelerate (2), ln-gate (2), ln-identity (2), ln-publish (2) | port/adapter seam — port-contract surface, do not merge |
| 10 | kind | 9 | ln-decode (5), ln-applicability (1), ln-kb-ontology (1), ln-temporal (1) | accessor shape — proposal |
| 11 | try_new | 9 | ln-storage (3), ln-decode (2), ln-applicability (1), ln-kb-ontology (1), ln-query (1), ln-temporal (1) | constructor shape — proposal |
| 12 | block_of | 8 | ln-kb-ontology (8) | intra-crate test helper — proposal |
| 13 | consultant_export_dir | 8 | ln-consultant-parser (3), ln-product-cli (2), ln-kb-ontology (2), ln-decode (1) | test env helper — ln-testkit candidate |
| 14 | act | 7 | ln-temporal (6), ln-kb-ontology (1) | cross-crate test helper — proposal |
| 15 | contract_embeds_as_data_and_pins_schema_identity | 7 | ln-kb-ontology (7) | intra-crate test helper (pinned set) |
| 16 | contract_lifecycle_stays_proposed_and_non_authoritative | 7 | ln-kb-ontology (7) | intra-crate test helper (pinned set) |
| 17 | contract_marker_line | 7 | ln-kb-ontology (7) | intra-crate test helper (pinned set) |
| 18 | entity_blocks | 7 | ln-kb-ontology (7) | intra-crate test helper (pinned set) |
| 19 | entity_key_line_indices | 7 | ln-kb-ontology (7) | intra-crate test helper (pinned set) |
| 20 | entity_scalar | 7 | ln-kb-ontology (7) | intra-crate test helper (pinned set) |
| 21 | events | 7 | ln-decode (2), ln-observe (2), ln-kb-ontology (1), ln-storage (1), ln-temporal (1) | port/adapter seam — proposal, testkit candidate |
| 22 | required_field_keys | 7 | ln-kb-ontology (7) | intra-crate test helper (pinned set) |
| 23 | section_between | 7 | ln-kb-ontology (7) | intra-crate test helper (pinned set) |
| 24 | top_level_dash_items | 7 | ln-kb-ontology (7) | intra-crate test helper (pinned set) |
| 25 | embed | 6 | ln-storage (3), ln-query (2), ln-product-cli (1) | port/adapter seam — proposal |
| 26 | every_entity_carries_its_required_fields | 6 | ln-kb-ontology (6) | intra-crate test helper (pinned set) |
| 27 | inline_bracket_items | 6 | ln-kb-ontology (6) | intra-crate test helper (pinned set) |
| 28 | lookup | 6 | ln-consultant-parser (3), ln-relation (2), ln-promote (1) | cross-crate port method — proposal |
| 29 | path | 6 | ln-testkit (2), ln-consultant-parser (1), ln-decode (1), ln-kb-ontology (1), ln-replay (1) | test fixture helper — ln-testkit candidate |
| 30 | query | 6 | ln-storage (4), ln-query (2) | port/adapter seam — proposal |
| 31 | contract_without_non_claims | 5 | ln-kb-ontology (5) | intra-crate test helper (pinned set) |
| 32 | emit | 5 | ln-diagnostic (3), ln-observe (2) | cross-crate port method — proposal |
| 33 | exactly_one_embed_exists_in_this_suite | 5 | ln-kb-ontology (5) | intra-crate test helper (pinned set) |
| 34 | execute | 5 | ln-projection (2), ln-decode (1), ln-observe (1), ln-query (1) | cross-crate port method — proposal |
| 35 | finish | 5 | ln-admission (1), ln-applicability (1), ln-closure (1), ln-publish (1), ln-replay (1) | per-capability application twin — likely intentional-shape |
| 36 | fixture_path | 5 | ln-decode (4), ln-query (1) | test fixture helper — ln-testkit candidate |
| 37 | group | 5 | ln-decode (2), ln-kb-ontology (2), ln-product-cli (1) | cross-crate test helper — proposal |
| 38 | header_block | 5 | ln-kb-ontology (5) | intra-crate test helper (pinned set) |
| 39 | marker | 5 | ln-kb-ontology (5) | intra-crate test helper (pinned set) |
| 40 | neighbor_contract_tokens_never_mint_entity_keys | 5 | ln-kb-ontology (5) | intra-crate test helper (pinned set) |
| 41 | non_claims_carry_the_boundary_disclaimers | 5 | ln-kb-ontology (5) | intra-crate test helper (pinned set) |
| 42 | observe | 5 | ln-observe (3), ln-admission (2) | cross-crate port method — proposal |
| 43 | proposal | 5 | ln-kb-ontology (5) | intra-crate test helper (pinned set) |
| 44 | provenance | 5 | ln-kb-ontology (4), ln-temporal (1) | cross-crate domain twin — proposal |
| 45 | rid | 5 | ln-temporal (2), ln-closure (2), ln-hc11-runner (1) | partly hc-runner — intentional-shape there |
| 46 | span | 5 | ln-decode (5) | intra-crate accessor — proposal |
| 47 | strip_comment | 5 | ln-kb-ontology (3), ln-decode (2) | cross-crate utility — strongest ln-testkit candidate |
| 48 | text_span | 5 | ln-decode (5) | intra-crate accessor — proposal |
| 49 | top_level_row | 5 | ln-kb-ontology (5) | intra-crate test helper (pinned set) |
| 50 | committed_count | 4 | ln-promote (4) | intra-crate port/adapter seam — proposal |

## Disposition protocol (inherited from assessment/21)

Closing (dispositioning) any DCA row requires, simultaneously:

1. **frozen revision** — the row is judged against the pinned SHA in `## Frozen HEAD` (path:line anchors are Frozen-HEAD anchors);
2. **tracked evidence** — multi-channel proof recorded in a tracked artifact (graph + rustc `dead_code` + `rg`, R038; `gitnexus_impact` upstream spot check), never a truncated log digest or `.gsd/exec` transcript;
3. **preserved non-claims** — the row's non-claims survive closure (what the closure does *not* prove).

Removal (Tier-0) additionally requires all six keep-vs-remove criteria: zero inbound edges; zero rustc/`rg` corroboration; not in `ports.rs`/`adapters.rs` (or port has zero adapters and no port-contract references); not `pub` API consumed elsewhere; not a test fixture / entry point / macro-referenced item; not named by process gates (governor, preflight, `verify-adr-conformance.py`, verification matrix). Empty set is a valid outcome. Reuse seams are documented, never merged, in this milestone.

## Non-claims (preserved)

- This register is `[bounded]` inventory. It does **not** prove any listed symbol removable, dead, or safe to delete; `proposed` is a funnel stage, not a verdict.
- No product-behavior, legal-correctness, corpus-completeness, or retrieval-quality claim follows from this file. Dead-code hygiene is process evidence only and moves no lifecycle tag.
- Zero-inbound-in-graph ≠ dead: trait dispatch, macros/derives, `#[test]` harness entry points, re-exports, and process-gate name references are invisible to CALLS/USES/ACCESSES edges.
- Counts are pinned to the frozen index (HEAD `52314d7`); any later commit invalidates the numbers until re-derived. Research-era numbers (stale index `c187e4c`) are comparators only.
- Reuse rows are duplication observations, not refactor approvals; behavior-preserving merges need their own planner decision and tests.
