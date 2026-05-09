# 4. Review Findings: анализ целостности PRD

> **Назначение документа.** Трекинг несоответствий, пропусков и рекомендаций, выявленных при ревью файлов `01_general_idea.md`, `02_architecture.md`, `03_PRD.md`. Документ живой — статусы пунктов обновляются по мере исправления.
>
> **Дата ревью:** 2026-05-09
> **Объект ревью:** `prd/01_general_idea.md`, `prd/02_architecture.md`, `prd/03_PRD.md`

---

## 0. Легенда статусов

| Статус | Значение |
|---|---|
| `OPEN` | Найдено, не исправлено |
| `IN_PROGRESS` | Принято к работе |
| `FIXED` | Исправлено в PRD |
| `DEFERRED` | Сознательно отложено (с обоснованием) |
| `WONTFIX` | Не будет исправляться (с обоснованием) |

| Severity | Значение |
|---|---|
| `BLOCKER` | Должно быть исправлено до начала разработки |
| `MAJOR` | Должно быть исправлено до конца Phase 1 |
| `MINOR` | Желательно для зрелости PRD |

---

## 1. Общая оценка

### Сильные стороны

- Сквозная философия: *deterministic-first, evidence-first, graph-first, temporal-first, LLM non-authoritative*. Идея последовательно проходит через все три документа.
- Хорошо проработанная иерархия данных (`LegalAct → ActEdition → Chapter → Article → Part → Clause → SubClause → Paragraph`).
- Явное разделение ответственности: JS UDF (простые операции в FalkorDB) vs Python LegalNexus (оркестрация).
- Раздел «candidate ideas requiring validation» (3b, 9b, FR-30b, §13) — зрелая инженерная практика отделения гипотез от подтверждённых требований.
- Декомпозиция retrieval-сигналов с весами (структурный/граф/BM25/vector/YAKE/temporal/evidence).
- `no_answer` как первоклассный ответ (FR-29) — защита от галлюцинаций.
- Multi-representation text fields (FR-17) — сильное инженерное решение.

### Проблемные зоны (резюме)

- Структурные дефекты файла `03_PRD.md` (повреждённый раздел §10).
- Несоответствия в графовой модели между документами.
- Двусмысленность `LegalAct` как «базовый тип vs подтип `LegalDocument`».
- Нечёткая граница между MVP (Scope §7) и FR-21…FR-28 (которые фактически выходят за MVP).
- Не определены ключевые контракты: формат embedding, схемы JSONL, формат KnowQL-грамматики, версионирование UDF API.

---

## 2. Конкретные несоответствия и баги

### F-001 · Сломанная структура `03_PRD.md` §10

- **Severity:** BLOCKER
- **Status:** FIXED
- **Fixed in S07/T01:** Removed the stray NFR-8 JSON fragment and duplicate `## 10. Target data model` heading; `03_PRD.md` now has one canonical §10 target data model section.
- **Файл:** `03_PRD.md`, строки ~813–823

Между NFR-9 и §10 вставлен фрагмент, который явно «вылез» из NFR-8 (повторение JSON-блока, дубликат заголовка `## 10. Target data model`):

```
строки 813–823:
    "bm25": 0.74,
    "vector": 0.79,
    ...
## 10. Target data model
```

Раздел `## 10. Target data model` встречается дважды.

**Действие.** Удалить мусорный блок (строки ~814–822) и оставить единственный `## 10. Target data model`.

---

### F-002 · Несовпадение списка labels между `02_architecture.md` и `03_PRD.md`

- **Severity:** MAJOR
- **Status:** FIXED
- **Fixed in S07/T02:** `02_architecture.md` now includes `LegalDocument` and `ContentDomain` in the authoritative label list, defines `LegalDocument` as a FalkorDB multi-label base type, and requires `document_type`. `03_PRD.md` §10 now mirrors the base-label pattern and adds the missing `LegalDocument`, `ContentDomain`, and `Reference` nodes alongside existing `KeyPhrase` and `AutoTag` nodes.
- **Файлы:** `02_architecture.md` строки 102–125, `03_PRD.md` §10, `01_general_idea.md` §13e

