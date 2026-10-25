# Миграция Law-Nexus: GSD-Pi → Allspark + GSD Path + PDD Kit

## Назначение и границы

Этот документ — план исполнения технической миграции существующего репозитория. Само наличие этого файла не означает, что миграция уже выполнена. Пакет подготовлен без изменения Law-Nexus и без запуска его тестов локально.

Целевое разделение ответственности:

| Слой | Владелец |
|---|---|
| Host, модель, инструменты и исполнение ограниченных заданий | Allspark |
| План, зависимости, задачи, переходы и durable delivery state | GSD Path; один активный координатор |
| Согласованное описание наблюдаемого поведения продукта | PDD Kit, каталог product-model/ |
| Архитектура, юридические понятия и допустимые доказательные пределы | prd/ARCHITECTURE.md, owning ADR, glossary governance |
| Human adoption, Review Case disposition, promotion/publication | Существующие владельцы и контракты Law-Nexus |

GSD-Pi после переключения не остаётся вторым координатором. Его состояние и доказательства сохраняются как история, а не как активная база задач. Прямого штатного конвертера Pi → Path в исследованном Path нет: migrate_core.py предназначен для GSD Core .planning/. Не направлять его на .gsd/. [P1, P2]

Исследован публичный HEAD Law-Nexus f15612b2034ce71c9109326173c5e8a3b8a86b76: актуален при чтении 2026-10-23, сам коммит датирован 2026-09-24. Перед работой сравнить его с фактическим локальным HEAD и origin. Локальная .gsd и пользовательские настройки через GitHub не были доступны. Сведения о состоянии milestone из этого документа не заменяют локальную инвентаризацию. [L1, L2]

Особенности Allspark, проверенный release pin и изолированный HOME описаны
в [ALLSPARK_NOTES.md](ALLSPARK_NOTES.md). Установка и точные версии компонентов
описаны в [INSTALL.md](INSTALL.md); контракт первого запуска агента — в [AGENT_HANDOFF.md](AGENT_HANDOFF.md). Не заменять закреплённые версии произвольным latest.

## 1. Последовательность и контрольные точки

| Этап | Что делаем | Условие выхода |
|---|---|---|
| C0 — inventory | Читаем текущий checkout, локальные инструкции, Pi state, процессы, worktrees, MCP и approvals | Известно, где находятся реальные state и незавершённая работа; неизвестное явно отмечено |
| C1 — freeze и backup | Останавливаем старого writer штатным способом, сохраняем согласованные state и Git snapshots | Ни один процесс Pi не пишет в проект; backup проверен |
| C2 — bootstrap PR | На обычной migration branch готовим tracked overlay и перенос control gates | Diff проверяем, целевые проверки выполнены; остаточный baseline debt назван |
| C3 — чистый remote baseline | Bootstrap PR попадает в default branch; создаём чистый checkout точно на fetched origin default | HEAD равен remote default SHA; индекс и worktree чисты |
| C4 — native Path bootstrap | Native initialize, затем bind-initial; brownfield inspect | Валидный Path state, правильная ветка, один выбранный runtime, без ручного STATE |
| C5 — reconcile backlog и PDD | Переносим только проверенные активные обязательства; создаём небольшой product model | Dependencies и unresolved approvals сохранены; scope модели утверждён |
| C6 — pilot | Выполняем одну ограниченную техническую задачу, затем resume и проверку состояния | Реальные результаты и revision recorded; no-op/пропуск не выдан за успех |
| C7 — cutover | Проверяем отсутствие активных Pi imports/writers и полноту handoff | Path — единственный delivery owner; history сохранена; recovery проверяем |

Не нужно запрашивать отдельное разрешение на каждое чтение, резервную копию, локальную ветку, обратимое исправление или проверку внутри уже разрешённой технической миграции. Решения, требующие существующего human authority, не выводятся из общего согласия на смену инструментов. Публикацию/merge выполнять в пределах фактически выданного разрешения; для review подготовить законченный diff и результаты до обращения к владельцу.

## 2. C0 — прочитать реальное локальное состояние

### 2.1. Bootstrap контекста

Читать в этом порядке:

1. prd/ARCHITECTURE.md.
2. Owning ADR затронутого изменения.
3. prd/architecture/glossary-governance.md и, когда затронуты понятия, §3 prd/temporal-legal-model.md.
4. Применимые локальные AGENTS.md/CLAUDE.md и инструкции skills; выявить, какие из них описывают заменяемый Pi workflow.
5. Текущие Rust/Python interfaces, contracts и tests.
6. Только затем legacy delivery records и дорожные карты как evidence о процессе.

