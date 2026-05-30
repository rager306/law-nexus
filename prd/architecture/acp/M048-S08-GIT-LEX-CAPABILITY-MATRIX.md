# M048 S08 git-lex Capability Matrix

## Status

Adopted for `M048-q4x62e / S08 / T01` as the tracked ACP capability matrix for deciding git-lex functional fit.

This artifact is not a runtime adoption decision. It is a proof contract: every required ACP capability receives a priority, ACP rationale, proof method, pass condition, fail consequence, and allowed disposition before any future git-lex adoption can be claimed.

## Authority Rule

ACP uses the anti-imitation authority rule from `R055` and `D072`:

```text
No artifact is authoritative by shape alone.
Authority requires source category + lifecycle state + evidence anchor + proof gate or accepted decision.
```

Consequences:

- polished Markdown, generated prose, git-lex views, JSONL/RDF projections, dashboards, recovery views, and GSD summaries are not authoritative merely because they look complete;
- source truth remains tracked source records, accepted requirements/decisions, source code, tests, and durable proof summaries;
- derived outputs can support recovery and diagnostics only when their upstream authority chain is explicit;
- runtime git-lex adoption remains blocked until the proof contract below is satisfied or explicitly superseded.

## Allowed Dispositions

| Disposition | Meaning | Adoption effect |
| --- | --- | --- |
| `use git-lex runtime` | git-lex proves the capability, adds ACP value beyond ordinary project files/git, and satisfies mutation/source-boundary controls. | May become part of ACP runtime only after a later explicit adoption decision. |
| `absorb approach` | git-lex demonstrates a useful concept or workflow, but ACP should implement the concept without depending on git-lex runtime. | Inform ACP design; no runtime dependency. |
| `implement ACP-native` | ACP needs the capability directly and git-lex evidence is absent, insufficient, or not the right boundary. | Build in ACP core or profile layer as appropriate. |
| `adapter later` | Keep an extension seam for git-lex or another backend, but do not block ACP core closure. | Future integration point only. |
| `reject` | Capability shape is unnecessary, incompatible, or unsafe for ACP. | Do not adopt for ACP. |
| `blocked` | Evidence is missing, runtime is unavailable, mutation is unsafe, or the capability cannot be evaluated. | Cannot be used as authority or adoption evidence. |

## Failure Categories

| Failure category | Trigger | Required ACP response |
| --- | --- | --- |
| `ImitativeArtifact` | Artifact has architecture-like shape but lacks typed source category, lifecycle state, evidence anchor, proof gate, accepted decision, upstream trace, or downstream verification scenario. | Keep candidate/diagnostic only; block authority inheritance. |
| `BlockedCapability` | Required capability cannot be proven by tracked evidence or executable diagnostics. | Mark capability `blocked`; do not use as adoption evidence. |
| `UnsupportedGitLexRuntime` | `git lex` / `git-lex` executable acquisition, build, invocation, representative operation, or rollback is unavailable or unapproved. | Keep runtime adoption `blocked` or `adapter later`; continue ACP-native proof where safe. |
| `UnsafeMutation` | A proof creates or mutates main-repository `.lex` state, runs blind `git lex init`, or lacks rollback/cleanup policy. | Fail closed; reject runtime adoption until isolated proof and explicit mutation policy exist. |
| `InsufficientEvidence` | Evidence is only prose, projection shape, self-assertion, stale artifact, or unverified summary. | Require source/proof anchors or keep the record non-authoritative. |

## Capability Matrix

