---
id: ADR-0022
title: Industry profiles architecture (ontology layer L7)
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-11
supersedes: none
related: [ADR-0019, ADR-0020, ADR-0021]
---

# ADR-0022: Industry profiles architecture

## Status

**Accepted [proposed]** — industry profile architecture designed. Not
implemented. Moves to `[bounded]` per-profile when each profile's rules and
TDD ship; to `[validated]` with real profile corpus proof.

## Context

The core ontology (L1-L6, ADR-0016..0021) is industry-neutral by design:
hierarchy, clocks, versioning, status, practice, and risk are common to all
Russian law. But real use is industry-specific: budget accounting (БК, казначейство,
обязательства, лимиты), construction/reconstruction/overhaul/repair (ГрК,
квалификация видов работ, техрегламенты), medicine (61-ФЗ, реестры, ЖНВЛП,
медизделия), and general control (КоАП, давность). Each vertical has
industry-specific conflict priorities, special norms, and practice traditions.

Tracked architecture policy (ADR-0015 hexagonal verification + living
`prd/ARCHITECTURE.md` profile boundary) mandates that law-nexus-specific and
industry-specific constraints live in a **profile/adapter layer**, not in the
neutral core. Session-local `AGENTS.md` may restate this for agents but is
gitignored and is **not** the durable authority for the decision.

## Decision

1. **Profiles are adapters over the neutral core, not core extensions.** Each
   profile implements a `Profile` contract that supplies:

   - **industry priority** — which norm governs an industry question
     (БК for budget, ГрК for construction, 61-ФЗ/44-ФЗ for medicine procurement)
     consumed by ADR-0019 conflict resolution;
   - **special-norm registry** — industry-specific lex specialis rules;
   - **industry practice weighting** — which practice sources dominate in this
     vertical (e.g. Казначейство letters for budget), consumed by ADR-0020;
   - **industry risk factors** — typical violations, sanctions, mitigating
     circumstances, consumed by ADR-0021.

2. **Initial profile set:**

   | Profile | Core NPA | Key temporal concern |
   |---------|----------|----------------------|
   | **Budget** | БК, 44-ФЗ, 6-ФЗ, приказы Минфина | бюджетный цикл (год/3 года), обязательства, лимиты БО LBO/SBO, кассовый год vs обязательство |
   | **Construction** | ГрК, 44-ФЗ, 384-ФЗ, ПП РФ | квалификация вида работ (капремонт vs текущий ремонт), изменяющиеся классификаторы (ОК 013, ОКВЭД2) |
   | **Medicine** | 61-ФЗ, 44-ФЗ ст.93, ПП РФ, приказы Минздрава | реестровые цены, перечни ЖНВЛП/медизделий, ФЗ-100 (2024) обращения лекарств |
   | **General control** | КоАП, 41-ФЗ, профильные | давность (ст. 4.5 КоАП), состав на дату события vs дату рассмотрения |

3. **Budget temporal subtlety (profile-owned).** The budget cycle creates a
   profile-scoped "бюджетный час" (obligation vs cash year). This is modeled
   WITHIN the budget profile as a projection over the five clocks (ADR-0009),
   not as a sixth clock — the core stays at five.

4. **Core/profile isolation enforced by architecture.** A profile may not
   mutate kernel evidence (D119) or invent clocks; it supplies rules the core
   resolvers consume. This is verifiable by import boundaries (onion/hexagonal,
   ADR-0015).

5. **Profiles are independently [bounded]/[validated].** The core can be
   `[bounded]` while a profile is still `[proposed]`; each profile graduates
   on its own evidence.

6. **EA-04 clarification — profiles supply applicability inputs, not the
   protocol.** Under ADR-0023, profiles provide versioned `CaseFacts` schemas,
   predicate declarations, classifiers and industry lists. The neutral core
   owns final decision, abstention and trace. Profile-specific industry
   priority remains an input and never elevates `NormativeRank`.

## Consequences

- Adds a Profile contract + four initial profile adapters as the top ontology
  layer, consumed by L4/L5/L6.
- Keeps the core industry-neutral and reusable, per ADR-0015 / profile-adapter isolation.
- Lets industry depth (budget/construction/medicine) advance independently of
  the common temporal engine.

## Non-claims

- No profile is implemented; all four are `[proposed]`.
- No claim that industry priority rules are legally complete — they encode
  common doctrine, validated per-profile against real corpus/practice.
- Budget "бюджетный час" is a profile projection, not a core clock change.

## References

- ADR-0015 (hexagonal verification; profile = adapter)
- `prd/ARCHITECTURE.md` (living profile/core isolation boundary)
- ADR-0019 (industry priority consumed by conflict resolver)
- ADR-0020 (industry practice weighting)
- ADR-0021 (industry risk factors)
- ADR-0023 (profiles supply applicability inputs, not final decisions)
