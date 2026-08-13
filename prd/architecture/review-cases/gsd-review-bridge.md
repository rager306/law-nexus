# GSD ↔ Review Case Bridge Policy (P2)

**Lifecycle:** `[proposed]` process contract  
**Authority companions:** ADR-0024 §9 / §9a,  
`prd/architecture/review-cases/continuity-contract.md` (D153)  
**Non-authority:** does not complete GSD milestones, accept findings, close TSG
rows, or claim product readiness.

## 1. Problem

Two honest systems can disagree without either being “wrong”:

| System | Truth it owns |
|---|---|
| **L_review** | residual after disposition / execution_linked / verification |
| **L_delivery** | GSD milestone/slice/task Attempt lifecycle |

If product code lands and a Review Case ceremony closes a finding while GSD
tasks remain `pending` without Attempts, cold readers see **dual-truth**:

```text
L_review:  finding closed (spine)
L_delivery: milestone still active / tasks pending
L_capability: TSG still active (expected for spine)
```

Fabricating GSD completion (direct STATE/db edits, fake Attempts, or
`gsd_task_complete` without a running Attempt) is **forbidden**. It recreates
the registry corruption path already rejected in M161–M166 reconcile work.

## 2. Bridge vocabulary (B1 / B2)

### 2.1 B1 — delivery intent (at or before work)

Every accepting disposition that expects work MUST record one delivery intent:

| Intent | Meaning | When to use |
|---|---|---|
| `delivery:gsd:<MID>[/S##[/T##]]` | Work is planned to run under GSD | Normal path |
| `delivery:out-of-band` | Work runs outside GSD Attempts (hot-fix / review wave) | Exception; must name why |
| `delivery:none` | No implementation work (docs already_satisfied, duplicate, reject, defer park) | Terminal/process dispositions |

Recording surfaces (docs-first, until schema fields exist):

- disposition or execution rationale;
- session triage / this bridge register;
- opaque `execution_linked.to` may cite `gsd:…` as **reference only**.

`gsd:…` inside `execution_linked.to` is an **opaque pointer**, not GSD mutation
and not proof that Attempts completed.

### 2.2 B2 — delivery evidence → execution_linked

| If B1 was… | B2 evidence must include |
|---|---|
| `delivery:gsd:…` | Prefer Attempt/result identity when available; else git rev + honest lag note |
| `delivery:out-of-band` | git rev + paths + tests; **must** say GSD not authoritative for this unit |
| `delivery:none` | No execution_linked required (or `not_required`) |

### 2.3 Ordering rules

1. Prefer **GSD-first** for new product slices: plan → Attempt → code → B2 → L_review verify.
2. **Review-first / out-of-band** is allowed for residual waves only when B1 is
   explicit `delivery:out-of-band` and dual-truth is registered (this file).
3. Closing L_review never closes L_delivery.
4. Completing L_delivery never closes L_review without B2 + verification.
5. Neither closes L_capability without TSG triggers (B3).

## 3. Dual-truth classes

| Class | Definition | Allowed resolution |
|---|---|---|
| **DT-lag** | Product/review evidence ahead of GSD markers | Keep visible; complete GSD only via real Attempts **or** leave active with bridge note |
| **DT-orphan-gsd** | GSD unit active; no review finding and no product evidence | Plan work or cancel/skip via GSD tools with reason |
| **DT-orphan-review** | Finding open; no B1 | Add B1 or disposition terminal |
| **DT-conflict** | GSD claims complete; review verification failed/stale | Reopen delivery or mark review stale; do not silent-green |

Silent resolution (delete history, rewrite STATE, invent Attempts) is always
**DT-corruption** and is rejected.

## 4. Incident register: M167-odlgt8 / RC11-F04a

### 4.1 Facts

| Axis | State |
|---|---|
| GSD milestone | `M167-odlgt8` NormRule IR fail-closed design spine — **active** |
| GSD slices | S01/S02/S03 **pending**, task done counts **0** (no durable Attempts) |
| Product evidence | NormRule IR in `ln-applicability` at git `1403294…`; tests `norm_rule_ir_*` |
| L_review | `RC11-F04a` **closed** (design, ceiling `spine`); exec refs cite `gsd:M167-odlgt8` opaquely |
| L_capability | TSG-005 / positive applicability **still open** (expected) |

### 4.2 Classification

```text
class: DT-lag
B1 effective (reconstructed): delivery:out-of-band
  reason: residual wave implemented IR under review ceremony before GSD Attempts ran
B2: git:1403294 + RC11-F04a verification_recorded (design, tested_revision 1403294…)
L_delivery debt: M167 registry not Attempt-complete
```

### 4.3 What this does **not** mean

- Does **not** mean M167 GSD milestone is complete.
- Does **not** authorize `gsd_task_complete` without Attempts.
- Does **not** close F04b, Applicable/NotApplicable, or TSG-006.
- Does **not** make opaque `gsd:M167-odlgt8` in execution_linked a GSD status write.

### 4.4 Allowed next moves for M167 (human chooses one)

| Option | Action | Effect |
|---|---|---|
| **A. Honest lag (default now)** | Keep M167 active; this register + roadmap note declare DT-lag | Cold-reader sees split; no fake complete |
| **B. Engine-true close** | Run real GSD Attempts/replays that re-verify existing IR scope only; then complete tasks/slices/milestone via tools | L_delivery catches up to product |
| **C. Descoped GSD unit** | If planning authority decides M167 is obsolete because out-of-band proof already satisfies the **planned** vision, cancel/skip via GSD waiver tools with pointer to this register + `1403294` + F04a events | Clears active milestone without inventing Attempts |

Option C is **not** automatic from L_review closed. It needs explicit planning
authority, not residual inventory green.

### 4.5 Bridge line (canonical)

```text
finding=RC11-F04a
ceiling=spine
B1=delivery:out-of-band
B2=git:1403294:ln-applicability#NormRuleIR + EVT-VER-2026-08-13-02-RC11-F04a
delivery_unit=gsd:M167-odlgt8 (reference only; Attempt-incomplete)
capability=TSG-005 active; Applicable deferred
dual_truth=DT-lag
```

## 5. Operator checklist (P2)

Before claiming “aligned”:

1. [ ] Inventory residual for finding  
2. [ ] B1 intent recorded  
3. [ ] If `delivery:gsd:*` — Attempt exists or DT-lag registered  
4. [ ] B2 execution_linked present for implemented work  
5. [ ] Verification class-matched; ceiling named  
6. [ ] B3 TSG note  
7. [ ] If GSD active and review closed → entry in this register or successor  

## 6. Roadmap / Governor honesty

- Project-state roadmap may mark **latest completed GSD** separately from
  **active GSD** and from **L_review residual**.
- Governor GSD checks own **registry coherence**, not Review residual.
- A green Governor with active M167 + closed F04a is coherent **if** DT-lag is
  documented; it is not proof that L_delivery finished.

## 7. Non-claims

- This policy does not complete, cancel, or reopen GSD units by itself.
- Opaque `gsd:` strings in review events are not GSD API calls.
- Out-of-band delivery is technical debt visibility, not a preferred steady state.
- Future schema fields for `delivery_intent` remain deferred; docs-first is
  mandatory until then.

## 8. Adoption

- Human accepted continuity P2 after D153 three-lifecycle contract.
- First registered dual-truth incident: **M167 / RC11-F04a** (this document).
