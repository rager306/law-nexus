# Stub/fake/hardcode census register (CID)

**Статус:** `[bounded]` inventory register (non-authoritative working register, серия assessment)
**Предыдущий в серии:** `assessment/08-known-defects.md` (DOC-01..DOC-10); дисциплина заголовка и disposition protocol унаследованы
**Census HEAD:** `c46ef0e872ff6f4c84630a97e557ddcc27c1b8e8` (branch `main`, dirty 0)
**Дата фиксации:** 2026-08-26 (M185-wuj4zf / S02 / T01)
**Проверка ревизии (T02):** слой L2 измерен на HEAD `834f77184e2b37dd92f7994b0dd14f2aa49c4deb` (dirty 0); `git diff --stat c46ef0e872ff6f4c84630a97e557ddcc27c1b8e8..HEAD -- crates src/law_nexus_harness` пуст — продуктовое дерево между ревизиями идентично, смешения замеров L1 (c46ef0e) и L2 (834f771) нет.
**Область обследования:** продуктовый Rust `crates/*/src/**/*.rs` (исключая `crates/ln-testkit/**` и любые `**/tests/**`) плюс тонкий harness `src/law_nexus_harness/**` только как источник probes. Vault-каталоги (`python_archive/`, `.lex/`, `Old_project/`, `prd/archive/`, `archive/`) — вне поиска и вне таблиц: vaults не являются product truth.
Счётчики исследовательской фазы ранних проходов каноном не считаются; все числа ниже воспроизводятся командами против Census HEAD (см. §L1 marker layer).

## Роль документа

Инвентаризация кандидатов «заглушки / фиктивные реализации / баги / хардкод» для волн M186+. Этот файл:

- НЕ roadmap authority — живой план замен обновляется `gsd_reassess_roadmap` после слайсов;
- НЕ закрывает TSG-001..017 и НЕ исполняет GC-001..040;
- НЕ чеканит Rust-типы под `[proposed]` словари (D216);
- НЕ является фактом замены: census = инвентаризация; замены — отдельными волнами с TDD и evidence (§5 `assessment/20`).

Классы находок:

- **A (`bounded-adapter`)** — port-имплементация на продуктовом пути с детерминированно упрощённым поведением, явной границей `[bounded]`/ADR и (при наличии) port-contract тестом;
- **B (`fail-closed stub`)** — заглушка, безопасно отказывающая без притязаний на семантику (заполнено в T02);
- **C (`fake-claiming-function`)** — функция, декларирующая больше, чем делает (заполнено в T02: 0 строк, CID-C-ZERO);
- **D (`hardcode-env-candidate`)** — зашитые настройки/значения, кандидаты на вынос в `.env` с зеркалом в `.env.example` (S03).

Lifecycle-метки CID: `open`, `addressed-in-draft`, `verified-closed`, `accepted-exception`, `superseded`.

## Disposition protocol

Закрытие CID требует одновременно:

1. **frozen revision** — фиксация целевой ревизии (commit SHA + путь:строка), против которой сделан вывод;
2. **tracked evidence** — tracked-артефакт с repro-командой и её зафиксированным результатом (тест, governor/probe отчёт, assessment-файл); усечённый дайджест лога evidence не является;
3. **preserved non-claims** — ограничение притязаний сохраняется вместе с закрытием (что именно НЕ доказано закрытием).

Повторная отметка той же ячейки новым прогоном не является закрытием: тикание ячейки ≠ closure. Состояние `addressed-in-draft` означает только коррекцию working tree или наличие paper-артефакта (наследие D0-дисциплины assessment/08). `accepted-exception` требует rationale, owner и revisit trigger.

## L1 marker layer (лексические маркеры)

Источник паттерна — продуктовый probe губернатора: `src/law_nexus_harness/governor.py`, функция `check_semantic_stub_in_product_code` (def на строке 2713 на Census HEAD), advisory anti-drift probe (MEM676). Срез: `crates/*/src/**/*.rs` без `/tests/` и без `crates/ln-testkit/`. Ожидание на продуктовом пути — ноль совпадений.

Воспроизведение (все команды — от корня репозитория; форма через `-e` эквивалентна анкерной альтернации губернатора `//\s*(stub|fake|dummy|placeholder|hardcoded)`):

