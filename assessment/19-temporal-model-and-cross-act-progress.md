# Assessment 19 — прогресс темпоральной модели НПА и связей с другими актами

**Дата:** 2026-08-26  
**HEAD на момент обзора:** `1829749` (`main`, dirty 0, ahead origin 92; **не push**)  
**GSD:** idle; Last Completed = `M183-t5u1dg`; Active Milestone = None; Queue empty  
**Lifecycle:** `[bounded]` repository-document/process assessment  
**Роль:** non-authoritative disposition и карта долга. Не закрывает TSG, не промоутит ADR, не исполняет golden corpus, не является product/legal proof.

**Источники (living oracles, не память):**
`prd/ARCHITECTURE.md`, `prd/architecture/capability-promotion-board.md`,
`prd/architecture/temporal-semantic-gap-register.md`,
`prd/architecture/golden-corpus-catalog.yaml`, `prd/architecture/kb-ontology.yaml`,
`prd/temporal-legal-model.md` §3/§11, `doc/adr/0016`..`0023`/`0019`,
`crates/ln-kb-ontology/src/domain.rs` (`try_cross_act_edge`),
`crates/ln-kb-ontology/tests/real_cross_act_edges.rs`,
`.gsd/continue.md`, `.gsd/STATE.md`.

**Заказ на включение в работу (2026-08-26):** закрыть накопленный процессный/honesty-долг и разрывы последовательностей *до* исполнения G1–G3 и *до* P2 resolver. Не хардкодить настройки в код; не чеканить Rust-типы под `[proposed]` словари (D216); не сглаживать `[bounded]`/`[smoke]` в `[validated]` (D098).

## 1. Где остановились

Последняя волна M175–M183 — **design-only honesty**, не runtime. M183 посадил каталог 40 кейсов G0–G3 + advisory `golden-corpus-catalog`. Кейсы **не исполняются**. GSD completion ≠ product readiness.

Следующий *продуктовый* шаг остаётся human-gated: исполнить G1–G3, затем развилка G2 corpus vs P2 resolver. Этот шаг **заблокирован** процессным долгом ниже: `roadmap.json` врёт `M183 active`, TSG-015 говорит «18 paper cases» при 40 GC + 19 TL-GC, 484-ФЗ acquired без ребра, leftover в continue.md исторический.

Честный первый milestone после idle — **honesty/process**, не G1-театр и не ConflictResolver.

## 2. Темпоральная модель акта (L1–L7)

Лестница: `S0 → S1 → S2 → S3 bounded_runtime → S4 representative → S5 human → S6 closed`. **Ни один TSG не на S6.** `S_ready_bounded` ≠ S6 ≠ O3.

| Слой | ADR / TSG | Сделано | Доказательства | Не сделано — почему | Разрыв (2–5 шагов) |
|---|---|---|---|---|---|
| L1 identity WEMI | ADR-0016 `[proposed]`; TSG-013 **S3** | FRBR-носители YAML; `mint_work` / `compare_work_identities`; CC-path; `document_groups` + `parsed_as`; opaque WorkId overlay | write-set `ln-kb-ontology`; 44-ФЗ 8 glava + 94 statya; PP_60 punkt mint | Dual-formulation кристалла (D216 number+date+authority **и** opaque WorkId) не сведён в runtime-тип. WALK-I от `edition-0001_rev-initial_from-unknown` не доказан как C0 | Не чеканить WorkId. Identity растёт от earliest oracle, не от registry 0118 |
| L2 CTV / assembly | ADR-0017 `[proposed]`; TSG-003/013/017 **S3** | Assembly FSM 12/12 → `S_ready_bounded`; membership/presence fold; `edition_ast_at`; oracle drift=0; replay 0080→0081 (+24/−57); `resolve_ctv` 85/94; PP_60 `ctv_resolved>0` при `membership_committed=0` | 402-ФЗ pipeline; 44-ФЗ edition-0118; CLI inspect/replay | TextChange ≠ NormativeEffect только taxonomy (TSG-002 **S1**). Нет compiler fold over accepted assertions. Replay = marker diff, не законодательная история | G0 Shape → G2 hostile split/merge (GC-015..020) → только потом P2 CTV resolver |
| L2 clocks | ADR-0009 `[bounded]` safety; TSG-011 **S0–S1** | 5 часов safety; ISO day → YAML ordinal; impossible dates fail-closed | `ln-temporal`; KBO-R031; FSM `O2_calendar_ordinal` | Нет interval/bitemporal algebra; нет correction ledger | Календарь ≠ InForce. TSG-011 после стабильного CST |
| L3 NormativeState | ADR-0018 `[proposed]`; TSG-004 **S3** | `resolve_force_status_at`; `join_force_with_membership`; Unknown при дыре | hostile joins; KBO-R012 | Нет публичного ортогонального resolver text/status/applicability. Membership ≠ InForce | Не строить Applicable на force |
| L4 hierarchy / conflict | ADR-0019 `[proposed]`; TSG-007 **S0** | Design: NormativeRank + maxims. Partial: `try_cross_act_edge` | ADR; constructor tests | **ConflictResolver нет.** `conflicts_with` в YAML не решается | Typed ranks → maxim evidence → hostile delegation → corpus. Industry priority ≠ rank bump |
| L5 practice | ADR-0020; TSG-008 **S0** | non-claim: practice ≠ AST | board: `court_practice` probe-only | Нет PracticeEvidence port | Не начинать: практика как InForce снесёт kernel |
| L6–L7 + Applicable | ADR-0021/22/23; TSG-006/009/010 **S0–S2** | `ln-applicability` v0 abstention-only | fail-closed Abstain | Нет Applicable product claim | Запрещённый прыжок Satisfied → Applicable. GC-035..040 требуют runtime, которого нет |
| G0 design overlay | review-25/26; M175–M182 | P0 E.1; P1 E.2.1–E.2.7 YAML; P0-1..P0-8 + §3/§4/§7 design-only | D222 pins; crystal v2; governor 67/0 | P1-8 full semantic governor §11 не начат | Design-only ≠ bounded. Чеканка enum = D216 |

