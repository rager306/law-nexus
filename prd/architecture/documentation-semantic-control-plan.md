# План коррекции и семантического контроля ADR/PRD

**Статус:** `[proposed]` process design
**Базовая ревизия:** `60fd8245ace999f3f29911844375dd7cc36a2a38` (2026-08-11)
**Область:** только архитектурные, продуктовые и process-документы; без изменений product runtime
**Authority:** `prd/ARCHITECTURE.md` + `doc/adr/**`; tracked `prd/PRODUCT.md` defines the `[proposed]` Product Contract and remains below governing ADR ceilings
**Non-authority:** `.gsd/**` как локальная workflow-поверхность, `prd/architecture/**` как derived registry, LLM-отчёты и внешние framework/tool outputs
**Внешний assessment track:** `prd/migration/external-architecture-assessment-roadmap.md`

## 1. Цель

Устранить подтверждённые противоречия публикационной поверхности и построить сквозной многоуровневый контроль:

```text
Product intent
→ Product Contract clauses
→ Requirements
→ ADR decisions
→ Architecture claims
→ Roadmap commitments
→ Evidence/proof class
→ Independent assessment disposition
```

Контроль должен обнаруживать:

- мёртвые и локально-разрешимые, но не опубликованные ссылки;
- lifecycle smoothing между ADR, ARCHITECTURE, Product Contract и roadmap;
- orphan requirements / ADR / contract clauses;
- derived-registry authority creep;
- устаревшую milestone-front навигацию;
- исторический ACP/FalkorDB/PyO3 шум на active plane;
- нормативные или продуктовые утверждения без proof class и tracked evidence;
- семантические противоречия, которые нельзя надёжно найти простым regex.

LLM может только формировать advisory findings. Lifecycle promotion, acceptance и BLOCK без детерминированного подтверждения остаются за человеком.

## 2. Подтверждённые дефекты

| ID | Дефект | Класс | Приоритет |
|----|--------|-------|-----------|
| DOC-01 | `prd/ARCHITECTURE.md` ссылается на отсутствующие `prd/01_general_idea.md` и `prd/02_architecture.md` | publication integrity | P0 |
| DOC-02 | README/ARCHITECTURE представляют `.gsd/*.md` как cold-reader поверхности, хотя `.gsd` не tracked | authority/publication boundary | P0 |
| DOC-03 | Нет современного tracked Product Contract: ARCHITECTURE описывает направление, но не полный продуктовый контракт | product intent gap | P0 |
| DOC-04 | `prd/project-state/roadmap.md` сообщает M160/M161, хотя M161–M165 уже завершены | freshness/navigation | P0 |
| DOC-05 | Derived registry/readiness содержит active-looking FalkorDB/ACP rows и устаревшие source anchors | derived-authority/staleness | P1 |
| DOC-06 | Temporal readiness представлен в основном `GATE-G005`; нет gates для CTV, applicability, correction, status separation, case timeline | proof coverage | P1 |
| DOC-07 | Cross-surface matrix не описывает Product Contract и external assessment authority | traceability gap | P1 |
| DOC-08 | Нет формализованного разделения deterministic semantic checks, LLM review и human acceptance | governance ambiguity | P1 |
| DOC-09 | Нет event-triggered freshness policy для living documents | continuity gap | P2 |
| DOC-10 | Нет revision-bound external assessment packet | independent review gap | P1 |

## 3. Authority stack A0–A7

Authority направлена сверху вниз; evidence поднимается снизу вверх. Нижний слой не может повысить lifecycle верхнего.

| Level | Поверхность | Роль | Authority |
|-------|-------------|------|-----------|
| A0 | vault/retired-ID policy | определяет active plane | policy authority |
| A1 | `prd/ARCHITECTURE.md` | living architecture truth oracle | canonical architecture |
| A2 | `doc/adr/**` | append-only decision substance | canonical decisions |
| A3 | tracked `prd/PRODUCT.md` (`[proposed]`, EA-02 `ready-for-assessment`) | пользовательский/product contract | canonical product intent after final acceptance; not EA-10 accepted yet |
| A4 | tracked `prd/REQUIREMENTS.md` (не локальные `.gsd` bodies) | `[proposed]` capability obligations | tracked projection; not requirement-validation proof |
| A5 | migration/project roadmaps | последовательность, а не readiness | planning authority only |
| A6 | cross-matrices и control catalog | проверка связности | process evidence |
| A7 | `prd/architecture/**`, generated reports, LLM reports | диагностика и поиск | derived, non-authoritative |

