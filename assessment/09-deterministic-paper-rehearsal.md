# EA-07 Deterministic paper rehearsal

**Assessment class:** deterministic control paper rehearsal
**Method:** `paper-rehearsal` for every checklist row
**Status:** `[bounded]` process evidence; technical `NO-BLOCK`; aggregate `WARN`
**Tested revision:** `430ebfdf57b8a8589a29b44bf1b8dc7809bf43ec`
**Tested corpus:** committed D7/archive/governor documentation package
**Review date:** 2026-08-11
**Publication state:** revision-bound EA-07 process evidence; not an EA-09 external packet

## 1. Boundary

This record manually applies the EA-07 paper gate catalog. Commands and parsers provide diagnostic inputs, but the disposition is a paper rehearsal and must not be represented as automated-gate evidence.

Authority remains `prd/ARCHITECTURE.md` plus `doc/adr/**`. Product and requirements documents remain `[proposed]`. Derived registry, local GSD state, LLM output, archive content and this assessment cannot promote lifecycle, satisfy a requirement, or prove product/legal readiness.

## 2. Checklist

| ID | Check | Method | Result | Evidence / rationale |
|---|---|---|---|---|
| EA07-01 | tracked link integrity | `paper-rehearsal` | PASS | 34 living/assessment files and 30 relative Markdown links scanned; zero missing targets |
| EA07-02 | schema and section conformance | `paper-rehearsal` | PASS | 19 ADRs have Status lifecycle and required MADR sections; Product/Requirements contracts present; governor ADR hygiene PASS |
| EA07-03 | unique IDs | `paper-rehearsal` | PASS | 19 unique ADR IDs; PC-001..020; RQ-001..020; TL-G01..12; TL-GC01..18; TQ-01..07; registry items 63 and edges 98 unique |
| EA07-04 | reciprocal supersession | `paper-rehearsal` | PASS | ADR-0017 §5 ↔ ADR-0023 and ADR-0005 crate-map ↔ ADR-0011 are reciprocally scoped; whole predecessor ADRs remain at their recorded lifecycle |
| EA07-05 | typed edge integrity | `paper-rehearsal` | PASS | 98 edges: 29 superseded and 69 hypothesis; zero active authority-like `satisfies`/`validated_by`/`implements` edges and zero dangling endpoints |
| EA07-06 | lifecycle ceiling | `paper-rehearsal` | PASS | Oracle foundation map matches all ADR Status lifecycles; Product/Requirements remain `[proposed]`; ADR-0007 `[validated]` is process-harness only |
| EA07-07 | proof-class sufficiency | `paper-rehearsal` | PASS | PC/RQ records retain proof classes and non-claims; no bounded/smoke/paper evidence is promoted to validated product capability |
| EA07-08 | non-claim preservation | `paper-rehearsal` | PASS | Product, Requirements, temporal crosswalk, D7 views and assessment records retain explicit runtime/legal/readiness ceilings |
| EA07-09 | roadmap front sync | `paper-rehearsal` | PASS | ARCHITECTURE, root README, charter and project-state Markdown/JSON identify EA-07 as current process front; D7/EA-06 is completed with staleness WARN |
| EA07-10 | era/noise and retired-ID policy | `paper-rehearsal` | PASS | governor era-noise and retired-ID checks PASS; retired active symlink/scripts/tests removed; vault copies ignored/untracked |
| EA07-11 | registry quarantine | `paper-rehearsal` | PASS | `assessment/06-derived-registry-quarantine.md`: IDs preserved, active authority edges removed, obsolete/missing-anchor rows blocked or superseded |
| EA07-12 | temporal readiness coverage | `paper-rehearsal` | PASS | TL-G01..12, TL-GC01..18 and TQ-01..07 are complete as paper design/readiness coverage; O1–O7 remain `[proposed]` and runtime absent |

## 3. Warnings

| ID | Finding | Owner | Remediation | Revisit trigger |
|---|---|---|---|---|
| EA07-W01 | Derived graph verifier remains fail-closed: 243 source-anchor, 11 graph-integrity and 2 freshness findings; historical extractor/builder absent | architecture registry process owner | keep D7 quarantine and non-authority banners; do not invent anchors or restore ACP tooling; design a current non-ACP builder only as separate process work | any proposal to use registry/graph output as authority or a new builder proposal |
| EA07-W02 | Governor still reports historical vocabulary in seven active test files | harness/CI process owner | retain qualified negative fixtures where they test policy; relocate only tests that depend on archived behavior, not historical-token assertions needed by governor | next archive hygiene closeout or CI process-suite change |
| EA07-W03 | MADR `status: Accepted` coexists with lifecycle `[proposed]` for design ADRs and can be misread by naive tooling | ADR steward | keep lifecycle as the machine proof ceiling; explain this distinction in governor `--explain`; never infer lifecycle from MADR status alone | governor evidence/explain implementation or any lifecycle promotion |
| EA07-W04 | Several cross-surface references are bare repository paths rather than clickable Markdown links | documentation process owner | retain path-existence checking; optionally normalize high-value Product/Requirements/temporal links before external packet publication | EA-09 cold-reader review |

Every WARN has an owner, remediation and revisit trigger. None authorizes lifecycle promotion or product work.

## 4. Diagnostic inputs

The following diagnostic inputs were green at rehearsal time:

- full repository pytest: `374 passed, 4 skipped`;
- `verify-adr-conformance.py`: zero findings;
- governor: zero errors, one advisory historical-test-debt warning;
- preflight: status ok;
- generated architecture views freshness: ok;
- remediation matrix freshness: ok;
- major track split freshness: ok;
- Ruff and lock consistency: ok.

The derived graph verifier remains red as documented in EA07-W02. Its result is not hidden or converted to PASS.

## 5. Disposition

**Technical disposition:** `NO-BLOCK`.

All required EA-07 rows are PASS under `method=paper-rehearsal`; no BLOCK was found. The aggregate remains WARN because derived-registry staleness is intentionally unresolved. The content packet was committed and rerun successfully at the tested revision.

This permits EA-08 semantic review rehearsal against the revision-bound packet. It does not itself close EA-08, EA-09 or EA-10.

## 6. Non-claims

- no automated-gate evidence claim;
- no product, runtime, parser, retrieval, citation, RuVector, CTV or applicability validation;
- no legal correctness or case-applicability acceptance;
- no lifecycle promotion of Product, Requirements or ADR-0014/0016–0023;
- no requirement satisfaction from paper checks, registry output, archive content or LLM review;
- no EA-09 external assessment or EA-10 final acceptance.
