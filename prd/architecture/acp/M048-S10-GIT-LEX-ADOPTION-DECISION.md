# M048 S10 git-lex Adoption Decision

## Status

Adopted for `M048-q4x62e / S10 / T01` as the per-capability git-lex disposition record required before ACP closure can be used as input to future law-nexus architecture binding.

This is a conservative closure decision, not a runtime adoption approval.

## Decision

Do **not** adopt runtime git-lex as the ACP core backend from M048 evidence.

Use the following baseline instead:

```text
ACP-native typed source records + ACP-native validation/lifecycle/proof/recovery mechanics + ordinary git repository history
```

Allow git-lex only as a future isolated adapter/runtime spike after explicit proof of executable provenance, acquisition policy, representative operations, `.lex` state policy, rollback, cleanup, and source/projection authority preservation.

## Authority rule

No artifact is authoritative by shape alone.

Authority requires:

```text
source category + lifecycle state + evidence anchor + proof gate or accepted decision
```

This decision therefore treats Markdown reports, generated projections, JSONL/RDF views, dashboards, recovery views, and git-lex-derived outputs as non-authoritative unless they are linked back to source records and accepted proof or decisions.

## Evidence consumed

- `prd/architecture/acp/M048-S08-GIT-LEX-CAPABILITY-MATRIX.md` — required ACP capability matrix and allowed dispositions.
- `prd/architecture/acp/M048-S08-GIT-LEX-PROOF-CONTRACT.md` — proof scenarios, workspace constraints, blocked-runtime semantics, and no-main-repo `.lex` guard.
- `prd/architecture/acp/M048-S09-GIT-LEX-FUNCTIONAL-FIT-REPORT.md` — scenario results and capability evidence.
- `prd/architecture/acp/M048-S09-GIT-LEX-RUNTIME-DIAGNOSTICS.md` — runtime probe diagnostics and mutation guard evidence.
- `prd/architecture/acp/M048-S09-INDEPENDENT-PROOF-REVIEW.md` — independent proof review verdict `PASS_BOUNDED_DECISION_INPUT`.
- `.gsd/milestones/M048-q4x62e/M048-q4x62e-ASSESSMENT.md` — post-validation requirement for ACP closure before law-nexus binding.
- `.gsd/REQUIREMENTS.md` — especially `R046`, `R047`, `R048`, `R055`, `R056`, and `R057`.
- `.gsd/DECISIONS.md` — especially `D071`, `D072`, `D073`, and `D074`.

## Per-capability adoption table