В `02_architecture.md` перечислены labels включая `Condition`, `Exception`, `Deadline`, `Reference`, но **отсутствует `LegalDocument`**, хотя §13e и `01_general_idea.md` объявляют его базовым типом.

В `03_PRD.md`:
- FR-28 говорит про `LegalDocument` как базовый тип,
- но в §10 (ER-диаграмма) `LegalDocument` отсутствует — есть только `LegalAct`.

**Несоответствие.** Концептуально декларируется extensibility через `LegalDocument`, но в графовой модели его нет. Не определено, как `LegalAct ↔ LegalDocument` соотносятся (наследование? тег? отдельный node с relationship `IS_A`?).

**Действие.** Явно описать в `02_architecture.md` раздел «extensible base type pattern» — например:
- `LegalDocument` это **label**, который ставится на каждом `LegalAct`/`CaseLaw`/`PracticeDocument` (multi-label подход FalkorDB);
- свойство `document_type` ∈ {`legal_act`, `case_law`, `practice_document`} обязательно;
- обновить ER-диаграмму в `03_PRD.md` §10.

---

### F-003 · Несовпадающие relationships

- **Severity:** MAJOR
- **Status:** FIXED
- **Fixed in S07/T02:** Added `HAS_BLOCK` and `HAS_DOMAIN` to the authoritative relationship list in `02_architecture.md`; reconciled the target graph to use `HAS_BLOCK`, `HAS_DOMAIN`, and `REFERS_TO` consistently. `VERSION_OF`, `SUPERSEDES`, and `AMENDED_BY` are explicitly documented as deferred post-MVP temporal/versioning relationships until S08/later temporal modeling defines event semantics.
- **Файлы:** `02_architecture.md` строки 129–151, `03_PRD.md` §10

В `02_architecture.md` объявлен `HAS_BLOCK`, но в перечне relationships (строки 129–151) его **нет** — есть только `CONTAINS`, `DERIVED_FROM`, `HAS_CHUNK` и т.д. При этом в графе (строка 157) и в ER в `03_PRD.md` (`SourceDocument ||--o{ SourceBlock : HAS_BLOCK`) он используется.

Аналогично `VERSION_OF`, `SUPERSEDES`, `AMENDED_BY` объявлены, но не упомянуты ни в одной диаграмме и не покрыты ни одним FR.

**Действие.** Добавить `HAS_BLOCK` (или `CONTAINS_BLOCK`) в общий список relationships. Провести аудит: каждый relationship должен встречаться (a) в общем списке, (b) хотя бы в одной диаграмме, (c) хотя бы в одном FR.

---

### F-004 · Конфликт направления/кардинальности в ER-диаграмме `03_PRD.md` §10

- **Severity:** MAJOR
- **Status:** FIXED
- **Fixed in S07/T02:** `03_PRD.md` §10 now uses `ActEdition }o--|| SourceDocument : DERIVED_FROM`, matching the architecture diagram semantics that an edition is derived from one source document. The surrounding text notes `Reference` resolution and multi-label document semantics separately.
- **Файл:** `03_PRD.md` §10

```
SourceDocument ||--o{ ActEdition : DERIVED_FROM
```

По логике стрелка обратная: `ActEdition --DERIVED_FROM--> SourceDocument` (редакция «происходит из» документа). В диаграмме `02_architecture.md` строка 159: `ED -->|DERIVED_FROM| SD` — корректно.

Кардинальность `||--o{` ставит SourceDocument как «one», ActEdition как «many» — спорная семантика, потому что одна редакция обычно соответствует одному источнику.

**Действие.** Уточнить кардинальности и направление. Скорее всего нужно `ActEdition }o--|| SourceDocument`.

---

### F-005 · MVP scope: WordML вместо ODF

