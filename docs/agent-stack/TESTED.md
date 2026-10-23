# Фактическая проверка Allspark starter

Дата: **2026-10-23**. Отчёт относится к адаптации **Allspark fork.009**.
Проверки выполнялись в отдельных временных Git repositories на Linux x86_64,
glibc 2.39, Python 3.12.14. Law-Nexus, его GitHub, реальное состояние GSD-Pi
и пользовательские provider credentials не изменялись.

## 1. Проверено именно для Allspark

| Область | Фактическая проверка | Результат |
|---|---|---|
| Release identity | GitHub release/tag metadata, actual archive, SHA256SUMS, полный `--version` | fork.009, commit `91ef629272eea1f556025ef0dbfe2b07bf8053fc` |
| Platform | `readelf` downloaded payload | Требует GLIBC_2.39; опубликован только Linux x86_64 asset |
| Archive layout | Actual tar contents | Только `bin/allspark` и `libexec/prime-agent`; runtime/skills/catalog JSON отсутствуют |
| Source supplement | SHA256 source archive того же commit, extraction, `PI_PACKAGE_DIR` | PASS |
| Fresh tools | Настоящий `bootstrap tools` в disposable checkout | Node 22.23.4, uv 0.13.5, Allspark fork.009, PDD 0.37.1 — PASS |
| Kernel | Настоящий официальный `--allspark-bootstrap` с source supplement | PASS; Python 3.11.17, runtime установлен из pinned source |
| Missing sidecar | Cold release без `PI_PACKAGE_DIR` | Ожидаемый exit 1 с ошибкой отсутствующего runtime |
| Launcher | Настоящие `--version`, `--help`, `--check-config` | PASS |
| Launcher guards | Autonomous/resume/update, invalid project Jev type, headless без модели | Ожидаемые отказы |
| Explicit model | `--model VALUE` проходит guard; финальный exec перехвачен тестом | PASS; модель не вызывалась |
| Settings | Init сохраняет существующий private profile; актуальный template применим | PASS; auth не открывается |
| HOME mapping | Original HOME, isolated HOME, profile, sessions, source, kernel, socket | PASS |
| Shell isolation | `source env.sh` в primary и sibling | HOME не меняется; fork PRIME/PI variables не вводятся; существующие upstream vars сохраняются |
| Worktree topology | Настоящий linked worktree и canonical primary resolution | PASS; внешний storage; отдельный cwd; общий profile/source |
| Placement | Существующий native receipt, conflicting env, nested primary/sibling storage | Receipt сохранён; конфликты и вложенные paths отклонены |
| PDD install | Настоящий `agents/project/orchestrate=off` | Полные 3 skills; marker `orchestrate: "off"` |
| Path install | Настоящий native installer 1.6.2 | 16 skills и native contracts |
| Dual cache | Native restore + `status_runtime.py --runtime-path` в обоих HOME | Один exact version/digest, две validated cache copies |
| Git hooks | Настоящий `bootstrap hooks`, doctor в обоих HOME | Одинаковые effective hooks с Path guards |
| Git execution | Реальный bootstrap commit из isolated HOME до `.project/STATE.md` | Native pre-commit/commit-msg прошли, bypass не использовался |
| Sibling execution | Реальные Allspark `--version`, `--check-config`, PDD `--version` из linked worktree | PASS; Allspark cwd — sibling, ресурсы — canonical primary |
| Combined doctor | После tools → skills → hooks | Exit 0; model selection/Path initialization остаются ожидаемо PENDING |
| DeepWiki MCP | `read_wiki_structure` и два `ask_wiki_question` по `rager306/allspark` | Сервер доступен, fork индексирован; release-specific утверждения сверены с primary sources |
| Artifact validation | 7 Python scripts, 2 Bash scripts, 3 JSON files, 13 Markdown files | AST/Bash/JSON syntax, Markdown fences и внутренние ссылки — PASS; 26 файлов |

Системный Rust toolchain в disposable combined fixture не устанавливался.
Doctor честно сообщил `PENDING cargo/rustup`; проверка Law-Nexus toolchain
остаётся этапом установки на целевой машине. Git signing configuration
сравнивалась между окружениями; подписанный commit с вашим ключом
и remote authentication не проверялись.

В проверках HOME дочерних процессов указывал на отдельные временные каталоги.
Реальный пользовательский home не использовался для Path install. Native
runtime validator, hooks и Git semantics не заменялись заглушками.
Официальный launcher Allspark использовался без изменений.

## 2. Pins и происхождение доказательств

Release archive SHA256:

```text
e910a9277a456f239a77d82cae16d630f199e43d730186a04370463b8efd4600
```

Source archive SHA256:

```text
8685c004e6096dad56b00f7313014af70a0f1c7d991930d9bc91906cefc042f8
```

Path runtime digest:

```text
6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f
```

Actual version output:

```text
allspark 0.10.1-beta.38 (fork build fork.009; upstream prime-agent 0.10.1-beta.38)
```

Полные URLs и hashes находятся в `repo/.ai/versions.json` и
`repo/docs/agent-stack/SOURCES.md`.

## 3. Source review, не live model acceptance

По pinned fork.009 source проверены:

- официальный launcher меняет HOME и сохраняет upstream wire names;
- CLI поддерживает `--model VALUE`; README-форма `-m` этой сборкой не поддерживается;
- native `rlm.spawn` наследует cwd; `rlm.create_session` имеет другой lifecycle;
- JSON print может завершиться exit 0 при terminal model error;
- `toolProfile` ограничивает tool roster, но не является OS read-only guard;
- полного GSD Path host/phase adapter в release и исследованном main не найдено;
- runtime требует локальный source sidecar и не скачивает отсутствующий runtime из package index;
- self-update содержит upstream installer paths; wrapper CLI guard не блокирует все внутренние TUI pathways;
- LSP table/settings и Jev defaults расходятся с отдельными утверждениями README;
- shared graph database использует имя последнего компонента project path: worktree identity/freshness требуют acceptance перед включением.

DeepWiki использован дополнительно. Его ответ не назвал точный indexed SHA
и смешал текущий release workflow с фактическим fork.009 asset. Поэтому он
не является источником pins, состава tar или проверки установленного binary.

## 4. История предыдущего Prime starter

Предыдущая версия отдельно проверяла Prime 0.10.1, repeat/fresh-clone Path
restore, conflict handling, native hooks и PDD installation. **Эти проверки
не переименованы в Allspark tests.** В таблице выше перечислены реально
повторённые/новые проверки адаптации. Неизменившиеся Path/PDD версии остаются
закреплены прежними integrity hashes.

## 5. Что не выполнено

- Login в ваш provider, проверка доступной вам модели, платные LLM requests.
- Полный Allspark phase adapter для Inspect/Research/Plan/Build/Review/QA/Finalize.
- Реальные model calls, Build/Review/PDD acceptance на Law-Nexus.
- Перенос `.gsd` backlog, изменение Law-Nexus harness/CI, migration/cutover.
- Проверка Python 3.13+/Rust toolchain и полного test suite Law-Nexus.
- Live LSP server startup; проверка графа на нескольких worktrees; Jev judge.
- Native Windows/macOS/arm64. Для них bootstrap не предлагает готовый asset.
- Полностью hermetic lock transitive Python/npm dependencies.
- Legal adoption, закрытие M210/F13 и любые несуществующие owner approvals.

Результат пакета — проверенные установочные компоненты и конкретный runbook.
Operational readiness требует полного phase adapter acceptance, пилота на
выбранной модели и критериев C7 в `MIGRATION.md`.
