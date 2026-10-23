# Установка с нуля: Allspark + GSD Path + PDD Kit

Дата проверки: **2026-10-23**. Целевая платформа — **Ubuntu 24.04 x86_64**
или такая же Ubuntu в **WSL2**. Опубликованный fork.009 требует **glibc 2.39+**;
starter отклоняет другие архитектуры и неподходящую libc. Команды выполняются
в Bash. Native Windows, macOS, Linux arm64 и Ubuntu 22.04 этим комплектом
не поддерживаются. Реальные проверки перечислены в `validation/TESTED.md`
в исходном архиве; установка и миграция пользовательского Law-Nexus ещё не выполнены.

Сначала прочитайте [ALLSPARK_NOTES.md](ALLSPARK_NOTES.md): форк использует
собственный launcher, изолированный HOME и отдельный source supplement.
Одной замены имени `prime-agent` в прежней инструкции недостаточно.

Для существующего Law-Nexus сначала выполнить inventory/freeze/backup из
[MIGRATION.md](MIGRATION.md). Этот документ не удаляет Pi и не переносит его
state автоматически. Полное поручение агенту — [AGENT_HANDOFF.md](AGENT_HANDOFF.md).

## 1. Целевая схема и предел готовности

| Компонент | Ответственность | Данные в репозитории |
|---|---|---|
| Allspark | Модель, инструменты, отдельные процессы исполнения | `.ai/allspark/`, `scripts/ai/allspark*` |
| GSD Path | План, зависимости, tasks, gates, recovery | `.project/`, `.gsd-path/`, root `WORKFLOW.md` |
| PDD Kit | Модель поведения продукта и source-level alignment | `product-model/`, PDD skills |
| Law-Nexus harness | Собственные quality/evidence/authority checks | Существующие Python controls и их миграция |

**Установка portable skills не означает готовый Allspark adapter для всех фаз
Path.** Starter содержит рабочий механизм установки и узкий CLI-мост для
Build/wave Review. Inspect/Research/Plan и другие нужные независимые роли
должны пройти отдельную adapter acceptance из [WORKFLOW.md](WORKFLOW.md).
До этого установка может быть исправна, а полный workflow — ещё не готов.

Начальная конфигурация намеренно использует один Path coordinator, один coder
за раз и свежие Allspark-процессы. PDD orchestration, Allspark autonomous loops,
factory и auto-refinement выключены. Это проектный выбор, не ограничение
возможностей этих инструментов и не operating-system sandbox.

## 2. Закреплённые версии

| Инструмент | Версия | Как устанавливается |
|---|---|---|
| Allspark | `0.10.1-beta.38-fork.009` | Published fork tar и source archive того же commit, отдельные SHA256 |
| GSD Path | 1.6.2 | Официальный npm tar, SHA512, native Python installer |
| PDD Kit | pdd-toolkit 0.37.1 | Официальный npm tar, SHA512, локальный npm prefix |
| Node.js | 22.23.4 | Официальный release tar, SHA256 |
| uv | 0.13.5 | Официальный release tar, SHA256 |
| Bootstrap Python | 3.12+ | Системный Python Ubuntu 24.04 |

Точные URL, hashes и Path runtime digest находятся в `.ai/versions.json`.
Allspark tag — `allspark-v0.10.1-beta.38-fork.009`, source commit —
`91ef629272eea1f556025ef0dbfe2b07bf8053fc`. На дату проверки fork main
`f4fc256bc88b95185cce823e6bd4f7196dc551c0` находится на 13 commits дальше;
его исправления не считаются частью установленного release.

Все команды `scripts/ai/*` — **обёртки данного starter**, а не команды upstream.
Не использовать install.sh/install.ps1 из верхнего README форка: их URL
по-прежнему устанавливают upstream Prime Agent.

Три Python context различаются: system 3.12+ запускает наши/native helpers;
Allspark создаёт собственный kernel 3.11; Law-Nexus требует project Python 3.13+
через его `pyproject.toml`/uv. Не заменять project interpreter на kernel Allspark.

