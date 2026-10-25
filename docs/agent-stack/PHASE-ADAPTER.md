# Allspark phase dispatch adapter (prepared integration component)

`scripts/ai/phase-dispatch.py` is the repo-owned glue for the mandatory
integration task in [WORKFLOW.md](WORKFLOW.md) §3: upstream GSD Path 1.6.2 has
no Allspark branch in its shared dispatch contract, so this repository must own
an explicit adapter before operational cutover (see also
[PATH_SETUP.md](PATH_SETUP.md) §5).

**Status: this is a prepared integration component, not a completed handoff.**
The adapter is verified against deterministic stub children only. No real
Allspark/model pilot has been run, no native phase gate has consumed its
records, and the acceptance table in §8 below is **not yet satisfied**.
Runtime/skills compatibility does not by itself prove phase dispatch readiness.

## 1. Contract

The adapter executes one dispatch plan:

- For every role in the plan it starts **one fresh worker child** (the
  configured Allspark `-p` worker), feeds the role brief to the child stdin,
  runs it in the role's assigned cwd, waits up to the role timeout, and captures
  the exit code plus bounded stdout/stderr tails.
- It classifies each child against the Path outcome contract and writes one
  per-role artifact and one summary dispatch record.

The adapter **never**:

- writes Path state, task status, answers, or approvals — state mutations stay
  with native Path helpers (`scripts/ai/path-run.py` and the pinned runtime);
- produces owner approval — no outcome value represents an approval, so no
  child output can be recorded as one;
- retries roles — `maxAttempts` and re-dispatch policy belong to Path;
- interprets or repairs child output — it records what the child produced.

Sequential execution is deliberate (the capacity-1 profile from
`.ai/path-run.json`): roles run one at a time in plan order. Each role is still
a separate fresh process with its own context; briefs are never merged.

## 2. Usage

```bash
python3 scripts/ai/phase-dispatch.py --plan plan.json --record record.json
python3 scripts/ai/phase-dispatch.py --plan plan.json --record record.json --dry-run
# Test override: run a stub argv instead of the configured worker.
python3 scripts/ai/phase-dispatch.py --plan plan.json --record record.json \
  --child-command '["python3", "-c", "print(\"RESULT: T001 ready\")"]'
```

The plan is produced by the owner session from the current native route and
phase contract (WORKFLOW.md §3 "Входы и процессы"). The adapter does not
generate, validate against, or modify native route/phase state.

`--dry-run` validates the plan fully, prints the resolved plan (absolute
paths, worker argv, per-role timeouts) as JSON on stdout, and spawns nothing.
Execution diagnostics go to stderr; stdout carries only the dry-run plan.

## 3. Dispatch plan schema

```json
{
  "schema": 1,
  "phase": "inspect",
  "roles": [
    {
      "name": "inspect_codebase",
      "brief_file": "/abs/path/inspect_codebase.brief.md",
      "cwd": "/abs/path/assigned-worktree",
      "timeout_seconds": 900,
      "artifact": "/abs/path/inspect_codebase.artifact.json"
    }
  ]
}
```

| Field | Rules |
|---|---|
| `schema` | integer, must be `1` |
| `phase` | non-empty string; the Path phase this plan belongs to |
| `roles` | non-empty array; one entry per required role |
| `roles[].name` | non-empty, unique across the plan; the deterministic logical name from the native contract |
| `roles[].brief_file` | absolute path to an existing file; fed verbatim to the child stdin |
| `roles[].cwd` | absolute path to an existing directory; the child's working directory |
| `roles[].timeout_seconds` | positive finite number; per-role wait budget (not a token/dollar budget) |
| `roles[].artifact` | absolute path; the adapter writes the per-role record here (parent directories are created) |

Unknown keys, missing fields, wrong types, non-absolute or non-existent
referenced paths, and duplicate role names are rejected before anything is
spawned (exit 2, message prefixed `plan error:` with a `$.roles[i].field`
pointer). Plan validation is fail-fast: no role runs if any role entry is
invalid.

## 4. Worker command

Without `--child-command` the adapter reads `worker` from
`.ai/path-run.json` (only `schema` and `worker` are consumed; full config
validation lives in `path-run.py`), requires the `-p`/`--print` flag (Path
passes the brief on stdin but adds no headless flag), and resolves `argv[0]`
against the primary checkout (`parents[2]` of the script) — e.g.
`scripts/ai/allspark-worker` becomes `/root/law-nexus/scripts/ai/allspark-worker`.

`--child-command` takes a JSON array of strings and replaces the worker argv
**verbatim** (no path resolution, no `-p` requirement). It exists for
deterministic stub tests; production dispatch uses the configured worker.

## 5. Execution model

Per role, in plan order:

1. Read the brief file bytes.
2. Spawn one child: `argv` as above, `cwd` = the role's assigned directory,
   brief on stdin, own process group (`start_new_session`), inherited
   environment.
3. Wait up to `timeout_seconds`. On timeout: `SIGKILL` the child's whole
   process group, then reap the child (`wait`) so no orphan or zombie remains.
4. Capture stdout/stderr through bounded tail buffers (last 256 KiB per
   stream); the exit code is the observed child status (negative = signal).
5. Classify, write the per-role artifact atomically, emit one stderr status
   line.

A role whose process cannot even be started is recorded as `failed` with the
spawn error in `stderr_tail`; remaining roles still run. If a per-role artifact
cannot be written, the adapter stops immediately (exit 2) and the summary
record is not written — the evidence contract is broken, and silently
continuing would hide it.

Known limitation: an adapter killed by `SIGKILL` mid-role can leave a running
child. Before re-dispatch, check for leftover children as PATH_SETUP.md §6
already requires; the summary record is only written for a fully executed plan.

## 6. Outcome classification

Classification reads the captured stdout tail and mirrors the vendored Path
1.6.2 `dispatch_driver.py` `classify()` precedence: a killed or crashing child
is a failure even when it wrote a question or a RESULT line.

| Priority | Child evidence | Outcome |
|---|---|---|
| 1 | killed on the per-role timeout | `timeout` |
| 2 | non-zero exit code (incl. death by signal) | `failed` |
| 3 | a stdout-tail line containing `NEEDS-ORCHESTRATOR` | `question` |
| 4 | last stdout-tail line matching `RESULT: <task> ready` | `ready` |
| 5 | last stdout-tail line matching `RESULT: <task> blocked` | `blocked` |
| 6 | clean exit with no terminal marker | `failed` |

Notes:

- The RESULT marker is the upstream regex `^RESULT:\s*(\S+)\s+(ready|blocked)\s*$`
  (case-insensitive, last match wins). The adapter does not check that the task
  name in the marker equals the role name; the stdout tail is preserved in the
  artifact so the orchestrator can verify it.
- A clean Allspark exit code is **not** task completion; only the terminal
  RESULT line classifies readiness (WORKFLOW.md §3).
- A `question` is recorded and surfaced (exit 4); the answer itself goes
  through the native Path channel (`path-run.py answer`), never through this
  adapter.

## 7. Records and exit codes

Per-role artifact (one JSON file per role, at `roles[].artifact`):

| Field | Meaning |
|---|---|
| `name` | logical role name from the plan |
| `brief_file`, `cwd` | planned absolute paths |
| `pid` | child process id (`null` only if the spawn itself failed) |
| `started_at`, `ended_at` | UTC ISO-8601 timestamps |
| `duration_ms` | wall-clock duration |
| `exit_code` | observed child status (negative = signal; `null` if the spawn failed) |
| `timed_out` | whether the per-role timeout killed the child |
| `stdout_tail`, `stderr_tail` | bounded capture, last 256 KiB per stream |
| `outcome` | `ready` \| `blocked` \| `question` \| `timeout` \| `failed` |

Summary dispatch record (at `--record`):

```json
{
  "schema": "law-nexus-phase-dispatch/v1",
  "phase": "inspect",
  "started_at": "2026-10-23T12:00:00+00:00",
  "ended_at": "2026-10-23T12:15:00+00:00",
  "roles": ["... per-role records as above ..."],
  "overall": "ready"
}
```

`overall` is the single worst non-ready outcome by severity
`failed > timeout > blocked > question > ready`; when a plan has two or more
distinct non-ready outcomes it is `mixed`. (`timeout` is a valid `overall`
value: a timeout-only plan must not be silently relabeled `failed`, and the
per-role records always carry the precise outcome.)

Exit codes:

| Code | Condition |
|---|---|
| 0 | every role outcome is `ready` |
| 2 | plan error: the `--plan` file is not a valid dispatch plan (unparseable JSON, unknown/missing fields, wrong types, non-absolute or non-existent referenced paths, duplicate names) |
| 3 | usage error: bad CLI arguments, unreadable plan file, malformed `--child-command`, unusable worker configuration, unwritable record |
| 4 | at least one role is `blocked` or `question` (needs orchestrator attention) and none failed or timed out |
| 5 | at least one role `failed` or `timeout` (5 wins over 4) |

## 8. Security and isolation

- The worker cwd is **assigned by Path** (the native dispatcher/task contract);
  the plan merely carries it. The adapter never changes the primary checkout,
  never `chdir`s itself, and never creates worktrees.
- Worker argv resolution against the primary checkout exists only to launch the
  pinned worker; the child still runs in its assigned cwd.
- Children must not start another coordinator, call `rlm.spawn`/factory, or
  delegate further (WORKFLOW.md §3). This is a brief-level rule the adapter
  cannot enforce; it records outcomes only.
