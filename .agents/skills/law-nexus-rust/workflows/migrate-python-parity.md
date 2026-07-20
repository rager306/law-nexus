<required_reading>
Read `../references/project-policy.md`, `../references/verification-matrix.md`, ADR-0004, ADR-0005, ADR-0007, the active migration roadmap, and the frozen Python artifact or behavior being matched.
</required_reading>

<process>
1. Select one frozen behavior with stable inputs, outputs, counts/hashes, and known limitations. Do not treat Python implementation details as the target architecture.
2. Define a language-neutral parity contract and lifecycle level. Keep single-document and corpus baselines distinct.
3. Build the Rust implementation behind a crate API or binary process boundary. Do not import Python, embed Python, or create FFI bindings.
4. Compare deterministic Rust output against the frozen artifact or independently specified semantic assertions.
5. Exercise malformed input and process failure. Ensure diagnostics contain context but not unnecessary source text or secrets.
6. Keep the Python product reference intact until whole-system parity and explicit cutover. Harness changes may only orchestrate the proof.
7. Record deviations as intentional contract changes or unresolved gaps; never smooth partial parity into complete parity.
</process>

<success_criteria>
- Rust owns the migrated behavior and matches the declared frozen contract.
- Comparison is reproducible and does not mutate tracked baselines.
- Python is used only as reference or process orchestrator.
- No PyO3, FFI, shared library, or duplicated Python product feature exists.
</success_criteria>
