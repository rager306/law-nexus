# M207 S07 — operational successor contract (`m207-s07-c4-protocol/v1`)

**Executable gate:** `uv run python scripts/m207_s07_schemas.py check` (marker
`M207_S07_SCHEMAS_OK`) and `uv run python scripts/m207_s07_schemas.py selftest` (marker
`M207_S07_SCHEMAS_SELFTEST_OK`). The closed schema document is
`prd/annotation/m207-s07-schemas.json` (`m207-s07-schemas/v1`).

**Status.** Frozen S07 protocol. S04/M204 stays byte-stable and keeps
`claims.operational_acceptance = non-pass`. S07 adds a *new* contract beside it: it classifies
the two outcomes the frozen S04 rule conflates — a short complete full walk and a killed walk that
reached the ceiling — without rewriting a single frozen byte and without relaxing the old verdict.

## 1. Scope, boundaries and frozen inputs

S07 is a **successor operational contract**, not a patch. The frozen S04 rule in
`scripts/m207_s04_c4_run.py` (`acceptance_for`) requires
`complete && exit_code == 0 && duration_ms >= budget_seconds * 1000`; a full walk of the corpus
that finishes in ~387 s is therefore published `non-pass` forever, mixed with the timeout case.
That rule is owned by M204/S06 and is **not** edited here. S07 freezes a second, independent
reading beside it, and the old reading keeps its own name and its own verdict.

Nothing in this document touches the product runtime. S07 stays an offline Python harness under
`scripts/` and `prd/`; `crates/**` gains no reader of any M207 artifact.

The frozen inputs, pinned by bare lowercase hex sha256 in `$.frozen_sources` and re-hashed against
the live tree on every `check` (a mismatch is `C4_RECEIPT_DRIFT`):

| Pin name | Path | sha256 |
|---|---|---|
| `m207_s04_c4_protocol` | `prd/annotation/m207-s04-c4-protocol.md` | `11dd5e0bbd29ecd398469be95321fc854d3da323bed2b3b0042c1c6f595642fb` |
| `m207_s04_schemas` | `prd/annotation/m207-s04-schemas.json` | `7d494b55f5bd7b5a6ee5dd7818f4ca3aa61a26dcfb81d1b1c4d2de27df217293` |
| `m207_s04_c4_operational_receipt` | `prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json` | `423d30de06080fce1c3da255d1d03cc3f19548d29e4338c74d913f4771e9e935` |
| `m204_s06_c4_operational_receipt` | `prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json` | `04e41f896f2bded096061d7caef2ec4abdaaf37cebf88c387d1dd011943b797c` |
| `m207_s04_battery` | `prd/migration/rust-evidence/m207-s04-battery.json` | `cc6dbb3933bc8e5d91c3cf7866ed28e40061a5740c77429b923d4e487ade91fc` |
| `m207_s03_battery` | `prd/migration/rust-evidence/m207-s03-battery.json` | `76b9a78e3e83772be3ca3e46b83a89b3b3baaf690ffe6aa0c72f77aa6d56b533` |
| `m199_s01_sample_manifest` | `prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json` | `134751f49db1858329248be1857ada669097f1860609090028c7b5af8975574f` |
| `m199_seed_sidecar` | `crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json` | `b88e5af14bcc9496c4d35627afda058d58956f459106c147f1cc7959a6930f28` |

**What the frozen S04 bytes already prove, and what they do not.** The historical receipt
`m207-s04-c4-operational-receipt.json` records `terminal = {outcome: complete, exit_code: 0,
signal: null, timeout: false}`, `duration_ms = 387174`, `budget_seconds = 3600`. It is a complete
walk in the S07 sense. It is *not* a pass, gold, legal truth, N2 acceptance or product quality,
and S07 does not upgrade it. The prior M204/S06 receipt
`m204-s06-c4-operational-receipt.json` records `terminal = {outcome: timeout, exit_code: null,
signal: SIGTERM, timeout: true}`, `duration_ms = 1009`; it stays a timeout forever.

**`run_status` is not terminal evidence.** `Acc::render` writes `operational_envelope.run_status`
as the literal string `"complete"` before the harness classifies the process
(`crates/ln-consultant-parser/src/contour_diagnostics.rs`, D444). The JSONL therefore carries no
proof that the kill never fired; only the harness receipt records the terminal outcome.

## 2. Predicates: full walk and timeout

S07 defines two **independent, recomputable** predicates. Neither reads a `claims.*` field, a
marker, or a prose verdict; both are recomputed from the receipt's terminal facts and the JSONL
header/payload. The outcome of a walk is the closed set
`full_walk | timeout | nonzero | launch_error`.

**`full_walk`** holds when all of the following are true:

- the attempt argv carries no `--limit` flag;
- `header.limit` is JSON `null` and `canonical_payload.limit` is JSON `null`;
- the corpus equals the pins of §5 (`43785` consultant XML, `12` Garant files);
- `aggregate.files == 43797`;
- `terminal.outcome == "complete"`, `terminal.exit_code == 0`, `terminal.timeout == false`.

**`timeout`** holds when all of the following are true:

- `terminal.outcome == "timeout"`;
- `terminal.exit_code` is JSON `null`;
- `terminal.signal == "SIGTERM"`;
- `terminal.timeout == true`.

**`duration_ms` is recorded and is not a predicate input.** `duration_ms` appears in the receipt
as an observation; it is deliberately absent from both predicate bodies
(`duration_ms_is_not_a_predicate_input` is `true`). A `full_walk` attempt whose
`duration_ms < budget_seconds * 1000` is **lawful and complete**; it is never named `timeout` and
never requires 3600 s of wall clock. The S04 duration floor stays where it is — inside the frozen
S04 rule — and is not imported as an S07 acceptance test
(`duration_floor_is_not_acceptance` is `true`; a floor that reappears in a predicate is
`DURATION_FLOOR_AS_ACCEPTANCE`).

The historical receipt satisfies `full_walk` under this contract, read-only, without rewriting its
bytes or its `claims.operational_acceptance`. The S04 record keeps saying `non-pass`; the S07
classifier says `full_walk`. Both statements are true and neither is a promotion.

## 3. Kill ceiling: budget is a ceiling, not an achievement

`budget_seconds >= 3600` is the **kill ceiling** for the attempt's process group. At the budget the
harness sends `SIGTERM` to the process group and, 30 s later, `SIGKILL`, so no child parser
survives the attempt. Reaching the ceiling produces `timeout`, not success.

`budget_seconds` is therefore not a target, not a stop condition the walk aims at, and not
evidence that the corpus envelope was exercised. A walk that finishes long before the ceiling is
as complete as one that finishes near it; the ceiling only bounds worst-case resource use.
Nothing in the receipt may claim the walk reached the ceiling
(`budget_is_a_ceiling_not_an_achievement`).

## 4. New attempt: identity, paths and write-once

A new S07 attempt is a **new identity** under the `m207-s07-*` namespace. It never lands on an
S04 path and never overwrites an existing artifact.

| Item | Value |
|---|---|
| attempt id | `m207-s07-<slug>-NNN` (slug is a lowercase token; the whole id is unique) |
| attempt directory | `prd/migration/rust-evidence/m207-s07-c4-attempts/<attempt-id>/` |
| receipt | `prd/migration/rust-evidence/m207-s07-c4-operational-receipt.json` |
| failure sidecar | `<attempt-dir>/failures.jsonl` via `--failures-out <attempt-dir>/failures.jsonl` |
| logs | `<attempt-dir>/stdout.log`, `<attempt-dir>/stderr.log` |

Rules:

- **`--limit` is forbidden.** A limited walk is not a full walk and fails the `full_walk`
  predicate at the argv level.
- **`--failures-out` is the new flag** that changes the argv and therefore the identity: adding it
  makes a *new* attempt, never an in-place re-run of an old one. An old argv must not be edited to
  carry it.
- **Write-once.** The receipt, the logs and the sidecar are created once. A second write to the
  same attempt path is refused; a later attempt is a new receipt under a new `attempt_id`.
- **Frozen paths are refused by name.** No S07 command may write to any `frozen_sources` path,
  to `prd/migration/rust-evidence/m207-s04-c4-attempts/` (any file under that prefix), or to
  `prd/migration/rust-evidence/m207-s03-evaluation-report.json`. The declared refusal set lives in
  `$.new_attempt_policy.forbidden_write_paths` and
  `$.new_attempt_policy.forbidden_write_prefixes`; a violation is `C4_RECEIPT_DRIFT`.
- The receipt is written only after the process facts are known; a receipt is never reconstructed
  from logs, from the battery, or from a documentation file.

## 5. Failure policy: sidecar, allowlist and named refusals

The failure sidecar is the existing contour artifact `npa-contour-failure-trace/v1`, reused
**verbatim**. S07 adds no failure type, no retry record and no last-error field to the product.

A sidecar line carries exactly the closed key set
`{record_kind, schema, provider, path, class}`:

| Key | Lawful value |
|---|---|
| `record_kind` | `failure` |
| `schema` | `npa-contour-failure-trace/v1` |
| `provider` | `consultant` or `garant` |
| `path` | repository-relative, under the provider's declared root |
| `class` | `read`, `digest`, `decode` or `toctou` |

