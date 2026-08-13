# Capability Promotion Board (L_capability)

**Lifecycle:** `[proposed]` process inventory  
**Authority companions:** ADR-0015, ADR-0024 §9a,  
`prd/architecture/review-cases/continuity-contract.md` (D153),  
`prd/architecture/temporal-semantic-gap-register.md`  
**Non-authority:** this board does not close TSG rows, promote ADR lifecycle,
complete GSD work, accept review findings, or claim product/legal readiness.

## 1. Purpose

L_review residual closeouts at ceiling `spine` (and similar) left **all TSG rows
active** while process residual reached `product_open = 0`. Without an explicit
**promotion board**, cold readers collapse:

```text
finding closed  →  capability done  →  product ready
```

This board is the **L_capability FSM surface**: ladder step per gap, current
progress ceiling, B3 non-closure links, and the only allowed path to move a
TSG row toward closure.

## 2. Capability ladder (states)

Every TSG row advances only along:

```text
S0 ownership_adr_proposed
  → S1 design_spine
  → S2 implementation_spine
  → S3 bounded_runtime
  → S4 representative_evidence
  → S5 human_scope_acceptance   (when legal/semantic judgment required)
  → S6 closed_bounded | closed_validated
```

| State | Meaning | Typical proof class |
|---|---|---|
| S0 | Owning ADR/decision exists; capability named | docs / design |
| S1 | Design taxonomy/IR/inventory; fail-closed non-claims | design |
| S2 | Structural planner/ports/algebra without product decision | implementation |
| S3 | Offline/synthetic + hostile contracts; no corpus claim | implementation |
| S4 | Representative fixtures/metrics under non-claims | evidence |
| S5 | Human acceptance on governing surface | evidence + human |
| S6 | TSG row closed under register disposition rules | class-matched |

**Rules:**

1. No skip of proof class required by the row’s closure trigger.  
2. S1/S2 **never** alone move status to `closed-*`.  
3. L_review `closed` @ `spine` maps at most to **S1 or S2** progress.  
4. ADR lifecycle move is **B4**, after S4/S5 as applicable — not automatic.  
5. Governor/process green is not a ladder transition.

## 3. Promotion packet (required to advance)

To propose advance from Sn → Sn+1 (or to S6), record a packet with:

| Field | Content |
|---|---|
| `tsg_id` | e.g. TSG-003 |
| `from_state` / `to_state` | ladder states |
| `proof_class` | docs \| design \| implementation \| evidence \| process |
| `tested_revision` | 40-hex git rev or verification source snapshot |
| `evidence_anchors` | repo-relative paths |
| `hostile_path` | one fail/diagnostic proof |
| `non_claims` | mandatory |
| `human_actor` | when to_state ≥ S5 or row requires judgment |
| `b3_link` | L_review finding ids or `none` |

Until schema fields exist, packets live as:

- gap-register disposition / non-closure updates, and/or  
- rows in §5 history below, and/or  
- review verification non_claims + completed_scope naming ceiling.

## 4. Forbidden promotions

| Jump | Why forbidden |
|---|---|
| S1 inventory → S6 closed | proof class mismatch |
| algebra Satisfied → Applicable (S6 for TSG-006) | ADR-0023 product boundary |
| CTV structural plan → amendment correctness | ADR-0017 non-claim |
| L_review closed → TSG closed | lifecycle collapse |
| Governor pass → S6 | process ≠ capability |
| Docs-only edit of this board → S6 | board is inventory |

## 5. Current board (RC11/RC12 spine wave)

**As-of git head context:** process residual RC11+RC12 product_open empty;
M167 complete (design IR); dual-truth lag resolved.

| TSG | Ladder now | Progress notes | L_review B3 / non-closure | Next honest step |
|---|---|---|---|---|
| TSG-001 | S0–S1 partial | vocabulary/glossary surfaces exist; not complete controlled vocabulary | gap register active | complete crosswalk + drift checks |
| TSG-002 | **S1** | `LegislativeEventKind` design taxonomy | RC11-F07 non-closure | executable events + hostile substitution (S2/S3) |
| TSG-003 | **S3** | planner + bounded-runtime `apply_industrial_op` + structural event log (offline/hostile) | RC11-F08 non-closure; not corpus | representative amendment fixtures + human scope (S4/S5); still not legal CTV product |
| TSG-004 | **S3** | force resolver + `join_force_with_membership` (membership context; membership≠InForce) | RC11-F09 non-closure | CTV text edition join + multi-dim provenance + corpus (S4) |
| TSG-005 | **S1–S2** | NormRule IR + fail-closed validation (M167/F04a); not full rule graph | RC12-F05 + F04a non-closure | provenance graph + promotion tests; **not** product Applicable |
| TSG-006 | **S1–S2** | abstention kernel + predicate algebra spine; top-level Abstain only | RC12-F05 / F04b non-closure | product CaseFacts + real cases before any Applicable (S3–S5) |
| TSG-007 | S0 | ADR-0019 `[proposed]` | — | design types + hostile delegation |
| TSG-008 | S0 | ADR-0020 `[proposed]` | — | coverage taxonomy + ports |
| TSG-009 | S0 | ADR-0021 `[proposed]` | — | typed transitional vs risk split |
| TSG-010 | S0 | ADR-0022/0023; F13 deferred | RC11-F13 deferred | after core applicability path |
| TSG-011 | S0–S1 | five-clock safety ≠ algebra; deferred inventory | RC11-F06 non-closure | correction ledger + rebuild equivalence |
| TSG-012 | S0 | gap named | — | owner decision + resolver |
| TSG-013 | **S3** | apply + versioned membership fold → StructuralAst (projection); not CTV text / Expression bind | RC11-F08 non-closure | Expression bind + calendar effect + fixtures (S4) |
| TSG-014 | S0 | partial paper shapes | — | port-tied schemas |
| TSG-015 | S0 | paper golden catalog | — | executable promotion per case |
| TSG-016 | S0–S1 | InMemory scoring `[bounded]` | — | real 1024d corpus + metrics |
| TSG-017 | **S0–S1** | Review 4 assembly design: EditionOracle vs AmendmentEvent; YAML corpus roles / evidence classes / `assembly_fsm` | Review 4 L0; not a packet | classify XML + one-fixture propose/fold/oracle-diff (S2/S3); still not 44-ФЗ history |

