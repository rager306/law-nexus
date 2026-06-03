# M053 S05 Claude Code Logs to Git Operations Feature Check

## Status

In progress for `M053-2jp3nm / S05`.

S05 exists because the user clarified the goal: Claude Code logs/session-to-git operations are interesting git-lex functionality and should be reflected in the git-lex skill, but they are not currently a useful ACP capability. This slice therefore checks the feature and classifies it as git-lex/harness prior art unless runtime evidence reveals a concrete ACP-safe use case.

## User boundary

```text
Interesting git-lex feature: yes.
Reflect in git-lex skill: yes.
Currently useful for ACP: not seen.
Default ACP classification: nonfit / prior art only.
```

## Guardrails

- Do not create or mutate main repository `.lex`.
- Do not create main repository `Squad` or `Raw` payloads.
- Runtime proof must use sanitized fake session logs in isolated `/tmp` only.
- Raw Claude/session payloads are privacy- and evidence-sensitive; do not use raw logs as durable ACP proof anchors.
- `git lex save` commits and can run hooks; never test it in the main checkout.
- This feature does not validate ACP source truth, R035/R037/R038, Russian legal evidence, parser quality, FalkorDB behavior, or production adoption.

## T01 source and GitNexus trace

### GitNexus result

GitNexus query for Claude Code/session logs and git operations surfaced `cmd_save` flows as the core source path:

```text
cmd_save -> harness::sync
cmd_save -> raw_mirror::run
cmd_save -> git add -A
cmd_save -> git commit --author ...
```

Relevant process summaries included:

```text
proc_3_cmd_save: Cmd_save -> Strip_fm_key
proc_19_cmd_save: Cmd_save -> Find_class_dir
proc_35_cmd_save: Cmd_save -> HarnessPath
proc_36_cmd_save: Cmd_save -> State_path
proc_9_cmd_raw_backfill: Cmd_raw_backfill -> Find_git_root
```

### Source flow

| Step | Source anchor | Behavior | ACP implication |
|---|---|---|---|
| Command entry | `/root/vendor-source/git-lex/src/main.rs:1020 fn cmd_save` | `git lex save` requires a git repo. | Runtime operation, not ACP static proof. |
| Agent identity | `/root/vendor-source/git-lex/src/main.rs:1031-1047` | Resolves `GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL` from environment or `.claude/settings.json`; hard-fails if missing. | Good for agent-harness provenance, but not legal/product proof. |
| Harness sync | `/root/vendor-source/git-lex/src/main.rs:1053`; `/root/vendor-source/git-lex/src/harness/mod.rs:11-18` | Calls `harness::sync(root, "claude")`. | Claude Code harness integration evidence only. |
| Skill/subagent sync | `/root/vendor-source/git-lex/src/harness/claude.rs:53-113` and following subagent code | Syncs `Skill/` and `Subagent/` documents into `.claude/skills` and `.claude/agents`. | Interesting for git-lex skill ecosystems; not ACP capability evidence. |
| Raw mirror | `/root/vendor-source/git-lex/src/main.rs:1057`; `/root/vendor-source/git-lex/src/raw_mirror.rs:303-376` | Copies watched harness session files into `Raw/<Harness>/` before `git add -A`. | Raw payload preservation; privacy/proof-anchor risk for ACP. |
| Config | `/root/vendor-source/git-lex/src/raw_mirror.rs:61-116` | Reads `.lex/repo.yml` `raw-mirror`; missing/invalid config falls back to defaults. | Config-sensitive; adapter would need explicit policy. |
| Default soul behavior | `/root/vendor-source/git-lex/src/raw_mirror.rs:119-135` | Only soul-like kits get default Claude Code `~/.claude/projects/<derived-from-cwd>/*.jsonl`; non-soul kits no-op by default. | Not a general ACP flow. |
| Watch path expansion | `/root/vendor-source/git-lex/src/raw_mirror.rs:143-162` | Expands `~` and `<derived-from-cwd>` with Claude Code path mangling. | Harness-specific and machine-path-specific. |
| State file | `/root/vendor-source/git-lex/src/raw_mirror.rs:166-199` | Per-machine state in `$XDG_STATE_HOME/git-lex/raw-mirror-state.json` or `~/.local/share/git-lex/raw-mirror-state.json`. | Non-repository state; weak fit for portable ACP proof. |
| Byte-faithful invariant | `/root/vendor-source/git-lex/src/raw_mirror.rs:1-23` | Raw files copied bit-identically, additive-only, no normalization. | Useful for receipts; risky for secrets/raw legal/session text. |
| File copy | `/root/vendor-source/git-lex/src/raw_mirror.rs:335-369` | Copies matching session files to `Raw/<Harness>/<first-seen>-<session-id>.jsonl`. | Raw payload enters git commit if `save` proceeds. |
| Commit operation | `/root/vendor-source/git-lex/src/main.rs:1063-1091` | Runs `git add -A`, checks staged diff, commits with agent author. | This is a real git operation with side effects. |

