# KB Ontology Draft — L1–L3 Projection Contract

**Lifecycle:** `[proposed]` design inventory  
**FSM state:** declared in `kb-ontology.yaml` (`fsm.current`)  
**Non-authority:** not production graph schema, not RuVector validation, not
legal ontology completeness, not Applicable/practice/risk product types.

## 1. Boundary

```text
Domain (ln-temporal, future identity FRBR, evidence kernel)
        │  pure projection (write-set)
        ▼
Graph/Vector ports (ADR-0014) ── adapters ── RuVector/redb/RVF
```

- Domain owns meaning.  
- Projection owns serializable node/edge shapes for storage.  
- Infrastructure must not redefine legal types.

## 2. In-scope layers (only)

| Layer | ADR | Graph meaning (draft) |
|---|---|---|
| L1 Identity carriers | 0016 | Work / Expression / Manifestation (+ Item optional later) |
| L2 CTV / membership | 0017 | ComponentConcept, MembershipEdge, StructuralIndustrialEvent |
| L3 Force status | 0018 | ForceStatusEvent → NormativeState force values only |

## 3. Node kinds (draft)

| kind | layer | Required properties (min) | Notes |
|---|---|---|---|
| `Work` | L1 | `work_id`, `authority`, `enactment_date` | number alone is never identity |
| `Expression` | L1 | `expression_id`, `work_id`, `legal_act_effect_day` | dated edition |
| `Manifestation` | L1 | `manifestation_id`, `expression_id`, `format`, `source_uri?` | file/format carrier |
| `ComponentConcept` | L2 | `component_concept_id` | article/part concept, not force |
| `AmendingAct` | L2/L3 | `amending_act_id` | provenance only |
| `MembershipEdge` | L2 | `parent_cc`, `child_cc` | structural composition |
| `StructuralIndustrialEvent` | L2 | `op_id`, `kind`, `subjects[]`, `targets[]`, `provenance` | not legal effect |
| `ForceStatusEvent` | L3 | `component_concept_id`, `status`, `effect_day`, `provenance` | status ≠ Unknown as write |

## 4. Edge kinds (draft)

| kind | from → to | Semantics |
|---|---|---|
| `expression_of` | Expression → Work | edition of abstract act |
| `manifestation_of` | Manifestation → Expression | format instance |
| `component_in_expression` | ComponentConcept → Expression | event-sourced include/exclude; later Expression does not inherit |
| `membership_parent` | ComponentConcept → ComponentConcept | parent of child |
| `industrial_op_subject` | StructuralIndustrialEvent → ComponentConcept | subject of op |
| `industrial_op_target` | StructuralIndustrialEvent → ComponentConcept | target of op |
| `force_status_of` | ForceStatusEvent → ComponentConcept | status evidence for component |
| `prov_amending_act` | *Event → AmendingAct | required provenance |

## 5. Join keys (mandatory)

| Key | Used by |
|---|---|
| `ComponentConceptId` | membership, force, future CTV text join |
| `AmendingActId` | all status/industrial events |
| `effect_day` | force resolution ordinal (offline synthetic unit) |
| `work_id` / `expression_id` | L1 identity (stable rules still open → KBO-R011) |

## 6. Forbidden kinds in L1–L3 core (KBO-R017)

Do **not** mint as core store truth in this draft:

- `ApplicableDecision` / case verdict nodes  
- `PracticeRuling` as force mutator  
- `RiskScore` as NormativeState  
- `ProfileCode` as sixth clock  
- `NormRule` product graph as authority  
- Mixed mega-type `NormativeBlob` (force+text+applicability)

These may appear later as **L4–L7 projections** under their own ADRs and
promotion packets — never as silent L1–L3 edges.

## 7. Projection rules (FSM-ish)

```text
ON ForceStatusEvent:
  require provenance + transition status ≠ Unknown
  emit ForceStatusEvent node + force_status_of + prov_amending_act
  NEVER emit Applicable*

ON Membership insert/apply:
  emit MembershipEdge + optional StructuralIndustrialEvent
  NEVER emit ForceStatus InForce from membership alone

ON missing force evidence at query time:
  resolve Unknown (read model); do not invent InForce node
```

## 8. Mapping to current Rust spines

| Domain API | Draft kind |
|---|---|
| `ComponentConceptId` | `ComponentConcept` |
| `MembershipGraph` / `apply_industrial_op` | `MembershipEdge`, `StructuralIndustrialEvent` |
| `ForceStatusTimeline` / `resolve_force_status_at` | `ForceStatusEvent` + read Unknown |
| `join_force_with_membership` | force + membership context; never Applicable |
| `NormativeDimension` | **not** a graph node (design inventory) |
| `ln-identity` C12 digest identity | **not** FRBR Work (separate gate) |
| `mint_work` / `mint_expression` / `compare_work_identities` | Work/Expression S2; number≠Work |
| `ln-kb-ontology::project_*` | typed write-set; no I/O; forbidden kinds rejected |
| `fold_membership_at` / `StructuralAst` | versioned membership projection @ t; not canon |
| `project_structural_ast` | write-set from folded tree; still no I/O |
| `fold_expression_presence` / `filter_ast_to_expression` | CC in Expression @ t; not CTV text |
| `map_hierarchy_marker` / `HierarchyMap` | decode candidate → CC or Unknown; not legal fact |
| `kb-ontology.yaml` + `OntologyCatalog` | meta-prompt FSM + vocabulary source |
| `marker_from_decode_token` | YAML decode aliases → HierarchyMarker; no ln-decode dep |
| `try_push_node` / `try_push_edge` | catalog-validated kind tokens; unknown fails closed |

## 9. Explicit non-claims

- Draft ≠ production schema freeze.  
- Draft ≠ corpus / multi-provider identity proof.  
- Draft ≠ RuVector capability validation.  
- Draft ≠ L4–L7 product types.  
- Governor structural check ≠ semantic ontology completeness.
