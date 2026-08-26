# Stub/fake/hardcode census register (CID)

**Статус:** `[bounded]` inventory register (non-authoritative working register, серия assessment)
**Предыдущий в серии:** `assessment/08-known-defects.md` (DOC-01..DOC-10); дисциплина заголовка и disposition protocol унаследованы
**Census HEAD:** `c46ef0e872ff6f4c84630a97e557ddcc27c1b8e8` (branch `main`, dirty 0)
**Дата фиксации:** 2026-08-26 (M185-wuj4zf / S02 / T01)
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
- **B (`fail-closed stub`)** — заглушка, безопасно отказывающая без притязаний на семантику (заполняется в T02);
- **C (`fake-claiming-function`)** — функция, декларирующая больше, чем делает (заполняется в T02);
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

Четвёртая альтернатива губернатора (`panic!("not implemented"-семейство)`) входит в тот же probe; отдельный замер в этой задаче не был зафиксирован как proof-grade артефакт и подлежит повтору в T02 вместе с layer-L2.

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

Заполняется в T02 (слой L2: семантика). Placeholder, пусто.

## Class C — fake-claiming functions

Заполняется в T02 (функции, декларирующие больше, чем делают). Placeholder, пусто.

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

## Residual blind spot (MEM679)

Placeholder к заполнению в T02/T03: semantic-equivalent заглушки без лексических маркеров; охват harness-Python; внешние бинарники/библиотеки; зоны, недоступные текущим слоям L1/L2/GitNexus.

## Non-claims (уровень документа)

Документ — процессная инвентаризация: не заменяет living roadmap, не доказывает функциональность продукта, не закрывает известные defect register записи, не отменяет границы канона (D098/D216, ADR-0019 S0, G1-block). Все replacement-волны проходят собственные TDD/evidence циклы.
