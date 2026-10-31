---
kind: primary
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect reference-package build with --corpus-dir, --catalog and --out-dir over the measure-ed50 fixture
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal
  - text: The Product derives the reference artifact set through ln_consultant_parser::reference_layer and writes the artifacts only inside --out-dir, printing one wrote line per artifact
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal
  - text: The Product re-derives the artifact set and compares bytes, then reports check=ok
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal
  - text: The command exits 0
    kind: condition
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal
---

# Build and check the reference package ok

## Trigger

The operator wants a reproducible reference data package for a corpus
directory and catalog, and proof that the package on disk matches it.

## Outcome

Build writes the artifact set inside `--out-dir` — four core artifacts, plus
the two ed-50 measurement artifacts where the corpus carries edition 50 —
each announced with a `wrote` line, and exits 0; the corpus and the catalog
stay byte-unchanged and a rebuild into the same directory is byte-identical.
Check on the unmodified package exits 0 and reports `check=ok`. On the
tracked measure-ed50 fixture this is pinned by
`crates/ln-product-cli/tests/reference_package_cli.rs`
(`build_measure_ed50_package_is_complete_idempotent_and_input_safe`,
`check_unmodified_package_passes_and_flipped_bytes_all_exit_6`), recorded
green 8/8 in the T001 Log (2026-10-31).

## Edge cases

- A corpus without edition 50 builds with the four core artifacts only, the measurements explicitly marked `measurement not applicable: corpus has no edition 50`, exit 0.
- Unreadable or missing inputs — a missing catalog, an absent corpus directory, an empty corpus directory — exit 3.
- An unknown flag, a missing required flag, or a flag value that is not there exits 2.