- Allspark exit 0 means the call completed, not that the task is done
  (§6). Conversely a non-zero exit is `failed` even if a RESULT line was
  printed.
- stdout/stderr capture is bounded; classification reads the tail. Output that
  scrolled past the 256 KiB tail is not evidence.
- Briefs are read as raw bytes and passed through stdin unmodified.
- The adapter inherits the caller's environment (the shared Allspark profile);
  it does not manage credentials, HOME isolation, or the fork HOME — that is
  the launcher/bootstrap layer (INSTALL.md, ALLSPARK_NOTES.md).

## 9. Acceptance status (WORKFLOW.md §3) — PARTIALLY satisfied

Three rows were proven by a real-model pilot on 2026-10-25 (see §9.1). The
others still require work the pilot did not exercise, and none may be claimed
from this component alone.

| Check (WORKFLOW.md §3) | Required result | Status |
|---|---|---|
| Skill discovery | Internal scripts/references reachable from primary and task worktree | **Satisfied** — a real worker resolved its pinned skills and answered from the primary checkout (§9.1) |
| Cwd | Worker really sees the assigned worktree; primary files do not become its working tree | **Satisfied** — a worker dispatched into `tmp/wt-rolectx` reported that absolute path, not the primary one (§9.1) |
| Fork HOME | Both runtime caches resolve one digest; Git identity/hooks/signing and worktree root agree | **Not satisfied** — outside adapter scope (doctor/bootstrap) |
| Role isolation | Two independent briefs get different fresh contexts | **Satisfied** — two roles in one plan ran as separate fresh processes with different cwds and produced different, correct answers (§9.1) |
| Planner/Research | Real outputs pass native gates; no emulated status | **Not satisfied** — no real planner/research role run; the pilot was an inspect-shaped probe, not a gated plan |
| Error/timeout | A wrong result never becomes success; the child is accounted for and stopped | **Partially satisfied** — two real failures were classified `failed` with the child's own stderr captured (`no model selected`, `model unavailable`); SIGTERM/timeout paths remain stub-tested |
| Question | A blocking question and the real answer go through the intended Path channel | **Not satisfied** — the adapter only classifies questions; the answer path stays with native helpers |
| Build→Review | A separate reviewer checks the landed scope per contract | **Not satisfied** — no real wave review dispatched |
| Resume | After the owner process ends, a new session picks the correct native route | **Not satisfied** — outside adapter scope |
| Approval | Neither API nor wrapper produces owner approval automatically | **Not satisfied as acceptance evidence** — enforced by design (no approval outcome exists), stub-tested only |

### 9.1 Real-model pilot (2026-10-25)

Model: `zai/glm-5.3-flash`, thinking `high`, through the repository launcher
(`scripts/ai/allspark --role worker -p`), i.e. the production path — not
`--child-command`.

| Run | Plan | Result |
|---|---|---|
| single role | one inspect role, cwd `/root/law-nexus` | `outcome=ready`, exit 0, 12.9 s; stdout `law-nexus` + `RESULT: T001 ready` |
| two roles | `ctx_primary` (primary) + `ctx_worktree` (`tmp/wt-rolectx`) | both `ready`, exit 0; the second role reported `/root/law-nexus/tmp/wt-rolectx` |

The second row is the one that matters: the two children were separate fresh
processes, each answered about **its own** cwd, and the worktree child did not
see the primary tree. That is the Cwd and Role-isolation claim, measured.

Two real failures were also exercised end to end, because a classification that
has only ever seen success proves nothing. Both were classified `failed` with
exit 1 and the child's own stderr preserved in the artifact:

- `AI stack: select a provider/model in the owner UI first` — the profile had no
  default model;
- `Configured default model "…" is unavailable` — the profile had a model name
  but no provider catalog cache.

Neither became a false `ready`. The diagnostics in `stderr_tail` were enough to
fix both causes, which is the property that makes a dispatch record useful.

**What this pilot does NOT prove:** the Planner/Research gate, a wave review, the
question→answer round trip, or resume. Those stay open above and must be shown
by the first real Path phase, not by a probe.

## 10. Testing

Tests use deterministic stub children through `--child-command` only; no real
Allspark process or model call is ever spawned:

```bash
uv run pytest -q tests/test_phase_dispatch_adapter.py
uv run ruff check scripts/ai/phase-dispatch.py tests/test_phase_dispatch_adapter.py
uv run ruff format --check scripts/ai/phase-dispatch.py tests/test_phase_dispatch_adapter.py
```

Covered: ready/blocked/question/failed/timeout classification, timeout
process-group kill with full reaping (pid gone), per-role artifact and summary
record fields, plan validation (invalid JSON, unknown keys, schema violations),
dry-run resolution without spawning, stdout tail bounding, and independent
per-role processes/cwds.
