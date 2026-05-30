# M048 S09 git-lex Functional Fit Report

## Status

- Harness status: `blocked`
- Runtime status: `blocked`
- Main-repo mutation guard safe: `True`
- Workspace cleanup: `deleted_by_TemporaryDirectory`

## Scenario Results

| Scenario | Capability | Result | Failure category | Allowed next action |
| --- | --- | --- | --- | --- |
| `source-record-lifecycle` | `ACP-S09-C01` | `pass` | `none` | implement_acp_native_or_adapter_later |
| `blocked-claim` | `ACP-S09-C02` | `pass` | `UnsupportedGitLexRuntime` | keep_runtime_adoption_blocked_deferred |
| `projection-boundary` | `ACP-S09-C03` | `pass` | `none` | keep_projection_derived_non_authoritative |
| `recovery-query` | `ACP-S09-C04` | `pass` | `none` | continue_acp_native_recovery |
| `git-semantics` | `ACP-S09-C05` | `blocked` | `UnsupportedGitLexRuntime` | ordinary_git_plus_acp_native_records_remains_sufficient |
| `isolation-safety` | `ACP-S09-C06` | `pass` | `none` | allow_future_isolated_adapter_spike_only |

## Capability Evidence

### source-record-lifecycle / Typed source record lifecycle

- Result: `pass`
- Failure category: `none`
- Evidence anchor: `prd/architecture/acp/fixtures/git-lex-isolated-proof/*.md`
- Authority status: `source_records_authoritative_projection_non_authoritative`
- Workspace path class: `temporary_disposable_workspace`
- Rollback status: `deleted_by_TemporaryDirectory`
- Value beyond ACP-native files plus ordinary git: No runtime git-lex value proven; ACP-native typed fixtures satisfy the lifecycle proof contract deterministically.
- Notes: S04 fixture records validate taxonomy, anchors, lifecycle states, profile boundary, and blocked actions.

### blocked-claim / Blocked claim and proof-gate diagnostics

- Result: `pass`
- Failure category: `UnsupportedGitLexRuntime`
- Evidence anchor: `prd/architecture/acp/fixtures/git-lex-isolated-proof/blocked-action.md`
- Authority status: `source_records_authoritative_projection_non_authoritative`
- Workspace path class: `temporary_disposable_workspace`
- Rollback status: `deleted_by_TemporaryDirectory`
- Value beyond ACP-native files plus ordinary git: git-lex adds no proven value while runtime is unavailable; explicit blocked diagnostics are ACP-native and durable.
- Notes: Runtime unavailability is recorded as a blocked/deferred result, not a pass and not adoption evidence.

### projection-boundary / Projection boundary and stale projection handling

- Result: `pass`
- Failure category: `none`
- Evidence anchor: `temporary derived projection generated from tracked fixtures`
- Authority status: `non_authoritative`
- Workspace path class: `temporary_disposable_workspace`
- Rollback status: `deleted_by_TemporaryDirectory`
- Value beyond ACP-native files plus ordinary git: No git-lex runtime value proven; ACP can generate and reject authority inheritance with native source/projection markers.
- Notes: Derived projection stayed non-authoritative and cannot validate R035/R037/R038 or override source records.

### recovery-query / Recovery query over source, proof gate, evidence, and dependents

- Result: `pass`
- Failure category: `none`
- Evidence anchor: `temporary derived projection generated from tracked fixtures`
- Authority status: `source_records_authoritative_projection_non_authoritative`
- Workspace path class: `temporary_disposable_workspace`
- Rollback status: `deleted_by_TemporaryDirectory`
- Value beyond ACP-native files plus ordinary git: No git-lex runtime value proven; deterministic source-record recovery covers the required cold-reader chain.
- Notes: Recovered AD-ACP-0001 and PG-ACP-0001 -> EA-ACP-0001 evidence edge without relying on polished prose.

### git-semantics / Record-aware value beyond ordinary git

- Result: `blocked`
- Failure category: `UnsupportedGitLexRuntime`
- Evidence anchor: `build/acp/m048-s09/git_lex_capability_results.json`
- Authority status: `not_applicable_no_git_lex_projection`
- Workspace path class: `temporary_disposable_workspace`
- Rollback status: `deleted_by_TemporaryDirectory`
- Value beyond ACP-native files plus ordinary git: Ordinary git covers branch/diff/history/conflict mechanics; no record-aware git-lex value was proven because the runtime is unavailable.
- Notes: Ordinary git comparison could not complete in disposable workspace.

### isolation-safety / Isolation safety and no-main-repo .lex guard

- Result: `pass`
- Failure category: `none`
- Evidence anchor: `prd/architecture/acp/M048-S09-GIT-LEX-RUNTIME-DIAGNOSTICS.md`
- Authority status: `not_applicable_safety_guard`
- Workspace path class: `temporary_disposable_workspace`
- Rollback status: `deleted_by_TemporaryDirectory`
- Value beyond ACP-native files plus ordinary git: No git-lex runtime state touched the main checkout; safety is preserved but adoption remains blocked/deferred.
- Notes: Main checkout .lex absence checked before and after; proof workspace is disposable.

## Value Assessment

S09 did not prove runtime git-lex adoption. Deterministic ACP-native fixtures provide typed records, lifecycle states, evidence anchors, proof gates, projection boundaries, and recovery/query behavior. Ordinary git provides branch, diff, history, and conflict mechanics. Because no local git-lex runtime responded to safe help probes, S09 found no proven record-aware git-lex value beyond ACP-native files plus ordinary git.

## Adoption Conclusion

Do not adopt runtime git-lex from S09 evidence. Keep ACP-native records plus ordinary git as sufficient baseline; consider adapter-only work only after explicit acquisition/runtime proof.

## Machine-readable Evidence

Per-capability rows are written to `build/acp/m048-s09/git_lex_capability_results.json`.
