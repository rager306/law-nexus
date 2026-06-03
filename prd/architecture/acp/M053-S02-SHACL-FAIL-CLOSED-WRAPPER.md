# M053 S02 SHACL Fail-Closed Wrapper Proof

## Status

In progress for `M053-2jp3nm / S02`.

S02 tests whether an ACP-side wrapper can make `git-lex validate` safe enough for adapter-later diagnostic use. The wrapper does not make git-lex authoritative. It only decides whether one isolated validation run is acceptable evidence, must fail closed, or remains blocked.

## Boundaries

- Main repository `.lex` must remain absent.
- Main repository `Squad` must remain absent.
- Runtime proof must use isolated `/tmp` workspaces only.
- git-lex validation output is derived diagnostic evidence, not ACP source truth.
- R035/R037/R038 are not validated by this proof.
- S02 does not adopt git-lex runtime, prebuilt binaries, or plugin binaries.

## Inputs

| Input | Required | Purpose |
|---|---:|---|
| `workspace` | yes | Isolated git repo root containing `.lex` and fixtures. |
| `kit` | yes | Expected git-lex kit name, for example `squad`. |
| `expected_shape_paths` | yes | Shape files that must exist before validation can count as evidence. |
| `expected_fixture_paths` | yes | Markdown fixture files the wrapper expects `git-lex validate` to count. |
| `command` | yes | Exact `git-lex validate` command and environment. |
| `git_lex_exit_code` | yes | Raw process exit code. |
| `stdout` / `stderr` | yes | Raw output used to classify diagnostics and counted files. |
| `main_repo_safety` | yes | Before/after checks for `/root/law-nexus/.lex` and `/root/law-nexus/Squad`. |

## Outputs

| Output | Meaning |
|---|---|
| `wrapper_status: pass` | git-lex exited 0, expected shapes exist, every expected valid fixture was counted, and no setup/skip diagnostics were found. |
| `wrapper_status: git-lex-fail` | git-lex exited non-zero because actual SHACL violations were found in counted files. This is a fail-closed diagnostic result, not a wrapper failure. |
| `wrapper_status: wrapper-fail` | The wrapper rejects the run despite git-lex exit 0 because evidence was missing, skipped, or ambiguous. |
| `wrapper_status: blocked` | Runtime behavior is too ambiguous to classify without implementation or upstream changes. |
| `wrapper_status: rejected` | The scenario is not a valid validation proof strategy, for example malformed YAML as a negative fixture. |

## Fail-closed decision table

| Condition | Raw git-lex behavior from M052/S01 | Wrapper decision | Rationale |
|---|---|---|---|
| Not a git repo | exits non-zero | `wrapper-fail` | Operational setup failed; no validation evidence. |
| No kit configured | returns success | `wrapper-fail` | A success with no kit is not proof that content was validated. |
| Expected shape file missing | may return success if no shapes found | `wrapper-fail` | Missing shapes are a setup failure. |
| Shape parse/load/schema/compile diagnostic | returns success | `wrapper-fail` | Setup errors are fail-open in raw git-lex. |
| Expected fixture not counted | may return success | `wrapper-fail` | File could have been skipped before SHACL. |
| Counted file total below expected | may return success | `wrapper-fail` | Expected coverage did not happen. |
| Malformed YAML frontmatter | skipped | `rejected` for negative proof; `wrapper-fail` if expected | Malformed YAML does not reach SHACL validation. |
| Missing frontmatter | skipped | `wrapper-fail` if expected | Not validated. |
| Unknown kit prefix / no usable kit-prefixed keys | skipped | `wrapper-fail` if expected | Not validated. |
| Generated Turtle parse/load diagnostic | logged and skipped | `wrapper-fail` | Data generation failed before conformance proof. |
| SHACL processor error | logged without violation count | `wrapper-fail` | Processor errors are not validation proof. |
| Actual SHACL violation in counted expected file | raw validate exits 1 | `git-lex-fail` | This is desired fail-closed behavior for invalid fixtures. |
| Positive expected file counted and raw exit 0 | exits 0 | `pass` | Acceptable positive diagnostic result if all setup checks pass. |

## Minimal wrapper checks

The wrapper proof script for T02 should implement these checks outside the main repository:

1. Assert `/root/law-nexus/.lex` and `/root/law-nexus/Squad` are absent before and after the matrix.
2. Create an isolated git repository under `/tmp`.
3. Initialize the chosen kit with `PATH=/root/vendor-source/git-lex/target/debug:$PATH`.
4. Assert expected shape paths exist after init.
5. Create fixture files.
6. Run `git-lex validate`.
7. Parse output for `Validated N files`.
8. Compare counted file total against expected fixture count for that run.
9. Treat setup/parse/load/schema/compile/processor diagnostics as wrapper failure unless the row is explicitly testing a rejected proof strategy.
10. Classify non-zero exit with violation output as `git-lex-fail`, not wrapper implementation failure.

## T02 runtime matrix contract

