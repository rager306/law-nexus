# Allspark: отличия форка, которые влияют на установку

Проверено 2026-10-23 по GitHub release, фактическому архиву и исходникам
`91ef629272eea1f556025ef0dbfe2b07bf8053fc`. Этот файл объясняет решения starter;
пошаговые команды находятся в [INSTALL.md](INSTALL.md). Состояние проверок —
в `validation/TESTED.md` исходного архива.

## 1. Какой именно Allspark устанавливаем

| Поле | Закреплённое значение |
|---|---|
| Repository | `rager306/allspark` |
| Release tag | `allspark-v0.10.1-beta.38-fork.009` |
| Commit tag | `91ef629272eea1f556025ef0dbfe2b07bf8053fc` |
| Asset | `allspark-v0.10.1-beta.38-fork.009-linux-x86_64.tar.gz` |
| SHA256 asset | `e910a9277a456f239a77d82cae16d630f199e43d730186a04370463b8efd4600` |
| Platform | Linux x86_64, glibc 2.39+ |
| Main при исследовании | `f4fc256bc88b95185cce823e6bd4f7196dc551c0`, 13 commits после tag |

Название Allspark относится к launcher и fork build. Compiled payload
сохраняет имя `prime-agent`, crates — `pa-*`, environment — `PRIME_AGENT_*`
и `PI_*`, kernel API — `rlm.*`. Переименовывать их в своих scripts нельзя.
Для выбора модели использовать подтверждённый CLI синтаксис `--model <value>`
или интерактивный `/model`. В этом pin README shorthand `-m` и форма
`--model=<value>` не поддерживаются parser; repo wrapper их отклоняет с
подсказкой, вместо добавления собственных скрытых aliases.

Форк идентифицируется по фактическому `--version`, release commit и hash,
а не только по слову `allspark` в PATH. Ожидаемый вывод данного payload:

```text
allspark 0.10.1-beta.38 (fork build fork.009; upstream prime-agent 0.10.1-beta.38)
```

Fork.009 основан на upstream beta.38;
это не тот же build, что upstream stable 0.10.1 из предыдущего starter.

Main уже содержит отдельные fixes graph architecture/index truth,
provider-session-id, overflow/idle timeout и упаковки catalogs. Они не
становятся частью fork.009 от чтения README main. Upgrade на следующий fork
release или собственный stamped build — отдельный проверяемый PR.