| Срез | Команда | Результат |
|---|---|---|
| comment markers | `rg -n -i -e '//\s*stub' -e '//\s*fake' -e '//\s*dummy' -e '//\s*placeholder' -e '//\s*hardcoded' crates -g '**/src/**/*.rs' -g '!ln-testkit/**' -g '!**/tests/**'` | 0 |
| todo-macro | `rg -n 'todo!\s*\(' crates -g '**/src/**/*.rs' -g '!ln-testkit/**' -g '!**/tests/**'` | 0 |
| unimplemented-macro | `rg -n 'unimplemented!\s*\(' crates -g '**/src/**/*.rs' -g '!ln-testkit/**' -g '!**/tests/**'` | 0 |

Четвёртая альтернатива губернатора (`panic!("not implemented"`-семейство), повтор в T02):

| Срез | Команда | Результат |
|---|---|---|
| panic-family | `rg -n -i -e 'panic!\("[^"]*(not implemented\|unimplemented\|todo)' crates -g '**/src/**/*.rs' -g '!ln-testkit/**'` | 0 |

Слой L2 (семантика) исполнен в T02: класс C = 0 строк (`CID-C-ZERO`, §Class C); каждое попадание L2-игл разобрано в ±10-строчном окне и либо поднято в класс B, либо снято в §Dropped hits.

Интерпретация: ноль анкерных маркеров подтверждает чистоту продуктового кода на лексическом слое. Это НЕ доказательство отсутствия semantic-equivalent заглушек — за этим слой L2 (семантика, T02) и GitNexus-слой (T03). См. §Residual blind spot (MEM679).

Исторические комментарии M161/M163 со словом «hardcoded» в `crates/ln-product-cli/src/main.rs` (строки 76, 198, 216, 268, 1315) стоят не сразу после `//`, под паттерн губернатора не попадают и дефектами не считаются — зафиксированы в §Dropped hits.

## Class A — bounded-adapters

Все строки класса — документированные продуктовые субституты с явной границей `[bounded]`; owner-wave W2 = M186+ (замена за портом c port contract в `ln-testkit` либо реальный acquired-источник, §7.2 `assessment/20`). Класс A в S03 не переходит. Номера строк сняты с файлов на Census HEAD.

Schema таблицы едина для всех классов и последующих задач (T02/T03 дополняют её же):

