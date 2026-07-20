# law-nexus Rust policy overlay

This file overrides generic Rust recommendations when they conflict with the active architecture or current evidence.

## Architecture boundary

- Product/domain/runtime behavior belongs in Rust.
- Python product code is a frozen behavioral reference until whole-system parity, not a place for new product features.
- A Python repository harness may invoke Rust binaries through subprocess and consume bounded machine-readable results.
- PyO3, C ABI bridges, embedded Python, `ctypes`, `cffi`, `dlopen`, shared-library coupling, and permanent dual-language product runtime are prohibited.
- ACP/git-lex is archive-only and must not return through Rust dependencies, CI, skills, or runtime design.

## Dependency policy

Default to the standard library for small capabilities. A new crate needs all of:

1. a concrete requirement that is awkward or unsafe to satisfy locally;
2. review of maintenance, license, transitive dependencies, and feature flags;
3. a bounded verification plan;
4. no violation of offline/reproducible CI expectations.

Generic defaults are not project mandates:

| Generic recommendation | law-nexus policy |
|---|---|
| `anyhow` for applications | Optional. Keep small tracers dependency-free when explicit errors are simple. |
| `thiserror` for libraries | Optional when typed error boilerplate demonstrably warrants it. |
| Tokio for async work | Add only after a real concurrent I/O requirement exists. |
| Rayon for CPU work | Add only after profiling and deterministic-output checks. |
| SmallVec, ArrayVec, ThinVec, arenas | Add only after allocation profiling. |
| Proptest, Criterion, Loom, Miri | Use selectively for the risk they address; do not burden every crate by default. |

## API and behavior policy

- Parse external data into validated domain types at boundaries.
- Use newtypes where legal identifiers, source positions, editions, dates, or evidence references could otherwise be mixed.
- Preserve deterministic ordering in serialized outputs. Do not rely on hash-map iteration order.
- Schema and CLI output are contracts. Changes require compatibility tests or an explicit versioned break.
- Prefer explicit error variants when callers need to branch; use opaque contextual errors only at executable orchestration boundaries.
- Do not expose raw legal source text unnecessarily in errors, snapshots, or logs.

## Performance policy

- Measure first with representative bounded inputs.
- Optimize the proven bottleneck, not adjacent code.
- Preserve deterministic and citation-safe semantics with before/after tests.
- Do not set `target-cpu=native` for portable CI or release artifacts.
- `panic = "abort"`, LTO, codegen-unit changes, PGO, SIMD, custom allocators, and faster non-DoS-resistant hashers require explicit deployment and benchmark evidence.

## Unsafe policy

Safe Rust is the default. Before adding owned `unsafe` code:

- show why safe Rust cannot meet the requirement;
- isolate the minimum operation;
- state every validity, aliasing, lifetime, alignment, provenance, and thread-safety invariant;
- add `// SAFETY:` immediately above the block and `# Safety` for public unsafe APIs;
- add targeted tests and consider a pinned Miri job;
- do not use unsafe to create a Python/Rust bridge.

## Current toolchain boundary

At adaptation time the workspace uses Rust 1.94.1 and `ln-status` uses edition 2021 with no dependencies. Upstream guidance targets Rust 1.96 and edition 2024. Verify version-sensitive syntax against the current toolchain and official documentation before applying it. Edition or MSRV migration is separate planned work.
