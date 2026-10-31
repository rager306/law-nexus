---
kind: validation
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect reference-package check with --corpus-dir, --catalog and --out-dir over a package whose artifacts no longer match the derivation
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal
  - text: The Product re-derives the artifact set, names every drift row on stderr, and exits 6
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal
---

# Check detects drift and refuses the package

## Trigger

The operator wants proof that a built package still matches its derivation —
or expects drift and checks for it.

## Outcome

Every drift row is named on stderr before the command exits 6; a changed
byte, a truncated (including zero-byte) artifact, and a deleted artifact are
all drift. There is no warn-and-pass path. This is pinned by
`crates/ln-product-cli/tests/reference_package_cli.rs`
(`check_unmodified_package_passes_and_flipped_bytes_all_exit_6`,
`zero_byte_artifact_is_drift_exit_6_not_missing_input_exit_3`,
`deleted_artifact_is_drift_exit_6`), recorded green 8/8 in the T001 Log
(2026-10-31).

## Edge cases

- A zero-byte artifact is drift (6), never a missing-input exit 3.
- Restoring the artifact bytes makes the same package check ok again (exit 0).
