# Temporal Legal Model Crosswalk

**Status:** `[proposed]` D3 / EA-03 semantic reconciliation; human disposition `ACCEPT-AS-PROPOSED`
**EA-03 tested revision:** `e1ac83a714e20a6b551d5305fc4fca9f29d91aa7` (`assessment/03-temporal-reconciliation.md`)
**Method:** `paper-rehearsal`; documentation/design only
**Authority:** `prd/ARCHITECTURE.md`, ADR-0009 and ADR-0016–0022
**Product boundary:** `prd/PRODUCT.md` + `prd/REQUIREMENTS.md`
**Non-authority:** `.gsd/**`, roadmaps, assessment artifacts, derived registry, LLM output, Litho, archive and external frameworks
**Lifecycle ceiling:** five-clock role safety remains `[bounded]`; all ontology layers O1–O7 remain `[proposed]`; applicability protocol remains `[deferred]`

## 1. Purpose and non-claims

This document reconciles terminology, ownership, invariants, hostile cases and graduation gates across the five-clock policy and the O1–O7 temporal legal ontology. It is a crosswalk, not a new oracle and not an ADR.

It does not:

- implement a temporal, CTV, status, applicability, practice, risk or profile runtime;
- promote ADR-0016–0022 above `[proposed]`;
- validate legal dates, legal correctness, case applicability or corpus completeness;
- treat golden cases as authoritative legal conclusions;
- adopt LRMoo, AKML, ELI, LKIF or any external framework as project canon;
- close the residual `NormRule → ApplicabilityPredicate → CaseFacts → ApplicabilityDecision → ExplainableTrace` decision.

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

| Term | Crosswalk meaning | Primary owner | Fail-closed boundary |
|------|-------------------|---------------|----------------------|
| Clock | one of five closed, role-bound temporal dimensions | ADR-0009 | no silent substitution or sixth core clock |
| Temporal anchor | provenance-bound value or explicit absence for a named clock | ADR-0009 | missing → `Unknown`; competing → `Conflict` |
| `factual_event` | when a real-world fact occurred | ADR-0009 | not proceeding, publication or legal effect |
| `proceeding` | when a legal proceeding started | ADR-0009 | not factual event or legal effect |
| `legal_act_effect` | when an act/status event enters legal order | ADR-0009 | not publication, observation or case applicability |
| `source_publication` | when the source document was published | ADR-0009 | not system observation or legal effect |
| `system_observation` | when the system observed/ingested evidence | ADR-0009 | not publication, force or applicability |
| Event time | not a closed domain term; must be qualified by one of the five clock roles | ADR-0009 crosswalk | unqualified `event_time` is ambiguous |
| Transaction time | recording dimension; must state whether the fact is source publication or system observation | ADR-0017 §5 + ADR-0009 | cannot collapse two ADR-0009 clocks into one source of truth |
| Valid/effective time | legal-order effect anchored to `legal_act_effect` | ADR-0017 + ADR-0009 | does not imply case applicability |
| CC | stable Component Concept identity | ADR-0017 | not text, force or applicability |
| CTV | semantic component content version derived from events | ADR-0017 | not a static interval, force or legal fact from lexical evidence alone |
| CLV | language realization of a CTV | ADR-0017 | not a separate legal status |
| NormativeState | time-indexed normative status (`InForce`, `Suspended`, `Repealed`, `Superseded`, `Transitional`, `Unknown`) | ADR-0018 | text presence does not imply `InForce` |
| Force | informal product term for NormativeState/status at a governing time | ADR-0018 | force is not applicability or system knowledge |
| Applicability | whether a norm/version governs supplied case facts, producing a typed decision and explainable trace | residual decision; conceptual parts in ADR-0017/0021/0022 | executable protocol absent; default is abstention |
| Knowledge | what the system can support from observed evidence and practice coverage | ADR-0009 + ADR-0020 crosswalk | knowledge of a claim is not the claim's legal state |
| Correction | a new immutable observation/evidence event and rebuilt projection | ADR-0009 + ADR-0017 crosswalk | no in-place rewrite or “latest scrape wins” |
| Status transition | evidence-gated change of NormativeState anchored to `legal_act_effect` | ADR-0018 | absence of evidence is not a transition |
| Transitional resolution | deterministic design for choosing a version across amendment rules | ADR-0021 | no chronology-only default; distinct from risk |
| Practice overlay | non-authoritative, temporally bounded `EffectiveInterpretation` projection | ADR-0020 | does not rewrite CTV/status except typed ex-tunc status event |
| Risk | provenance-bearing advisory assessment with explicit unknowns | ADR-0021 | not actuarial probability or legal conclusion |
| Profile | versioned adapter supplying industry priority, facts, special norms, practice weighting and risk factors | ADR-0022 | cannot mutate kernel evidence, ranks or clocks |

