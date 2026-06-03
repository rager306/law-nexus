# M055 S01 Git Lex Backend Adoption Cutline

## Status

In progress for `M055-dbt65v / S01`.

S01 defines what "use git-lex as backend" means under schedule pressure. It turns the user's acceleration request into a staged backend adoption plan that reuses proven git-lex functionality while preserving ACP authority boundaries.

## Trigger and decision

### User trigger

The user wants to accelerate and use `git-lex` as backend because there is no time to reimplement already working functionality.

### Recorded decision

```text
Decision: D078
Choice: staged git-lex backend adoption track
Immediate mode: shadow diagnostic/projection backend
Not immediate: ACP source-truth backend or production backend
```

Rationale:

- M054 proved a useful proof-only wrapper around git-lex diagnostics.
- Reimplementing all backend behavior would be slower.
- Direct source-truth/main `.lex` adoption remains risky.
- Staged adoption lets ACP reuse git-lex now without pretending all authority/provenance gates have passed.

## Evidence baseline from M054

M054 evidence anchors:

```text
prd/architecture/acp/M054-S01-PINNED-SOURCE-ADAPTER-CONTRACT.md
scripts/git_lex_diagnostic_adapter.py
tests/test_git_lex_diagnostic_adapter.py
prd/architecture/acp/M054-S03-ISOLATED-RUNTIME-DIAGNOSTIC-MATRIX.md
prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl
prd/architecture/acp/M054-S04-PROOF-ONLY-ADAPTER-SPIKE-SYNTHESIS.md
```

M054 proved:

```text
sync: pass
list_json: pass
bounded query: pass
bounded query_json: pass
positive validate_wrapped: pass
negative validate_wrapped: git-lex-fail with concrete SHACL violation
denied nuke: rejected without execution
no main .lex/Squad/Raw residue
```

M054 did not prove:

```text
main .lex adoption
production readiness
release/plugin-bundled binary trust
ACP source truth transfer
R035/R037/R038 validation
real legal payload ingestion
JSON-LD runtime support
broad SPARQL-star parity
```

## Backend level ladder

| Level | Name | Meaning | Current readiness | Promotion gate |
|---|---|---|---|---|
| L0 | Proof harness | Wrapper proves allowed git-lex diagnostics in isolation. | ✅ Proven by M054. | Already complete. |
| L1 | Shadow diagnostic/projection backend | ACP-native records feed an isolated git-lex backend workspace; git-lex emits diagnostics/projections only. | 🟡 Immediate M055 target. | S02/S03 implementation and runtime proof. |
| L2 | Operational diagnostic backend | ACP workflow can call git-lex diagnostics as a regular internal subsystem, still non-authoritative and no main `.lex`. | ⏳ Future after L1. | Stability, tests, failure handling, bounded storage. |
| L3 | Main-repo `.lex` backend | `.lex` exists in the main repository and participates in repo workflows. | ❌ Blocked. | Explicit human decision, rollback/state proof, ignored/tracked policy, cleanup plan. |
| L4 | ACP source-truth backend | git-lex backend becomes authoritative for some ACP records. | ❌ Blocked. | Authority migration design, proof gates, conflict resolution, requirement validation policy. |
| L5 | Production backend | Release/provenance-hardened git-lex backend in production workflows. | ❌ Blocked. | Release artifacts, signatures, SBOM, attestations, rollback, security review. |

## Immediate target

```text
M055 immediate target: L1 shadow diagnostic/projection backend
```

Operational meaning:

- ACP remains source of truth.
- ACP emits or stages ACP-shaped source records into an isolated git-lex workspace.
- git-lex performs sync/list/query/validate diagnostics.
- Results return as ACP diagnostic records, not source truth.
- Main repo `.lex`, `Squad`, and `Raw` remain absent.
- Output can inform agents and architecture verification, but cannot close R035/R037/R038 or legal evidence requirements.

## T01 conclusion

```text
S01/T01 disposition: backend-cutline-defined
D078 reflected: yes
immediate backend level: L1 shadow diagnostic/projection backend
main .lex adoption: blocked
source-truth backend: blocked
production backend: blocked
```

## T02: Backend reuse matrix

### What we can reuse now

| git-lex capability | Reuse in ACP L1 shadow backend | Why it is usable now | Boundary |
|---|---|---|---|
| Source-built pinned binary | Yes | D077 and M054 identity proof. | Proof/local backend only; not release/prod. |
| `scripts/git_lex_diagnostic_adapter.py` | Yes | M054 wrapper passed tests and runtime matrix. | Internal diagnostic adapter foundation. |
| `sync` | Yes | M054 runtime matrix `pass`. | Isolated backend workspace only. |
| `list_json` | Yes | M054 runtime matrix `pass`; truncation bug fixed. | Diagnostic class/shape inventory only. |
| Bounded `query` | Yes | M054 runtime matrix `pass`. | Predefined query IDs only. |
| Bounded `query_json` | Yes | M054 runtime matrix `pass`. | Parse full stdout internally; emit bounded records. |
| `validate_wrapped` positive/negative | Yes | M054 proved pass and concrete fail behavior. | Fail-closed diagnostic only, not ACP requirement proof. |
| Denylist rejection | Yes | M054 rejected `nuke` without execution. | Expand denied-command tests as adapter surface grows. |

### What we can reuse with additional gates

