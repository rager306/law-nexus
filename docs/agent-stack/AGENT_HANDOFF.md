# Передача Law-Nexus агенту Allspark

## Что это за документ

Это контракт будущего исполнения технической миграции. Он подготовлен вместе с конфигурацией и планом, но сам не является отчётом о выполненной установке, успешных тестах или принятии юридических решений.

Владелец выбрал целевой стек **Allspark + GSD Path + PDD Kit**, с выводом GSD-Pi из активной работы. Сохранение истории Pi нужно для provenance и recovery; сохранение его как второго активного координатора не входит в цель.

Форк и границы published release: [ALLSPARK_NOTES.md](ALLSPARK_NOTES.md).
Основной runbook: [MIGRATION.md](MIGRATION.md). Установка и pinned configuration: [INSTALL.md](INSTALL.md). Повседневная работа после cutover: [WORKFLOW.md](WORKFLOW.md).

> Current delivery state (2026-10-27): the current-state document is
> [POST-SHIP-STATE-2026-10-27.md](POST-SHIP-STATE-2026-10-27.md); it supersedes
> `CUTOVER-READINESS-M001.md` (kept untouched as the dated pre-ship snapshot).
> A fresh session bootstraps from disk alone via that report's
> "Fresh-session bootstrap" section.

## Готовое поручение для первой сессии

Следующий текст предназначен для передачи агенту владельцем при начале исполнения:

~~~text
Прочитай docs/agent-stack/ALLSPARK_NOTES.md, AGENT_HANDOFF.md, MIGRATION.md
и INSTALL.md.
Выполни техническую миграцию Law-Nexus с GSD-Pi на Allspark + GSD Path + PDD Kit.

Сначала сделай read-only inventory реального локального checkout, gitignored
.gsd state, существующих AGENTS/CLAUDE/MCP,
worktrees, hooks, активных процессов и незавершённой работы.
Не выводи секреты и не меняй state на этом этапе.

После inventory продолжай обратимые технические шаги runbook автономно:
согласованный backup, штатный freeze старого writer, отдельная migration branch,
точечный merge starter/config, реализация переносимых harness gates и проверки.
Подготовь конкретный bootstrap PR/review packet. Публикацию и merge выполняй
только в пределах уже выданного мной разрешения; если его нет, подготовь всё
до этой границы и укажи точное требуемое действие.

Используй repo scripts/ai/allspark с pinned fork.009 и same-commit source
supplement. Проверь оба Path runtime caches, общий внешний worktree root,
Git identity/hooks/signing и toolchain при normal и Allspark HOME.
Не запускай upstream installer и не копируй старый auth profile.

После bootstrap merge и чистого fetched origin baseline используй native
Path initialize/bind. Не создавай STATE вручную, не запускай Pi параллельно,
не импортируй .gsd как GSD Core .planning.
Перенеси только доказанные активные обязательства с dependencies и approvals.
Выполни один bounded технический pilot и проверь resume.

Не превращай legacy done, PDD aligned, green tests или общую просьбу о миграции
в legal adoption, Review Case decision, requirement/lifecycle promotion.
M210 not-adopted/hold действует, пока нет отдельного подходящего owner decision.
~~~

Если владелец запросил только review/план, ограничиться inventory и предложенным diff/планом; не начинать миграцию из-за чтения этого файла.

## 1. Сначала установить факты

Не предполагай, что публичный GitHub HEAD равен локальной работе. Исследованный baseline: f15612b2034ce71c9109326173c5e8a3b8a86b76, проверен 2026-10-23, commit date 2026-09-24. Это отправная точка для сравнения, не приказ checkout старой ревизии.

Первый отчёт должен назвать:

- фактические repository root, HEAD, branch и remote default;
- состояние Git index/worktree и все связанные worktrees;
- где находится .gsd, является ли она symlink, что можно прочитать из state;
- какой процесс пишет старый state и как его штатно остановить;
- присутствие AGENTS.md, CLAUDE.md, local skills и MCP config;
- actual Allspark build/SHA, source supplement, normal и isolated HOME;
- effective Git identity/hooks/signing, Rust paths и Path placement в обоих окружениях;
- найденные active tasks, pending approvals, blockers и unresolved dependencies;
- наличие .project/.planning и их владельца; не присваивать себе чужой state;
- доступные corpus/evidence artifacts, недоступные inputs;
- что будет backup, что остаётся приватным, где будет migration branch.

Не дампить весь environment, credentials, DB или corpus. В tracked report помещать только очищенные metadata, нужные refs и non-secret configuration.

Существующий cold clone не содержит фактических AGENTS/.gsd/.mcp.json, потому что эти поверхности gitignored. Отсутствие источника — Unknown/unavailable, не чистый backlog.

## 2. Обязательный порядок чтения

1. prd/ARCHITECTURE.md.
2. Owning ADR изменяемого контракта.
3. prd/architecture/glossary-governance.md; при затрагивании понятий — §3 prd/temporal-legal-model.md.
4. Применимые локальные инструкции и skill contracts.
5. Текущие implementation, tests и source-bound evidence.
6. Legacy GSD records — как процессные данные с recorded revision.

Смена workflow уже выбрана владельцем. Pi-specific предписания заменить явно в migration diff; не использовать старую политику host для блокировки всей миграции. Сохранить юридические и продуктные ограничения.

Law-Nexus — Rust product runtime; Python — repository harness. LLM, PDD и planning artifacts не являются юридическим авторитетом. Deferred-undefined и runtime deferred — границы scope, не предложение сгенерировать недостающую онтологию.

## 3. Управление работой и автономность

| Состояние | Кто пишет delivery state | Что разрешено |
|---|---|---|
| Inventory | Старый writer, если ещё работает; только наблюдаем | Read-only facts, подготовка freeze |
| Freeze/backup | Никто | Согласованный snapshot, проверка recovery |
| Bootstrap PR preparation | Path ещё не активен; Pi заморожен | Обычная migration branch, code/config/test changes |
| Native Path initialized/bound | Один Path coordinator | Только helper-owned state/task mutations |
| Task execution | Worker в выданном scope | Code/tests; status/landing — через Path owner |
| Recovery | Только назначенный recovery owner | Native transaction recovery; никакого второго writer |

Не создавать скрытую синхронизацию .gsd ↔ .project. Не завершать milestone вручную, не создавать фиктивные Attempts и не имитировать approvals.

Продолжать без повторных вопросов все уже разрешённые, обратимые технические шаги. На настоящий blocker подготовить:

1) доказательство и точный scope;
2) что уже выполнено;
3) конкретный diff/вариант решения;
4) одно недостающее действие/решение владельца.
Не превращать обычный выбор имени функции или тестовой фикстуры в approval gate.

Native Path approvals/recovery нельзя обходить. Повторно использовать уже действительное разрешение в его scope; pre-approval записывать только если владелец действительно выдал соответствующий grant. Ship/review/adoption остаются отдельными решениями, когда их требует применимый контракт.

## 4. Bootstrap preparation: конкретный технический scope

Изменять в пределах migration tasks:

- docs/agent-stack/, .ai/, scripts/ai/ из starter, с точечным merge existing files;
- явный перенос non-secret MCP config в settings и independent login Allspark;
- two-HOME runtime restore и stable external worktree placement, без symlinks;
- новый typed workflow-state adapter в Python harness;
- governor/preflight consumers и соответствующие tests;
- roadmap projection и successor delivery/review bridge contract;
- live source-integrity successor, сохраняющий старые pinned records;
- active hooks/CI invocations, реально зависящие от Pi;
- source-path/symlink boundary для новых workflow directories;
- minimal PDD model только после согласования его product meaning.

