# Рабочий цикл и контракт интеграции

Этот документ дополняет generated root `WORKFLOW.md` GSD Path и инструкции
Law-Nexus. Он не заменяет native phase contracts. Установка описана в
[INSTALL.md](INSTALL.md), особенности fork — в [ALLSPARK_NOTES.md](ALLSPARK_NOTES.md),
migration gates — в [MIGRATION.md](MIGRATION.md).

## 1. Один владелец каждого вида состояния

| Вид | Владелец и поверхность |
|---|---|
| Delivery plan, task dependencies/status, transitions | Path, `.project/` |
| Версия runtime и native helpers | `.gsd-path/runtime.json` и verified cache |
| Описание product behavior | PDD, `product-model/` |
| Архитектурный/нормативный смысл | Law-Nexus architecture, owning ADR, glossary |
| Исполнение одного brief | Fresh Allspark process в назначенном cwd |
| Credentials, chat sessions, kernel | Ignored `.ai/local/` |
| Legacy GSD-Pi | Frozen snapshot и sanitized crosswalk |

Не вести параллельно второй backlog в PDD и не синхронизировать `.gsd`/`.project`.
`sdd.paths` в PDD лишь связывает ссылки. Reference на code/ADR не доказывает
прохождение тестов, принятие правила или наличие human decision.

## 2. Начальный профиль Path

`.ai/path-run.json` — **настройка нашей обёртки**, не native Path config.
Общий `GSD_PATH_WORKTREE_ROOT` вычисляется в shared environment и одинаков
для shell и Allspark HOME. Native Path runtime восстановлен с одним digest
в обоих HOME. Существующий placement receipt не переопределяется env.

Базовый профиль:

```json
{
  "schema": 1,
  "projectDir": ".project",
  "worker": ["scripts/ai/allspark-worker", "-p"],
  "capacity": 1,
  "childTimeoutSeconds": 900,
  "pollSeconds": 5,
  "maxAttempts": 1
}
```

`-p` обязателен: Path передаёт brief в stdin, но не добавляет headless flag.
Launcher превращает worker path в абсолютный путь primary checkout. Cwd
задаёт native dispatcher; worker не переходит обратно в primary repository.

`capacity:1` и `maxAttempts:1` действуют на coder round. Deep review может
иметь отдельные lens reviewers; это не общий предел числа процессов.
Timeout — предел ожидания child, а не token/dollar budget. Для Allspark counters
в существующем Path token ledger пока не доказан native adapter; не включать
его и не обещать hard token cap без отдельной реализации/проверки.

Все процессы первоначально используют одну выбранную модель и общую
авторизацию. Их контексты новые. Общий profile удобен для эксплуатации;
отдельные worktrees не разделяют OS permissions. Промпт reviewer ограничивает
его роль, но не является системным запретом записи.

## 3. Обязательная интеграционная задача до operational cutover

**Название задачи:** Allspark phase dispatch adapter для Path 1.6.2.

В upstream shared `references/dispatch.md` перечислены supported host tools,
но ветки Allspark нет. CLI `dispatch_driver.py --child-command` уже обслуживает
Build/wave Review; этого недостаточно для всех фаз. Нельзя просто поставить
`--codex`, увидеть skills и записать migration completed.

Реализация должна жить как repo-owned glue с собственным контрактом и
проверками, без неподписанных изменений downloaded upstream skills. Возможное
место — `scripts/ai/` и `docs/agent-stack/`; это scope будущего implementation,
не заявление о наличии готового `phase-run` API в starter.

### Входы и процессы

1. Родитель читает текущую route и phase contract из выбранной версии.
2. Каждая required роль получает отдельный Allspark `-p` process с complete
   brief, точным cwd и deterministic logical name из native contract.
3. Brief содержит абсолютные paths role/template/input/output, AGENTS/WORKFLOW,
   read/write boundary, consuming phase, gate и terminal result.
4. Inspect-code, inspect-docs, research dimensions, planner, plan panels,
   final reviewers не объединяются в одну роль/контекст. При ограниченной
   concurrency можно запускать независимые процессы последовательно.
