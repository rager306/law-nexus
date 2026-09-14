# M206/S07 runtime admission: RC28-F06..F12 grammar context remediation completion

**source_bound_admission:** prd/architecture/m206-s05-runtime-admission.md
**S05 already records the owner's Accept** for the M206/S05 runtime scope; this
document extends that recorded acceptance to the S07 remediation completion
slice without changing its scope or conditions.

**scope: RC28-F06..F12**
**selected_d388_gates:** G01, G02, G14
**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16 remain individually deferred and are not selected by this document.
**runtime_stop:** lifted for M206/S07 remediation completion only, by the same
owner decision recorded in the S05 admission; it remains active everywhere
else.

## Historical no-start provenance

S01, S02, S03, and S04 remain **NOT_RUN** with respect to runtime execution:
their batteries are documentation contracts and have never been executed as
runtime tests. S05 confirmed the admission checkpoint. S06 supplied the
red-oracle reproduction baseline. This slice supplies the missing green
runtime remediation evidence.

## Executable contract and fail-closed boundary

- Executable admission check: scripts/m206_s07_admission_contract.test.mjs
- Reproduction oracle: scripts/m206_s06_reproduction.test.mjs
- Green reproduction command: M206_EXPECT=green node --test scripts/m206_s06_reproduction.test.mjs
- Execution evidence policy: every claimed result names the command actually executed `--exact` case, and the recorded exit status consistent with that result.
- Fail-closed execution evidence: spawn errors, signals, compile failures, skipped cases, and missing output are
not evidence of a PASS.
- Failure boundary: missing, conflicting, or unavailable evidence remains fail-closed.

## Admitted finding scope

RC28-F06, RC28-F07, RC28-F08, RC28-F09, RC28-F10, RC28-F11, RC28-F12 — the
grammar context and binding candidate findings from review packet
RC-2026-09-10-001 are admitted for runtime remediation in the owning surfaces
recorded in the S05 admission (crates/ln-decode: document_context.rs,
local_grammar.rs, lawref.rs; crates/ln-temporal: document_context.rs,
semantic_scope.rs) with their regression and contract suites.

## Boundary

- This document does not promote lifecycle, requirements, or product
  readiness claims.
- F12 remediation must not activate deferred IR (F12-NO-IR); cue recognition
  is not a NormRule.
- The D388 deferred gates are not selected; no Pullenti port is admitted.
- If fresh sources contradict this record, the result is a blocker; no policy
  is chosen by inference.
