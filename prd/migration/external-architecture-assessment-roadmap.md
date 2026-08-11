# Roadmap внешней оценки архитектуры и продуктовой документации

**Статус:** `[proposed]` documentation/process roadmap
**Базовая ревизия:** `60fd8245ace999f3f29911844375dd7cc36a2a38`
**Scope:** ADR/PRD/architecture/roadmap/requirements traceability; без product-code реализации
**Primary input:** `prd/architecture/documentation-semantic-control-plan.md`
**Non-claim:** успешная внешняя оценка документов не означает product readiness или legal correctness

## 1. Цель внешней оценки

Получить независимое, revision-bound заключение по вопросам:

1. непротиворечива ли опубликованная authority chain;
2. отделены ли canonical, local, archive и derived surfaces;
3. имеют ли архитектурные и продуктовые утверждения typed traces и proof ceilings;
4. честно ли отражено текущее состояние temporal/applicability architecture;
5. может ли независимый cold reader воспроизвести архитектурную картину без локальной `.gsd`/archive среды;
6. не используется ли LLM/registry/semantic similarity как acceptance authority;
7. готовы ли документы стать контрактом для последующего Rust TDD, не утверждая его наличие.

## 2. Ограничения

Внешний assessor оценивает:

- полноту и непротиворечивость документов;
- качество traceability;
- sufficiency process controls;
- lifecycle honesty;
- reproducibility assessment packet.

Assessor не подтверждает:

- юридическую корректность;
- применимость норм к делу;
- parser completeness;
- CTV/applicability runtime;
- RuVector/TEI readiness;
- citation-safe answers;
- требования R035/R038 только на основании документации.

## 3. Workstreams

| Track | Назначение | Результат |
|-------|------------|-----------|
| A | Published truth repair | cold-reader surface без dead/local-only authority links |
| B | Product Contract | tracked clauses, inputs/outputs, acceptance/non-claims |
| C | Temporal semantic consolidation | единый crosswalk ADR-0009/0016–0022 и gap gates |
| D | Traceability and control catalog | typed edges, lifecycle/proof gates, role separation |
| E | Derived registry quarantine | FalkorDB/ACP era rows не выглядят active authority |
| F | External assessment | frozen packet, independent findings, dispositions |

## 4. Phased roadmap

### Разделение execution и assessment ownership

- `prd/architecture/documentation-semantic-control-plan.md` (D0–D8) — единственный execution track коррекции документов.
- Этот roadmap (EA-00–EA-10) — assessment track: charter, вопросы, exit gates, frozen packet и disposition.
- EA-01..EA-06 не создают вторую копию deliverables; они оценивают результаты соответствующих D-фаз.

| Execution phase | Assessment phase |
|-----------------|------------------|
| D0 | EA-00 |
| D1 | EA-01 |
| D2 | EA-02 |
| D3 | EA-03 |
| D4 | EA-04 |
| D5 + D6 | EA-05 |
| D7 | EA-06 |
| Gate catalog + C0–C7 controls | EA-07 |
| D8 | EA-08 |
| External assessment | EA-09 + EA-10 |

В deliverables ниже перечисляется assessment evidence, ожидаемая от execution phase, а не новая авторская работа assessor.

### EA-00 — Scope and assessor charter

**Depends:** none.
**Goal:** до изменения документов зафиксировать границы оценки.

Deliverables:

- assessment charter;
- source revision;
- authority map;
- known-defect register DOC-01..DOC-10;
- assessor independence statement;
- conflict-of-interest and source-access declaration;
- explicit non-claims.

Acceptance:

- assessor не является единственным автором оцениваемых документов;
- assessment не использует local ignored artifacts как published evidence;
- критерии и severity определены до review.

### EA-01 — Publication surface repair

**Depends:** EA-00.
**Goal:** обеспечить reproducible cold-reader package.

Deliverables:

- исправленные living links;
- `.gsd` local-workflow qualifier;
- зафиксированный tracked publication path и boundary для будущего externally relevant Product Contract / requirements projection; сами contract artifacts публикуются в D2 / EA-02;
- archive-only references с явным qualifier;
- symlink policy.

Assessment questions:

1. Все ли living ссылки разрешаются в tracked SHA?
2. Может ли reader понять current architecture без `.gsd` symlink?
3. Не восстановлены ли старые pre-Rust PRD как active truth?
4. Квалифицированы ли retired ADR IDs?

