# M053 S06 Minimal ACP Adapter Boundary Contract

## Status

In progress for `M053-2jp3nm / S06`.

S06 synthesizes S02-S05 into a minimal ACP adapter boundary. It is not an implementation plan and not a production adoption decision. The goal is to decide which git-lex surfaces are candidate adapter-later diagnostics, which are ACP-native only, and which are excluded by default.

## Guardrails

- ACP remains source of truth.
- git-lex output remains derived diagnostic/recovery evidence unless a later explicit adoption decision changes that boundary.
- Main repository `.lex`, `Squad`, and `Raw` must remain absent.
- No production adoption, release/binary trust, or main `.lex` adoption is approved by S06.
- R035/R037/R038 are not validated by git-lex, RDF, SHACL, SPARQL, JSON-LD, Raw logs, or this contract.
- Raw session logs and provider payloads are not durable ACP proof anchors by default.

## T01: Evidence include/exclude ledger

### Evidence inputs

| Slice | Artifact | Result consumed by S06 |
|---|---|---|
| S02 | `prd/architecture/acp/M053-S02-SHACL-FAIL-CLOSED-WRAPPER.md` | Wrapper-backed SHACL validation can be adapter-later diagnostic for counted shape-derived validations in isolated workspaces. Raw `git-lex validate` remains blocked as standalone ACP gate. |
| S03 | `prd/architecture/acp/M053-S03-SPARQL-STAR-BOUNDARY.md` | Narrow history graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK support confirmed; triple JSON is non-standard; broad RDF-star parity remains blocked. |
| S04 | `prd/architecture/acp/M053-S04-JSON-LD-BRIDGE-RECHECK.md` | git-lex JSON-LD RDF import/export rejected; `.jsonld` metadata only; ACP-native static JSON-LD bridge preserved. |
| S05 | `prd/architecture/acp/M053-S05-CLAUDE-LOGS-GIT-OPS-NONFIT.md` | Claude/session logs-to-git feature runtime-backed as git-lex harness feature but ACP-nonfit by default. |

### Include/exclude ledger

| Surface | Evidence | S06 disposition | Reason |
|---|---|---|---|
| `init` in isolated workspace | M051/M052 runtime smoke; S01 source recheck | `include-candidate` | Required only to create disposable proof workspace; not main repo adoption. |
| `sync` in isolated workspace | M051/M052 runtime smoke | `include-candidate` | Needed to materialize derived graph diagnostics from isolated data. |
| `list --json` | M051/M052 runtime smoke | `include-candidate` | Shape-driven class discovery; useful for diagnostics, not ontology truth. |
| `query` with bounded templates | S03 | `include-candidate` | Only history graph SELECT/ASK templates and ordinary bounded diagnostic queries. |
| `query --json` triple bindings | S03 | `adapter-later with normalization` | Non-standard `type: triple` JSON must be normalized or kept internal. |
| `validate` behind wrapper | S02 | `include-candidate with wrapper gates` | Usable only with expected-shape and expected-file coverage checks. |
| raw `git-lex validate` | S02 | `exclude` | Fails open/skips missing kit, missing shapes, malformed YAML, parser/load/setup errors. |
| JSON-LD RDF import/export | S04 | `exclude` | No source/help/runtime route found. |
| `.jsonld` file metadata | S04 | `metadata-only` | Can be observed as git file language, not RDF body import. |
| ACP JSON-LD bridge | S04 | `ACP-native-only` | Static/prototype interchange may remain ACP-owned, not git-lex runtime. |
| Claude/session logs-to-git Raw mirror | S05 | `exclude by default` | Raw payload, privacy, machine-local state, broad commit behavior, no ACP mapping. |
| `git lex save` | S05 + M052 S05 | `exclude by default` | Broad `git add -A` and commit side effects; not scoped adapter primitive. |
| `create` | M052 S05 | `exclude by default` | Can generate SHACL-invalid templates; mutates working tree. |
| `raw backfill` | M052 S05 + S05 | `exclude by default` | Copies raw harness payloads and uses machine-local state. |
| `join` | M052 S05 | `exclude by default` | Mutates two repositories and leaves commit policy external. |
| `kit-update` | M052 S05 | `blocked/update-only` | Network/scaffold/shape mutation; not implicit adapter step. |
| `nuke` | M052 S05 | `rejected` | Destructive `.lex`/`.git/lex` removal, commit, attempted push. |
| `serve` / `viz` / `listen` | M052 S04, S01 | `defer / non-core diagnostic` | Local UI/server diagnostics only; `/api/store-info` and listen kit mismatch unresolved. |
| production/bundled binaries | M052 S06, S01 | `blocked` | Provenance, release, signature/SBOM/attestation/version gates missing. |
| main repository `.lex` | M048/M051/M052/M053 boundaries | `blocked` | Requires explicit adoption decision and rollback/state policy. |