| Row | Fixture type | Raw git-lex expectation | Wrapper expectation |
|---|---|---|---|
| positive counted fixture | Valid `squad:Bug` with required `bugId` and allowed enum values. | exit 0, counted. | `pass` |
| shape-derived invalid fixture | Valid YAML `squad:Bug` missing `bugId` or invalid enum. | exit 1 with SHACL violations. | `git-lex-fail` |
| malformed YAML fixture | Broken YAML frontmatter. | likely exit 0 if no other violations; skipped. | `rejected` as negative proof; `wrapper-fail` when expected counted. |
| unknown-prefix fixture | Valid YAML with no usable `squad.*` keys. | likely exit 0; skipped. | `wrapper-fail` when expected counted. |
| missing shapes/setup fixture | Remove or hide expected shapes before validate. | may exit 0 or setup diagnostic. | `wrapper-fail` |

## Safe ACP wording

Safe wording after T01:

> A wrapper may be able to convert git-lex validation into a fail-closed adapter diagnostic by requiring expected shapes, expected counted files, and rejecting skipped/setup-error cases. This remains unproven until T02 runs the isolated matrix.

Unsafe wording:

> git-lex validation is a complete ACP proof gate.

Unsafe wording:

> malformed frontmatter is a valid negative SHACL test.

## T01 conclusion

The wrapper contract is explicit: raw `git-lex validate` is not sufficient by itself, but a wrapper can potentially fail closed by checking expected shapes, expected counted files, raw exit codes, and fail-open diagnostics. T02 must now prove this contract with an isolated runtime matrix.

## T02: Isolated wrapper runtime matrix

### Scope and safety

T02 ran only in disposable `/tmp` repositories using the source-built debug binary:

```text
binary: /root/vendor-source/git-lex/target/debug/git-lex
binary_sha256: 40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c
workspace_root: /tmp/m053-s02-shacl-wrapper-8bezx6yg
main_lex_after: absent
main_squad_after: absent
```

Raw evidence anchor:

```text
.gsd/exec/977d60a7-200a-41d3-9930-bea9fb072934.stdout
```

Before the matrix, help/safety checks were captured at:

```text
.gsd/exec/15b96a30-48ca-4a2e-a32d-2edb944b8f75.stdout
```

### Matrix method

Each row used a fresh `squad` workspace. The script:

1. Created an isolated git repository under `/tmp`.
2. Ran `git-lex init --kit squad` with `PATH=/root/vendor-source/git-lex/target/debug:$PATH`.
3. Ran baseline `git-lex validate` and parsed `Validated N files`.
4. Added one fixture.
5. Ran `git-lex validate` again.
6. Compared observed count against `baseline + 1`.
7. Classified the row using the T01 wrapper contract.
8. Checked main `/root/law-nexus/.lex` and `/root/law-nexus/Squad` stayed absent.

### Runtime matrix result

| Row | Fixture | Shape exists | Baseline count | Expected count | Observed count | git-lex exit | Wrapper status | Interpretation |
|---|---|---:|---:|---:|---:|---:|---|---|
| positive counted | `Squad/Bug/M053ValidBug.md` | yes | 1 | 2 | 2 | 0 | `pass` | Positive fixture was counted and passed. |
| shape-derived invalid | `Squad/Bug/M053InvalidBug.md` | yes | 1 | 2 | 2 | 1 | `git-lex-fail` | Actual SHACL violations reached raw fail-closed path. |
| malformed YAML | `Squad/Bug/M053MalformedBug.md` | yes | 1 | 2 | 1 | 0 | `rejected` | Malformed YAML was skipped; invalid as negative proof strategy. |
| unknown prefix | `Squad/Bug/M053UnknownPrefix.md` | yes | 1 | 2 | 1 | 0 | `wrapper-fail` | Wrapper detects expected counted file mismatch. |
| missing expected shape | `Squad/Bug/M053ValidButNoShape.md` | no | 1 | 2 | n/a | 0 | `wrapper-fail` | Wrapper detects missing shape despite raw success/skip diagnostic. |

### Key observed outputs

#### Positive counted fixture

```text
Validated 2 files in 51.3ms — all pass ✓
wrapper_status: pass
```

#### Shape-derived invalid fixture

```text
Squad/Bug/M053InvalidBug.md — 3 violation(s):
  → In constraint not satisfied ... bugStatus
  → MinCount(1) not satisfied
  → In constraint not satisfied ... bugSeverity
Validated 2 files in 42.2ms — 3 violation(s) in 1 file(s)
exit code: 1
wrapper_status: git-lex-fail
```

#### Malformed YAML skipped fixture

```text
Validated 1 files in 31.6ms — all pass ✓
expected_count: 2
observed_count: 1
wrapper_status: rejected
```

#### Unknown prefix skipped fixture

```text
Validated 1 files in 33.6ms — all pass ✓
expected_count: 2
observed_count: 1
wrapper_status: wrapper-fail
```

#### Missing expected shape