| # | Capability | Priority | Why ACP needs it | Proof method | Pass condition | Fail consequence | Allowed disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Typed records | P0 required | ACP records must not be unstructured Markdown or fluent prose only; record kind, stable ID, owner/source category, and schema version are required for authority and recovery. | Create or extract representative ACP source records through the candidate git-lex path and validate the resulting fields against the ACP record contract. | Stable typed records can be represented, extracted, and round-tripped with IDs, types, source category, lifecycle state, anchors, and schema version intact. | `ImitativeArtifact` or `InsufficientEvidence`; ACP must implement typed records natively and cannot treat git-lex output as source truth. | `use git-lex runtime`, `absorb approach`, `implement ACP-native`, `blocked` |
| 2 | Schema/frontmatter validation | P0 required | Shape-only artifacts must fail when required fields, status values, anchors, or proof fields are missing or malformed. | Run positive and negative validation fixtures for missing fields, invalid status, invalid disposition, malformed anchors, and projection/source-truth confusion. | Invalid fixtures fail with durable diagnostics; valid fixtures pass without requiring runtime side effects in the main repository. | `ImitativeArtifact` and `InsufficientEvidence`; ACP must reject promotion and keep validation ACP-native if git-lex cannot enforce it. | `use git-lex runtime`, `absorb approach`, `implement ACP-native`, `blocked` |
| 3 | Evidence anchors | P0 required | Claims need portable repo-relative proof anchors so future agents can recover what was proven and by which command/artifact. | Attach evidence anchors to records and verify they resolve to tracked files, commands, summaries, or source lines without using gitignored local paths as authority. | Anchors are repo-relative, typed, resolvable, and connected to lifecycle/proof status; broken or local-only anchors are rejected. | `InsufficientEvidence`; candidate remains non-authoritative and cannot close a requirement or adoption decision. | `use git-lex runtime`, `absorb approach`, `implement ACP-native`, `adapter later`, `blocked` |
| 4 | Lifecycle transitions | P0 required | ACP must distinguish candidate, accepted, blocked, deferred, rejected, stale, and derived states; status drives allowed actions. | Execute source-record lifecycle scenario: create candidate, add evidence, validate, transition, block/defer on proof failure, and query final state. | Valid transitions are explicit, invalid transitions fail, and blocked/deferred states cannot be misread as accepted. | `BlockedCapability` or `ImitativeArtifact`; ACP must keep transition enforcement in its own lifecycle model. | `use git-lex runtime`, `absorb approach`, `implement ACP-native`, `blocked` |
| 5 | Transition history | P1 high | ACP recovery must explain why a state changed, who/what caused it, what evidence existed, and which prior state was superseded. | Change a record through at least two lifecycle states and recover rationale/provenance/diff/history from tracked artifacts or git-lex metadata. | History preserves previous state, new state, rationale, timestamp/context, actor/tool or source, and evidence anchor. | `InsufficientEvidence`; future recovery cannot explain authority changes, so git-lex cannot be the sole lifecycle backend. | `use git-lex runtime`, `absorb approach`, `implement ACP-native`, `adapter later`, `blocked` |
| 6 | Proof gates | P0 required | Accepted architecture claims require proof commands/results or accepted decisions; defining a gate is not satisfying it. | Create a proof-required claim, attach proof command/result evidence, and verify failed/unavailable proof leaves the record blocked/deferred. | Proof status, command, result, evidence artifact, and non-claim boundary are linked to the record; failed proof cannot promote acceptance. | `BlockedCapability` or `InsufficientEvidence`; ACP must keep proof-gate satisfaction native and reject proof-by-prose. | `use git-lex runtime`, `absorb approach`, `implement ACP-native`, `blocked` |
| 7 | Derived projection boundary | P0 required | Projections are useful for interoperability and recovery but must never become source truth or requirement-validation proof by themselves. | Generate a projection, mutate or stale it, then verify ACP can detect derived/stale status and recover upstream source records. | Projection is marked derived, regenerable, freshness-checked, non-authoritative, and unable to override source records. | `ImitativeArtifact` or `UnsafeMutation`; derived views are rejected as authority and ACP keeps projection checks native. | `absorb approach`, `implement ACP-native`, `adapter later`, `reject`, `blocked` |
| 8 | Query/recovery | P1 high | ACP must answer what exists, why it is accepted/blocked, what depends on it, and where evidence/proof/projection records live. | Run recovery query scenario for a decision/claim and traverse source record, evidence anchor, proof gate, derived projections, dependent records, and blocked findings. | Query output contains the full authority chain and blocked findings without relying on fluent summary text. | `InsufficientEvidence`; git-lex may remain only an optional index/adapter while ACP implements canonical recovery. | `use git-lex runtime`, `absorb approach`, `implement ACP-native`, `adapter later`, `blocked` |
| 9 | Health findings and blocked diagnostics | P0 required | ACP needs durable visibility into stale, sparse, unsafe, unsupported, imitative, and blocked capability states. | Produce representative health findings for imitative artifact, unsupported runtime, unsafe mutation, stale projection, and insufficient evidence. | Findings are typed, durable, queryable, tied to affected records/capabilities, and visible in proof summaries. | `BlockedCapability`; missing diagnostics prevent adoption because failures would be hidden as neutral prose. | `use git-lex runtime`, `absorb approach`, `implement ACP-native`, `adapter later`, `blocked` |
| 10 | Git semantics beyond ordinary git | P2 conditional | git-lex should only be adopted if it adds value beyond ordinary git history/diff/merge for ACP workflows. | Compare branch/diff/history/conflict/rebase behavior for record changes with ordinary git and candidate git-lex operations. | git-lex provides meaningful record-aware diff/history/conflict/recovery value without weakening source/projection boundaries. | `UnsupportedGitLexRuntime` or `InsufficientEvidence`; do not adopt runtime merely for branding if ordinary git plus ACP-native records suffice. | `use git-lex runtime`, `adapter later`, `reject`, `blocked` |
| 11 | Isolation and mutation guard | P0 required | Main `law-nexus` repository must not be mutated blindly; `.lex` state requires isolated proof, rollback, cleanup, and explicit adoption decision. | Run all candidate git-lex work outside the main checkout; assert main repo has no `.lex` state before/after and no blind `git lex init` occurs. | Proof uses isolated workspace, leaves no main-repo `.lex`, records rollback/delete path, and fails closed on unexpected mutation. | `UnsafeMutation`; runtime adoption is rejected or blocked until a later proof establishes a safe mutation policy. | `use git-lex runtime`, `adapter later`, `reject`, `blocked` |
| 12 | Profile adapters | P1 high | ACP core must remain reusable; law-nexus constraints for Russian legal evidence, parser completeness, FalkorDB, LLM authority, and R035/R037/R038 belong in profile/adapter layers. | Model generic ACP records separately from law-nexus profile constraints and verify profile-specific proof gates do not leak into reusable core requirements. | Core/profile boundary is explicit, queryable, and enforced; generic ACP remains independent from law-nexus-only legal/runtime obligations. | `ImitativeArtifact` or `BlockedCapability`; ACP core may become overfit and future adoption claims become invalid. | `absorb approach`, `implement ACP-native`, `adapter later`, `reject`, `blocked` |