5. Coder получает только Path-owned task worktree. Reviewer пишет разрешённый
   artifact в disposable root; parent проверяет его и переносит штатно.
6. Child не создаёт нового coordinator и не вызывает `rlm.spawn`/factory.

### Выходы, ошибки и recovery

- Сохранять identity logical task, process/session reference, cwd, inputs,
  start/end, timeout, cancellation и actual exit code.
- Использовать native phase validators; наличие файла и stdout `OK` недостаточны.
- Учитывать Path ready/blocked/question/failed outcomes по его contract.
- Нулевой exit code Allspark означает успешное завершение вызова, а не task done.
  Coder `RESULT: T001 ready` означает readiness for Verify/landing.
- При корректном вопросе записывать ответ через native Path channel/helper;
  не подставлять предполагаемое human approval.
- При timeout/error сохранять evidence и native blocked/failed disposition;
  проверить отсутствие оставленного активного child перед повтором.
- Новая owner session восстанавливается из native state/dispatch journals.
  Не читать предыдущий чат как единственный источник статуса.
- Не выдавать Allspark JSON print stream за надёжный exit-code gate без parser:
  исследованный `--mode json -p` может иметь exit 0 при terminal model error.
  Этот starter использует обычный text `-p`.

### Acceptance задачи

| Проверка | Требуемый результат |
|---|---|
| Skill discovery | Внутренние scripts/references доступны из primary и task worktree |
| Cwd | Worker действительно видит назначенный worktree; primary files не стали его working tree |
| Fork HOME | Оба runtime caches разрешают один digest; Git identity/hooks/signing и external worktree root согласованы |
| Role isolation | Два independent brief получают разные fresh contexts |
| Planner/Research | Реальные outputs проходят native gates; не эмуляция status |
| Error/timeout | Неверный результат не превращается в success; child учтён/остановлен |
| Question | Блокирующий вопрос и реальный ответ проходят предусмотренный Path путь |
| Build→Review | Раздельный reviewer проверяет landed scope по контракту |
| Resume | После завершения owner process новая сессия выбирает правильную native route |
| Approval | Ни API, ни wrapper не производят owner approval автоматически |

Сначала тестировать lifecycle на deterministic stub children, затем провести
один real-model pilot. Выполненные component checks перечислены в
`validation/TESTED.md` исходного архива; полную phase acceptance starter
не заявляет. Неподдерживаемая phase — конкретный blocker,
а не разрешение на скрытое inline исполнение.

## 4. Обычный цикл после принятой интеграции

### Начало сессии

Из primary root:

```bash
source scripts/ai/env.sh
python3 scripts/ai/path-run.py status
python3 scripts/ai/path-run.py route
./scripts/ai/allspark
```

В Allspark: `/skill:path status`, затем продолжить по native router. Recovery
имеет приоритет перед новой работой. При metadata/runtime conflict сначала
diagnostic; не инициализировать новый STATE поверх старого.

### Изменение продукта

Сформулировать наблюдаемое изменение и bounded acceptance. Для нового
behavior использовать `/skill:pdd-ideate ...`; для уже существующего scope —
`/skill:pdd-map ...`. Проверить exact proposed delta. Code-derived inference
не получает автоматически статус approved product contract.

После принятия delta сделать её обычной Path model-only task, если workflow
уже active. У Path approval checkpoints ограниченный allowlist: dirty
`product-model/` не следует прятать в `.project` checkpoint или в stage all.
Когда model baseline включается в initial bootstrap PR, это происходит до
native Path binding и отдельно отмечается в migration record.

Запустить structural check:

```bash
python3 scripts/ai/pdd lint --json
```

Ошибки — blocking для model; warnings просмотреть явно. Exit 0 не обещает
отсутствия warnings, semantic gaps или runtime defects.

### План и Build

Path создаёт задачи с dependencies, allowlist, Verify и acceptance. Gate
привязан к конкретной проверенной revision. Уже выданное разрешение повторно
не спрашивается; actual approval нельзя выдумать из общего намерения.

