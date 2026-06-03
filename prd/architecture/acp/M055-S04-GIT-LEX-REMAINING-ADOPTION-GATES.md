# M055 S04 Git Lex Remaining Adoption Gates

## Status

Expanded through `M055-dbt65v / S04 / T03`.

S04 inventories and gates all remaining adoption questions before any stronger git-lex backend role beyond L1 shadow diagnostics. It consumes S01 cutline, S02 adapter evidence, and S03 ACP-shaped runtime proof, but it does **not** approve main `.lex`, source-truth transfer, production adoption, release/plugin-bundled binary trust, or LegalGraph requirement validation.

## Current evidence baseline

### Proven enough for L1 shadow diagnostics

S01 defined the backend ladder and immediate target:

```text
immediate backend target: L1 shadow diagnostic/projection backend
ACP source truth: unchanged, ACP-native records remain authoritative
main .lex: blocked
source-truth backend: blocked
production backend: blocked
```

S02 implemented the internal adapter:

```text
adapter schema: m055.acp_git_lex_backend_diagnostic.v1
backend level: L1-shadow-diagnostic-projection
authority: non-authoritative-diagnostic
can_validate_requirement: false
can_mutate_source_truth: false
allowed operations: backend_help, workspace_init, workspace_sync, class_inventory, bounded_query, bounded_query_json, validation_diagnostic, reject_denied
blocked operations: save, create, raw, raw backfill, join, kit-update, nuke, display, serve, viz, listen, history-verify, dump, parse
```

S03 proved the ACP-shaped runtime matrix in isolation:

```text
final disposition: acp-shaped-shadow-runtime-proof-passed
tracked diagnostics: prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl
rows: 10
classification summary: pass=7, diagnostic-fail=1, rejected=2
workspace cleanup: clean
main .lex/Squad/Raw residue: none
```

### Still not proven

M055 through S03 still does not prove:

```text
ACP source truth migration
main repository .lex adoption
production runtime readiness
release/plugin-bundled binary trust
real legal payload ingestion
Russian legal evidence correctness
FalkorDB runtime behavior
Garant ODT parser completeness
R035/R037/R038 validation
JSON-LD runtime support
broad RDF-star/SPARQL-star parity
server/viz/listen suitability
save/create/raw/join/kit-update/nuke suitability
raw/session payload safety
```

## Classification vocabulary

| Classification | Meaning |
|---|---|
| `L1-compatible` | Safe inside the current L1 shadow diagnostic/projection boundary with existing S02/S03 constraints. |
| `L2-candidate` | Plausible next operational diagnostic backend capability, still non-authoritative and no main `.lex`, but needs stronger workflow/stability proof. |
| `rehearsal-needed` | Requires isolated rehearsal before any adoption decision; not safe to treat as current capability. |
| `blocked` | Cannot advance without explicit new proof gates and/or human adoption decision. |
| `rejected` | Excluded from ACP adapter scope by current safety/authority policy unless a future explicit reversal occurs. |
| `out-of-scope` | Belongs to another subsystem/profile rather than git-lex backend adoption. |

## Remaining-question backlog

### Summary table

