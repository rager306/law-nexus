# Temporal Legal Model Crosswalk

**Status:** `[proposed]` D3 / EA-03 semantic reconciliation; human disposition `ACCEPT-AS-PROPOSED`
**EA-03 tested revision:** `e1ac83a714e20a6b551d5305fc4fca9f29d91aa7` (`assessment/03-temporal-reconciliation.md`)
**Method:** `paper-rehearsal`; documentation/design only
**Authority:** `prd/ARCHITECTURE.md`, ADR-0009, ADR-0016–0022 and ADR-0023 (applicability ownership boundary only)
**Product boundary:** `prd/PRODUCT.md` + `prd/REQUIREMENTS.md`
**Non-authority:** `.gsd/**`, roadmaps, assessment artifacts, derived registry, LLM output, Litho, archive and external frameworks
**Lifecycle ceiling:** five-clock role safety remains `[bounded]`; all ontology layers O1–O7 remain `[proposed]`; ADR-0023 ownership is `[proposed]`, while applicability runtime/product capability remains `[deferred]`

## 1. Purpose and non-claims

This document reconciles terminology, ownership, invariants, hostile cases and graduation gates across the five-clock policy and the O1–O7 temporal legal ontology. It is a crosswalk, not a new oracle and not an ADR.

It does not:

- implement a temporal, CTV, status, applicability, practice, risk or profile runtime;
- promote ADR-0016–0022 above `[proposed]`;
- validate legal dates, legal correctness, case applicability or corpus completeness;
- treat golden cases as authoritative legal conclusions;
- adopt LRMoo, AKML, ELI, LKIF or any external framework as project canon;
- implement or validate the ADR-0023 `NormRule → ApplicabilityPredicate → CaseFacts → ApplicabilityDecision → ExplainableTrace` protocol.

## 2. Namespace and composition

- **A0–A7** are authority levels.
- **C0–C7** are documentation-control levels.
- **O1–O7** are ontology layers ADR-0016–0022; `prd/ARCHITECTURE.md` currently labels the same sequence L1–L7.

Composition order:

```text
ADR-0009 five-clock safety policy
→ O1 ADR-0016 structural legal identity
→ O2 ADR-0017 component temporal versioning
→ O3 ADR-0018 normative status
→ O4 ADR-0019 hierarchy and conflict
→ O5 ADR-0020 practice overlay
→ O6 ADR-0021 transitional provisions and risk
→ O7 ADR-0022 industry profiles
```

Each layer consumes lower-layer evidence. No higher layer may rewrite source evidence, invent a clock, or raise a lower layer's lifecycle.

## 3. Glossary and ownership