## Proof Scenarios

| Scenario | Required flow | Capabilities exercised | Passing interpretation |
| --- | --- | --- | --- |
| A — Source record lifecycle | create ACP record → mark candidate → add evidence anchor → validate → transition to accepted → query transition history | typed records, validation, evidence anchors, lifecycle transitions, transition history | Accepted only if the authority chain is explicit and queryable. |
| B — Blocked claim | create proof-required claim → proof fails or runtime unavailable → record becomes blocked/deferred → diagnostics persist → projection shows blocked, not accepted | proof gates, health findings, projection boundary | Runtime unavailability is a recorded blocked/deferred state, not adoption evidence. |
| C — Projection boundary | source records → generated projection → projection stale or manually edited → ACP detects derived/stale surface → source remains authoritative | derived projection boundary, validation, health findings | Projection remains diagnostic and cannot override source truth. |
| D — Recovery query | recover source record, evidence anchor, proof gate, derived projections, dependent records, and blocked findings for a claim | query/recovery, anchors, proof gates, health findings | Recovery does not depend on polished prose shape. |
| E — Git semantics | change record in branch → inspect git-lex diff/history behavior → test merge/conflict/rebase implications | git semantics, transition history | Adopt runtime only if record-aware git behavior is proven to add ACP value beyond ordinary git. |
| F — Isolation safety | run all git-lex work outside main repo → verify no `.lex` or runtime state mutation in main checkout → verify rollback/delete path | isolation/mutation guard, health findings | Unsafe mutation blocks runtime adoption even if other mechanics pass. |

## Priority Interpretation

- `P0 required`: blocks ACP closure or git-lex adoption if not satisfied, absorbed, or implemented ACP-native.
- `P1 high`: required for robust ACP operations, but may be staged behind ACP-native implementation or adapter seam if the P0 authority chain remains safe.
- `P2 conditional`: required only to justify runtime git-lex adoption; failure should not block ACP-native closure.