Пользователь уже выбрал уход с Pi: правила, которые предписывают именно старый host, подлежат явной замене в migration diff. Юридические и продуктные инварианты от этого выбора не меняются. Не создавать Rust types из deferred-undefined или runtime deferred. [L3]

### 2.2. Инвентаризация до установки

В .gitignore Law-Nexus исключены AGENTS.md, CLAUDE.md, .gsd/, .mcp.json и .agents/skills/. Поэтому cold clone не отражает действующий рабочий контекст. [L2]

Составить приватный inventory и краткий очищенный отчёт для репозитория:

| Поверхность | Что зафиксировать |
|---|---|
| Git | Absolute root, HEAD, branch, origin, status, staged/unstaged changes, local refs, unpushed commits |
| Worktrees | Каждый путь, branch/HEAD, владелец процесса, незакоммиченные и untracked изменения |
| .gsd | Directory или symlink; настоящий target; state/db/journal/projection files; версия Pi |
| Live execution | Активные Attempts, child processes, supervisors, locks, background jobs и способы их штатной остановки |
| Инструкции | Существующие локальные AGENTS.md/CLAUDE.md; какие части архитектурные, какие относятся к Pi |
| Skills/extensions | Локальные skills, Pi extensions, их версии, прямые runtime imports |
| MCP | Имена серверов, transports, рабочие directories, необходимые функции, имена env vars; никаких значений токенов в Git или чате |
| Hooks | core.hooksPath, tracked hooks и локальные hook wrappers, pre-commit; определить реальных вызывающих Pi |
| Allspark environment | Actual fork build/SHA, source supplement, isolated HOME; Git identity/signing/hooks и toolchain должны работать в обоих окружениях |
| Product/evidence | Доступность corpus, frozen artifacts, source pins, текущие approvals и blockers |
| Другие workflow roots | Наличие .planning/ или .project/; принадлежность, schema и незавершённые transactions |

Не выводить весь environment, private keys, credential files или полные command lines процессов в публичный отчёт. Полный локальный backup может содержать секреты; его не коммитят.

Полезные read-only команды из корня checkout:

~~~bash
git rev-parse --show-toplevel
git rev-parse HEAD
git branch --show-current
git status --short
git worktree list --porcelain
git diff --stat
git diff --cached --stat
git config --get core.hooksPath
git check-ignore -v AGENTS.md CLAUDE.md .mcp.json .gsd .agents/skills
~~~

git config --get и git check-ignore могут завершаться ненулевым кодом при отсутствии значения/совпадения — это факт inventory, а не ошибка миграции. Список ignored/untracked paths сохранять отдельно от их содержимого.

Если .gsd отсутствует, записать local Pi state unavailable. Не восстанавливать его из названий коммитов, README или таблицы roadmap. Можно подготовить technical bootstrap и явно ограниченный brownfield scope; перенос неизвестного backlog остаётся blocked до получения источника.

## 3. C1 — остановка одного writer и резервная копия

1. По inventory определить фактический Pi coordinator/supervisor и дочерние процессы. Запросить штатную паузу/завершение; дождаться устойчивого состояния. Не угадывать PID и не применять массовый kill.
2. Сохранить состояние незавершённых Attempts и привязанные worktrees. Остановка процесса не делает Attempt completed.
3. Проверить, что старый процесс больше не пишет в .gsd, task worktrees и evidence outputs.
4. Создать приватный backup вне рабочего репозитория с ограниченными правами. Записать его absolute path в локальный receipt; в tracked отчёт вынести только безопасный идентификатор/manifest digest.
5. Сохранить отдельно Git history, незакоммиченную работу и workflow state. Git bundle не содержит dirty/untracked/ignored файлов.
6. Сделать согласованный database snapshot штатным export/backup способом. Если используется SQLite WAL, нельзя считать копию одного gsd.db полной базой. Не редактировать SQL, WAL, locks или projection markers вручную.
7. Для symlink .gsd сохранить сам link и снимок реального target с recorded resolved path. Не подменять link пустой директорией.
8. Проверить backup чтением manifest, контрольными суммами и отдельным restore smoke. Не проверять восстановление поверх живого checkout.

Пример Git-части backup после задания абсолютного MIGRATION_BACKUP_DIR оператором:

~~~bash
: "${MIGRATION_BACKUP_DIR:?Set an absolute private backup directory outside the repository}"
umask 077
mkdir -p "$MIGRATION_BACKUP_DIR"
git bundle create "$MIGRATION_BACKUP_DIR/repository.bundle" --all
git diff --binary > "$MIGRATION_BACKUP_DIR/worktree.patch"
git diff --cached --binary > "$MIGRATION_BACKUP_DIR/index.patch"
git status --porcelain=v1 -uall > "$MIGRATION_BACKUP_DIR/status.txt"
git worktree list --porcelain > "$MIGRATION_BACKUP_DIR/worktrees.txt"
git ls-files --others --exclude-standard -z > "$MIGRATION_BACKUP_DIR/untracked-paths.nul"
git ls-files --others --ignored --exclude-standard -z > "$MIGRATION_BACKUP_DIR/ignored-paths.nul"
git bundle verify "$MIGRATION_BACKUP_DIR/repository.bundle"
~~~

Эти команды не копируют untracked/ignored содержимое. Скопировать нужные файлы отдельным backup-способом по inventory, сохраняя permissions и ссылки; большие corpus/cache directories переносить только по необходимости. Для каждого незавершённого worktree сохранить собственные dirty patches и untracked contents. Не считать git stash единственным backup.

**Checkpoint C1:** legacy writer stopped; согласованный state backup и Git/work backup доступны; нет потери локальных инструкций или approvals. До этого не запускать нового координатора на том же дереве.

## 4. C2 — подготовить bootstrap PR

Пока Pi заморожен, Path ещё не активен. Работать на обычной выделенной migration branch. Это явный этап migration preparation, а не фиктивная Path milestone.

Смержить файлы overlay из INSTALL.md: docs/agent-stack/, .ai/, scripts/ai/. Существующие README, AGENTS.md, .gitignore, hooks и MCP настройки читать и изменять точечно. AGENTS.fragment — материал для merge, не команда перезаписи. Private keys и локальные MCP credentials остаются вне Git.

Для Allspark это не перенос старого profile: published fork.009 запускается
через официальный launcher с `.ai/local/allspark-home` и same-commit runtime/skills
supplement. Non-secret MCP declarations переносить в tracked settings;
legacy `.mcp.json` не считать автоматически активным. Выполнить независимый
login; не копировать upstream/Pi refresh tokens. Восстановить обе exact Path
cache copies и общий внешний worktree root. Проверить effective Git
identity/hooks/signing и Rust toolchain при normal и isolated HOME до
первого commit/dispatch. Подробности — INSTALL и ALLSPARK_NOTES.

Затем реализовать следующие control-plane изменения.

Отдельно проверить полноту host integration. scripts/ai/path-run.py — ограниченный launcher для предусмотренных им native operations; его наличие не означает, что upstream Path уже поддерживает Allspark во всех фазах. Для нужных inspect/research/plan/build/review ролей требуется явный проверенный dispatch adapter, включая fresh worker contexts, file scope, tools, outcome handling и isolation там, где её требует контракт. Исследованный upstream не предоставляет готового полного Allspark adapter. Если этого слоя ещё нет, добавить bounded integration task в bootstrap scope и проверить её до объявления cutover. Не выдавать status/validate за end-to-end phase proof и не заменять обязательные независимые роли скрытым inline fallback.

### 4.1. Typed adapter между harness и workflow state

Предлагаемый новый модуль: src/law_nexus_harness/workflow_state.py. Это новый repo-owned adapter, не существующий upstream API.

Контракт адаптера:

- Backend выбран явно: целевой GSD Path. Случайное отсутствие .project не включает Pi fallback.
- Раздельно представлять bootstrap preparation и operational state. В bootstrap можно проверить portable repository controls, но workflow readiness остаётся not-cut-over.
- Для operational Path запускать выбранные native runtime status/validate helpers и читать их typed JSON. Не парсить STATE frontmatter регулярными выражениями.
- При runtime declaration пользоваться её verified runtime; отсутствующий/невалидный runtime не заменять новой глобальной версией.
- Missing, invalid, unsupported schema, unavailable runtime и conflicting ownership — разные диагностические состояния, ни одно не PASS.
- Runtime facts, legacy historical facts и product/review acceptance имеют отдельные поля/типы; не сводить их к одному done.
- Adapter read-only: он не исправляет STATE, не завершает задачи и не пишет Review Case events.
- Pi adapter, если нужен для import inventory, читает только явно указанный frozen snapshot и маркирует его historical. Он не является runtime fallback.
- Новый Path проект без завершённых milestones допустим. Не требовать выдуманной завершённой milestone только потому, что старый governor ожидал completed registry row.

В конфигурации/контракте harness явно определить момент operational cutover. Не выдавать собственные поля адаптера за нативные ключи Allspark, PDD или Path. Operational отсутствие обязательного state должно давать blocking diagnostic; bootstrap report не должен скрывать его под portable PASS. [L4, P2, P3]

### 4.2. Обязательные места изменения