| Term | Crosswalk meaning | Primary owner | Vocabulary status | Fail-closed boundary |
|------|-------------------|---------------|-------------------|----------------------|
| Clock | one of five closed, role-bound temporal dimensions | ADR-0009 | canonical `[bounded]` | no silent substitution or sixth core clock |
| Temporal anchor | provenance-bound value or explicit absence for a named clock | ADR-0009 | canonical `[bounded]` | missing → `Unknown`; competing → `Conflict` |
| `factual_event` | when a real-world fact occurred | ADR-0009 | canonical `[bounded]` | not proceeding, publication or legal effect |
| `proceeding` | when a legal proceeding started | ADR-0009 | canonical `[bounded]` | not factual event or legal effect |
| `legal_act_effect` | when a proven act/status event enters the legal order | ADR-0009 | canonical `[bounded]` | not publication, observation, an `InForce` determination or case applicability |
| `source_publication` | when the source document was published | ADR-0009 | canonical `[bounded]` | not system observation or legal effect |
| `system_observation` | when the system observed/ingested evidence | ADR-0009 | canonical `[bounded]` | not publication, force or applicability |
| Event time | not a closed domain term; must be qualified by one of the five clock roles | ADR-0009 crosswalk | qualified-view only | unqualified `event_time` is ambiguous |
| Transaction time | recording dimension; must state whether the fact is source publication or system observation | ADR-0017 §5 + ADR-0009 | qualified-view only `[proposed]` | cannot collapse two ADR-0009 clocks into one source of truth |
| Valid/effective time | legal-order effect anchored to `legal_act_effect` | ADR-0017 + ADR-0009 | qualified-view only `[proposed]` | does not imply case applicability |
| `edition_date` | legacy/provider field with no active canonical temporal semantics | future identity/CTV schema decision | deferred-undefined | must not substitute for Expression identity, CTV event time or legal effect |
| `effective_from` / `effective_to` | interval projections derived from proven CTV/status events, never source facts by themselves | ADR-0017 + ADR-0018 | projection-only `[proposed]` | static fields cannot override event provenance or decide applicability |
| CC | stable Component Concept identity | ADR-0017 | canonical `[proposed]` | not text, force or applicability |
| CTV | semantic component content version derived from events; structural membership/industrial ops spine in `ln-temporal` (RC11-F08) | ADR-0017 | canonical `[proposed]` | not a static interval, force or legal fact from lexical evidence alone; structural spine ≠ full CTV runtime |
| CLV | language realization of a CTV | ADR-0017 | canonical `[proposed]` | not a separate legal status |
| `EvidenceSpan` | future source-bound byte-span evidence contract referenced by readiness prose | ADR-0010 + future evidence schema | deferred-undefined | wording does not assert a current public type, real-corpus coverage or legal truth |
| `SourceBlockRecord` | tracked non-authoritative parser inspection record contract | ADR-0013 + `prd/parser/parser_record_contract.md` | canonical parser-record term `[bounded]` | not an authoritative legal evidence entity, active Rust domain type or proof of a future `SourceBlock` contract |
| `SourceBlock` | future evidence-domain entity named in readiness prose | ADR-0010 + future evidence schema | deferred-undefined | must not be inferred from `SourceBlockRecord` or archive terminology |
| NormativeState | time-indexed normative status (`InForce`, `Suspended`, `Repealed`, `Superseded`, `Transitional`, `Unknown`); force orthogonal to version/applicability/epistemic (RC11-F09 design inventory) | ADR-0018 | canonical `[proposed]` | text presence does not imply `InForce`; InForce ≠ Applicable |
| NormativeStatus | compatibility alias for NormativeState | ADR-0018 | deprecated-alias `[proposed]` | unqualified use must not create a second status dimension |
| Force | informal product term for NormativeState/status at a governing time | ADR-0018 | informal `[proposed]` | force is not applicability or system knowledge |
| Applicability | whether a norm/version governs supplied case facts, producing a typed decision and explainable trace | ADR-0023 ownership `[proposed]`; ADR-0017/0021/0022 prerequisites; runtime `[deferred]` | canonical design term; runtime deferred | executable protocol absent; default is abstention |
| Knowledge | what the system can support from observed evidence and practice coverage | ADR-0009 + ADR-0020 crosswalk | canonical crosswalk `[proposed]` | knowledge of a claim is not the claim's legal state |
| Correction | a new immutable observation/evidence event and rebuilt projection | ADR-0009 + ADR-0017 crosswalk | canonical invariant `[proposed]` | no in-place rewrite or “latest scrape wins” |
| Status transition | evidence-gated change of NormativeState anchored to `legal_act_effect` | ADR-0018 | canonical `[proposed]` | absence of evidence is not a transition |
| Transitional resolution | deterministic design for choosing a version across amendment rules | ADR-0021 | canonical `[proposed]` | no chronology-only default; distinct from risk |
| Practice overlay | non-authoritative, temporally bounded `EffectiveInterpretation` projection | ADR-0020 | canonical `[proposed]` | does not rewrite CTV/status except typed ex-tunc status event |
| Risk | provenance-bearing advisory assessment with explicit unknowns | ADR-0021 | canonical `[proposed]` | not actuarial probability or legal conclusion |
| Profile | versioned adapter supplying industry priority, facts, special norms, practice weighting and risk factors | ADR-0022 | canonical `[proposed]` | cannot mutate kernel evidence, ranks or clocks |
| `TextChangeEvent` | critique vocabulary for a future provenance-backed structural/content change event; no active schema | future ADR-0017 amendment + TSG-002 | deferred-undefined | must not be inferred from lexical amendment wording or collapsed into legal effect |
| `NormativeEffectEvent` | critique vocabulary for a future proven change in legal consequence; no active taxonomy | future ADR-0018/0021 amendment + TSG-002 | deferred-undefined | must not be inferred from text change alone |
| `ComponentMembershipVersion` | critique vocabulary for future parent/position/version membership provenance; no active type | future ADR-0017 amendment + TSG-003 | deferred-undefined | must not be invented from current hierarchy order |
| `NormRule` | critique vocabulary for a future normative-rule intermediate representation; no accepted IR | future ADR under ADR-0023 prerequisites + TSG-005 | deferred-undefined | parser candidates and LLM text cannot become rules |
| `Condition` | possible future NormRule predicate/guard role; no active schema | future NormRule ADR + TSG-005 | deferred-undefined | ordinary prose labelled as a condition is not a domain fact |
| `LegalEffect` | possible future NormRule consequence role; no active schema | future NormRule ADR + TSG-005 | deferred-undefined | not `legal_act_effect`, status or applicability by name similarity |
| `Exception` / `Defeater` | possible future NormRule exception/defeat roles; no active schema | future NormRule ADR + TSG-005 | deferred-undefined | absence or lexical markers cannot establish defeat semantics |
| `ApplicabilitySelector` | critique vocabulary for a future applicability expression/AST; ADR-0023 owns only protocol boundaries | future applicability ADR + TSG-006 | deferred-undefined; runtime `[deferred]` | do not invent AST fields or emit case decisions |
| `LegalList` / `ListEntry` / `ClassifierCode` | critique vocabulary for future versioned legal lists/classifiers | future ADR-0017/0022 amendment + TSG-013 | deferred-undefined | current lists/codes cannot be treated as timeless source truth |
| `ProcurementCase` | critique vocabulary for a future procurement proving-profile case aggregate | future profile/application ADR + TSG-010 | deferred-undefined | not a second ontology core or inferred from a document |
| `ProcurementRegimeResolution` | critique vocabulary for a future traced regime-choice result | future profile/application ADR + TSG-010 | deferred-undefined | no chronology-only or profile-private final decision |
| `PracticeCoverageOutcome` | critique vocabulary for typed coverage states such as no applicable practice versus search/corpus unknown | future ADR-0020 amendment + TSG-008 | deferred-undefined | missing search result cannot imply absence of applicable practice |
| `BitemporalCorrectionLedger` | critique vocabulary for immutable correction/observation history beyond current five-clock safety | future ADR-0009/0017 amendment + TSG-011 | deferred-undefined | no in-place rewrite or latest-observation authority |