| CID | Class | Path:line | Symbol | Description (short) | Repro (от корня репо) | Owner wave | Lifecycle | Non-claims |
|---|---|---|---|---|---|---|---|---|
| CID-A-01 | A | `crates/ln-product-cli/src/main.rs`:58,59,66,78,115,200,218,222 | `StubEmbedding` + `deterministic_vector` | Хеш-детерминированный embedding-провайдер CLI inspect (M163-замена константного `vec![0.5; n]`); wired в execute/find-similar; реальный адаптер — `TeiEmbeddingAdapter` | `rg -n 'struct StubEmbedding\|impl EmbeddingPort for StubEmbedding\|fn deterministic_vector' crates/ln-product-cli/src/main.rs` | W2 | open · [bounded] | Детерминированный хеш ≠ семантическое сходство; не мерило качества retrieval |
| CID-A-02 | A | `crates/ln-storage/src/adapters/in_memory.rs`:35 | `InMemoryVectorStore` | VectorStorePort: BTreeMap + OperationJournal/replay; ranking честным cosine (M161-замена truncate-by-key-order); до durable vector store | `rg -n 'pub struct InMemoryVectorStore' crates/ln-storage/src/adapters/in_memory.rs` | W2 | open · [bounded] | In-memory only; persistence/consistency не заявлены |
| CID-A-03 | A | `crates/ln-storage/src/adapters/in_memory.rs`:117 | `InMemoryGraphStore` | GraphStorePort: nodes/edges + journal/replay; edge-upsert replaces same (source,target); до durable graph store | `rg -n 'pub struct InMemoryGraphStore' crates/ln-storage/src/adapters/in_memory.rs` | W2 | open · [bounded] | In-memory only; без транзакций/конкурентности |
| CID-A-04 | A | `crates/ln-consultant-parser/src/catalog.rs`:81 | `InMemoryCatalog` | CatalogPort: consid→CatalogRecord; genuine miss → `in_catalog=false`; рядом SQLite-twin `crate::SqliteCatalog`; контракт-модуль `contract::` в файле | `rg -n 'pub struct InMemoryCatalog' crates/ln-consultant-parser/src/catalog.rs` | W2 | open · [bounded] | Тестовая карта метаданных ≠ реальный каталог Консультант |
| CID-A-05 | A | `crates/ln-accelerate/src/adapters.rs`:8 | `InMemoryAccelerationLedger` | AccelerationLedgerPort: provisional map; `authoritative_count()` константно 0 (честная bounded-фикция до реального authoritative store); hostile-twin `HostileLabelMutatorLedger` в том же файле | `rg -n 'pub struct InMemoryAccelerationLedger' crates/ln-accelerate/src/adapters.rs` | W2 | open · [bounded] | Authority-числа фиктивны (0); реального ускорителя нет |
| CID-A-06 | A | `crates/ln-citation/src/adapters.rs`:7 | `InMemoryCitationSource` | CitationSourcePort: source→(anchor,authority) map; builder `with()` | `rg -n 'pub struct InMemoryCitationSource' crates/ln-citation/src/adapters.rs` | W2 | open · [bounded] | Не источник цитат; резолв ограничен засеянным map |
| CID-A-07 | A | `crates/ln-conformance/src/adapters.rs`:6 | `InMemoryConformanceOracle` | ConformanceOraclePort: seeded verdicts; miss → `CaseVerdict::Unsupported` (fail-closed); `all_pass(n)` для smoke | `rg -n 'pub struct InMemoryConformanceOracle' crates/ln-conformance/src/adapters.rs` | W2 | open · [bounded] | Верdict'ы заданы вручную; оракул ≠ прогон конформанс-набора |
| CID-A-08 | A | `crates/ln-decode/src/adapters.rs`:415 | `InMemoryDiagnosticSink` | DiagnosticPort (decode): Vec<SafeDiagnostic>; соседствует с legacy synthetic-decoder HC-05 fixtures (см. §Dropped hits) | `rg -n 'pub struct InMemoryDiagnosticSink' crates/ln-decode/src/adapters.rs` | W2 | open · [bounded] | Sink буфер; никуда не доставляет |
| CID-A-09 | A | `crates/ln-diagnostic/src/adapters.rs`:7 | `InMemoryDiagnosticSink` | DiagnosticSinkPort: allow-set + журнал emitted (sink_id,content); counter helper | `rg -n 'pub struct InMemoryDiagnosticSink' crates/ln-diagnostic/src/adapters.rs` | W2 | open · [bounded] | Журнал в памяти; доставки/ретраев нет |
| CID-A-10 | A | `crates/ln-dispose/src/adapters.rs`:10 | `InMemoryDispositionStore` | DispositionStorePort: item_id→Disposition map, set/get | `rg -n 'pub struct InMemoryDispositionStore' crates/ln-dispose/src/adapters.rs` | W2 | open · [bounded] | Хранилище неперсистентно |
| CID-A-11 | A | `crates/ln-dispose/src/adapters.rs`:26 | `InMemoryPromotionGate` | PromotionGatePort: accepted → `CommitId("commit:synthetic-1")` — синтетический commit-id, не git-backed; ключевой кандидат W2 | `rg -n 'InMemoryPromotionGate\|synthetic-1' crates/ln-dispose/src/adapters.rs` | W2 | open · [bounded] | Commit-id синтетический; promotion не исполняется |
| CID-A-12 | A | `crates/ln-gate/src/adapters.rs`:7 | `InMemoryCandidateStore` | CandidateStorePort: candidate_id→record map, get/put | `rg -n 'pub struct InMemoryCandidateStore' crates/ln-gate/src/adapters.rs` | W2 | open · [bounded] | Неперсистентное хранилище кандидатов |
| CID-A-13 | A | `crates/ln-identity/src/adapters.rs`:7 | `InMemoryIdentityStore` | IdentityStorePort: CRUD (get/put/remove/contains) по identity_id | `rg -n 'pub struct InMemoryIdentityStore' crates/ln-identity/src/adapters.rs` | W2 | open · [bounded] | Неперсистентно; без конкурентного контроля |
| CID-A-14 | A | `crates/ln-inventory/src/adapters.rs`:7 | `InMemoryInventoryStore` | InventoryStorePort: append_attempt/attempts_for (Vec попыток на item) | `rg -n 'pub struct InMemoryInventoryStore' crates/ln-inventory/src/adapters.rs` | W2 | open · [bounded] | Попытки только в памяти |
| CID-A-15 | A | `crates/ln-inventory/src/adapters.rs`:34 | `InMemoryVisibilityView` | VisibilityPort: `inventory_review_visible()` возвращает `true` безусловно — семантически тонкая заглушка видимости | `rg -n 'pub struct InMemoryVisibilityView' crates/ln-inventory/src/adapters.rs` | W2 | open · [bounded] | Политики видимости НЕТ: always-visible ≠ review policy |
| CID-A-16 | A | `crates/ln-observe/src/adapters.rs`:46 | `InMemoryWorkState` | WorkStatePort: журнал переходов (Vec<WorkTransition>) + чтение slice | `rg -n 'pub struct InMemoryWorkState' crates/ln-observe/src/adapters.rs` | W2 | open · [bounded] | Журнал в памяти; восстановление вне диапазона |
| CID-A-17 | A | `crates/ln-observe/src/adapters.rs`:61 | `InMemoryDiagnosticSink` | DiagnosticPort (observe): emit/events по Vec<DiagnosticEvent> | `rg -n 'pub struct InMemoryDiagnosticSink' crates/ln-observe/src/adapters.rs` | W2 | open · [bounded] | Буфер событий; экспорта нет |
| CID-A-18 | A | `crates/ln-promote/src/adapters.rs`:7 | `InMemoryPromotionStore` | PromotionStorePort: op→record + commits map; `next_commit_id()` генерирует последовательность `commit:N` — синтетические номера коммитов | `rg -n 'pub struct InMemoryPromotionStore\|next_commit_id' crates/ln-promote/src/adapters.rs` | W2 | open · [bounded] | Commit-id синтетические; git-связи нет |
| CID-A-19 | A | `crates/ln-publish/src/adapters.rs`:8 | `InMemoryPublicationLedger` | PublicationLedgerPort: authoritative-per-scope + writer-exclusivity support (HC-15 pure seam) | `rg -n 'pub struct InMemoryPublicationLedger' crates/ln-publish/src/adapters.rs` | W2 | open · [bounded] | Леджер в памяти; персистентной публикации нет |
| CID-A-20 | A | `crates/ln-query/src/adapters.rs`:7 | `InMemoryQueryState` | QueryStatePort: membership набора evidence-id | `rg -n 'pub struct InMemoryQueryState' crates/ln-query/src/adapters.rs` | W2 | open · [bounded] | Не поисковая система; только набор id |
| CID-A-21 | A | `crates/ln-relation/src/adapters.rs`:10 | `InMemoryClosedRegistry` | RelationRegistryPort: закрытый мир; фиксированный seed-predicate `amends` (family-A) + факты | `rg -n 'pub struct InMemoryClosedRegistry' crates/ln-relation/src/adapters.rs` | W2 | open · [bounded] | Реестр фиксирован seed'ом; не live-реестр правил |
| CID-A-22 | A | `crates/ln-replay/src/adapters.rs`:9 | `InMemoryCheckpointStore` | CheckpointPort: checkpoint_id→record, load-only | `rg -n 'pub struct InMemoryCheckpointStore' crates/ln-replay/src/adapters.rs` | W2 | open · [bounded] | Чекпоинты в памяти |
| CID-A-23 | A | `crates/ln-replay/src/adapters.rs`:32 | `InMemoryEffectLedger` | EffectLedgerPort: идемпотентность (operation,effect)→digest через try_apply | `rg -n 'pub struct InMemoryEffectLedger' crates/ln-replay/src/adapters.rs` | W2 | open · [bounded] | Леджер эффектов в памяти |
| CID-A-24 | A | `crates/ln-temporal/src/adapters.rs`:7 | `InMemoryClockEvidence` | ClockEvidencePort: clock-kind→anchor map; helpers `with_all_except`/`with_only` для hostile-путей | `rg -n 'pub struct InMemoryClockEvidence' crates/ln-temporal/src/adapters.rs` | W2 | open · [bounded] | Якоря часов заданы вручную |
| CID-A-RUNNERS | A | `crates/ln-hc01-runner/src/main.rs`:4,13,39,40 (+16/20 sibling mains) | `adapter_for` + InMemory-конструкции | [smoke]-драйверы HC-01..20 строят InMemory-адаптеры для сценариев; единая агрегированная строка вместо ряда по call-site; hc10–hc13 идут другими портами | `rg -n 'fn adapter_for\|InMemory' crates/ln-hc01-runner/src/main.rs` | W2 | open · [smoke]/[bounded] | Smoke-сквозняк на doubles ≠ acquired-source run |