Это pin верхнего уровня. Allspark при первом запуске создаёт kernel на Python
3.11 и устанавливает зависимости; PDD имеет npm dependencies с диапазонами
версий. Полностью герметичный lock всего окружения здесь не обещается.
После пилота можно отдельно закрепить полный environment/image; это не
нужно смешивать с первым переходом с Pi.

## 3. Подготовить машину и checkout

На Windows использовать WSL2 с Ubuntu 24.04 x86_64 и checkout внутри Linux
filesystem, например `~/src/law-nexus`. Не переносить эту Bash-инструкцию
в PowerShell. Перед установкой проверить архитектуру и libc:

```bash
uname -m
getconf GNU_LIBC_VERSION
```

Ожидаются `x86_64` и glibc не ниже 2.39. Базовые пакеты Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates python3 python3-venv \
  build-essential pkg-config libssl-dev unzip rsync
python3 --version
git --version
```

Node, uv и Allspark затем устанавливаются в `.ai/local`, поэтому глобальные npm
install, shell aliases и изменения `.bashrc` этому starter не нужны.

Если Law-Nexus уже есть, работать с существующим checkout после snapshot;
новый clone сам по себе не переносит ignored `.gsd`, private instructions,
MCP credentials и незакоммиченную работу. Для действительно новой машины:

```bash
mkdir -p "$HOME/src"
cd "$HOME/src"
git clone https://github.com/rager306/law-nexus.git
cd law-nexus
```

Такой clone достаточен для подготовки инфраструктуры, но unknown legacy
backlog остаётся unknown, пока не получен snapshot старой рабочей машины.
Не делать checkout исследованного в документе старого SHA поверх новой работы.

## 4. Freeze, snapshot и preparation branch

В [MIGRATION.md](MIGRATION.md) описаны C0/C1: inventory → остановка фактического
Pi writer → согласованный state/Git backup → restore smoke. Только затем
начинается preparation branch. Не создавать её поверх непонятных dirty worktrees.

Если текущее дерево уже чистое и сохранённая работа учтена:

```bash
git switch -c chore/allspark-path-pdd-bootstrap
```

Если такое имя уже существует, использовать принадлежащую этой миграции
ветку или выбрать новое осмысленное имя. Не сбрасывать существующую ветку.

## 5. Внести starter в репозиторий

Распаковать архив отдельно. В репозиторий попадает **содержимое каталога
`repo/`**, а не весь верхний каталог starter. Пример после настройки переменной:

```bash
STARTER_DIR="$HOME/Downloads/allspark-path-pdd-starter"
rsync -ani "$STARTER_DIR/repo/" ./
rsync -a --ignore-existing "$STARTER_DIR/repo/" ./
```

Первый вызов показывает изменения. Второй копирует отсутствующие файлы;
существующие коллизии он пропускает. Для них нужен точечный merge после чтения,
а не уверенность, что `--ignore-existing` применил новую конфигурацию.

Далее объединить `examples/gitignore.fragment` и `examples/AGENTS.fragment.md`
с существующими `.gitignore` и `AGENTS.md`. Root `AGENTS.md` может содержать
локальные секретные примечания — переносить в Git только проверенные правила.
Law-Nexus игнорирует AGENTS.md: убрать этот конкретный ignore или добавить
проверенный файл через адресный `git add -f AGENTS.md`.

Обязательное правило ignore: `/.ai/local/`. Для skills сохранить существующие
custom directories: широкий `/.agents/skills/` уместен, если они уже целиком
генерируются; иначе игнорировать только конкретные generated PDD/Path dirs.

```bash
chmod +x scripts/ai/bootstrap scripts/ai/allspark scripts/ai/allspark-worker \
  scripts/ai/allspark-settings.py scripts/ai/pdd scripts/ai/path-run.py \
  scripts/ai/doctor.py