## Feature model

The feature is best described as:

```text
Claude Code/session harness material -> byte-faithful Raw mirror -> git commit with agent identity -> downstream hooks/extract/sync diagnostics
```

It is not:

```text
ACP source truth validation
ACP legal evidence proof
Russian legal retrieval evidence
FalkorDB ingestion proof
JSON-LD/RDF proof gate
production adoption readiness
```

## Why this is likely ACP-nonfit by default

| Concern | Reason |
|---|---|
| Raw payload sensitivity | Claude/session JSONL may contain prompts, model output, tool calls, file paths, secrets, or personal data. |
| Proof-anchor policy | law-nexus durable proof anchors should not use raw provider payloads or ignored/local paths. |
| Machine-local state | First-seen dates depend on local state file, not repository-only deterministic state. |
| Harness specificity | Default path is Claude Code-specific and uses path mangling; not portable ACP logic. |
| Commit side effects | `git lex save` stages all changes with `git add -A` and commits. ACP adapters need narrower scoped operations. |
| Authority inversion risk | Preserved logs are receipts, not authoritative ACP requirement/proof lifecycle records. |
| Privacy/security | Byte-faithful mirroring preserves sensitive content rather than redacting it. |

## ACP fit criteria

For this feature to become ACP-useful, a later proposal would need all of:

1. Sanitized log selection or redaction policy.
2. Explicit human decision that selected session material may become tracked evidence.
3. Repository-relative, tracked, non-secret proof anchors.
4. No raw provider payloads as durable proof anchors unless explicitly accepted.
5. Scoped staging/commit behavior, not broad `git add -A`.
6. Deterministic state or explicit handling of machine-local first-seen dates.
7. Clear mapping from session event to ACP source category, lifecycle state, and proof gate.
8. Evidence that this improves ACP workflows beyond existing GSD/PRD/ADR/source/test artifacts.

S05 starts with the opposite assumption: until those criteria are met, Claude logs-to-git is git-lex prior art and skill knowledge, not ACP capability.

## T01 conclusion

Source and GitNexus confirm the feature exists as a real git-lex/Claude Code harness flow. It is interesting and should be documented in the git-lex skill, but it is currently ACP-nonfit by default because it preserves raw, machine-local, harness-specific session payloads and commits broad repository changes. T02 may run an isolated sanitized smoke only to verify behavior, not to promote ACP adoption.

## T02: Isolated sanitized runtime smoke

### Scope and safety

T02 ran only in an isolated `/tmp` workspace with a fake sanitized JSONL payload. It did not read real Claude Code logs.

Evidence anchor:

```text
.gsd/exec/bf44b9d6-c28f-4407-9712-2386d566f5f7.stdout
```

Runtime identity:

```text
workspace_root: /tmp/m053-s05-claude-logs-6_t__xk2
repo: /tmp/m053-s05-claude-logs-6_t__xk2/repo
harness_dir: /tmp/m053-s05-claude-logs-6_t__xk2/fake-claude-project
state_home: /tmp/m053-s05-claude-logs-6_t__xk2/state
binary: /root/vendor-source/git-lex/target/debug/git-lex
binary_sha256: 40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c
main_lex_absent: true
main_squad_absent: true
main_raw_absent: true
```

### Runtime setup

The smoke used `git-lex init --kit squad`, then explicitly configured `.lex/repo.yml` with a fake harness path:

```yaml
raw-mirror:
  enabled: true
  harness-paths:
    - harness: ClaudeCodeSessionLog
      watch-path: /tmp/m053-s05-claude-logs-6_t__xk2/fake-claude-project
      file-glob: "*.jsonl"
```

The fake source file was:

```text
/tmp/m053-s05-claude-logs-6_t__xk2/fake-claude-project/m053-s05-session-0001.jsonl
```

It contained only sanitized dummy lines and no real user/provider payload.

### Observed result

`git lex save` exited 0:

```text
Raw: mirrored 1 new, 0 updated
[master 9379514] m053 s05 raw mirror smoke
 Author: M053 S05 Agent <m053-s05@example.invalid>
 1 file changed, 2 insertions(+)
 create mode 100644 Raw/ClaudeCodeSessionLog/2026-06-02-m053-s05-session-0001.jsonl
Saved: m053 s05 raw mirror smoke [as M053 S05 Agent <m053-s05@example.invalid>]
Markdown links: 3 from 3 files
Extracted in 47.2ms
Validated 1 files in 34.0ms — all pass ✓
```

