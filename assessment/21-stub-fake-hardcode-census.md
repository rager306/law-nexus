# Stub/fake/hardcode census register (CID)

**Статус:** `[bounded]` inventory register (non-authoritative working register, серия assessment)
**Предыдущий в серии:** `assessment/08-known-defects.md` (DOC-01..DOC-10); дисциплина заголовка и disposition protocol унаследованы
**Census HEAD:** `c46ef0e872ff6f4c84630a97e557ddcc27c1b8e8` (branch `main`, dirty 0)
**Дата фиксации:** 2026-08-26 (M185-wuj4zf / S02 / T01)
**Проверка ревизии (T02):** слой L2 измерен на HEAD `834f77184e2b37dd92f7994b0dd14f2aa49c4deb` (dirty 0); `git diff --stat c46ef0e872ff6f4c84630a97e557ddcc27c1b8e8..HEAD -- crates src/law_nexus_harness` пуст — продуктовое дерево между ревизиями идентично, смешения замеров L1 (c46ef0e) и L2 (834f771) нет.
**Проверка ревизии (T03):** слои L3 (env/hardcode) и GitNexus измерены на HEAD `227c439e284f01e211765cfb7ed4ca726d038975` (dirty 0 на момент замеров); `git diff --exit-code` между `c46ef0e872ff6f4c84630a97e557ddcc27c1b8e8..HEAD` на `-- crates src/law_nexus_harness tests .env.example` пуст (job `.gsd/exec/90b4bf76-87cf-44ae-8e9c-5c020049c7d8.stdout`) — дерева смешений L1/L2/L3 нет.
**Ревизия исполнения S03 (T04):** перенос W3 класса D исполнен в слайсе M185-wuj4zf/S03; на момент правки регистра снято HEAD `f5798366bad386f643c77713f360a7f79ff3f155`, dirty 0 (`git rev-parse HEAD` + `git status --porcelain`, job `.gsd/exec/af4dd702-1b69-44d7-829b-ed4f296413d5.stdout`) — код переноса T01–T03 уже входит в эту ревизию, а сам регистр с переводом Class D в новый lifecycle в неё ещё НЕ входит (правка создаётся задачей T04). Якоря Path:line класса D сохранены Census-HEAD'овскими (`c46ef0e`); якоря S03-дерева и полные stdout переноса — в §Class D («Перенос W3») и §Closeout S03.
**Ревизия исполнения M192 S02 (T01):** первая замена строки класса A (CID-A-23) исполнена слайсом M192-79ij5m; на момент правки регистра снято HEAD `0c16de3f7f59a7817d3ee83d1258beac6a1e6aa2`, dirty 0 (`git rev-parse HEAD` + `git status --porcelain`, job `.gsd/exec/4e6b4597-1893-4c9f-9ee3-9625e60afe68.stdout`) — код замены S01 (`JsonlEffectLedger`, контракт-сьют) уже входит в эту ревизию, а сам регистр с переводом CID-A-23 в `addressed-in-draft` в неё ещё НЕ входит (правка создаётся задачей S02/T01; tracked-evidence-триада замыкается попаданием регистра в tracked-коммит). Якоря Path:line класса A сохранены Census-HEAD'овскими (`c46ef0e`); GitNexus reindex делегирован после tracked-коммита регистра (прецедент §Closeout S03/S04).
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
| CID-A-23 | A | `crates/ln-replay/src/adapters.rs`:32 | `InMemoryEffectLedger` | EffectLedgerPort: идемпотентность (operation,effect)→digest через try_apply. M192 S01: продуктовый durable-путь за тем же портом — `JsonlEffectLedger` (append-only JSONL по D102, канон-формат D310/D311; `EFFECT_LEDGER_PATH` empty-as-unset fail-closed без дефолта; строгая гидратация: corrupt/truncated/duplicate/non-canonical → типизированная ошибка без частичной гидратации; якорь S01-дерева `pub struct JsonlEffectLedger` в том же файле); InMemory не удалён — закреплён pinned test double'ом контракт-сьютой | `rg -n 'pub struct InMemoryEffectLedger' crates/ln-replay/src/adapters.rs && cargo test -p ln-testkit --offline --test effect_ledger_port_contracts` (8/8; tracked-сьют = tracked evidence) | W2 — первая замена исполнена M192 (durable за портом); остатки строки ([smoke]-пути hc14-runner `InMemoryEffectLedger::new()`, test-double pin) — M186+ | addressed-in-draft · [bounded] · против frozen HEAD `0c16de3f7f59a7817d3ee83d1258beac6a1e6aa2` (содержит код замены S01, сам регистр — нет; `verified-closed` — только триадой против ревизии, содержащей и код, и направленный вывод регистра) | Дurable-байты ≠ R070: R070 остаётся named-open; ротация/компакция и мультипроцессная блокировка файла не заявлены; без корпуса, без push; остальные CID-A открыты |
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

