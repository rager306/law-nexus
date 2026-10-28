# Archive — 007-ci-proof-inputs

Milestone: ci-proof-inputs
Shipped: 2026-10-28
Final verdict: all criteria met; project verify passed
Waves: 2  Tasks: 2 done / 2 total  Review cycles used: 1/1
Carried forward: 15 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| SC1 — The rust workspace job checks out the full history and tags, so the pinned native status helper can prove the shipped integration on main and the governor reports the shipped-integrated surface. | met | .project/review/wave-1.cycle1.md |
| SC2 — The migration job's governor honesty step names the exact missing proof input when the surface is not shipped-integrated, so a checkout-shape defect is diagnosable from the job log alone. | met | .project/review/wave-2.cycle1.md |
| SC3 — `uv run --frozen pytest tests/test_ci_runtime_restore.py -q` passes and pins both job shapes. | met | .project/review/wave-1.cycle1.md, .project/review/wave-2.cycle1.md |

## Contents

- build/evidence.json
- build/verify-ledger.jsonl
- intent/INTENT.md
- plan/PLAN.md
- research/DOCS-AUDIT.md
- research/SYNTHESIS.md
- review/FINAL.md
- review/final-gap-1.md
- review/wave-1.cycle1.md
- review/wave-2.cycle1.md
- tasks/T001-rust-proof-inputs.md
- tasks/T002-governor-diagnostic.md

## Notes

- none
