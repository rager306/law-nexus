# M048 S09 Independent Proof Review

## Verdict

**PASS_BOUNDED_DECISION_INPUT.** S09 provides sufficient bounded evidence for an S10 git-lex disposition decision, but it does **not** prove runtime git-lex adoption. The durable artifacts support a conservative decision: keep ACP-native source records plus ordinary git as the current baseline, and defer any runtime git-lex adapter until separate acquisition/runtime proof exists.

## Review Scope

This review inspected S09 evidence as a cold-reader proof gate in the spirit of R038:

- `prd/architecture/acp/M048-S09-GIT-LEX-RUNTIME-DIAGNOSTICS.md`
- `prd/architecture/acp/M048-S09-GIT-LEX-FUNCTIONAL-FIT-REPORT.md`
- `build/acp/m048-s09/git_lex_capability_results.json`
- `tests/test_m048_s09_git_lex_functional_fit.py`
- Requirement boundaries in `.gsd/REQUIREMENTS.md`, especially `R035`, `R037`, `R038`, `R043`, `R046`, `R047`, `R048`, `R055`, `R056`, and `R057`.

## Self-Confirming Artifact Check

| Check | Result | Evidence |
| --- | --- | --- |
| Per-capability rows are machine-readable, not prose-only | `pass` | `build/acp/m048-s09/git_lex_capability_results.json` contains six scenario rows with capability IDs, result states, failure categories, authority status, rollback status, evidence anchors, and allowed next actions. |
| Human report matches machine evidence | `pass` | `M048-S09-GIT-LEX-FUNCTIONAL-FIT-REPORT.md` repeats the six scenario outcomes and preserves the blocked runtime conclusion instead of replacing it with optimistic prose. |
| Runtime diagnostics are externally inspectable | `pass` | `M048-S09-GIT-LEX-RUNTIME-DIAGNOSTICS.md` records command probes for `git lex --help` and `git-lex --help`, the unsupported runtime blocker, safe acquisition policy, and the main-repo `.lex` guard. |
| Tests assert proof substance rather than only file existence | `pass` | `tests/test_m048_s09_git_lex_functional_fit.py` asserts required scenario coverage, allowed states, blocked-runtime diagnostics, mutation guard fields, and adoption-overclaim absence. |
| Review does not rely on implementation internals | `pass` | The review consumes durable JSON/Markdown artifacts and requirement text, not the harness logic as proof of itself. |

## Blocked Status and Overclaim Review

S09 uses `blocked` conservatively and does not treat blocked runtime evidence as a pass:

- Runtime status is `blocked` with blocker class `UnsupportedGitLexRuntime`.
- `git-semantics` is `blocked`, not `pass`, because no record-aware git-lex value beyond ordinary git was proven.
- `blocked-claim` may pass only as a diagnostic behavior check: it proves the system records blocked diagnostics, not that runtime git-lex works.
- The adoption conclusion says: “Do not adopt runtime git-lex from S09 evidence.”
- No S09 artifact claims that `R035`, `R037`, or `R038` is validated by this git-lex proof.

This is the correct interpretation for `R046` and `R047`: derived projections and diagnostic reports remain non-authoritative, and main-repository `.lex` mutation remains blocked absent a later explicit adoption decision.

## Evidence Sufficiency for S10 Decision

S09 is sufficient for an S10 decision **only at bounded disposition level**:

| Decision question for S10 | S09 support | Review assessment |
| --- | --- | --- |
| Can runtime git-lex be adopted now? | Runtime probes are unavailable and `git-semantics` is blocked. | **No.** S09 blocks runtime adoption. |
| Can ACP-native source records remain the baseline? | Typed lifecycle, projection boundary, recovery query, blocked diagnostics, and isolation safety all have durable pass evidence. | **Yes, bounded.** ACP-native mechanics remain usable. |
| Is ordinary git still sufficient for repository mechanics while runtime git-lex is blocked? | Report states ordinary git covers branch/diff/history/conflict mechanics; no record-aware git-lex value was proven. | **Yes, provisional baseline.** This does not prove all future ACP needs, only S09 functional fit disposition. |
| Is a future adapter spike allowed? | Allowed next action for isolation safety is `allow_future_isolated_adapter_spike_only`; acquisition/runtime proof is explicitly required. | **Yes, with guardrails.** Must remain isolated and non-mutating until a separate decision. |
| Can downstream law-nexus binding proceed without ACP closure? | `R057` requires proof-backed git-lex decision and ACP-native delta before binding. | **No.** S10 must record the final disposition and ACP-native delta first. |

## Findings

### F-01 — Bounded pass evidence is adequate for ACP-native baseline

S09 proves enough deterministic ACP-native behavior to support a conservative baseline: typed records, blocked diagnostics, projection authority boundaries, recovery query behavior, and isolation safety. This is not git-lex runtime adoption evidence.

### F-02 — Runtime git-lex remains blocked, and the blocked state is correctly preserved

The unavailable executable is classified as `UnsupportedGitLexRuntime`. The blocked state appears in JSON, diagnostics, and the functional-fit report. This prevents a self-confirming pass where deterministic ACP-native checks would mask missing runtime capability.

### F-03 — Main-repo mutation guard is materially evidenced

The main checkout `.lex` absence is recorded before and after proof, and the isolated workspace cleanup status is `deleted_by_TemporaryDirectory`. This satisfies the S09 safety proof needed to avoid blind `git lex init` in the main repository.

### F-04 — S10 still needs an explicit decision and ACP-native delta

S09 tells S10 what not to adopt and which ACP-native mechanics are sufficient for now. S10 still must record the proof-backed git-lex disposition, adapter boundary, ACP-native implementation delta, and remaining blocked items before downstream architecture binding.

## Negative Claims Explicitly Rejected

S09 evidence must not be used to claim any of the following:

- Runtime git-lex is adopted.
- Main-repository `.lex` initialization is safe.
- Derived projections can become source truth.
- `R035`, `R037`, or `R038` is fully validated by S09.
- git-lex provides proven record-aware value beyond ACP-native files plus ordinary git.
- ACP may proceed to law-nexus binding without the S10 closure decision required by `R057`.

## Review Conclusion

S09 passes independent proof review as **bounded decision input**. The evidence is not self-confirming because it includes machine-readable rows, external command diagnostics, mutation guard fields, and deterministic tests that would fail on missing capability coverage, unsafe adoption language, or loss of blocked runtime diagnostics.

Recommended S10 interpretation: **do not adopt runtime git-lex now; keep ACP-native records plus ordinary git as the baseline; allow only a later isolated adapter/runtime proof; and record ACP-native deltas before downstream law-nexus architecture binding.**