- **Severity:** BLOCKER
- **Status:** FIXED
- **Fixed in S07/T01:** Replaced MVP wording with `ODF/ODT XML extraction (content.xml via odfpy)` to match FR-2 and the Garant ODT verification target.
- **Файл:** `03_PRD.md` §7

В `03_PRD.md` §7 «Входит в MVP» написано:
> WordML XML extraction;

Но FR-2 и весь остальной документ (включая `02_architecture.md` §13) говорят про **ODT/odfpy**. WordML — это формат `.docx` (OOXML), это **другой формат**. ODT использует ODF (OpenDocument), а не WordML.

**Действие.** Заменить на `ODF/ODT XML extraction (content.xml via odfpy)`.

---

### F-006 · FR-21 — дублирующий список функций

- **Severity:** BLOCKER
- **Status:** FIXED
- **Fixed in S07/T01:** Removed the duplicate Legal Nexus function bullet list after the Python class example, keeping one canonical list before the example.
- **Файл:** `03_PRD.md` FR-21, строки 514–524 и 549–557

В FR-21 (Legal Nexus Module) список функций приведён **дважды** — до и после блока кода Python. Очевидно, остаток от слияния правок.

**Действие.** Удалить дубль.

---

### F-007 · Расхождение «UDF в JS» vs «Python методы»

- **Severity:** MAJOR
- **Status:** OPEN
- **Файлы:** `02_architecture.md` §7, §13c; `03_PRD.md` FR-24

В FR-24 (`03_PRD.md`) написано:
```
JavaScript UDF в FalkorDB:
  legal.active_at, legal.format_citation, legal.get_norm_id
Python методы в LegalNexus:
  legal.find_requirements, legal.verify_evidence, ...
```

Но `02_architecture.md` §7 перечисляет `legal.active_at`, `legal.find_requirements`, `legal.verify_evidence`, `legal.build_context` и т.д. **под общим списком** «Ключевые процедуры», без разделения на JS/Python.

**Действие.** В `02_architecture.md` §7 ввести табличку:

| Имя | Слой | Реализация | Возвращает |
|---|---|---|---|
| `legal.active_at(node_id, date)` | UDF | JS in FalkorDB | enum |
| `legal.format_citation(node_id)` | UDF | JS in FalkorDB | string |
| `legal.find_requirements(...)` | Nexus | Python | EvidencePack |
| ... | | | |

---

### F-008 · Roadmap vs MVP scope: embeddings

- **Severity:** MAJOR
- **Status:** FIXED
- **Fixed in S07/T03:** Added a `FR-to-phase scope matrix` in `03_PRD.md` §7 covering FR-21 through FR-30b; marked FR-28b embeddings/FalkorDB vector index as post-MVP and research-gated; updated §13 roadmap wording so Phase 3–5 items are directional post-MVP scope rather than immediate MVP commitments. Related implementation details remain tracked separately by G-002, G-011, and R-001.
- **Файлы:** `03_PRD.md` §7, FR-28b, §13; `02_architecture.md` §13d

§7 PRD previously said that embeddings/vector were outside MVP, while FR-28b made embeddings look mandatory and Roadmap (§13) placed embeddings/vector index in Phase 5 without a clear phase contract.

**Действие.** Keep the §7 matrix as the source of truth for MVP vs post-MVP vs candidate research. Do not promote embedding generation, FalkorDB vector index creation, or hybrid vector retrieval into MVP implementation unless a later validation milestone explicitly narrows and promotes that scope.

---

### F-009 · Веса retrieval-формулы и значение `evidence_confidence`

- **Severity:** MINOR
- **Status:** OPEN
- **Файлы:** `02_architecture.md` §9, `03_PRD.md` NFR-8

Сумма весов `0.25 + 0.20 + 0.15 + 0.15 + 0.10 + 0.10 + 0.05 = 1.00` ✓

