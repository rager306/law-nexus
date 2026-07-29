# Rust verification matrix

Authority: **ADR-0015** (hexagonal verification architecture). Use the smallest
set that proves the changed behavior and its diagnostic surface. Inspect test
collection and fixtures before any potentially expensive run.

## Contours (ADR-0015)

Prefer overlapping contours over a classic unit→E2E pyramid:

| Contour | When required |
|---|---|
| Domain semantic | pure types, policies, transitions |
| Application functional | use case through driving port |
| Port contract | any port with InMemory/Hostile/Real adapters |
| Adapter integration | real TEI/RuVector/redb/protocol behavior |
| Composition | product-cli / runner wiring |
| System journey | few real-fixture end paths only |
| Architecture/process | crate deps, lifecycle tags, residual debt |
| Concurrency/resilience | only when workers/durability change |

## Change matrix

| Change | Required checks | Additional evidence |
|---|---|---|
| Formatting-only Rust change | `cargo fmt --all --check` | Confirm no semantic diff |
| New or changed Rust behavior | `cargo fmt --all --check`; targeted `cargo test`; `cargo check --workspace --offline` | Test one failure or diagnostic path |
| Port or adapter change | Shared port contract suite if present; otherwise track as process debt | InMemory and Hostile must not diverge silently |
| Cargo/workspace change | `cargo metadata --no-deps --format-version 1`; `cargo check --workspace --offline`; targeted tests | Confirm lockfile and dependency intent; no domain→adapter edge |
| Public API or serialized schema | Targeted unit/integration tests; deterministic repeat-output check | Compatibility or explicit break evidence |
| Parser / decode change | Positive + hostile tests; provider isolation (Consultant ≠ Garant) | Byte-span validity; no silent unknown drop |
| Storage / retrieval change | Port contracts; fail-closed diagnostics | Non-claims unless real adapter proven |
| Python-to-Rust parity slice | Rust tests; frozen artifact comparison; subprocess harness test | Prove Python product imports/FFI are absent |
| Error handling | Targeted failing input or forced failure | Exit code, bounded stderr/JSON, no sensitive payload |
| Performance change | Representative before/after benchmark in **release** mode | Same-output assertion; no debug numbers as release truth |
| Async/concurrency | Targeted cancellation, shutdown, ordering, and backpressure tests | No lock held across await; deterministic result where required |
| Unsafe code | Normal tests plus targeted Miri where feasible | Written invariants and `// SAFETY:` audit |
| CI/pre-commit | Local equivalent command and contract test | Path gating and failure propagation |
| Evidence / lifecycle claim | ADR conformance + honest tag | Non-claims when ceiling is `[bounded]`/`[smoke]` |

## Port-contract rules

1. One semantic suite per outbound port; run it on **InMemory**, **Hostile**, and **Real** adapters.
2. Application tests may use a fake only when that fake is covered by the port contract (or the missing suite is tracked process debt).
3. Prefer state/result/provenance assertions over mock call-order choreography.
4. Interaction asserts only when the interaction is policy (promote-after-verify, no double promote, audit-before-write).

## Lifecycle and non-claims

- Tag consequential claims: `[proposed]`, `[smoke]`, `[bounded]`, `[validated]`, `[deferred]`.
- Do not promote `[validated]` from InMemory-only success.
- Release smoke, synthetic probes, and one-fixture tracers must record non-claims for packaging, corpus completeness, legal correctness, and unproven infrastructure.
- Consultant WordML and Garant ODT remain independent risk profiles.

## Default command set

Use offline checks where dependencies are already locked and available:

```bash
cargo fmt --all --check
cargo check --workspace --offline
cargo test --workspace --offline
cargo clippy --workspace --all-targets --offline -- -D warnings
uv run python scripts/verify-adr-conformance.py
uv run law-nexus-harness governor
uv run law-nexus-harness preflight
```

Do not run the full matrix blindly. For a zero-dependency tracer, targeted
build/test and direct process checks may be sufficient. For parser parity,
inspect fixtures and avoid hidden corpus regeneration before running any suite.

## Anti-slop checks

Reject or flag:

- fake luxury (InMemory missing conflicts/uniqueness/ordering honesty);
- oracle collapse (verifier reuses builder helper);
- choreography-only tests;
- nondeterministic goldens without canonicalization;
- dead CI/tooling deps after archival;
- residual product-era Python on the active control plane.

## Completion rule

Compilation alone is insufficient. Verification must demonstrate:

1. intended behavior;
2. a relevant failure or diagnostic surface;
3. no boundary regression such as FFI, Python product imports, tracked-artifact mutation, or nondeterministic output;
4. honest lifecycle tag and non-claims for the evidence ceiling (ADR-0015 / D098).
