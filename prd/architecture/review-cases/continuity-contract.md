# Review / Delivery / Capability Continuity Contract

**Lifecycle:** `[proposed]` process contract  
**Authority:** ADR-0024, ADR-0015, `prd/ARCHITECTURE.md`  
**Non-authority:** this note does not accept findings, close TSG rows, complete
GSD work, promote ADR lifecycle, or claim product/legal readiness.

## 1. Purpose

RC11/RC12 process residual waves closed many findings at **spine / inventory /
docs hygiene** ceilings. Without an explicit multi-lifecycle model, cold readers
smooth “finding closed” into “capability done” or “milestone done”.

This contract defines **three orthogonal lifecycles**, **closure ceilings**,
**bridge obligations**, **forbidden jumps**, and the **operator cycle** that keep
stage transitions continuous without laundering authority.

## 2. Three lifecycles (must not collapse)

| ID | Name | Owns | Terminal success means |
|---|---|---|---|
| **L_review** | Review Case residual | ADR-0024 packets, disposition, execution_link, verification, residual class | Finding residual is terminal/closed/deferred **for a declared ceiling** |
| **L_delivery** | Delivery execution | GSD milestone/slice/task Attempts (or explicit non-GSD work) | Attempt verified under GSD rules |
| **L_capability** | Semantic capability | TSG register + owning ADR lifecycle + ADR-0015 proof class | TSG row satisfied under its closure trigger; ADR may propose lifecycle move |

### Hard separation rules

1. Success on one lifecycle **never** implies success on another.
2. A bridge event/record may **cite** the other lifecycle; it may not **copy** or
   **control** the other lifecycle’s state machine.
3. `review-case inventory` residual `closed` is **L_review only**.
4. Governor green is structural honesty for process surfaces, not L_capability
   acceptance and not L_delivery completion.

## 3. Closure ceilings (L_review honesty)

Every accepting verification for a product/design/impl finding must imply exactly
one **closure ceiling** for the completed scope:

| Ceiling | Allowed completed scope | Must remain open elsewhere |
|---|---|---|
| `spine` | design taxonomy, fail-closed inventory, structural planner, IR types, pure algebra without product decision | TSG runtime/evidence rows; ADR still `[proposed]` unless separately moved |
| `bounded_runtime` | offline/synthetic ports+hostile contracts, no representative corpus claim | real-corpus / human legal-scope rows |
| `evidence` | representative fixtures + metrics under declared non-claims | human acceptance when required; lifecycle promotion |
| `accepted` | human scope acceptance recorded on governing surface | still not automatic ADR/`[validated]` without promotion rules |

### Mapping examples (RC11/RC12 wave)

| Finding | Actual ceiling used | Explicit residual outside L_review |
|---|---|---|
| RC11-F06 | `spine` | temporal algebra / TSG-011 still active |
| RC11-F07 | `spine` | TSG-002 executable events |
| RC11-F08 | `spine` (structural ops) | TSG-003/013 event-sourced CTV + corpus |
| RC11-F09 | `spine` | TSG-004 NormativeState resolver |
| RC11-F04a | `spine` (IR) | positive applicability |
| RC11-F04b | `spine` (algebra) | Applicable/NotApplicable deferred |
| RC12-F05 | `spine` (capability inventory) | TSG-005/006 product path |
| RC12-F18 | docs/process (not product ceiling) | n/a product |

If ceremony text claims a higher ceiling than evidence supports, the verification
is dishonest even if residual class becomes `closed`.

## 4. Bridge contracts

Bridges are **obligations on human ceremony and durable notes**, not automatic
promotions.

| Bridge | From → To | Required content | Failure mode if skipped |
|---|---|---|---|
| **B1** Disposition → delivery intent | L_review → L_delivery | finding_id; work needed? ; delivery_ref **or** `delivery:none` + reason | work happens invisibly; residual lies |
| **B2** Delivery evidence → execution_linked | L_delivery → L_review | opaque external_ref; execution status; source_revision; human actor | finding stuck open or false implemented |
| **B3** Verification → capability register | L_review → L_capability | TSG/ADR ids; close **or** explicit non-closure note; ceiling | semantic laundering (“closed” read as TSG done) |
| **B4** Capability proof → ADR lifecycle proposal | L_capability → ADR | class-matched proof package; human accept for legal-scope | silent lifecycle promotion |
| **B5** Drift → reopen/risk | HEAD/surfaces → L_review | when claimed surface moves past tested_revision for ceiling ≥ `bounded_runtime` | stale closed residual |

### Minimal durable recording (P1, docs-first)

Until schema fields exist, bridges MUST appear in at least one of:

- verification `non_claims` + `completed_scope` (ceiling language);
- gap-register non-closure note for the TSG ids;
- session triage / continuity log line with finding_id, ceiling, delivery_ref or
  `delivery:none`, TSG ids.