### 3.1. Роли

| Роль | Разрешено | Запрещено |
|------|-----------|-----------|
| Author | подготовить draft, варианты и evidence map | самостоятельно принять lifecycle promotion |
| Semantic reviewer | проверить смысл, противоречия, non-claims, candidate links | принимать архитектурное решение или закрывать finding без disposition |
| Acceptance authority | принять/reject решение, exception, lifecycle transition | молча считать CI green достаточным принятием |
| Independent assessor | перепроверить frozen packet и дать assessment | изменять канонические документы в ходе оценки |

## 4. Canonical artifact graph

### 4.1. Типы артефактов

| Kind | Канонический путь | Минимальные поля |
|------|-------------------|-----------------|
| `TruthOracle` | `prd/ARCHITECTURE.md` | revision, direction contract, ADR lifecycle table, current front, non-claims |
| `ADR` | `doc/adr/0NNN-*.md` | id, status + D098 LC, context, decision, consequences, scope, supersession, references |
| `ProductContract` | tracked `prd/PRODUCT.md` (`[proposed]`) | clause id, class, lifecycle, proof class, evidence refs, acceptance criteria, non-claims |
| `Requirement` | tracked `prd/REQUIREMENTS.md` / local GSD workflow source | id, class, status, owning clauses, governing ADRs, validation route |
| `RoadmapSurface` | `prd/migration/**`, `prd/project-state/**` | current front, revision/as-of, depends, exit criteria, non-claims |
| `TemporalCrosswalk` | tracked `prd/temporal-legal-model.md` (`[proposed]`) | glossary, invariants, ADR crosswalk, readiness gates, unresolved questions, non-claims; не lifecycle authority |
| `ControlCatalog` | этот документ / process annex | control id, severity, authority, evidence class, remediation |
| `AssessmentPacket` | tracked root `assessment/`, зафиксированный D0 / EA-00; пакет пока `[proposed]`, не frozen/accepted | revision, inventory, gate results, findings, dispositions, signatures |
| `DerivedRegistry` | `prd/architecture/**` | source revision, `derived=true`, diagnostic-only banner |

### 4.2. Разрешённые edges

| Edge | From → To | Семантика |
|------|-----------|-----------|
| `cites` | Oracle/README → ADR | упоминание решения с lifecycle context |
| `mirrors_lifecycle` | Oracle/Product clause ↔ ADR | lifecycle не сильнее governing ADR/evidence |
| `governs` | ADR → Contract clause/Requirement | решение ограничивает intent |
| `derives_from` | Requirement → Product clause | требование выводится из продуктового обязательства |
| `satisfied_by` | Contract/Requirement → tracked evidence | proof pointer, не prose justification |
| `supersedes` | ADR/Roadmap item → predecessor | append-only evolution |
| `depends_on` | Requirement/roadmap item → prerequisite | явная зависимость |
| `diagnoses` | DerivedRegistry/LLM finding → canonical item | только диагностический сигнал |
| `historical_only` | Active doc → archive/retired item | квалифицированная историческая ссылка |
| `publishes` | local GSD source → tracked projection | внешне доступная копия/выжимка |

### 4.3. Запрещённые edges