These deferred critique terms are stop-signals recovered from the 2026-08-11 independent architecture criticism. Listing them does not adopt their names, fields, ontology, ownership or implementation. A future human-owned ADR may rename, split, reject or define them.

ADR-0018 EA-04 clarification makes `NormativeState` the canonical public term and treats `NormativeStatus` as a deprecated alias for the same dimension. Residual documentation, design, implementation and evidence gaps are inventoried in [`architecture/temporal-semantic-gap-register.md`](architecture/temporal-semantic-gap-register.md); that register is non-authoritative and cannot close or promote any row by itself.

## 4. Five-clock contract

| Clock | Typical consumer | Explicit non-substitution |
|-------|------------------|---------------------------|
| `factual_event` | case facts and limitation-window inputs | not `proceeding` |
| `proceeding` | procedural windows and practice context | not factual occurrence |
| `legal_act_effect` | CTV/status/legal-order transitions | not source publication |
| `source_publication` | source provenance and transaction/publication view | not system observation |
| `system_observation` | evidence acquisition and knowledge history | not legal effect |

Practice has first-class **temporality**, not a sixth clock. Budget cycles and other industry periods are profile projections over the five clocks.

Intervals, bitemporal views, correction histories and effective-interpretation windows are derived projections. Immutable typed events/evidence remain the source.

