# M207 S04 — frozen C4 operational contract (`m207-s04-c4-protocol/v1`)

**Status:** `[bounded]` operational/evidence contract, frozen **before** any corpus walk is launched.
**Milestone:** M207-b2i96m / S04 / T01
**Frozen inputs:** `prd/architecture/npa-acceptance-contract.yaml` (`npa-acceptance-contract/v1`,
sha256-pinned), `prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json` (the pinned
prior non-pass attempt, sha256-pinned), `prd/migration/rust-evidence/m207-s03-battery.json` (the
current S03 integrity battery, sha256-pinned), `prd/annotation/m207-s03-schemas.json` (the frozen
S03 evaluation contract, sha256-pinned), `prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json`
(40 documents / 180 fragments, sha256-pinned), `crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json`
(the rule-seed sidecar, sha256-pinned).
**Receipt form:** `m204-s06-c4-operational-receipt/v1` is reused **verbatim** (D444). No new receipt
key, no schema-version bump, no relaxed acceptance rule.
**Closed schema file:** `prd/annotation/m207-s04-schemas.json` (`m207-s04-c4-schemas/v1`).
**Executable gate:** `uv run python scripts/m207_s04_schemas.py check` (marker
`M207_S04_SCHEMAS_OK`); negative proof: `uv run python scripts/m207_s04_schemas.py selftest`.

This document is the frozen instruction sheet for the S04 operational unit plus its
machine-readable contract. It freezes *which attempt may be recorded*, *which fields the receipt
carries*, *how a terminal outcome is published*, *which corpus is the input*, and *what may never
be claimed*. It launches **no** walk and produces **no** receipt: S04/T02 does that. Until a live
attempt exists there is no C4 receipt at all, and an absent receipt is `C4_RECEIPT_MISSING`, never
an inferred or reconstructed success.

The contract is fixed **before** the walk on purpose. If the receipt shape could still be edited
once the outcome is known, a timeout could be rewritten as a completion and an integrity marker
could be read as an operational pass (RC28-F01 in the operational register).

## 1. Scope, framing and ownership

S04 owns the **operational attempt**: one fresh, pinned, process-level C4 walk over the declared
consultant and Garant roots, the immutable receipt that records what that process did, and the
integrity battery that re-checks the receipt without re-running it. It does **not** own the
codebook (S01), the two human coding passes, the agreement or the adjudication (S02), or the
per-aspect rates and provider strata (S03).

The framing is **process facts only**: the receipt says which binary ran with which argv, under
which toolchain, against which declared corpus, for how long, and how the process ended. It says
nothing about what the run means. Semantic C4 data stays in the Rust JSONL envelope; the receipt
is the sidecar that records the terminal process facts the envelope intentionally does not claim
(D444).

- `M207_S04_VERIFY_OK` means **the integrity battery ran and every check passed**. It is not a C4
  pass, not operational acceptance, not independently measured rates and not a requirement
  closure (`INTEGRITY_MARKER_AS_ACCEPTANCE`).
- `terminal.outcome = complete` is a process fact, not an acceptance verdict. Acceptance is
  `claims.operational_acceptance`, computed by the frozen rule of §4, and it is recorded by the
  emitter before any human reads the receipt.
- S03 remains the independent-measurement contour. It stays at exit 3 with `HUMAN_PILOT_ABSENT`;
  S04 neither performs that pilot nor imports its results.

Ownership by construction: any S04 artifact that promotes a label, requests a classification, sets
a threshold, imports an S03 rate or rewrites a terminal outcome is invalid, and the executable gate
rejects it.

## 2. Frozen inputs, pins and admissibility

Every frozen input is pinned by content digest, and a byte of drift in any of them stops the gate
(`FROZEN_SOURCE_DRIFT`):

| Input | Role | Pin |
|---|---|---|
| `prd/architecture/npa-acceptance-contract.yaml` | the runtime contract the walk is run against (`c4-live-check`, mode `runtime`) | sha256 |
| `prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json` | the **prior non-pass** attempt (D444) | sha256 + outcome/acceptance pins |
| `prd/migration/rust-evidence/m207-s03-battery.json` | the current S03 integrity battery (`human_pilot_performed = false`) | sha256 |
| `prd/annotation/m207-s03-schemas.json` | the frozen S03 evaluation contract S04 must not extend | sha256 |
| `prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json` | 40 documents / 180 fragments of the seed | sha256 |
| `crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json` | the rule-seed sidecar refused as an evaluation input | sha256 |