| Surface | Current classification | Why |
|---|---|---|
| L1 shadow diagnostic/projection continuation | `L1-compatible` | S02/S03 prove adapter and ACP-shaped synthetic runtime diagnostics within isolation and non-authority boundaries. |
| Internal adapter invocation in ACP workflows | `L2-candidate` | Adapter exists and tests pass, but regular ACP workflow integration, retries, retention, and failure-state surfaces are not yet proven. |
| Durable bounded diagnostics JSONL | `L1-compatible` | S03 tracked bounded ACP-facing JSONL with no private raw fields and no forbidden payload markers. |
| Diagnostic storage/retention policy | `L2-candidate` | JSONL evidence exists, but retention, compaction, indexing, and lifecycle policy are not yet specified as product workflow behavior. |
| Main repository `.lex` | `rehearsal-needed` | Still blocked for direct adoption; requires isolated main-repo rehearsal, rollback/state proof, ignored/tracked policy, and explicit human decision. |
| Main repository `Squad` / `Raw` | `blocked` | S02/S03 explicitly require absence; `Raw` in particular risks session/provider payload leakage. |
| Source truth migration | `blocked` | ACP-native records remain authoritative; migration needs authority design, conflict resolution, proof gates, and accepted decision. |
| ACP source-record lifecycle authority | `blocked` | git-lex projections can imitate authority; authoritative ACP statements require source category, lifecycle state, evidence anchor, and proof gate/decision. |
| Rollback and state cleanup | `rehearsal-needed` | S03 cleaned `/tmp` workspace, but main `.lex`, `.git/lex`, generated sidecars, commits, hooks, and failed-state cleanup are not rehearsed. |
| Pinned source-built debug binary | `L1-compatible` | D077/M054 identity is sufficient for local proof and L1 diagnostics only. |
| Updating git-lex source pin | `rehearsal-needed` | Remote HEAD drift was observed; any update needs new decision, rebuild, identity, tests, and runtime matrix. |
| Release binaries | `blocked` | No release/provenance proof; tags/releases/signatures/SBOM/attestations remain missing or unaccepted. |
| Plugin-bundled binaries | `blocked` | Plugin binary inventory is not source/build/release trust; needs manifest, checksum/signature/SBOM/attestation, license, and rollback policy. |
| Production deployment | `blocked` | Requires production provenance, security review, observability, rollback, auth/network policy, and authority gate. |
| JSON-LD runtime import/export | `blocked` | M052 rejected current runtime support claim; no observed import/export/roundtrip path. |
| ACP-native JSON-LD projections | `out-of-scope` | ACP may keep native/static JSON-LD surfaces, but that is not git-lex runtime support. |
| SPARQL named graph queries used in bounded diagnostics | `L1-compatible` | Bounded query/query_json passed in M054 and S03 within predefined query IDs. |
| Broad SPARQL-star/RDF-star parity | `blocked` | Narrow history ASK/query evidence is not broad user-facing parity; requires source trace and runtime proof if claimed. |
| Arbitrary SPARQL pass-through | `rejected` | S02/S03 explicitly require predefined bounded query IDs only. |
| `git lex sync` in isolated backend workspace | `L1-compatible` | Proven through S02/S03 adapter path with no main state residue. |
| `git lex list --json` class inventory | `L1-compatible` | Proven as shape-driven diagnostic inventory, not ontology truth. |
| `git lex validate` behind wrapper gates | `L1-compatible` | Proven as fail-closed diagnostic with positive/negative synthetic fixtures; not requirement proof. |
| `git lex init` in controlled isolated workspace | `L1-compatible` | Proven for isolated workspace setup only; not main repo init. |
| `parse` diagnostic surface | `L2-candidate` | Runtime-backed as read-only prior smoke, but excluded from current L1 adapter; could be reconsidered only with bounded diagnostic contract. |
| `dump` diagnostic surface | `L2-candidate` | Optional diagnostic prior smoke exists, but excluded from current L1 because dump can emit broad graph content. Needs bounding/redaction. |
| `history-verify` | `L2-candidate` | Runtime-backed in isolated prior smoke but excluded from L1; may be useful only after bounded proof and retention policy. |
| `serve` / `viz` | `rehearsal-needed` | Local smoke exists, but auth/TLS/CSRF/external exposure, API gaps, rollback, and production policy are unproven. |
| `listen` | `rehearsal-needed` | Partial prior smoke only; kit-string mismatch observed; not adapter-safe. |
| `display` | `rehearsal-needed` | Depends on local `viz`; inherits server/API limitations. |
| `create` | `rehearsal-needed` | Runtime-backed but can generate invalid documents; not safe without scoped staging/validation/cleanup policy. |
| `save` | `blocked` | Broad staging/commit behavior and failure residue risk; not ACP-safe without scoped staging, rollback, redaction, and human adoption decision. |
| `join` | `rehearsal-needed` | Mutates two repos and leaves commit policy external; needs isolated multi-repo rehearsal if ever relevant. |
| `kit-update` | `blocked` | Network-dependent and mutates generated shapes/templates; not safe as implicit runtime step. |
| `raw backfill` | `rejected` | Copies raw harness payloads and uses per-machine state; nonfit for durable ACP proof anchors by default. |
| `raw` / raw session payloads | `rejected` | Session/provider/raw payloads risk secrets and personal data; excluded from ACP proof anchors by default. |
| `nuke` | `rejected` | Destructive and can attempt push; S02/S03 prove denylist rejection only. |
| Claude/session logs-to-git | `rejected` | Runtime-backed as harness prior art only; ACP-nonfit by default due prompt/tool/provider/secret risks. |
| Provider payload mirroring | `rejected` | Same raw-payload risk; not a durable proof anchor. |
| Real legal evidence ingestion | `out-of-scope` | Owned by law-nexus legal evidence/parser/retrieval proof, not git-lex diagnostics. |
| Russian legal evidence correctness | `out-of-scope` | Requires real-document/parser/retrieval/citation proof; not proven by git-lex runtime. |
| Garant ODT parser completeness | `out-of-scope` | Parser proof belongs to legal evidence slices; git-lex does not prove ODT parsing. |
| FalkorDB interaction | `out-of-scope` | FalkorDB ingestion/query/vector/full-text behavior needs FalkorDB runtime proof, not git-lex diagnostics. |
| R035 validation | `blocked` | Cannot be closed from git-lex/ACP projection diagnostics; requires its own accepted proof path. |
| R037 validation | `blocked` | Cannot be closed from git-lex/ACP projection diagnostics; requires its own accepted proof path. |
| R038 validation | `blocked` | Cannot be closed from git-lex/ACP projection diagnostics; requires its own accepted proof path. |
| Architecture registry decisions | `L2-candidate` | git-lex diagnostics can inform registry/verifier health but cannot replace accepted decisions/proof gates. |
| Security review for L2/production | `blocked` | Required before broader runtime/server/raw/production surfaces; not done in M055 through S03. |
| Observability/failure persistence | `L2-candidate` | ACP-facing diagnostics include classifications, but regular workflow retry/failure-state persistence is not yet proven. |
| Network exposure | `blocked` | Any server/listen/viz/public surface requires security/network/auth policy and isolated proof. |
| Secrets handling | `blocked` | Current policy avoids secrets; any surface touching raw/session/provider payloads requires explicit redaction policy and proof. |
| License and dependency review | `blocked` | Required before production/release/plugin adoption; not covered by S02/S03. |

## Detailed backlog by adoption area

### L1 continuation questions

| Question | Classification | Current answer | Next action |
|---|---|---|---|
| Can ACP keep using git-lex as shadow diagnostic/projection backend? | `L1-compatible` | Yes, within S02/S03 boundaries. | S05 may recommend continuing L1 while preparing L2 gates. |
| Can S03 diagnostics inform architecture verification? | `L1-compatible` | Yes as non-authoritative diagnostic input. | Keep `authority: non-authoritative-diagnostic`; never close requirements from diagnostics alone. |
| Can the adapter run bounded query/list/sync/validate diagnostics? | `L1-compatible` | Yes for proven synthetic ACP-shaped fixtures. | Keep allowlist and bounded query IDs. |