## 5. Identity and CTV invariants

1. Work identity requires authority, enactment date and number; number alone is insufficient.
2. Manifestation format is not Expression identity.
3. CC remains stable across content versions.
4. CTV validity is derived from create/terminate micro-events with amendment provenance.
5. Static `valid_from`/`valid_to` fields are projections, not source truth.
6. `resolve_CTV(CC,t)` returns a CTV or typed `Unknown` / `Conflict` / `MissingAnchor`.
7. Whole-act compilation fails closed if any required component is unresolved.
8. Parser lexical/structural candidates do not become CTV/legal facts without provenance and lifecycle gates.

## 6. Text, force, applicability and knowledge separation

| Dimension | Answers | Requires | Must not answer |
|-----------|---------|----------|-----------------|
| Text/CTV | what component content is evidenced at `t` | identity + event-derived CTV lineage | force, applicability, legal interpretation |
| Force/NormativeState | status of the norm/component at `t` | provenance-backed status transition | text content or case applicability |
| Applicability | whether a norm/version governs CaseFacts | future core decision/trace protocol + versioned profile inputs | cannot be derived from force or temporal phrase alone |
| Knowledge/practice | what observed practice evidence supports at `t` | observation and practice coverage | cannot mutate kernel state or guarantee legal truth |
| Risk | bounded advisory implications under known evidence | transition, status, practice and profile evidence | cannot decide applicability or legal outcome |

Hard invariants:

```text
CTV present       ≠ InForce
InForce           ≠ ApplicableToCase
Observed          ≠ LegallyEffective
Published         ≠ Observed
Practice available≠ Kernel state
Risk low/unknown  ≠ Legal conclusion
```

A CTV may remain retrievable for historical citation while status is `Suspended` or `Repealed`.

## 7. Applicability ownership boundary

ADR-0023 resolves TQ-01 at `[proposed]` design level:

- the neutral core owns predicate evaluation, typed decision outcomes, abstention/prerequisite gates and `ExplainableTrace`;
- versioned profiles supply `CaseFacts` schemas/instances, predicate declarations, classifiers and industry lists as read-only inputs;
- ADR-0021 continues to own transitional version choice;
- ADR-0022 continues to own profile isolation and inputs;
- profiles cannot emit final decisions outside the core protocol or mutate clocks, CTV, NormativeState or kernel ranks.

```text
Neutral core (future)
  owns ApplicabilityPredicate evaluation,
       ApplicabilityDecision outcomes,
       abstention and ExplainableTrace.

Versioned profiles
  supply CaseFacts schemas and instances,
         special-predicate declarations,
         industry priority inputs,
         versioned lists/classifiers.
```

Ownership is decided; implementation is not. Until Rust domain/ports and proof gates exist, every case-applicability request must abstain. Procurement remains a proving profile and cannot become a second ontology core.

## 8. Practice, transition and risk boundaries

- PracticeEvidence is temporally bounded and provenance-bearing.
- `EffectiveInterpretation(t)` is a derived projection.
- Practice does not mutate CTV or NormativeState, except a separately typed and proven ex-tunc constitutional status event.
- TransitionalResolver is deterministic design for version choice under explicit provisions.
- RiskReport is advisory and separate from transition/applicability decisions.
- Missing precedent analog means likelihood `Unknown`, never default low risk.

## 9. Cross-reference boundary

Parser references are candidates. A temporal reference resolver must later join:

```text
reference candidate
→ target identity
→ target CTV at governing time
→ target NormativeState
→ resolved reference or typed non-success
```

It must not resolve to “latest known text,” merge provider identities silently, or use an unresolved target as citation authority. ADR-0016–0022 do not yet own a complete reference-resolution algorithm; this remains an explicit design gap, not a hidden capability.

## 10. Paper readiness gates

