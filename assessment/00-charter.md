# Charter внешней оценки архитектуры и продуктовой документации

**Статус:** `[proposed]` assessment charter
**Assessment root:** `assessment/`
**Базовая ревизия:** `60fd8245ace999f3f29911844375dd7cc36a2a38` (2026-08-11)
**Текущая стадия:** EA-10 complete — human disposition D150 `accepted-with-findings` for the documentation/process packet frozen through independent EA-09 report `120d44b`. Findings remain visible; no product/legal/runtime acceptance or lifecycle promotion. EA-00 charter remains the scope contract.
**Execution contract:** `prd/architecture/documentation-semantic-control-plan.md`
**Assessment contract:** `prd/migration/external-architecture-assessment-roadmap.md`

## 1. Цель

Независимо проверить, что опубликованный ADR/PRD/process-корпус:

- воспроизводим из tracked revision без локальной `.gsd`, ignored-кэшей и archive vaults;
- сохраняет явную границу canonical / planning / local / derived / archive;
- не повышает D098 lifecycle сильнее governing ADR и доступного proof class;
- содержит typed traceability для consequential product и architecture claims;
- честно фиксирует отсутствие executable applicability kernel;
- пригоден как контракт для последующего Rust TDD, не утверждая готовность runtime.

## 2. Scope

### В scope

- `prd/ARCHITECTURE.md`;
- `doc/adr/**` и `doc/adr-architecture-cross-matrix.md`;
- tracked `prd/PRODUCT.md` (`[proposed]`, EA-02 `ready-for-assessment`);
- tracked `prd/REQUIREMENTS.md` projection (`[proposed]`, not requirement-validation proof);
- active migration/project-state roadmaps;
- documentation semantic-control catalog;
- temporal/applicability crosswalk;
- derived-registry authority boundary;
- assessment evidence и human disposition в `assessment/`.

### Вне scope

- изменения Rust product runtime и Python repository harness;
- юридическая оценка применимости норм;
- parser, retrieval, RuVector, citation и release validation;
- принятие CALM, ISO draft или community ADR tooling как project canon;
- восстановление ACP/git-lex, FalkorDB, PyO3/FFI или архивных PRD на active plane;
- Litho/deepwiki-rs output как assessment evidence или authority.

## 3. Authority и source access

Assessor получает frozen tracked revision и читает authority в следующем порядке:

1. `prd/ARCHITECTURE.md` — living architecture truth oracle;
2. `doc/adr/**` — каноническое decision substance и lifecycle ceilings;
3. `prd/PRODUCT.md` — `[proposed]` Product Contract с EA-02 document state `ready-for-assessment`; не EA-10 accepted;
4. `prd/REQUIREMENTS.md` — tracked `[proposed]` capability obligations; не requirement-validation proof и не замена governing ADR;
5. active roadmaps — sequence/planning authority only;
6. matrices, controls и `assessment/**` — process evidence;
7. `prd/architecture/**`, generated/LLM reports — derived diagnostic input only.

`.gsd/**`, `.litho/**`, `litho.docs/**`, raw provider payloads, ignored local files и `.gsd/exec/**` не являются published evidence. Archive/vault материалы допускаются только как явно квалифицированный historical context.

## 4. Разделение ролей

| Роль | Ответственность | Запрет |
|------|-----------------|--------|
| Author | готовит correction artifacts и evidence map | не принимает собственное lifecycle promotion единолично |
| Semantic reviewer | проверяет смысл, non-claims и противоречия с exact citations | не является acceptance authority по умолчанию |
| Independent assessor | перепроверяет frozen packet, gates и sample chains | не редактирует canonical документы в ходе оценки |
| Acceptance authority | принимает итоговый disposition и exceptions | не выводит acceptance только из all-green tools |

Минимальная независимость: independent assessor не является единственным автором оцениваемого consequential документа.

### EA-09 independence and source-access declaration

| Поле | EA-09 состояние |
|------|-----------------|
| Independent assessor | two non-authoring model-assisted desk reviewers at frozen revision `d96a903` |
| Independence statement | reviewers did not author or edit the assessed packet and hold no lifecycle, release or acceptance authority |
| Conflict-of-interest declaration | no ownership of product runtime claims, legal interpretation, requirement closure or EA-10 disposition |
| Source-access declaration | tracked repository tree and read-only deterministic controls only; no private legal corpus, secrets, raw provider payloads or archive content as authority |
| Acceptance authority | human project owner; D150 `accepted-with-findings` recorded in `assessment/12-final-disposition.md` |

Detailed assessor declarations and limitations are recorded in `assessment/11-independent-external-assessment.md`; human acceptance is recorded separately in `assessment/12-final-disposition.md`. Assessor evidence did not auto-accept the packet.

## 5. Finding classes и severity

| Class | Смысл | Может блокировать |
|-------|-------|------------------|
| `PASS` | критерий доказан в заявленном документальном scope | нет |
| `WARN` | ограниченный долг с owner, remediation и revisit trigger | только если становится sole authority/proof dependency |
| `BLOCK` | deterministic или human-confirmed нарушение acceptance contract | да |
| `ADVISORY` | LLM/reviewer candidate с exact citation | нет, пока не подтверждён deterministic evidence или human disposition |

Numeric scores и model confidence не являются proof и не меняют lifecycle.

## 6. Freeze и invalidation

Для EA-09 packet freeze должен зафиксировать:

- exact Git SHA;
- assessment date;
- tracked inventory и excluded sources;
- tool/model versions без secrets;
- deterministic paper-rehearsal results;
- semantic findings с exact source spans;
- known defects и dispositions.

Изменение frozen SHA инвалидирует prior acceptance для materially changed chains. Чисто editorial diff может быть принят acceptance authority как non-material только с записанным rationale.

## 7. Entry gates

EA-09 не начинается, пока:

- `published-link-integrity` не имеет `PASS`;
- нет local-only sole authority/proof dependencies;
- Product Contract не имеет состояния `ready-for-assessment`;
- roadmap fronts не синхронизированы;
- derived registry не помещён в quarantine;
- paper rehearsal не содержит `BLOCK`;
- каждый `WARN` имеет owner/remediation/revisit trigger;
- каждый consequential LLM finding получил human disposition.

## 8. Допустимые итоговые dispositions

- `accepted-for-process`;
- `accepted-with-findings`;
- `rejected-needs-remediation`;
- `superseded-by-new-assessment`.

Запрещены `product-validated`, `legal-correctness-validated` и любые эквивалентные claims из documentation-only review.

## 9. Non-claims

- Этот charter не закрывает DOC-01..DOC-10 автоматически.
- Он не назначает конкретного assessor и не имитирует независимую оценку.
- Базовая ревизия — planning baseline, а не SHA принятого assessment packet.
- D0 / EA-00 фиксирует процесс; D1–D8 and EA-01–EA-10 now have revision-bound evidence and D150 `accepted-with-findings`; retained findings remain open under their recorded triggers.