Но `evidence_confidence: 0.05` слишком низкий вес для системы, в которой evidence — главный принцип. Либо это вес «уверенности» (а не «значимости»), и тогда нужно пояснить в комментарии, либо его надо повысить.

**Действие.** В §9 добавить пояснение: «`evidence_confidence` — это коэффициент *штрафа/бонуса* для уже отфильтрованных по evidence кандидатов; кандидаты без evidence отбрасываются hard-cut’ом до scoring».

---

### F-010 · Temporal-модель: семантика `valid_*` vs `effective_*`

- **Severity:** MAJOR
- **Status:** OPEN
- **Файлы:** `02_architecture.md` §3, `03_PRD.md` FR-9

В §3 architecture и FR-9:
```
edition_date, valid_from, valid_to, effective_from, effective_to, status
```

Не объяснено различие между `valid_*` и `effective_*`. В русской правовой традиции часто это синонимы; в международной — `valid` (формально действующая) vs `effective` (применяемая на практике). Без фиксации UDF `legal.active_at` будет реализован произвольно.

**Действие.** Добавить glossary в §3 (новый подраздел 3a):
- `valid_from/valid_to` — период юридической силы (от вступления до утраты);
- `effective_from/effective_to` — период применения (например, переходные положения);
- `edition_date` — дата фиксации редакции в источнике (Гарант).

---

### F-011 · NormStatement: модальность vs тип

- **Severity:** MAJOR
- **Status:** OPEN
- **Файл:** `03_PRD.md` FR-14

FR-14 объявляет:
- `type ∈ {definition, requirement, obligation, prohibition, permission, ...}`
- `modality ∈ {must, must_not, may, is_defined_as, ...}`

Эти оси **не ортогональны**: `prohibition` практически всегда `must_not`, `obligation`/`requirement` всегда `must`. Получается, что модальность можно вывести из типа в большинстве случаев, что вызовет рассинхронизацию (обе оси заполнены — какая авторитетна?).

**Действие.** Определить, какая ось primary, и сделать вторую — derived. Например:
- primary: `modality` (must/must_not/may/is_defined_as) + `subject_type` (requirement/permission/...);
- ИЛИ оставить обе, но описать матрицу совместимости и валидатор.

---

### F-012 · Формат идентификаторов: несовместимости

- **Severity:** MAJOR
- **Status:** OPEN
- **Файл:** `03_PRD.md` FR-6

```
id = "ru_fz_44_edition_2025_12_28_article_31_part_1_clause_4"
citation_key = "44fz:2025-12-28:art31:part1:clause4"
```

Проблемы:
- `id` использует `_` как разделитель, и часть `2025_12_28` плохо парсится (даты с подчёркиваниями неоднозначны);
- `citation_key` использует `:` — могут быть проблемы при использовании в URL или Cypher;
- не определена нормализация для актов с буквами в номере (например, `№ 273-ФЗ-1`);
- не определена политика для актов **без** номера (региональные акты, нормативные письма).

**Действие.** Ввести формальную BNF-грамматику ID и citation_key, добавить регэкспы для валидации, и обработку edge-cases (буквенные суффиксы, подзаконные акты, утратившие силу).

---

### F-013 · Citation_label: локаль и формат

- **Severity:** MINOR
- **Status:** OPEN
- **Файл:** `03_PRD.md` FR-6

`"п. 4 ч. 1 ст. 31 44-ФЗ"` — это русская правовая традиция. Не описано:

- что делать с международными актами;
- как форматировать в латинице (для логов, тестов);
- какой порядок частей (`п. ч. ст.` vs `ст. ч. п.`) — в России используются оба;
- citation_label vs path — оба `human-readable`, но один наоборот: `path = "44-ФЗ / Статья 31 / Часть 1 / Пункт 4"`.

**Действие.** Добавить FR-6b «Citation formatting policy» с явным правилом и тестами.

---

### F-014 · KnowQL: нет грамматики, синтаксис расходится между документами