Структурная целостность: 23 продукта-структуры `struct InMemory*` в 18 файлах (A-02..A-24) — соответствует рабочему счётчику Census HEAD.

## Class B — fail-closed stubs

Слой L2 ложных заглушек не нашёл: игла присвоений score/similarity/relevance := 0.0/1.0 дала 0 попаданий (§Class C), литеральные константные векторы живут только в комментариях исторических замен (DH-05). Строки ниже — документированные fail-closed границы; номера сняты с диска на HEAD `834f77184e2b37dd92f7994b0dd14f2aa49c4deb` (продуктовое дерево = Census HEAD):

| CID | Class | Path:line | Symbol | Description (short) | Repro (от корня репо) | Owner wave | Lifecycle | Non-claims |
|---|---|---|---|---|---|---|---|---|
| CID-B-01 | B | `crates/ln-applicability/src/domain.rs`:336-337,350 | `AbstentionKind::ProtocolUnimplemented` (+ arm `"protocol_unimplemented"`) | Протокол ADR-0023 принят как design-only, положительные решения v0-оценщиком не производятся (докомментарий `ApplicabilityDecision`:355-356 «must not be produced by the v0 evaluator») — домен отдаёт типизированное воздержание вместо фиктивного решения. Паттерн-оракул семейства design-only: `crates/ln-temporal/tests/event_kind_boundary.rs`:19 `both_kinds_are_design_only_not_runtime` | `rg -n 'ProtocolUnimplemented' crates/ln-applicability/src/domain.rs` | ADR-gated (R074) — census типы не чеканит | [proposed]/design-only · open | Нет юридической корректности; Applicable/NotApplicable не выдаются; замена — отдельная ADR-волна, не M186-env |
| CID-B-02 | B | `crates/ln-product-cli/src/main.rs`:550 (+ JSON-поле `retrieval` inspect-println ~530) | `classify_knowql_retrieval` | Остаток MEM1120 закрыт честностью, НЕ fake: count==0 всегда парен со status `ok`/`unavailable`/`unexpected_result`; non_claims inspect-JSON рестейтят «never a silent zero». Четыре пути закреплены тестами `main.rs`:1378,1385,1393,1399 | `rg -n 'fn classify_knowql_retrieval' crates/ln-product-cli/src/main.rs && cargo test -p ln-product-cli --offline classify` | none | accepted-exception · honesty-present · revisit: появление непарного статуса или варианта `KnowQLResult` без теста | retrieval.count детерминированно-несемантичен (хеш-векторы, CID-A-01); ok-hit ≠ качество сходства |
| CID-B-03 | B | `crates/ln-product-cli/src/main.rs`:586 | `classify_inspect_assembly` | Та же honesty-схема для шести assembly-счётчиков: `no_edition_day`/`unavailable` отличимы от честного `ok` — «never a silent six-zero collapse»; тесты `main.rs`:1407,1422,1429 | `rg -n 'fn classify_inspect_assembly' crates/ln-product-cli/src/main.rs && cargo test -p ln-product-cli --offline classify` | none | accepted-exception · honesty-present · revisit: изменение `InspectAssemblyCounts`/набора статусов | Счётчики — структурные AST-проекции, не юридическая иерархия/CTV |