Ниже — интерфейс CLI-моста, а не последовательность для произвольного state:

```bash
python3 scripts/ai/path-run.py gate-plan
python3 scripts/ai/path-run.py lint-round
python3 scripts/ai/path-run.py --dry-run round --wave 1
```

`approve-plan --expected-head <FULL_REVIEWED_SHA>` выполняется только после
действительного plan approval. Wave number берётся из native plan. После
legal build entry:

```bash
python3 scripts/ai/path-run.py round --wave 1
python3 scripts/ai/path-run.py dispatch-status
```

Если было block/question/error, читать typed outcome и native recovery.
Не запускать round бесконечным циклом. `maxAttempts` этого wrapper не является
глобальным разрешением дополнительных попыток других фаз.

### Review и PDD

Native wave review запускается по текущему номеру cycle:

```bash
python3 scripts/ai/path-run.py review --wave 1 --cycle 1
```

Оба числа здесь пример; фактические значения принадлежат Path. PDD-проверку
выполнять отдельным source-reading review context для утверждённого scope:

```text
/skill:pdd-verify report only. Проверь <точный scope> против approved model
и owning ADR. Перечисли alignment, gaps, unverifiable и причины.
Не меняй файлы, не запускай implementation или делегирование.
```

Обычный invocation с orchestration off всё ещё может предложить/выполнить
выбранные fixes; `report only` нужен отдельно. PDD не выполняет продуктовые
build/tests во время анализа. Они входят в actual Path Verify.

PDD report остаётся ответом. Parent/native reviewer отдельно формирует и
валидирует canonical Path review artifact по его template. Не существует
проверенной штатной команды «import-review из PDD stdout»; не дописывать
выдуманные `.project/pdd-status.json` или frontmatter statuses.

### Завершение

После native acceptance использовать дальнейшую route. `path-run.py complete`
делегирует native Build completion; это не publish, merge, Ship или legal
adoption. Полный milestone проходит предусмотренные Path final review/Ship
и проектные quality gates. PR integration проверяется по actual remote state.

## 5. Что особенно сохранить в Law-Nexus

- Rust product и Python repository harness имеют разные роли.
- `prd/ARCHITECTURE.md`, owning ADR и glossary governance сохраняют authority.
- `prd/PRODUCT.md`/REQUIREMENTS с proposed/ready-for-assessment не становятся
  accepted от генерации `product-model/`.
- M210 not-adopted/hold и соответствующие source-bound decisions сохраняются;
  техническая миграция не даёт разрешения на normative IR/promotion.
- Новый workflow-state adapter должен блокировать invalid/missing operational
  Path state. Старый «нет .gsd → PASS/N-A» нельзя просто перенести.
- Source-integrity successor имеет собственный versioned contract. Исторические
  hashes не переписываются для получения зелёного результата.

## 6. Работа после сбоя

1. Зафиксировать actual HEAD, worktree/status и diagnostic, остановить только
   текущий неуспешный writer.
2. В новой Allspark session прочитать native `status`/`route`.
3. Следовать exact recovery action: например `resume-checkpoint`; для других
   journals использовать helpers из selected runtime/skill bundle.
4. Подтвердить отсутствие старого child/дублированного logical task.
5. Возобновить только разрешённый следующий шаг с complete brief.

Не удалять `.project`, не менять STATE вручную и не возвращать Pi автоматически.
Полный rollback описан в MIGRATION.md.

## Первичные источники

- [Path dispatch contract](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/gsd-path/references/dispatch.md).
- [Path Build CLI](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/gsd-path-build/scripts/dispatch_driver.py).
- [Path plan contract](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/gsd-path/PLAN.md).
- [Allspark print runtime](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-cli/src/print_runtime.rs).
- [PDD verify](https://pdd-kit.dev/docs/skill-pdd-verify), [model](https://pdd-kit.dev/docs/product-model), [lint](https://pdd-kit.dev/docs/cli-lint).
- Law file-level evidence и sources находятся в MIGRATION.md.