Verification facts:

| Check | Result |
|---|---|
| Raw file created | `Raw/ClaudeCodeSessionLog/2026-06-02-m053-s05-session-0001.jsonl` |
| Byte-faithful copy | source sha256 equals Raw sha256: `c8cbb99513dd95a6f1bcc65423437472b21cad07de0ba54ea9b82ab8619afe62` |
| Per-machine state | `state/git-lex/raw-mirror-state.json` records `m053-s05-session-0001` first seen `2026-06-02` |
| Commit author | `M053 S05 Agent <m053-s05@example.invalid>` |
| Commit message | `m053 s05 raw mirror smoke` |
| Working tree after save | clean |
| Main repo pollution | no `.lex`, no `Squad`, no `Raw` |

### What T02 proves

T02 upgrades the feature from source-backed to isolated runtime-backed smoke:

- Explicit raw-mirror config can watch a harness directory.
- A fake Claude/session `.jsonl` file is copied byte-faithfully into `Raw/ClaudeCodeSessionLog/`.
- `git lex save` commits the Raw copy with the provided agent identity.
- Per-machine mirror state is written under isolated `XDG_STATE_HOME`.
- Hooks/extract/validate run as part of the commit flow.
- Main law-nexus checkout stays clean when the test is isolated.

### What T02 does not prove

T02 does not make this ACP-useful:

- It used fake/sanitized logs, not real Claude Code logs.
- It confirmed raw byte-faithful payloads enter git history, which is a privacy and proof-anchor risk.
- It confirmed broad commit behavior through `git lex save`.
- It did not map log events to ACP source categories, lifecycle states, proof gates, requirements, or LegalGraph evidence.
- It did not validate R035/R037/R038 or any Russian legal evidence behavior.

### T02 conclusion

```text
Feature behavior: runtime-backed in isolated smoke.
ACP utility: still not shown.
Default classification: git-lex/harness prior art and skill knowledge, not ACP capability.
```

## T03: Final classification and skill update

### Final classification

| Surface | Result | Classification |
|---|---|---|
| Claude/session JSONL Raw mirroring | Runtime-backed in isolated smoke with fake sanitized payload. | `git-lex feature: confirmed` |
| `git lex save` agent-authored commit | Runtime-backed in isolated smoke. | `git-lex feature: confirmed` |
| Raw payload as ACP proof anchor | Raw payload is byte-faithful session material and may contain secrets/provider/user data. | `rejected by default` |
| Logs/session flow as ACP capability | No mapping to ACP source categories, lifecycle states, proof gates, or LegalGraph requirements was proven. | `ACP-nonfit by default` |
| Skill guidance | User asked to reflect the feature in git-lex skill. | `update skill` |

### S06/S08 implications

S06 should not include logs-to-git as an ACP adapter surface unless a later human decision defines a concrete ACP use case, redaction policy, scoped staging policy, and proof-anchor contract.

S08 should record S05 as:

```text
confirmed: git-lex can mirror sanitized Claude/session JSONL into Raw and commit it via git lex save in isolation
rejected for ACP by default: raw/session payloads as durable ACP proof anchors
preserved: git-lex skill knowledge / prior art for harness workflows
blocked: ACP adoption without explicit privacy/proof/staging policy
```

### Safe wording

Safe:

> git-lex has a runtime-backed Claude Code/session Raw mirroring feature: with explicit config, `git lex save` can copy watched JSONL session files into `Raw/<Harness>/` and commit them with agent identity.

Safe:

> For law-nexus ACP, this is prior-art/skill knowledge only by default; raw session logs are not ACP source truth or durable proof anchors.

Unsafe:

> Claude Code logs are ACP proof evidence by default.

Unsafe:

> `git lex save` is an ACP-safe adapter primitive without scoped staging, redaction, and proof-anchor policy.

Unsafe:

> Raw mirrored logs validate LegalGraph requirements or Russian legal evidence.

### Skill update

Updated:

```text
.agents/skills/git-lex/SKILL.md
```

The skill now contains a Claude logs-to-git feature boundary section so future agents treat it as interesting git-lex/harness functionality, not as ACP capability evidence by default.

### T03 conclusion

```text
S05 disposition: feature-confirmed-acp-nonfit
confirmed: Claude/session JSONL Raw mirroring and git lex save commit behavior in isolated smoke
rejected by default: raw/session logs as ACP proof anchors or ACP capability evidence
preserved: git-lex skill guidance and prior-art knowledge
main repo safety: .lex absent; Squad absent; Raw absent
```
