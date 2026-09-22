# M207 reassessment after fixture isolation repair

Status: [bounded] source audit; recommendations [proposed]. No human adoption,
requirement closure, runtime admission, or change to frozen contracts.

## Technical regression repaired

M211 parity TSV files had been added to the frozen `npa-lawref` directory.
The existing M207 `SEED_ENLARGED` guard correctly rejected the enlarged seed,
causing cascading S01/S02/S03/S04 failures. Commit `242b0e8` moves those files
unchanged to `crates/ln-decode/tests/fixtures/npa-members` and adjusts their two
Rust test consumers. No M207 guard, battery, or pin was relaxed.

Verification: `cargo fmt --all --check` and both `npa_members_gold_parity` and
`npa_members_typed` suites passed. A read-only run of
`scripts/m207_s04_t04_verify.sh` exited 0 with `M207_S04_VERIFY_OK`; its S03
child exited 3 with `MACHINERY_GREEN_HUMAN_ABSENT`. S03/S04 batteries remained
current (9/8 checks). This proves machinery integrity, not legal acceptance.

## Human packets are not yet context-ready

Sources: `prd/migration/rust-evidence/m207-unit-diagnosis.json`,
`prd/migration/rust-evidence/m207-s01-pilot-cases.json`, both
`m207-s02-coder-kit-pass*.json`, and
`prd/architecture/m207-unit-diagnosis.md`.

The diagnosis covers 180 fragments, 10 series and 27 series members. The
40-case pilot contains 37 unique texts. Four selected fragments belong to
incomplete series, without their other members in the coder kit:

| Case suffix | Fragment | Required series members |
|---|---|---|
| 011 | 115 | 115, 116 |
| 015 | 091 | 091, 092 |
| 019 | 081 | 081, 082 |
| 032 | 099 | 096, 097, 098, 099 |

Cases 006 (fragment 046) and 025 (fragment 053) are orphan tails without a
reconstructed series in the diagnosis. Their heads are not proven by the
harvested seed; do not guess them. Cases 013 and 018 have other truncation
flags and require separate genre/context assessment, not automatic series glue.
Case 040 is a duplicate of 009, not a diagnosed series member. The older
"6 glue pair" prose must not be used as a precise case inventory.

The kit generator follows its closed schema: fragment-local inputs, not a
complete-series presentation. Its success marker therefore does not prove
context readiness. Checks found no filled model-answer fields in either kit;
pass differences are header-only. Empty templates are not annotations.

Recommendation [proposed]: preserve the frozen 40-case draw and add a separately
versioned, answer-free presentation sidecar with ordered fragment references and
hashes. Display joins must not create a cross-block TextAnchor. Unresolved heads
stay unavailable-for-coding. Present the same context to both blind coders.
This sidecar needs an explicit protocol compatibility decision before human use;
it must not silently alter the current unit or closed kit schema. Do not put
machine-predicted genres or answers in the coder-facing sidecar.

## C4 acceptance and observability

Sources: `prd/annotation/m207-s04-c4-protocol.md`,
`scripts/m207_s04_c4_run.py` (`acceptance_for`, `build_argv`, launch timeout),
`prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json`, and its
`m207-s04-c4-attempts/m207-s04-c4-full-walk-001/stdout.log`.

The recorded walk completed with exit 0 in 387174 ms, budget 3600 seconds,
43797 files, 43796 decoded and 1 failed. It used `--jobs 0`, no `--limit`.
The current frozen rule requires complete/0 AND duration >= budget. The same
budget is the process timeout ceiling. This creates a boundary-race criterion,
not a reliable measure of full-corpus completion or sustained stability.
The existing receipt correctly remains `operational_acceptance=non-pass`.

Recommendation [proposed]: a future contract must distinguish a full-walk
completion criterion (inventory/counts/digest/complete/no limit and explicit
failure policy) from a sustained-load criterion with a separate duration and
larger timeout. Never pad execution with sleep to obtain a pass. Do not edit
the existing receipt or frozen formula in place.

The M207 invocation did not request `--failures-out`; its aggregate does not
identify the failed input. The older M204 S12 Garant N1875 decode failure is a
hypothesis only: binary/source hashes differ, so it cannot identify this attempt's
failure. A new diagnostic invocation with a failure sidecar can establish the
current failure, but cannot retroactively prove the old attempt's identity.

## Evaluation coverage and development exposure

The frozen S03 protocol explicitly specifies `rater-vs-resolved-reference`
(section 1) and `not system quality` (non-claim 5). Its runtime inputs are human
coding passes and resolved observations from agreement/adjudication, not parser
outputs. `scripts/m207_s03_metrics.py` resolves those observations and compares
per-pass labels; no M211 prediction adapter is wired into this measurement.
Earlier descriptions of S03 as an independent parser-precision evaluator were
incorrect.

