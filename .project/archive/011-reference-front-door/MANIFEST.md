# Archive — 011-reference-front-door

Milestone: reference-front-door
Shipped: 2026-10-31
Final verdict: all criteria met; project verify passed
Waves: 2  Tasks: 3 done / 3 total  Review cycles used: 1/1
Carried forward: 15 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| `law-nexus-inspect reference-package build --corpus-dir <measure-ed50 fixture> --catalog <catalog> --out-dir <dir>` exits 0 and creates the expected reference artifact set (edition/digest layer, references document, pageindex document, measurement artifacts) on the tracked measure-ed50 fixture; it writes only inside `--out-dir` and leaves the corpus directory and catalog byte-unchanged. | met | crates/ln-product-cli/tests/reference_package_cli.rs:206; .project/build/verify-ledger.jsonl (86bd8af3f3fcb9cc23917b1f90eaf936587e06e9, pass); README status band at README.md:12-15 names the tracked fixture lineage `measure-ed50` used by this run |
| `law-nexus-inspect reference-package check` with the same arguments on the unmodified built package exits 0 and must never exit 0 when any artifact differs from the derivation — any byte drift, including a truncated or zero-byte artifact, exits 6. | met | crates/ln-product-cli/tests/reference_package_cli.rs:266,:316,:336; .project/build/verify-ledger.jsonl (86bd8af3f3fcb9cc23917b1f90eaf936587e06e9, pass); sidecar walkthrough run |
| Two builds into different temporary output directories produce byte-identical artifacts. | met | crates/ln-product-cli/tests/reference_package_cli.rs:354; sidecar walkthrough run |
| A missing or unreadable input (corpus dir absent, catalog unreadable, empty corpus directory with zero XML documents) exits 3. | met | crates/ln-product-cli/tests/reference_package_cli.rs:375; sidecar walkthrough run |
| Invalid arguments (unknown flag, missing required flag) exit 2. | met | crates/ln-product-cli/tests/reference_package_cli.rs:412; sidecar walkthrough run |
| A corpus that carries no edition 50 builds and checks with the measurements explicitly reported not applicable (no drift counted, exit 0); a corpus that carries edition 50 has its measurements compared normally. | met | crates/ln-product-cli/tests/reference_package_cli.rs:457; sidecar walkthrough run |
| `cargo run -q -p ln-product-cli -- health` (README quick-start, as written) exits 0 after `default-run` is set. | met | README.md:416; crates/ln-product-cli/Cargo.toml:6; .project/build/verify-ledger.jsonl (86bd8af3f3fcb9cc23917b1f90eaf936587e06e9, pass) |
| README status band enumerates 47 workspace members naming `ln-consultant-parser` and `ln-kb-ontology`; AGENTS.md names an existing slice-writing guide (`.agents/skills/law-nexus-rust/`); POST-SHIP-STATE-2026-10-28.md separates current state from dated history (M004 chapter superseded, red-CI table dated); the ARCHITECTURE.md ADR-0031 row states the measurement-level module code exists while corpus-wide D5/D4 execution is unproven — each verifiable by reading the file at HEAD or by the tracked doc suites. | met | README.md:12-15; AGENTS.md:326-331; docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:53,:100,:207; prd/ARCHITECTURE.md:68 |
| `product-model/` gains reference-package capability documentation linked to the measure-ed50 fixture, the executable test, and a recorded check result. | met | product-model/capabilities/reference-package/capability.md; product-model/capabilities/reference-package/scenarios/build-check-ok.md; product-model/capabilities/reference-package/scenarios/check-detects-drift.md; product-model/coverage.md; crates/ln-product-cli/tests/reference_package_cli.rs |

## Contents

- build/evidence.json
- build/verify-ledger.jsonl
- intent/INTENT.md
- plan/PLAN.md
- research/DOCS-AUDIT.md
- research/SYNTHESIS.md
- research/evidence-codebase.md
- review/FINAL.md
- review/PATCH-FINDINGS.md
- review/final-gap-1.md
- review/wave-1.cycle1.md
- review/wave-2.cycle1.md
- tasks/T001-reference-package-cli.md
- tasks/T002-docs-pdd-alignment.md
- tasks/T003-fix-docs-audit-rulings-pin.md

## Notes

- none