### hc-runners disposition

`adapter_for` (`crates/ln-hc01-runner/src/main.rs`:13) подставляет InMemory→`InterruptibleSourceAdapter` канарки сценариям [smoke]; hc13 (`crates/ln-hc13-runner/src/main.rs`:123-125) строит `HostileVendorCapacity` c `bound_id: Some(BoundId::parse("bound:fake"))` как намеренно hostile двойника host-contract сценария (run_hostile_vendor_rejects: capacity-притязание отвергается — Rejected/VendorCapacityRejected). Оба — bounded smoke-драйверы с явной schema-честностью вердикта; **классом C не считаются**, остаются агрегированы в `CID-A-RUNNERS`, детализация тестовой инфраструктуры — §Aggregated (T03).

### Owner-wave итог класса B

W1 по классу B пуста: остаток MEM1120 не пережил чтение функции вместе с её тестами — честность парных статусов доказана, поэтому строки оформлены `accepted-exception · honesty-present` c owner-wave `none`, а не открытым дефектом. Единственная open-строка (CID-B-01) волны не получает: applicability-протокол остаётся ADR-gated (R074); чеканка положительных решений возможна только решением ADR, не через census.

## Class C — fake-claiming functions

Слой L2 исполнен на HEAD `834f771` (продуктовое дерево = Census HEAD `c46ef0e`): три семантические иглы плюс повтор panic-family альтернативы губернатора; каждый hit прочитан в ±10-строчном окне и либо поднят в класс B, либо снят в §Dropped hits. Полные stdout-логи прогонов — `.gsd/exec/<job-id>.stdout` сессии T02:

| # | Игла (что ищем) | Команда (от корня репо) | Совпадений → разбор |
|---|---|---|---|
| N1 | присвоение score/similarity/relevance := 0.0/1.0 | `rg -n -e '(score\|similarity\|relevance)[A-Za-z_]*[=:]+= ?-?(0\.0\|1\.0)' crates -g '**/src/**/*.rs' -g '!ln-testkit/**'` | **0** |
| N2 | литеральные константные векторы `vec![0.0…`/`vec![0.5…` | `rg -n -e 'vec!\[0\.0' -e 'vec!\[0\.5' crates -g '**/src/**/*.rs' -g '!ln-testkit/**'` | 3 — только комментарии замен M163 (`main.rs`:198,217,1315) → DH-05 |
| N3 | фразы not implemented / design only | `rg -n -i -e 'not implemented' -e 'design only' crates -g '**/src/**/*.rs' -g '!ln-testkit/**'` | 4 — маркеры дизайн-границ `ln-applicability/src/domain.rs`:132,237,267,336 → DH-06; :336 поднято в CID-B-01 |
| N4 | `panic!("not implemented"`-семейство (повтор губернаторской альтернативы) | `rg -n -i -e 'panic!\("[^"]*(not implemented\|unimplemented\|todo)' crates -g '**/src/**/*.rs' -g '!ln-testkit/**'` | **0** — см. также §L1 marker layer |

**CID-C-ZERO:** класс C = **0 строк**. Ни одна функция продуктового src не молча возвращает константу либо вырожденный алгоритм при имени/доке, обещающих реальную работу: константные возвраты, найденные чтением, являются документированными fail-closed guard'ами (класс B / Dropped hits) или честными bounded-фикциями класса A. Негативный контроль, обязанный попасть в луч и осознанно снятый: `cosine_similarity` zero-norm → `Ok(0.0)` (`crates/ln-storage/src/similarity.rs`:52-53, DH-04) — показательно, что игла N1 его вообще не анкерит: у возврата нет идентификатора score/similarity/relevance. Это эмпирическое подтверждение MEM679 (§Residual blind spot). Ноль — **pass с evidence** (команды выше, разбор всех попаданий, прогон honesty-тестов `cargo test -p ln-product-cli --offline classify`), не skip: L1+L2 исполнены, класс D/env и GitNexus-слой остаются за S03/T03.

## Class D — hardcode/env candidates

Заполняется в S03 (env-sweep: вынос настроек в `.env`, зеркало `.env.example`; дефолты в коде допустимы только как fail-closed значения). Placeholder, пусто; CID-номера класса D сейчас не присваиваются.

## Aggregated: test-infra-bounded

Заполняется в T03 (сводка тестовой инфраструктуры). Зафиксированный факт к переносу: `StubTransport` в продуктовом src отсутствует — существует только в тестах (`crates/ln-storage/tests/retrieval_gate_contract.rs`:8, `crates/ln-storage/tests/tei_adapter_contract.rs`:6, `crates/ln-testkit/tests/embedding_port_contracts.rs`:12); `TeiEmbeddingAdapter` (`crates/ln-storage/src/adapters/tei.rs`:36) — реальный адаптер с транспортной инъекцией, заглушкой не считается.

## Приложение: GitNexus excerpt по stub-символам

Заполняется в T03 (repo `law-nexus`; выдержка query по stub/InMemory-символам). Placeholder, пусто.