git check-ignore -v .ai/local/probe
```

## 6. Установить локальные инструменты

```bash
python3 scripts/ai/bootstrap tools --dry-run
python3 scripts/ai/bootstrap tools
```

Первый вызов только показывает pinned URLs и назначения. Второй скачивает
архивы, проверяет hashes, извлекает их и устанавливает PDD CLI под локальным
npm prefix. Allspark fork.009 содержит только `bin/allspark` и
`libexec/prime-agent`. Поэтому bootstrap дополнительно извлекает проверенный
**source archive того же commit** в `.ai/local/allspark-source` и задаёт
`PI_PACKAGE_DIR` на него: оттуда берутся `prime-agent-runtime/`, полные
`skills/` и другие доступные package resources. Kernel sidecar не скачивается
автоматически при его отсутствии. Bootstrap отдельно прогревает kernel без
model call; receipt подтверждает именно сборку установленного слоя.

В published archive нет `models.bundled.json` и `mcp-services.bundled.json`.
Используется предусмотренный кодом compiled fallback и последующий live
catalog/cache. Starter не приписывает release более поздний packaging fix
из main и не подмешивает sidecar из upstream 0.10.1.

Рабочая команда проекта — `scripts/ai/allspark`, которая вызывает официальный
`bin/allspark` из pinned distribution. Payload сохраняет имя `prime-agent`.
Не обходить launcher прямым запуском payload: он отвечает за изоляцию state.

Для нативных команд проекта в текущем Bash-сеансе включить локальные Node/uv:

```bash
source scripts/ai/env.sh
uv --version
node --version
uv sync --frozen
```

Для Rust-проверок нужен Rust toolchain по текущей CI-конфигурации Law-Nexus.
На новой машине установить его по [официальной инструкции rustup](https://rustup.rs/),
затем установить `rustfmt`, `clippy` и, для native LSP, `rust-analyzer`:

```bash
rustup component add rustfmt clippy rust-analyzer
cargo fetch --locked
```

Команды выполняются для toolchain проекта; pin Rust 1.98.1 в исходниках
Allspark относится к сборке самого форка и не заменяет pin Law-Nexus.
Project `.venv`, Cargo target и caches не коммитят. `env.sh` сохраняет обычный
HOME текущей shell и передаёт абсолютные `CARGO_HOME`/`RUSTUP_HOME`, чтобы
дочерний Allspark с изолированным HOME видел установленный Rust.
Python language server — отдельный `pyright-langserver` на PATH; Allspark
не устанавливает его сам. Для первого Rust pilot он не обязателен.
Не подменять project Python 3.13+ kernel interpreter 3.11.

Шаблон `.ai/allspark/settings.json` копируется в локальный profile
`.ai/local/allspark-home/.prime/agent/settings.json`. `ALLSPARK_HOME`
фиксируется на `.ai/local/allspark-home`; официальный launcher меняет HOME
только своему процессу и потомкам. Существующий profile сохраняется. Если инструмент уже установлен
с matching receipt, он используется повторно. При конфликте/partial install
bootstrap останавливается с точным путём; не удалять `.ai/local` целиком,
поскольку там будет auth и сессии. Разбирать только названный tool/cache path.

## 7. Установить portable skills

```bash
python3 scripts/ai/bootstrap skills --dry-run
python3 scripts/ai/bootstrap skills
```

Upstream Path выполняется через `scripts/install.py` из проверенного npm
пакета. Первый install использует `--codex --local --project <ROOT>`: флаг
`--codex` выбирает shared `.agents/skills`, не запускает Codex и не добавляет
Allspark host adapter. В fresh clone существующая tracked runtime declaration
должна совпасть с pins; bootstrap восстанавливает именно этот runtime и
устанавливает skills, сохраняя tracked project contracts.

Bootstrap обеспечивает **две отдельные копии одного exact runtime digest**:
`<обычный HOME>/.gsd-path/runtimes/<digest>` для shell/helpers и
`.ai/local/allspark-home/.gsd-path/runtimes/<digest>` для Allspark. Path 1.6.2
не имеет runtime-cache override и отвергает symlink storage. Поэтому нельзя
заменить вторую копию симлинком или считать только первый cache достаточным.
Декларация `.gsd-path/runtime.json` остаётся единственной и tracked.

Allspark умеет сканировать `.agents/skills` в ancestors текущего checkout,
но ignored bundles primary checkout отсутствуют в новом linked worktree.
Наш launcher использует `--no-skills` с явными абсолютными `--skill` путями
к pinned source skills и primary `.agents/skills`, сохраняя назначенный cwd.
Это делает набор skills одинаковым у owner и workers и исключает случайные
skills из пользовательского окружения. Не копировать только `SKILL.md`.

Для PDD используется эквивалент закреплённой официальной команды:

```bash
npx pdd-toolkit@0.37.1 install \
  --providers agents --scope project --orchestrate=off --yes
