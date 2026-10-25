# GSD Path 1.6.2: установка, launcher и границы интеграции

Этот starter использует штатные Python helpers и неизменённые skills GSD Path. `scripts/ai/path-run.py` только собирает аргументы и запускает их. Path остаётся владельцем `.project`, gates, worktrees и журнала восстановления. Launcher не является полноценным host adapter для Allspark.

## 1. Что устанавливается

В bootstrap предусмотрены отдельные этапы tools, skills и hooks. Перед этапом hooks нужно проверить и архивировать именно старые Pi hooks, относящиеся к прежнему workflow. Не удалять все Git hooks: upstream installer умеет сохранять совместимые чужие hooks в цепочке, и эта цепочка тоже должна быть проверена при миграции.

Ниже — команды upstream, на которые опирается bootstrap. `PATH_PACKAGE` означает абсолютный путь к корню извлечённого и проверенного npm-пакета `@opengsd/gsd-path@1.6.2`; `PROJECT_ROOT` — абсолютный путь к primary checkout. Оба значения относятся к конкретной установке, а не к настройкам пользовательского HOME.

```bash
cd "$PROJECT_ROOT"

python3 -B "$PATH_PACKAGE/scripts/install.py" \
  --codex --local --project "$PROJECT_ROOT" --dry-run

python3 -B "$PATH_PACKAGE/scripts/install.py" \
  --codex --local --project "$PROJECT_ROOT"

# Отдельный этап после проверки прежних hooks:
python3 -B "$PATH_PACKAGE/scripts/install.py" \
  --codex --local --project "$PROJECT_ROOT" --hooks-init
```

`--local` выбирает skill root относительно текущего каталога; `--project` отдельно выбирает место project contracts. Поэтому `cd` существенен. `--codex` в этой схеме устанавливает общий формат Agent Skills в `.agents/skills`; это не декларация поддержки Allspark как host. Параметры заданы явно, wizard и `--yes` не нужны. Python entry point — штатная часть npm-пакета.

При установке сразу с guards upstream также поддерживает `--codex --local --project "$PROJECT_ROOT" --hooks`. Starter разделяет эти операции, чтобы старые Pi hooks можно было проверить отдельно.

Повторная установка и свежий clone идут по другой ветке bootstrap. Если tracked `.gsd-path/runtime.json` уже существует, bootstrap сначала сверяет schema/version/digest с `.ai/versions.json`, выполняет exact `--runtime-restore`, а затем устанавливает только local skills без `--project`. Project contracts при этом сохраняются. `--update` добавляется только при обнаружении установленного pinned Path bundle с его ownership markers; при отсутствующих ignored skills он не применяется. Чужие или неполные одноимённые skills, неизвестная версия и несовпадающий digest требуют review и не перезаписываются автоматически.

| Файл или каталог | Происхождение и хранение |
|---|---|
| `.agents/skills/path`, `.agents/skills/gsd-path-*` | 16 установленных skills. В Law-Nexus каталог игнорируется; восстанавливается bootstrap из pinned package. |
| `.agents/disabled-gsd-skills*` | Upstream backups прежних owned skills при повторной установке; тоже исключить из Git. Локальные изменения остаются в backup и не переносятся автоматически. |
| `AGENTS.md` | Installer добавляет управляемый Path block и сохраняет owner text. Результат нужно прочитать, убрать конфликтующие активные Pi-инструкции и включить в bootstrap PR. |
| `WORKFLOW.md` | Управляемый контракт Path; также включить в bootstrap PR. Коллизия с чужим файлом может потребовать явного решения до установки. |
| `.gsd-path/runtime.json` | Декларация версии и digest; хранить в Git. |
| `.gsd-path/status_runtime.py` | Stable launcher; хранить в Git. |
| `.gsd-path/git_guard.py`, `.gsd-path/guard_hook.py` | Stable launchers этапа hooks; хранить в Git. |
| `.codex/hooks.json` | Создаётся выбранным `--codex` на этапе hooks. Allspark этот файл не исполняет. Не считать его Allspark pre-tool guard. |
| Git `pre-commit`, `commit-msg`, `pre-push` | Устанавливаются в hooks directory Git, не попадают в обычный commit. Их нужно восстановить в каждом clone. |
| `<normal HOME>/.gsd-path/runtimes/<digest>` | Проверяемый exact runtime для shell/native helpers. |
| `.ai/local/allspark-home/.gsd-path/runtimes/<digest>` | Вторая exact копия того же runtime для Allspark HOME; не symlink. |
| `<parent>/<repo-name>-path-worktrees/` | Общий внешний root task/reviewer worktrees, заданный starter. |

