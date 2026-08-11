# Authority map для документационной коррекции

**Статус:** `[proposed]` D0 / EA-00 authority map
**Базовая ревизия:** `60fd8245ace999f3f29911844375dd7cc36a2a38` (2026-08-11)
**Assessment root:** `assessment/`
**Lifecycle rule:** нижний или derived слой не может повысить claim выше governing ADR и proof class

## 1. Authority stack A0–A7

| Level | Surface | Роль | Ограничение |
|-------|---------|------|-------------|
| A0 | vault/retired-ID policy (включая active-plane/archive classification) | определяет допустимый publication plane | не доказывает product behavior |
| A1 | `prd/ARCHITECTURE.md` | living architecture truth oracle | обязан отражать ADR ceilings и explicit non-claims |
| A2 | `doc/adr/**` | каноническое decision substance | `[proposed]` design не является implementation proof |
| A3 | `prd/PRODUCT.md` — `[proposed]` D2 draft | tracked Product Contract после EA-02 readiness review | до принятия остаётся draft и не может превышать ADR/proof ceilings |
| A4 | `prd/REQUIREMENTS.md` — `[proposed]` D2 projection | published capability obligations после EA-02 readiness review | local `.gsd` body не заменяет projection; draft не является accepted contract |
| A5 | `prd/migration/**`, `prd/project-state/**` | sequence и current-front planning | completion не является readiness proof |
| A6 | cross-matrices и control catalog; `assessment/**` как `AssessmentPacket` process evidence | process evidence и disposition | AssessmentPacket никогда не получает A1–A4 authority и не является product/runtime proof |
| A7 | `prd/architecture/**`, generated wiki/reports, LLM outputs | derived diagnostics | не удовлетворяют requirement и не повышают lifecycle |

`O1–O7` обозначает ontology layers ADR-0016–0022. `C0–C7` обозначает control layers. Эти namespaces не являются authority levels A0–A7.

## 2. Surface classification

### Canonical active

| Surface | Classification | Cold-reader expectation |
|---------|----------------|-------------------------|
| `prd/ARCHITECTURE.md` | canonical architecture | tracked, self-contained entrypoint |
| `doc/adr/**` | canonical decisions | tracked, indexed, status/lifecycle explicit |
| `prd/PRODUCT.md` | proposed canonical product intent | D2 draft существует, но ещё не `ready-for-assessment`/accepted |
| `prd/REQUIREMENTS.md` | proposed tracked requirements projection | D2 draft существует; не копия `.gsd` и не accepted proof |

### Planning/process

| Surface | Classification | Boundary |
|---------|----------------|----------|
| `prd/architecture/documentation-semantic-control-plan.md` | `[proposed]` execution/process design | не меняет ADR lifecycle |
| `prd/migration/external-architecture-assessment-roadmap.md` | `[proposed]` assessment roadmap | не является external report |
| `assessment/**` | revision-bound process evidence | не является product/legal validation |
| active roadmaps | planning authority only | sequence ≠ readiness |

### Local/non-published

| Surface | Classification | Boundary |
|---------|----------------|----------|
| `.gsd/**` | local workflow/state | не sole external proof и не cold-reader dependency |
| `.litho/**`, `litho.docs/**`, local `litho.toml` | ignored derived/local state | не assessment evidence и не authority |
| `.gsd/exec/**`, local logs | ephemeral execution evidence | не durable tracked proof anchor |

### Derived

| Surface | Classification | Boundary |
|---------|----------------|----------|
| `prd/architecture/**` registry/views | tracked derived projection | diagnostic only; canonical docs win |
| LLM reports/findings | advisory candidate evidence | exact citations + human disposition required |
| external framework/tool output | candidate mechanics | adoption decision required before canon |

### Archive/historical

| Surface | Classification | Boundary |
|---------|----------------|----------|
| `archive/**`, `python_archive/**`, `prd/archive/**` | historical prior art | no active authority without explicit adoption decision |
| ACP/git-lex and FalkorDB-era surfaces | decommissioned history | must remain qualified historical/superseded |
| retired ADR IDs | historical identifiers | cannot be silently reused |

## 3. Canonical graph directions

Разрешено:

```text
ADR → governs Product clause / Requirement
Product clause → derives Requirement
Claim / Requirement → satisfied_by tracked evidence
Roadmap item → depends_on prerequisite
Canonical item → historical_only archive item
Derived finding → diagnoses canonical item
Local GSD source → publishes tracked projection
Assessment report → disposition_by acceptance authority
```

Запрещено:

```text
Derived registry → promotes lifecycle
LLM finding → BLOCK без deterministic/human corroboration
Archive artifact → active authority без adoption decision
Local .gsd body → sole external proof
Roadmap completion → implementation/readiness proof
Temporal crosswalk → changes ADR lifecycle
External assessment → product/legal validation
Similarity hit → satisfies requirement
```

## 4. Product and temporal boundary

Подтверждённый design spine:

```text
ADR-0009 safety/clock policy
→ O1 ADR-0016 identity
→ O2 ADR-0017 component temporal versioning
→ O3 ADR-0018 NormativeState
→ O4 ADR-0019 hierarchy/conflict
→ O5 ADR-0020 practice overlay
→ O6 ADR-0021 transitional/risk
→ O7 ADR-0022 industry profiles
```

Все O1–O7 сохраняют `[proposed]` ceiling там, где он установлен governing ADR. Подтверждённый executable gap:

```text
NormRule
→ ApplicabilityPredicate
→ CaseFacts
→ ApplicabilityDecision
→ ExplainableTrace
```

Отсутствие этого runtime не означает отсутствие temporal design, но запрещает claim computable legal applicability. Procurement остаётся proving profile нейтрального applicability kernel, не второй core ontology.

## 5. Acceptance boundaries

- Author, semantic reviewer, independent assessor и acceptance authority — разные роли, даже если отдельный человек совмещает не-load-bearing подготовительную работу.
- Consequential finding не закрывается молча.
- Deterministic structural failure может дать `BLOCK`.
- LLM-only finding остаётся `ADVISORY`.
- Human disposition должен ссылаться на frozen revision и evidence.
- Assessment packet не использует raw legal corpus, secrets, ignored paths или raw provider payloads.

## 6. Open publication gaps after D0/D1 drafts

- Product Contract и tracked requirements projection существуют как `[proposed]` D2 working-tree drafts, но ещё не frozen/tracked at revision и не `ready-for-assessment`.
- Living entrypoint corrections существуют в working tree; D1 closure требует frozen tracked-link scan и disposition.
- Roadmap current-front surfaces требуют D5 synchronization.
- Derived registry требует D7 quarantine/refresh.
- Deterministic controls пока существуют как paper catalog, а не implemented gates.
- Independent assessor ещё не назначен; EA-09 не начат.

Эти gaps являются явными `[proposed]`/open состояниями и не сглаживаются в readiness.