| Файлы/функции | Требуемое изменение |
|---|---|
| src/law_nexus_harness/governor.py: check_active_requirement_contradictions | Убрать неявную зависимость от .gsd/REQUIREMENTS.md; проверять согласованность нового плана с существующим PC/RQ/authority, не переносить local requirement status |
| governor.py: check_roadmap_freshness | Сравнивать tracked projection с typed Path state и явным legacy ID mapping; не полагаться на emoji и числовую непрерывность Pi milestones |
| governor.py: check_gsd_residual_debt | Переопределить active, blocked, deferred inventory, dependencies для Path; unknown legacy debt оставить видимым |
| governor.py: check_gsd_review_dual_truth | Сохранить независимость delivery/review/capability, заменить источник delivery facts |
| governor.py: check_journal_retry_loops, check_compat_marker_hygiene | Pi-specific audit сделать явно historical/not-applicable-to-Path; добавить реальные Path failure/transaction checks, не генерировать fake .gsd journal/compat |
| src/law_nexus_harness/preflight.py: _gsd_state_surface_check и его call site | Читать adapter, заменить Pi headings/remediation; в operational mode missing target state блокирует |
| tests/test_harness_governor.py; tests/test_harness_preflight.py | Обновить фикстуры и semantics; старый missing-Pi PASS нельзя перенести на missing-Path |
| tests/test_project_state_roadmap_freshness.py | Проверять новый adapter/projection; добавить новый проект без completed milestone и конфликт импортированного history |
| prd/project-state/data/roadmap.json и prd/project-state/roadmap.md | Перестроить delivery projection с явными legacy references; не поднимать readiness |
| prd/architecture/review-cases/gsd-review-bridge.md; continuity-contract.md | Создать successor bridge contract/активную ссылку с Path refs; сохранить исторические события и три независимых оси |
| src/law_nexus_harness/review_case/domain.py; adapters/filesystem.py | Расширить source-evidence boundary: workflow .project/.planning не становится нормативным источником; сохранить path/symlink защиты |
| review_case/application.py: record_execution_link_command; policy.py: record_execution_link | Сохранить opaque delivery reference и human/event semantics; не переписывать legal FSM ради нового имени workflow |
| scripts/verify-architecture-graph.py | Обработать новые state roots и symlink aliases без превращения workflow state в source authority |
| scripts/analyze-session-learning.py | Адаптировать активного потребителя .gsd/exec либо явно вывести его из active workflow |
| .github/workflows/repository-quality.yml; .pre-commit-config.yaml; локальные hooks | Подключить portable successor checks и убрать только доказанно Pi-specific active invocations |
| doc/gsd-headless-supervisor.md и scripts/m204_* | Сохранить historical records; заменить текущую навигацию/runbook, не переписывать всю историю |

Не искать все вхождения GSD и массово заменять их на Path. Старые identifiers, hashes, event refs и результаты испытаний остаются историческими данными. Источники actionable dependencies: [L4–L8].

### 4.3. Удалить активную зависимость source integrity от Pi runtime

scripts/m204_s08_source_revision.mjs импортирует verification-source-integrity.js и preferences.js из GSD_HOME/agent/extensions/gsd либо ~/.gsd/agent/extensions/gsd. Его используют в том числе scripts/m210_s02_rebind.mjs и scripts/m210_s02_slice_battery.mjs. Это реальная runtime dependency, а не только текстовое упоминание. [L7]

Порядок замены:

1. Составить call graph активных проверок, которые вызывают старый hasher.
2. Зафиксировать старый алгоритм/version и сохранённые digests как historical evidence.
3. Ввести отдельный versioned successor source-snapshot helper с собственным schema/algorithm identifier и tests. Предлагаемое имя: scripts/verify-source-snapshot-v2.py; оно ещё не существует в исходном Law HEAD.
4. Определить его контракт: deterministic path ordering, raw-byte hashes, scope manifest, HEAD плюс содержимое затронутых tracked/dirty files, поведение для deletion/untracked input/symlink, исключение собственного generated output. Не подменять source snapshot одним git HEAD.
5. Перевести текущие control gates на successor через явный migration diff. Старый m204 helper и byte-bound M210 packets могут оставаться archived replay artifacts, но не обязательным живым вызовом нового стека.
6. Если изменение затрагивает pin-bound governing surface, создать новый successor record по его правилам. Не перезаписывать старые source_revision, verdict или tested revision, чтобы старый checkpoint снова выглядел зелёным.
7. Проверить отсутствие Pi/GSD_HOME imports в active execution path и честный diagnostic при невозможности воспроизвести historical engine-dependent check.

Результат новой проверки не равен старому digest, пока специально не доказана byte-for-byte совместимость. Ни новый hash, ни новая pipeline не создают legal adoption.

