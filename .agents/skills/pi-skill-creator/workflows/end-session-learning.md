# End-of-Session Learning Loop

<required_reading>
- `references/eval-method.md`
- `references/description-triggering.md`
- `scripts/analyze-session-learning.py` from the repository root when available
</required_reading>

<process>
## Purpose
Run this workflow at the end of a meaningful development session, milestone slice, or skill-improvement pass. The goal is to convert repeated friction into better skills and durable memory without encoding one-off noise.

## Steps
1. Run the local retrospective script from the repository root:
   ```bash
   uv run python scripts/analyze-session-learning.py --exec-limit 30
   ```
2. Read the generated reports:
   - `.gsd/session-learning-report.md`
   - `.gsd/session-learning-report.json`
3. Classify each recommendation:
   - **Durable skill rule** — update the nearest `SKILL.md`, workflow, reference, or eval.
   - **Memory only** — save a concise fact/gotcha to agentmemory, but do not edit skills.
   - **One-off noise** — do nothing.
4. If a skill is edited, update or add an eval that would catch the lesson next time.
5. Run that skill's verifier before claiming the update is complete. For FalkorDB skills, use:
   ```bash
   uv run python scripts/verify-falkordb-pack.py
   ```
6. Save only durable memory candidates. Prefer manual review first; if using the script directly, pass `--save-memory` only after confirming the candidates are not secrets or one-off failures.

## What belongs in skills
- Repeated workflow mistakes.
- Capability boundaries that prevent overclaiming.
- Verification commands that future agents should always run.
- Trigger/eval gaps revealed by actual use.

## What belongs only in memory
- Project-local gotchas that are useful but too narrow for a reusable skill.
- Environment setup facts.
- Tooling limitations such as unavailable activation telemetry.

## What should be discarded
- Typos.
- Transient network failures.
- A single failed experiment with no reusable pattern.
- Secrets, tokens, credentials, or raw private data.
</process>

<success_criteria>
- The session retrospective report exists.
- Any proposed memory entries are reviewed for durability and secrecy.
- Any skill edits have matching eval/verification coverage.
- No one-off failure is promoted into long-lived guidance without evidence.
</success_criteria>