| Gate | Dimension | Current ceiling | Paper acceptance | Hostile case | Future executable proof | Non-claim |
|------|-----------|-----------------|------------------|--------------|-------------------------|-----------|
| TL-G01 | five clock roles | `[bounded]` synthetic safety | five closed anchors and projection rule explicit | clock substitution or sixth clock | real-fixture anchor tests | no legal-time validation |
| TL-G02 | identity/membership | `[proposed]` | Work/Expression/Manifestation and CC/CTV/CLV distinctions explicit | identity by number or file format | Rust resolver + conflict tests | no corpus identity correctness |
| TL-G03 | CTV event-to-interval | `[proposed]` | event-derived validity and fail-closed compilation | static interval as source or partial assembly | event-sourced resolver + hostile cases | no CTV runtime |
| TL-G04 | observation/correction | `[bounded]` observation policy; correction design | immutable observations and projection rebuild | in-place overwrite/latest scrape wins | immutable log/rebuild tests | no legal completeness |
| TL-G05 | text vs legal effect | `[proposed]` | CTV and status orthogonal | text present ⇒ `InForce` | dual resolver/join tests | no legal status correctness |
| TL-G06 | force/applicability/knowledge | status/practice `[proposed]`; ADR-0023 ownership `[proposed]`; runtime `[deferred]` | triad, core/profile ownership and abstention explicit | `InForce` ⇒ Applicable | status/practice runtimes + applicability domain/ports | applicability runtime absent |
| TL-G07 | cross-reference | candidate-only `[bounded]`; resolution design gap | target join and typed non-success described | latest-text guessing | temporal reference resolver | no resolved-link corpus claim |
| TL-G08 | transition | `[proposed]` | transition choice separate from risk | chronology-only default | resolver + real transitional fixtures | no legal correctness |
| TL-G09 | practice coverage | `[proposed]` | temporality/provenance/non-mutation explicit | practice rewrites kernel | practice port/projection tests | no practice corpus |
| TL-G10 | risk | `[proposed]` | advisory/Unknown/provenance explicit | default low/legal conclusion | projection tests | no calibrated probability |
| TL-G11 | profile lists/classifiers | `[proposed]` | profile inputs versioned; core neutral | core mutation/sixth clock | per-profile contracts | no profile completeness |
| TL-G12 | applicability trace | ADR-0023 `[proposed]`; runtime `[deferred]` | core ownership recorded; runtime absence explicit; any derived NormRule graph remains non-authoritative | decision from force/text/LLM/derived graph/profile bypass | Rust domain/ports + hostile and representative real cases | no executable applicability or NormRule source truth |

A paper PASS for any gate does not change its lifecycle.

### 10.1. D6 graduation and dependency integration

This is the single tracked temporal readiness matrix. Derived blocker reports may diagnose drift but cannot replace or satisfy it.