| Capability | Evidence | Status | Final disposition | Rationale | Risk | ACP delta |
|---|---|---|---|---|---|---|
| Typed records | S09 `source-record-lifecycle` passed using ACP-native fixtures; S08 requires stable IDs, record kinds, source categories, and schema versions. | Proven only ACP-native; no runtime git-lex value proven. | `implement ACP-native` | ACP needs typed records regardless of backend. Existing evidence shows deterministic ACP fixtures can satisfy the authority chain without a runtime git-lex dependency. | Medium: under-typed Markdown would recreate imitative artifacts. | Keep typed ACP source-record schema in core; expose any future git-lex representation only through an adapter that maps into the ACP schema. |
| Schema/frontmatter validation | S04/S05/S09 deterministic validation paths passed for ACP fixtures; negative semantics are covered by S08 matrix/contract expectations. | Proven ACP-native. | `implement ACP-native` | Validation is a core safety function and must not depend on optional runtime availability. | High: shape-only reports could pass as authority if validation is optional. | Implement required-field, status, anchor, proof-gate, and projection-boundary validation in ACP core. |
| Evidence anchors | S09 lifecycle and recovery evidence cites repo-relative anchors and durable reports; S08 requires portable anchors. | Proven ACP-native. | `implement ACP-native` | ACP must resolve evidence anchors even when git-lex is unavailable. | High: unresolvable anchors break cold-reader recovery and requirement boundaries. | Keep repo-relative evidence-anchor model in ACP core; adapters may contribute anchors but cannot be authority by themselves. |
| Lifecycle states and transitions | S09 `source-record-lifecycle` passed; S05 lifecycle/proof-gate/profile-boundary workflow passed; D071 preserves deterministic mechanics. | Proven ACP-native. | `implement ACP-native` | Candidate, accepted, blocked, deferred, rejected, stale, and derived states drive allowed actions and health. | High: lifecycle ambiguity enables premature acceptance. | Implement lifecycle state machine and blocked-action checks in ACP core. |
| Transition history | S08 marks transition history P1; S09 proves bounded recovery/lifecycle behavior but not a git-lex-specific transition log. | Partially evidenced ACP-native; runtime git-lex not proven. | `implement ACP-native` | ACP must recover why a state changed even without record-aware git-lex semantics. Ordinary git history is useful but not sufficient for typed rationale/provenance. | Medium: future agents may lose rationale for accepted/blocked changes. | Add ACP-native transition history records with previous state, new state, rationale, actor/tool context, evidence anchors, and supersession links. |
| Proof gates | S09 `blocked-claim` passed as durable blocked diagnostics; S05 proof-gate mechanics passed; R055 requires proof or accepted decision for authority. | Proven ACP-native; runtime blocked. | `implement ACP-native` | Proof gates are the core authority boundary. Defining a gate is not satisfying it. | Critical: requirement validation could be overclaimed from definitions or projections. | Implement proof-gate records and validation that separates gate definition, executed evidence, accepted decision, blocked diagnostics, and requirement-validation status. |
| Derived projection boundary | S09 `projection-boundary` passed; R046 forbids treating ACP/git-lex/RDF/SHACL/SPARQL/JSONL projections as source truth. | Proven ACP-native. | `implement ACP-native` | ACP must mark projections as derived and detect stale or edited projection surfaces independently of git-lex. | Critical: projections could become false source truth. | Keep projection provenance, freshness checks, non-authoritative markers, and source-record regeneration paths in ACP core. |
| Query/recovery | S09 `recovery-query` passed over source, lifecycle, anchors, proof gates, projections, dependents, and blocked findings. | Proven ACP-native. | `implement ACP-native` | Recovery must work for a cold-reader agent without relying on optional git-lex runtime. | Medium: incomplete recovery makes future audits self-confirming. | Implement ACP-native recovery queries and reports over records, decisions, requirements, proofs, health findings, and projections. |
| Health findings and blocked diagnostics | S09 records `UnsupportedGitLexRuntime`, blocked runtime status, and durable diagnostics; S08 defines `ImitativeArtifact`, `BlockedCapability`, `UnsafeMutation`, and `InsufficientEvidence`. | Proven as ACP-native diagnostic pattern; runtime remains blocked. | `implement ACP-native` | Health findings are needed to make unsupported, stale, sparse, unsafe, imitative, and blocked states durable. | High: blocked capability could be mistaken for pass evidence. | Add health-finding records with category, severity, affected capability, evidence anchor, allowed next action, and fail-closed semantics. |
| Git semantics beyond ordinary git | S09 `git-semantics` is `blocked` with `UnsupportedGitLexRuntime`; ordinary git remains sufficient baseline for branch/diff/history/conflict mechanics. | Blocked; no proven git-lex value beyond ordinary git. | `adapter later` | This is the only capability whose value is specifically about git-lex differentiating from ordinary git. It cannot justify runtime adoption without executable proof. | Medium: adopting without value proof adds repository-state risk and operational dependency. | Keep ordinary git as baseline. Define an optional future adapter proof for record-aware diff/history/conflict/rebase semantics before any runtime use. |
| Isolation and mutation guards | S09 `isolation-safety` passed; diagnostics show `.lex` absent before/after proof and no clone/install/download/build/init from main checkout. R047 forbids blind main-repo mutation. | Proven safety guard; runtime adoption still blocked. | `absorb approach` | The fail-closed isolation discipline is valuable and must apply to any future backend, not only git-lex. | Critical: main-repo `.lex` mutation could contaminate source truth and rollback. | Keep no-main-repo mutation rule in ACP core governance; require isolated workspace, rollback, cleanup, and explicit adoption decision for any repository-state backend. |
| Profile adapters | S08/S09 keep law-nexus constraints outside reusable ACP core; R048 requires Russian legal/FalkorDB/parser/R035/R037/R038 obligations to stay in profile/adapter layers. | Proven as boundary decision, not runtime integration. | `implement ACP-native` for seam; `adapter later` for git-lex backend | ACP core needs a generic adapter seam. git-lex can only attach later if it satisfies source/projection and mutation constraints. | High: profile leakage would make ACP non-reusable and could validate law-nexus claims incorrectly. | Define a core/profile boundary: generic ACP records and health semantics in core; law-nexus proof gates and any git-lex backend binding behind adapters. |

## Final disposition summary

| Disposition | Capabilities |
|---|---|
| `use git-lex runtime` | None from M048 evidence. |
| `absorb approach` | Isolation and mutation guards. |
| `implement ACP-native` | Typed records; schema/frontmatter validation; evidence anchors; lifecycle states and transitions; transition history; proof gates; derived projection boundary; query/recovery; health findings and blocked diagnostics; profile adapter seam. |
| `adapter later` | Git semantics beyond ordinary git; optional git-lex backend binding after separate proof. |
| `reject` | Blind main-repository `git lex init`; projection-as-source-truth interpretation; runtime adoption from unavailable executable evidence. |
| `blocked` | Runtime git-lex acquisition/build/invocation; record-aware git-lex value beyond ordinary git; any `.lex` state mutation in the main checkout. |

## Requirement boundary

This decision advances `R056` and supports `R057` by recording per-capability disposition. It does **not** validate `R035`, `R037`, or `R038`.

- `R035` remains active because ontology/product architecture claims still require bounded source/runtime/proof gates.
- `R037` remains active because FalkorDB ingest/runtime proof is outside ACP/git-lex disposition.
- `R038` remains a standing independent proof-review gate; S09 review is evidence for this decision input only, not global validation.
- `R046`, `R047`, and `R048` remain hard constraints.
- `R055` is adopted as an authority guardrail for ACP closure.

## Allowed next actions

- Implement ACP-native core mechanics for required capabilities.
- Use ordinary git as the repository history/diff baseline.
- Preserve an optional git-lex adapter seam.
- Plan a future isolated git-lex runtime spike only if executable provenance, acquisition, representative operations, `.lex` state policy, rollback, cleanup, and projection-boundary controls are explicit.
- Proceed to ACP closure package only after the implementation delta is recorded.

## Blocked actions

- Do not adopt runtime git-lex now.
- Do not run blind `git lex init` or create `.lex` state in the main repository.
- Do not treat git-lex reports, generated projections, JSONL/RDF, dashboards, recovery views, or GSD summaries as source truth by shape alone.
- Do not begin downstream law-nexus architecture binding until the ACP-native implementation delta and closure package are recorded.

## Closeout verdict

`ACP-native first; runtime git-lex blocked; optional adapter later; no main-repo mutation; no projection-as-authority; no downstream law-nexus binding until ACP closure package is complete.`