Проверить полноценный Allspark host dispatch отдельно. Наличие scripts/ai/path-run.py и рабочего native status не доказывает поддержку всех фаз Path. Исследованный upstream Path не имеет готового Allspark adapter для полного phase workflow. Для inspect/research/plan и остальных нужных ролей требуется явная проверенная интеграция с fresh worker contexts, инструментами и результатами по контракту Path. Если её нет, реализовать её отдельной bounded integration task; не заменять требуемые независимые роли бесшумным inline исполнением и не объявлять стек полностью готовым.

Где начинать в существующем codebase:

| Область | Точные файлы |
|---|---|
| State reads | src/law_nexus_harness/governor.py; src/law_nexus_harness/preflight.py |
| State tests | tests/test_harness_governor.py; tests/test_harness_preflight.py; tests/test_project_state_roadmap_freshness.py |
| Review bridge | prd/architecture/review-cases/gsd-review-bridge.md; continuity-contract.md |
| Opaque delivery refs | src/law_nexus_harness/review_case/application.py; policy.py |
| Source boundary | src/law_nexus_harness/review_case/domain.py; adapters/filesystem.py; scripts/verify-architecture-graph.py |
| Pi source import | scripts/m204_s08_source_revision.mjs |
| Active consumers | scripts/m210_s02_rebind.mjs; scripts/m210_s02_slice_battery.mjs |
| Quality gates | .github/workflows/repository-quality.yml; .pre-commit-config.yaml |

Не переписывать scripts/m204_* и historical reports массовым search/replace. Не обновлять старые hashes/approvals ради прохождения нового gate. Подробная migration matrix и источники — в MIGRATION.md.

Typed adapter должен явно различать:

- bootstrap not-cut-over;
- operational valid Path state;
- missing state;
- invalid/unsupported schema;
- unavailable or mismatched selected runtime;
- conflicting ownership/branch/transaction;
- historical legacy evidence.

В operational mode missing/invalid target state — blocking outcome. Portable bootstrap checks могут проходить отдельно, но это не workflow-ready.

## 5. Начальный Path state создаёт только native bootstrap

В рекомендованном порядке bootstrap PR сначала должен попасть в origin default. Затем:

1. Чистый checkout на exact fetched origin/<default> SHA.
2. Нет старого writer и неопубликованных локальных изменений.
3. Выбран pinned runtime через native launcher/manifest.
4. Native router /skill:path запускает detect_project.py initialize и принимает его typed classification.
5. Между initialize и bind-initial не делать commit.
6. bind-initial берёт route.branch, full remote SHA и recorded default branch; начальный STATE — единственное допустимое untracked исключение.
7. Branch transition/status/route выполняются native helpers.
8. Integration mode задаётся до build; первая migration — pull-request, если владелец не выбрал другое.

Не вызывать выдуманный pipeline_state init. Не проставлять pipeline: gsd-path/v2 в чужой файл. При orphan/error/transaction journal выполнять native recovery, а не создавать ещё одну .project.

Если runtime отсутствует/повреждён, остановить helper execution и следовать exact-version restore diagnostic. Не переключаться молча на глобальный latest.

## 6. Переносимый backlog и первый pilot

Перенести legacy IDs в crosswalk, а не в новую нумерацию Path. Для каждого active item нужны source reference, observed status, remaining work, dependencies, review/adoption boundaries и новый delivery mapping.

Нет фактов — Unknown/blocked. Старый done, code commit или зелёный отчёт не делают новый task done автоматически. .project/archive остаётся native Path archive, а не складом старого Pi state.

Первый рекомендуемый pilot — закрытый parser аргументов provenance CLI:

- implementation принимает ledger;
- старый negative test требует для ledger Usage error;
- нужно проверить intended contract и сделать минимальное исправление;
- сохранить отказ для неизвестного mode и неправильной комбинации write/check.

Предпосылка: cargo fetch --locked выполнен, toolchain и C build dependencies доступны.