- **Severity:** BLOCKER
- **Status:** OPEN
- **Файлы:** `01_general_idea.md`, `02_architecture.md` §6, `03_PRD.md` FR-22

Примеры KnowQL разные в трёх документах:
- `01_general_idea.md`: `FIND requirements FOR subject "..." IN act "..." AT date "..." RETURN ...`
- `02_architecture.md`: `GET norm WHERE act = "44-ФЗ" AND article = "31" ... AT "..." RETURN ...`
- `03_PRD.md` FR-22: `GET norm WHERE act="44-ФЗ" AND article="31"`

Несовместимый синтаксис: `IN act "..."` vs `WHERE act="..."`, `AT date "..."` vs `AT "..."`.

**Действие.** В FR-22 зафиксировать формальную грамматику KnowQL (EBNF или ANTLR), с примерами, токенизацией и приоритетом операторов. Привести все документы к единому синтаксису.

---

### F-015 · Validation: не определён вывод

- **Severity:** MAJOR
- **Status:** OPEN
- **Файлы:** `03_PRD.md` FR-20, `02_architecture.md` §12

FR-20 и §12 architecture перечисляют **что** проверять, но не определяют:
- формат `14_validation_report.json`;
- severity levels (ERROR / WARNING / INFO);
- блокирующие/неблокирующие проверки;
- exit code семантику;
- что значит «valid Cypher» — синтаксис? Можно ли его проверить без запуска FalkorDB?

**Действие.** Добавить FR-20a «Validation report schema» с конкретной JSON Schema.

---

### F-016 · Idempotency vs SHA-256: нет политики

- **Severity:** MAJOR
- **Status:** OPEN
- **Файлы:** `03_PRD.md` NFR-4, FR-1

NFR-4 декларирует idempotency, FR-1 требует SHA-256. Но не описана связь:
- Если файл импортируется повторно с тем же SHA — что происходит? skip / merge / replace?
- Если файл изменился (тот же `act_number`, новая `edition_date`, новая SHA) — это новая `ActEdition` или обновление существующей?
- Что с `imported_at`? Каждое повторение перезаписывает?

**Действие.** Ввести FR-1a «Idempotent import policy» с диаграммой состояний.

---

## 3. Пропуски / отсутствующие разделы

| # | Что пропущено | Где должно быть | Severity | Status |
|---|---|---|---|---|
| G-001 | Безопасность и доступы к FalkorDB, KnowQL endpoint, audit log read access | Новый NFR-10 | MAJOR | OPEN |
| G-002 | Формат `12_embeddings.jsonl` — структура, как связан с TextChunk | FR-19 / FR-28b | MAJOR | OPEN |
| G-003 | Версионирование UDF API — что если `legal.find_requirements` v1 → v2? | `02_architecture.md` §7 | MAJOR | OPEN |
| G-004 | Migration / backfill — как добавить новое поле к 100k legal units | NFR / отдельный FR | MAJOR | OPEN |
| G-005 | Стратегия конфликтов между редакциями (две `ActEdition` за одну дату) | `02_architecture.md` §3 | MAJOR | OPEN |
| G-006 | Обработка ошибок KnowQL (синтаксис, неизвестная статья, неоднозначность) | FR-22 | MAJOR | OPEN |
| G-007 | Метрики наблюдаемости (latency, throughput, p50/p99) для Nexus API | NFR-7 / новый NFR-11 | MINOR | OPEN |
| G-008 | Тестовые контракты: golden tests на парсинг 44-ФЗ, baseline retrieval recall | FR-30 | MAJOR | OPEN |
| G-009 | Стратегия для подзаконных актов и приложений (часто отсутствуют главы — только статьи) | FR-5 | MAJOR | OPEN |
| G-010 | Сноски, примечания, табличный материал — как они становятся `SourceBlock`? | FR-2 / FR-3 | MAJOR | OPEN |
| G-011 | Языковая политика — NFR-5 локально, но embedding-модель `deepvk/USER-bge-m3` тянет HuggingFace; offline-режим? | NFR-5 / `02_architecture.md` §13d | MINOR | OPEN |
| G-012 | Разделение ответственности при множественных source provenance (FR-30b упоминает, но не разворачивает) | `02_architecture.md` §3 / FR-1 | MINOR | OPEN |
| G-013 | Lifecycle EvidenceSpan при изменении источника (новая SHA → старые EvidenceSpan устаревают?) | FR-7 / NFR-4 | MAJOR | OPEN |
| G-014 | Чанк-стратегия — упомянут «sliding window vs clause-aligned», но MVP-чанкер не специфицирован | FR-8 / `02_architecture.md` §9b | MAJOR | OPEN |
| G-015 | Failure modes для FalkorDBLite → Docker миграции | `02_architecture.md` §13b | MINOR | OPEN |

