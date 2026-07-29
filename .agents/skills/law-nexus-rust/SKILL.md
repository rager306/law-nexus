---
name: law-nexus-rust
description: "Implements, reviews, migrates, tests, and optimizes Rust product code in law-nexus. Use for Cargo workspace changes, Rust APIs and domain types, Python-to-Rust parity slices, parser or retrieval migration, error handling, unsafe review, performance work, and Rust CI configuration."
license: MIT
metadata: upstream-rust-skills-fd2a861
---

<essential_principles>
## law-nexus Rust contract

1. Rust owns all product, domain, parser, retrieval, graph, and runtime behavior.
2. Python product code is archived prior art under `python_archive/product/`. A thin Python harness may orchestrate processes, Cargo, parity, docs, CI, and GSD only.
3. The Python/Rust boundary is subprocess-only. Reject PyO3, FFI, `ctypes`, `cffi`, shared libraries, embedded interpreters, and duplicated cross-language domain logic.
4. Preserve deterministic-first, temporal-first, citation-safe behavior. An LLM is never legal authority.
5. Add crates, async runtimes, abstractions, unsafe code, and release optimizations only for a concrete requirement with verification evidence.
6. Keep tests bounded. Do not rebuild the full legal corpus inside unit tests or mutate tracked parity artifacts.
7. Follow ADR-0015 hexagonal verification architecture: overlapping contours, shared port contracts, semantic oracles, hostile proofs, lifecycle honesty, and non-claims. Details: `references/verification-matrix.md` and `doc/adr/0015-hexagonal-verification-architecture.md`.
8. Treat upstream Rust rules as advisory retrieval material. `references/project-policy.md` overrides generic guidance.
9. Before editing an existing symbol, follow project GitNexus impact-analysis requirements. Before completion, produce fresh verification evidence.
</essential_principles>

<quick_reference>
## Default engineering posture

- Prefer borrowing, slices, validated types, exhaustive enums, explicit conversions, and `Result` for recoverable failures.
- Preserve error source and operation context without logging legal text, secrets, credentials, vectors, or unnecessary raw payloads.
- Prefer safe standard-library code while the requirement remains small; preserve the current zero-dependency tracer boundary unless a dependency has demonstrated value.
- Profile before optimizing. Keep portable release defaults unless a deployment target is explicitly fixed.
- If owned code introduces `unsafe`, require a minimal block, a `// SAFETY:` invariant, targeted tests, and Miri consideration.
- Use current workspace edition and toolchain contracts; do not silently migrate edition, MSRV, panic strategy, target CPU, or public schema.
</quick_reference>

<routing>
| Intent | Follow |
|---|---|
| Implement a Rust vertical slice or new crate | `workflows/implement-rust-slice.md` |
| Review Rust code or a Cargo change | `workflows/review-rust-change.md` |
| Migrate Python behavior to Rust | `workflows/migrate-python-parity.md` |
| Optimize a measured Rust hot path | `workflows/optimize-proven-hot-path.md` |
| Introduce or review `unsafe` | `workflows/review-unsafe-code.md` |

For legal evidence, parser semantics, FalkorDB capability, retrieval/citation, or architecture proof claims, also load the matching project-specific skill. This skill governs Rust engineering; it does not supply legal or database proof.
</routing>

<reference_index>
- `references/project-policy.md` — mandatory law-nexus overlay and rejected generic defaults.
- `references/curated-rust-guidance.md` — selected upstream rule IDs adapted to current project needs.
- `references/verification-matrix.md` — ADR-0015 agent-facing checks by change type and failure surface.
- `doc/adr/0015-hexagonal-verification-architecture.md` — project verification architecture authority.
- `UPSTREAM.md` — pinned source, revision, hashes, adaptation boundary, and update process.
- `LICENSE.upstream` — MIT license retained from the upstream corpus.
</reference_index>

<workflows_index>
| Workflow | Output |
|---|---|
| `workflows/implement-rust-slice.md` | Minimal vertical Rust capability with tests and diagnostics |
| `workflows/review-rust-change.md` | Evidence-based findings or a bounded clean review |
| `workflows/migrate-python-parity.md` | Rust behavior proven against frozen Python artifacts without FFI |
| `workflows/optimize-proven-hot-path.md` | Before/after benchmark evidence with unchanged semantics |
| `workflows/review-unsafe-code.md` | Soundness invariants, risk findings, and targeted verification |
</workflows_index>

<success_criteria>
- Rust work respects the Rust-only product and subprocess-only harness boundary.
- Relevant project policy and curated guidance were applied, not the entire generic corpus blindly.
- Dependencies and optimizations have stated need and evidence.
- Feature behavior and at least one relevant failure or diagnostic path are verified.
- Tests are bounded and do not mutate tracked parity artifacts.
- Port/adapter changes prefer shared contract semantics over mock choreography (ADR-0015).
- Claims use the project lifecycle/proof vocabulary and do not promote smoke or bounded evidence to validated product behavior.
</success_criteria>
