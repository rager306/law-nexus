# GSD headless supervisor — law-nexus

**Status:** local process helper, `[bounded]` to the active GSD milestone
watcher (default `WATCH_UNIT_GLOB=M20*`, covering M204-w2ktfw through
M210-3afp79 per D442). Not product runtime. Not GSD engine.
**Lifecycle:** keep `gsd headless auto` alive until a **real** product
HARD BLOCK. Agent repairs closeout / hung LLM; the supervisor is a rule
FSM, not a second planner.

Scripts live under the gitignored `.gsd/` overlay (symlink to
`/root/.gsd/projects/3495c0714df3/`). This file is the **tracked**
operator contract. The local playbook
(`.gsd/m203-supervisor-playbook.md`) is a short sensor cheat-sheet. The
watcher selection is generalized by `WATCH_UNIT_GLOB`; M203 references in
this document remain names of the existing local helper files and historical
examples, not a milestone-only scope.

## Authority (fail-closed)

| Surface | Role |
|---------|------|
| `prd/ARCHITECTURE.md` | Living product truth — supervisor never overrides it |
| `doc/adr/**` | Architectural substance |
| GSD engine (`~/.gsd/agent/extensions/gsd/`) | Wedges, closeout, query, journal |
| `.gsd/m203-gsd-supervisor.sh` | Rule FSM (this process) |
| `.gsd/m203-gsd-snapshot.mjs` | Authoritative sensors (wedge / closeout / journal.lastEvent / git) |
| Interactive agent | Repair ruff/clippy/untracked modules; SIGTERM hung LLM when the FSM is not yet loaded |

**Rules**

1. Supervisor is **not** product proof, not a governor, not GitNexus.
2. Do **not** put an LLM or `memory_query` in the hot loop (injection
   rewards archive-era FalkorDB/M004 rows). New failure class →
   `capture_thought` once + this runbook.
3. `[MEMORY]` is leads only. Era beats familiarity (pre-M174 = archive
   until a tracked source confirms otherwise).
4. R035 / R070 stay HOLD until extractor + proof-gate evidence exists.
   Frozen M201 must not change.
5. Raw legal corpus text must not enter tracked artifacts.

## What it is for

- Run `gsd headless auto` **asynchronously** (user preference) and keep
  one child alive across LLM-silent turns, journal date rollover, and
  `cancelled` after a hung model.
- Distinguish **live work** from **zombie dispatch** and from **closeout
  debt**.
- Resume only a wedge the DB still reports open.
- Stop on a real `query.blocked`, disk &lt; 5G, max crash restarts, or
  genuine idle (see below).

## Watcher scope

`WATCH_UNIT_GLOB` defaults to `M20*`. The active-unit guard therefore covers
M204-w2ktfw through M210-3afp79 (and later M20x units) without changing the
FSM's fail-closed rules. A deployment may narrow the glob for a controlled
run, but must not use a milestone-specific idle exemption as a substitute for
checking the queried unit.

What it is **not**: a second auto, a clippy fixer, a `gsd rebuild
markdown` loop, or a reason to `pkill -f 'gsd headless'`.

## Files and runtime paths

| Path | Role |
|------|------|
| `.gsd/m203-gsd-supervisor.sh` | FSM. `--selftest`, `--snapshot` |
| `.gsd/m203-gsd-snapshot.mjs` | `getOpenWedge` + closeout + `journal.lastEvent` + git |
| `.gsd/m203-open-wedge.mjs` | Wedge-only fallback |
| `.gsd/m203-supervisor-playbook.md` | Local sensor table |
| `/tmp/gsd-closeout.mjs` | Agent closeout `status` / `retry` (not called from the FSM) |
| `/tmp/m203-supervisor.log` | Append-only supervisor log |
| `/tmp/m203-supervisor.pid` | Supervisor pidfile |
| `/tmp/m203-supervisor.flock` | Single-instance lock (fd 9) |
| `/tmp/m203-headless-live.pid` | **Only** kill target for hung LLM |
| `/tmp/m203-headless-live.jsonl` | THIS child's `headless_result` |
| `/tmp/m203-headless-live.stderr` | THIS child's stderr (archive before truncate) |
| `/tmp/m203-supervisor-heartbeat.json` | Last query + wall/utime |
| `/tmp/m203-headless-archive/` | Rotated jsonl/stderr |
| `/root/.gsd/projects/3495c0714df3/journal/20*.jsonl` | Date-scoped GSD journal |

