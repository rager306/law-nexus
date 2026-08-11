# EA-08 Advisory semantic review rehearsal

**Assessment class:** semantic contradiction discovery and human disposition
**Status:** `[bounded]` process evidence; advisory findings disposed; factual remediation verified in working tree and pending frozen remediation SHA
**Frozen source revision:** `430ebfdf57b8a8589a29b44bf1b8dc7809bf43ec`
**Review orchestration revision:** `1f7cc61918c6ddc33e299cff4cbeee71e07c55c1`
**Review date:** 2026-08-11
**Authority ceiling:** LLM findings are advisory; exact citations and human disposition are mandatory

## 1. Boundary

Three independent reviewers inspected authority/lifecycle, temporal/applicability, and archive/governor/process claims at the frozen source revision. They did not edit documents or make acceptance decisions.

Canonical authority remained `prd/ARCHITECTURE.md` plus `doc/adr/**`. Product and Requirements remained `[proposed]`. Assessment records, derived registry, archive, local GSD state and LLM output remained non-authoritative.

## 2. Review result

| Review contour | Result | High-impact outcome |
|---|---|---|
| Authority and lifecycle | factual contradictions found | stale Product/Requirements gap wording; charter future tense; ACP decommission lifecycle ambiguity |
| Temporal and applicability | no live semantic contradiction | qualified alias/naming residuals only; TQ-04/TQ-05 explicitly deferred |
| Archive, governor and process | factual contradictions found | test-manifest gap; stale registry counts; ADR-0023 ownership/runtime wording; ignored research references |

Temporal/applicability aggregate remained coherent: five clocks are closed; O1–O7 and L1–L7 are explicit aliases; CC/CTV/CLV and NormativeState boundaries align; ADR-0023 owns neutral applicability decision/abstention/trace with profile inputs; executable applicability runtime is absent and `[deferred]`.

## 3. Human disposition

**Selected:** `Fix factual drift; preserve semantic aliases with qualifiers`.

Decision reference: D149.

The human explicitly selected the recommended disposition:

- correct factual documentation, archive-manifest, count and ignored-anchor drift;
- split accepted archive-only authority from incomplete decommission hygiene;
- do not perform a broad ontology/type rename in this wave;
- retain semantic aliases as warnings with owners and revisit triggers;
- preserve all D098 lifecycle ceilings.

No answer was inferred from review output.

## 4. Confirmed factual findings and remediation

| ID | Frozen finding | Classification | Applied remediation |
|---|---|---|---|
| EA08-F01 | root README called tracked Product/Requirements unresolved D2 gaps | contradiction | states published `[proposed]` / EA-02 `ready-for-assessment`; not EA-10 accepted |
| EA08-F02 | charter called Product/Requirements future documents | contradiction | scope/authority list references tracked `prd/PRODUCT.md` and `prd/REQUIREMENTS.md` with proof ceilings |
| EA08-F03 | ARCHITECTURE mixed accepted archive-only boundary with `[proposed]` decommission | contradiction/ambiguity | accepted authority decision separated from `[proposed]` residual manifest/archive hygiene |
| EA08-F04 | project-state showed M112 69/109 counts as current | contradiction | M112 count labelled historical; D7 current count stated as 63/98 and non-authoritative |
| EA08-F05 | assessment/07 compressed ADR-0023 `[proposed]` ownership and `[deferred]` runtime | ambiguity | wording separates proposed decision/ownership design from absent deferred executable runtime |
| EA08-F06 | four archived test hashes were absent from decommission manifest | missing trace | added source path, archive destination, SHA-256 and `historical_test` classification; reconciled manifest summary counters with actual entries |
| EA08-F07 | generated claims view advertised ignored `prd/research/**` as remediation evidence | contradiction to tracked-anchor policy | removed ignored paths; archive artifacts are explicitly non-anchors and R035 requires new tracked current-plane evidence |
| EA08-F08 | living process front lagged EA-07 after revision binding | process drift | metadata commit `1f7cc61` advanced the front to EA-08 after revision-bound EA-07 NO-BLOCK |