Admissible inputs for the walk are **only** the two declared corpus roots and the acceptance
contract. `consru_export/consru_export/exports` and `law-source/garant` are **declared**, never
derived from a path, a file name or a directory listing, and the S04 helper does not re-attribute
provider metadata (RC28-F02).

Refused inputs (`PROXY_INPUT_REFUSED`): `npa-quality-receipts/v1`, any `npa-c5-*` manifest, the
corpus-manifest schema `law-nexus-npa-corpus-manifest/v1`, `npa-lawref-seed/v1` with
`provenance=rule-seed`, the rule-seed sidecar `crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json`,
and — for this slice — **any** S03 evaluation artifact. The S03 evaluation report is not an input,
not a baseline and not a fallback: it is a refused surface (`S03_RATE_IMPORTED`).

## 3. C4 receipt contract: process facts only

The receipt is a single JSON object with exactly the closed key set of
`m204-s06-c4-operational-receipt/v1`, reused verbatim. The contract in `m207-s04-schemas.json`
declares the root closure, the nested closure of every container object and the required subset.

Required facts (the minimum a receipt must carry to be admissible):

- **immutable attempt identity** — `attempt_id` plus `immutable_attempt_identity.argv_sha256`,
  with `argv_sha256` computed as the sha256 of `json.dumps(argv, separators=(",", ":"))`, exactly
  as the M204/S06 emitter computes it. The identity is written once and never recomputed:
  `attempt_identity_rebuild_forbidden` and `receipt_rebuild_forbidden` are both `true`
  (`IMMUTABLE_IDENTITY_MISSING`).
- **full argv** — the resolved binary path, `--root`, `--garant-root`, `--profile contour`,
  `--jobs 0`, `--acceptance-contract` and `--source-revision`. `--limit` is a **forbidden** flag:
  a limited walk is not the full corpus and is `ARGV_PIN_DRIFT`. The plan for T02 says "Do not pass
  `--limit`" and `c4_binding.limit` must therefore be `null`.
- **binary pin** — `binary.path` and `binary.sha256`, equal to `build_inputs.binary_sha256`
  (`BINARY_HASH_MISSING`).
- **toolchain pin** — `toolchain.rustc`, `toolchain.cargo` and `toolchain.commands_exit_code`
  (`TOOLCHAIN_PIN_MISSING`).
- **source revision** — `source_revision` is a caller pin recorded by the caller. It is never the
  GSD aggregate and never a `sha256:` digest; a digest in that field is `SOURCE_REVISION_MISSING`
  (the field would then name a tree state that the attempt never bound to).
- **contract pin** — `contract.path`, `contract.sha256` (equal to
  `build_inputs.contract_sha256`), `contract.version = npa-acceptance-contract/v1`,
  `contract.check_id = c4-live-check`, `contract.mode = runtime`.
- **location pins** — the attempt writes `prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json`
  and its logs under `prd/migration/rust-evidence/m207-s04-c4-attempts/<attempt_id>/`
  (`stdout.log`, `stderr.log`), from the release binary
  `target/release/npa-contour-diagnostics`. A later attempt is a **new** receipt under a new
  `attempt_id`; an existing receipt and its logs are never overwritten in place.
- **corpus counts** — `corpus.consultant_xml_count`, `corpus.consultant_root`,
  `corpus.garant_file_count`, `corpus.garant_root`, pinned by §5 (`CORPUS_COUNT_DRIFT`).
- **duration and budget** — `duration_ms` (observed) and `budget_seconds` (declared ceiling,
  `>= 3600`) (`DURATION_MISSING`, `BUDGET_BELOW_MINIMUM`).
- **terminal facts** — `terminal.outcome`, `terminal.exit_code`, `terminal.signal`,
  `terminal.timeout`, closed and required (§4) (`TERMINAL_OUTCOME_DRIFT`).
- **log hashes** — `logs.stdout`, `logs.stderr` (repository-relative paths under
  `prd/migration/rust-evidence/m207-s04-c4-attempts/<attempt_id>/`) plus `logs.stdout_sha256` and
  `logs.stderr_sha256` (`LOG_HASH_MISSING`, `ATTEMPT_LOG_MISSING`).
- **claims** — `claims.operational_acceptance` and `claims.receipt_is_runtime_attempt`, both
  computed by the frozen rule of §4 and never hand-edited afterwards.

**Wall-clock fields are lawful here and forbidden in the battery.** The receipt *is* a process
record: `duration_ms`, `started_at` and `finished_at` are exactly the evidence it exists to carry.
The tracked integrity battery is a byte-stable projection and may carry no wall-clock key at all
(`BATTERY_WALLCLOCK_FORBIDDEN`). One rule per artifact class; the gate applies the wall-clock scan
only to the battery subtree and enforces the receipt closure structurally.

