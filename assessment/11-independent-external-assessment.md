# EA-09 Independent external desk assessment

**Assessment class:** independent artifact, semantic, process and reproducibility review
**Status:** `[bounded]` process evidence; `COMPLETE-WITH-WARNINGS`; technical `NO-BLOCK`
**Frozen revision:** `d96a903f0d8e2deef8549fa6d82dfe1ba658df4f`
**Assessment date:** 2026-08-11
**Independent recommendation:** `accepted-with-findings`
**Acceptance authority:** human project owner; EA-10 disposition pending

## 1. Independence, conflict of interest and access

Two non-authoring model-assisted desk reviewers independently assessed the frozen tracked tree. Neither reviewer edited the packet, owned product/runtime claims, interpreted legal outcomes, controlled requirement closure, or held EA-10 acceptance authority.

Source access was limited to the tracked repository and read-only deterministic controls. Private legal corpus, secrets, raw provider payloads, ignored archive bodies and local GSD state were unavailable or excluded as authority. GitNexus and LLM outputs were advisory instrumentation only.

## 2. Mode verdicts

| Mode | Result | Evidence ceiling |
|---|---|---|
| Artifact | WARN | living authority surfaces and IDs complete; packet naming differs from roadmap template; open DOC rows retained |
| Semantic | PASS | sampled consequential claims coherent at declared lifecycles; no live temporal/applicability contradiction |
| Process | WARN | roles and non-claims clear; EA-10 disposition and several defect closures remain open |
| Reproducibility | WARN | deterministic controls reproduce; derived graph intentionally remains red/stale and non-authoritative |

No `BLOCK` was found that prevents a process-level EA-10 disposition.

## 3. Required trace chains

Each chain was checked as Product clause → Requirement → ADR → Oracle claim → Roadmap → Evidence/proof class.

| Chain | Result | Trace summary | Proof ceiling / non-claim |
|---|---|---|---|
| Rust-only runtime | PASS | PC-001 → RQ-001 → ADR-0004/0005/0007/0011 → direction contract → evidence-gated roadmap | product `[bounded]`; harness `[validated]` process only |
| Five clocks | PASS | PC-007 → RQ-007 → ADR-0009 → oracle five-clock closure → temporal roadmap | synthetic-hostile; no legal-date correctness |
| Evidence kernel | PASS | PC-003 → RQ-003 → ADR-0010/0011/0015 → oracle C10/C12/C13 → hostile sequence | synthetic-hostile; not product readiness |
| Temporal ontology O1–O7 | PASS | PC-008 → RQ-008 → ADR-0016–0022 → L1–L7 oracle alias → M165 design band | `[proposed]`, `none-design`; no ontology runtime |
| Applicability ownership | PASS | PC-009 → RQ-009 → ADR-0023 → neutral core/profile boundary → evidence-gated roadmap | ownership `[proposed]`; executable runtime absent `[deferred]` |
| RuVector infrastructure | PASS | PC-019 → RQ-019 → ADR-0014 → proposed direction contract → infrastructure prerequisites | `[proposed]`, `none-design`; no live TEI/RuVector proof |
| Archive-only legacy | PASS | anti-revival clauses → RQ-001/archive obligations → ADR-0004/0007/0014 → archive-only oracle → decommission hygiene | process/archive proof only; no legacy authority |
| Retrieval/citation non-claims | PASS | PC-005/006/014/016 → corresponding RQ → ADR-0010/0012/0015/0014 → oracle non-claims → M161–M164 honesty | port/synthetic only; no production retrieval or legal-answer validation |
| LLM non-authority | PASS | PC-014 → RQ-014 → ADR-0012/0015 → oracle → EA roadmap | process invariant; LLM never legal/acceptance authority |
| Provider separation | PASS | PC-002 → RQ-002 → ADR-0013/0015 → independent Consultant/Garant oracle → parser roadmap | bounded fixtures/port contracts; no parser completeness |
| Procurement profile | PASS | PC-010 → RQ-010 → ADR-0022/0023 → profile boundary → design roadmap | `none-design`; no procurement applicability runtime |

## 4. Reproducibility evidence

At the frozen revision:

- full pytest: `374 passed, 4 skipped`;
- ADR conformance: zero findings;
- governor: status ok, 45 pass and one advisory historical-test-debt warning;
- preflight: status ok;
- generated views, remediation matrix and track split: freshness checks pass;
- living/assessment links: no missing relative target in the audited set;
- derived architecture graph verifier: fail-closed staleness WARN, not hidden and not promoted to PASS.

## 5. Findings

| ID | Finding | Owner | Remediation | Revisit trigger |
|---|---|---|---|---|
| EA09-W01 | project-state `source_revision` names EA-08 remediation `962a4e7`, not EA-09 binding commit | project-state steward | bind final packet/disposition revision in EA-10 metadata | EA-10 publication or any freeze-equality claim |
| EA09-W02 | DOC-01/02/07/08/09/10 remain `addressed-in-draft` | owners in known-defect register | close only with frozen evidence and EA-10 disposition, or retain accepted exception | EA-10 checklist and relevant living-surface changes |
| EA09-W03 | derived graph remains stale; six residual active-looking REQ rows are local-GSD anchored | architecture registry process owner | keep quarantine; block/retarget only with tracked current evidence; never treat as RQ satisfaction | any proposal to use registry as authority or new builder work |
| EA09-W04 | assessment packet filenames differ from the roadmap’s illustrative template | assessment process owner | retain phase-index mapping or add packet index; do not rewrite frozen history | EA-10 packaging |
| EA09-W05 | governor still reports seven historical-vocabulary test files | harness/CI process owner | retain qualified policy fixtures; relocate only behavior-dependent historical tests | CI suite or archive-hygiene change |
| EA09-W06 | retained semantic alias and terminology warnings from EA-08 remain open | ADR/Product owners listed in assessment/10 | preserve qualifiers; normalize only at listed type/schema/product triggers | EA08-W01..W07 triggers |
| EA09-W07 | paper controls exceed the deterministic governor subset | governor/process owner | implement evidence/explain/matrix checks incrementally; do not call paper checks automated | governor verification implementation slices |

Every WARN has an owner, remediation and revisit trigger. No warning is a sole authority or proof dependency.

## 6. Known-defect disposition input

- DOC-03/04/05/06 remain `verified-closed` within their documentation/process scopes.
- DOC-01/02 have strong frozen evidence for closure but require EA-10 disposition.
- DOC-07 remains matrix-modeling debt.
- DOC-08 is substantively exercised by EA-07/EA-08 but awaits final process disposition.
- DOC-09 remains event-triggered freshness adoption debt.
- DOC-10 requires this report plus EA-10 signed disposition.

No defect closure here validates product/runtime/legal behavior.

## 7. Independent recommendation

**Recommendation:** `accepted-with-findings`.

Rationale: the authority chain is coherent; all required sample chains resolve with honest proof ceilings; D7 quarantine prevents derived authority creep; EA-07 and EA-08 produced no BLOCK and preserved human authority. Remaining WARN debt is material enough to rule out `accepted-for-process`, but does not justify `rejected-needs-remediation` for the documentation/process scope.

This recommendation is advisory. EA-10 acceptance authority must select the final disposition and map retained findings.

## 8. Non-claims

- no product, release or legal-correctness validation;
- no parser completeness or representative corpus validation;
- no production retrieval quality or citation-safe legal answer acceptance;
- no live RuVector/TEI, ontology or applicability runtime;
- no lifecycle promotion from paper, governor, assessment, LLM, registry, GSD or archive;
- no EA-10 acceptance or automatic known-defect closure.