## Dropped hits

Lexical echoes и добросовестные случаи, сознательно НЕ заносимые как CID:

- **DH-01** `crates/ln-product-cli/src/main.rs`:76,198,216,268,1315 — исторические комментарии замен M161/M163 («replaces the prior hardcoded vec![…]», «any act-specific hardcode» guard). Под анкерный паттерн губернатора не попадают; классом D не считаются (решение об env-выносе принимает S03 независимо от этих комментариев).
- **DH-02** `StubTransport` — три определения, все в тестовых файлах (см. §Aggregated: test-infra-bounded); продуктового кода не касается.
- **DH-03** Hostile/synthetic двойки внутри продуктовых src (`HostileLabelMutatorLedger`, `HostileMirrorRelabeler`, `HostileVerdictInflator`, `HostileCanarySink`, `InPlaceMutatingHostileStore`, `ErasingMergerHostileStore`, `HostileGapInventorState`, `OpenRelationHostileRegistry`, `HostileDualWriterLedger`, `HostileDuplicateEffectLedger`, `SubstitutingHostileEvidence`, `HonestSyntheticDecoder`, `MaliciousSyntheticDecoder`) — осознанные HC host-contract fixtures («preserved for HC hostile contract tests»); лексически чистые, вне объёма п.7 данной задачи (scope = `struct InMemory*`). Их судьба при смене контрактной стратегии HC рассматривается отдельно, здесь CID не назначается.
- **DH-04** `crates/ln-storage/src/similarity.rs`:52-53 — `return Ok(0.0)` при zero-norm любой из сторон (guard над константой `ZERO_NORM_EPSILON`:13) — документированный fail-closed отказ вырожденного входа с юнит-pin'ами в соседнем `#[cfg(test)]`, а не фиктивная функция; сам cosine-расчёт ранжирования — живая замена M161 (CID-A-02). Обязательный негативный контроль слоя L2 снят здесь (см. CID-C-ZERO); показательно, что идентификатор-игла N1 этот возврат не видит.
- **DH-05** `crates/ln-product-cli/src/main.rs`:198,217,1315 — комментарии исторических замен M163 («replaces the prior hardcoded vec![0.5; …]»): живых конструкций `vec![0.5; n]` в src нет — это эхо замен, добирающее DH-01 по результатам L2-иглы N2.
- **DH-06** `crates/ln-applicability/src/domain.rs`:132,237,267 — фразы «design only» в докомментариях типов NormRule IR (temporal window, defeater, structural marker): честные маркеры дизайн-границ, runtime-поведения не претендуют; четвёртое совпадение той же иглы (:336) поднято в CID-B-01. Совпадений иглы N3 вне этого файла нет.

## Residual blind spot (MEM679)

T02 закрыл lexical (L1) и identifier-anchored semantic (L2) слои, но каскады тихих констант вне имён score/similarity/relevance остаются вне луча:

- **semantic-equivalent без якоря имени** — функция, все ветви которой возвращают один литерал при любом входе, без слов stub/fake/design-only рядом (пример-контроль T02: `similarity.rs`:53 `Ok(0.0)` для grep-иглы невидим вовсе);
- **вырожденные алгоритмы** — формально «настоящая» реализация, деградировавшая до identity/clamp/первого элемента при обещанной статистике;
- **охват harness-Python** (`src/law_nexus_harness/**`) — вне L2-среза этой задачи;
- **внешние бинарники/FFI/библиотеки** — значения за границей репозитория недостижимы для grep/GitNexus.

GitNexus-слой (T03) видит типы и call-graph, но не вырожденность значений — это общая граница всех трёх слоёв. Предложение на последующую волну (здесь не исполняется, решение D272): усилить `check_semantic_stub_in_product_code` детекторами degenerate-return («все ветви возвращают один литерал/константный вектор при объявленном score-подобном контракте») и value-independence (результат не зависит от входов) на AST-уровне; новый check_id вводится только governor-волной, census фиксирует потребность.

## Non-claims (уровень документа)

Документ — процессная инвентаризация: не заменяет living roadmap, не доказывает функциональность продукта, не закрывает известные defect register записи, не отменяет границы канона (D098/D216, ADR-0019 S0, G1-block). Все replacement-волны проходят собственные TDD/evidence циклы.
