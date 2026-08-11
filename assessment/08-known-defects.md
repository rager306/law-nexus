# Known-defect register DOC-01..DOC-10

**Статус:** `[proposed]` D0 / EA-00 defect baseline
**Базовая ревизия:** `60fd8245ace999f3f29911844375dd7cc36a2a38` (2026-08-11)
**Правило:** `addressed-in-draft` не означает `verified-closed`; closure требует phase exit evidence и disposition

| ID | Defect | Severity | Owner phase | D0 state | Closure evidence required |
|----|--------|----------|-------------|----------|---------------------------|
| DOC-01 | `prd/ARCHITECTURE.md` ссылается на отсутствующие `prd/01_general_idea.md` и `prd/02_architecture.md` | P0 | D1 / EA-01 | addressed-in-draft | working-tree scan: zero residual references in living entrypoints; closure still requires frozen tracked-link scan + disposition |
| DOC-02 | README/ARCHITECTURE публикуют `.gsd/*.md` как cold-reader surfaces, хотя `.gsd` local/ignored | P0 | D1 / EA-01 | addressed-in-draft | `.gsd` now explicitly local/non-authoritative in living entrypoints; closure requires frozen scan proving no local-only sole authority/proof dependency |
| DOC-03 | Нет современного tracked Product Contract | P0 | D2 / EA-02 | addressed-in-draft | `prd/PRODUCT.md` + `prd/REQUIREMENTS.md` drafts exist with PC/RQ traces; closure requires frozen tracked publication, EA-02 checklist and disposition |
| DOC-04 | `prd/project-state/roadmap.md` сообщает устаревший M160/M161 front | P0 | D5 / EA-05 | open | all active roadmap fronts agree at frozen revision |
| DOC-05 | Derived registry/readiness содержит active-looking FalkorDB/ACP rows и stale anchors | P1 | D7 / EA-06 | open | quarantine gate PASS; obsolete rows historical/superseded; missing anchors resolved |
| DOC-06 | Temporal readiness покрыт в основном `GATE-G005`, без полного набора CTV/applicability/correction/case gates | P1 | D6 / EA-05 | open | readiness matrix covers each acknowledged O1–O7/applicability gap with hostile case/non-claim |
| DOC-07 | Cross-surface matrix не моделирует Product Contract и external assessment authority | P1 | D2 + D6 / EA-02 + EA-05 | addressed-in-draft | A3/A4 and assessment edges are defined in Product/requirements/authority-map drafts; cross-matrix update and frozen edge review remain open |
| DOC-08 | Нет формального разделения deterministic checks, LLM review и human acceptance | P1 | D8 / EA-08 | addressed-in-draft | draft basis: control plan §6 C0–C7 + §8 D8; closure: protocol applied to frozen sample, each LLM finding advisory + human disposition |
| DOC-09 | Нет event-triggered freshness policy для living documents | P2 | D8 / EA-08 | addressed-in-draft | draft basis: control plan §10; closure: trigger catalog adopted, sampled change maps to required refresh/review |
| DOC-10 | Нет revision-bound external assessment packet | P1 | D0 + EA-00..EA-10 | addressed-in-draft | `assessment/` complete at frozen SHA; EA-09 report + EA-10 signed disposition |

## D0 observations

- `assessment/` зафиксирован как tracked packet root.
- Charter и authority map созданы как `[proposed]` process artifacts.
- `addressed-in-draft` для DOC-01/DOC-02/DOC-03/DOC-07/DOC-08/DOC-09/DOC-10 означает только working-tree correction или наличие paper design/baseline artifacts, не tracked freeze, не выполнение owning phase exit и не closure.
- Независимый assessor и acceptance authority не назначены этим документом.
- Ни один defect не считается `verified-closed` на D0.
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