### Minimal ACP-useful candidate set

S06 can preserve only this candidate set for a future adapter-later spike:

```text
init in isolated workspace
sync in isolated workspace
list --json
query / query --json with bounded templates
validate behind fail-closed wrapper gates
```

Everything else is excluded, blocked, deferred, or ACP-native-only.

### T01 conclusion

The minimal adapter boundary is narrow. It is not a git-lex adoption path; it is a diagnostic-only, isolated, non-authoritative candidate surface. S02 and S03 provide the only currently ACP-relevant git-lex diagnostics. S04 and S05 primarily define non-goals and exclusions.

## T02: Minimal adapter boundary contract

### Contract status

```text
contract_status: adapter-later candidate
implementation_status: not implemented
production_status: blocked
main_repo_lex_status: blocked
ACP_authority_status: unchanged; ACP-native source truth remains authoritative
```

### Allowed command surface

| Command | Allowed? | Required wrapper/policy |
|---|---:|---|
| `git-lex --help` / `git-lex <cmd> --help` | yes | Read-only capability discovery only. |
| `git-lex init` | yes, isolated only | Must run in disposable or explicit isolated workspace; never main checkout. |
| `git-lex sync` | yes, isolated only | Must run after controlled fixture/source material is placed in isolated workspace. |
| `git-lex list --json` | yes | Treat as shape-driven class metadata, not ontology/source truth. |
| `git-lex query` | yes, bounded | Only bounded diagnostic templates; preserve raw query, exit, result count. |
| `git-lex query --json` | yes, bounded | Normalize/label non-standard `type: triple` bindings; do not claim generic JSON-LD. |
| `git-lex validate` | yes, wrapper only | Must enforce S02 fail-closed wrapper checks. |
| `git-lex dump` | optional diagnostic | Only in isolated workspace; output may be large and derived. |
| `git-lex history-verify` | optional diagnostic | Only in isolated workspace; equivalence diagnostic, not ACP proof gate. |

### Denylist and non-goals

| Surface | Status | Reason |
|---|---|---|
| main repo `.lex` | denied | No adoption decision, rollback/state policy, or production gate. |
| `git lex save` | denied by default | Broad `git add -A` + commit behavior; raw payload risk. |
| Claude/session Raw mirror | denied by default | ACP-nonfit unless later explicit privacy/proof/scoped-staging policy exists. |
| `raw backfill` | denied by default | Raw harness payloads and machine-local state. |
| `create` | denied by default | Mutates working tree and can create SHACL-invalid templates. |
| `join` | denied by default | Mutates two repositories. |
| `kit-update` | denied by default | Network/scaffold/shape mutation. |
| `nuke` | rejected | Destructive removal/commit/push-attempt behavior. |
| JSON-LD import/export | rejected | No source/help/runtime route. |
| broad RDF-star/SPARQL-star parity | blocked | Only narrow history graph SELECT/ASK is proven. |
| serve/viz/listen production use | deferred | Browser/server gaps and production hardening remain unresolved. |
| production/bundled binaries | blocked | Provenance/release/signature/SBOM/attestation/version gates missing. |

### SHACL wrapper gates

A future adapter may call `git-lex validate` only if it records and enforces:

1. isolated workspace path;
2. expected shape file paths;
3. expected fixture/document paths;
4. raw git-lex exit code;
5. parsed `Validated N files` count;
6. expected-count versus observed-count comparison;
7. setup/parse/load/schema/compile/processor diagnostics scan;
8. classification: `pass`, `git-lex-fail`, `wrapper-fail`, `blocked`, or `rejected`;
9. before/after main checkout safety checks.

