<required_reading>
Read `../references/project-policy.md`, the unsafe section of `../references/curated-rust-guidance.md`, and the unsafe row in `../references/verification-matrix.md`. Consult the current Rust Reference/Nomicon for version-sensitive claims.
</required_reading>

<process>
1. Ask whether safe Rust can satisfy the requirement with acceptable measured cost. Remove unsafe if the answer is yes.
2. Enumerate validity, initialization, aliasing, lifetime, alignment, provenance, panic/unwind, thread-safety, and ownership invariants relevant to the operation.
3. Trace every caller and data source. Treat external bytes, parser offsets, graph payloads, and FFI as untrusted boundaries.
4. Minimize the unsafe block and place a precise `// SAFETY:` explanation immediately above it. Public unsafe APIs need a `# Safety` contract.
5. Add tests targeting each invariant and misuse boundary. Run normal tests plus a pinned targeted Miri check where feasible.
6. Reject unsafe used to implement a Python/Rust bridge; the architecture permits subprocess only.
</process>

<success_criteria>
- The need for unsafe is demonstrated rather than assumed.
- All safety invariants are explicit and upheld by callers.
- Unsafe scope is minimal and tested.
- No FFI migration boundary or unsupported soundness claim is introduced.
</success_criteria>