| Gate | Graduation criteria | Evidence owner | Current state | Dependencies |
|------|---------------------|----------------|---------------|--------------|
| TL-G01 | `[bounded]` product-temporal scope requires role-preserving real-fixture anchors; `[validated]` requires representative legal-date corpus + human scope acceptance | ADR-0009, `ln-temporal` contracts | HC-09 synthetic safety `[bounded]`; legal-time correctness unvalidated | real provider fixtures for stronger claim |
| TL-G02 | `[bounded]` requires Rust Work/Expression/Manifestation and CC/CTV/CLV identity with conflict tests; `[validated]` needs multi-provider identity corpus | ADR-0016 | design only `[proposed]` | parser identity candidates as inputs, never legal facts |
| TL-G03 | `[bounded]` requires event-sourced CTV resolver and fail-closed whole-act compilation; `[validated]` needs real amendment fixtures | ADR-0017 | design only `[proposed]`; first implementation priority after parser data | TL-G01, TL-G02, provenance-ready parser components |
| TL-G04 | `[bounded]` correction requires immutable observation log and projection rebuild with no in-place rewrite | ADR-0009/0017; TQ-04 future owner if load-bearing | observation policy partial; correction protocol deferred | evidence kernel and storage ports, not RuVector alone |
| TL-G05 | `[bounded]` requires orthogonal CTV and NormativeState resolvers with join/hostile tests | ADR-0018 | design only `[proposed]` | TL-G03 and status evidence anchors |
| TL-G06 | paper graduation records triad/ownership/abstention only; runtime graduation follows TL-G12 | ADR-0018/0020/0023 | ownership `[proposed]`; applicability runtime `[deferred]` | TL-G05 and ADR-0023; never force alone |
| TL-G07 | `[bounded]` requires reference candidate → identity → CTV → NormativeState or typed non-success | TQ-05 future capability owner | candidates `[bounded]`; authoritative join deferred | TL-G02, TL-G03, TL-G05 and parser candidate quality |
| TL-G08 | `[bounded]` requires TransitionalResolver, risk separation and real transitional fixtures | ADR-0021 | design only `[proposed]` | TL-G03, TL-G05 and sourced transitional provisions |
| TL-G09 | `[bounded]` requires PracticeEvidence port/projection, clock-role tests and kernel non-mutation | ADR-0020 | design only `[proposed]`; no practice corpus | TL-G01, provenance, typed ex-tunc exception |
| TL-G10 | `[bounded]` requires advisory RiskReport with missing analog → `Unknown` | ADR-0021 | design only `[proposed]` | must not decide transition or applicability |
| TL-G11 | `[bounded]` requires versioned profile inputs and hostile core-neutrality contracts | ADR-0022 | design only `[proposed]` | neutral clocks/ranks/CTV/status remain stable |
| TL-G12 | `[bounded]` runtime requires Rust domain/ports and hostile abstention; any positive case outcome additionally requires representative real cases + human acceptance | ADR-0023 core; profiles input-only | ownership `[proposed]`; executable protocol `[deferred]` | TL-G03/05/08/09/11 snapshots; parser NormRule candidates; RuVector is not substitute proof |

Product/RQ links: TL-G01 → PC/RQ-007; TL-G02–05 and 08–11 → PC/RQ-008 plus PC/RQ-013; TL-G06/12 → PC/RQ-009 and profile inputs PC/RQ-010. PC/RQ-016 non-claims govern every gate. RuVector PC/RQ-019 and release PC/RQ-020 remain separate proof programs.

## 11. Staged golden-case catalog

These are semantic-shape oracles for future fixtures, not legal gold answers.

| ID | Stage | Case | Expected paper outcome | Hostile twin |
|----|-------|------|------------------------|--------------|
| TL-GC01 | primitives | one observation with all five clock roles | roles remain independent; missing role = `Unknown` | publication substituted for effect |
| TL-GC02 | primitives | interval bounded by two immutable events | interval is a projection | interval field overrides events |
| TL-GC03 | identity | same number, different authority/date | distinct Works | merge by number alone |
| TL-GC04 | identity | ODT and XML carriers for same edition | distinct Manifestations, not new Expressions | format creates new Expression |
| TL-GC05 | CTV | wording amendment under stable CC | terminate prior CTV/create next with provenance | new CC or unproven validity |
| TL-GC06 | CTV | one component has MissingAnchor | whole-act compilation abstains | partial silent assembly |
| TL-GC07 | text/status | CTV exists while status is Suspended | text retrievable; force Suspended; no applicability | text presence means InForce |
| TL-GC08 | text/status | repealed norm retains historical CTV | status Repealed; citation history preserved | delete text/history |
| TL-GC09 | clocks | publication precedes legal effect | publication and effect remain distinct | publication date used as effect |
| TL-GC10 | reference | internal reference at historical query time | identity+CTV+status join or typed non-success | latest edition selected |
| TL-GC11 | transition | explicit transition selects old version | OldVersion with provision provenance | date-only NewVersion default |
| TL-GC12 | practice | plenum interpretation applies ex nunc | interpretation projection changes; kernel unchanged | unproven retroactive rewrite |
| TL-GC13 | risk | no precedent analog | likelihood `Unknown` | default low risk |
| TL-GC14 | procurement profile | versioned 44-ФЗ facts influence profile predicate inputs | neutral core ranks/clocks/CTV unchanged | profile mutates core or adds clock |
| TL-GC15 | profile isolation | same neutral CTV under two profiles | different versioned profile inputs, one kernel | profile forks kernel identity |
| TL-GC16 | applicability | case request while protocol absent | explicit abstention; no decision/trace | Applicable from CTV/InForce/LLM |
| TL-GC17 | correction | new observation corrects prior projection | original evidence retained; projection rebuilt | in-place evidence rewrite |
| TL-GC18 | constitutional practice | typed ex-tunc annulment evidence | separate provenance-backed status event | generic practice prose rewrites status |

