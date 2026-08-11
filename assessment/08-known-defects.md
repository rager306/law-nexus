# Known-defect register DOC-01..DOC-10

**Статус:** `[proposed]` D0 / EA-00 defect baseline
**Базовая ревизия:** `60fd8245ace999f3f29911844375dd7cc36a2a38` (2026-08-11)
**Правило:** `addressed-in-draft` не означает `verified-closed`; closure требует phase exit evidence и disposition

| ID | Defect | Severity | Owner phase | D0 state | Closure evidence required |
|----|--------|----------|-------------|----------|---------------------------|
| DOC-01 | `prd/ARCHITECTURE.md` ссылается на отсутствующие `prd/01_general_idea.md` и `prd/02_architecture.md` | P0 | D1 / EA-01 | verified-closed | frozen EA-07/EA-09 tracked-link scans found zero missing living targets; EA-10 `accepted-with-findings` at packet `120d44b`; publication-integrity scope only |
| DOC-02 | README/ARCHITECTURE публикуют `.gsd/*.md` как cold-reader surfaces, хотя `.gsd` local/ignored | P0 | D1 / EA-01 | verified-closed | frozen EA-09 confirms no local-only sole authority/proof dependency; `.gsd` remains explicit workflow/non-authority; EA-10 process disposition only |
| DOC-03 | Нет современного tracked Product Contract | P0 | D2 / EA-02 | verified-closed | tracked Product/requirements at `37f82c4`; EA-02 readiness PASS in `assessment/02-product-contract.md`; closure is document-publication scope only, not product validation |
| DOC-04 | `prd/project-state/roadmap.md` сообщает устаревший M160/M161 front | P0 | D5 / EA-05 | verified-closed | frozen `roadmap-front-sync=PASS` at `94d58ea`; user `ACCEPT-WITH-FINDINGS`; `assessment/05-roadmap-readiness.md` |
| DOC-05 | Derived registry/readiness содержит active-looking FalkorDB/ACP rows и stale anchors | P1 | D7 / EA-06 | verified-closed | `assessment/06-derived-registry-quarantine.md`: quarantine PASS at baseline `bfe2ee6`; obsolete/era rows blocked or superseded, authority edges demoted, IDs preserved; unresolved historical anchors remain an explicit non-authoritative staleness WARN |
| DOC-06 | Temporal readiness покрыт в основном `GATE-G005`, без полного набора CTV/applicability/correction/case gates | P1 | D6 / EA-05 | verified-closed | frozen `temporal-readiness-coverage=PASS` at `94d58ea`; user `ACCEPT-WITH-FINDINGS`; single tracked matrix remains `prd/temporal-legal-model.md` §10–10.1 |
| DOC-07 | Cross-surface matrix не моделирует Product Contract и external assessment authority | P1 | D2 + D6 / EA-02 + EA-05 | addressed-in-draft | A3/A4 and assessment edges are defined in Product/requirements/authority-map drafts; cross-matrix update and frozen edge review remain open |
| DOC-08 | Нет формального разделения deterministic checks, LLM review и human acceptance | P1 | D8 / EA-08 | verified-closed | EA-07 paper method, EA-08 advisory reviews, human D149 remediation disposition, independent EA-09 and human EA-10 D150 were applied separately; process scope only |
| DOC-09 | Нет event-triggered freshness policy для living documents | P2 | D8 / EA-08 | addressed-in-draft | draft basis: control plan §10; closure: trigger catalog adopted, sampled change maps to required refresh/review |
| DOC-10 | Нет revision-bound external assessment packet | P1 | D0 + EA-00..EA-10 | verified-closed | packet frozen through EA-09 report `120d44b`; independent assessment in `assessment/11-independent-external-assessment.md`; explicit human EA-10 D150 in `assessment/12-final-disposition.md` |

## D0 observations

- `assessment/` зафиксирован как tracked packet root.
- Charter и authority map созданы как `[proposed]` process artifacts.
- `addressed-in-draft` для DOC-01/DOC-02/DOC-07/DOC-08/DOC-09/DOC-10 означает только working-tree correction или наличие paper design/baseline artifacts, не выполнение owning phase exit и не closure.
- DOC-01..DOC-06, DOC-08 and DOC-10 `verified-closed` are documentation/process closures only; DOC-05 retains a visible derived-staleness WARN and none validates product/runtime/legal readiness.
- DOC-03 `verified-closed` ограничен публикацией и EA-02 document readiness; это не EA-10 acceptance, product validation или validation локальных GSD requirements.
- Независимый assessor и acceptance authority не назначены этим документом.
- На исходном D0 ни один defect не был `verified-closed`; последующие состояния требуют отдельного frozen evidence record.
- Paper-only controls не выдаются за implemented CI/governor gates.

## Disposition protocol

Для изменения состояния defect обязательны:

1. exact frozen revision;
2. owning phase exit checklist;
3. tracked evidence refs;
4. reviewer finding либо deterministic result;
5. acceptance authority disposition;
6. preserved non-claims.

Допустимые состояния register: `open`, `addressed-in-draft`, `verified-closed`, `accepted-exception`, `superseded`. `accepted-exception` требует rationale, owner и revisit trigger.