```text
No SHACL shapes found for kit 'repolex-ai/git-lex-kit-squad' — skipping validation.
shape_exists: false
wrapper_status: wrapper-fail
```

### What T02 proves

T02 upgrades the wrapper hypothesis from source contract to isolated runtime proof:

- A wrapper can accept a positive result only when expected shapes exist and expected fixtures are counted.
- A wrapper can preserve raw git-lex fail-closed behavior for counted SHACL violations.
- A wrapper can reject skipped malformed frontmatter by expected-count mismatch.
- A wrapper can reject unknown-prefix skipped input by expected-count mismatch.
- A wrapper can reject missing expected shapes even when raw git-lex exits 0.
- The main repository remained unpolluted by `.lex` or `Squad`.

### What remains bounded

T02 proves wrapper logic for a minimal `squad` matrix only. It does not prove:

- all kits;
- all SHACL constraints;
- production adapter implementation;
- browser/server behavior;
- release/provenance safety;
- ACP source-truth validation;
- R035/R037/R038 validation.

T03 must classify whether this is enough for S06 minimal adapter contract or whether more upstream/runtime proof is needed.

## T03: Final classification and downstream adapter contract

### Final classification

| Capability / claim | S02 result | Classification |
|---|---|---|
| Raw `git-lex validate` as standalone ACP proof gate | Raw validation can still pass skipped/missing-shape/setup cases. | `still blocked` |
| Wrapper-backed positive diagnostic | Positive counted fixture passed only when expected shape existed and count increased. | `upgraded to adapter-later diagnostic` |
| Wrapper-backed negative diagnostic | Shape-derived invalid fixture was counted and raw validation exited 1 with SHACL violations. | `upgraded to adapter-later diagnostic` |
| Malformed YAML as negative SHACL proof | Fixture was skipped and count did not increase. | `rejected` |
| Unknown-prefix fixture as proof of validity | Fixture was skipped and count did not increase. | `rejected as validation proof`; wrapper catches as `wrapper-fail` |
| Missing expected shapes | Raw git-lex exited 0 with skip diagnostic. | `wrapper-fail`; raw behavior remains `fail-open` |
| ACP/legal/product requirement validation | No ACP source-truth semantics were tested. | `no upgrade` |
| Main `.lex` adoption | Main `.lex` stayed absent; runtime proof stayed isolated. | `still blocked pending later adoption decision` |

### S06 minimal adapter contract implications

S06 may treat wrapper-backed SHACL validation as a candidate adapter diagnostic only if the adapter contract includes all of the following:

1. **Isolation**: run only in a declared isolated workspace; never create main-repo `.lex`.
2. **Expected shapes**: require explicit expected shape paths and fail if any are absent.
3. **Expected files**: require explicit expected fixture/document paths and fail if counted validation total does not match expected coverage.
4. **Raw exit handling**:
   - exit `0` + expected coverage + no setup diagnostics => `pass`;
   - exit non-zero + violation output + expected coverage => `git-lex-fail` diagnostic;
   - exit `0` + skipped/missing coverage => `wrapper-fail`.
5. **Diagnostic scan**: reject setup/parse/load/schema/compile/processor diagnostics even if raw git-lex exits 0.
6. **Non-authority**: output is `derived diagnostic evidence`, not ACP source truth.
7. **Structured log**: persist workspace path, binary identity, command, exit code, expected count, observed count, expected shapes, fixture paths, status, and reason.
8. **Cleanup/safety checks**: record before/after `test ! -e /root/law-nexus/.lex` and `test ! -e /root/law-nexus/Squad`.
9. **No broad inference**: do not infer all-kit or all-document validation from this minimal `squad` proof.

### Final S02 disposition

```text
S02 disposition: upgraded
upgraded claim: wrapper-backed git-lex SHACL validation can be used as adapter-later diagnostic evidence for counted shape-derived validations in isolated workspaces.
still blocked: raw git-lex validate as standalone ACP proof gate.
rejected: malformed YAML or skipped input as negative SHACL proof.
S06 requirement: adapter contract must implement fail-closed expected-shape and expected-file coverage checks.
main repo safety: .lex absent; Squad absent.
```

### Evidence anchors

```text
prd/architecture/acp/M053-S02-SHACL-FAIL-CLOSED-WRAPPER.md
.gsd/exec/15b96a30-48ca-4a2e-a32d-2edb944b8f75.stdout
.gsd/exec/977d60a7-200a-41d3-9930-bea9fb072934.stdout
.gsd/exec/38c50e30-202d-4810-824d-d76e6cb6a777.stdout
```

### Safe final wording

> Wrapper-backed git-lex SHACL validation is runtime-backed as an adapter-later diagnostic for counted, shape-derived validations in isolated workspaces. It is not a standalone ACP proof gate and does not validate ACP source-truth, legal retrieval, production runtime, or R035/R037/R038.

### Unsafe final wording

> git-lex validation is now fail-closed for all invalid documents.

> git-lex validation can replace ACP proof gates.

> S02 proves git-lex production adoption readiness.