WAL holder `gsd` (daemon) is not the child. Do not kill it.

## Order of use (agents)

Do this in order. Do not skip to a second `gsd auto`.

1. **Selftest (if scripts changed, supervisor not yet running, or after
   a disk edit of the FSM):**
   ```bash
   bash -n .gsd/m203-gsd-supervisor.sh
   bash .gsd/m203-gsd-supervisor.sh --selftest
   ```
   Expect `SELFTEST_OK`. Do **not** restart a live supervisor inode just
   to pick up a disk edit (fd 255 holds the old script until boot).

2. **Snapshot — truth, not `query.wedge`:**
   ```bash
   node .gsd/m203-gsd-snapshot.mjs
   # or: bash .gsd/m203-gsd-supervisor.sh --snapshot
   ```
   Read `wedge.wedgeId` / `guardId` / `unitId`, `closeout.n`,
   `journal.lastEvent` (`eventType`, `unitId`, `status`), `git.head`,
   `git.dirtyN`. `gsd headless query` is for `action` / `unitType` /
   `unitId` / `phase` / `active` / `blocked` only. **`query.wedge` is
   always null.**

3. **Classify the live child** (pidfile `/tmp/m203-headless-live.pid`):
   - product bin (`cargo`, `rustc`, `npa-*- --check`) → **never SIGTERM**
   - `action=dispatch` + journal `unit-start` of **this** unit → live LLM,
     journal silence is expected
   - `action=dispatch` + journal last is **another** unit's
     `auto-exit blocked` + wall ≥ 15 min + tiny utime + no product bin
     → **zombie**; SIGTERM **pidfile only**
   - closeout `n>0` (ruff / clippy / untracked modules) → **agent
     repairs the tree**, then `node /tmp/gsd-closeout.mjs retry`. The
     supervisor logs debt and does not `retry`.

4. **Start or leave the supervisor** (one instance):
   ```bash
   # only if /tmp/m203-supervisor.pid is dead AND flock is free
   nohup bash .gsd/m203-gsd-supervisor.sh >> /tmp/m203-supervisor.log 2>&1 &
   ```
   If the pidfile is live, **do not** start a second auto. Never
   `pkill -f 'gsd headless'` in the same cmdline as the launcher
   (MEM983 kills the starter).

5. **Hung LLM (confirmed):** `kill` the **headless pidfile**, leave the
   supervisor. It must log `CLASSIFY cancelled interrupted` then
   `INTERRUPTED RESTART #N resume=W-…`. Recheck: `finalize-retry` is
   `blocking:false` when closeout `n=0` — the wedge acks, query
   advances. Do not treat `cancelled` as “wedge still blocking”.

6. **Idle stop** only when **all** hold: `action=stop` AND no
   `activeTask` AND phase not a work phase
   (`executing|evaluating-gates|planning|refining|summarizing|researching|discussing`)
   AND unit does not match `WATCH_UNIT_GLOB` (default `M20*`). `stop` +
   `active=T01` is wait, not idle. Units matched by the watcher remain
   supervised even when their milestone differs from the historical M203
   helper filenames.

## Sensors (authoritative)