**CID-C-ZERO:** класс C = **0 строк**. Ни одна функция продуктового src не молча возвращает константу либо вырожденный алгоритм при имени/доке, обещающих реальную работу: константные возвраты, найденные чтением, являются документированными fail-closed guard'ами (класс B / Dropped hits) или честными bounded-фикциями класса A. Негативный контроль, обязанный попасть в луч и осознанно снятый: `cosine_similarity` zero-norm → `Ok(0.0)` (`crates/ln-storage/src/similarity.rs`:52-53, DH-04) — показательно, что игла N1 его вообще не анкерит: у возврата нет идентификатора score/similarity/relevance. Это эмпирическое подтверждение MEM679 (§Residual blind spot). Ноль — **pass с evidence** (команды выше, разбор всех попаданий, прогон honesty-тестов `cargo test -p ln-product-cli --offline classify`), не skip: L1+L2 исполнены в T02; слой L3/env и GitNexus-слой исполнены в T03 ниже (§Class D, §Aggregated, §Приложение) — исполнение переносов остаётся за S03/M186+.

## Class D — hardcode/env candidates

Слой L3 исполнен в T03 на HEAD `227c439e284f01e211765cfb7ed4ca726d038975` (продуктовое дерево идентично Census HEAD, см. шапку). Иглы прогонялись отдельными командами без альтернаций, vaults вне поиска; полный stdout — `.gsd/exec/ec67f8cd-dc66-47e1-be30-dc230909dd4f.stdout`:

| # | Игла | Команда (от корня репо) | Совпадений |
|---|---|---|---|
| E1 | `env::var(` | `rg -n 'env::var\(' crates src/law_nexus_harness` | 7 — все в `**/tests/**`; продуктовый `crates/*/src/**/*.rs`: **0** |
| E2 | `var_os(` | `rg -n 'var_os\(' crates src/law_nexus_harness` | 0 |
| E3 | `os.environ` (harness-Python) | `rg -n 'os\.environ' src/law_nexus_harness` | 1 — `governor.py`:1975 |
| E4 | `getenv` | `rg -n 'getenv' src/law_nexus_harness` | 0 |
| E5 | `env::vars(` | `rg -n 'env::vars\(' crates src/law_nexus_harness` | 0 |

Полнота ключей: во всём объёме «продуктовый Rust + тонкий harness» найден ровно один runtime-ключ окружения — **`CONSULTANT_EXPORT_DIR`**, и он же уже документирован в `.env.example`:7 (`CONSULTANT_EXPORT_DIR=consru_export`, семантика пути — :3-6). Новых ключей относительно `.env.example` нет: S03 не invent-ит ничего сверх этого ключа. Компиляторный `env!("CARGO_MANIFEST_DIR")` ключом конфигурации не является (см. DH-07).

Schema таблицы едина с классами A/B/C:

| CID | Class | Path:line | Symbol | Description (short) | Repro (от корня репо) | Owner wave | Lifecycle | Non-claims |
|---|---|---|---|---|---|---|---|---|
| CID-D-01 | D | 7 тестовых сидов, одинаковый `unwrap_or_else(\|_\| "consru_export".to_owned())` (Path:line ниже — Census-HEAD'овские, `c46ef0e`; якоря S03-дерева — §«Перенос W3»): `crates/ln-product-cli/tests/real_44fz_assembly.rs`:31, `real_44fz_text_ctv.rs`:96, `crates/ln-kb-ontology/tests/hierarchy_registry.rs`:192, `corpus_role.rs`:63, `crates/ln-consultant-parser/tests/classifier_recall_test.rs`:25 (+ дококомментарий :15), `multi_edition_test.rs`:10, `crates/ln-decode/tests/registry_bindings_generator.rs`:230 | `consultant_export_dir()` (было `std::env::var("CONSULTANT_EXPORT_DIR")`) | Агрегированная строка тестовых консюмеров корпус-path: литерал дефолта `consru_export` повторён в 7 файлах, склейка `join(dir).join("consru_export…")` воспроизводит схему пути из `.env.example`:5; отсутствующий каталог → честный SKIP (skip-capable тесты); ключ уже в `.env.example` — S03 собрал рассыпанный литерал на единый конфиг-вход, нового ключа не создав. Документационный дрейф: `.env.example`:4 называл консюмером «the product CLI», тогда как L3 в продуктовом src не нашёл ни одного env-чтения — фактически читают только эти тесты и harness (CID-D-02); комментарий уточнён при переносе (S03/T02) | `rg -n 'CONSULTANT_EXPORT_DIR_ENV' crates --glob '**/tests/**'` → константа + fn-helper ровно в семи сидовых файлах (полный stdout — §Closeout S03) | W3 = S03 (M185-wuj4zf; только перенос конфигурации) — перенесено configuration-only; непереносимые остатки литералов — M186+ | verified-closed @50e960e · перенос исполнен (S03 T01–T03, §Closeout S03); вердикт поставлен S04 triad против предсуществующего frozen HEAD 50e960e4050da46111d4e3f9818c8ace0e23c898 (код переноса — предки e3cc51e/33d7b2e/f579836) | Дефолт `consru_export` остаётся допустимым fail-closed значением в коде; наличие корпуса не гарантируется; skip-семантика тестов не меняется |
| CID-D-02 | D | `src/law_nexus_harness/governor.py`:1217, :1219, :1927, :1975 (Census HEAD; S03-дерево: public def `corpus_export_dir()` :1222, единственное чтение ключа через него :1990) | `corpus_export_dir()` над `_CORPUS_GROUNDING_ENV` — было `os.environ.get(_CORPUS_GROUNDING_ENV, _CORPUS_GROUNDING_DEFAULT_EXPORT)` | Harness-консюмер того же ключа: имя ключа спрятано в константе :1217, дефолт-литерал `consru_export` задублирован в константе :1219 и докомментарии :1927; отсутствие каталога экспортов → advisory-файндинг `status="pass" / severity="ok"` (fail-closed-absent, тело probe :1975+) | S03: `sed -n '1222p;1990p' src/law_nexus_harness/governor.py && uv run pytest tests/test_harness_governor.py -k corpus_grounding -q` | W3 = S03 (конфигурация; логика probe не менялась) — перенесено configuration-only | verified-closed @50e960e · перенос исполнен (S03 T01/T02, §Closeout S03); вердикт поставлен S04 triad против предсуществующего frozen HEAD 50e960e4050da46111d4e3f9818c8ace0e23c898 | Advisory-поведение при пустом корпусе сохраняется; governor-чекиды этой строкой не закрываются |

Хардкод-литералы `consru_export` в продуктовом src отсутствуют: все 4 упоминания — комментарии схемы путей в `crates/ln-kb-ontology/src/registry.rs` (:150, :228, :269, :295) → DH-08; отдельных CID из них не заводится.

### Перенос W3 (S03) — evidence

Правки configuration-only исполнены в дереве слайса M185-wuj4zf/S03 (код переноса закоммичен ревизией `f5798366bad386f643c77713f360a7f79ff3f155`; данный блок — часть правки T04 поверх неё). Ни один check_id, ни одна skip/warn-ветка или сообщение probe не менялись (D272); новых env-ключей не заведено.

- **CID-D-01 → семь сидов (T03):** каждый lookup заменён локальной копией helper'а с контрактом empty-as-unset — `Ok(v) if !v.trim().is_empty() => v`, иначе `CONSULTANT_EXPORT_DIR_DEFAULT.to_owned()` (= `consru_export`); `std::env::set_var` в cargo-тестах запрещён (D282), поэтому runtime-override-proof живёт на pytest (см. CID-D-02), а для Rust контракт доказывается компиляцией + содержимым исходника. Якоря S03-дерева (const ENV + fn helper): `real_44fz_assembly.rs`:30/:35, `real_44fz_text_ctv.rs`:95/:100, `multi_edition_test.rs`:8/:13, `classifier_recall_test.rs`:24/:29, `registry_bindings_generator.rs`:229/:234, `hierarchy_registry.rs`:190/:195, `corpus_role.rs`:61/:66 (job `.gsd/exec/b88aa857-6929-4ce0-bc09-b7ea8ec187fe.stdout`). Skip-семантика (`eprintln` SKIP / early return / `exists().then_some`) сохранена.
- **CID-D-02 → harness helper (T01):** рядом с константами добавлен публичный `corpus_export_dir()` (`src/law_nexus_harness/governor.py`:1222; `None`/strip-empty → `_CORPUS_GROUNDING_DEFAULT_EXPORT`); единственное чтение ключа на :1990 идёт через helper — сырой `os.environ.get(...)` устранён. Новый pytest-контур (tests/test_harness_governor.py): `test_corpus_grounding_honors_export_dir_override`:692 (env задан → значение применяется к alt-каталогу; краснел бы, будь helper игнорируем), `test_corpus_grounding_empty_env_uses_default`:720 и `test_corpus_grounding_whitespace_env_uses_default`:738 (empty/whitespace ведут себя как unset → дефолт; без helper'а были RED), unset-skip тест сохранён без смены семантики.
- **Зеркало документа (T02):** `.env.example`:4 больше не называет консюмером «product CLI» — формулировка «Skip-capable tests and the harness corpus-grounding probe resolve real corpus paths as»; дефолт документирован как «unset or empty/whitespace: consru_export»; ключ на :7 единственный, новых ключей нет. Pin-тест `test_env_example_documents_corpus_grounding_export_dir` (tests/test_harness_governor.py:768) отрицает рецидив ложного консюмера.

Lifecycle обеих строк класса D при переносе W3 был `addressed-in-draft`: ячейки перевёрнуты правкой S03/T04, когда код переноса уже был закоммичен, а сам регистр ещё нет; tracked-evidence-триада disposition protocol замкнулась только тогда, когда направленный вывод регистра вошёл в tracked-коммит `50e960e4050da46111d4e3f9818c8ace0e23c898`. Теперь обе строки — `verified-closed @50e960e` (S04 triad): пруф стоит против ревизии, которая уже содержит и код переноса, и вывод регистра; GitNexus reindex delegated to T03 after this register edit's commit.

## Aggregated: test-infra-bounded

Тестовая инфраструктура — основной лексический носитель слов stub/fake (≈90% лексических попаданий по проекту), поэтому сведена сюда агрегатами и исключена из продуктовых таблиц классов A–D. Зафиксированный факт к переносу (T01): `StubTransport` в продуктовом src отсутствует — существует только в тестах (`crates/ln-storage/tests/retrieval_gate_contract.rs`:8, `crates/ln-storage/tests/tei_adapter_contract.rs`:6, `crates/ln-testkit/tests/embedding_port_contracts.rs`:12); `TeiEmbeddingAdapter` (`crates/ln-storage/src/adapters/tei.rs`:36) — реальный адаптер с транспортной инъекцией, заглушкой не считается. Инвентаризация исполнена в T03 (HEAD `227c439e`, диск = Census HEAD); прогоны — `.gsd/exec/f79eed86-dd2c-446e-9f92-6d83222c30b3.stdout`.

| ID | Поверхность | Объём / содержание | Repro |
|---|---|---|---|
| TI-01 | `crates/ln-testkit/tests/` | Каталог целиком состоит из **24** общих port-contract сюит `*_port_contracts.rs` (ADR-0015 verification matrix): двойники портов прогоняются через общие assert-функции testkit'а; индивидуальные symbol-строки сознательно не ведутся — агрегата по glob достаточно | `ls crates/ln-testkit/tests/*_port_contracts.rs \| wc -l` → `24`; прочих тестовых файлов в каталоге нет |
| TI-02 | `crates/ln-query/tests/knowql_contract.rs` | Контрактная репетиция KnowQL над тремя стабами: `StubEmbedding`:7 (честно отдаёт `vec![0.5; dims]`), `StubVectorStore`:20, `StubGraphStore`:35; негативная поверхность — пять validation-отказов (`validation_rejects_empty_embed_text`/`zero_dimensions`/`empty_find_similar_vector`/`nan_vector`/`empty_label`) | `rg -n 'struct Stub' crates/ln-query/tests/knowql_contract.rs` |
| TI-03 | `crates/ln-storage/tests/` | Портовые контракты storage: `storage_ports_contract.rs` (`StubEmbedding.embed`:9-20, `vector_store_port_round_trips_through_stub`:127-134), `retrieval_gate_contract.rs` (:8 StubTransport), `tei_adapter_contract.rs` (:6 StubTransport) плюс `similarity_contract.rs`/`in_memory_adapters_contract.rs`; дубль записи DH-02 — новые CID не заводятся | `ls crates/ln-storage/tests/` |

Oracle-quality remark (качество оракула, НЕ класс C и НЕ продуктовый баг): `crates/ln-query/tests/knowql_integration.rs` интегрирует реальные записи парсера (tracked Consultant fixture) с InMemory-адаптерами (CID-A-02/A-03), но локальный `StubEmbedding` (:32-38) возвращает нулевой вектор `vec![0.0; dims]` (:35) против блоков, засеянных `vec![0.5; 4]` (:56, :70): cosine нулевой стороны вырождается guard'ом DH-04 в `Ok(0.0)` и ранжирование теряет разрешающую силу — интеграционный позитив слабый фикстурный оракул. Кандидат на усиление поздней волны (различающиеся детерминированные векторы либо реальный embedding-провайдер за портом); filed здесь намеренно, поскольку это осознанная слабость тестовой фикстуры, а не функция, претендующая на работу.

## Приложение: GitNexus excerpt по stub-символам

Индекс `law-nexus`; четыре обязательных вызова исполнены 2026-08-26 (T03), продукт на момент вызовов = Census HEAD `c46ef0e`. Компактная свёртка без дампов:

| Вызов | Результат (компактно) |
|---|---|
| `gitnexus_query {search_query:"stub placeholder adapter implementation", repo:"law-nexus"}` | Определения только в tests/harness/scripts: `ln-testkit/tests/embedding_port_contracts.rs` — `tei_stub_transport_satisfies_shared_embedding_port_contract`:26-33, `tei_stub_transport_rejects_model_identity_drift`:36-46, `tei_stub_transport_rejects_non_finite_values`:75-85; `governor.py` — `check_semantic_stub_in_product_code`:2712-2782, `check_live_adapter_readiness`:2481-2539; `ln-storage/tests/storage_ports_contract.rs` — `StubEmbedding.embed#1`:9-20, `vector_store_port_round_trips_through_stub`:127-134; `retrieval_gate_contract.rs` — `build_gate`:17-39; `scripts/verify-multi-adapter-port-coverage.py` — `discover_port_impls`:76-132; `tests/test_harness_governor.py`:1539-1737 (негативный контроль губернатора, включая `test_semantic_stub_in_product_code_detects_planted_stub`:1721). Определений в продуктовых `crates/*/src` — **ноль**: независимое от grep подтверждение пустоты класса C. `processes: []` — stub-символы не участвуют ни в одном execution flow индекса |
| `gitnexus_context InMemoryVectorStore` (uid `Struct:crates/ln-storage/src/adapters/in_memory.rs:InMemoryVectorStore`) | struct :34-37; методы `default/store/query`; свойства `records`,`journal`; implements `VectorStorePort` (`ln-storage/src/lib.rs`). Epistemic `lower-bound` («интерфейс с 3 имплементациями»). Прямой вызов по имени вернул ambiguity Struct:34/Impl:39 в том же файле — разрешён явно uid'ом |
| `gitnexus_context StubEmbedding` (`crates/ln-product-cli/src/main.rs`) | struct :57 (+ метод `embed#1`), implements `EmbeddingPort`; epistemic `lower-bound` («интерфейс с 5 имплементациями») — разнообразие реализаций шире, чем видит один символ |
| `gitnexus_context check_semantic_stub_in_product_code` | Function `governor.py`:2712-2782, epistemic `exact`; входящих/исходящих рёбер нет — advisory-probe живёт вне кодового call-graph, `processes: []` |

Примечание о свежести индекса: якоря строк расходятся с диском @Census HEAD на ±1 (`InMemoryVectorStore` :34 против :35 в L1-замере T01/CID-A-02; `StubEmbedding` :57 против :58 в CID-A-01) — индекс построен незадолго до Census HEAD; идентичность символов (файл+имя+тип) подтверждена. Reindex сознательно не исполнялся (делегирован S04 после tracked-коммита census) и продуктовым изменением не считается. Опциональный запрос «embedding stub panic» не исполнялся — четырёх обязательных достаточно для цели приложения.

## Волны M186+ (wave map)

Инвентарная сводка владения строками на конец S02/T03; живой план остаётся за `gsd_reassess_roadmap`, эта карта authority не является.

| Волна | Владелец | Объём |
|---|---|---|
| W1 — inspect-honesty leftover | — | Пуста: класс B закрыт без открытых строк (B-02/B-03 `accepted-exception · honesty-present`; B-01 ADR-gated). Открывается только revisit-триггером этих строк |
| W2 — replace class A | M186+ | 25 строк A (CID-A-01..A-24 + агрегат CID-A-RUNNERS): хранение/embedding/registers → durable за теми же портами либо реальный acquired-source; port-contract protection из TI-01 (24 сюиты `ln-testkit`) переиспользуется как safety-net |
| W3 = S03 | M185-wuj4zf/S03 | Класс D: единый конфиг-вход для `CONSULTANT_EXPORT_DIR` — тестовые сиды CID-D-01 + harness-консюмер CID-D-02; зеркало в `.env.example` уже есть (:3-7); только перенос конфигурации, без изменения логики; уточнение комментария `.env.example`:4 («product CLI») при переносе. **Исполнение:** перенос выполнен configuration-only в S03 (T01 harness-helper, T02 зеркало документа + pin-тест, T03 семь сидов); строки CID-D переведены в `addressed-in-draft` в S03 (§Class D, §Closeout S03) и закрыты `verified-closed @50e960e` волной S04 triad (регистр tracked самим 50e960e, код переноса — его предки). Литералы fail-closed дефолтов, которые S03 не поднимает, остаются M186+ и переклассифицируются следующим census-sweep |
| ProtocolUnimplemented | вне волн M186 | Applicability: ADR-gated (R074) — не первая волна; положительные решения v0-оценщиком не чеканятся census'ом |

Non-claims волн (усиливают документ-level non-claims ниже): **0** исполнений GC-001..040; **0** работ ConflictResolver; **0** чеканки enum под `[proposed]`-словари (D216); **0** функциональных замен заглушек в этом слайсе; **0** push. Класс D волной W3 не «закрывается», а переносится: closure по disposition protocol потребует отдельного frozen revision + tracked evidence.

## Closeout T03 (honesty spot-check)

Губернатор запущен package-формой `uv run python -m law_nexus_harness governor` (dotted-форма `law_nexus_harness.governor` — известный silent no-op, MEM935, не использовалась). Поля отчёта `law-nexus-governor-report/v1` (канон — поля отчёта, не exit code): `status:"ok"`, `pass_count:67` (наблюдаемое значение; пин конкретного числа запрещён MEM1143), `warn_count:0`, `tool_error_count:0`; процесс завершился кодом 0. Полный stdout — `.gsd/exec/ceb534dd-13e2-4a59-b0c5-08027a405a5f.stdout`. Battery не потревожена регистрацией markdown-регистра; финальная цепочка проверок задачи (needle-верify, повторный governor, чистота `git diff --exit-code -- crates src/law_nexus_harness tests .env.example`) зафиксирована в Verification Evidence задачи T03.

## Closeout S03 (env-sweep W3)

Команды verify по задачам слайса (пройдены в T01–T03):

- T01: `uv run ruff format tests/test_harness_governor.py src/law_nexus_harness/governor.py` + `uv run ruff check tests/test_harness_governor.py src/law_nexus_harness/governor.py` + `uv run pytest tests/test_harness_governor.py -k corpus_grounding -q` + package-form governor;
- T02: `uv run ruff format tests/test_harness_governor.py` + `uv run ruff check tests/test_harness_governor.py` + `uv run pytest tests/test_harness_governor.py -k corpus_grounding -q`;
- T03: `cargo test -p ln-consultant-parser --offline --test multi_edition_test --test classifier_recall_test` + `cargo test -p ln-kb-ontology --offline --test hierarchy_registry --test corpus_role` + `cargo test -p ln-product-cli --offline --test real_44fz_assembly --test real_44fz_text_ctv` + `cargo test -p ln-decode --offline --test registry_bindings_generator` + `cargo fmt --all --check` + `cargo check --workspace --offline`.

Губернатор запускался ТОЛЬКО package-формой `uv run python -m law_nexus_harness governor` (dotted-форма `law_nexus_harness.governor` — известный silent no-op, MEM935, ни разу не использовалась). Контрольный прогон T04 против перевёрнутых ячеек — поля отчёта `law-nexus-governor-report/v1` (канон — поля отчёта, не exit code): `status:"ok"`, `warn_count:0`, `tool_error_count:0`, `pass_count:<наблюдаемое>` (пин конкретного числа запрещён MEM1143). Полный stdout прогона T04 — `.gsd/exec/0d32dd9c-c72d-447a-92b7-eef7fecf578f.stdout`.

Единственный записанный этим юнитом файл — настоящий регистр (assessment/21); файлы переноса T01–T03 им не тронуты. GitNexus reindex сознательно не исполнялся (делегирован S04 после tracked-коммита); GC-001..040 не исполнялись; push не выполнялся.

Итог класса D после W3 (на момент S03/T04): обе строки — `addressed-in-draft`. Честная оговорка того момента остаётся в силе как история: код переноса был закоммичен (HEAD `f5798366`, dirty 0), а переворот lifecycle'а становился tracked-evidence только после попадания регистра в коммит. Вердикт с тех пор поставлен волной S04 против предсуществующего frozen HEAD — см. §Closeout S04.

## Closeout S04 (census triad closure)

Вердикт класса D закрыт честной триадой: `verified-closed @50e960e` выставлен против предсуществующего frozen HEAD `50e960e4050da46111d4e3f9818c8ace0e23c898` (dirty 0 на момент правки), в которой сосуществуют (a) закоммиченный код переноса W3 — цепочка e3cc51e → 33d7b2e → f579836, прямые предки этого HEAD, — и (b) уже-tracked направленный вывод самого регистра. Новый SHA под вердикт не чеканился; freeze-инвариант: репро-команды §Closeout S03 воспроизводимы против 50e960e дословно, перепрогон 4.6G-корпуса не требуется; якоря Path:line класса A остаются Census-HEAD'овскими (`c46ef0e`), Class A не закрывается. GitNexus reindex delegated to T03 after this register edit's commit.

## Closeout M192-79ij5m S02 (CID-A-23 disposition)

Первая замена строки класса A исполнена волной M192. S01 добавил durable `JsonlEffectLedger` за существующим `EffectLedgerPort` (`crates/ln-replay/src/adapters.rs`; append-only JSONL по D102, канон-формат зафиксирован D310 и подтверждён D311; путь из `EFFECT_LEDGER_PATH` — empty-as-unset fail-closed, без дефолта, в отличие от `CONSULTANT_EXPORT_DIR`; строгая гидратация — corrupt/truncated/duplicate/non-canonical записи дают типизированную ошибку без частичной гидратации; персистентный сбой через infallible-порт — консервативный `false` + типизированный `take_error`). InMemory-двойник не удалён, а закреплён: общий контракт-сьют прогоняет оба адаптера через одни assert'ы, test-double-статус — инвариант тестами. S02 переворачивает ячейку CID-A-23 по disposition protocol:

1. **frozen revision** — HEAD `0c16de3f7f59a7817d3ee83d1258beac6a1e6aa2` (dirty 0 на момент правки; job `.gsd/exec/4e6b4597-1893-4c9f-9ee3-9625e60afe68.stdout`): содержит код замены S01 и контракт-сьют, сам регистр с новым lifecycle ещё нет — правку создаёт S02/T01; триада замыкается попаданием регистра в tracked-коммит (прецедент Class D: `addressed-in-draft` → `verified-closed @…`);
2. **tracked evidence** — tracked контракт-сьют `crates/ln-testkit/tests/effect_ledger_port_contracts.rs` (8 тестов: общий порт-контракт обоих адаптеров, durability reopen с побайтовой сверкой канонической формы, `ledger_env_fail_closed`, `corrupt_ledger_file_fails_closed_without_hydration`, `missing_parent_directory_is_io_error`, `ledger_path_directory_is_io_error`, `hostile_duplicate_ledger_still_fails_honest_contract`) + зеркала `.env.example` (`EFFECT_LEDGER_PATH=` — сверено S02, не дублировалось) и настоящего регистра; unit-поверхность ln-replay: `append_write_failure_is_fail_closed` (`/dev/full`), `strict_parser_rejects_non_canonical_shapes`, `canonical_record_round_trips_through_strict_parser`;
3. **preserved non-claims** — durable-байты не R070: R070 остаётся named-open; InMemory остаётся на [smoke]-путях hc14-runner'а (`main.rs`:47,74,100,127) как pinned test double; ротация/компакция ledger-файла и мультипроцессная блокировка не заявлены (S01 Known Limitations); governor check_id не менялись (D272); GC-001..040 не исполнялись; корпуса нет; push нет; остальные 24 строки CID-A открыты.

Verify-цепочка T01: губернатор — ТОЛЬКО package-форма `uv run python -m law_nexus_harness governor` (dotted-форма — известный silent no-op, MEM935), канон — поля отчёта `law-nexus-governor-report/v1`, не exit code (MEM1143: пин pass_count запрещён); контракт-сьют — `cargo test -p ln-testkit --offline --test effect_ledger_port_contracts`. Пред-существующий красный губернатора по bookkeeping `prd/project-state/data/roadmap.json` (current отстаёт от latest_completed после M190/M191) — не порождение среза; remediation — отдельный roadmap-фикс (Q3 плана слайса). GitNexus `detect_changes` (repo law-nexus) исполнен перед коммитом; reindex сознательно не исполнялся — делегирован после tracked-коммита регистра (как в §Closeout S03/S04).

## Dropped hits

Lexical echoes и добросовестные случаи, сознательно НЕ заносимые как CID:

- **DH-01** `crates/ln-product-cli/src/main.rs`:76,198,216,268,1315 — исторические комментарии замен M161/M163 («replaces the prior hardcoded vec![…]», «any act-specific hardcode» guard). Под анкерный паттерн губернатора не попадают; классом D не считаются (решение об env-выносе принимает S03 независимо от этих комментариев).
- **DH-02** `StubTransport` — три определения, все в тестовых файлах (см. §Aggregated: test-infra-bounded); продуктового кода не касается.
- **DH-03** Hostile/synthetic двойки внутри продуктовых src (`HostileLabelMutatorLedger`, `HostileMirrorRelabeler`, `HostileVerdictInflator`, `HostileCanarySink`, `InPlaceMutatingHostileStore`, `ErasingMergerHostileStore`, `HostileGapInventorState`, `OpenRelationHostileRegistry`, `HostileDualWriterLedger`, `HostileDuplicateEffectLedger`, `SubstitutingHostileEvidence`, `HonestSyntheticDecoder`, `MaliciousSyntheticDecoder`) — осознанные HC host-contract fixtures («preserved for HC hostile contract tests»); лексически чистые, вне объёма п.7 данной задачи (scope = `struct InMemory*`). Их судьба при смене контрактной стратегии HC рассматривается отдельно, здесь CID не назначается.
- **DH-04** `crates/ln-storage/src/similarity.rs`:52-53 — `return Ok(0.0)` при zero-norm любой из сторон (guard над константой `ZERO_NORM_EPSILON`:13) — документированный fail-closed отказ вырожденного входа с юнит-pin'ами в соседнем `#[cfg(test)]`, а не фиктивная функция; сам cosine-расчёт ранжирования — живая замена M161 (CID-A-02). Обязательный негативный контроль слоя L2 снят здесь (см. CID-C-ZERO); показательно, что идентификатор-игла N1 этот возврат не видит.
- **DH-05** `crates/ln-product-cli/src/main.rs`:198,217,1315 — комментарии исторических замен M163 («replaces the prior hardcoded vec![0.5; …]»): живых конструкций `vec![0.5; n]` в src нет — это эхо замен, добирающее DH-01 по результатам L2-иглы N2.
- **DH-06** `crates/ln-applicability/src/domain.rs`:132,237,267 — фразы «design only» в докомментариях типов NormRule IR (temporal window, defeater, structural marker): честные маркеры дизайн-границ, runtime-поведения не претендуют; четвёртое совпадение той же иглы (:336) поднято в CID-B-01. Совпадений иглы N3 вне этого файла нет.
- **DH-07** `env!("CARGO_MANIFEST_DIR")` — compile-time макрос cargo build-system, встречается в 27 тестовых файлах (по одному попаданию; `cli_contract.rs` — четыре). Переменная сборки, а не runtime-конфиг приложения: ключом класса D не заносится намеренно, чтобы S03 не изобретал несуществующий env-ключ; иглы L3 (E1-E5) этот макрос не анкерят — проверено отдельной командой `rg -c 'env!\("CARGO_MANIFEST_DIR"\)' crates` (`.gsd/exec/f79eed86-dd2c-446e-9f92-6d83222c30b3.stdout`).
- **DH-08** `consru_export` в продуктовом src — 4 упоминания, все комментарии схемы путей в `crates/ln-kb-ontology/src/registry.rs` (:150, :228, :269, :295, включая «No needle matched: try consru_export edition filename grounding»): лексическое эхо конвенции именования корпуса, runtime-литералов дефолта в src нет (конфиг-сид проходит только через env — CID-D-01/D-02); классом D не считаются, чтобы не дублировать строки класса D комментарием.

## Residual blind spot (MEM679)

T02 закрыл lexical (L1) и identifier-anchored semantic (L2) слои, но каскады тихих констант вне имён score/similarity/relevance остаются вне луча:

- **semantic-equivalent без якоря имени** — функция, все ветви которой возвращают один литерал при любом входе, без слов stub/fake/design-only рядом (пример-контроль T02: `similarity.rs`:53 `Ok(0.0)` для grep-иглы невидим вовсе);
- **вырожденные алгоритмы** — формально «настоящая» реализация, деградировавшая до identity/clamp/первого элемента при обещанной статистике;
- **охват harness-Python** (`src/law_nexus_harness/**`) — вне L2-среза этой задачи;
- **внешние бинарники/FFI/библиотеки** — значения за границей репозитория недостижимы для grep/GitNexus.

GitNexus-слой (T03) видит типы и call-graph, но не вырожденность значений — это общая граница всех трёх слоёв. Предложение на последующую волну (здесь не исполняется, решение D272): усилить `check_semantic_stub_in_product_code` детекторами degenerate-return («все ветви возвращают один литерал/константный вектор при объявленном score-подобном контракте») и value-independence (результат не зависит от входов) на AST-уровне; новый check_id вводится только governor-волной, census фиксирует потребность.

## Non-claims (уровень документа)

Документ — процессная инвентаризация: не заменяет living roadmap, не доказывает функциональность продукта, не закрывает известные defect register записи, не отменяет границы канона (D098/D216, ADR-0019 S0, G1-block). Все replacement-волны проходят собственные TDD/evidence циклы.