Raw `git-lex validate` output is not sufficient as ACP proof.

### Query gates

A future adapter may expose only bounded query diagnostics:

1. ordinary read-only SELECT/ASK diagnostics over isolated store;
2. history graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK patterns proven by S03;
3. `query --json` results, with explicit warning that triple bindings use git-lex diagnostic JSON, not standard SPARQL 1.1 JSON and not JSON-LD.

The adapter must not expose quoted-subject, nested quoted-triple, legacy no-parentheses, CONSTRUCT, DESCRIBE, or broad RDF-star parity as supported surfaces without new fixture-backed proof.

### Structured log contract

Every adapter operation must emit or persist a structured record with:

| Field | Required | Notes |
|---|---:|---|
| `operation_id` | yes | Stable per adapter run. |
| `operation_type` | yes | `init`, `sync`, `query`, `validate`, etc. |
| `workspace_path` | yes | Must be isolated and not main checkout. |
| `git_lex_binary` | yes | Path or acquisition source. |
| `git_lex_identity` | yes | Source commit/hash/version when available. |
| `command` | yes | Full command, with secrets redacted. |
| `exit_code` | yes | Raw process exit. |
| `classification` | yes | Adapter classification, not just raw exit. |
| `stdout_digest` / `stderr_digest` | yes | Bounded, no secrets, raw full output only if safe/tracked. |
| `expected_shapes` | validation only | Required for `validate`. |
| `expected_files` | validation only | Required for `validate`. |
| `observed_count` | validation/query | Parsed count when applicable. |
| `main_lex_absent_before_after` | yes | Must be true unless explicit adoption decision exists. |
| `raw_payload_touched` | yes | Must be false for ACP adapter by default. |
| `proof_anchor_paths` | yes | Tracked repo-relative anchors only; not `.gsd/exec`, ignored files, raw logs, or absolute paths as durable proof. |

### Isolation and cleanup contract

A future adapter spike must:

1. create an isolated workspace under `/tmp` or explicit GSD worktree;
2. assert main `.lex`, `Squad`, and `Raw` absent before and after;
3. use sanitized fixtures, not real provider/session payloads;
4. avoid broad commits unless the workspace is disposable;
5. record cleanup status and any residue;
6. never stage `.gsd/exec`, raw provider payloads, secrets, vectors, or large generated stores as durable proof anchors.

### Authority boundary

The adapter may produce:

```text
derived diagnostic evidence
projection/recovery hints
query/debug output
validation diagnostics
```

The adapter may not produce:

```text
ACP source truth
requirement validation proof by itself
legal authority
Russian legal answer evidence
FalkorDB runtime proof
parser completeness proof
R035/R037/R038 validation
production adoption proof
```

### S06 safe wording

Safe:

> A future git-lex adapter spike may use isolated `init`, `sync`, bounded `query`, `list --json`, and wrapper-backed `validate` as non-authoritative diagnostics.

Safe:

> S06 excludes logs-to-git, JSON-LD runtime import/export, broad SPARQL-star parity, production binaries, and main `.lex` adoption from ACP scope by default.

Unsafe:

> git-lex is now an ACP backend.

Unsafe:

> git-lex validation, SPARQL, Raw logs, or JSON-LD validate LegalGraph requirements.

Unsafe:

> S06 approves production or main-repo `.lex` adoption.

### S06/S08 implications

S08 should treat S06 as a boundary contract, not a build-ready implementation milestone. The next safe iteration, if any, is either:

1. a very small isolated adapter spike implementing the allowed diagnostic subset; or
2. stop git-lex runtime advancement for ACP and preserve only learned patterns; or
3. run provenance hardening first if binary/distribution trust becomes the bottleneck.

S06 does not by itself choose implementation. It defines what implementation must not exceed.

## T03: Final recommendation and verification contract

### Final recommendation

```text
S06 disposition: boundary-contract-complete
implementation recommendation: optional tiny isolated adapter spike only after S07/S08 review
production recommendation: no
main .lex recommendation: no
ACP authority change: no
```