```text
DerivedRegistry → promotes lifecycle
LLM finding → blocks without deterministic/human corroboration
Archive artifact → active authority without adoption decision
GSD decision row (`D###`) → replaces ADR architectural substance
Untracked .gsd artifact → sole external proof
Similarity/retrieval hit → satisfies requirement
TemporalCrosswalk → promotes ADR or ontology lifecycle
```

## 5. Lifecycle и proof ceilings

| Lifecycle | Минимальный документальный смысл | Минимальный proof class для product claim |
|-----------|----------------------------------|-------------------------------------------|
| `[proposed]` | решение/контракт определены, proof ещё нет | none/design only |
| `[bounded]` | проверен ограниченный контракт/fixture/static invariant | synthetic/static/port contract |
| `[smoke]` | пройден реальный путь на ограниченной fixture/runtime | real fixture/runtime smoke |
| `[validated]` | доказан заявленный scope на representative evidence | real corpus/release class + human acceptance |
| `[deferred]` | scope сознательно отложен | не является proof |

`Unknown`, `Conflict`, missing evidence и advisory findings не должны автоматически изменять lifecycle. Numeric readiness scores не заменяют blocker thresholds.

## 6. Multi-level control model C0–C7

### C0 — File and publication controls

Детерминированно:

- tracked-path integrity для living entrypoints;
- vault/retired ID policy;
- symlink target policy;
- `.gsd` publication qualifier;
- no secret/local execution path as durable evidence.

### C1 — Structure and schema controls

Детерминированно:

- required ADR/Product sections;
- unique stable IDs;
- allowed lifecycle values;
- valid status transitions;
- reciprocal supersession links;
- required Product clause fields.

### C2 — Referential graph controls

Детерминированно:

- no dangling edges;
- no duplicate IDs;
- no forbidden edge types;
- no orphan `[validated]` clause;
- bidirectional coverage reports generated from explicit edges;
- cycles allowed only where explicitly modeled; dependency/supersession cycles forbidden.

### C3 — Lifecycle and authority controls

Детерминированно + human:

- oracle lifecycle equals ADR status ceiling;
- Contract/Requirement cannot exceed governing ADR/proof class;
- derived registry cannot satisfy acceptance;
- lifecycle promotion requires acceptance authority disposition.

### C4 — Evidence controls

Детерминированно:

- tracked evidence reference exists;
- evidence class is allowed for lifecycle;
- evidence has source revision and scope;
- bounded/smoke non-claims preserved;
- external sources recorded with URL, date/version and adoption disposition.

### C5 — Semantic invariant controls

Hybrid:

- deterministic rules for known invariants (Rust-only runtime, no PyO3/FFI, five-clock no substitution, ontology layers O1–O7 / ADR-0016–0022 `[proposed]`);
- LLM advisory review for free-text contradiction, missing consequences, scope drift, inconsistent terms;
- every LLM finding must be classified `candidate`, cite exact source spans, and receive human disposition.

### C6 — Change impact and freshness controls

Детерминированно + human:

- changed ADR triggers oracle/index/matrix review;
- milestone close triggers roadmap/oracle freshness review;
- changed Product clause triggers requirements/ADR coverage review;
- external assessment expires when frozen SHA changes materially;
- 90-day human review due date is an obligation, not a quality score.

### C7 — Independent assessment

- assessor uses frozen SHA;
- re-runs deterministic checks;
- samples consequential semantic chains;
- verifies role separation;
- disposition is `accepted-for-process`, `accepted-with-findings`, `rejected-needs-remediation`, or `superseded-by-new-assessment`;
- vocabulary authority is EA-10 in `prd/migration/external-architecture-assessment-roadmap.md`;
- never `product-validated` from documentation review alone.

## 7. Gate catalog

| Gate | Mode | Initial severity | Future blocking condition |
|------|------|------------------|---------------------------|
| `published-link-integrity` | deterministic | BLOCK living entrypoints | always |
| `gsd-publication-boundary` | deterministic | WARN | BLOCK when unpublished item is sole external proof |
| `product-contract-present` | deterministic | WARN | BLOCK before external architecture acceptance |
| `artifact-schema-conformance` | deterministic | WARN | BLOCK after schema adoption |
| `typed-edge-integrity` | deterministic | WARN | BLOCK on dangling/forbidden current-authority edges |
| `adr-truth-oracle-sync` | deterministic | BLOCK | existing |
| `contract-lifecycle-ceiling` | deterministic | BLOCK | lifecycle exceeds ADR/proof class |
| `proof-class-sufficiency` | deterministic | BLOCK | `[validated]` without representative proof |
| `non-claim-preservation` | deterministic + semantic | BLOCK on deterministic loss | LLM-only finding stays advisory |
| `roadmap-front-sync` | deterministic | WARN | BLOCK external packet if stale |
| `derived-registry-quarantine` | deterministic | BLOCK | registry used as authority |
| `derived-registry-staleness` | deterministic | WARN | remains diagnostic |
| `active-era-claim-ban` | deterministic | BLOCK | unqualified active FalkorDB/ACP/PyO3 claim |
| `temporal-readiness-coverage` | deterministic + human | WARN | BLOCK ontology/product promotion without gates |
| `semantic-consistency-review` | LLM advisory | ADVISORY | never blocks alone |
| `independent-assessment-disposition` | human | required | BLOCK publication of accepted assessment without disposition |

## 8. План коррекции документов

### D0 — Freeze authority map

**Deliverables:**

- перечень canonical/derived/local/archive surfaces;
- frozen source revision;
- Author / Reviewer / Acceptance roles;
- список известных дефектов DOC-01..DOC-10.

**Exit:** authority map принят; derived registry явно исключён из acceptance evidence.

### D1 — Living links and publication boundary

**Depends:** D0.

- удалить или переписать active living-links, указывающие на отсутствующие `prd/01_general_idea.md` и `prd/02_architecture.md`, на актуальные tracked surfaces (ARCHITECTURE / Product Contract / archive-qualified historical references);
- сами `prd/01_general_idea.md` / `prd/02_architecture.md` не восстанавливать как active truth; при сохранении — только archive-only с qualifier;
- пометить `.gsd/**` как local workflow;
- определить tracked publication path для product requirements/contract summary.

**Exit:** zero unresolved tracked links на ARCHITECTURE/README/ADR index/cross-matrix.

### D2 — Product Contract

**Depends:** D1.

Создать `prd/PRODUCT.md` со следующими разделами:

1. personas и human authority;
2. user/legal-question loops;
3. обязательные inputs;
4. typed outputs и abstention outcomes;
5. product capabilities;
6. quality attributes;
7. threat model юридической ошибки;
8. human review boundary;
9. release/readiness criteria;
10. non-claims;
11. trace table Product clause → Requirement → ADR → Evidence.

**Exit:** все clauses имеют ID, lifecycle и proof class; ни одна не `[validated]` без proof.

### D3 — Temporal legal semantic specification

**Depends:** D2.

Создать crosswalk-документ, не новый oracle:

```text
prd/temporal-legal-model.md
```

Он связывает ADR-0009 и ADR-0016–0022, определяет glossary, invariants, unresolved questions, readiness gates и будущие golden cases. Каждое решение ссылается на owning ADR; документ сам не повышает lifecycle.

**Exit:** crosswalk checklist не содержит неразрешённых противоречий clock/event/time, force/applicability/knowledge и text-change/legal-effect; каждый открытый вопрос явно `[proposed]`, имеет owner/revisit trigger, а acceptance authority disposition записан для frozen revision.

### D4 — ADR amendments and one residual ADR decision

**Depends:** D3.

- ADR-0009: clocks как anchor roles + temporal primitives cross-reference;
- ADR-0017: text change vs normative effect, membership versioning, correction semantics;
- ADR-0018: orthogonal status dimensions;
- ADR-0019: partial-order authority scope;
- ADR-0020: practice coverage outcomes;
- ADR-0021: transitional applicability отделить от advisory risk;
- ADR-0022: core/profile boundary.

Не создавать пакет ADR-0023–0032. Один новый ADR допустим только если после crosswalk остаётся load-bearing решение `NormRule + Applicability boundary`.

**Exit:** required-section и cross-reference checklist пройден; supersession links reciprocal; открытые semantic conflicts перечислены с owner/revisit trigger; acceptance authority disposition записан.

### D5 — Roadmap synchronization

**Depends:** D2–D4.

- обновить current front после M165;
- исправить lifecycle table в `forward-roadmap.md`;
- отразить documentation-first milestones и будущий executable kernel как deferred downstream;
- пометить FalkorDB/ACP sequences historical/superseded;
- добавить source revision/as-of.

**Exit:** все active roadmap surfaces указывают один current front и source revision; lifecycle tags не сильнее oracle/ADR; исключения явно перечислены и имеют owner/revisit trigger.

### D6 — Readiness/control matrix expansion

**Depends:** D3–D5.

Добавить бумажные gates для:

- temporal primitives;
- component identity/membership;
- CTV event-to-interval;
- text change vs legal effect;
- force/applicability separation;
- bitemporal observation/correction;
- cross-reference resolution;
- transitional applicability;
- NormRule and applicability trace;
- procurement case timeline;
- practice coverage;
- versioned lists/classifiers.

**Readiness home:** единственная tracked matrix — `prd/temporal-legal-model.md` §10–10.1 (TL-G01..TL-G12 + TL-GC01..18). Derived registry/readiness reports may diagnose drift but cannot replace or satisfy it.

**Exit:** каждый `[proposed]` layer имеет graduation criteria, hostile case, evidence owner, dependency, current state и explicit non-claims; paper PASS не меняет lifecycle.

### D7 — Derived registry quarantine and refresh plan

**Depends:** D0, D5, D6.

- retire/reclassify active-looking FalkorDB/ACP/PyO3 rows;
- удалить active anchors на отсутствующие PRD/research paths;
- сохранить historical/decommission records;
- определить безопасную regeneration sequence;
- не редактировать generated views в authority.

**Exit:** registry отражает канон как derived projection и не содержит пути к lifecycle promotion.

#### Annex D7 — Derived Registry Quarantine Contract

**Baseline:** `bfe2ee6`; **method:** fail-closed data disposition; **authority effect:** none.

Every registry item/edge is always `non-authoritative-derived`; it cannot satisfy a living requirement, promote/demote ADR/Product lifecycle, or replace canonical evidence. D7 preserves IDs and archaeology while changing active-reader visibility.

Disposition rules:

| Condition | Item disposition | Edge disposition | Reader effect |
|-----------|------------------|------------------|---------------|
| ACP/git-lex/FalkorDB/PyO3/pre-Rust active-looking row | `superseded`, proof `none`, `sunsetting` | `superseded` | historical archaeology only |
| any claimed anchor missing from active tracked plane | `blocked`, proof `none` | `hypothesis` | blocked diagnostic; never current claim |
| derived `satisfies`/`validated_by`/`implements` authority-like edge | endpoint retained; no lifecycle effect | `superseded` | cannot satisfy Product/RQ |
| current Rust-direction row with all tracked anchors | existing honest status may remain | diagnostic edge only | still non-authoritative |

Hard invariants:

```text
lifecycle_effect = none
requirement_effect = cannot-satisfy
preserve_record = true
archive symlink existence ≠ active authority anchor
missing anchor ≠ current claim
verifier/view PASS ≠ product readiness
```

Safe regeneration sequence:

1. update canonical docs/evidence first;
2. freeze source revision;
3. inventory era tokens, missing anchors and authority-like edges;
4. apply dispositions while preserving IDs;
5. regenerate only if both declared extractor and graph builder exist and consume current mappings;
6. regenerate health/blocker/claims/remediation views downstream;
7. run graph verifier and process gates;
8. interpret PASS as artifact health only.

At the D7 baseline, historical extractor and graph builder are absent. Therefore JSONL quarantine is applied directly and generated Markdown views are marked stale/quarantined instead of pretending a safe rebuild occurred. Restoring generators is separate process work, not a product or lifecycle gate.

EA-06 stop conditions: recreating retired PRDs to clear anchors; reviving archive ACP/Falkor scripts; deleting unique archaeology; using registry rows to validate R035/R038; inventing active anchors; treating clean counts as product proof.

### D8 — Semantic review protocol

**Depends:** D1–D7.

Для каждого review:

1. deterministic checks;
2. LLM claim extraction с exact citations;
3. entailment classification: support / contradiction / neutral / missing;
4. second independent model или reviewer для consequential findings;
5. human disposition;
6. durable assessment record.

**Exit:** ни один LLM finding не меняет документы без human disposition.

## 9. External practices adopted as patterns

| Source | Adopt/adapt | Что берём | Что не утверждаем |
|--------|-------------|-----------|------------------|
| FINOS CALM Standards/Controls | adapt | JSON Schema composition; requirement vs configuration; controls attached to elements | CALM не становится каноном и не доказывает legal semantics |
| GOV.UK ADR Framework (2025) | adapt | decision levels, stakeholders, escalation, review/approval | не копируем bureaucracy/boards буквально |
| Microsoft Azure WAF ADR | adopt pattern | append-only ADR, supersede+link, confidence, significant decisions only | vendor framework не является project authority |
| ReqToCode (2026 preprint) | adapt later | explicit hard IDs, bidirectional trace, graduated deprecation | не внедряем compile-time traceables на бумажном этапе |
| Audit-as-Code (2026) | adapt | versioned policy + evidence bundle + PASS/WARN/BLOCK + Fix-It | readiness score не является legal/product validation |
| AI-documentation studies | adopt caution | LLM-only review не audit-grade; evidence retrieval/citations + human review | LLM agreement не является proof |
| DECIDER / Structured MADR / adr-kit / adrkit / SARA | candidate patterns | typed metadata, scope, graph validation, selective retrieval | community tooling не является стандартом; adoption не принято |

## 10. Freshness obligations

| Trigger | Обязательное обновление |
|---------|-------------------------|
| ADR status/decision changes | Oracle lifecycle table, ADR index, cross-matrix, affected Contract clauses |
| Product clause changes | Requirements trace + governing ADR review + roadmap impact |
| Milestone close | ARCHITECTURE current front + all active roadmap fronts |
| Derived registry regeneration | source revision + diagnostic-only marker |
| External assessment | freeze SHA, rerun checks, invalidate prior semantic findings on material diff |
| 90 days without material change | human entrypoint review due; не автоматическая деградация lifecycle |

## 11. Definition of done

План коррекции завершён, когда:

- living entrypoints не имеют мёртвых tracked links;
- `.gsd` publication boundary явно описан;
- tracked Product Contract существует;
- temporal semantic crosswalk согласован с ADR-0009/0016–0022;
- roadmap current front синхронизирован;
- derived registry quarantine подтверждён;
- все consequential clauses имеют explicit typed traces;
- LLM semantic review остаётся advisory;
- frozen external assessment packet (см. `prd/migration/external-architecture-assessment-roadmap.md`, EA-00..EA-10 и структуру packet в §6) может быть воспроизведён независимым reviewer;
- ни один документальный PASS не объявляет product/legal readiness.

## 12. Non-claims

- Этот план не реализует governor checks или schemas.
- Он не меняет lifecycle существующих ADR.
- Он не валидирует legal correctness, parser completeness, RuVector runtime, retrieval или citation safety.
- Он не принимает CALM или community ADR tools как dependency.
- Он не возвращает архивные PRD/ACP/FalkorDB surfaces на active plane.
- Он не делает derived registry источником истины.
- Внешняя оценка документации не является product validation.

## 13. Sources (2025–2026 review)

Primary/official:

- FINOS CALM Standards: https://calm.finos.org/core-concepts/standards/
- FINOS CALM Controls: https://calm.finos.org/core-concepts/controls/
- FINOS Architecture as Code: https://github.com/finos/architecture-as-code
- GOV.UK ADR Framework (2025-11-04): https://www.gov.uk/government/publications/architectural-decision-record-framework/architectural-decision-record-framework
- Microsoft Azure Well-Architected ADR: https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record
- ISO/IEC/IEEE CD 15289 (committee draft; pattern only, не принятая норма проекта): https://www.iso.org/standard/94699.html

Research:

- ReqToCode (2026 preprint): https://arxiv.org/html/2603.13999
- Audit-as-Code (2026): https://pmc.ncbi.nlm.nih.gov/articles/PMC12979488/
- AI technical-documentation compliance study (2025): https://link.springer.com/article/10.1007/s10664-025-10645-x

Community patterns (non-standards):

- DECIDER: https://github.com/sventorben/decider
- Structured MADR: https://smadr.dev/
- SARA: https://github.com/cledouarec/sara
- ADRScope: https://github.com/zircote/adrscope
