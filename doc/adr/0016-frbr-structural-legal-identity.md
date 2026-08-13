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

**Accepted [proposed]** — structural identity model designed; **Work/Expression**
offline spine shipped (`mint_work` / `mint_expression` / `compare_work_identities`
in `ln-identity`, KBO-R011 S2). Number alone is never Work; same number +
divergent authority/date → Conflict. Still not Manifestation/Item store or corpus
identity stability. Distinct from C12 digest identity.
Moves to `[bounded]` when Manifestation carriers + fail-closed parser identity
join land; to `[validated]` only when identity is proven stable across the
representative corpus.

## Context

law-nexus must answer "which act / edition / article is this?" before any
temporal or normative reasoning. Russian legal sources (Consultant, Garant)
publish the same normative act as many dated editions, in many file formats,
with non-unique numbering (e.g. "188-ФЗ" exists in both 2013 and 2015). Without
a stable, comparable identity layer, every downstream comparison (is this the
same article? the same edition?) is ambiguous.

Prior research (archive-only prior art under
`prd/archive/research-era/ontology_architecture_requirements/`, not an active
`prd/research/` surface) selected the **FRBR four-level model**
(Work / Expression / Manifestation / Item) as the structural normalization
standard at adoption-ladder level L3 (compatibility/proof-gated per D046):
project-local evidence kernel stays authoritative, FRBR is the compatible
structural reference.

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

6. **Work is stable across amendments (Review 4 R4-01).** de Martim v5 models
   each Temporal Version as a distinct F1 Work. law-nexus does **not** adopt
   that identity rule. Russian act identity is number + enactment date +
   authority (decision 2). Each dated edition is an **Expression** of the
   same Work. A new Work is minted only for a different act (divergent
   number/authority/enactment), never for an amending ФЗ that revises 44-ФЗ.
   LRMoo/ELI remain compatibility projections (D046); they are not a licence
   to mint Work-per-amendment.

## Consequences

- Adds a structural-identity domain model above the raw parser output and below
  the temporal/versioning layer (ADR-0017).
- Enables stable cross-source comparison (Consultant vs Garant parity) at the
  structural level.
- Does NOT answer "what was the text of article X on date Y" (that is ADR-0017
  component versioning) nor "what did it legally mean" (ADR-0018+).

## Review 5 amendments (2026-08-14, L0 `doc/review/review-14-08-2026.md`)

### R5-07: ELI/AKN URI mapping for interoperability

de Martim v5 and ELI employ URI-based identification
(`eli/ru/{type}/{year}/{number}`). law-nexus employs project-local IDs
(`cc:402fz:statya-1`, `amendingact:c2-oracle-edition`). A compatibility
mapping layer (not a replacement) enables interop with AKN/ELI/LexML
corpora when needed. This is a D046 L6 compatibility projection `[proposed]`,
not a runtime requirement. When external corpus exchange is required, a
`to_eli_uri(work, expression, cc)` adapter can be added without changing
the internal ID canon.

## Non-claims

- `HierarchyMarker` / `map_hierarchy_marker` is a **fail-closed candidate lift**:
  unmapped markers are `Unknown`; number+level does not mint ComponentConcept,
  force, Expression presence, or legal fact. Parser output remains a candidate.

- `component_in_expression` / `fold_expression_presence` is **presence only**:
  not CTV text, not force, not decode HierarchyNode→CC, not calendar legal_act_effect.
  Later Expression does not silently inherit earlier presence.

- Offline `mint_work`/`compare_work_identities` is **structural L1 only**: not C12
  merge, not ForceStatus, not Applicability, not ELI global resolution.
- Same act number with divergent authority or enactment date is **Conflict**, never
  a silent pick.
- de Martim Temporal Version ≠ law-nexus Work. Copying TV=new-Work would
  break this ADR and Russian identity (Review 4 §3).
- A Consultant/Garant file is a **Manifestation** of an Expression, not a
  new Work and not the edition canon.

- No legal correctness of identity resolution.
- No claim that ELI URNs are globally resolvable beyond this project.
- No corpus completeness or cross-source parity validation yet.

## References

- D046 adoption-ladder (L3 structural)
- Archive-only prior art (not active product authority):
  `prd/archive/research-era/ontology_architecture_requirements/`
  (historical FRBR/Akoma Ntoso intake; superseded by this ADR + `prd/ARCHITECTURE.md`)
- ADR-0009 (five clocks; Expression uses `legal_act_effect`)
- ADR-0010 (evidence kernel; C12 identity authority)
- ADR-0013 (universal parser — structural carrier source)
- `prd/ARCHITECTURE.md` (living architecture truth oracle)