## Current M048 Evidence Boundary

Current M048 evidence supports the following bounded interpretation:

- S04/S05 deterministic ACP mechanics are useful evidence for typed records, validation, projection/recovery, lifecycle/proof-gate/profile-boundary checks, and mutation guard patterns.
- Runtime git-lex acquisition/build/invocation remains blocked/deferred by `D071`, `D073`, and `D074` until a later proof-gated milestone.
- `R035`, `R037`, and `R038` remain non-validated by ACP/git-lex/projection evidence alone.
- `R046`, `R047`, and `R048` remain hard boundaries for source/projection separation, mutation safety, and reusable-core/profile separation.
- This matrix advances `R056` by making the required capability contract explicit, but it does not itself satisfy runtime proof.

## Failure Modes

| Dependency | Failure path | Handling / evidence required |
| --- | --- | --- |
| Tracked source artifacts | Missing, stale, or contradictory `M048-q4x62e-RESEARCH.md`, `M048-q4x62e-ASSESSMENT.md`, requirements, decisions, or prior ACP reports | Treat matrix as incomplete; do not infer missing authority from memory or generated prose. |
| Runtime git-lex surface | `git lex` / `git-lex` missing, non-zero, malformed, times out, cannot be acquired safely, or cannot run representative operations | Mark affected capabilities `UnsupportedGitLexRuntime` and `blocked`/`adapter later`; do not clone, install, initialize, or claim runtime adoption from this task. |
| Filesystem / repository state | Main repository gains `.lex`, proof writes runtime state into main checkout, rollback path is absent, or generated outputs overwrite source records | Mark `UnsafeMutation`; fail closed and reject runtime adoption until isolated proof and mutation policy exist. |
| Validation/proof evidence | Required fields, anchors, statuses, proof results, or non-claim boundaries are missing or represented only by prose/projection shape | Mark `InsufficientEvidence` or `ImitativeArtifact`; keep record candidate/diagnostic only. |
| Human-readable matrix drift | Future edits remove required columns, capabilities, allowed dispositions, failure categories, or overclaim full adoption / requirement validation | `tests/test_m048_s08_git_lex_capability_matrix.py` should fail and force repair before closeout. |

Network acquisition is deliberately not a dependency of this T01 artifact. Any future network clone/download/build path must be introduced by a separate proof-gated task with explicit provenance and rollback controls.

## Load Profile

This task has no production runtime load dimension. It creates one static Markdown matrix and one document-level regression test; it does not add a server, API endpoint, database, queue, crawler, background worker, browser flow, or telemetry stream.

At 10x the expected matrix size, the first constrained resource is human/agent review clarity and local Markdown parsing in tests. The protection is explicit priority labels, fixed allowed dispositions, mandatory failure categories, and table-driven pytest checks. No pool sizing, rate limiting, pagination, caching, autoscaling, or runtime backpressure is required for this artifact.

A future runtime git-lex proof must define its own load/repository-state profile before any operational ACP adoption claim.

## Negative Tests

Negative coverage for this matrix is provided by `tests/test_m048_s08_git_lex_capability_matrix.py`:

- rejects a missing matrix document or title drift;
- rejects missing required sections, failure categories, or allowed dispositions;
- rejects omission of any required ACP capability;
- rejects missing proof-method, pass-condition, fail-consequence, priority, or disposition language per capability row;
- rejects full runtime adoption overclaims and requirement-validation leaks for `R035`, `R037`, and `R038`;
- requires explicit references to source/projection boundary, `.lex` mutation guard, unsupported git-lex runtime, imitative artifacts, blocked capabilities, unsafe mutation, and insufficient evidence.

The test is intentionally document-level because T01 defines an architecture/proof contract rather than executable runtime behavior.

## Observability Impact

This matrix is the durable human-readable observability surface for future ACP closure work. It makes per-capability failure disposition explicit: `blocked`, `partial`, `rejected`, `ACP-native`, `adapter-later`, or future `runtime-adopt` only after proof.

Future agents should use this artifact to explain why a capability is accepted, blocked, implemented ACP-native, left behind an adapter seam, or rejected, without relying on transient logs or fluent summaries.