The provider roots are `consru_export/consru_export/exports/` for `consultant` and
`law-source/garant/` for `garant`. A path outside its provider root is not a lawful record.

The policy is checked, not asserted:

- `len(sidecar) == aggregate.failed` on the **same** attempt: the sidecar and the JSONL aggregate
  must agree, and the comparison is against *this* attempt's `failed`, never against the historical
  number `1`.
- An empty sidecar is lawful only when `aggregate.failed == 0`.
- `failed > 0` with no sidecar on a **new** attempt is a named policy refusal. It is never a
  reason to append to a historical log or to reconstruct the missing identity from
  `m204-s12-failed-file.json` (a different attempt, a bounded Garant probe).
- When a failing path is outside the allowlist, `record_failure` does not push a sidecar line but
  `observe` still increments `failed`; the CLI then returns `EXIT_OUT_UNWRITABLE` (`3`) and writes
  no sidecar. `exit_code == 3` with an allowlist refusal is a **lawful `nonzero`** outcome
  (`allowlist_refusal`), not a full walk and not a schema hole.
- The sidecar carries `acceptance_effect = none`: a decode failure is not gold, not quality, not a
  rate and not a promotion (D444). Making the failure visible does not make it a measurement.
- The provider and class vocabularies are closed. Adding a retry, a last-error or a
  persistence surface to the product is out of scope; R063 stays supporting/partial.

## 6. Promotion contract: nothing is promoted

| Field | Frozen value | Diagnostic if moved |
|---|---|---|
| `promotion` | `none` | `PROMOTION_CLAIM` |
| `classification` | `not-authorized` | `PROMOTION_CLAIM` |
| `human_acceptance` | `null` | `GOLD_CLAIM` |
| `is_gold` | `false` | `GOLD_CLAIM` |
| `model_invoked` | `false` | `PROMOTION_CLAIM` |
| `legal_claim` | `forbidden` | `PROMOTION_CLAIM` |
| `rate_publication` | `forbidden` | `PROMOTION_CLAIM` |
| `acceptance_effect_of_failures` | `none` | `PROMOTION_CLAIM` |

The 180-fragment seed stays frozen by count and by aggregate digest
(`SEED_ENLARGE` when it grows). `corpus_complete_is_not_acceptance` and
`marker_is_not_acceptance` are both `true`: a green full walk over 43 797 files, and any S07
marker, are process facts about the harness, never gold, legal truth, N2 acceptance, product
quality or a measured rate.

## 7. Human pilot is not a gate (D519)

The human pilot was removed as a gate for this scope (D519,
`prd/annotation/m207-context-presentation-contract.md`). S07 does not wait for submissions, does
not require `human_pilot_performed = true`, and does not treat the S03
`HUMAN_PILOT_ABSENT` / exit-3 boundary as a blocker. `human_pilot_is_not_a_gate` is `true`.
The historical S01–S04 protocol is not rewritten to say otherwise, and no S03 rate is imported.

## 8. Markers and what they do not mean

| Marker | Owner | Means | Does **not** mean |
|---|---|---|---|
| `M207_S07_SCHEMAS_OK` | `scripts/m207_s07_schemas.py check` | the frozen S07 protocol and schema agree with each other and with the live frozen sources | not a C4 pass, not a walk, not gold, not a promotion |
| `M207_S07_SCHEMAS_SELFTEST_OK` | `scripts/m207_s07_schemas.py selftest` | every named hostile mutation produced its named diagnostic | not an operational attempt |
| `M207_S04_C4_RECEIPT_OK` | `scripts/m207_s04_c4_run.py check` | the S04 receipt is intact and honestly `non-pass` | not a full walk in the S07 sense by itself |
| `M207_S04_VERIFY_OK` | `scripts/m207_s04_t04_verify.sh` | the S04 integrity chain ran | not acceptance, not pilot scale |
| `M207_HYBRID_RECORDS_OK` | S05 hybrid records | the hybrid byte contract holds | not operational evidence, not S07 |

A marker is a statement about the tool that printed it. Reading any marker as acceptance, gold or
promotion is `PROMOTION_CLAIM` / `GOLD_CLAIM` by name.

## 9. Non-claims

1. **not gold** — no S07 artifact, predicate, sidecar row or marker is a gold label.
2. **not a promotion** — `promotion` stays `none`, `classification` stays `not-authorized`,
   `human_acceptance` stays `null`.
3. **not a threshold** — no rate threshold, pass/fail cut-off or accept/reject decision is
   introduced; `threshold` stays `null`.
4. **not a classification** — no classifier is fitted, no D388 gate is selected and no gate is
   scored.
5. **not independent-measured** — S07 runs no human pilot and publishes no measured rate; S03
   rates stay `not-measured`.