| Signal | Source | `query` JSON? |
|--------|--------|----------------|
| Open liveness wedge | `getOpenWedge(realpath)` via snapshot | **no** |
| Closeout git failure | `listUnresolvedCloseoutFailures()` | no |
| Next unit | `gsd headless query` | yes — action/unit/phase/active/blocked |
| Journal lag | mtime of `journal/20*.jsonl` | no — **today's file may not exist** |
| Journal last event | `journal.lastEvent` | no — query unit can lie |
| Child result | THIS pid jsonl + stderr (archive first) | leftover HARD BLOCK is a lie |
| Product bins | `/proc` `cargo` / `rustc` / `npa-*` | live `--check` is never a hung LLM |
| Git | snapshot `git.head` / `dirtyN` | dirty tree is not a kill reason |

## FSM actions (do / do not)

1. `action=dispatch` + live pid → **never SIGTERM** unless the zombie
   predicate or the pre-dispatch hung predicate below is true. The
   pre-dispatch window is measured from the continuous dispatch unit,
   not process age (“Bounded confirmations”). LLM/journal silence is
   expected (S09 `refine-slice` died 13× on a 1200s stall because
   `refine-slice` / `complete-slice` / `run-uat` were missing from an
   old unit-type whitelist). Stall-exempt is **`action=dispatch`**, not
   a unit-type list.
2. Zombie dispatch (S09 T03, 2026-09-10): query names T03, journal last
   is T02 `auto-exit blocked`, no `unit-start` for **this** unit, wall
   ≥ 15 min, utime tiny, no product bin. SIGTERM **headless pidfile
   only**. After a real `unit-start` of the query unit, do not kill.
3. Resume `--resume-wedge` only if snapshot `wedge.wedgeId` is still
   open. Env `RESUME_WEDGE_ID` is a hint: ignored unless it matches the
   open DB row (stale `W-0ea76246` ×13 after ack).
4. Closeout `n>0` is **debt**, not idle, not a product HARD BLOCK.
   Typical: `ruff format --check` on staged Python (T05
   `npa_s09_battery_report.py`), clippy `-D warnings`, untracked
   modules declared in `lib.rs`. Format **before** retry. Never
   `#[allow]` as the first clippy fix. Never
   `cargo fmt --all --config imports_granularity=Crate`.
5. `headless_result.status=blocked` → one DB resume, else STOP — with
   two bounded exceptions (see “Bounded confirmations” below): a
   `recovery-required` state never restarts at all, and an unchanged
   wedge after a resume is waited out alive instead of being resumed
   again. Crash / timeout / signal increment `crash_restarts` (cap 12).
6. Journal lag without today's file is **not** a stall if dispatch is
   live (2026-09-10.jsonl appeared late; stall used 09-09 mtime).
7. `completed-no-advance` is not fixed by `--resume-wedge` alone: the
   hash of target rows must change (write Q3/Q4 via
   `gsd_save_gate_result`) or the wedge reopens.
8. Do not run `gsd headless rebuild markdown` (MEM912 hang).
9. GitNexus overlay mangles tool stdout that looks like timestamps /
   file hits. Dump sensors to unique files under `.gsd/exec/` and print
   numbered short keys.

## Zombie predicate (loaded on next supervisor boot)

`zombie_verdict` returns yes only if **all** hold:

- query unit is non-empty
- wall ≥ `ZOMBIE_WALL_SECS` (900)
- utime &lt; `ZOMBIE_UTIME_MAX` (250)
- no product bin
- last journal event is **not** `unit-start` (or later progress) of
  **this** query unit
- last event unitId ≠ query unitId **or** last event is
  `auto-exit` / `orchestrator-terminal` / `iteration-end` with status
  `blocked` / `stopped`

Selftest cases: `zombie:T03-vs-T02-blocked`, `zombie:live-unit-start`,
`zombie:product-bin-exempt`, `zombie:short-wall`, `zombie:high-utime`.

## Bounded confirmations (2026-09-24)

Three FSM refinements, each a pure, selftested predicate. All are
fail-closed in the same direction: one noisy sample must neither drop
supervision nor kill a healthy child, and no state may spin restarts.