## 4. Terminal outcomes: non-pass is published as-is

`terminal.outcome` is closed at `complete | nonzero | timeout | launch_error | not-run`.
`claims.operational_acceptance` is closed at `pass | non-pass` and is computed by the rule reused
verbatim from M204/S06:

> `pass` only when `terminal.outcome == "complete"` **and** `terminal.exit_code == 0` **and**
> `duration_ms >= budget_seconds * 1000`. Every other combination is `non-pass`.

S04 does not relax that rule. A walk that completes in less than the declared budget is published
`non-pass` rather than promoted, because a short walk is not evidence that the corpus envelope was
exercised; a walk that exceeds the budget is killed and published `timeout`.

- `timeout` sets `timeout = true`, `exit_code = null`, `signal = "SIGTERM"` and is produced by
  killing the **process group** of the walk, so no child parser survives the attempt.
- `outcome_rewrite_forbidden` and `timeout_is_never_accepted` are both `true`: a later unit may
  add a *new* attempt, but it may never edit an existing receipt, and a timeout may never become a
  completion (`C4_TIMEOUT_AS_PASS`).
- The pinned M204/S06 receipt stays a prior **non-pass** forever: `terminal.outcome = timeout`,
  `signal = SIGTERM`, `timeout = true`, `claims.operational_acceptance = non-pass`. Rewriting it —
  or re-pinning a "successful" successor in its place — is `C4_TIMEOUT_AS_PASS`.
- The same diagnostic covers the second laundering path: reading `terminal.outcome = complete` or
  the `M207_S04_VERIFY_OK` marker as a C4 pass / gold / pilot-scale proof
  (`INTEGRITY_MARKER_AS_ACCEPTANCE` names the marker variant).
- `budget_seconds` is a ceiling, not an achievement: `budget_is_a_ceiling_not_an_achievement` is
  `true`, and nothing in the receipt claims that the walk reached it.

## 5. Corpus pins and reproducible inputs

The walk is reproducible only against a declared corpus. The pins are:

| Pin | Value |
|---|---|
| `consultant_root` | `consru_export/consru_export/exports` |
| `consultant_xml_suffix` | `.xml` |
| `consultant_xml_count` | `43785` |
| `garant_root` | `law-source/garant` |
| `garant_file_count` | `12` |

The count basis is the recursive file count under the declared root, identical to the M204/S06
basis, and the gate re-counts the live tree on every `check`. A count that differs is
`CORPUS_COUNT_DRIFT` — including the tempting case of "the corpus grew, so update the pin": the
pin is the slice contract, and moving it requires editing this protocol and the schema together.

No semantic input is published here. The counts are a **corpus pin**, not promotion evidence, not
intake evidence, and not proof that the consultant drop zone behaves correctly (R069 is untouched).
Reading the declared roots is all S04 does; it implements no intake, no quarantine and no atomic
promotion.

## 6. Promotion contract: nothing is promoted

Frozen in `promotion_contract`, rejected by name wherever it appears as a scalar:

| Field | Frozen value | Diagnostic if moved |
|---|---|---|
| `promotion` | `none` | `PROMOTION_CLAIM` |
| `classification` | `not-authorized` | `CLASSIFICATION_REQUESTED` |
| `threshold` | `null` | `THRESHOLD_REQUESTED` |
| `human_acceptance` | `null` | `GOLD_CLAIM` |
| `is_gold` | `false` (admitted only as the pinned-false guard) | `IS_GOLD_CLAIM` |
| `model_invoked` | `false` | `MODEL_INVOKED` |
| `legal_claim` | `forbidden` | `AUTHORITY_CLAIM` |
| `n2_claim` | `forbidden` | `AUTHORITY_CLAIM` |

`rate_publication` and `measurement_status_publication` are `forbidden`: S04 publishes no rate and
no `measurement_status`, because it has no resolved reference and ran no pilot.
`corpus_complete_is_not_acceptance` is `true` — a green walk over 43 785 documents is a process
fact, and `complete` never means gold, legal truth, N2 acceptance or product quality.

## 7. S03 isolation: rates stay not-measured

S04 and S03 are separate contours and S04 must not become a second measurement convention:

- `prd/migration/rust-evidence/m207-s03-evaluation-report.json` **must be absent**. If it appears
  while the S03 battery still records `human_pilot_performed = false`, the run is
  `REPORT_WITHOUT_HUMAN_DATA`: a report without a validated human reference is not a measurement,
  it is a fabricated denominator.
