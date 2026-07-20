<required_reading>
Read `../references/project-policy.md`, `../references/curated-rust-guidance.md`, and `../references/verification-matrix.md`. Read the active architecture/ADR/migration contract and the specific parity artifact before changing code.
</required_reading>

<process>
1. Define one observable vertical capability and its failure contract. Avoid horizontal scaffolding without a runnable tracer.
2. Inspect the current crate, tests, Cargo metadata, and callers. Run GitNexus impact analysis before editing existing symbols.
3. Write or identify a bounded failing test or process check. Confirm it cannot rebuild the full corpus or mutate tracked artifacts.
4. Implement the smallest safe Rust change. Preserve deterministic output, explicit error context, and current dependency/edition boundaries.
5. If a dependency seems necessary, document the requirement, alternatives, license/transitive surface, offline behavior, and verification before adding it.
6. Verify the intended behavior and at least one forced failure or diagnostic path using the relevant matrix row.
7. Inspect changed scope and remove only code made obsolete by this change.
</process>

<success_criteria>
- A vertical Rust capability is observable through a test, binary, or stable API.
- No Python product logic, FFI, or speculative framework was introduced.
- Output and failure behavior are deterministic, bounded, and safe to diagnose.
- Fresh targeted verification passes.
</success_criteria>