1. **Blocked confirm (transitional `query.blocked`).** A `query.blocked`
   sample with **no open DB wedge** is transitional more often than
   real — the engine emits `guard-block` / `auto-exit blocked`
   mid-recovery and can still advance (2026-09-22/23 verification-retry
   transitions). The FSM exits on `blocked` only when an open wedge
   backs the blocker or when the **same text** is observed
   `BLOCKED_CONFIRM_SAMPLES` (default 3) consecutive samples
   (`blocked_streak_update` + `blocked_confirm_verdict`). A changed
   text resets the streak. Selftest: `blocked-streak:*`,
   `blocked-transitional:*`.
2. **Pre-dispatch hung window from the continuous dispatch unit.** The
   `HUNG_DISPATCH_SECS` window is measured from the current continuous
   `action|unitType|unitId` dispatch signature
   (`dispatch_timer_update`), **not** from process age: a headless that
   has served units for hours always has process wall ≫ 900 s and
   could kill a healthy pre-dispatch transition on a quiet journal.
   Any non-dispatch query or unit change resets the timer. Process
   wall/utime remain zombie-predicate inputs and stay in the log for
   observability. Selftest: `dispatch-timer:*`,
   `hung:dispatch-elapsed-not-process-age`.
3. **Recovery-required: never loop an unchanged wedge.** When the
   **this child's stderr** matches `recovery already aborted` /
   `task-recovery-abort` / `gsd recover` / `gsd_task_recovery_resume`,
   a canonical Task Attempt recovery is aborted and only the sanctioned
   recovery action can unblock it. Do not search an unscoped journal tail:
   a historical abort for another unit would poison later dispatches.
   Re-running auto repeats the same guard-block with unchanged inputs —
   that is what tripped the engine liveness backstop and minted
   `W-2fc2c52a` (2026-09-23). In this state the FSM **never restarts**
   and **never re-resumes** an unchanged wedge: it waits alive in
   `RECOVERY_WAIT_SECS` (default 120) cycles up to
   `MAX_WEDGE_WAIT_CYCLES` (default 30), then stops with reason
   `recovery-required` and the extracted `recoveryActionId`. An
   unchanged wedge after a resume gets the same alive-wait treatment
   instead of an instant stop or a second identical `--resume-wedge`.
   A fresh wedge is still resumed exactly once (`resume` verdict).
   Selftest: `recovery-required:*`, `wedge-wait:*`.

None of these predicates ever kills a process: only the zombie and
pre-dispatch predicates SIGTERM, and both keep the product-bin guard
(`is_product_bin_live`) intact.

A supervisor process that was started **before** this predicate was
added still runs the old script in memory. Disk edit ≠ live FSM until
the next boot. Do not rewrite the live inode while a task is executing.

## M073 residue: documented-only operator recipe

`prd/migration/rust-evidence/m204-s05-m073-residue-waiver.json` records a
project-local snapshot of the blocked-in-scope `DT-orphan-gsd` residue for
`M073-68ysz1/S01/T01..T04`. It is documentation only: it is not an engine
waiver, does not change lifecycle state, and does not claim delivery of the
archived Python `LegalDomain` surface. The snapshot must not be presented as
a fresh database query; its observation timestamp and source artifacts are
part of the evidence boundary.

If this residue is ever reconsidered, use a **separate human-gated operator
unit** and perform the following recipe only after the operator explicitly
chooses to proceed:

1. Obtain fresh status through sanctioned GSD status/query surfaces for the
   terminal parent `M073-68ysz1`; do not infer current state from this
   snapshot.
2. Record the fresh status and the operator's explicit decision in the
   authorized workflow before any lifecycle action.
3. Confirm the operator has authority to reopen the terminal parent and that
   the intended scope is limited to the named residue.
4. Only the authorized GSD lifecycle workflow may perform a reopen; this
   document and `scripts/m204_s05_process_verify.py` must never perform it.