- The S03 battery stays current and keeps `human_pilot_performed = false`; a battery that claims
  the pilot ran while the report is absent is `S03_BATTERY_PILOT_PERFORMED`, and a damaged or
  unreadable battery is `FROZEN_SOURCE_DRIFT`.
- No S04 artifact may import, embed, re-derive or re-publish an S03 aspect value, stratum rate,
  denominator or `measurement_status` (`S03_RATE_IMPORTED`). S04 does not read the S03 evaluation
  contract to "reuse" its numbers; it pins that contract only to keep it frozen.
- The 180-fragment seed stays frozen: the fragment count is 180, its aggregate digest is pinned,
  and the rule-seed sidecar is pinned by digest. A nineteenth file is `SEED_ENLARGED`; a modified
  fragment is `SEED_DRIFT`.
- `crates/**` may not reference the offline harness at all: `m207-s03`, `m207_s03`, `m207-s04` and
  `m207_s04` are forbidden tokens in every tracked file under `crates/` (`S03_RATE_IMPORTED`).
  The product runtime gains no reader of an S04 or S03 artifact (D466/D487).

## 8. Requirement bindings and HOLD pins

S04 is a **supporting** contour for R038, R063, R064, R071 and R077: it supplies evidence, never a
status change. R035 and R070 are touched only as **HOLD pins**: a corpus walk is operational
diagnostics, not `GATE-PILOT-SCALE-READINESS` and not corpus-scale edition provenance.

The frozen re-test commands (T04 runs them; a green pin is not a status change):

- `cargo test -p ln-kb-ontology --offline --test r035_proof_gate`
- `cargo test -p ln-temporal --offline --test r070_proof_gate`
- `cargo test -p ln-decode --offline --test npa_lawref_sample_contract`

`validated_ids` and `invalidated_ids` are both empty, `status_effect` is `unchanged`, and
`requirement_closure_forbidden` is `true`. `D444`, `D466` and `D487` are reaffirmed; `D388`,
`D416`, `D430` and `D495` are untouched. R071's table drift is not repaired from S04.

## 9. Fail-closed diagnostics

Every S04 tool is fail-closed: a non-zero exit with a named, machine-distinguishable diagnostic
from the closed vocabulary in `$.diagnostics`, never a silent success and never a fabricated
artifact. A tool that speaks a name outside that vocabulary is `DIAGNOSTIC_TABLE_DRIFT`.

The honesty core of this slice:

- **no receipt, no success.** An absent receipt is `C4_RECEIPT_MISSING`; the gate never runs the
  walk and never reconstructs a receipt from logs, from the battery or from a documentation file.
- **no rewrite.** A timeout/nonzero/launch_error receipt is published as-is; editing it or pinning
  a successor in its place is `C4_TIMEOUT_AS_PASS`.
- **no marker promotion.** `M207_S04_VERIFY_OK` is printed only by the integrity battery and means
  the battery passed (`INTEGRITY_MARKER_AS_ACCEPTANCE` otherwise).
- **no report without human data, no human data without a report.** The S03 pair stays consistent
  and S04 imports neither half (`REPORT_WITHOUT_HUMAN_DATA`, `S03_RATE_IMPORTED`).
- **no seed growth.** The 180 fragments stay 180 (`SEED_ENLARGED`).

## 10. Lifecycle markers and non-claims

Every derived S04 artifact carries the lifecycle markers:

| Marker | Value | Meaning |
|---|---|---|
| `human_adoption` | `pending` | no human has adopted the operational attempt |
| `runtime_stop_active` | `true` | runtime remains stopped |
| `selected_d388_gates` | `none` | no D388 gate is selected by this work |
| `requirement_status_effect` | `unchanged` | R038/R063/R064/R071/R077 stay as they are |
| `review_disposition_effect` | `unchanged` | review dispositions are untouched |

Non-claims, enforced as an exact frozen list by the executable gate:

1. **not gold** — no S04 artifact, receipt field or terminal outcome is a gold label;
2. **not a promotion** — promotion stays `none`, classification stays `not-authorized`, threshold
   stays `null`;
3. **not a threshold** — no rate threshold, pass/fail cut-off or accept/reject decision is
   introduced;
4. **not a classification** — no classifier is fitted, no gate is selected and no D388 gate is
   scored;
5. **not independent-measured** — S04 performs no human pilot and publishes no independently
   measured rate;
6. **not an S03 rate publication** — the S03 evaluation report stays absent and no S03 aspect or
   stratum rate is imported or synthesized;
7. **not a seed enlargement** — the 180 frozen fragments, the M199 sample manifest and the
   rule-seed sidecar stay frozen;