Для проверенного npm-пакета 1.6.2 installer создал такую декларацию:

```json
{
  "schema": "gsd-path/runtime/v1",
  "version": "1.6.2",
  "digest": "6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f"
}
```

Декларацию создаёт installer. Не писать её вручную вместо установки и не исправлять digest при несовпадении. Starter сверяет её с `runtimeDigest` из `.ai/versions.json`.

Path 1.6.2 не предоставляет runtime-cache override: native store определяется HOME и отвергает symlink storage. Официальный Allspark launcher меняет HOME на `.ai/local/allspark-home`, поэтому bootstrap восстанавливает тот же version/digest отдельно в normal HOME и isolated HOME. Это две cache copies одного выбранного runtime, не два workflow state. Не заменять одну копию симлинком.

`GSD_PATH_WORKTREE_ROOT` поддерживается для worktrees; путь внутри primary repository или другого worktree того же Git repository запрещён. Shared environment starter задаёт абсолютный внешний sibling `<parent>/<repo-name>-path-worktrees`. Shell, owner и worker получают одинаковое значение. Existing Path placement receipt имеет силу: его placement проверяется, а не перезаписывается новым env. `source scripts/ai/env.sh` настраивает общие tools/worktree variables и оставляет HOME shell без изменения. Конфигурация и декларация — в Git; caches, secrets, sessions и рабочие worktrees — нет.

Новый key для placement в `.ai/path-run.json` не вводится. Если нужен иной
внешний root, задать native environment **до первого allocation**:

```bash
export GSD_PATH_WORKTREE_ROOT=/ABS/EXTERNAL/law-nexus-path-worktrees
source scripts/ai/env.sh
```

Это пример: заменить `/ABS/EXTERNAL` реальным абсолютным путём без literal `~`.
Если receipt уже существует и явный override ему противоречит, wrapper
останавливается; изменение env не является миграцией worktrees. Без явного
override существующее placement сохраняется. Repo-level policy по умолчанию
остаётся переносимой: один sibling каталог рядом с primary checkout.


## 2. Bootstrap PR до первого milestone

В мигрируемом Law-Nexus сначала заморозить Pi и подготовить отдельный bootstrap PR: starter, согласованные AGENTS/WORKFLOW, декларацию и launchers Path, правила ignore и решение по прежним hooks. Merge должен попасть в origin/default. Затем primary checkout переключается на чистый обновлённый default branch.

При отсутствии Path STATE native Git guards допускают обычный bootstrap commit и push по bootstrap contract. Проверить фактическую effective hook chain в normal и Allspark окружении; результат предыдущей установки не заменяет эту проверку. Для репозитория с уже существующим `.project/STATE.md` действует его текущий контракт.

Перед первым initialize обновить remote refs и локальный указатель default branch:

```bash
git fetch origin
git remote set-head origin --auto
```

Первое binding требует `HEAD` на точном fetched SHA `origin/<default_branch>`. Локальный bootstrap commit, ещё не попавший в origin/default, этому условию не соответствует.

## 3. Первая сессия и native initialization

Allspark читает установленный skill как `/skill:path`; read-only вариант — `/skill:path status`. Существующий owned STATE сначала проходит native validation. Отсутствие STATE запускает `detect_project.py initialize`, а не ручное создание Markdown.

До native initialization `path-run.py runtime` уже может успешно проверить установку, а `path-run.py status` штатно возвращает ошибку об отсутствующем `.project`. Doctor должен различать «runtime установлен; pipeline ещё не инициализирован» и неисправную установку. Если `.project` существует без owned STATE, нужен `detect_project.py classify`: orphan artifacts нельзя автоматически считать пустым проектом.

Инициализация, которую выполняет router, использует следующий штатный helper:

```bash
PATH_RUNTIME="$(python3 -B "$PROJECT_ROOT/.gsd-path/status_runtime.py" \
  --repo "$PROJECT_ROOT" --runtime-path)"

python3 -B "$PATH_RUNTIME/detect_project.py" initialize \
  --repo "$PROJECT_ROOT" \
  --template "$PROJECT_ROOT/.agents/skills/path/templates/state.md" \
  --require-git
```

Продолжать можно только по JSON verdict/route: brownfield обычно означает `inspect/active`, greenfield — `define/active`; orphan или ошибка блокируют продолжение. Initial STATE оставляют untracked. Не вставлять commit между initialize и bind.

Далее router вызывает `pipeline_git.py bind-initial` с branch из route, recorded default branch и точным fetched base SHA. После успешного bind он выполняет `pipeline_state.py transition` с точными ожидаемыми полями предыдущего route, записывает возвращённую branch и event `router bound initial milestone`, затем снова вызывает route. Один `bind-initial` не завершает эту последовательность. Не заменять её ручным редактированием `STATE.md`.

**Граница Allspark:** parser/skills совместимы, но shared dispatch contract Path 1.6.2 не содержит ветки Allspark. Установка skills и работа native initialization не доказывают, что следующий Inspect/Research/Plan успешно сможет создать требуемые независимые children. На первой неподдерживаемой delegation нужно остановиться и сообщить о недостающем adapter, сохранив состояние. Проверенная ниже CLI-связка покрывает Build и wave Review, не весь router.

## 4. Команды launcher

Запускать копию из primary checkout. Если текущий каталог — task worktree, использовать абсолютный путь `"$PROJECT_ROOT/scripts/ai/path-run.py"`. Launcher сам передаёт primary root helpers; дочерний cwd назначает штатный Path dispatcher.

```bash
python3 -B scripts/ai/path-run.py runtime
python3 -B scripts/ai/path-run.py status
python3 -B scripts/ai/path-run.py validate
python3 -B scripts/ai/path-run.py route
python3 -B scripts/ai/path-run.py dispatch-status
```

Для просмотра собираемой команды без её исполнения ставить `--dry-run` перед subcommand. При `validate` и `resume-checkpoint` dry-run всё равно читает декларацию и проверяет runtime, чтобы разрешить его настоящий путь.

```bash
python3 -B scripts/ai/path-run.py --dry-run round --wave 1
python3 -B scripts/ai/path-run.py --dry-run review --wave 1 --cycle 1
```

После подготовки и штатной проверки плана:

```bash
python3 -B scripts/ai/path-run.py gate-plan
python3 -B scripts/ai/path-run.py lint-round
# Только после явного owner approval именно этого commit:
python3 -B scripts/ai/path-run.py approve-plan --expected-head FULL_REVIEWED_SHA
```

Во время Build команды выбираются по текущим Path receipts и gate results:

```bash
python3 -B scripts/ai/path-run.py round --wave 1
python3 -B scripts/ai/path-run.py dispatch-status
python3 -B scripts/ai/path-run.py review --wave 1 --cycle 1
```

Это не автоматическая последовательность. `round` может dispatch, settle, Verify и land задачи; `review` может создавать reviewer worktree и собирать review artifacts. Следующий вызов определяется native receipt. Повторный Review после исправлений может требовать `--repair-evidence PATH` к штатному receipt. `answer --task-id ID --answer TEXT` записывает реальный ответ оркестратора/владельца на вопрос worker. `complete` проверяет завершение всех waves и review и выполняет переход в Ship; он не означает публикацию или merge в default branch.

При незавершённом approval checkpoint и соответствующем native route:

```bash
python3 -B scripts/ai/path-run.py resume-checkpoint
```

Не использовать recovery как универсальную команду исправления STATE. Непредставленные в launcher операции выполняются по соответствующему upstream skill/helper contract.

## 5. Worker, ограничения и independent roles

`.ai/path-run.json` — конфигурация только этого launcher, не новый формат Path state. В начальном профиле `round` получает capacity 1, max attempts 1, timeout каждого child 900 секунд и polling window 5 секунд. Окончание polling window не завершает работающий child; native driver сохраняет dispatch record. Timeout child — отдельное ограничение. Вопросы `NEEDS-ORCHESTRATOR` имеют отдельную native семантику и не равны обычной failed attempt.