5. If authority, fresh status, or the human decision is missing, stop
   fail-closed. Do not call `gsd_skip_slice`, `gsd_slice_reopen`,
   `gsd_task_reopen`, or `gsd_task_complete` for these historical tasks.

This recipe is not executed by the S05 verifier or supervisor. Direct
`gsd.db` access, upstream filing claims, and implementation or revival of
archive Python `LegalDomain` remain prohibited.

## Failure classes already paid for (2026-09-10)

| Class | Symptom | Correct move |
|-------|---------|--------------|
| Live refine/complete/UAT | journal silent, `action=dispatch` | leave it |
| Zombie execute-task | query T03, journal T02 `auto-exit blocked`, CPU idle, no product files | SIGTERM headless; INTERRUPTED RESTART |
| Hung complete-slice LLM | query `complete-slice`, journal `auto-exit blocked`, JSONL 0, wall ≫ utime | repair closeout first if `n>0`, then SIGTERM headless |
| Closeout ruff format | `ruff format --check` Failed, check Passed | `uv run ruff format` staged py → `node /tmp/gsd-closeout.mjs retry` |
| `finalize-retry` after repair | snapshot still shows W-… until resume recheck | closeout n=0 → recheck not blocking; wedge acks |
| Stale `RESUME_WEDGE_ID` | every restart passes a gone wedge | resume only DB-open id |
| Plan-slice artifact verification | research cites a path outside the project root | rewrite the citation with project-local evidence and rerun sanctioned verification; do not read the external path |
| Execute-task completion abort | `gsd_task_complete` receives unsupported `escalation`; durable adapter rejects it | retry without `escalation`, preserving supported closeout fields; this is a compatibility workaround, not an engine fix |
| Second auto | pidfile live | do not start |
| Recovery-required (`canonical Task Attempt recovery already aborted`, `task-recovery-abort`) | engine refuses dispatch until `/gsd recover <id>` | never restart, never re-resume the unchanged wedge; alive-wait bounded, then STOP `recovery-required` printing the `recoveryActionId` (2026-09-22: two re-runs tripped the engine liveness backstop and minted `W-2fc2c52a`) |
| Transitional `query.blocked` | one sample, no open wedge, engine mid-recovery | confirm `BLOCKED_CONFIRM_SAMPLES` identical samples before exit; wedge-backed blocker still exits at once |
| `pkill -f 'gsd headless'` | kills the launcher | kill by pidfile |
| `query.wedge` | always null | snapshot |
| Validate technical-verdict deadlock | `validate-milestone` aborts because the technical verdict requires the current criterion and matching settled attempt | engine HARD BLOCK: do not restart auto for another validate, do not sqlite-patch, and do not mark C4 pass; preserve the deadlock evidence and stop |

## Related project surfaces

- This runbook (tracked): [`doc/gsd-headless-supervisor.md`](gsd-headless-supervisor.md)
- Local overlay pointer: `AGENTS.md` (gitignored)
- Local FSM: `.gsd/m203-gsd-supervisor.sh` (selected active units use
  `WATCH_UNIT_GLOB`, default `M20*`)
- Living oracle: [`prd/ARCHITECTURE.md`](../prd/ARCHITECTURE.md)
- ADR index: [`doc/adr/README.md`](adr/README.md)
- GSD tool contract: `AGENTS.md` § GSD tool contract
- Closeout helper: `/tmp/gsd-closeout.mjs`

## M204 S12 validate HARD BLOCK

S12 identity and failure-sidecar evidence are supporting-only. `S12 identity/sidecar is not a settled milestone.validate attempt; do not re-dispatch validate.` The S12 carrier keeps the S09 abort message verbatim, records `engine_fix=not_fixed`, `upstream_issue=not_filed`, `s12_called_validate_milestone=false`, and leaves findings open. This control does not call `gsd_validate_milestone`, patch the database, or claim operational acceptance.

Post-S15 no-artifact validate ×3 is the same S09 engine deadlock; do not re-dispatch validate-milestone as a settled-attempt substitute. The S16 census is supporting-only and does not create a validation projection or alter lifecycle state.

