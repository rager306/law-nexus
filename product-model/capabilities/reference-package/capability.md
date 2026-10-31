---
availability:
  - place: terminal
references:
  - kind: code
    role: implementation
    target: crates/ln-product-cli/src/main.rs#reference_package
    title: reference_package()
  - kind: code
    role: implementation
    target: crates/ln-consultant-parser/src/reference_layer.rs
    title: reference_layer
  - kind: code
    role: context
    target: crates/ln-product-cli/tests/reference_package_cli.rs
    title: reference_package_cli.rs
---

# Reference package

Build and byte-check a reproducible ADR-0031 reference data package from a
corpus directory and a catalog: `law-nexus-inspect reference-package
build|check --corpus-dir <dir> --catalog <path> --out-dir <dir>`. Build
derives the artifact set through `ln_consultant_parser::reference_layer` and
writes only inside `--out-dir`: the corpus and the catalog stay
byte-unchanged, a rebuild into the same directory is byte-identical, and
unrelated files there are left alone. Check re-derives and compares bytes,
naming every drift row on stderr before it exits. The exit contract is
closed: 0 ok, 2 argv, 3 unreadable inputs, 6 byte drift; 5 stays reserved and
is not emitted. The ed-50 measurements are compared only where the corpus
carries edition 50; elsewhere they are explicitly marked not applicable,
never written, and never counted as drift.

Fixture-level proof only: the tracked measure-ed50 fixture
(`crates/ln-consultant-parser/tests/fixtures/reference-layer/measure-ed50/`)
with its recipe-built catalog (`scripts/test_m217_reference_parity.py`,
`build_catalog` over `MEASURE_CATALOG_ROWS`). No corpus-wide D5/D4 execution
is claimed or performed; ADR-0031 stays `[proposed]`.

Recorded check result (T001 Log, 2026-10-31; authoritative orchestrator rerun
`.git/gsd-path/dispatch/gsd-path-M011/T001/attempt-2/verify.json`): Verify
exit 0 — `cargo test -p ln-product-cli --offline --test
reference_package_cli` 8/8 ok, including `check` exit 0 with `check=ok` on
the unmodified package and exit 6 naming every drifted artifact after any
artifact byte is modified.
