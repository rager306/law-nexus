# Supplied spec — external review directive, 2026-10-26

<!-- Source: owner chat message ("двигай" + review), 2026-10-26. Saved verbatim by the
     define session as the supplied-spec artifact for milestone M001. The define
     contract requires noting this path in INTENT.md Summary. -->

**Проект перешёл на следующий этап: bootstrap уже принят в `main`, основные замечания прошлой проверки исправлены. Теперь главный шаг — нативная инициализация Path и первый полный цикл задачи, review и восстановления сессии.**

Есть существенная оговорка: **общий зелёный CI получен сочетанием исправлений кода и перевода M207-проверок в необязательный режим**. Поэтому он подтверждает готовность переносимого набора проверок, но ещё не подтверждает прохождение всех корпусных и milestone gates.

## 1. Что изменилось в Git

Я обновил Git и сравнил текущую основную ветку с предыдущим проверенным `067d1b99`.

| Показатель | Текущее состояние |
|---|---|
| Основная ветка | **`main@54a495cd`** |
| PR #1 | **Merged** |
| Время merge | **25 октября 2026, 21:42 по Бангкоку** |
| Изменения после прошлого review | **9 новых коммитов + merge-коммит** |
| Размер новой дельты | **12 файлов, +668 / −45 строк** |
| Открытые PR на момент проверки | Нет |
| Последний CI на `main` | **4 jobs success, 1 skipped** |
| Мои локальные тесты workflow-state / dispatcher / snapshot | **68 passed**, ранее было 65 |
| Маркер окончательного перехода | **`cutover: false`** |

Это уже важный практический результат: **прежнее препятствие для native bootstrap — отсутствие миграционных изменений в основной удалённой ветке — устранено**.

## 2. Какие замечания теперь снимаю

- **Зависание обработчика SIGTERM — исправлено** (`f8ded730`, non-reentrant lock убран из `InterruptGuard`; проверка с SIGTERM во время чтения `signal_number` завершилась корректно). Finding закрыт.
- **Две оставшиеся Pi-проверки больше не используют архив как текущую истину** (`387a54e`: `check_active_requirement_contradictions`, `check_gsd_residual_debt` → `historical-only` + warning на старых fixtures). «Архив Pi блокирует текущий проект» закрыто.
- **Roadmap получил настоящий источник данных из Path**: workflow adapter передаёт `native_milestone`/`native_phase`, governor сравнивает roadmap milestone с operational native state (совпадение → PASS, расхождение → blocking error, operational без milestone → unverifiable/error). Сравнение по полной идентичности, без вывода порядка из `M###`. Граница: проверяется только ID текущего milestone, не актуальность описаний.
- **Python-пропуски учитываются правильно** (`pytest.skip` + `-rs`; hook tests 6 passed/1 skipped; governor/preflight 264 passed/2 skipped).
- **Исправлена действующая инструкция по M210** (`dd05034`: вариант C granted, F13 `deferred-explicit`, повторного решения владельца не требуется; отдельно — незавершённые implementation и activation).

## 3. Что реально подтверждает зелёный CI

Run `40203533977` на `main`: Python harness ✅, Migration layer ✅ (84 migration tests), Rust + product harness ✅ (Cargo 3265 passed/0 failed/7 ignored; 533 passed/2 skipped Python), Milestone chains ✅ **по новой политике** (S04/S03 `continue-on-error: true` — M207 report-only: `S03_RATE_IMPORTED`, отсутствующий corpus, отсутствующие pinned logs, offline-Cargo ошибки `quick-xml`, ненулевые цепочки — остаются в логе, но не блокируют), Strict corpus integration ⏭ skipped. Числа разных pytest jobs нельзя складывать как уникальное покрытие.

**Расхождение, которое стоит поправить**: комментарий workflow обещает обязательные portable schema/fragment checks, а schema запускается как `uv run python scripts/m207_s04_schemas.py check >/dev/null 2>&1 || true` — подавляет вывод и код ошибки; fragment-count внутри report-only chain. Рекомендация: явно разделить обязательные portable checks и advisory results (`.github/workflows/repository-quality.yml:290-326`).