---

## 4. Архитектурные риски

### R-001 · FalkorDB как vector store

- **Severity:** MAJOR
- **Status:** OPEN
- **Файл:** `02_architecture.md` §13d

§13d: «no external vector store required, FalkorDB vector index, dim=1024».

- FalkorDB поддерживает векторные индексы, но при больших корпусах (Phase 5: ГК + ФАС + судебная практика → миллионы chunks × 1024 float32 ≈ 4 ГБ embeddings) может стать узким местом.
- Не указан HNSW/IVF параметризм (M, efConstruction, ef).

**Действие.** Добавить FR-28c с конкретными параметрами индекса и стратегией fallback на внешний vector store (Qdrant/pgvector) если FalkorDB не справится.

---

### R-002 · GraphBLAS layer без указания библиотеки

- **Severity:** MAJOR
- **Status:** OPEN
- **Файл:** `02_architecture.md` §8

§8: GraphBLAS algorithms — но не указано:
- какой биндинг (`pygraphblas`, `python-graphblas`, `SuiteSparse:GraphBLAS` напрямую через Cython)?
- как граф из FalkorDB транслируется в GraphBLAS-матрицу (export/import overhead)?
- какая частота пересборки матриц при изменениях графа?

**Действие.** Добавить §8b «GraphBLAS integration model» — кэш матриц, инвалидация, технология.

---

### R-003 · JS UDF в FalkorDB — ограничения

- **Severity:** MINOR
- **Status:** OPEN
- **Файл:** `02_architecture.md` §13c

FalkorDB UDF на JS работают в sandboxed runtime — ограничены по памяти, нет async I/O. Сложные процедуры типа `legal.format_citation` с lookup нескольких узлов могут оказаться неприемлемо медленными.

**Действие.** В §13c явно описать, какие операции **нельзя** делать в JS UDF (cross-node traversal с условиями, агрегация по большим выборкам).

---

### R-004 · Legal YAKE — реализация не специфицирована

- **Severity:** MAJOR
- **Status:** OPEN
- **Файл:** `03_PRD.md` FR-15

FR-15 объявляет требования (русский, n-граммы 1-7, legal stop-list), но:
- какой базовый алгоритм YAKE (классический Campos 2018)?
- legal stop-list — кто его курирует, где хранится?
- где legal_glossary файл?
- как замеряется качество keyphrases?

**Действие.** Добавить FR-15a «Legal YAKE specification» с алгоритмическим описанием и форматом stop-list/glossary файлов.

---

### R-005 · Связь NormStatement ↔ LegalUnit неоднозначна

- **Severity:** MAJOR
- **Status:** OPEN
- **Файл:** `02_architecture.md` §2 (граф), `03_PRD.md` FR-14, FR-27

В графе:
```
NS -->|DERIVED_FROM| PT
NS -->|SUPPORTED_BY| EV
```

- `NormStatement` происходит **из Part**, но реальная норма может занимать несколько Part или, наоборот, быть кусочком одной Part (одно условие, одно исключение).
- Если NormStatement extractor — это LLM-кандидат (FR-27 разрешает `norm_statement_extraction: llm_allowed_if_verified`), как происходит верификация?