Источники: [release](https://github.com/rager306/allspark/releases/tag/allspark-v0.10.1-beta.38-fork.009),
[compare tag→main snapshot](https://github.com/rager306/allspark/compare/91ef629272eea1f556025ef0dbfe2b07bf8053fc...f4fc256bc88b95185cce823e6bd4f7196dc551c0),
[fork changelog](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/CHANGELOG-FORK.md).

## 2. Почему bootstrap скачивает и release, и source

В опубликованном tar находятся только launcher и binary. Для работы Python
kernel нужен source sidecar; автоматически скачать отсутствующий sidecar
bootstrap kernel не умеет. Поэтому starter использует две независимо
проверяемые загрузки одного source revision.

| Локальная поверхность | Назначение |
|---|---|
| `.ai/local/allspark-dist/bin/allspark` | Официальный launcher из release |
| `.ai/local/allspark-dist/libexec/prime-agent` | Скомпилированный payload |
| `.ai/local/allspark-source/prime-agent-runtime/` | Kernel source того же commit |
| `.ai/local/allspark-source/skills/` | Полные native skill packages того же commit |
| `.ai/local/kernel-venv/` | Созданное для этой машины kernel environment |
| `.ai/versions.json` | Tracked URL, версии, hashes и runtime digest |

`PI_PACKAGE_DIR` задаётся на проверенный `.ai/local/allspark-source`.
Это явное package-resource resolution, а не смешивание версий. Нельзя взять
`skills/` из случайного upstream main или оставить inherited `PI_PACKAGE_DIR`
от другого агента. Source archive целиком сохраняется как package supplement;
сборка Rust binary на машине пользователя не нужна.

В tar fork.009 нет JSON bundled catalogs, а main workflow был исправлен
позже. Код поддерживает compiled fallback моделей и MCP catalog; прямые
MCP entries в settings также независимы от наличия этих JSON. Starter не
генерирует новые каталоги и не выдаёт их за часть опубликованного asset.

Источники: [release workflow в tag](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/.github/workflows/release-fork.yml),
[kernel source resolution](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/kernel/bootstrap/venv/runtime_source.rs),
[model fallback chain](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-models/src/chain.rs),
[MCP catalog assembly](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/mcp/service_catalog.rs).

## 3. Изолированный HOME — часть рабочего контракта

Официальный launcher выставляет HOME в ALLSPARK_HOME и фиксирует agent/session
paths внутри него. В starter ALLSPARK_HOME — абсолютный путь
`<primary>/.ai/local/allspark-home`; profile остаётся с upstream layout:
`.prime/agent/settings.json`, `auth.json`, `sessions/`, `logs/`.
Публичная настройка хранится в `.ai/allspark/settings.json`, затем явно
применяется в этот profile. Само по себе `.ai/allspark/` не является нативным
config directory Allspark. Supervisor socket задаётся shared helper отдельно:
`/tmp/allspark-<uid>-<root-hash>.sock`. Короткий путь избегает Unix socket
path limit; hash primary root разделяет проекты. Socket не находится
в profile и не переносится через Git.

`env.sh` не меняет HOME интерактивной shell. Allspark launcher меняет HOME
своему процессу и потомкам. Поэтому нужно согласовать четыре вещи:

1. **Path runtime.** Native helpers используют `Path.home()`. Нужны два
   проверенных cache с одним digest: host HOME и Allspark HOME. Symlink storage
   не допускается Path. Декларация и `.project` остаются одними.
2. **Worktrees.** Оба окружения используют общий внешний абсолютный root
   `<parent>/<repo-name>-path-worktrees`. Уже записанный Path placement receipt
   проверяется и сохраняется; новый env не переносит существующие worktrees.
3. **Git.** Repository-local config читается в обоих окружениях, global config
   может различаться. Проверить identity, hooksPath, signing и способ доступа
   к remote. Не отключать signing и не копировать secrets ради обхода ошибки.
4. **Toolchain.** `CARGO_HOME` и `RUSTUP_HOME` передаются абсолютными путями;
   project Python и kernel Python остаются разными средами.

Upstream `auth.json`, models и refresh tokens не копируются. В Allspark нужно
снова выполнить `/login`. Native paths проекта `<cwd>/.prime/agent/` также
сохраняются: wrapper выявляет конфликтующие settings там, вместо того чтобы
предполагать, что они называются `.allspark/`.

Источник: [официальный launcher](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/scripts/allspark-launcher.sh).
Архитектурное описание: [fork identity](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/docs/fork-identity.md).
Точный код имеет приоритет при расхождении с описанием.

## 4. Какие fork tools полезны Law-Nexus

| Возможность | Рекомендация для первого migration pilot |
|---|---|
| Native LSP | Использовать для Rust symbols, references, diagnostics при установленном `rust-analyzer` |
| Native edit | Использовать проверяемые небольшие edits; результат подтверждают обычный diff и tests |
| Graph | Рассматривать как вспомогательный индекс кода; включать после проверки worktree isolation и актуальности |
| Jev/judge chain | Явно выключить на первом pilot; оценивать позже отдельной задачей |
| Automatic refinement/factory/autonomous | Оставить выключенными, пока единственный delivery coordinator — Path |
| Debug log | Включать локально для конкретного сбоя; logs не коммитить |

В fork.009 встроенная таблица LSP содержит **шесть** серверов: Rust,
TypeScript/JavaScript, Go, Python, C/C++ и Bash. `rust-analyzer` и
`pyright-langserver` запускаются с PATH по требованию; это не установка
сервера за пользователя. Поля `lsp.servers` и `lsp.idleTimeoutMs` есть в
settings schema, но active engine создаёт `LspManager::new()` без передачи
этих overrides. Starter не предлагает непроверенную настройку этих полей.

`jev.enabled` принимает строки `off`, `auto`, `on`. `false` — неподходящий
тип. Внутренние defaults autoThinking/graphRerank уже `auto`; внешняя gate
`enabled` по умолчанию off. Для воспроизводимой migration policy выключить
слой явно, вместо надежды на комментарии старой версии.

Почему graph выключен на старте: default DB находится в общем profile
`<agentDir>/graph.db`, а project identity строится из последнего компонента
root path. В database `projects.name` — primary key, и conflict обновляет
`root_path`. Отсюда следует конкретный риск: два разных worktrees с одинаковым
basename, использующие общий profile, могут занять одну project identity.
Это вывод из схемы, не утверждение, что все worktrees Path обязательно
конфликтуют. Перед включением нужен проверенный способ раздельного DB или
уникальной identity, затем bounded indexing/re-index/freshness test на двух
worktrees. Одного `graph.enabled:true` в shared profile для этого недостаточно.

Источники: [project name из basename](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/tools/graph.rs),
[DB schema](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-graph/src/schema.rs),
[store upsert](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-graph/src/store.rs).

Ни graph, ни judge, ни PDD не принимают юридических решений. Architecture,
owning ADR, glossary и source-bound adoption в Law-Nexus остаются authority.
Native LSP rename/edit — пишущие инструменты; название reviewer role и
словесный read-only brief не являются operating-system sandbox.

Источники: [LSP server table](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-lsp/src/servers.rs),
[engine integration](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/session_engine/engine.rs),
[settings types и enum defaults](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/settings/types.rs).

## 5. Skills, PDD и MCP — три разные поверхности

**Skills.** Allspark читает portable Markdown skills и свои Python skill
packages. Package manager умеет находить `.agents/skills` в ancestors.
Repo wrapper выбирает точные абсолютные skill roots через `--no-skills`
и `--skill`, чтобы linked worktree использовал те же bundles. Полные
scripts/references и PDD install marker нужны наравне с `SKILL.md`.

**PDD Kit.** Устанавливается прежней командой `pdd-toolkit@0.37.1 install
--providers agents --scope project --orchestrate=off --yes`. Это shared skills
layout. Команды Allspark — `/skill:pdd-map`, `/skill:pdd-ideate`,
`/skill:pdd-verify report only`. Отключённая PDD orchestration не делает все
skills read-only и не создаёт полного host adapter GSD Path.

**MCP.** Config находится в `settings.mcpServers`, transport обозначается
обязательным `type: http` или `type: stdio`. Не считать legacy `.mcp.json`
подключённым от одного наличия этого файла. CLI `mcp add` пишет local global
profile и не имеет project scope; переносимый источник — tracked settings.
HTTP secrets передаются через `bearerTokenEnvVar`, stdio env — через
`{"env":"ENV_NAME"}`. OAuth сохраняется отдельно в private auth store.

DeepWiki public endpoint `https://mcp.deepwiki.com/mcp` работает без auth.
Вызовы и argument schemas нужно получать через live discovery. В ходе
подготовки доступный сервер объявил `ask_wiki_question`, хотя публичная docs
страница называла `ask_question`; это наглядная причина не угадывать API.
Индекс конкретного fork revision и полнота его документации не гарантированы.

Источники: [auto-discovery](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/packages/resolve/auto.rs),
[explicit resource resolution](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/resources/resolution.rs),
[MCP settings schema](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/mcp/mod.rs),
[MCP CLI](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-cli/src/mcp_command.rs),
[DeepWiki docs](https://docs.devin.ai/work-with-devin/deepwiki-mcp).

## 6. Какие положения README нельзя переносить буквально

| Документация | Что проверено для данного pin |
|---|---|
| Верхний README предлагает installer Prime и Windows PowerShell | Ссылки ведут к upstream; fork release имеет один Linux x86_64 asset |
| Crate README описывает полный exe-adjacent release package | Фактический fork tar содержит два файла; source supplement обязателен для kernel/skills |
| Fork README перечисляет 57 LSP servers | Active table в данном pin содержит 6 |
| Fork README предлагает `lsp.servers`/idle timeout tuning | Поля не подключены к active engine в исследованном pin |
| Fork README называет default Jev consumers `off` | Enum defaults уже `auto`; outer gate off |
| Названия `.allspark` и legacy migration из раннего плана | Fork identity помечает тот план superseded; текущий путь задаётся launcher HOME |
| README показывает 9router free-tier quickstart | Main удалил соответствующие dead routes; это не рекомендуемый старт migration |
| Наличие fork RLM/skills предполагает совместимость всех Path phases | Full phase dispatch требует отдельной repo-owned интеграции и acceptance |

Windows named-pipe namespace в fork identity отмечен как нерешённая граница
coexistence. Поэтому Windows-сценарий starter — WSL2/Linux, а не выдача
upstream install.ps1 за installer Allspark.

## 7. Когда можно считать перенос на Allspark готовым

Успешный `--version` подтверждает binary; kernel bootstrap — подготовку Python
runtime; skill discovery — доступность prompts/scripts. Эти проверки не
подтверждают все Path phases, реальный provider или сохранность legacy state.

До operational cutover должны отдельно пройти: migration inventory/backup,
оба runtime cache, Git/toolchain в двух окружениях, model smoke, required Path
phase adapter, один bounded Law-Nexus pilot и восстановление owner session
из native state. Полная матрица — в [MIGRATION.md](MIGRATION.md) и
[WORKFLOW.md](WORKFLOW.md). Ни установка форка, ни PDD alignment не меняют
M210 adoption/hold и human review authority.
