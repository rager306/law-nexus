---
title: GSD Sync Drift Diagnostic Contract
status: S02 diagnostic contract
date: 2026-05-17
inputs:
  - prd/research/ontology_architecture_requirements/06-r035-evidence-audit.md
  - .gsd/milestones/M019-v10cgp/slices/S01/S01-SUMMARY.md
non_authoritative: true
---

# GSD Sync Drift Diagnostic Contract

This contract defines stable diagnostic IDs for the S02 GSD sync drift check. It detects synchronization drift between requirement lifecycle state, milestone completion summaries, planned registry mappings, current derived registry/views, and unsafe lifecycle wording.

It is intentionally narrow: these diagnostics do **not** validate R035, do **not** prove registry completeness, and do **not** synchronize or repair R035. They only make the active/unmapped contradiction class repeatably detectable.

## Diagnostic Table

| Diagnostic ID | Drift signal | Evidence source | Expected condition | Failure message | Remediation owner | Non-claim boundary |
|---|---|---|---|---|---|---|
| DRIFT-R035-ACTIVE-UNOWNED | Active requirement not owned by an in-progress milestone | `06-r035-evidence-audit.md` Audit Verdict and S02 Drift Signals; S01 summary completion metadata | If R035 remains Active while M017/M018 are complete, at least one in-progress milestone or explicit follow-up owner must own the active work. | `DRIFT-R035-ACTIVE-UNOWNED: R035 remains Active but is not visibly owned by an in-progress milestone or explicit follow-up owner.` | GSD planning / requirement lifecycle owner | Does not claim M017/M018 failed; only flags lifecycle ownership drift. |
| DRIFT-R035-REGISTRY-MAPPING-ABSENT | Registry-mapping absence for planned ontology candidates | `05-registry-integration-plan.md` candidate mappings as cited by `06-r035-evidence-audit.md`; current `prd/architecture/architecture_items.jsonl` | Planned R035 candidate item IDs must resolve to current derived registry items before any lifecycle wording treats mapping as complete; known planning aliases may resolve through verifier-policy canonical IDs only when the generated registry record carries explicit alias reconciliation evidence. | `DRIFT-R035-REGISTRY-MAPPING-ABSENT: planned R035 ontology candidate IDs are absent from architecture_items.jsonl.` | Extractor / registry integration owner | Does not assert which mappings are correct; only detects absence of planned candidates in current derived registry. |
| DRIFT-R035-MISSING-PROOF-GATE | Missing named proof gate | `06-r035-evidence-audit.md` Current derived-state evidence; `scripts/verify-architecture-graph.py` policy references | `GATE-AKOMA-FRBR-NORMALIZATION` must exist as a registry item before it can be treated as registry-backed proof structure; its presence is still only a proof-gate endpoint, not satisfied proof. | `DRIFT-R035-MISSING-PROOF-GATE: required gate GATE-AKOMA-FRBR-NORMALIZATION is referenced by source/policy evidence but missing from architecture_items.jsonl.` | Extractor / ontology proof-gate owner | Verifier-policy mentions are not proof that the gate exists or is satisfied. |
| DRIFT-R035-STALE-GATE-VIEW | Stale or empty derived R035 gate-status view | `prd/architecture/claims_ledger.md` `## R035 Gate Status`; `06-r035-evidence-audit.md` Current derived-state evidence | The R035 gate-status view must enumerate the planned M017 candidate gates/data items using synchronized canonical IDs before it can be considered fresh for R035 mapping coverage. | `DRIFT-R035-STALE-GATE-VIEW: claims_ledger.md has an R035 Gate Status section but does not enumerate the planned M017 ontology candidate set.` | Architecture view / claims-ledger regeneration owner | Does not treat claims ledger as authoritative source evidence; it only checks view freshness against tracked source expectations. |
| DRIFT-R035-POLICY-ENDPOINT-MISSING | Enforced verifier rules with missing registry endpoints | `scripts/verify-architecture-graph.py` `ONTOLOGY_PROMOTION_RULES`; current `architecture_items.jsonl`; `06-r035-evidence-audit.md` verifier-policy evidence | R035-relevant gate IDs named by verifier policy must resolve to registry items before policy references are counted as registry-backed endpoints; unrelated verifier gates are outside this R035 drift signal. | `DRIFT-R035-POLICY-ENDPOINT-MISSING: ontology verifier policy names required gates that do not resolve to current registry items.` | Verifier / registry integration owner | Does not claim verifier policy is wrong; it prevents policy text from being counted as generated registry proof. |
| DRIFT-R035-CANDIDATE-CURRENT-MISMATCH | Candidate-vs-current mismatch | `05-registry-integration-plan.md` 12 candidate items and 9 edge mapping classes as cited by `06-r035-evidence-audit.md`; current JSONL outputs | Current derived JSONL should contain the planned candidate set after alias-aware canonicalization, with explicit alias reconciliation evidence for known planning-vs-policy name drifts, or the mismatch must remain visible as drift. | `DRIFT-R035-CANDIDATE-CURRENT-MISMATCH: source plan lists 12 candidate items and 9 edge mapping classes, but current derived registry outputs do not contain the candidate set.` | Extractor / architecture registry owner | Does not validate candidate correctness, edge endpoints, source anchors, or proof levels. |
| DRIFT-R035-GATE-ID-DRIFT | Gate ID drift between planning docs and verifier policy | `06-r035-evidence-audit.md` Missing Proof Decisions; `05-registry-integration-plan.md`; `scripts/verify-architecture-graph.py` | Known aliases or naming mismatches must be reconciled before registry emission, including `GATE-DEONTIC-MAPPING-PROOF` -> `GATE-LKIF-DEONTIC-BENCHMARK` and `GATE-1000-DOC-PILOT` -> `GATE-PILOT-SCALE-READINESS`; generated canonical records must retain explicit non-authoritative alias evidence. | `DRIFT-R035-GATE-ID-DRIFT: planned gate IDs and verifier-policy gate IDs disagree and have not been reconciled as registry aliases or chosen canonical IDs.` | Ontology architecture / verifier owner | Does not choose canonical IDs; it only reports unresolved naming drift. |
| DRIFT-R035-UNSAFE-LIFECYCLE-LANGUAGE | Unsafe lifecycle language that validates R035 from milestone completion alone | `06-r035-evidence-audit.md` Audit Verdict and Non-Claims; S01 key decisions | No document, requirement update, summary, or derived view may state or imply that R035 is validated merely because M017/M018 completed. | `DRIFT-R035-UNSAFE-LIFECYCLE-LANGUAGE: lifecycle wording implies R035 validation from milestone completion without regenerated registry presence and verifier/view coverage.` | Requirement lifecycle / documentation owner | Does not block safe wording such as Active, not validated, planned, proposed, bounded evidence, or deferred proof. |

## Diagnostic Output Requirements

A conforming S02 drift check should emit diagnostics with:

- the stable `DRIFT-*` ID;
- the evidence source used for the check;
- the observed mismatch;
- the remediation owner;
- the non-claim boundary when the diagnostic could be mistaken for R035 validation evidence.

## Non-Claims

This contract does **not** claim any of the following:

- R035 is validated.
- M017 or M018 completion proves registry integration.
- The 12 planned candidate items are complete or correct.
- The 9 planned edge mapping classes have valid current endpoints.
- Any ontology proof gate exists in the current registry unless generated registry artifacts show it.
- Any ontology proof gate is satisfied.
- Verifier-policy references prove registry presence.
- Claims-ledger or JSONL views are authoritative source evidence.
- Manual JSONL/view edits are an acceptable substitute for extractor integration and regeneration.
- This contract synchronizes, repairs, or updates R035 lifecycle state.
