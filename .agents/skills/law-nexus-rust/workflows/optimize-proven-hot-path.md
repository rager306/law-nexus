<required_reading>
Read `../references/project-policy.md`, the performance and ownership sections of `../references/curated-rust-guidance.md`, and the performance row in `../references/verification-matrix.md`.
</required_reading>

<process>
1. Reproduce the bottleneck with a representative bounded input and record baseline wall time, CPU/memory where relevant, output hash/count, build mode, and host/toolchain context.
2. Identify the measured hot path. Do not optimize neighboring code from intuition.
3. Prefer algorithm, I/O, allocation, and data-layout improvements before compiler flags or unsafe code.
4. Make one attributable change at a time. Preserve deterministic and citation-safe semantics.
5. Rerun the same benchmark and semantic assertions. Report variance and avoid claims below measurement noise.
6. Reject `target-cpu=native`, PGO, SIMD, custom allocators, non-DoS-resistant hashers, or unsafe implementations unless deployment constraints and gains justify them explicitly.
</process>

<success_criteria>
- A reproducible baseline identified the changed hot path.
- Before/after evidence shows a meaningful improvement.
- Outputs and failure behavior remain equivalent.
- Portability, safety, and dependency costs are stated.
</success_criteria>