Post-S16 no-artifact validate ×2 plus intercepted predispatch (cancelled, interrupted, `toolCalls=0`, no journal unit-start) is the same S09 engine deadlock; do not re-dispatch validate-milestone as a settled-attempt substitute. The S17 census is supporting-only: its markers are not an engine fix, a C4 pass, a `VALIDATION.md` projection, or a lifecycle transition.

Post-S17 no-artifact validate ×2 plus intercepted predispatch (cancelled, interrupted, `toolCalls=0`, no journal unit-start) is the same S09 engine deadlock; do not re-dispatch validate-milestone as a settled-attempt substitute. The S18 census is supporting-only; `law_nexus_fixable=false`, and its evidence does not repair the engine or promote lifecycle state.

## M204 S21 mixed post-S20 validate window

S21 records four validate dispatches after the S20 completion/UAT boundary: two no-artifact/finalize-retry aborts and two journal-cancelled interrupts. All four dispatches have `unit-start`; the cancelled terminal sessions have `toolCalls=0`, but they are not intercepts and have no finalize fields. Their measured provider error is `Provider error: Connection error.`; this observation is not attributed to the historical SQL trigger defect. The sibling supervisor terminal flow is a separate `closeout-break` event bound to headless PID `1841192`. The STOP message after four retries is not an additional abort and does not define the census abort count.

The fixed evidence is `prd/migration/rust-evidence/m204-s21-post-s20-validate-loop.json`, with sixteen ordered S09–S20 predecessor pins in `prd/migration/rust-evidence/m204-s21-frozen-hashes.json`. Use `bash scripts/m204_s21_t03_verify.sh` for the bounded offline check. It runs the S21 checker in `check` mode, the independent adversarial suite, and documentation/count assertions while preserving census, manifest, and predecessor bytes. It does not inspect live `.gsd` state, call `validate-milestone`, compose evidence, or create `VALIDATION.md`.

Disposition remains supporting-only: `engine_fix=not_fixed`, `law_nexus_fixable=false`, and C4 is `non-pass`. The census does not close requirements or findings and is not an automatic retry substitute; the historical trigger defect remains distinct from the measured provider connection errors.

## M204 S22 source-bound operational control

S22 records an external GSD recovery blocker separately from a bounded Rust C4 control. The blocker remains `gsd_recovery_liveness=blocked-external`, `engine_fix=not_fixed`, `law_nexus_fixable=false`, and `retry_substitute=false`; the S10 duplicate `inventory_digest` reason remains operationally non-pass. S22 does not call `validate-milestone`, retry the engine, or close R035/R070.

The separate control command is `cargo test -p ln-consultant-parser --offline --locked -j 1 --test contour_diagnostics_contract`. The source-bound recorder sets `c4_control=pass` only for the actual zero-exit suite with a non-empty test-result summary. This is not operational acceptance: `c4_operational_acceptance=non-pass`, classification is supporting-only, and lifecycle status is unchanged. A timeout, nonzero result, missing test summary, missing output log, source/output hash drift, or forged promotion fails closed.

`bash scripts/m204_s22_t03_verify.sh` runs the T01 checker, independent S22 subprocess tests, and independent S21/S15 consumers. It then checks exact argv, relative cwd, UTC/monotonic timing, toolchain versions, stdout/stderr hashes, and the tracked Cargo/Rust, S22 evidence, and documentation source set. The host does not rewrite evidence, inspect live/GSD-ignored state, perform a corpus walk, or treat the receipt as a GSD aggregate `testedSourceRevision`.

## Non-claims

Adopting this runbook does **not** claim:

- that any watched milestone (including historical M203 / S09) is
  `[validated]`;
- that R035 / R070 are closed;
- that the supervisor is part of the Rust product or the harness
  governor;
- that `query` JSON is a complete liveness signal;
- that a disk edit of the FSM is live in an already-running supervisor
  process.