8. **not an R035 closure** — a corpus walk is operational diagnostics, not
   GATE-PILOT-SCALE-READINESS;
9. **not an R070 closure** — a corpus walk is not edition provenance and not an amending-act chain;
10. **not a requirement status change** — `requirement_status_effect` stays unchanged and
    R038/R063/R064/R071/R077 stay supporting-only;
11. **not human acceptance** — `human_acceptance` stays `null`;
12. **not system quality** — operational completion is a process fact, never product, legal or N2
    quality;
13. **not a product surface** — S04 stays an offline Python harness under `scripts/` and no
    `crates/` file references it;
14. **not a terminal-outcome rewrite** — timeout, nonzero and launch_error are published as-is and
    never rewritten to `complete`;
15. **not a marker promotion** — `M207_S04_VERIFY_OK` means the integrity battery ran, not a C4
    pass;
16. **not a budget achievement** — `budget_seconds` is a ceiling, not evidence that the walk
    reached it;
17. **not a second measurement convention** — `npa-quality-receipts/v1`, `npa-c5-*` and
    `npa-lawref-seed/v1` inputs are refused.

## 11. Boundaries

S01 owns the codebook and the selected cases; S02 owns the two human passes, the kit, the
submission contract, the agreement and the separate adjudication; S03 owns the derived per-aspect
rates and strata; S04 owns the fresh pinned operational attempt over the full declared corpus. S04
never edits a frozen input, never re-runs S03, never enlarges the seed, and never changes a
`crates/**` file to make an operational number look different (D444: an external process-only
receipt is not a repair of the Rust `operational_envelope.run_status`).

Schema ids are disjoint by construction: S04 owns `m207-s04-*` and reuses
`m204-s06-c4-operational-receipt/v1` for the receipt. No S04 schema id may collide with an
`m207-s01-*`, `m207-s02-*` or `m207-s03-*` id.

## Machine-readable protocol contract

The block below is the machine-readable half of this protocol. The executable gate
(`scripts/m207_s04_schemas.py`) parses it, compares it field-by-field with
`prd/annotation/m207-s04-schemas.json`, re-counts the live corpus, re-reads the pinned inputs and
fails closed on any drift. Edit this block and the schema together, or not at all.