`NormativeState` and `NormativeStatus` in ADR-0018 are treated as names for the same status dimension. A later amendment should normalize the public term before implementation.

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

The governing documents currently distribute partial concerns:

- ADR-0017 separates enters-legal-order from applicability and calls applicability profile-sensitive;
- ADR-0021 owns transitional version choice, not general case applicability;
- ADR-0022 owns profile facts, special predicates and industry weighting, not the decision protocol;
- Product clause PC-009 records the absent typed protocol.

Proposed reconciliation for later ADR decision:

```text
Neutral core (future)
  owns ApplicabilityPredicate evaluation,
       ApplicabilityDecision outcomes,
       abstention and ExplainableTrace.

Versioned profiles
  supply CaseFacts schemas,
         special predicates,
         industry priority inputs,
         versioned lists/classifiers.
```

This crosswalk does **not** adopt that boundary as architecture substance. Until EA-04 records a governing decision, every case-applicability request must abstain. Procurement remains a proving profile and cannot become a second ontology core.

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
| TL-G06 | force/applicability/knowledge | status/practice `[proposed]`; applicability `[deferred]` | triad and abstention explicit | `InForce` ⇒ Applicable | status/practice runtimes + future applicability ADR/runtime | applicability absent |
| TL-G07 | cross-reference | candidate-only `[bounded]`; resolution design gap | target join and typed non-success described | latest-text guessing | temporal reference resolver | no resolved-link corpus claim |
| TL-G08 | transition | `[proposed]` | transition choice separate from risk | chronology-only default | resolver + real transitional fixtures | no legal correctness |
| TL-G09 | practice coverage | `[proposed]` | temporality/provenance/non-mutation explicit | practice rewrites kernel | practice port/projection tests | no practice corpus |
| TL-G10 | risk | `[proposed]` | advisory/Unknown/provenance explicit | default low/legal conclusion | projection tests | no calibrated probability |
| TL-G11 | profile lists/classifiers | `[proposed]` | profile inputs versioned; core neutral | core mutation/sixth clock | per-profile contracts | no profile completeness |
| TL-G12 | applicability trace | `[deferred]` | absence and residual owner recorded; any derived NormRule graph remains non-authoritative | decision from force/text/LLM/derived graph | new ADR + Rust domain/ports + real cases | no executable applicability or NormRule source truth |

A paper PASS for any gate does not change its lifecycle.

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

## 12. Open questions and EA-04 inputs

| ID | Open question | Current disposition | Required owner | Revisit trigger |
|----|---------------|--------------------|----------------|-----------------|
| TQ-01 | core applicability protocol vs profile-owned predicates | `[deferred]`; abstain | one residual ADR decision in EA-04 | before any applicability domain/port task, case-level claim or procurement applicability profile |
| TQ-02 | exact mapping of transaction time to source publication and system observation | `[proposed]`; preserve both roles | ADR-0009/0017 clarification | before CTV event schema or bitemporal projection contract is frozen |
| TQ-03 | canonical name `NormativeState` vs `NormativeStatus` | `[proposed]` alias | ADR-0018 clarification | before Rust status type/port naming is implemented |
| TQ-04 | operational correction/supersession protocol | `[proposed]` invariant only | future evidence/temporal decision if load-bearing | before correction ingestion, projection rebuild or audit API work |
| TQ-05 | temporal cross-reference resolution algorithm | `[proposed]` gap | future ADR or owning capability decision | before parser reference candidates can affect query/citation authority |
| TQ-06 | practice “own clock” wording | interpret as first-class temporality over five clocks | ADR-0020 clarification | before practice event schema or projection implementation |
| TQ-07 | industry-priority maxim vs neutral NormativeRank | profile input, never rank elevation | ADR-0019/0022 clarification | before any profile conflict resolver or versioned industry list implementation |

No package ADR-0023–0032 is justified by this crosswalk. Only TQ-01 is currently confirmed as a residual load-bearing new decision candidate; the remaining items are clarification/amendment candidates unless later review proves otherwise.

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
- [x] O1–O7 remain `[proposed]`, applicability remains `[deferred]`;
- [x] semantic reviewer recorded a source-bound PASS for `e1ac83a`;
- [x] user explicitly selected `ACCEPT-AS-PROPOSED`; no acceptance was fabricated.

EA-03 acceptance is limited to this proposed paper reconciliation. EA-04 ADR decisions and EA-09/EA-10 assessment remain open.

## 14. Stop conditions

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
- closes TQ-01 by assumption instead of a governing decision.