## 4. Corpus integration: правильная защита добавлена, реальный запуск ещё впереди

Появился `LAW_NEXUS_REQUIRE_CORPUS=1` (отсутствие corpus root → failure с фактическим путём; `85e08e4`). Но job настроен `runs-on: ubuntu-latest` + `if: vars.LAW_NEXUS_CORPUS_AVAILABLE == '1'` при комментарии про self-hosted runner; шага доставки корпуса нет (`.github/workflows/repository-quality.yml:210-249`). Сейчас job пропущен; простое включение переменной запустит его без данных → строгий guard должен упасть. Следующий результат — один успешный strict run на конкретном revision и известном snapshot. В обычном Rust job два corpus-сценария печатают `SKIP` и попадают в passed: **3265 passed не означает, что все корпусные сценарии исполнены**.

## 5. Решение сохранить старый Pi hasher — обоснованное

`e1025e0`: стандартные CI/pre-commit entrypoints старый hasher не требуют; исторические generators/receipts сохраняют семантику hash; новый ручной запуск старых M223 baseline/corpus-run scripts потребует старый helper. **Переписывать старые hashes ради bootstrap не нужно.** Новый corpus run этими producers → отдельный versioned producer/receipt с явным snapshot.

## 6. Небольшая защитная регрессия в native adapter

Optional milestone/phase fields смягчили type-check: отсутствующее поле и поле неправильного типа обрабатываются одинаково. Payload `{"state": {"phase": 123, "milestone": "001-probe"}, "route": {"action": "run-phase", "phase": "build"}}` старый adapter отклонял, новый допускает operational verdict, взяв phase из route (`src/law_nexus_harness/workflow_state.py:610-634`). Воспроизведено на подставленном payload; реальный pinned runtime такого не выдаёт. Доработка: разрешать missing/null у optional, отклонять присутствующее значение неправильного типа.

## 7. Где проект относительно миграции

| Этап | Оценка по Git |
|---|---|
| C2 — bootstrap PR | принят, в `main`; прежние блокеры исправлены |
| C3 — remote baseline | удалённая часть выполнена |
| C4 — native initialize / bind / inspect | в Git подтверждения нет (см. примечание ниже) |
| C5 — backlog и PDD | crosswalk исправлен; шесть legacy obligations `unmapped` |
| C6 — реальная задача, review, resume | прежний worker smoke есть; полный native цикл не подтверждён |
| C7 — окончательный cutover | выключен: `cutover: false` |

В проверенном дереве `main` нет tracked `.project/` и `product-model/`; локальные, неопубликованные действия этой проверкой не видны.

### Что делать следующим

**Следующее основное поручение агенту — C4–C6 на принятом `main`:**

1. Выполнить native Path initialization и binding.
2. Получить настоящий native status и связать его milestone с roadmap.
3. Перенести конкретную оставшуюся validation-работу M225 в новые Path IDs.
4. Согласовать минимальную PDD-модель с уже существующим кодом.
5. Провести одну ограниченную задачу через worker, native validators и отдельный review.
6. Закрыть сессию и доказать корректный resume новой сессией.
7. Сохранить результаты в репозитории, после чего оценивать cutover.

Коррекцию CI policy, настройку corpus job и проверку типов native payload можно оформить отдельным небольшим пакетом.

**Оценка: этап подготовки и доставки bootstrap пройден. Следующая убедительная демонстрация продвижения — завершённая native Path задача с независимым review и восстановлением сессии, после которой можно обоснованно включать C7.**

---

<!-- Session note (2026-10-26): reviewer item C4 is already satisfied LOCALLY — native
     initialize/bind/inspect were executed and committed on gsd-path/M001
     (2c7f5b13 → 1b934188) but are not yet pushed; the reviewer audited origin/main only. -->