### L2 operational diagnostic backend questions

| Question | Classification | Why unresolved | Next action |
|---|---|---|---|
| Can ACP workflows invoke the adapter regularly? | `L2-candidate` | Adapter exists, but workflow integration/retry/retention not proven. | Define operational diagnostic integration proof. |
| Can diagnostics be retained, compacted, and indexed safely? | `L2-candidate` | JSONL exists, but lifecycle policy is not defined. | Specify retention/compaction/indexing policy. |
| Can failure states be persisted for unattended agents? | `L2-candidate` | Current diagnostics are per-run; retry/failure history is not yet operationalized. | Add failure-state contract and tests. |
| Can optional `parse`/`dump`/`history-verify` join L2 diagnostics? | `L2-candidate` | Prior smoke exists but current L1 excludes them. | Require bounded/redacted diagnostic contracts before adding. |

### Main `.lex` and state questions

| Question | Classification | Why unresolved | Next action |
|---|---|---|---|
| Can main `.lex` be initialized? | `rehearsal-needed` | No main-state rehearsal/rollback proof. | Separate isolated main-repo rehearsal milestone with explicit human decision. |
| Can generated sidecars be safely tracked/ignored? | `rehearsal-needed` | `.spo`, `.git/lex`, `.lex`, hooks, and generated files need policy. | Define tracked/ignored matrix and cleanup proof. |
| Can failed operations roll back cleanly? | `rehearsal-needed` | Save/create/validation failures can leave staged/generated residue. | Rehearse failure cleanup in disposable clone. |
| Can main `Squad`/`Raw` exist? | `blocked` / `rejected` for Raw | S02/S03 require absence; Raw is payload-risky. | Keep absent until explicit adoption decision; Raw remains rejected by default. |

### Authority and source-truth questions

| Question | Classification | Why unresolved | Next action |
|---|---|---|---|
| Can git-lex become ACP source truth? | `blocked` | Authority migration and conflict resolution are undefined. | Future authority migration design only after L2 stability. |
| Can RDF/SPARQL/SHACL projections validate requirements? | `blocked` | Derived projections are not proof gates by themselves. | Keep requirement validation ACP-native and evidence-specific. |
| Can git-lex diagnostics close R035/R037/R038? | `blocked` | Explicitly prohibited by S01/S02/S03 boundaries. | Use separate LegalGraph proof paths. |

### Provenance, release, and production questions

| Question | Classification | Why unresolved | Next action |
|---|---|---|---|
| Can D077 source-built binary support L1? | `L1-compatible` | Yes for local proof/shadow diagnostics. | Preserve pin unless update decision is recorded. |
| Can the pin be updated? | `rehearsal-needed` | Remote HEAD drift observed. | New decision, rebuild, hash, tests, runtime matrix. |
| Can release/plugin binaries be trusted? | `blocked` | Missing release manifest/signature/SBOM/attestation/source-build binding. | Provenance milestone required. |
| Can git-lex run in production ACP workflows? | `blocked` | Needs provenance, security, rollback, observability, authority gates. | Production adoption milestone required after L2. |

### Semantic interoperability questions

| Question | Classification | Why unresolved | Next action |
|---|---|---|---|
| Can bounded SPARQL diagnostics continue? | `L1-compatible` | Proven for predefined query IDs. | Keep bounded allowlist. |
| Can arbitrary SPARQL be exposed? | `rejected` | Too broad; risk of unbounded data/query behavior. | Do not expose; add query IDs deliberately. |
| Can JSON-LD runtime import/export be claimed? | `blocked` | M052 found no observed runtime path. | Source trace and isolated import/export/roundtrip proof required if revisited. |
| Can broad SPARQL-star/RDF-star parity be claimed? | `blocked` | Narrow evidence only; no broad parity proof. | Dedicated source/runtime proof if needed. |

### Payload, security, and legal evidence questions

| Question | Classification | Why unresolved | Next action |
|---|---|---|---|
| Can real legal text enter git-lex diagnostics? | `out-of-scope` / `blocked for M055` | Legal evidence correctness/parser proof is separate. | Keep S03 synthetic-only; route legal proof elsewhere. |
| Can session logs or provider payloads be proof anchors? | `rejected` | Raw logs risk secrets/personal/provider data. | Keep rejected unless explicit redaction/proof policy is accepted. |
| Can server/viz/listen be used operationally? | `rehearsal-needed` | Local smoke only; security/network gaps. | Security review and isolated server proof required. |
| Is FalkorDB behavior proven by git-lex? | `out-of-scope` | Different runtime; no FalkorDB proof. | Use FalkorDB-specific source/runtime evidence. |

## Proof-gate matrix

This matrix converts the T01 backlog into promotion gates. It is intentionally stricter than the S03 proof: existing L1 diagnostics can continue, but every stronger backend role needs explicit evidence, failure classification, and follow-up routing before adoption.

### Proof class definitions