~~~bash
cargo test -p ln-consultant-parser --offline --locked --lib amendment_provenance::tests::argument_parsing_is_closed_and_requires_one_action -- --exact
~~~

Проверь, что выполнен ровно один тест; нулевое совпадение фильтра не считается PASS. Приведи before/after, diff, current revision и проверенные non-claims.

PDD initial scope — inspect/provenance CLI, возможно bounded snapshot replay. Не заявлять готовый legal applicability interface. pdd-verify report-only проверяет source alignment; actual runtime tests выполняются отдельно задачей Path. PDD aligned ≠ Law validated.

## 7. Контракт доказательств

Каждый verification receipt должен содержать:

- фактическую revision и scope;
- точную команду;
- exit code, количество executed/skipped tests;
- stdout/stderr или пригодную ссылку на них;
- наличие нужных fixtures/corpus/runtime;
- интерпретацию результата и non-claims.

Статусы не смешивать:

| Факт | Чего он не означает |
|---|---|
| PDD lint pass | Semantic alignment или product validation |
| PDD aligned | Выполненный runtime test или legal correctness |
| Path task done | Review Case disposition или requirement promotion |
| Rust tests pass | Human legal adoption |
| Legacy milestone complete | Полная миграция неизвестного локального state |
| Документ ready-for-assessment | Accepted product contract или release-ready |
| Source snapshot captured | Юридическая правильность содержащихся данных |

Исторический CI исследованного HEAD failing. Не скрывать baseline debt и не выдавать исторический run от сентября за текущий local run. Не делать всё CI зелёным расширением scope без причины; сначала исправить мигрируемые controls и ограниченный pilot.

## 8. Human authority, которое миграция не переносит

Прочитать текущий prd/architecture/m210-s02-adoption-checkpoint.md.

В исследованном baseline:

- admission: not-adopted;
- owner_admission_ref: none;
- f13_status: hold;
- runtime_stop активен;
- review_case_events_written: 0;
- requirements_promoted: 0.

Не внедрять bounded normative IR, не менять §3 glossary, не снимать F13 и не начинать S03 из общего разрешения на инструменты. Не создавать human Review Case event от имени владельца. Если фактически имеется новое source-bound решение, проверить его scope и governing surface, а не просто найти слова «approved».

Эта граница не запрещает независимые technical maintenance tasks. Работу по migration controls и parser pilot можно завершить, сохранив normative backlog blocked.

## 9. Что передать владельцу в конце

Короткий основной отчёт:

1. Что установлено/изменено: actual fork version/tag/SHA, supplement и project revision.
2. Где находится active Path state, selected runtime и безопасный backup manifest.
3. Что из backlog импортировано, что осталось Unknown/blocked и почему.
4. Какие проверки фактически выполнены; что skipped/not run.
5. Какой pilot выполнен и что он доказывает.
6. Какие старые active imports/hooks отключены, какие historical records сохранены.
7. Сохранились ли M210/human authority boundaries.
8. Следующая разрешённая задача и конкретные оставшиеся owner gates.
9. Recovery entry point при прерывании.

Не заканчивать утверждением «миграция завершена», если работает второй writer, отсутствует target-state adapter, active checks требуют Pi runtime, не проверен native resume или backlog был восстановлен догадками.

Аналогично, build launcher без полного нужного phase dispatch — это подготовленный integration component, а не завершённая передача проекта Path.

## 10. При сбое

- Остановить текущего writer, сохранить текущую работу и diagnostic.
- Сначала native status/route/recovery, затем любые действия.
- Не удалять .gsd/.project, worktrees или DB.
- Не использовать reset --hard, clean -fd, --no-verify или ручной SQL как универсальное восстановление.
- Git rollback и ignored/local-state restore — разные операции.
- Возврат к backup не запускает Pi автоматически.
- После recovery снова проверить единственного writer, branch/runtime/state agreement и actual HEAD.

Source links, проверенные command sources и detailed rollback находятся в [MIGRATION.md](MIGRATION.md#источники).