Exit gate: `published-link-integrity=PASS`; unresolved local-only dependencies отсутствуют.

### EA-02 — Product Contract publication

**Depends:** EA-01.
**Goal:** отделить product intent от architecture status.

Deliverables:

- `prd/PRODUCT.md`;
- personas/human authority;
- user/legal-question loops;
- input/output/error contracts;
- quality attributes;
- legal-error threat model;
- readiness/release criteria;
- non-claims;
- clause IDs and trace table.

Assessment questions:

1. Является ли каждый consequential product claim отдельной clause?
2. Есть ли typed outcome для abstention/Unknown/Conflict?
3. Не объявлена ли capability сильнее evidence?
4. Определена ли human-review boundary?
5. Отличается ли Product Contract от roadmap и ARCHITECTURE?

Exit gate: Product Contract `ready-for-assessment`; clauses не выше текущего proof ceiling. Это readiness состояния документа, не финальный EA-10 disposition.

### EA-03 — Temporal semantic reconciliation

**Depends:** EA-02.
**Goal:** превратить подтверждённую критику в непротиворечивый design contract.

Deliverables:

- `prd/temporal-legal-model.md` crosswalk;
- glossary;
- temporal anchor/event/time distinctions;
- text change vs legal effect;
- force/applicability/knowledge dimensions;
- NormRule/applicability boundary;
- core vs procurement profile boundary;
- invariants;
- unresolved design questions;
- proof-gate matrix;
- staged golden-case catalog.

Assessment questions:

1. Five clocks — роли evidence anchors или смешанная algebra?
2. Разведены ли publication, observation, valid time и applicability?
3. Может ли CTV существовать без automatic InForce?
4. Является ли Applicability core outcome protocol, а procurement — profile facts?
5. Не превращён ли derived NormRule Graph в source truth?
6. Разделены ли deterministic transition resolution и advisory risk?

Exit gate: семантический reviewer и architecture acceptance authority disposition recorded; ontology layers O1–O7 (ADR-0016–0022) остаются `[proposed]`.

### EA-04 — ADR corpus amendment review

**Depends:** EA-03.
**Goal:** привести ADR-0009/0017–0022 к crosswalk без ADR proliferation.

Deliverables:

- proposed amendments/cross-references;
- supersession policy;
- options and consequences;
- stakeholder list;
- one-decision-per-ADR review;
- decision whether a single new NormRule/Applicability ADR is necessary.

Assessment questions:

1. Изменяется ли accepted substance или только clarification?
2. Нужно ли supersede, а не edit in place?
3. Не дублирует ли новый ADR существующие ontology layers O1–O7 (ADR-0016–0022)?
4. Указаны ли negative consequences и revisit triggers?
5. Каждая ли decision scope имеет appropriate acceptance level?

Exit gate: ADR review complete; no package ADR-0023..0032 without separate justification.

### EA-05 — Roadmap and readiness alignment

**Depends:** EA-02–EA-04.
**Goal:** одна current-front история и полный бумажный readiness map.

Deliverables:

- roadmap front после M165;
- исправленные lifecycle mismatches;
- historical/superseded FalkorDB/ACP notes;
- documentation milestones before implementation milestones;
- temporal readiness gates from the single tracked matrix `prd/temporal-legal-model.md` §10–10.1 (TL-G01..12), not from derived readiness views;
- external assessment milestones;
- explicit dependencies and non-claims.

Assessment questions:

1. Совпадает ли current front на всех active roadmap surfaces?
2. Представлены ли design-only layers как `[proposed]`?
3. Есть ли graduation criteria для CTV, applicability, correction, case profile?
4. Не используется ли roadmap completion как implementation proof?

Exit gate: `roadmap-front-sync=PASS`; readiness map covers all acknowledged semantic gaps.

### EA-06 — Derived registry quarantine

**Depends:** EA-05.
**Goal:** derived surfaces полезны для диагностики, но не создают альтернативную истину.

Deliverables:

- registry authority policy;
- source revision/freshness marker;
- historical status for obsolete FalkorDB/ACP/PyO3 rows;
- removal/reclassification of missing active anchors;
- forbidden edge rules;
- safe regeneration plan.

Assessment questions:

1. Можно ли пройти от registry row к accepted claim без canonical clause/human acceptance?
2. Содержат ли generated views non-authoritative banners?
3. Являются ли obsolete rows historical/superseded?
4. Не скрывает ли clean registry отсутствие product proof?

