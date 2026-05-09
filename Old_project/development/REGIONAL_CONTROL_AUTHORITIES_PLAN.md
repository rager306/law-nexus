# Federal Control Authorities Development Roadmap

**Created**: 2025-12-30
**Status**: Phase 1 - Complete
**Next Phase**: Territorial Bodies Research

---

## Completed (Phase 1)

| Spec File | Description |
|-----------|-------------|
| `federal_authorities.yaml` | Federal authorities structure (legislative, executive, judicial branches) |
| `federal_control_authorities.yaml` | Federal control/regulatory bodies with cross-references |

## Planned: Territorial Bodies Research (Phase TBD)

### Research Objectives
Create `territorial_bodies.yaml` with structure of territorial (regional) branches of federal control authorities across all 85+ Russian subjects.

### Key Distinction
- **Территориальные органы** — regional branches OF FEDERAL authorities (ИФНС, таможенные посты, территориальные подразделения Роструда)
- **Региональные органы** — bodies OF THE SUBJECTS themselves (КСО субъектов, региональные министерства)

### Scope

#### Территориальные органы федеральных контрольных органов:

##### 1. Territorial Tax Inspections (территориальные инспекции ФНС)
- 85+ territorial tax bodies
- Links to parent: ФНС России
- Functions: tax control, compliance checks

##### 2. Territorial Customs Posts (таможенные посты ФТС)
- Regional customs offices
- Links to parent: ФТС России
- Functions: customs control, import/export

##### 3. Territorial Labor Inspections (Гострудинспекции)
- State labor inspection in each subject
- Links to parent: Роструд
- Functions: labor law compliance, OHS

##### 4. Territorial Housing Inspections (ГЖИ)
- State housing inspection in each subject
- Functions: housing code compliance, utilities

##### 5. Territorial Environmental Inspections
- Nature protection bodies in subjects
- Links to parent: Росприроднадзор

##### 6. Territorial Technical Inspections
- Building/technical inspections
- Links to parent: Ростехнадзор

#### Региональные органы субъектов РФ:

##### 7. Control-Scount Chambers of Subjects (КСО субъектов РФ)
- Legislative audit bodies of each region
- Links to parent: Счетная палата РФ (coordination)
- Document types: заключения, отчеты, представления

### Cross-Reference Structure

```yaml
regional_control_authorities:
  authority_links:
    mappings:
      - control_authority: "КСО Московской области"
        parent_authority: "Счетная палата РФ"
      - control_authority: "ИФНС по г. Москве"
        parent_authority: "ФНС России"
```

---

## Planned: Regional Bodies of Subjects (Phase TBD)

### Research Objectives
Create `regional_bodies.yaml` with structure of regional-level bodies OF THE SUBJECTS (not territorial branches of federal authorities).

### Scope

#### Regional Bodies (органы субъектов РФ):
- Regional legislatures (законодательные собрания)
- Regional executives (правительства, администрации)
- Regional control bodies (КСО, региональные инспекции)

---

## Integration Goals

### Unified Inspection Practice Database
- Aggregate inspection data across:
  - Federal control authorities
  - Territorial bodies (территориальные органы) of federal authorities
  - Regional bodies of subjects (органы субъектов)
- Common metadata structure for:
  - control_authority
  - authority_id
  - authority_level  # federal / territorial / regional / municipal
  - control_type
  - inspection_type (planned/unplanned, on-site/documentation)
  - violations_found
  - sanctions_applied

### Cross-Level Analytics
- Federal policy implementation via territorial bodies
- Regional variations in enforcement
- Best practices aggregation across 85+ subjects

### Control Body Performance Metrics
- Inspection frequency by territorial body
- Violation detection rates by region
- Sanction application patterns

---

## Legal Basis References

| Document | Description |
|----------|-------------|
| ФЗ № 248-ФЗ | О государственном контроле (надзоре) |
| Указ Президента РФ № 326 от 11.05.2024 | Структура федеральных органов исполнительной власти |
| ФЗ № 6-ФЗ | О Контрольно-счетных органах субъектов РФ |
| ФЗ № 294-ФЗ | О защите прав юридических лиц при госконтроле |

---

## Next Actions

1. [ ] Research territorial bodies of federal authorities (TBD)
2. [ ] Create `territorial_bodies.yaml`
3. [ ] Research regional bodies of subjects (TBD)
4. [ ] Create `regional_bodies.yaml`
5. [ ] Design unified inspection aggregation schema
6. [ ] Implement cross-level analytics