## 5. Retained semantic warnings

| ID | Warning | Owner | Remediation / disposition | Revisit trigger |
|---|---|---|---|---|
| EA08-W01 | ontology uses explicit O1–O7/L1–L7 alias while D046 adoption ladder also uses L-level wording | ADR and temporal-model steward | retain explicit ontology/ladder qualifiers; no broad rename now | Rust public type/schema freeze or repeated cold-reader confusion |
| EA08-W02 | ADR-0018 retains deprecated `NormativeStatus` wording beside canonical `NormativeState` | ADR-0018 steward | retain deprecation note; normalize public type names before implementation freeze | TQ-03 or Rust type freeze |
| EA08-W03 | ADR-0020 Context/References retain “own clock” while Decision clarifies projection over five clocks | ADR-0020 steward | retain five-clock clarification as governing decision; no sixth-clock inference | TQ-06 or practice schema freeze |
| EA08-W04 | transitional prose uses “which version applies”, overloading case-applicability vocabulary | ADR-0021/0023 steward | retain with explicit transition-vs-case-applicability separation | transitional resolver public API design |
| EA08-W05 | PC-007 uses `InForce` in a clock-anchor hostile acceptance statement | Product Contract steward | treat as anti-smoothing shorthand; consider clock-only outcome wording in next Product revision | EA-09 cold-reader review or PC-007 amendment |
| EA08-W06 | MADR `status: Accepted` coexists with D098 lifecycle `[proposed]` on design ADRs | governor/ADR steward | lifecycle remains machine proof ceiling; planned governor `--explain` must show distinction | governor evidence/explain implementation or lifecycle promotion |
| EA08-W07 | derived registry verifier remains red despite quarantine PASS | architecture registry process owner | keep staleness WARN, do not invent anchors, and do not restore ACP builders | any current non-ACP builder proposal or authority-use attempt |

## 6. Rejected false positives

The following were reviewed and rejected as current contradictions:

- Product `ready-for-assessment` versus lifecycle `[proposed]`: intentional dual state;
- MADR `Accepted` versus lifecycle `[proposed]`: accepted decision does not mean implemented/validated proof;
- O1–O7 versus L1–L7: explicit alias, not semantic fork;
- EA-03 open TQ wording: frozen snapshot with later-decision notice;
- ADR-0017 profile applicability wording: narrowly and reciprocally superseded by ADR-0023;
- practice “own clock” as a sixth clock: governing Decision and crosswalk explicitly reject a sixth core clock;
- ADR-0007 `[validated]`: process harness boundary only;
- D7 quarantine PASS versus red graph verifier: quarantine and freshness are separate gates.

## 7. Verification after remediation

Required evidence before closing this rehearsal:

- full repository pytest green;
- ADR conformance zero findings;
- governor/preflight status ok;
- generated architecture views fresh;
- no ignored `prd/research/ontology_architecture_requirements` references on generated active views;
- manifest rows and archived hashes agree;
- process-front surfaces agree on EA-08;
- GitNexus change detection contains no unexpected product execution flow.

## 8. Disposition

**EA-08 semantic review rehearsal:** `REMEDIATION-VERIFIED-PENDING-FREEZE`.

Confirmed factual contradictions are remediated under human disposition D149, and the §7 checks passed in the working tree. Retained semantic warnings have explicit owners and revisit triggers. No semantic finding changed lifecycle automatically, and no product/legal/runtime claim was accepted.

EA-08 becomes `COMPLETE-WITH-WARNINGS` only after the remediation is committed, the frozen SHA is recorded, and the §7 checks are rerun against that SHA. Only then may EA-09 packet preparation begin.

## 9. Non-claims

- no product, parser, retrieval, citation, RuVector, temporal or applicability runtime validation;
- no legal correctness or case-applicability acceptance;
- no lifecycle promotion/demotion by LLM or assessment;
- no requirement satisfaction from semantic review, derived registry, archive or paper evidence;
- no EA-09 external assessment or EA-10 final acceptance.