| Proof class | Required evidence shape |
|---|---|
| `policy-boundary` | Tracked architecture/decision artifact that states the allowed boundary and preserves ACP authority hierarchy. |
| `contract-test` | Automated tests over the adapter or ACP workflow contract, including negative/failure cases. |
| `isolated-runtime` | Reproducible runtime run in a disposable workspace outside the main checkout, with tracked bounded diagnostics. |
| `isolated-rehearsal` | Disposable clone/workspace rehearsal of stateful or mutating behavior, including cleanup and rollback evidence. |
| `provenance-review` | Source/build/release/license/SBOM/signature/attestation evidence tied to a pinned binary or accepted risk decision. |
| `security-review` | Threat model and verification for network, auth, local server, secret, payload, and destructive-command risk. |
| `profile-proof` | Separate law-nexus profile proof for Russian legal evidence, FalkorDB, parser, retrieval, or requirement validation. |
| `rejection-policy` | Explicit denylist/policy proof that a surface is intentionally unavailable or nonfit for ACP. |

### Gate matrix

| Surface | Required evidence type | Proof class | Minimum verification command/evidence | Adoption level affected | Failure classification | M055 or follow-up location |
|---|---|---|---|---|---|---|
| L1 shadow diagnostic/projection continuation | S02/S03 adapter contract and diagnostics retained as non-authoritative evidence. | `policy-boundary` + `isolated-runtime` | Existing S03 diagnostics plus `test ! -e .lex && test ! -e Squad && test ! -e Raw`; diagnostics keep `authority: non-authoritative-diagnostic`. | L1 continuation | `blocked-if-authority-inversion` | Inside M055; S05 decision synthesis. |
| Internal adapter invocation in ACP workflows | Workflow integration design, invocation contract, retry behavior, and failure-state tests. | `contract-test` | `uv run pytest tests/test_acp_git_lex_backend.py` plus future ACP workflow integration tests that assert fail-closed diagnostics. | L2 operational diagnostic | `defer-to-L2-if-unintegrated` | Follow-up L2 diagnostic integration milestone. |
| Durable bounded diagnostics JSONL | Repository-relative diagnostics path and schema/field policy. | `contract-test` | JSONL schema check over `prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl`; assert no raw stdout/stderr/private payload fields. | L1 continuation / L2 retention | `blocked-if-unbounded-payload` | Inside M055 for current file; follow-up for lifecycle policy. |
| Diagnostic storage/retention policy | Retention, compaction, indexing, privacy, and lifecycle specification. | `policy-boundary` + `contract-test` | Tracked policy artifact and tests that reject ignored paths, `.gsd/exec`, raw payloads, and absolute anchors as durable proof. | L2 operational diagnostic | `defer-if-no-retention-policy` | Follow-up ACP observability/storage slice. |
| Main repository `.lex` | Explicit human adoption decision, isolated main-repo rehearsal, tracked/ignored policy, rollback plan. | `isolated-rehearsal` + `policy-boundary` | Disposable clone proof: init/sync/failure/cleanup; pre/post `test ! -e /root/law-nexus/.lex`; diff/status audit showing no main mutation. | Main `.lex` rehearsal | `blocked-without-human-decision` | Follow-up main-state rehearsal milestone; not inside M055. |
| Main repository `Squad` / `Raw` | Explicit adoption decision and payload policy; Raw requires redaction/secret handling proof. | `security-review` + `rejection-policy` | Pre/post `test ! -e Squad && test ! -e Raw`; any proposed Raw proof must demonstrate sanitized fixtures only and no provider/session payload leakage. | Main-state adoption / payload policy | `blocked-or-rejected-payload-risk` | Blocked; Raw remains rejected by default. |
| Source truth migration | Authority model, conflict resolution, lifecycle mapping, migration rehearsal, and accepted decision. | `policy-boundary` + `isolated-rehearsal` | Migration fixture proves ACP-native source records remain authoritative until accepted proof gates promote them; verifier rejects projection-only authority. | Source-truth backend | `blocked-authority-inversion` | Future authority migration milestone after L2. |
| ACP source-record lifecycle authority | Source category/lifecycle/evidence/proof-gate contract tied to accepted decisions. | `policy-boundary` + `contract-test` | Architecture verifier tests that Turtle/JSON-LD/SPARQL results alone cannot validate a requirement. | Source-truth backend / verifier | `blocked-if-shape-implies-authority` | Follow-up architecture verifier work. |
| Rollback and state cleanup | Stateful failure rehearsal for `.lex`, `.git/lex`, sidecars, hooks, commits, staged files, and server processes. | `isolated-rehearsal` | Disposable clone script records before/after `git status --short`, generated paths, failed validation residue, and cleanup result. | Main `.lex` / L2 mutating helpers | `blocked-if-residue-remains` | Follow-up main-state rehearsal milestone. |
| Pinned source-built debug binary | Source commit, lockfile hash, binary hash/help identity, and local proof-only boundary. | `provenance-review` | Existing pinned D077/M054 identity plus help/version evidence; preserve source-built debug-only status. | L1 runtime diagnostics | `blocked-if-binary-identity-missing` | Inside M055 as existing boundary; no production promotion. |
| Updating git-lex source pin | Pin-vs-update decision, rebuild, binary identity, regression matrix, and drift rationale. | `provenance-review` + `isolated-runtime` | Rebuild from selected commit, record lockfile/binary hashes, rerun M054/M055 adapter tests and S03-style matrix. | L1/L2 runtime diagnostics | `blocked-if-unreviewed-drift` | Follow-up pin-update slice only after decision. |
| Release binaries | Release artifact, source/build binding, checksum/signature/SBOM/attestation or accepted absence decision. | `provenance-review` | Verify release URL/tag/source commit/build workflow/hash/signature/SBOM; compare clean-room build if required. | Production/provenance | `blocked-provenance-missing` | Follow-up production provenance milestone. |
| Plugin-bundled binaries | Bundle manifest, binary hash, source mapping, license, update channel, rollback, and trust decision. | `provenance-review` + `security-review` | Inventory plugin binary hash and prove source/release binding; record accepted risk or reject. | Production/provenance | `blocked-bundled-binary-untrusted` | Follow-up provenance/security milestone. |
| Production deployment | Production provenance, security review, observability, rollback, auth/network, and authority gates. | `provenance-review` + `security-review` + `contract-test` | Full production readiness checklist; tests for fail-closed behavior, no authority inversion, and cleanup/rollback. | Production backend | `blocked-production-unready` | Future production adoption milestone only. |
| JSON-LD runtime import/export | Source trace and isolated import/export/roundtrip proof if this capability is claimed. | `isolated-runtime` | Concrete command/API proof that JSON-LD is parsed/emitted as RDF, with roundtrip fixture and negative malformed fixture. | Semantic interoperability | `blocked-unproven-runtime-capability` | Follow-up only if JSON-LD runtime is needed. |
| ACP-native JSON-LD projections | ACP-native projection contract and verifier boundary. | `policy-boundary` | ACP projection tests; explicitly state not git-lex runtime evidence. | ACP-native interoperability | `out-of-scope-for-git-lex-runtime` | Outside git-lex adoption; ACP projection work. |
| SPARQL named graph queries used in bounded diagnostics | Predefined query IDs, expected result schema, and bounded output checks. | `contract-test` + `isolated-runtime` | Adapter tests for bounded query/query_json; reject unknown query IDs. | L1/L2 diagnostics | `blocked-if-query-unbounded` | Inside M055 as current L1; L2 can expand only by adding IDs. |
| Broad SPARQL-star/RDF-star parity | Source trace plus explicit user-facing query/runtime compatibility proof. | `isolated-runtime` | Dedicated fixture with quoted triples/SPARQL-star queries and expected results; negative unsupported query behavior. | Semantic interoperability | `blocked-broad-parity-unproven` | Follow-up semantic runtime proof if required. |
| Arbitrary SPARQL pass-through | Denylist/allowlist policy and adapter rejection tests. | `rejection-policy` + `contract-test` | Test unknown/unbounded query attempts return `rejected` without execution. | Diagnostics safety | `rejected-by-policy` | Inside M055 denylist; no adoption route by default. |
| `git lex sync` in isolated backend workspace | Isolated workspace run, tracked bounded diagnostics, no main residue. | `isolated-runtime` | Existing S03 matrix plus no-main-state checks before/after. | L1 diagnostics | `blocked-if-main-state-mutates` | Inside M055 L1. |
| `git lex list --json` class inventory | Shape-driven inventory contract; no ontology-truth overclaim. | `contract-test` | Tests assert parsed class inventory and non-authoritative classification. | L1 diagnostics | `blocked-if-treated-as-ontology-truth` | Inside M055 L1. |
| `git lex validate` behind wrapper gates | Positive and negative fixtures, expected file counts, setup/shape/parser failures as hard failures. | `contract-test` + `isolated-runtime` | Adapter tests for positive pass and concrete SHACL negative diagnostic; assert ambiguous setup errors do not become pass. | L1 diagnostics / L2 validation diagnostics | `blocked-if-fail-open` | Inside M055 for current wrapper; L2 for workflow integration. |
| `git lex init` in controlled isolated workspace | Disposable workspace setup proof with cleanup and no main residue. | `isolated-runtime` | Pre/post no-main-state checks; workspace path outside checkout; cleanup evidence. | L1 diagnostics / main rehearsal prerequisite | `blocked-if-main-init` | Inside M055 for isolated use; main init follow-up only. |
| `parse` diagnostic surface | Bounded read-only parse contract and output redaction policy. | `contract-test` + `isolated-runtime` | Isolated fixture proving parse emits bounded diagnostics without raw legal/session payloads. | L2 optional diagnostic | `defer-if-unbounded-output` | Follow-up L2 diagnostic expansion. |
| `dump` diagnostic surface | Redaction, graph-size bound, path/payload policy, and retention limits. | `security-review` + `contract-test` | Fixture proves dump output is bounded or rejected; no private raw fields in durable artifact. | L2 optional diagnostic | `blocked-if-broad-graph-leak` | Follow-up only after redaction policy. |
| `history-verify` | Bounded history equivalence contract and repository-state prerequisites. | `isolated-runtime` | Disposable committed/synced repo proving expected pass/fail and no main residue. | L2 optional diagnostic | `defer-if-history-preconditions-unclear` | Follow-up L2 diagnostic expansion. |
| `serve` / `viz` | Local-server threat model, auth/network policy, API gap handling, process lifecycle, rollback. | `security-review` + `isolated-runtime` | Browser/API proof on loopback plus no console/network failures accepted by policy; verify server cleanup. | Server diagnostics / production-adjacent | `blocked-server-security` | Follow-up security/server milestone; not M055. |
| `listen` | Kit-string compatibility proof, event contract, auth/network policy, process lifecycle. | `security-review` + `isolated-runtime` | Isolated listener proof with standard init kit string, `/notify` and `/events`, cleanup, and no external bind. | Server diagnostics | `blocked-partial-runtime-proof` | Follow-up server milestone. |
| `display` | Dependency on `viz` API and bounded local client behavior. | `isolated-runtime` + `security-review` | Local `viz`/`display` fixture with route compatibility and no broad exposure. | Server/client diagnostics | `defer-viz-dependency` | Follow-up with `serve`/`viz`. |
| `create` | Scoped workspace, generated-document validity, staged-file policy, and cleanup on invalid output. | `isolated-rehearsal` + `contract-test` | Disposable repo proof that create output is validated or cleaned; before/after `git status --short`. | Mutating workflow helper | `blocked-if-invalid-or-residue` | Follow-up mutating-helper rehearsal. |
| `save` | Scoped staging, commit policy, validation gates, rollback, redaction, and human adoption decision. | `isolated-rehearsal` + `security-review` | Disposable repo proof covering successful save and failed validation residue cleanup; no raw/session payload commit. | Mutating workflow helper / source truth risk | `blocked-broad-staging-risk` | Blocked until dedicated rehearsal and decision. |
| `join` | Multi-repo mutation policy, commit ownership, rollback, and evidence retention. | `isolated-rehearsal` | Two-disposable-repo proof with before/after status and cleanup; no main repo mutation. | Multi-repo workflow helper | `defer-multi-repo-policy` | Follow-up only if ACP needs it. |
| `kit-update` | Network/update policy, source pin decision, diff review, rollback, and generated-shape compatibility proof. | `provenance-review` + `isolated-rehearsal` | Isolated update fixture; capture network source, generated diffs, tests, rollback. | Update/provenance | `blocked-implicit-network-mutation` | Blocked by default; follow-up update policy. |
| `raw backfill` | Explicit rejection or sanitized-payload policy with per-machine state controls. | `rejection-policy` + `security-review` | Denylist test rejects operation; if ever revisited, sanitized-only fixture and no durable raw payload anchors. | Payload/raw workflow | `rejected-payload-risk` | Rejected by default. |
| `raw` / raw session payloads | Redaction/secret policy, consent/retention model, provider payload filtering, and proof-anchor rules. | `security-review` + `rejection-policy` | Current minimum is denylist proof and no `Raw` path; future proof would need sanitizer tests and secret canaries. | Payload policy / proof anchors | `rejected-secret-and-privacy-risk` | Rejected by default; security milestone only if reversed. |
| `nuke` | Destructive-command rejection and remote/push safety policy. | `rejection-policy` + `contract-test` | Adapter denylist test returns `rejected` without execution; no remote/destructive command invoked. | Destructive operations | `rejected-destructive` | Inside M055 denylist; no adoption route by default. |
| Claude/session logs-to-git | ACP-nonfit policy plus optional redaction proof if later reversed. | `rejection-policy` + `security-review` | Current proof: deny as ACP proof anchor; no raw log files tracked; no provider payloads in diagnostics. | Payload/provenance | `rejected-by-default` | Rejected by default. |
| Provider payload mirroring | Secret/privacy policy and sanitizer/retention proof if ever allowed. | `security-review` + `rejection-policy` | Current proof: no provider payload fields in durable diagnostics and no `Raw` directory. | Payload/provenance | `rejected-secret-risk` | Rejected by default. |
| Real legal evidence ingestion | Real-document parser/retrieval proof outside git-lex; legal evidence anchors. | `profile-proof` | Separate law-nexus real-document tests and citation-safe retrieval evidence; git-lex diagnostics cannot satisfy this. | Legal evidence profile | `out-of-scope-for-git-lex` | Legal evidence/parser milestone, not M055. |
| Russian legal evidence correctness | Legal interpretation/evidence/citation proof path. | `profile-proof` | Requirement-specific legal evidence validation with accepted anchors; not S03 synthetic diagnostics. | LegalGraph profile | `out-of-scope-for-git-lex` | Legal evidence milestone. |
| Garant ODT parser completeness | Parser fixtures over real Garant ODT documents. | `profile-proof` | Parser tests against tracked ODT fixtures and structural/citation assertions. | Parser/profile | `out-of-scope-for-git-lex` | Parser milestone. |
| FalkorDB interaction | FalkorDB runtime/source proof for ingestion/query/index behavior. | `profile-proof` | FalkorDB smoke/source tests and graph assertions; no git-lex evidence substitution. | Graph runtime/profile | `out-of-scope-for-git-lex` | FalkorDB-specific milestone. |
| R035 validation | Requirement-specific proof anchored outside git-lex projections. | `profile-proof` + `policy-boundary` | Requirement validation artifact must cite accepted proof gates; verifier rejects projection-only validation. | Requirement validation | `blocked-requirement-overclaim` | Future R035 proof path; not M055. |
| R037 validation | Requirement-specific proof anchored outside git-lex projections. | `profile-proof` + `policy-boundary` | Same as R035: accepted source/runtime/profile evidence required. | Requirement validation | `blocked-requirement-overclaim` | Future R037 proof path; not M055. |
| R038 validation | Requirement-specific proof anchored outside git-lex projections. | `profile-proof` + `policy-boundary` | Same as R035: accepted source/runtime/profile evidence required. | Requirement validation | `blocked-requirement-overclaim` | Future R038 proof path; not M055. |
| Architecture registry decisions | Registry/verifier policy for using diagnostics as health input only. | `policy-boundary` + `contract-test` | Verifier tests that diagnostics can flag health but accepted decisions/proof gates remain authoritative. | Architecture governance / L2 diagnostic input | `blocked-if-diagnostic-becomes-decision` | Follow-up architecture verifier slice. |
| Security review for L2/production | Threat model for adapter, server, raw payloads, destructive commands, secrets, and network. | `security-review` | Filing-ready security report with mitigations and tests before enabling broader surfaces. | L2/production/security-sensitive surfaces | `blocked-security-unreviewed` | Follow-up security milestone. |
| Observability/failure persistence | Durable failure-state contract: phase, classification, timestamp, retry count, bounded stderr digest. | `contract-test` | Tests that failed adapter runs persist structured non-secret failure state and remain fail-closed. | L2 operational diagnostic | `defer-if-failure-state-missing` | Follow-up observability slice. |
| Network exposure | Loopback-only/default-deny network policy, auth/CSRF/TLS decision, process lifecycle. | `security-review` + `isolated-runtime` | Server proof verifies bind address, routes, auth policy, shutdown, and no external exposure. | Server/production | `blocked-network-policy-missing` | Follow-up security/server milestone. |
| Secrets handling | Secret redaction policy, canary tests, payload bans, and durable artifact scan. | `security-review` + `contract-test` | Canary-based tests prove diagnostics/artifacts do not include secrets or provider payloads. | L2/production/payload surfaces | `blocked-secret-policy-missing` | Follow-up security/observability milestone. |
| License and dependency review | License/dependency inventory tied to source/build/release and accepted risk decision. | `provenance-review` | Tracked review of git-lex, kits, plugin bundles, dependencies, and redistribution constraints. | Production/provenance | `blocked-license-review-missing` | Follow-up production provenance milestone. |