## 3. Связи с другими актами

YAML `cross_act_edge_kinds`: `amends | implements | specifies | conflicts_with | cites | refers_to`.  
`refers_to` — надсемейство над `cites`. `amends` вне reference family. Binding semantics design-only. **Rust enum нет.**

| Связь | Сделано | Доказательства | Не сделано — почему | Разрыв на 2–5 шагов |
|---|---|---|---|---|
| Конструктор ребра | `try_cross_act_edge`: YAML kind, reject self/unknown/empty provenance | `cross_act_edges.rs`; authority ≠ edge kind | Не граф, не store, не ConflictResolver | Не класть рёбра в RuVector (ADR-0014 `[proposed]`) |
| C1 amends | 138-ФЗ → 44-ФЗ ст. 31/43; 333-ФЗ → ст. 95; **484-ФЗ → 44-ФЗ ст. 93 constructor-proof executed @SHA 67f781db… [bounded]** (M186-b55iey S03: три hop'а — parser SHA+hlink, constructor, empty timeline Unknown) | `real_cross_act_edges.rs` (138/333 без регрессии); `c1_484_evidence_battery.rs` 5 passed; pin `prd/architecture/c1-484-fz-provenance.yaml` `executed_edge` | 118-edition verify по-прежнему нет; R070 edition-delta provenance открыт; skip parser-hop без `consru_export` = SKIP, не pass | Leftover: Class A 25 CID-A / G1 blocked / R070. Не называть 3+1 ребро корпусом или «cross-act системой» |
| Parser → candidate | Consultant hyperlink → class → candidate; 435-ФЗ 119 markers G1 | `ln-consultant-parser`; ADR-0025/0027 `[bounded]` | Не legal resolution. `consru_export` 6→1025 amends = gitignored `[smoke]` | G1 official (GC-021/022) требует tracked official artifacts. Smoke-числа не в ADR |
| ReferenceMention / Binding | YAML vocabulary; pin tests; GC-026..034 catalogued | `reference_binding.rs`; amends ∉ reference family | TSG-012 **active**. Нет typed resolver. Unclassified не runtime | Mention → Binding → Semantics против folded CST, не raw XML. Latest text ≠ authority |
| Replay как «поправки» | MarkerDiff 0080→0081 | CLI replay; drift=0 | Diff ≠ `AmendmentEvent`. Нет привязки removed CC → amending act → commencement | R070: edition без evidence-backed provenance остаётся Unknown |
| Identity цели ребра | Fixture CC `cc:138-fz:statya-1` → `cc:44-fz:statya-31` | Тесты | WALK-I не вырастил CC от earliest oracle. 0118 ≠ вселенная CC | Не хардкодить `statya`. Out-of-corpus (GC-026) = Unclassified |
| Сила цели | non-claim: binding survives Repealed; cites ≠ authority | YAML non_claims | Runtime не проверяет | Join force×edge без fail-closed даст ложный InForce |

## 4. Каталог G0–G3 (M183) — карта долга, не исполнение

40 кейсов, все `design-only`. Tiers: G0=20 / G1=2 / G2=12 / G3=6. Groups: 8/6/6/5/9/6. TL-GC01–19 остаются paper-oracles: 8 `covered-by`, 11 `remains-TL-only`.

| Что каталог даёт | Чего не даёт |
|---|---|
| Именованный leftover review-26 §10 | Исполнение, legal gold, Rust enum, OntologyCatalog input |
| G1 = 2 official-source кейса (GC-021/022) | Official corpus на диске как promotion evidence |
| G2 = hostile refs/identity | Runtime, который мог бы их прогнать |
| G3 = 6 procurement traces | Applicable protocol (намеренно deferred) |

Три омонима «G0» нельзя схлопывать: parser ladder / ADR dispositions G0(a–g) / catalog Shape.

**Дрейф TSG-015:** gap-register всё ещё пишет «18 paper cases». Живое: 19 TL-GC + 40 GC catalog. Это процессный разрыв, не продукт.

## 5. Процессные разрывы, которые блокируют честную следующую волну

| ID | Разрыв | Почему блокирует | Честный фикс |
|---|---|---|---|
| P-01 | `roadmap.json` `current_milestone.status=active` на закрытом M183 (`generated_at` 2026-08-25) | Governor `roadmap-current-tracks-gsd` / range-coverage красный после closeout (MEM932) | Bump id/status=complete, notes[], `generated_at`; зеркало `roadmap.md` |
| P-02 | TSG-015 «18 paper cases» vs 40 GC + 19 TL-GC | Холодный читатель думает, что каталог не сел | Honesty-правка register + companion (MEM940) |
| P-03 | Assessment 19 не существовал | Review жил только в чате | Этот файл |
| P-04 | 484-ФЗ «acquired; edge not executed» не в DESIGN FRONT leftover | Следующий агент начнёт G1 и забудет C1-хвост | Честный leftover на living surfaces без раздувания ARCHITECTURE за 325 строк. **Закрыт leftover-формулировкой M186-b55iey S03** (2026-08-28): executed @SHA 67f781db… [bounded], honesty sync пяти плоскостей (pin `executed_edge`, эта строка, roadmap.md, roadmap.json note, CHANGELOG M186); R070 остаётся открытым |
| P-05 | GitNexus reindex после closeout-коммитов не сделан (MEM1135); owned by M186 S04 T03 / reindex after S04 tracked commit | Impact/detect_changes на stale index | `node .gitnexus/run.cjs analyze --force --name law-nexus` после tracked-коммита |
| P-06 | P1-8 full semantic governor §11 | Отдельный leftover review-26, не каталог | Не в этой волне (D272 exercise-not-expand, если нет нового check_id) |
| P-07 | Dual Work identity в кристалле | Сознательный dual-canon (MEM1099) | Не «чистить». Не чеканить тип |

## 6. Что сознательно НЕ делать в ближайшей волне

- Исполнять G1 (GC-021/022) без tracked official artifacts + protocol manifest (нет корпуса → фикстурный театр).
- Чеканить Rust enum `WorkId` / `ReferenceSemantics` / ConflictResolver (D216, ADR-0019 S0).
- Называть replay «законодательной историей» или 3 C1-ребра «cross-act системой».
- Тащить `consru_export` числа в living architecture.
- Applicable, RuVector product, practice-as-force, Python-product, ACP/FalkorDB.
- Push без подтверждения. `/gsd rebuild markdown` (MEM912 hang).
- Хардкод настроек в код; секреты не нужны этой волне (`.env` не трогать).

## 7. Рекомендуемый порядок волн (GSD)

1. **M184 (этот заказ):** honesty/process — assessment/19, MEM932, TSG-015, leftover 484/R070, GitNexus reindex, CHANGELOG. Proof class = docs + governor/pytest.  
2. **Следующая human-gated продуктовая:** G1 official (GC-021/022) *или* 484-ФЗ edge как узкий C1 constructor — не оба и не ConflictResolver.  
3. **Затем:** G2 references (GC-026..034) xor P2 Mention/Binding resolver.  
4. **Затем:** TSG-012 против folded CST.  
5. **Потом:** ADR-0019 ConflictResolver. Applicable ещё позже.

## 8. Governor / review strengthening (session leftover)

- Pin TSG-015 счётчик на живые 19 TL-GC + 40 GC (или явная формула «paper TL-GC vs catalog GC»), чтобы дрейф «18» не вернулся.
- Не заводить новый check_id, если существующий `temporal-vocabulary-contract` / capability-board может нести формулу — D272 exercise-not-expand.
- Verify-поля: только newline-separated shell; не RU/IT проза (gsd-pi#1994 жив на 1.16.2).

## 9. Non-claims

Этот файл не закрывает TSG-001..017, не исполняет GC-001..040, не доказывает R070, не промоутит ADR-0016..0023, не является legal gold и не заменяет `prd/ARCHITECTURE.md`.