**Действие.** Ввести `NormStatement.extraction_method ∈ {deterministic, llm_candidate, manual}` и `NormStatement.verification_status` явно. В `02_architecture.md` добавить отдельный flow для верификации NormStatement.

---

### R-006 · ContentDomain — концепт без чёткого определения

- **Severity:** MAJOR
- **Status:** FIXED
- **Fixed in S07/T02:** `02_architecture.md` and `03_PRD.md` now define `ContentDomain` as a first-class node, connected from `LegalDocument` with M:N `HAS_DOMAIN`; every document requires at least one domain and the MVP default is `normative_acts`.
- **Файл:** `02_architecture.md` §13e

В §13e architecture: `ContentDomain` — first-class, перечислены значения. Но:
- это label или property?
- может ли документ принадлежать нескольким доменам (например, ФАС + закупки)?
- обязателен ли при импорте?

**Действие.** Уточнить кардинальность (`document HAS_DOMAIN domain`, M:N) и сделать обязательным с дефолтом.

---

## 5. План действий (TODO для следующей итерации PRD)

### 5.1. Блокирующие (must-fix перед началом разработки)

- [x] **F-001** — Починить структуру `03_PRD.md`: удалить мусорный фрагмент в §10 и дубликат заголовка.
- [x] **F-005** — Заменить «WordML» → «ODF/ODT» в §7 PRD MVP.
- [x] **F-006** — Удалить дубль списка функций в FR-21.
- [ ] **F-014** — Унифицировать KnowQL грамматику (BNF/EBNF) и зафиксировать в FR-22.
- [x] **F-002 / F-003** — Зафиксировать единый список node labels и relationships, синхронизированный с ER в §10 и mermaid в §1.
- [x] **F-002** — Решить вопрос `LegalDocument` vs `LegalAct` (multi-label или иерархия наследования).
- [x] **F-002 / F-004** — Расширить ER `03_PRD.md` §10: добавить `LegalDocument`, `ContentDomain`, `Reference`, `KeyPhrase`, `AutoTag`; исправить кардинальности.

### 5.2. Важные (до конца Phase 1)

- [ ] **F-010** — Glossary temporal-полей (`valid_*` vs `effective_*`).
- [ ] **F-007** — Контракт UDF API: таблица «имя / слой / контракт / возвращаемый тип».
- [ ] **G-002 / F-015** — JSON Schema для всех 17 файлов import package, включая `12_embeddings.jsonl` и `14_validation_report.json`.
- [ ] **F-016** — Idempotency policy: что происходит при повторном импорте.
- [x] **F-008** — MVP↔Roadmap matrix: таблица «FR → фаза».
- [ ] **F-011** — NormStatement type/modality: матрица совместимости + валидатор.
- [ ] **F-012** — BNF citation_key + ID, регэкспы, edge-cases.
- [ ] **R-005** — `NormStatement.extraction_method` и `verification_status`.
- [x] **R-006** — `ContentDomain` уточнение (label/property, кардинальность).
- [ ] **G-005** — Стратегия конфликтов между редакциями.
- [ ] **G-009** — Стратегия для подзаконных актов / приложений.
- [ ] **G-010** — Сноски, примечания, таблицы как `SourceBlock`.
- [ ] **G-013** — Lifecycle EvidenceSpan при изменении источника.
- [ ] **G-014** — Чанк-стратегия для MVP.

### 5.3. Желательные (для зрелости)