### 4.4. Hooks без скрытого обхода

Сначала сохранить original hook files, core.hooksPath и pre-commit configuration. Удалять/заменять только подтверждённый Pi dispatcher; сохранить действующие format, dependency, ADR, evidence и security gates. Path hooks ставить штатным installer в предусмотренный INSTALL.md момент. Проверить композицию hook chains.

Не использовать --no-verify, не отключать все hooks и не переводить failing gate в warning ради bootstrap. Если blocker исторический, классифицировать его и сделать явное scoped decommission/successor изменение с regression coverage.

## 5. Проверки bootstrap PR и baseline debt

Предпосылки: Python 3.13+ и uv, Rust stable с rustfmt/clippy, C compiler/toolchain для bundled SQLite, Node версии из INSTALL.md. В исходном CI использовался Node 22. Для первых задач не нужен optional torch/local-embeddings group.

~~~bash
uv sync --frozen
cargo fetch --locked
~~~

Целевые проверки существующих областей после изменения adapter/bridge:

~~~bash
uv run pytest -q tests/test_harness_governor.py tests/test_harness_preflight.py tests/test_project_state_roadmap_freshness.py
uv run pytest -q tests/test_review_case_domain.py tests/test_review_case_filesystem_adapters.py tests/test_review_case_application.py tests/test_review_case_policy.py
uv run pytest -q tests/test_harness_review_case_cli.py tests/test_documentation_navigation.py
uv run python -m law_nexus_harness governor
uv run python -m law_nexus_harness preflight
uv run python scripts/verify-crate-dependency-allowlist.py
uv run python scripts/verify-adr-conformance.py
~~~

Добавить meaningful tests нового adapter и source-snapshot helper в реальный test suite после их реализации. Нельзя заранее записать их PASS. Минимальные случаи: target state missing; invalid schema; чужой/повреждённый runtime; wrong branch; stale/conflicting source; partial transaction; old+new writer conflict; unresolved imported dependency; pending approval; новый проект без завершённого history.

Portable Python и Rust проверки, существующие в CI:

~~~bash
uv run ruff check src/
uv run ruff format --check src/
uv run basedpyright src/
uv run ty check src/
uv run pyrefly check src/
cargo fmt --all -- --check
cargo check --workspace --offline
cargo clippy --workspace --offline --all-targets -- -D warnings
cargo build --workspace --offline
cargo test --workspace --offline
~~~

Расширять проверки по затронутым рискам и CI gates. Зафиксировать revision, команды, exit codes, scope, skip count, отсутствующие inputs. Не запускать каждый frozen corpus battery как универсальный cold-clone check.

Известный исторический CI baseline на исследованном HEAD — failure, а не all-green: Rust parsing assertion для ledger, 51 basedpyright errors в governor.py, M207 battery с отсутствующими corpus/artifacts и offline dependency. Это исходные факты для сравнения; не waiver и не результаты сегодняшнего запуска. node scripts/m210_s02_slice_battery.mjs ещё зависит от старого engine hasher и не является portable prerequisite нового стека. [L9]

**Checkpoint C2:** подготовлен конкретный PR/diff, работающие проверки отделены от blockers, pre-cutover harness не лжёт о workflow readiness.

## 6. C3/C4 — native bootstrap только на чистом remote baseline

### 6.1. Почему порядок обязателен

Path v1.6.2 bind-initial требует:

- HEAD ровно равен full SHA fetched origin/<default>;
- remote ref всё ещё соответствует fetched ref;
- индекс/worktree чисты;
- единственное допустимое untracked исключение — начальный .project/STATE.md, созданный native initializer;
- .project содержит только этот regular non-linked state file;
- branch не занят другим worktree и не существует как конфликтующая remote branch.

Поэтому нельзя скопировать tracked starter, сделать неопубликованный локальный bootstrap commit и сразу выполнить bind-initial. Рекомендованный путь: отдельный bootstrap PR → merge по обычному разрешённому workflow → clean checkout актуального remote default → native initialize/bind. Не обходить guard скрытым ignore или ручным STATE. [P4]

Если bootstrap PR ещё не merged, закончить доступную подготовку и передать готовый review packet. Это внешний gate, а не повод выдумывать активный Path state.

### 6.2. Выполнение native bootstrap

Следовать INSTALL.md и установленному native router; в Allspark вход — /skill:path. Не создавать .project/STATE.md вручную и не выдумывать пустую schema.

1. Убедиться, что freeze Pi сохранился и merge уже отражён в origin.
2. Выполнить git fetch origin и git remote set-head origin --auto; установить clean checkout на выбранный фактический origin default штатным Git способом. Сохранить все старые worktrees.
3. Сопоставить git rev-parse HEAD с git rev-parse origin/<default>; использовать полный SHA, не предположение main.
4. Если .gsd-path/runtime.json существует, получить verified runtime:

~~~bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
python3 -B "$REPO_ROOT/.gsd-path/status_runtime.py" --repo "$REPO_ROOT" --runtime-path
~~~

5. Читать skill runtime-selection rules: runtime-owned helpers брать из возвращённого каталога, templates/role briefs и bundle-owned helpers — из закреплённой skill installation. Не смешивать версии.
6. Вызвать native router. Его реальный initializer — detect_project.py initialize --repo <ABS_ROOT> --template <ABS_STATE_TEMPLATE> --require-git. Он классифицирует brownfield/greenfield/orphan и сам создаёт допустимый STATE.
7. При orphan, error или wrote_state:false не дописывать state руками. Сохранить diagnostics и выполнить только предусмотренное recovery.
8. Для Law-Nexus ожидается brownfield inspection, но решение принимает helper, не этот документ.
9. Без промежуточного commit между initialize и bind выполнить native pipeline_git.py bind-initial с route.branch, recorded origin/<default> и full fetched SHA. Затем native pipeline_state transition фиксирует returned branch с expected-state comparison, как предписывает router.
10. Повторно запустить route/status/validate. В случае partial transaction следовать typed recovery; не угадывать следующий этап по Markdown.
11. До build настроить integration через native configure-integration. Для первой миграции использовать pull-request, если владелец не задал другую политику. Не оставлять direct случайно только потому, что это встроенный default.

Точный контракт bind-initial: pipeline_git.py bind-initial --repo <ABS_ROOT> --branch <ROUTE_BRANCH> --remote-default origin/<RECORDED_DEFAULT> --base <FULL_FETCHED_SHA>. Placeholders заменяются только результатами helpers/Git. Команду перехода STATE берёт router — она должна сравнивать именно текущие expected fields. [P2–P4]

**Checkpoint C4:** корректный Path-owned branch, native state validate/status и выбранный runtime; нет Pi fallback; bootstrap остаётся отделён от legal adoption.

## 7. C5 — перенос backlog, approvals и минимальный PDD

### 7.1. Перенос delivery backlog

Сначала создать sanitized crosswalk вне .project/archive, например в docs/agent-stack/history/LEGACY_CROSSWALK.md. Это предлагаемый migration artifact; сами приватные Pi данные остаются в backup.

Для каждого действительно активного обязательства записать:

| Поле | Содержание |
|---|---|
| Legacy identity | Полный milestone/slice/task/requirement ID, без переименования истории |
| Evidence | Snapshot identifier, exact source path, revision/digest, record/Attempt reference |
| Observed delivery state | Что прямо следует из snapshot; Unknown, если источника нет |
| Product/review state | Отдельные lifecycle, disposition, human approval и их источники |
| Remaining work | Что надо сделать теперь, что уже является historical evidence |
| Dependencies | Другие delivery items, inputs, approvals и проверяемые blockers |
| New mapping | Новый Path milestone/task или parked/unmapped inventory; причина |
| Acceptance | Нужный observable result, exact verification scope, preserved non-claims |

Нативные Path tasks создавать через его plan/build workflow и template: deps, files allowlist, acceptance, Verify, owner/base/worktree поля имеют свой контракт. Переходы task/state делает Path, а не importer.

Правила:

- Legacy done — historical fact, а не автоматическое Path done.
- Существующий code commit не доказывает завершение старого Attempt и не закрывает Review Case.
- Pending, deferred, hold, unknown и not-adopted не превращаются в approved.
- Не переносить raw Pi DB/STATE в .project/STATE.md или native .project/archive/.
- Не выдумывать непрерывную нумерацию M001… из M210; Path создаёт собственные IDs, crosswalk сохраняет legacy refs.
- Незавершённый branch/dirty patch сначала привязать к owner и scope; затем решать rebase/cherry-pick в отдельной task. Не молча импортировать всё.
- Для missing/contradictory dependencies создать явный blocker и continue с независимой технической работой.
- Технический milestone миграции может завершиться при сохранении отдельно указанного blocked normative backlog.

Сохранить независимость L_delivery, L_review, L_capability. Opaque execution_linked references допускают новый формат ссылки, но не являются mutation или доказательством завершения другого процесса. Human-only event нельзя записывать от имени человека без его действительного решения. [L5]

### 7.2. PDD baseline

Первый scope: операторские inspect/provenance flows; при необходимости bounded replay. Не картографировать весь репозиторий.