| Capability | Why not immediate | Required next proof |
|---|---|---|
| ACP-shaped records instead of generic squad fixtures | M054 used synthetic squad fixtures. | S03 shadow backend proof over ACP-shaped synthetic records. |
| Regular ACP workflow invocation | M054 was a proof harness. | S02 internal adapter interface and tests. |
| Durable diagnostic storage | M054 tracked diagnostics JSONL but not product workflow storage. | Adapter record schema and retention policy. |
| Main `.lex` | It mutates repository state and changes operational contract. | Isolated main-repo rehearsal, rollback/state policy, explicit human decision. |
| Stronger backend role | Authority conflicts unresolved. | Source category, conflict resolution, proof-gate and migration design. |

### What must stay ACP-native

| ACP surface | Reason |
|---|---|
| Source truth records | git-lex outputs are derived until authority migration is explicitly accepted. |
| Requirements validation | R035/R037/R038 require their own proof paths. |
| Russian legal evidence and citation safety | Not tested by M054; requires real-document/parser/retrieval proof. |
| FalkorDB runtime behavior | git-lex does not prove FalkorDB ingestion/query/vector/full-text behavior. |
| Architecture registry decisions | git-lex diagnostics can inform, not replace, accepted decisions and proof gates. |

### Still blocked for accelerated track

```text
release/plugin-bundled binary trust
production backend
main .lex without rollback decision
raw/session logs as proof anchors
save/create/raw/join/kit-update/nuke/server/viz/listen in ACP automation
JSON-LD runtime claims
broad SPARQL-star parity claims
real legal payload ingestion
R035/R037/R038 validation from git-lex diagnostics
```

### Schedule-risk tradeoff

Using git-lex as an L1 shadow backend is the fastest safe acceleration path:

- it reuses working `sync`, `list`, `query`, and `validate` functionality;
- it avoids reimplementing graph/projection behavior immediately;
- it preserves ACP source truth while the backend matures;
- it keeps rollback simple because `.lex` remains outside the main checkout;
- it creates concrete diagnostics that can guide later source-truth/backend decisions.

The cost is that L1 cannot yet replace ACP-native authority. This is acceptable under schedule pressure because it still removes near-term implementation burden without promoting unproven production/source-truth claims.

### T02 conclusion

```text
S01/T02 disposition: reuse-matrix-ready
reuse now: pinned source binary, wrapper, sync, list_json, bounded query/query_json, validate_wrapped, denylist
reuse with gates: ACP-shaped fixtures, regular ACP workflow invocation, diagnostic storage, main .lex, stronger backend role
must stay ACP-native: source truth, requirements validation, legal evidence, FalkorDB runtime, architecture registry decisions
blocked: production, release/plugin binaries, raw/session logs, denied commands, JSON-LD runtime, broad SPARQL-star, R035/R037/R038 validation
```

## T03: Downstream implementation constraints

### S02 implementation constraints

S02 should implement only the L1 adapter surface.

Required constraints:

1. Reuse the M054 wrapper behavior rather than broadening command access.
2. Keep D077 pin unless a new explicit update/recheck decision is recorded.
3. Preserve `authority: non-authoritative-diagnostic` or an equivalent ACP-facing field.
4. Preserve no-main-state checks for `.lex`, `Squad`, and `Raw`.
5. Preserve denylist behavior; denied commands must be rejected without executing git-lex.
6. Parse full stdout internally when structured output is needed, but emit only bounded diagnostics.
7. Add tests for:
   - allowed operation dispatch;
   - denied operation rejection;
   - diagnostic schema;
   - no private raw stdout/stderr leakage;
   - no main `.lex`/`Squad`/`Raw` assumptions.
8. Do not introduce server/viz/listen, raw/session logs, release/plugin binaries, or real legal payloads.

### S03 runtime constraints

S03 should prove L1 against ACP-shaped synthetic fixtures.

Required constraints:

1. Use an isolated workspace.
2. Use ACP-shaped records, not real legal documents and not raw session logs.
3. Run only allowed operations through the adapter.
4. Track a bounded diagnostics JSONL artifact.
5. Record workspace path, binary identity, command classifications, and cleanup status.
6. Verify no main `.lex`, `Squad`, or `Raw` before and after.
7. Treat failures as classification evidence, not as something to hide.

### Accepted acceleration risk

```text
Accepted risk: ACP will rely on git-lex earlier as a shadow diagnostic/projection backend to save implementation time.
Rejected risk: ACP will not yet rely on git-lex as source truth, main repository state owner, production backend, or LegalGraph requirement validator.
```

This is the practical compromise:

- use working git-lex graph/projection/validation machinery now;
- keep ACP-native authority and proof gates intact;
- create runtime evidence for stronger adoption rather than asserting it;
- defer expensive reimplementation until the git-lex backend role fails, narrows, or graduates.

### Proposed next actions after S01

1. Execute S02: implement the internal ACP diagnostic backend adapter over the M054 wrapper.
2. Execute S03: run shadow backend diagnostics over ACP-shaped synthetic records.
3. If S03 passes, decide whether to:
   - continue using L1 shadow backend only;
   - proceed to L2 operational diagnostic backend;
   - plan a separate isolated main `.lex` rehearsal;
   - stop and keep git-lex as diagnostic prior art.

### S01 final disposition

```text
S01 final disposition: backend-adoption-cutline-ready
immediate backend target: L1 shadow diagnostic/projection backend
acceleration accepted: yes, for L1 only
source-truth transfer: no
main .lex adoption: no
production adoption: no
S02 readiness: ready to implement internal diagnostic backend adapter
S03 readiness: ready to prove ACP-shaped shadow runtime after S02
```