### T02 gate conclusions

```text
S04/T02 disposition: proof-gate-matrix-ready
proof classes defined: policy-boundary, contract-test, isolated-runtime, isolated-rehearsal, provenance-review, security-review, profile-proof, rejection-policy
L1 gates handled inside M055: bounded shadow diagnostics, adapter allowlist, bounded JSONL, pinned source-built debug binary boundary, denylist rejection
L2 gates requiring follow-up: workflow invocation, retention, failure persistence, optional bounded parse/dump/history diagnostics, architecture verifier diagnostic input
main-state gates requiring follow-up: main .lex rehearsal, generated sidecar policy, rollback/state cleanup, Squad/Raw policy
blocked promotion gates: source truth migration, production, release/plugin binaries, JSON-LD runtime, broad SPARQL-star, R035/R037/R038, server/network/security-sensitive surfaces
rejected gates: arbitrary SPARQL pass-through, nuke, raw backfill, raw/session/provider payload proof anchors, logs-to-git by default
out-of-scope gates: Russian legal evidence correctness, Garant ODT parser completeness, FalkorDB runtime behavior
T03 readiness: ready to finalize follow-up adoption route and S05 inputs
```

## Follow-up adoption route

### Current M055 scope

M055 should close with a bounded backend adoption decision, not another runtime expansion. The current milestone scope is:

| Area | Decision for M055 | Reason |
|---|---|---|
| L1 shadow diagnostic backend | Keep as proven and usable for non-authoritative diagnostics. | S02/S03 prove bounded ACP-shaped diagnostics with no main-state residue. |
| L2 operational diagnostic backend | Candidate only; do not promote inside M055. | Workflow integration, retention, failure persistence, and observability are not yet proven. |
| Main `.lex` rehearsal | Follow-up only; do not start in M055. | Needs explicit human adoption decision, isolated main-repo rehearsal, rollback, and state policy. |
| Production/provenance hardening | Follow-up only; do not claim in M055. | Release/plugin binaries, SBOM/signature/attestation/license/security evidence remain missing. |
| Source-truth migration | Blocked. | ACP-native records remain authoritative; authority/conflict/migration gates are not designed. |
| Stop/rollback option | Keep available but not selected by S04 alone. | S04 identifies many blockers, but S02/S03 evidence is useful enough to continue L1 diagnostics. |

### Recommended S05 decision options

S05 should evaluate these options in this order and choose exactly one primary next move:

| Option | Minimum evidence threshold | S04 assessment | Likely S05 disposition |
|---|---|---|---|
| Continue L1 shadow diagnostics | S02 adapter + S03 runtime matrix + S04 gate matrix, all preserving non-authority and no main state. | Threshold met. | Strong default recommendation. |
| Promote to L2 operational diagnostic backend | L1 evidence plus workflow invocation, retention, failure persistence, and fail-closed operational tests. | Threshold not met. | Recommend as next follow-up, not current promotion. |
| Plan isolated main `.lex` rehearsal | Explicit human decision plus state/rollback/sidecar policy and disposable clone rehearsal plan. | Threshold not met. | Candidate follow-up after L2 or as a separately approved rehearsal track. |
| Harden production/provenance | Release/source/build/SBOM/signature/license/security evidence and rollback plan. | Threshold not met. | Future provenance milestone only. |
| Stop git-lex backend adoption | Evidence that L1 diagnostics provide insufficient value or risks exceed current benefits. | Threshold not met. | Not favored by S04; L1 remains useful and bounded. |