S06 recommends neither immediate adoption nor full stop. It recommends a constrained decision for S08:

| Option | When it is valid | S06 assessment |
|---|---|---|
| Stop runtime advancement | If S08 decides current diagnostic value is too small for ACP. | Valid and safe. |
| Preserve patterns only | If ACP can absorb wrapper/query patterns without git-lex runtime. | Valid and likely sufficient. |
| Tiny isolated adapter spike | If user wants implementation after S07 provenance review. | Allowed only within S06 contract. |
| Production/main `.lex` adoption | Never from current evidence. | Rejected / blocked. |

### Candidate adapter spike scope, if later chosen

A future implementation milestone must be limited to:

```text
isolated workspace only
source-built or provenance-reviewed binary only
init/sync/list/query/validate-wrapper only
no save/create/raw/join/kit-update/nuke
no JSON-LD runtime import/export
no broad SPARQL-star support
no real Claude/session logs
no main .lex
no production deployment
```

### Required proof before implementation

Before any implementation milestone, S08 or a follow-up milestone must choose and document:

1. acquisition mode: source-built debug only, source-pinned build, or provenance-reviewed release;
2. fixture source: sanitized ACP-like synthetic fixtures only;
3. storage policy: no raw provider payloads, no secrets, no `.gsd/exec` durable anchors;
4. failure policy: fail closed on missing shapes, skipped files, setup diagnostics, and raw command ambiguity;
5. cleanup policy: isolated workspace deletion or residue report;
6. authority policy: adapter output is non-authoritative diagnostics only;
7. decision gate: explicit human approval before any main-repo `.lex` or production use.

### Final evidence anchors

```text
prd/architecture/acp/M053-S02-SHACL-FAIL-CLOSED-WRAPPER.md
prd/architecture/acp/M053-S03-SPARQL-STAR-BOUNDARY.md
prd/architecture/acp/M053-S04-JSON-LD-BRIDGE-RECHECK.md
prd/architecture/acp/M053-S05-CLAUDE-LOGS-GIT-OPS-NONFIT.md
prd/architecture/acp/M053-S06-MINIMAL-ACP-ADAPTER-BOUNDARY.md
```

Runtime/support anchors consumed by S06:

```text
.gsd/exec/977d60a7-200a-41d3-9930-bea9fb072934.stdout  # S02 wrapper matrix
.gsd/exec/61770074-e38a-4f17-8df2-f5dd322dd766.stdout  # S03 SPARQL-star matrix
.gsd/exec/c412f08c-664c-4002-b9d3-405349bc5af5.stdout  # S04 JSON-LD absence probe
.gsd/exec/bf44b9d6-c28f-4407-9712-2386d566f5f7.stdout  # S05 logs-to-git smoke
```

These `.gsd/exec` paths are verification evidence for this GSD run, not durable product proof anchors.

### Final safe wording

Safe:

> M053/S06 defines a minimal adapter-later boundary for git-lex diagnostics. It permits only isolated, non-authoritative use of `init`, `sync`, `list --json`, bounded `query`, and wrapper-backed `validate` if a later implementation milestone is approved.

Safe:

> S06 excludes logs-to-git, JSON-LD runtime, broad SPARQL-star parity, raw validation, mutating/destructive CLI commands, production binaries, and main `.lex` adoption from ACP scope by default.

Unsafe:

> M053 approves git-lex as an ACP backend.

Unsafe:

> S06 validates LegalGraph requirements or Russian legal evidence.

Unsafe:

> S06 approves implementation without S07/S08 review and explicit human decision.

### T03 conclusion

```text
S06 final classification: adapter-boundary-only
ACP-useful candidate surfaces: isolated init/sync/list/query/validate-wrapper diagnostics
excluded surfaces: logs-to-git, JSON-LD runtime, broad SPARQL-star, save/create/raw/join/kit-update/nuke, production/main .lex
recommended next decision: S07 provenance recheck, then S08 choose stop/preserve-patterns/tiny-isolated-spike
main repo safety: .lex absent; Squad absent; Raw absent
```