```

В самом starter вызов идёт через уже установленный локальный PDD CLI. `agents`
— поддерживаемый alias Codex directory layout. PDD ставит три полных skills
и `.agents/skills/.pdd-kit-install.json`; `product-model/` ещё не создаёт.
PDD не имеет install `--dry-run`: наш preview печатает его команду без исполнения,
а Path preview действительно запускает upstream dry-run.

Нельзя переносить только SKILL.md. Его `references/`, `scripts/` и marker
тоже нужны. При коллизии непринадлежащего PDD каталога не добавлять `--force`
автоматически: сначала определить владельца.

## 8. Разобрать старые hooks, затем включить Path guards

Сохранить текущие `core.hooksPath` и hook files по migration inventory.
Убрать только доказанную активную Pi integration и сохранить остальные
quality gates. Изолированный HOME меняет также поиск глобального Git config:
identity, credential helpers, signing и `core.hooksPath` могут отличаться.
Проверить effective configuration в обоих окружениях; doctor сообщает
несовпадения. При необходимости закрепить проверенные `user.name`, `user.email`
и путь hooks в repo-local Git config. Сохранить выбранную владельцем signing
policy и цепочку hooks. Не копировать целиком `~/.gitconfig`, `~/.ssh` или
credentials в Allspark HOME. После review цепочки:

Если identity пока задана только глобально, добавить её в local config этого
репозитория с вашими реальными значениями:

```bash
git config --local user.name "Ваше имя"
git config --local user.email "Ваш Git email"
```

Это локальные Git settings, а не файлы для commit. Signing и credential helper
переносить по их действующему контракту; успешный doctor не заменяет проверку
подписанного commit и remote access. Затем установить hooks:

```bash
python3 scripts/ai/bootstrap hooks --dry-run
python3 scripts/ai/bootstrap hooks
```

Это штатный `--hooks-init`. Он создаёт Git guards и Codex hook settings.
Allspark не выполняет `.codex/hooks.json`; Git hooks проверяют Git операции,
а не каждую запись файла. Поэтому это **не native fail-closed PreToolUse
защита Allspark**. Ограничения worktree/allowlist должны также проверяться
Path и проектными gates.

Если `.project/STATE.md` ещё отсутствует, native hooks разрешают bootstrap
commit/push по своему bootstrap contract. Если state уже есть, сначала ownership/recovery;
исключение для bootstrap на такой checkout не распространяется.

## 9. Настроить Allspark и сохранить public settings в Git

```bash
python3 scripts/ai/allspark-settings.py init
python3 scripts/ai/allspark --check-config
./scripts/ai/allspark
```

Bootstrap tools уже подготавливает локальное kernel environment через uv;
первый полноценный запуск проверяет его готовность. В интерфейсе Allspark: `/login`, затем `/model`. Выбрать реального доступного
провайдера/модель; на пустом профиле `model list` может не показывать моделей
до авторизации. На первом пилоте достаточно одной способной модели для всех
ролей: сначала проверить механику и качество, затем разводить модели по ролям.

После выхода:

```bash
./scripts/ai/allspark model list
python3 scripts/ai/allspark-settings.py export-model
git diff -- .ai/allspark/settings.json
```

Экспортируются только `defaultProvider`, `defaultModel` и, если задан,
`defaultThinkingLevel`. Auth не читается и не копируется. После последующего
редактирования tracked settings **явно применить** их:

```bash
python3 scripts/ai/allspark-settings.py apply
python3 scripts/ai/allspark --check-config
```

Обычный launch ничего не перезаписывает. `apply` следует выполнять, когда
workers остановлены. Настройки launcher проверяет в локальном profile и в
реальном Allspark project path `<cwd>/.prime/agent/settings.json`; конфликт
показывается как ошибка вместо молчаливого override.

Основные настройки starter:

```json
{
  "rlmMaxDepth": 0,
  "harnessRefinements": false,
  "autoRefine": {"enabled": false, "compact": false},
  "factory": {"enabled": false},
  "agentTraces": {"enabled": false},
  "telemetry": {"enabled": false},
  "compaction": {"enabled": true, "thresholdPercent": 80},
  "enableSkillCommands": true,
  "lsp": {"enabled": true},
  "editHybrid": {"enabled": true, "defaultMode": "replace"},
  "graph": {"enabled": false, "auto": "off"},
  "jev": {
    "enabled": "off",
    "autoThinking": "off",
    "graphRerank": "off",
    "toolArbiter": "off"
  }
}
```

Это общий стартовый baseline; точный действующий шаблон, включая fork
native-tool настройки, находится в `.ai/allspark/settings.json`. Для pilot
LSP и native edit включены, graph выключен. Включать graph после проверки
актуальности индекса и изоляции worktree. Judge layer задаётся строкой `"jev": {"enabled":"off"}`,
а не boolean `false`. Его `autoThinking`/`graphRerank` в коде имеют default
`auto`, хотя README описывает старый default. Политика migration фиксирует
их явно. Подробнее — [ALLSPARK_NOTES.md](ALLSPARK_NOTES.md).

`rlmMaxDepth:0` предотвращает вложенный RLM spawn в новых сессиях; Path
использует внешние процессы. Здесь нет выдуманного `autonomous.enabled` или
`autoUpdate`. Launcher не передаёт autonomous flags и устанавливает реальный
`PI_SKIP_VERSION_CHECK=1`. Он отклоняет обычные resume/continue/fork, поскольку
сохранённая Allspark session может нести прежние autonomy overrides. Продолжение
работы выполняется из disk state Path в новой сессии. Обновление происходит
отдельным изменением pins и повторной проверкой; не использовать `/update`
или обходить repo wrapper во время migration.

### MCP и DeepWiki

Public MCP config входит в tracked `.ai/allspark/settings.json`, например:

```json
{
  "mcpServers": {
    "deepwiki": {
      "type": "http",
      "url": "https://mcp.deepwiki.com/mcp"
    }
  }
}
```

Объединить этот фрагмент с существующими settings и выполнить
`python3 scripts/ai/allspark-settings.py apply`, пока workers остановлены.
Для публичного DeepWiki авторизация не требуется. В новой Allspark session
проверить connection и получить реальные schemas через `mcp.list_connections()`
и `await mcp.list_tools("deepwiki")`; имена remote tools брать из discovery.
Наличие settings не доказывает handshake или индекс конкретного репозитория.

Legacy `.mcp.json` не импортируется автоматически. Переносить отдельно имена,
transport, command/args и env references. HTTP bearer token можно связать через
`bearerTokenEnvVar`, stdio env — через `{"env":"ENV_NAME"}`. Значения секретов
и `auth.json` остаются local. `allspark mcp add/list/get/remove` управляет
локальным global profile; у него нет `--scope project`. Для portable config
источник истины — tracked template и явный apply.

## 10. Проверить установленный слой

```bash
python3 scripts/ai/doctor.py
python3 scripts/ai/path-run.py runtime
python3 scripts/ai/path-run.py --dry-run round --wave 1
```

Doctor проверяет versions, supplemental runtime/skills, profile, PDD marker,
обе копии Path runtime digest, внешний worktree root и effective Git hooks
и identity в shell/Allspark окружениях. До native initialization ожидается
`PENDING Path initialization`, а не фиктивный PASS pipeline. Existing orphan
`.project` или missing runtime — ошибки. Doctor не делает model call.

Первый отдельный model smoke с вашей авторизацией:

```bash
printf '%s\n' 'Ответь только OK. Не вызывай инструменты и не меняй файлы.' \
  | ./scripts/ai/allspark -p