Exit gate: `derived-registry-quarantine=PASS`; staleness findings documented.

### EA-07 — Deterministic control rehearsal

**Depends:** EA-01–EA-06.
**Goal:** вручную применить бумажный gate catalog из §7 control-plan к frozen corpus; реализация CI/governor checks остаётся вне scope.

Required checks:

- tracked link integrity;
- schema/section conformance;
- unique IDs;
- reciprocal supersession;
- typed edge integrity;
- lifecycle ceiling;
- proof-class sufficiency;
- non-claim preservation;
- roadmap front sync;
- era/noise and retired-ID policy;
- registry quarantine;
- temporal readiness coverage.

Assessment output:

```text
PASS  — requirement structurally met
WARN  — bounded debt; must be in packet
BLOCK — acceptance cannot proceed
```

Exit gate: no BLOCK при ручном checklist review; каждая строка содержит `method=paper-rehearsal`, а WARN — owner, remediation и revisit trigger. Это не automated-gate evidence.

### EA-08 — LLM semantic review rehearsal

**Depends:** EA-07.
**Goal:** использовать LLM только для поиска free-text contradictions.

Protocol:

1. atomize consequential claims;
2. require exact source spans;
3. compare across Product/ADR/Oracle/Roadmap;
4. classify support / contradiction / neutral / missing;
5. use independent second reviewer/model for high-impact candidate;
6. human disposition;
7. map confirmed finding to deterministic rule or explicit human decision.

Rules:

- LLM output = `ADVISORY`;
- no lifecycle promotion/demotion automatically;
- no numeric confidence as proof;
- missing citation → reject finding or request evidence;
- disagreement remains visible.

Exit gate: every semantic finding has disposition and exact evidence; no automated authority.

### EA-09 — Independent external desk assessment

**Depends:** EA-07, EA-08.
**Goal:** независимый reviewer перепроверяет frozen packet.

Assessment modes:

| Mode | Scope |
|------|-------|
| Artifact | files, schemas, links, lifecycle, trace graph |
| Semantic | sampled claims, contradictions, non-claims, terminology |
| Process | roles, acceptance, supersession, freshness obligations |
| Reproducibility | rerun deterministic checks at frozen SHA |

Required sample chains:

```text
Product clause → Requirement → ADR → Oracle claim → Roadmap → Evidence class
```

Минимум по одной цепочке для:

- Rust-only runtime;
- Python harness boundary;
- parser/provider separation;
- five-clock safety;
- temporal ontology O1–O7 (ADR-0016–0022);
- NormRule/applicability gap;
- RuVector proposed boundary;
- LLM non-authority;
- procurement profile boundary.

Exit gate: external report issued with findings and non-claims.

### EA-10 — Human disposition and publication

**Depends:** EA-09.
**Goal:** acceptance authority обрабатывает external findings.

Allowed dispositions:

- `accepted-for-process`;
- `accepted-with-findings`;
- `rejected-needs-remediation`;
- `superseded-by-new-assessment`.

Forbidden:

- `product-validated`;
- `legal-correctness-validated`;
- automatic acceptance from all-green tools.

Exit gate: signed disposition; unresolved findings mapped to roadmap; packet published at frozen SHA.

## 5. Dependency map

```text
EA-00
  └─ EA-01
       └─ EA-02
            └─ EA-03
                 └─ EA-04
                      └─ EA-05
                           └─ EA-06
                                └─ EA-07
                                     └─ EA-08
                                          └─ EA-09
                                               └─ EA-10
```

Параллельная работа допустима только внутри фазы и только после фиксации freeze criteria. Semantic review не начинается до deterministic rehearsal.

## 6. External assessment packet

Рекомендуемая структура:

```text
assessment/
├── 00-charter.md
├── 01-authority-map.md
├── 02-product-contract.md (copy/reference)
├── 03-adr-inventory.md
├── 04-traceability-matrix.md
├── 05-roadmap-and-readiness.md
├── 06-deterministic-gates.md
├── 07-semantic-findings.md
├── 08-known-defects.md
├── 09-independent-report.md
└── 10-human-disposition.md
```

Metadata:

```text
source_revision
assessment_date
assessor_identity/role
models/tools used
presented source set
excluded sources
known limitations
finding counts by PASS/WARN/BLOCK/ADVISORY
supersedes assessment id
```

Secrets, raw provider payloads, ignored `.gsd/exec` paths и raw legal corpus не публикуются.