Schema-level bridge fields are a later bounded extension; absence of schema
fields does **not** waive B1–B3 for new ceremonies.

## 5. Forbidden jumps

| Jump | Why forbidden |
|---|---|
| disposition → residual closed without events | erases ledger continuity |
| `spine` verification → TSG status closed | class/ceiling mismatch |
| algebra Satisfied → Applicable | ADR-0023 product boundary |
| CTV structural plan → legal amendment correctness | ADR-0017 non-claim |
| Governor pass → product ready | process ≠ product |
| inventory `next_admissible_events` → auto event | suggestions only |
| deferred unpark without adoption decision | roadmap laundering |
| GSD complete ↔ review closed without B1/B2 | dual lifecycle drift |
| already_satisfied without satisfying surface+revision | terminal laundering |

## 6. Operator cycle (continuous stage transitions)

```text
1. Register packet (L0 source immutable)
2. Normalize findings + spans (projection only)
3. Human disposition (class + proof_class + non-claims)
4. If work required:
   a. declare closure_ceiling
   b. B1: delivery_ref or delivery:none
   c. implement only that ceiling
   d. B2: execution_linked
   e. verification_recorded (class-matched, tested_rev, anchors, non-claims)
   f. B3: TSG close OR non-closure note
5. inventory: residual must match intent
6. Governor: structural only
7. Later review: delta reaffirm / refine / reopen / supersede
```

### Deferred park / unpark

- **Park:** disposition `deferred` + residual `deferred_parked` + reason + what
  adoption looks like.
- **Unpark:** new disposition citing **adopted** roadmap/ADR/decision id; then
  re-enter step 4. Chat agreement alone is insufficient.

### Reopen matrix (minimum)

Reopen (or record continuity risk) when:

- source hash/span no longer matches;
- later review contradicts closed ceiling;
- re-verification fails;
- stronger claim is attempted without new proof;
- for ceiling ≥ `bounded_runtime`, claimed surfaces advanced past tested_revision
  without re-verify (B5).

## 7. Capability ladder (L_capability only)

Operational board (states, current TSG progress, promotion history):
`prd/architecture/capability-promotion-board.md`.

Default order for ontology/runtime depth (debt-first):

```text
ownership ADR [proposed]
  → design spine
  → implementation spine
  → bounded runtime (synthetic + hostile)
  → representative evidence
  → human scope acceptance (when required)
  → ADR lifecycle move / [bounded]|[validated] only with promotion rules
```

Review findings may close at any early step **only** with ceiling + B3.

Recommended depth order after continuity contract:

1. CTV beyond structural planner (TSG-003/013)  
2. NormativeState resolver (TSG-004)  
3. Positive applicability only after prerequisites + real cases (TSG-006)

## 8. Continuity observability checklist

Cold-reader must answer per finding without chat memory:

1. residual class and operator stage?  
2. disposition / execution / verification?  
3. closure ceiling of last passing verification?  
4. delivery_ref or delivery:none?  
5. TSG/ADR refs and whether closed or non-closed?  
6. tested_revision?  
7. next admissible events and what is still forbidden?

P1 docs-first surfaces: inventory + this contract + gap register + session triage.  
P2+ may add inventory columns / schema fields without changing authority rules.

## 9. Relationship to RC11/RC12 end state

As of the continuity adoption wave:

- L_review product_open = 0 for RC11+RC12  
- L_delivery may still show GSD lag (e.g. historical M167 dual-truth risk)  
- L_capability still has active TSG-002…016  

That split is **expected and healthy** if B3 non-closure notes remain visible.

### 9.1 GSD bridge (P2)

B1/B2 details, dual-truth classes, and the M167 / RC11-F04a incident register:
`prd/architecture/review-cases/gsd-review-bridge.md`.

Default for that incident: **DT-lag** with reconstructed
`B1=delivery:out-of-band` — product/review evidence ahead of GSD Attempts.
Do not fake `gsd_task_complete` or rewrite `.gsd` state to erase the lag.

## 10. Non-claims

- This contract is not product readiness, legal correctness, or TSG closure.
- It does not adopt RC12-F19 / M166–M176 proposals.
- It does not un-defer RC11-F13.
- It does not authorize Applicable/NotApplicable.
- Documentation of bridges is not a substitute for later schema/engine enforcement.
- ADR-0024 remains `[proposed]` until its own bounded runtime criteria say otherwise.

## 11. Adoption record

- Human direction: accept three-lifecycle continuity work after RC11/RC12 residual
  wave (session continuation).
- Living companions: ADR-0024 amendment section, `prd/ARCHITECTURE.md`, this file,
  gap-register disposition cross-link, review-cases README operator section.