### Next-milestone candidates

These are candidate tracks only; S04 does not create new milestones or assign IDs.

| Candidate track | Purpose | Entry criteria | Exit evidence |
|---|---|---|---|
| L2 operational diagnostic integration | Wire the S02 adapter into a regular ACP diagnostic workflow while staying non-authoritative. | S05 selects “continue L1 and prepare L2”; no main `.lex`; adapter tests pass. | Workflow invocation tests, failure-state persistence, retention policy, bounded diagnostics scan. |
| Main `.lex` rehearsal | Rehearse main-repo-like state in a disposable clone without mutating `/root/law-nexus`. | Explicit human adoption decision and L2 boundary accepted. | Init/sync/failure/cleanup rehearsal, sidecar tracked/ignored policy, rollback proof, no main residue. |
| Production provenance and binary trust | Decide whether any source-built, release, or plugin-bundled binary can be trusted beyond proof-only diagnostics. | Need production intent; current L1/L2 value established. | Source/build/release manifest, hashes, license/dependency review, SBOM/signature/attestation or accepted absence decision. |
| Security and network surfaces | Evaluate `serve`/`viz`/`listen`, raw payloads, secrets, and local network exposure. | Explicit desire to use server/payload surfaces. | Threat model, loopback/auth/CSRF/TLS/process lifecycle proof, secret canary tests, rejection or scoped enablement decision. |
| Semantic runtime interoperability | Revisit JSON-LD runtime or broad SPARQL-star/RDF-star only if product need appears. | Specific semantic-interoperability requirement. | Source trace and isolated import/export/roundtrip or quoted-triple query proof; otherwise remains blocked. |
| LegalGraph profile proof | Validate Russian legal evidence, Garant ODT parser, FalkorDB behavior, and R035/R037/R038 through their own proof paths. | Requirement-specific LegalGraph need. | Profile/runtime/parser/retrieval/FalkorDB evidence; no substitution from git-lex diagnostics. |