- [ ] **R-001** — FR-28c: параметры vector index + fallback стратегия.
- [ ] **R-002** — §8b: GraphBLAS integration model.
- [ ] **R-003** — Ограничения JS UDF в `02_architecture.md` §13c.
- [ ] **R-004** — FR-15a: Legal YAKE algorithmic spec.
- [ ] **G-001** — NFR-10: Security (авторизация, audit log access).
- [ ] **G-007** — NFR-11: Observability (Prometheus metrics, traces).
- [ ] **G-004** — Migration/backfill policy для эволюции схемы.
- [ ] **G-006** — Обработка ошибок KnowQL.
- [ ] **G-011** — Языковая политика / offline-режим для embedding-модели.
- [ ] **G-012** — Source provenance: разворот концепции из FR-30b.
- [ ] **G-015** — Failure modes для FalkorDBLite → Docker миграции.
- [ ] **F-009** — Пояснение веса `evidence_confidence` в формуле scoring.
- [ ] **F-013** — FR-6b: Citation formatting policy.

---

## 6. Сводная таблица: что и где править

| Issue ID | Файл | Раздел | Проблема | Severity |
|---|---|---|---|---|
| F-001 | `03_PRD.md` | §10 (стр. 813–823) | Сломанная склейка | BLOCKER |
| F-002 | `02_architecture.md`, `03_PRD.md` | §02 labels / §10 ER | Нет `LegalDocument` в графе | MAJOR |
| F-003 | `02_architecture.md` | строки 102-151 | `HAS_BLOCK` не в списке | MAJOR |
| F-004 | `03_PRD.md` | §10 ER | Неверное направление `DERIVED_FROM` | MAJOR |
| F-005 | `03_PRD.md` | §7 MVP scope | «WordML» вместо ODF | BLOCKER |
| F-006 | `03_PRD.md` | FR-21 | Дубль функций | BLOCKER |
| F-007 | `02_architecture.md` | §7 UDF | Нет разделения JS/Python | MAJOR |
| F-008 | `03_PRD.md` | §7, FR-28b, §13 | embeddings: MVP vs Phase 5 | MAJOR |
| F-009 | `02_architecture.md`, `03_PRD.md` | §9 / NFR-8 | `evidence_confidence` низкий вес | MINOR |
| F-010 | `02_architecture.md`, `03_PRD.md` | §3 / FR-9 | `valid_*` vs `effective_*` неясно | MAJOR |
| F-011 | `03_PRD.md` | FR-14 | type/modality неортогональны | MAJOR |
| F-012 | `03_PRD.md` | FR-6 | Нет грамматики ID/citation_key | MAJOR |
| F-013 | `03_PRD.md` | FR-6 | Нет citation formatting policy | MINOR |
| F-014 | все 3 файла | KnowQL | Несовместимый синтаксис | BLOCKER |
| F-015 | `03_PRD.md` | FR-20 | Нет validation report schema | MAJOR |
| F-016 | `03_PRD.md` | NFR-4 / FR-1 | Нет idempotency policy | MAJOR |
| G-001…G-015 | разные | — | См. раздел 3 | разные |
| R-001…R-006 | `02_architecture.md` / `03_PRD.md` | разные | См. раздел 4 | разные |

---

## 7. Положительные моменты, которые нужно сохранить

- **Раздел «candidate ideas requiring validation»** (3b, 9b, FR-30b, §13) — выдающаяся инженерная практика. Сохранить и расширять.
- **Чёткое разделение deterministic vs LLM** (FR-27 policy table) — оставить как «контракт».
- **`no_answer` как первоклассный ответ** (FR-29) — защищает от галлюцинаций.
- **Multi-representation text fields** (FR-17) — сильное инженерное решение, стоит развить (явно описать преобразования между ними).
- **Citation-aligned indexing** (§5.3 PRD) — формулировка, которую стоит вынести в slogan продукта.
- **Сквозная философия** *deterministic-first / evidence-first / temporal-first* — основа для дизайн-решений на всех этапах.

---

## 8. История ревью

| Дата | Автор | Действие |
|---|---|---|
| 2026-05-09 | AI Reviewer | Первичный ревью, создание документа |
| 2026-05-09 | GSD S07/T03 | Закрыт F-008: добавлена FR-to-phase матрица, FR-28b и roadmap помечены как post-MVP / research-gated. |