### Promotion history (append-only)

| Date | TSG | Transition | Evidence (short) | Actor/process |
|---|---|---|---|---|
| 2026-08-13 | TSG-002 | → S1 | RC11-F07 design taxonomy | review ceremony |
| 2026-08-13 | TSG-003/013 | → S2 | RC11-F08 structural ops | review ceremony |
| 2026-08-13 | TSG-004 | → S1 | RC11-F09 dimensions | review ceremony |
| 2026-08-13 | TSG-005 | → S1–S2 | M167 + F04a IR | GSD skip-waiver + review |
| 2026-08-13 | TSG-006 | → S1–S2 | F04b algebra + F05 inventory | review ceremony |
| 2026-08-13 | TSG-011 | → S0–S1 | F06 five-clock vs algebra | review ceremony |
| 2026-08-13 | TSG-003 | S2 → **S3** | `apply_industrial_op` + `StructuralEventLog` offline/hostile | product TDD slice |
| 2026-08-13 | TSG-013 | S2 → **S2–S3** | membership mutation under apply | product TDD slice |
| 2026-08-13 | TSG-017 | → **S0–S1** | Review 4 L0 + ADR-0013/16/17/19 design inventory | review intake |

No row advanced to S6 in the spine wave; S3 apply landed later (see history).

## 5b. KB ontology draft (O1)

Parallel inventory (not TSG S6): `prd/architecture/kb-ontology-requirements.md`,
`kb-ontology-l1-l3-draft.md`, `kb-ontology-projection-contract.json`.
FSM current is `fsm.current` in `kb-ontology.yaml`; open dep KBO-R013.
Governor check `kb-ontology-draft` is structural only.

| Date | Req | Change | Proof |
|---|---|---|---|
| 2026-08-13 | KBO-R025 | YAML FSM catalog | `kb-ontology.yaml` drives states/kinds/levels |
| 2026-08-13 | KBO-R026 | decode aliases | YAML Statya→statya; unknown token fail-closed |
| 2026-08-13 | KBO-R027 | catalog kinds | node/edge/presence tokens from YAML; no Rust enums |
| 2026-08-13 | KBO-R028 | closed vocab coverage | Governor compares Rust enums to YAML tables |
| 2026-08-13 | KBO-R029 | composition lift | product-cli HierarchyNode → YAML alias; empty registry Unknown |
| 2026-08-13 | KBO-R030 | YAML decode prefixes | Статья/Глава/§ live in YAML; inspect count unchanged |
| 2026-08-13 | KBO-R031 | calendar ordinal | ISO legal_act_effect_day → civil-day ordinal; Feb 30 fail-closed |
| 2026-08-13 | KBO-R032–R040 | Review 4 assembly vocabulary | AmendmentEvent facets, EditionOracle, corpus roles, assembly_fsm; readiness FSM unchanged |
| 2026-08-13 | KBO-R034 | assembly `S_ingest` | YAML `corpus_role_signals` classify path/title; Unknown if unmatched |
| 2026-08-13 | KBO-R041 | assembly `S_propose` | stack propose from YAML ranks; inspect 435-ФЗ 0 attach / 22 quarantine |
| 2026-08-13 | KBO-R042 | scoped YAML registry | 435-FZ statya 1–22 Bound by path needle; forest roots, 0 attach |
| 2026-08-13 | KBO-R042 | 402-FZ chapter tree | 4 glava + 33 statya Bound; inspect drafts attach > 0; not a log write |
| 2026-08-13 | KBO-R043 | assembly `S_admit` | two-parent / cycle / self-parent quarantine gate; 402-FZ 33 admitted 0 conflict |
| 2026-08-13 | KBO-R044 | assembly `S_commit`/`S_fold` | admit → commit → fold → StructuralAst; 402-FZ 4 roots / 37 nodes; fold canon wired |
| 2026-08-14 | KBO-R045..R050 | Review 5 gaps | edition_ast_at, resolve_CTV, oracle diff, macro/micro P9, cross-act S1, ELI mapping |
| 2026-08-14 | KBO-R045 | assembly `S_fold` | edition_ast_at unifies 3 canons; 3 tests green; FSM S_commit→S_fold |

## 6. Operator cycle (capability-only)

```text
1. Pick one TSG row (prefer debt-first: CTV S3 or NormativeState S2/S3; not Applicable first)
2. Declare from_state / to_state and proof package
3. B1 delivery intent (prefer delivery:gsd:…)
4. Implement only that ladder step
5. Verify class-matched + hostile path
6. B3: update this board history + gap-register non-closure or disposition
7. Inventory: L_review residual may close at ceiling without S6
8. Never mark TSG closed without §3 disposition rules in gap register
```

## 7. Relationship to Governor

Advisory check `capability-promotion-board` verifies:

- this file exists and declares non-authority;  
- every `TSG-XXX` active in the gap register is named in §5 board table;  
- does **not** prove semantic correctness of ladder states.

## 8. Non-claims

- Board presence is not product readiness.  
- Ladder S1/S2 is not legal validation.  
- Completing M167 is not TSG-005/006 closure.  
- RC residual closed is not S6.  
- This file is not a backlog commitment or GSD roadmap.