Capacity и max attempts относятся к `round`. `review` не принимает эти аргументы; deep review может создавать два независимых reviewer. Поэтому capacity 1 не является глобальным ограничением всей системы. Token limits не включены: Path 1.6.2 не умеет подтверждать token usage обычного Allspark text output. Не создавать project model policy до реализации проверенного Allspark capabilities adapter. Существующую policy или ledger launcher не удаляет и не обходит — helper может блокировать работу по ним.

Upstream dispatcher принимает `--child-command`, запускает argv без shell, устанавливает child cwd в выделенный worktree и подаёт self-contained brief на stdin. Он не добавляет flags headless-режима. Поэтому в `.ai/path-run.json` задано `"worker": ["scripts/ai/allspark-worker", "-p"]`. Абсолютный worker сохраняет этот cwd и передаёт `-p` в Allspark, который читает stdin и выдаёт plain text. Один и тот же worker получает разные coder/reviewer role briefs. Он не должен сам запускать ещё один workflow loop или произвольно делегировать дальше.

Package manager Allspark умеет искать `.agents/skills` в ancestors текущего checkout, но ignored bundles primary checkout не появляются в другом linked worktree. Поэтому repo launcher передаёт явные абсолютные skill roots вместе с `--no-skills`, сохраняя assigned cwd. PDD reviewer использует pinned bundle primary checkout через этот же механизм. PDD `report only` не пишет Path review artifact: отдельный Path reviewer обязан оформить и проверить его по native schema.

Для стандартных Inspect/Research/Plan нужен отдельный adapter, который сохраняет логические имена, абсолютные входы/выходы, самостоятельные briefs, cwd isolation, timeout/cancellation, сбор результатов и phase gates. Последовательное исполнение независимых fresh CLI workers допустимо лишь как явно спроектированная и проверенная реализация этого adapter; starter её не поставляет. Нельзя молча выполнять роль исследователя или planner в родительском контексте. Upstream quick lane имеет узкое исключение без planner dispatch (`define/done` и `Lane: quick`), но это не общий обход отсутствующего host adapter.

## 6. Восстановление установки

Проверить pinned runtime:

```bash
python3 -B scripts/ai/path-run.py runtime
```

Для полного восстановления обеих cache copies использовать `python3 scripts/ai/bootstrap skills`: этот этап проверяет declaration и exact pins. Если диагностируется конкретный native cache, штатная операция для текущего HOME имеет вид:

```bash
python3 -B "$PATH_PACKAGE/scripts/install.py" \
  --runtime-restore --project "$PROJECT_ROOT" --source-root "$PATH_PACKAGE"
```

Не подменять `runtime.json` новой версией для обхода ошибки. Upgrade runtime — отдельная операция upstream и отдельное review. Не экспортировать Allspark HOME в обычную shell ради обхода cache error: bootstrap выбирает оба окружения сам. После нового clone также восстановить ignored skills и hooks через соответствующие bootstrap stages. Проверить обе копии и общий placement через doctor.

## Проверка starter

Фактически выполненные проверки именно Allspark-комплекта перечислены в
`validation/TESTED.md` исходного архива. Результаты предыдущего Prime starter
не считаются автоматическим доказательством поведения fork launcher.

На целевой машине отдельно проверить normal/isolated HOME cache resolution,
worktree root, Git identity/hooks/signing, fresh child cwd и доступность
полных skills. Затем нужна acceptance всех required phases и real-model pilot.
Ни runtime status, ни dry-run `round` сами по себе не доказывают cutover.

Если installer не видит штатный process identity через `ps`, исправить среду,
а не удалять lock checks. Для повреждённого cache пользоваться exact restore
и native diagnostic; не патчить upstream store и guards.

## Первичные источники

- [Installer и точные CLI flags, v1.6.2](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/install.py)
- [Runtime validation, restore hint и cache path](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/status_runtime.py)
- [Worktree placement и запрет вложенного root](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/worktree_paths.py)
- [Router: initialization, ownership, binding, recovery](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/path/SKILL.md)
- [Shared host dispatch contract](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/path/references/dispatch.md)
- [CLI dispatcher и ограничения round/review](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/dispatch_driver.py)
- [Native plan/approval workflow helpers](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/workflow_run.py)
- [Git commit/push guards](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/git_guard.py)
- [Quick mode как специальный контракт Plan](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/gsd-path-plan/SKILL.md)