| M211 output | Existing M207 measurement | Remaining gap |
|---|---|---|
| Date and number | Binary presence of `date` and `doc_no` in human coding | Parser values and occurrence alignment are not measured |
| Source span | Human pass span vs resolved span | Parser must emit fragment-local spans; explicit alignment required |
| TYPE | No TYPE axis in frozen eight-slot vocabulary | Separate annotation/evaluation contract needed |
| Inherited source | Derived scope label from slot presence | Actual provenance edge correctness is not measured |
| approved_by, aliases, this_ref | No corresponding edge labels | Separate relation reference and endpoint matching needed |
| Letterhead and classification axes | Not covered by the six S03 aspects | Separate output-specific reference needed |
| Abstention | Human abstention vs resolved abstention | Parser unresolved/abstention needs its own comparison |

The names `scope`, `binding`, and `false_authority` in S03 must not be equated
with relation correctness or legal authority of M211 outputs. Their exact derived
rules remain those of `prd/annotation/m207-s03-eval-protocol.md` section 3.
Do not insert a ninth slot or parser predictions into that frozen format. A future
parser evaluator requires a separately versioned contract, source-bound reference
annotations (not merely aggregate S03 rates), and an explicit occurrence alignment.
Presence agreement cannot stand in for value or relation accuracy.

A read-only join of `m207-s03-eval-manifest.json` cases through
`m207-s01-pilot-cases.json` fragment IDs to the `frag` rows in both M211 parity TSVs
found all 14/14 selected holdout fragments in the development regression surface.
Both TSVs include all 180 seed fragments. The S03 leakage checker only audits its
specified annotation surfaces; its zero-leakage result does not establish an
unseen algorithm evaluation set. This is demonstrated development exposure, not
evidence about model-training ingestion or knowledge of absent human answers.

Keep the existing holdout's original human-protocol meaning. Do not relabel the
180-fragment regression set as a sealed algorithm test. A future unseen evaluation
needs a prospective selection rule, family-level separation from known development
inputs, an exposure ledger covering corpus-driven iterations, and a pinned system
revision. Merely drawing outside the 180 seed is insufficient when the prototype
has also been tuned using corpus-wide diagnostics. Record uncertainty about earlier
exposure; no retroactive sealing. Consultant-only results do not cover Garant.

## Proposed evaluation work packages

These are follow-up design packages, not new accepted schemas or completed GSD
Tasks. They do not duplicate parser implementation already assigned to M211.

1. **Context presentation bridge.** Produce an operator-side inventory of each
   case's focus span and permitted context references. Keep all anchors local;
   never expose machine-predicted labels to blind coders. Define series/member
   alignment and eligibility before human use. Acceptance: identical presentation
   to both passes, pinned inputs, no cross-document joins, explicit unresolved
   cases, no silent denominator shrinkage or frozen-kit mutation.
2. **Output-to-reference contract.** Define separate occurrence, field-value,
   provenance and relation comparisons for M211, reusing existing human fields
   only where their meaning genuinely matches. Acceptance: missing/extra/wrong/
   ambiguous outcomes remain distinct; unmatched outputs are not dropped; empty
   reference yields not-measured, not zero error. No S03 schema impersonation.
3. **Prospective evaluation split.** Preserve the current seed as regression;
   audit exposure at family and duplicate-text granularity, then pin a new
   evaluation protocol and system revision before examining evaluation outputs.
   Acceptance: documented selection frame, provider-specific claims, overlap and
   exposure checks, no threshold tuning on the final evaluation set.
4. **Operational successor contract.** Resolve full-walk versus sustained-load
   goals with separate completion, failure-policy, duration and timeout rules.
   Acceptance: no boundary race, no sleep-padding, no retroactive pass of C4 v1.
5. **Failure trace.** Run a new scoped diagnostic with explicit failures sidecar
   and binary/source identity. Acceptance: classify each observed failure and
   distinguish current reproduction from identification of the historic attempt.

Packages 1-3 precede any claim of independent M211 quality. Implementation can
proceed on synthetic and regression inputs, but human-only observations cannot be
fabricated and accepted label vocabularies require their owning protocol decision.

## Decision boundary

Automatic work: machinery regression repair, context inventory, leakage checks,
new diagnostic failure trace, and reproducible metric computation after valid
reference data exists.

Owner/protocol decisions: context-sidecar compatibility and coding unit; whether
C4 means full-walk completion or sustained load. Human contributions under the
current contract: two independent coding passes and adjudication. No automatic
pass, fake human input, frozen-pin rewrite, or requirement promotion follows from
this reassessment. M211 implementation correctness remains a separate workstream.