## 12. EA-04 decisions and remaining open questions

| ID | Open question | Current disposition | Required owner | Revisit trigger |
|----|---------------|--------------------|----------------|-----------------|
| TQ-01 | core applicability protocol vs profile-owned predicates | ownership resolved `[proposed]` by ADR-0023; runtime `[deferred]`; abstain until proof | ADR-0023 | revisit only through superseding ADR with cross-profile evidence, or before implementation if protocol details exceed the decided boundary |
| TQ-02 | exact mapping of transaction time to source publication and system observation | resolved `[proposed]`: qualified independent anchors, never one composite clock | ADR-0009/0017 EA-04 clarification | revisit before schema freeze only if a transaction view cannot preserve both roles |
| TQ-03 | canonical name `NormativeState` vs `NormativeStatus` | resolved `[proposed]`: `NormativeState` canonical; `NormativeStatus` deprecated alias | ADR-0018 EA-04 clarification | revisit before Rust type freeze only if compatibility requires an explicit migration alias |
| TQ-04 | operational correction/supersession protocol | `[proposed]` invariant only | future evidence/temporal decision if load-bearing | before correction ingestion, projection rebuild or audit API work |
| TQ-05 | temporal cross-reference resolution algorithm | `[proposed]` gap | future ADR or owning capability decision | before parser reference candidates can affect query/citation authority |
| TQ-06 | practice “own clock” wording | resolved `[proposed]`: first-class temporality over five clocks, not sixth clock | ADR-0020 EA-04 clarification | revisit before practice schema only if existing clock roles cannot represent required evidence |
| TQ-07 | industry-priority maxim vs neutral NormativeRank | resolved `[proposed]`: versioned profile input, never rank elevation | ADR-0019/0022 EA-04 clarification | revisit before profile resolver only with evidence that neutral ranks cannot preserve explainability |

ADR-0023 is the single residual applicability-ownership decision; it does not begin a package ADR-0023–0032. EA-04 clarification notes resolve TQ-02/03/06/07 at `[proposed]` design level without lifecycle promotion. TQ-04/05 remain deferred unless implementation makes them load-bearing.

## 13. EA-03 assessment checklist

- [x] authority limited to ARCHITECTURE, governing ADRs and Product/requirements boundaries;
- [x] five clocks represented as role-bound evidence anchors;
- [x] publication, observation, legal effect, CTV, status and applicability remain separate;
- [x] CTV does not imply `InForce`;
- [x] force does not imply applicability;
- [x] practice and risk remain derived/non-authoritative;
- [x] procurement remains a proving profile over neutral core;
- [x] TL-G01–TL-G12 each have acceptance, hostile case, future proof and non-claim;
- [x] golden cases are semantic-shape oracles, not legal truth;
- [x] TQ-01–TQ-07 remain visible with owner/disposition/revisit trigger;
- [x] O1–O7 and ADR-0023 ownership remain `[proposed]`; applicability runtime remains `[deferred]`;
- [x] semantic reviewer recorded a source-bound PASS for `e1ac83a`;
- [x] user explicitly selected `ACCEPT-AS-PROPOSED`; no acceptance was fabricated.