```json
{
  "protocol_id": "m207-s04-c4-protocol/v1",
  "schema_id": "m207-s04-c4-schemas/v1",
  "receipt_schema_id": "m204-s06-c4-operational-receipt/v1",
  "receipt_schema_reused_verbatim": true,
  "frozen_sources": {
    "npa_acceptance_contract": {
      "path": "prd/architecture/npa-acceptance-contract.yaml",
      "sha256": "34e8a38a4bd7619d35e8bc2c1294e3a9bc77179b3385d9b5d9161157220d51e3"
    },
    "m204_s06_c4_operational_receipt": {
      "path": "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json",
      "sha256": "04e41f896f2bded096061d7caef2ec4abdaaf37cebf88c387d1dd011943b797c"
    },
    "m207_s03_battery": {
      "path": "prd/migration/rust-evidence/m207-s03-battery.json",
      "sha256": "76b9a78e3e83772be3ca3e46b83a89b3b3baaf690ffe6aa0c72f77aa6d56b533"
    },
    "m207_s03_schemas": {
      "path": "prd/annotation/m207-s03-schemas.json",
      "sha256": "34d874e59b16e356e5658b7eec45d3fef01a4342592728f10f122b0126903456"
    },
    "m199_s01_sample_manifest": {
      "path": "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json",
      "sha256": "134751f49db1858329248be1857ada669097f1860609090028c7b5af8975574f"
    },
    "m199_seed_sidecar": {
      "path": "crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json",
      "sha256": "b88e5af14bcc9496c4d35627afda058d58956f459106c147f1cc7959a6930f28"
    }
  },
  "prior_non_pass_pin": {
    "path": "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json",
    "sha256": "04e41f896f2bded096061d7caef2ec4abdaaf37cebf88c387d1dd011943b797c",
    "attempt_id_pin": "full-walk-timeout-001",
    "terminal_outcome_pin": "timeout",
    "terminal_signal_pin": "SIGTERM",
    "timeout_flag_pin": true,
    "operational_acceptance_pin": "non-pass",
    "may_be_rewritten": false,
    "diagnostic": "C4_TIMEOUT_AS_PASS"
  },
  "receipt_contract": {
    "schema_id": "m204-s06-c4-operational-receipt/v1",
    "schema_reused_verbatim": true,
    "binary_path_pin": "target/release/npa-contour-diagnostics",
    "receipt_path": "prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json",
    "attempt_log_dir": "prd/migration/rust-evidence/m207-s04-c4-attempts",
    "attempt_log_files": [
      "stdout.log",
      "stderr.log"
    ],
    "new_attempt_policy": "a later attempt is a new receipt under a new attempt_id; an existing receipt and its logs are never overwritten in place",
    "closed_keys": [
      "schema",
      "attempt_id",
      "immutable_attempt_identity",
      "argv",
      "binary",
      "build_inputs",
      "toolchain",
      "parser_revision",
      "source_revision",
      "contract",
      "corpus",
      "observed_output",
      "c4_binding",
      "started_at",
      "finished_at",
      "duration_ms",
      "budget_seconds",
      "terminal",
      "logs",
      "claims",
      "non_claims"
    ],
    "required_keys": [
      "schema",
      "attempt_id",
      "immutable_attempt_identity",
      "argv",
      "binary",
      "build_inputs",
      "toolchain",
      "source_revision",
      "contract",
      "corpus",
      "observed_output",
      "c4_binding",
      "started_at",
      "finished_at",
      "duration_ms",
      "budget_seconds",
      "terminal",
      "logs",
      "claims",
      "non_claims"
    ],
    "nested_closed_keys": {
      "immutable_attempt_identity": [
        "attempt_id",
        "argv_sha256"
      ],
      "binary": [
        "path",
        "sha256"
      ],
      "build_inputs": [
        "binary_sha256",
        "contract_sha256",
        "parser_source_sha256"
      ],
      "toolchain": [
        "rustc",
        "cargo",
        "commands_exit_code"
      ],
      "contract": [
        "path",
        "sha256",
        "version",
        "check_id",
        "mode"
      ],
      "corpus": [
        "consultant_xml_count",
        "consultant_root",
        "garant_file_count",
        "garant_root"
      ],
      "observed_output": [
        "stdout_sha256",
        "inventory_digest"
      ],
      "c4_binding": [
        "profile",
        "limit",
        "jobs",
        "inventory_scope",
        "baseline_sha256"
      ],
      "terminal": [
        "outcome",
        "exit_code",
        "signal",
        "timeout"
      ],
      "logs": [
        "stdout",
        "stderr",
        "stdout_sha256",
        "stderr_sha256",
        "inventory_digest"
      ],
      "claims": [
        "operational_acceptance",
        "receipt_is_runtime_attempt"
      ]
    },
    "identity_fields": [
      "attempt_id",
      "argv_sha256"
    ],
    "argv_sha256_basis": "sha256 over json.dumps(argv, separators=(',', ':')), reused verbatim from the M204/S06 emitter",
    "argv_required_flags": [
      "--root",
      "--garant-root",
      "--profile",
      "--jobs",
      "--acceptance-contract",
      "--source-revision"
    ],
    "argv_forbidden_flags": [
      "--limit"
    ],
    "profile_pin": "contour",
    "jobs_pin": 0,
    "limit_pin": null,
    "contract_version_pin": "npa-acceptance-contract/v1",
    "contract_check_id_pin": "c4-live-check",
    "contract_mode_pin": "runtime",
    "binary_hash_fields": [
      "binary.sha256",
      "build_inputs.binary_sha256"
    ],
    "binary_hash_fields_must_be_equal": true,
    "contract_hash_fields": [
      "contract.sha256",
      "build_inputs.contract_sha256"
    ],
    "contract_hash_fields_must_be_equal": true,
    "source_revision_basis": "caller pin recorded by the caller; never a GSD aggregate and never a sha256 digest",
    "source_revision_digest_forbidden": true,
    "log_path_fields": [
      "logs.stdout",
      "logs.stderr"
    ],
    "log_hash_fields": [
      "logs.stdout_sha256",
      "logs.stderr_sha256"
    ],
    "duration_field": "duration_ms",
    "budget_field": "budget_seconds",
    "budget_seconds_minimum": 3600,
    "budget_is_a_ceiling_not_an_achievement": true,
    "terminal_closed_keys": [
      "outcome",
      "exit_code",
      "signal",
      "timeout"
    ],
    "terminal_required_keys": [
      "outcome",
      "exit_code",
      "signal",
      "timeout"
    ],
    "outcome_values": [
      "complete",
      "nonzero",
      "timeout",
      "launch_error",
      "not-run"
    ],
    "accepted_outcomes": [
      "complete"
    ],
    "non_pass_outcomes": [
      "nonzero",
      "timeout",
      "launch_error",
      "not-run"
    ],
    "acceptance_values": [
      "pass",
      "non-pass"
    ],
    "acceptance_rule": "operational_acceptance is pass only when terminal.outcome is complete, terminal.exit_code is 0 and duration_ms >= budget_seconds * 1000; every other combination is non-pass",
    "acceptance_rule_source": "m204-s06-c4-operational-receipt/v1, reused verbatim; S04 does not relax it",
    "timeout_is_never_accepted": true,
    "outcome_rewrite_forbidden": true,
    "process_group_kill": {
      "signal": "SIGTERM",
      "scope": "process group of the launched walk",
      "timeout_flag": true,
      "exit_code_on_timeout": null
    },
    "immutable_attempt_identity": true,
    "attempt_identity_rebuild_forbidden": true,
    "receipt_rebuild_forbidden": true
  },
  "corpus_pins": {
    "consultant_root": "consru_export/consru_export/exports",
    "consultant_root_is_declared_not_derived": true,
    "consultant_xml_suffix": ".xml",
    "consultant_xml_count": 43785,
    "garant_root": "law-source/garant",
    "garant_file_count": 12,
    "count_basis": "recursive file count under the declared root, identical to the M204/S06 basis",
    "count_is_a_corpus_pin_not_promotion_evidence": true,
    "drift_diagnostic": "CORPUS_COUNT_DRIFT"
  },
  "promotion_contract": {
    "promotion": "none",
    "classification": "not-authorized",
    "threshold": null,
    "human_acceptance": null,
    "is_gold": false,
    "model_invoked": false,
    "legal_claim": "forbidden",
    "n2_claim": "forbidden",
    "rate_publication": "forbidden",
    "measurement_status_publication": "forbidden",
    "corpus_complete_is_not_acceptance": true,
    "integrity_marker_is_not_acceptance": true
  },
  "s03_isolation": {
    "evaluation_report_path": "prd/migration/rust-evidence/m207-s03-evaluation-report.json",
    "evaluation_report_must_be_absent": true,
    "s03_battery_path": "prd/migration/rust-evidence/m207-s03-battery.json",
    "s03_battery_human_pilot_performed_required": false,
    "s03_rates_required_status": "not-measured",
    "rate_import_forbidden": true,
    "seed_fragment_root": "crates/ln-decode/tests/fixtures/npa-lawref",
    "seed_fragment_glob": "*.txt",
    "seed_fragment_count": 180,
    "seed_aggregate_sha256": "50b48668cba5b89d75af0604a78004404310e36377679984273fa0a883053c9d",
    "seed_aggregate_basis": "sha256 over sorted lines '<file name>\\0<file sha256>\\n'",
    "seed_sidecar_path": "crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json",
    "seed_sidecar_sha256": "b88e5af14bcc9496c4d35627afda058d58956f459106c147f1cc7959a6930f28",
    "crates_reference_forbidden": true,
    "crates_reference_patterns": [
      "m207-s03",
      "m207_s03",
      "m207-s04",
      "m207_s04"
    ],
    "crates_reference_scope": "every tracked file under crates/, excluding target/ and .git/",
    "seed_enlarge_diagnostic": "SEED_ENLARGED",
    "seed_drift_diagnostic": "SEED_DRIFT"
  },
  "requirement_bindings": {
    "supporting_ids": [
      "R038",
      "R063",
      "R064",
      "R071",
      "R077"
    ],
    "hold_pin_ids": [
      "R035",
      "R070"
    ],
    "hold_pin_commands": [
      "cargo test -p ln-kb-ontology --offline --test r035_proof_gate",
      "cargo test -p ln-temporal --offline --test r070_proof_gate",
      "cargo test -p ln-decode --offline --test npa_lawref_sample_contract"
    ],
    "validated_ids": [],
    "invalidated_ids": [],
    "status_effect": "unchanged",
    "requirement_closure_forbidden": true,
    "evaluation_report_forbidden": true,
    "decisions_reaffirmed": [
      "D444",
      "D466",
      "D487"
    ],
    "decisions_untouched": [
      "D388",
      "D416",
      "D430",
      "D495"
    ]
  },
  "integrity_marker": {
    "marker": "M207_S04_VERIFY_OK",
    "meaning": "the S04 integrity battery ran and every check passed",
    "does_not_mean": [
      "C4 pass",
      "operational acceptance",
      "independent-measured rates",
      "gold",
      "requirement closure"
    ],
    "marker_is_not_acceptance": true,
    "marker_values": [
      "M207_S04_VERIFY_OK"
    ],
    "battery_path": "prd/migration/rust-evidence/m207-s04-battery.json",
    "diagnostic": "INTEGRITY_MARKER_AS_ACCEPTANCE"
  },
  "diagnostics": [
    "PROMOTION_CLAIM",
    "GOLD_CLAIM",
    "IS_GOLD_CLAIM",
    "THRESHOLD_REQUESTED",
    "CLASSIFICATION_REQUESTED",
    "MODEL_INVOKED",
    "AUTHORITY_CLAIM",
    "LEAK_FORBIDDEN_KEY",
    "C4_RECEIPT_MISSING",
    "C4_RECEIPT_DRIFT",
    "C4_TIMEOUT_AS_PASS",
    "INTEGRITY_MARKER_AS_ACCEPTANCE",
    "BUDGET_BELOW_MINIMUM",
    "TERMINAL_OUTCOME_DRIFT",
    "ARGV_PIN_DRIFT",
    "CORPUS_COUNT_DRIFT",
    "LOG_HASH_MISSING",
    "ATTEMPT_LOG_MISSING",
    "IMMUTABLE_IDENTITY_MISSING",
    "BINARY_HASH_MISSING",
    "TOOLCHAIN_PIN_MISSING",
    "SOURCE_REVISION_MISSING",
    "DURATION_MISSING",
    "PROXY_INPUT_REFUSED",
    "REPORT_WITHOUT_HUMAN_DATA",
    "S03_RATE_IMPORTED",
    "S03_BATTERY_PILOT_PERFORMED",
    "S03_REGRESSION_FAILED",
    "SEED_ENLARGED",
    "SEED_DRIFT",
    "HOLD_PIN_FAILED",
    "REQUIREMENT_STATUS_CLAIM",
    "BATTERY_STALE",
    "BATTERY_WALLCLOCK_FORBIDDEN",
    "EMPTY_SUITE",
    "SUBCLI_FAILURE",
    "HOSTILE_CASE_MISSING",
    "MACHINERY_MARKER_MISSING",
    "FROZEN_SOURCE_DRIFT",
    "MISSING_ARTIFACT",
    "MISSING_SECTION",
    "MISSING_NON_CLAIM",
    "MISSING_LIFECYCLE_MARKER",
    "MISSING_SCHEMA",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "DUPLICATE_JSON_KEY",
    "DIAGNOSTIC_TABLE_DRIFT",
    "VOCABULARY_DRIFT",
    "UNSAFE_PATH"
  ],
  "required_sections": [
    "1. Scope, framing and ownership",
    "2. Frozen inputs, pins and admissibility",
    "3. C4 receipt contract: process facts only",
    "4. Terminal outcomes: non-pass is published as-is",
    "5. Corpus pins and reproducible inputs",
    "6. Promotion contract: nothing is promoted",
    "7. S03 isolation: rates stay not-measured",
    "8. Requirement bindings and HOLD pins",
    "9. Fail-closed diagnostics",
    "10. Lifecycle markers and non-claims",
    "11. Boundaries",
    "Machine-readable protocol contract"
  ],
  "non_claims": [
    "not gold: no S04 artifact, receipt field or terminal outcome is a gold label",
    "not a promotion: promotion stays none, classification stays not-authorized and threshold stays null",
    "not a threshold: no rate threshold, pass/fail cut-off or accept/reject decision is introduced",
    "not a classification: no classifier is fitted, no gate is selected and no D388 gate is scored",
    "not independent-measured: S04 performs no human pilot and publishes no independently measured rate",
    "not an S03 rate publication: the S03 evaluation report stays absent and no S03 aspect or stratum rate is imported or synthesized",
    "not a seed enlargement: the 180 frozen fragments, the M199 sample manifest and the rule-seed sidecar stay frozen",
    "not an R035 closure: a corpus walk is operational diagnostics, not GATE-PILOT-SCALE-READINESS",
    "not an R070 closure: a corpus walk is not edition provenance and not an amending-act chain",
    "not a requirement status change: requirement_status_effect stays unchanged and R038/R063/R064/R071/R077 stay supporting-only",
    "not human acceptance: human_acceptance stays null",
    "not system quality: operational completion is a process fact, never product, legal or N2 quality",
    "not a product surface: S04 stays an offline Python harness under scripts/ and no crates file references it",
    "not a terminal-outcome rewrite: timeout, nonzero and launch_error are published as-is and never rewritten to complete",
    "not a marker promotion: M207_S04_VERIFY_OK means the integrity battery ran, not a C4 pass",
    "not a budget achievement: budget_seconds is a ceiling, not evidence that the walk reached it",
    "not a second measurement convention: npa-quality-receipts/v1, npa-c5-* and npa-lawref-seed/v1 inputs are refused"
  ],
  "lifecycle": {
    "human_adoption": "pending",
    "runtime_stop_active": true,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged"
  }
}
```