```

Затем в интерактивном Allspark проверить, что `/skill:pdd-verify` и `/skill:path`
обнаруживаются именно как skills. Не запускать native Path initialization
до следующего этапа. Неизвестная slash-строка может пройти в модель как
обычный текст — один осмысленный ответ не доказывает загрузку skill.

## 11. Подготовить и принять bootstrap PR

Внести migration controls из MIGRATION.md: typed state adapter, live source
integrity successor, обновлённые consumers/tests. Отдельно реализовать и
проверить необходимый Allspark phase adapter. Для первоначального PDD model
можно подготовить bounded delta до Path initialization и включить принятый
результат в bootstrap PR; большой model не является prerequisite.

Reviewable bootstrap включает `.ai/` без local, `scripts/ai/`, документы,
согласованный `AGENTS.md`, native `WORKFLOW.md`, `.gsd-path` declaration/shims,
изменения harness и только реально нужную generated host config. Git hooks
сами в commit не попадают. Перед staging проверить ignore и diff.

Не писать `.project/STATE.md` в этом PR. Native Path binding для существующего
remote проекта требует clean HEAD на fetched origin default. Поэтому
**подготовительный PR сначала принимается, затем начинается первый Path
milestone**. Если merge ещё не разрешён, подготовить весь конкретный diff,
проверки и PR packet; это единственная оставшаяся внешняя операция.

## 12. Первый Path milestone на принятом baseline

После bootstrap merge обновить refs и перейти штатным Git способом на
чистый default branch. Не использовать `reset --hard` для создания видимости
чистоты.

```bash
git fetch origin
git remote set-head origin --auto
git symbolic-ref --short refs/remotes/origin/HEAD
git status --short
git rev-parse HEAD
```

Сравнить HEAD с полным SHA показанного `origin/<default>`; не предполагать,
что ветка всегда называется main. В Allspark выполнить `/skill:path` и следовать
native initialization/route из [PATH_SETUP.md](PATH_SETUP.md). Router использует
`detect_project.py initialize`, затем `bind-initial`, затем native transition
branch. Между initialize и bind не делать отдельный commit.

Выбрать `pull-request` integration через native configure-integration до
build, если владелец не задавал другую политику. Не править state YAML руками.

```bash
python3 scripts/ai/path-run.py status
python3 scripts/ai/path-run.py validate
python3 scripts/ai/path-run.py route
python3 scripts/ai/doctor.py --require-path-state
```

Если фаза требует ещё не реализованный Allspark dispatch, сохранить native
state и сообщить о конкретной отсутствующей capability. Не заменять роли
одной беседой и не объявлять operational cutover.

## 13. PDD baseline, pilot и переключение

Для Law-Nexus начать с inspect/provenance CLI. Иерархия authority остаётся
существующей: architecture/owning ADR/glossary; PRODUCT и REQUIREMENTS нельзя
целиком считать принятыми только по их наличию.

В Allspark использовать `/skill:pdd-map` с этим bounded scope. Подготовить
конкретную model delta, подтвердить спорный смысл и только затем записать её.
Если Path уже active, model-only change должен входить в Path task и landing;
`product-model/` — продуктовые файлы, не бесплатный workflow checkpoint.

В native PDD `product-model/config.yaml` допустимы:

```yaml
schema: 11
sdd:
  paths:
    - .project/