## 7. Assessor checklist

### Authority

- [ ] ARCHITECTURE/ADR/Product Contract roles не конфликтуют.
- [ ] Derived registry не является authority.
- [ ] `.gsd` local-only граница указана.
- [ ] Archived/retired surfaces квалифицированы.

### Lifecycle

- [ ] Oracle lifecycle не сильнее ADR.
- [ ] Product clauses не сильнее proof class.
- [ ] Supersession append-only и reciprocal.
- [ ] Нет `[validated]` product claim из synthetic/static proof.

### Traceability

- [ ] Consequential clauses имеют explicit IDs.
- [ ] Requirement/ADR/roadmap/evidence edges разрешаются.
- [ ] Нет dangling/orphan authority edges.
- [ ] Semantic similarity не используется как primary link.

### Temporal/applicability

- [ ] Safety boundary отделён от temporal computation.
- [ ] CTV design отделён от runtime claim.
- [ ] Force/applicability/knowledge разделены.
- [ ] NormRule/applicability gaps признаны.
- [ ] Procurement является profile, не core contamination.

### AI-assisted review

- [ ] LLM findings advisory.
- [ ] Exact citations обязательны.
- [ ] High-impact findings независимо перепроверены.
- [ ] Human disposition recorded.

### Freshness

- [ ] Roadmap front соответствует frozen revision.
- [ ] Derived views имеют source revision.
- [ ] Assessment invalidation policy определена.

## 8. Success criteria

Roadmap считается выполненным, когда:

1. внешний reviewer может клонировать frozen SHA и найти весь пакет;
2. living links не требуют локальных vault/GSD surfaces;
3. Product Contract и temporal crosswalk опубликованы;
4. ADR amendments согласованы без массового proliferation;
5. typed trace graph имеет zero unresolved authority edges;
6. roadmap/readiness отражают все подтверждённые semantic gaps;
7. derived registry изолирован;
8. deterministic checks reproducible;
9. LLM findings имеют human dispositions;
10. external report явно сохраняет product/legal non-claims.

## 9. Stop conditions

Остановить и replan, если:

- предлагается принять CALM/community tool до local fit assessment;
- schema начинает заменять человеческое решение;
- LLM-only finding используется как BLOCK;
- registry становится более авторитетным, чем source docs;
- external reviewer требует вернуть archive PRD как active truth;
- roadmap маскирует отсутствие implementation;
- numeric completeness/readiness score используется для lifecycle promotion;
- документальная работа начинает проектировать product runtime вместо фиксации контрактов.

## 10. Suggested review cadence

| Событие | Review |
|---------|--------|
| завершение документационной фазы | internal semantic review |
| изменение ADR lifecycle/Product clause | targeted external sample review при consequential scope |
| material architecture milestone | refresh packet + deterministic rerun |
| каждые 90 дней без material change | human freshness review due |
| перед implementation milestone | independent architecture readiness review |
| после significant external finding | remediation assessment at new SHA |

Это обязательства (obligations), а не гарантии качества и не readiness scores.

## 11. Evidence basis

Official/framework sources:

- FINOS CALM: https://calm.finos.org/
- CALM Standards: https://calm.finos.org/core-concepts/standards/
- CALM Controls: https://calm.finos.org/core-concepts/controls/
- GOV.UK ADR Framework: https://www.gov.uk/government/publications/architectural-decision-record-framework/architectural-decision-record-framework
- Microsoft Azure WAF ADR: https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record
- ISO/IEC/IEEE CD 15289 (committee draft; pattern only, не принятая норма проекта): https://www.iso.org/standard/94699.html

Research:

- ReqToCode: https://arxiv.org/html/2603.13999
- Audit-as-Code: https://pmc.ncbi.nlm.nih.gov/articles/PMC12979488/
- AI documentation compliance study: https://link.springer.com/article/10.1007/s10664-025-10645-x

Community patterns (evaluation candidates only):

- DECIDER: https://github.com/sventorben/decider
- Structured MADR: https://smadr.dev/
- SARA: https://github.com/cledouarec/sara
- ADRScope: https://github.com/zircote/adrscope

## 12. Non-claims

- Roadmap не реализует checks, schemas, CI или product code.
- Он не принимает внешний framework как project canon.
- Он не утверждает эффективность community tools.
- Он не подтверждает legal correctness или readiness.
- Он не повышает lifecycle ADR-0016–0022.
- Он не заменяет human architecture acceptance.
