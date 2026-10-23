<required_reading>
Read `../references/project-policy.md`, `../references/curated-rust-guidance.md`, and the verification row matching the change. Read the diff and relevant callers/tests before judging style.
</required_reading>

<process>
1. Establish the intended contract, current toolchain/edition, and changed execution flows.
2. Review correctness first: boundary validation, ownership, error propagation, deterministic ordering, schema compatibility, cancellation, and partial progress.
3. Review architecture: Rust product ownership, subprocess-only harness, no FFI, no new Python product behavior, no archived ACP/git-lex coupling.
4. Review safety and privacy: panic paths, unsafe invariants, numeric casts, sensitive diagnostics, raw legal text, credentials, and vectors.
5. Review dependencies and performance only against demonstrated need. Reject speculative crates, abstraction, and tuning.
6. Verify findings against code and tests. Report actionable file/line evidence ordered by severity; do not manufacture style findings when behavior is sound.
</process>

<success_criteria>
- Findings identify concrete defects, risks, or missing proof with evidence.
- Generic upstream preferences are not presented as law-nexus mandates.
- A clean review is explicitly bounded by the checks performed.
</success_criteria>