1. Прочитать PRODUCT/REQUIREMENTS, owning ADR и implementation.
2. Использовать pdd-map для established behavior, подготовить конкретный model delta.
3. Не считать PRODUCT.md целиком уже утверждённым: его текущий статус proposed/ready-for-assessment, A3 once accepted.
4. Не переносить legal ontology из Rust structs в PDD Entities автоматически.
5. Утвердить только реально неоднозначные вопросы product meaning; после этого записать model и запустить pinned PDD lint по INSTALL.md.
6. pdd-verify запускать report-only. Он делает source inspection, а реальные build/tests выполняет Path task.
7. Reference links связывают model с ADR/PC/RQ/code. Verification receipts и project lifecycle хранятся в execution/evidence surfaces, не в product-model frontmatter.
8. Не присваивать aligned значение Law validated. PDD coverage — охват кода моделью, не corpus coverage.
9. Не запускать параллельный PDD builder и Path orchestrator для одного scope. [D1–D4]

### 7.3. Непереносимый автоматически M210 gate

На исследованном HEAD checkpoint M210/S02 фиксирует not-adopted, owner_admission_ref:none, f13_status:hold, runtime_stop, ноль Review Case events и requirements promoted. Это законное завершение данного gate без grant. [L10]

Миграция инструментов не разрешает normative IR implementation, §3 glossary edits, promotion или S03. Сохранить gate и его provenance. Если новый фактический owner decision уже существует локально, проверить его scope/revision/отдельную governing surface; не переписывать исторический checkpoint по общей фразе «продолжай». Ограничение относится к этой normative scope и не запрещает независимую CLI maintenance.

## 8. C6 — первый ограниченный pilot

Рекомендуемая задача: разобраться с closed argument parsing provenance CLI.

В текущем коде ledger — разрешённый mode, а тест argument_parsing_is_closed_and_requires_one_action ожидает Usage error для ledger + out + write. Исторический CI фиксирует ложный matches! assertion; полный actual return в логе не напечатан. Прежде чем менять test/code, прочитать owning contract. [L9]

~~~bash
cargo test -p ln-consultant-parser --offline --locked --lib amendment_provenance::tests::argument_parsing_is_closed_and_requires_one_action -- --exact
~~~

Для baseline нужна ровно одна найденная test case; 0 tests не PASS. Затем минимальное исправление, сохраняющее отказ для действительно неизвестного mode, отсутствие output/action и конфликт write+check. PDD может описывать эти product scenarios; Path владеет task, изменениями и execution receipt.

Второй, необязательный пилот после успешного первого: existing bounded CLI contracts.

~~~bash
cargo test -p ln-product-cli --offline --locked --test cli_contract
~~~

Принятие migration pilot требует:

- reproducible before/after на recorded revision;
- scoped diff и актуальные тесты;
- один writer/task owner;
- source snapshot новой версии;
- native Path resume после остановки/новой сессии;
- неизменённые legal/product proof ceilings;
- model/code проверены для выбранного scope, без заявления «весь Law-Nexus validated».

## 9. C7 — критерии завершения

Миграция считается завершённой, когда одновременно выполнено:

- Все доступные локальные Pi state, worktrees, instructions и MCP inventoried; unavailable sources названы.
- Legacy writer остановлен, backup и recovery receipt доступны; история не удалена.
- Allspark стартует через официальный launcher из repo config, actual fork version/SHA совпадают с pins; supplement, kernel и skills доступны; секретов в tracked config нет.
- Normal и isolated HOME разрешают один Path runtime digest; placement общий, Git hooks/identity/signing и toolchain проверены в обоих окружениях.
- Нужные фазы Path исполняются через проверенный Allspark dispatch adapter; один build launcher не выдан за полную интеграцию.
- Native Path status/validate/route согласованы с branch/runtime и surviving transaction journals.
- Выбран только один operational delivery backend; отсутствие его state/runtime блокирует.
- Активные harness/CI/hook paths не требуют Pi engine/GSD_HOME.
- Successor source-integrity contract и его tests работают; старые evidence bytes не переписаны.
- Backlog crosswalk сохраняет dependencies, blockers, approvals и Unknown; нет fake completion.
- PDD scope ограничен, references честные, нет второго lifecycle ledger.
- Выполнен ограниченный pilot с реальными evidence и smoke нового resume.
- Остаточный baseline debt классифицирован; нет заявлений all-green на основании skipped/missing-input проверок.
- Review/adoption/capability axes не повышены самой миграцией.
- Handoff содержит текущую revision, где смотреть state, следующую разрешённую задачу и recovery instructions.

Наличие архивного .gsd не считается незавершённой миграцией. Наличие живого старого writer или скрытого active import считается.

## 10. Recovery и rollback

### Ошибка до native initialization