### Blocked and rejected list

Surfaces that S05 must keep blocked unless a later explicit decision and proof path reverses them:

```text
blocked: source truth migration; ACP lifecycle authority transfer; main .lex adoption without rehearsal and human decision; production deployment; release/plugin binaries including release binaries and plugin-bundled binaries; JSON-LD runtime support; broad SPARQL-star/RDF-star parity; save as ACP-safe primitive; kit-update as implicit runtime step; R035/R037/R038 validation from projections; server/network/security-sensitive surfaces without review; secrets handling without canary/redaction proof; license/dependency production adoption without review
rejected by default: arbitrary SPARQL pass-through; nuke; raw backfill; raw/session/provider payload proof anchors; Claude/session logs-to-git as ACP proof; provider payload mirroring; Raw in main repo without explicit redaction and consent policy
out of scope for git-lex adoption: Russian legal evidence correctness; Garant ODT parser completeness; FalkorDB runtime behavior; real legal payload ingestion; law-nexus citation/retrieval quality
```

### S05 handoff

S05 should consume S04 with these concrete inputs:

1. **Evidence coverage:** L1 shadow diagnostics are proven enough to continue; stronger adoption is not proven.
2. **Primary recommendation candidate:** continue L1 and plan a follow-up L2 operational diagnostic integration track.
3. **Rejected current promotions:** do not promote to main `.lex`, source-truth backend, production backend, release/plugin binary adoption, JSON-LD runtime support, broad SPARQL-star parity, or R035/R037/R038 validation.
4. **Decision ledger thresholds:** use the five S05 options above and require each option to cite its minimum evidence threshold before selection.
5. **No-main-state invariant:** S05 must preserve `test ! -e .lex`, `test ! -e Squad`, and `test ! -e Raw` as hard verification gates.
6. **Durable guidance check:** S05/T03 should update git-lex reference guidance only if final synthesis changes reusable boundaries; S04 itself introduces no new runtime-backed capability beyond the existing L1 proof.

### T03 route conclusions

```text
S04/T03 disposition: follow-up-adoption-route-ready
current-M055 scope: close with bounded next-decision synthesis, not runtime expansion
primary S05 input: continue L1 shadow diagnostics and prepare L2 operational diagnostic follow-up
next-milestone candidates: L2 operational diagnostic integration; main .lex rehearsal; production provenance and binary trust; security and network surfaces; semantic runtime interoperability; LegalGraph profile proof
blocked list: source-truth migration, main .lex without rehearsal/decision, production, release/plugin binaries, JSON-LD runtime, broad SPARQL-star, R035/R037/R038, security/network/secrets/license-sensitive promotions
rejected list: arbitrary SPARQL pass-through, nuke, raw backfill, raw/session/provider payload proof anchors, logs-to-git as ACP proof, provider payload mirroring
S05 handoff: use five decision options, select one primary next move, preserve no-main-state invariant, and do not overclaim beyond L1
```

## T01 disposition

```text
S04/T01 disposition: remaining-adoption-question-backlog-ready
covered surfaces: main .lex, source truth, rollback/state, provenance/release, plugin binaries, JSON-LD runtime, SPARQL-star breadth, logs-to-git, server/viz/listen, raw/session payloads, real legal evidence, FalkorDB interaction, R035/R037/R038, security, production
classification vocabulary: specified
L1-compatible surfaces: bounded shadow diagnostics, adapter operations, bounded diagnostics JSONL, pinned source-built binary for L1
L2-candidate surfaces: operational workflow invocation, retention/failure persistence, optional bounded diagnostics, architecture verifier input
rehearsal-needed surfaces: main .lex, rollback/state, source pin update, serve/viz/listen, create/join/display
blocked surfaces: source truth migration, production, release/plugin binaries, JSON-LD runtime, broad SPARQL-star, R035/R037/R038, security-sensitive surfaces
rejected surfaces: arbitrary SPARQL, raw/session/provider payload proof anchors, nuke, raw backfill, logs-to-git by default
out-of-scope surfaces: real legal evidence correctness, Garant parser, FalkorDB runtime behavior
T02 readiness: ready to convert backlog into proof-gate matrix
```
