---
id: ADR-0016
title: FRBR structural legal identity (ontology layer L1)
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-11
supersedes: none
related: [ADR-0009, ADR-0010, ADR-0013]
---

# ADR-0016: FRBR structural legal identity (ontology layer L1)

## Status

**Accepted [proposed]** — structural identity model designed. Not implemented.
Moves to `[bounded]` when a Rust FRBR Work/Expression adapter with fail-closed
identity resolution ships with TDD parity tests; to `[validated]` only when
identity is proven stable across the representative corpus.

## Context

law-nexus must answer "which act / edition / article is this?" before any
temporal or normative reasoning. Russian legal sources (Consultant, Garant)
publish the same normative act as many dated editions, in many file formats,
with non-unique numbering (e.g. "188-ФЗ" exists in both 2013 and 2015). Without
a stable, comparable identity layer, every downstream comparison (is this the
same article? the same edition?) is ambiguous.

Prior research (`prd/research/ontology_architecture_requirements/05-01`) selected
the **FRBR four-level model** (Work / Expression / Manifestation / Item) as the
structural normalization standard at adoption-ladder level L3
(compatibility/proof-gated per D046): project-local evidence kernel stays
authoritative, FRBR is the compatible structural reference.

Note: the **LRMoo** ontology (IFLA LRM object-oriented formalization, harmonized
with CIDOC CRM) is the current successor of FRBRoo and preserves the WEMI
levels (F1 Work / F2 Expression / F3 Manifestation / F5 Item). ADR-0017 uses
LRMoo terminology (F1/F2) at the component level; this L1 ADR uses the
FRBR/WEMI names for the act-level identity but is fully compatible with LRMoo.
The four levels below are WEMI, LRMoo-compatible.

## Decision

1. **Four FRBR levels, Russian-jurisdiction-adapted:**

   | Level | Meaning | Russian analog | Temporal? |
   |-------|---------|----------------|-----------|
   | **Work** | abstract normative act (undated) | "44-ФЗ" as a concept | no |
   | **Expression** | dated edition of the whole act | "44-ФЗ as amended by ФЗ-188" | yes (legal_act_effect, ADR-0009) |
   | **Manifestation** | a concrete format/file | ODT / XML / HTML carrier | no |
   | **Item** | a concrete stored copy | storage URI | no |

2. **Identity includes date + authority, not number alone.** The canonical
   identity of a Work ALWAYS includes the enactment date (YYYY-MM-DD) and
   issuing authority, because Russian act numbers are non-unique across years
   and authorities. A URN form (ELI-compatible, project-local):

   ```
   urn:lex:ru:federal:zakon:2013-04-05;44-fz                 # Work
   urn:lex:ru:federal:zakon:2013-04-05;44-fz@2014-01-01      # Expression
   ```

3. **ELI = compatibility reference (L4 ladder), not canon.** Project-local
   identity lives in the evidence kernel (D119 C12 identity); ELI URNs are a
   deterministic, reversible projection for interoperability.

4. **Fail-closed identity resolution.** Two records with overlapping identity
   but divergent authority/date resolve to `Conflict`, never to a silent pick.
   Missing identity evidence resolves to `Unknown` (D118 outcome discipline).

5. **Parser produces structural identity; it does NOT infer normative content.**
   `ln-decode` (ADR-0013) emits Work/Expression/Manifestation carriers from
   real Consultant/Garant sources; normative substance is layered above (L2+).

## Consequences

- Adds a structural-identity domain model above the raw parser output and below
  the temporal/versioning layer (ADR-0017).
- Enables stable cross-source comparison (Consultant vs Garant parity) at the
  structural level.
- Does NOT answer "what was the text of article X on date Y" (that is ADR-0017
  component versioning) nor "what did it legally mean" (ADR-0018+).

## Non-claims

- No legal correctness of identity resolution.
- No claim that ELI URNs are globally resolvable beyond this project.
- No corpus completeness or cross-source parity validation yet.

## References

- D046 adoption-ladder (L3 structural)
- `prd/research/ontology_architecture_requirements/05-01-structural-normalization-akoma-ntoso.md`
- ADR-0009 (five clocks; Expression uses `legal_act_effect`)
- ADR-0010 (evidence kernel; C12 identity authority)
- ADR-0013 (universal parser — structural carrier source)