Остановить только migration execution. Сохранить diff, logs и новый checkpoint. Оригинальный checkout/state backup не тронут. Не удалять ветку, worktree или незакоммиченные изменения автоматически.

### Ошибка initialize / orphan state / bind-initial

Не очищать .project и не менять pipeline marker/branch вручную. Записать helper JSON, HEAD, status, selected runtime. Если состояние принадлежит другому процессу, выбрать native recovery или отдельное место после проверки владельца. Не делать новый initialize поверх старого.

### Прерванная Path transaction

Запустить status/route и native diagnostics из выбранной runtime/skill версии. resume-checkpoint, resume-shipment, resume-promotion, resume-next-handoff и undo выполняются по точному typed recovery contract. Не заменять их ручным переносом archive или редактированием Log.

### Нужен откат bootstrap code

Сначала остановить Path writer, сохранить его текущий state и worktrees. Отменять tracked bootstrap изменения обычными reviewable revert commits/PR, сохраняя history; не reset --hard, не clean -fd и не удаление worktrees. Если bootstrap уже merged, учесть последующие commits: вернуть прежнюю ветку не равно откатить всю миграцию.

### Нужен откат локального состояния

Git revert не восстанавливает ignored .gsd, runtime selection, локальные инструкции, MCP secrets или dirty work. Их восстанавливают отдельно из проверенного backup в отдельный recovery checkout, сначала read-only.

Возврат к C1 означает «все writers остановлены». Он не запускает Pi автоматически. Если владелец выберет emergency возврат к старому engine, сначала подтвердить согласованность legacy state/code и отсутствие Path writer; активен снова только один координатор. Основной целевой план остаётся retirement Pi.

## Источники

- [L1 — Law HEAD](https://github.com/rager306/law-nexus/commit/f15612b2034ce71c9109326173c5e8a3b8a86b76).
- [L2 — локальные исключения .gitignore](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/.gitignore).
- [L3 — glossary bootstrap](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/prd/architecture/glossary-governance.md), [living architecture](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/prd/ARCHITECTURE.md).
- [L4 — governor](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/src/law_nexus_harness/governor.py), [preflight](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/src/law_nexus_harness/preflight.py).
- [L5 — Review bridge](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/prd/architecture/review-cases/gsd-review-bridge.md), [application opaque ref](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/src/law_nexus_harness/review_case/application.py#L696-L730), [policy](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/src/law_nexus_harness/review_case/policy.py#L1361-L1440).
- [L6 — source boundary](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/src/law_nexus_harness/review_case/adapters/filesystem.py), [graph/source checks](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/scripts/verify-architecture-graph.py#L629-L746).
- [L7 — live Pi hasher import](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/scripts/m204_s08_source_revision.mjs), [M210 rebind](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/scripts/m210_s02_rebind.mjs), [slice battery](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/scripts/m210_s02_slice_battery.mjs).
- [L8 — CI commands](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/.github/workflows/repository-quality.yml), [pyproject](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/pyproject.toml), [pre-commit](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/.pre-commit-config.yaml).
- [L9 — historical current-HEAD CI](https://github.com/rager306/law-nexus/actions/runs/35998940249), [parser](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/crates/ln-consultant-parser/src/amendment_provenance.rs#L1288-L1379), [failing test](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/crates/ln-consultant-parser/src/amendment_provenance.rs#L5570-L5618).
- [L10 — M210 not-adopted](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/prd/architecture/m210-s02-adoption-checkpoint.md).
- [P1 — Core-only migration implementation](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/gsd-path/scripts/migrate_core.py).
- [P2 — Path native router/bootstrap/recovery](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/gsd-path/SKILL.md).
- [P3 — runtime selection](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/gsd-path/references/runtime-selection.md).
- [P4 — bind-initial guards](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/gsd-path/scripts/pipeline_git.py#L581-L693).
- [D1 — PDD model and coverage](https://github.com/itai-gendler/pdd-kit/blob/a833ce7efa3d37adfae77128b4b153ddaa3ff0ea/docs/product-model.md).
- [D2 — map guardrails](https://github.com/itai-gendler/pdd-kit/blob/a833ce7efa3d37adfae77128b4b153ddaa3ff0ea/skills/pdd-map/SKILL.md).
- [D3 — static verification](https://github.com/itai-gendler/pdd-kit/blob/a833ce7efa3d37adfae77128b4b153ddaa3ff0ea/skills/pdd-verify/SKILL.md#L95-L125).
- [D4 — Law PRODUCT status](https://github.com/rager306/law-nexus/blob/f15612b2034ce71c9109326173c5e8a3b8a86b76/prd/PRODUCT.md#L3-L8).