6. **not a rewrite of S04/M204** — the frozen receipt, its logs, its `claims` and the M204 timeout
   receipt stay byte-identical; a successor attempt is a new identity, not an edit.
7. **not a timeout redefinition** — a short complete walk is not renamed `timeout`, and a timeout
   is never renamed `complete`.
8. **not a budget achievement** — `budget_seconds` is a kill ceiling, not evidence that the
   corpus envelope was exercised to the limit.
9. **not a product surface** — S07 is an offline Python harness; `crates/**` gains no reader and no
   new Rust type, and no serde surface is added.
10. **not a requirement status change** — `status_effect` stays `unchanged`; R035/R070 stay HOLD
    and are not discharged.
11. **not a failure identity for the historical run** — the S04 `failed = 1` file stays
    unidentified; S07 does not attach `m204-s12-failed-file.json` to it.
12. **not a human gate** — the human pilot is not a gate (D519).
13. **not a second measurement convention** — no S03 aspect or stratum rate is imported,
    re-derived or re-published.
14. **not a seed enlargement** — the 180 frozen fragments stay 180.

## 10. Requirement bindings

S07 is a **supporting** contour for R063, R064 and R038: it supplies observable evidence, never a
status change. R035 and R070 are touched only as **HOLD** pins and are not discharged — an
operational walk is not `GATE-PILOT-SCALE-READINESS` and not corpus-scale edition provenance.

- **R064** — the schema and the checker stay harness-local, use only the standard library, and use
  a closed key set. Python remains verification harness only (ADR-0007).
- **R063** — supporting only: the CLI exit codes and the harness terminal facts already exist; the
  sidecar adds last-failure identity for a new attempt, not product retry-persistence.
- **R038** — the marker `M207_S07_SCHEMAS_OK` is not acceptance evidence and does not substitute
  for independent verification; the predicates are recomputed from terminal + JSONL + sidecar, not
  read from a claim field.
- **R035 / R070** — HOLD; S07 does not close, discharge or re-scope them.

`validated_ids` and `invalidated_ids` are both empty, `status_effect` is `unchanged`, and
`requirement_closure_forbidden` is `true`. D444, D519 and D521 are reaffirmed and untouched.

## 11. Fail-closed diagnostics

Every S07 tool is fail-closed: a non-zero exit with a named, machine-distinguishable diagnostic
from the closed vocabulary below, never a silent success and never a fabricated artifact. A code
that appears in a tool but not in this block — or in this block but not in the schema — is
`PROTOCOL_DIAGNOSTIC_DRIFT`, checked in both directions.

The core honesty rules:

- **no artifact, no success.** A missing protocol or schema is `MISSING_ARTIFACT`; the gate never
  reconstructs either from prose.
- **no drift.** A frozen source whose live bytes no longer match its pin is `C4_RECEIPT_DRIFT`; a
  corpus or seed count that moved is `CORPUS_COUNT_DRIFT` / `SEED_ENLARGE`.
- **no duration floor.** A duration field inside a predicate is `DURATION_FLOOR_AS_ACCEPTANCE`;
  a missing or malformed predicate set is `PREDICATE_CONTRADICTION`; a moved outcome set is
  `TERMINAL_OUTCOME_DRIFT`.
- **no promotion.** A moved `promotion` / `classification` is `PROMOTION_CLAIM`; a moved
  `is_gold` / `human_acceptance` is `GOLD_CLAIM`.
- **no unexpected exception.** An unexpected internal failure surfaces as
  `GATE_INTERNAL_ERROR` with a non-empty stdout, never a traceback-only exit.

```text
<!-- s07-diagnostics:begin -->
MISSING_ARTIFACT
MISSING_SECTION
UNSAFE_PATH
SCHEMA_PARSE_ERROR
SCHEMA_KEY_DRIFT
SCHEMA_VERSION_DRIFT
MARKER_CONTRACT_DRIFT
C4_RECEIPT_DRIFT
CORPUS_COUNT_DRIFT
TERMINAL_OUTCOME_DRIFT
PREDICATE_CONTRADICTION
DURATION_FLOOR_AS_ACCEPTANCE
PROMOTION_CLAIM
GOLD_CLAIM
PROTOCOL_DIAGNOSTIC_DRIFT
SEED_ENLARGE
GATE_INTERNAL_ERROR
<!-- s07-diagnostics:end -->
```

`marker_contract` and the lifecycle markers are part of the schema document, not of the prose:
the gate reads `prd/annotation/m207-s07-schemas.json` as the machine-readable contract and this
document as its frozen narrative. Both must agree, and a disagreement is a named diagnostic —
never a silent pass.