EA-03 acceptance is limited to this proposed paper reconciliation. EA-04 decision substance is recorded by ADR-0023 and targeted clarification notes; applicability implementation and EA-09/EA-10 assessment remain open.

## 14. Primary-critique contract completeness matrix

This matrix preserves the fourteen self-contained temporal-contract areas
requested by the recovered 2026-08-11 criticism. Status here describes paper
coverage only. It neither accepts a schema nor closes a TSG row.

| Contract area | Paper coverage | Current surface | Owner / open gap | Explicit boundary |
|---------------|----------------|-----------------|------------------|-------------------|
| Glossary | present | §3, 42 controlled rows | owning ADR per row; TSG-001 remains open | inventory completeness is not semantic completeness |
| Entity model | partial | §§5–9 identity/CTV/status/applicability concepts | ADR-0016..0023; TSG-003..010 | cardinalities, stable public schemas and several entities remain unspecified |
| Event taxonomy | design-only inventory | glossary stop-signs + `LegislativeEventKind` design boundary in `ln-temporal` (RC11-F07) | ADR-0017/0018; TSG-002 | no executable `TextChangeEvent`/`NormativeEffectEvent` runtime taxonomy |
| Temporal axes | partial | §§4–6 five-clock safety and derived projections; RC11-F06 design inventory of deferred algebra in `ln-temporal` | ADR-0009/0017; TSG-011 | no complete interval/bitemporal algebra or legal-date validation |
| Applicability DSL | deferred-undefined | §7 ownership and abstention boundary | ADR-0023 + TSG-005/006 | no accepted AST, fields, evaluator or runtime |
| Status model | partial | §6 + ADR-0018 canonical `NormativeState` | ADR-0018; TSG-004 | dimensional model and resolver are not implemented |
| Provenance | partial | §§4–9 fail-closed source/evidence boundaries | ADR-0010/0012/0015; TSG-011/012 | no complete correction/reference provenance API |
| Conflict | partial | identity/status/reference typed non-success and ADR-0019 design | ADR-0016/0019; TSG-007/012 | no competence/jurisdiction graph or legal conflict runtime |
| Correction | partial | immutable-observation invariant and TL-G04/TL-GC17 | future TQ-04 owner; TSG-011 | no accepted ledger schema, rebuild API or storage proof |
| Invariants | present as paper rules | §§4–9, gates and stop conditions | governing ADRs | no claim that every invariant has executable proof |
| Deterministic API | absent | no request/result public schema | future owner; TSG-014 | no stable Rust signature or wire contract may be inferred |
| Golden cases | partial | §11 TL-GC01–18 semantic-shape catalog | human gold owners + TSG-015 | fewer than the requested 20–30; not executable legal gold |
| Error taxonomy | absent | scattered typed non-success names only | future API owner; TSG-014 | no unified accepted enum or compatibility promise |
| Proof gates | present as paper gates | §10 TL-G01–12 + §10.1 graduation matrix | ADR-0012/0015 and human acceptance | paper PASS cannot promote lifecycle or validate product behavior |

The matrix is intentionally fail-closed: an `absent`, `partial` or
`deferred-undefined` cell is owner-routed work, not an invitation for an agent
to fill event enums, API signatures, error variants, applicability fields or
legal expected outcomes by analogy.

## 15. Stop conditions

Stop and replan if any review:

- promotes O1–O7 from paper evidence;
- claims case applicability without the typed protocol;
- collapses CTV, force, applicability or knowledge;
- substitutes clocks or invents a sixth core clock;
- lets a profile mutate neutral kernel semantics;
- treats correction/observation as legal-effect source truth;
- lets practice rewrite kernel state without a typed status event;
- treats risk as transition/applicability/legal decision;
- uses `.gsd`, roadmap, assessment, derived registry, LLM, archive or external framework as architecture/product proof;
- contradicts or bypasses ADR-0023 ownership without a superseding ADR.

<!-- continuity: L_review closed ≠ L_capability TSG closed; see review-cases/continuity-contract.md -->

<!-- capability-promotion-board: L_capability ladder companion -->