```

Это фрагмент config, а не готовая замена всего сгенерированного файла.
`sdd.paths` указывает на planning artifacts; он не синхронизирует статусы.
Не добавлять произвольные `approved/validated/status` поля в strict frontmatter.

```bash
python3 scripts/ai/pdd lint --json
python3 scripts/ai/pdd view --no-open
```

`view` запускает локальный viewer; `Ctrl+C` завершает его. `lint` проверяет
структуру, не соответствие коду. Source alignment выполняет skill:

```text
/skill:pdd-verify report only. Проверь только согласованный scope
inspect/provenance CLI и перечисли aligned, gaps и unverifiable.
Не меняй model, code или файлы и не запускай builder.
```

По контракту PDD skill `report only` запрещает записи/делегирование; одного
`--orchestrate=off` для этого недостаточно. Это инструкция агенту. PDD verification не запускает
тесты продукта. Actual tests и native Path review/landing выполняются отдельно.

Далее выполнить pilot из MIGRATION.md, проверить новую сессию/resume по Path,
повторить scoped controls и явно зафиксировать cutover. Только после C7
GSD-Pi перестаёт быть активной зависимостью. Архивная `.gsd` может сохраняться.

## 14. Где что хранится и восстановление другой машины

| Surface | В Git? | Примечание |
|---|---|---|
| `.ai/versions.json`, `.ai/allspark/`, `.ai/path-run.json` | Да | Pins, публичные настройки, роли |
| `scripts/ai/`, `docs/agent-stack/` | Да | Воспроизводимая установка и handoff |
| `.gsd-path/`, root AGENTS/WORKFLOW | Да | Проверенные native contracts/launchers |
| `.project/`, `product-model/` | Да | По native workflow и scopes |
| `.agents/skills/` | Generated | Восстановить полные pinned bundles, включая marker |
| `.ai/local/allspark-home/.prime/agent/` | Нет | Auth, private settings, sessions и logs |
| `/tmp/allspark-<uid>-<root-hash>.sock` | Нет | Короткий per-repository supervisor socket; выбирается shared helper |
| `.ai/local/{allspark-dist,allspark-source,node,uv-dist,pdd,vendor,kernel-venv}` | Нет | Pinned payload, source supplement, инструменты и окружение |
| `.ai/local/{downloads,uv-cache,uv-python,npm-cache}` | Нет | Локальные кэши |
| `.git/hooks` или effective hooksPath | Нет | Восстановить `bootstrap hooks` |
| `<обычный HOME>/.gsd-path/runtimes/<digest>` | Нет | Exact runtime для shell/helpers |
| `.ai/local/allspark-home/.gsd-path/runtimes/<digest>` | Нет | Тот же exact runtime для Allspark HOME; отдельная копия |
| `<parent>/<repo-name>-path-worktrees/` | Нет | Общий внешний root task/review worktrees |

Path запрещает размещать worktree root внутри primary repository или другого
worktree того же Git repository. Starter задаёт `GSD_PATH_WORKTREE_ROOT`
абсолютно: по умолчанию sibling `<repo-name>-path-worktrees` рядом с primary
checkout. Это один путь для normal shell, Allspark и workers, независимо
от HOME. Если Path уже записал placement receipt, его нельзя молча заменить
новым env значением; launcher проверяет существующее размещение.
Параметры нашей обёртки описаны в [PATH_SETUP.md](PATH_SETUP.md).

Таким образом, в Git находится переносимое намерение, а binary/cache/auth
восстанавливаются отдельно. Два HOME здесь — свойство форка, не два delivery
state и не две независимые установки workflow.

На второй машине: clone → системные prerequisites → `bootstrap tools` →
`bootstrap skills` → `bootstrap hooks` → `allspark-settings.py apply` → login →
doctor → native state/route/recovery. Credentials и existing live worktrees
не возникают из clone. Скопированный venv с другого абсолютного пути не
считать переносимым.

## 15. Обновления

Обновлять отдельным PR: новые pins/hashes и runtime migration → bootstrap
на disposable checkout → smoke profile/skills/worktree/dispatch → один pilot.
Согласовать version checks и CLI/settings assumptions обёрток с новой
версией; одной замены числа в versions.json для upgrade недостаточно.
Не запускать `@latest`, `allspark update` или менять generated skills во время
product task. Старый Path declaration нельзя исправлять вручную под новый
digest: использовать его штатный runtime upgrade/restore contract.

Первичные источники и DeepWiki MCP: [SOURCES.md](SOURCES.md). Что действительно
проверено при подготовке: `validation/TESTED.md` в исходном архиве starter.
