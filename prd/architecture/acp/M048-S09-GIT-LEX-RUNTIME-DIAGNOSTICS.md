# M048 S09 git-lex Runtime Diagnostics

## Status

- Runtime status: `blocked`
- Blocker class: `UnsupportedGitLexRuntime`
- Safe acquisition policy: no clone/install/download/durable build/git-lex-init from law-nexus
- Main-repo mutation guard: `pass`

## Workspace

- Main repository: `/root/law-nexus`
- Isolated workspace policy: TemporaryDirectory outside the main checkout; copied tracked fixtures only; deleted after proof.

## Tool Versions

- Python: `3.13.12`
- git-lex runtime: `unavailable`

## Command Diagnostics

| Command | Exit code | Timed out | Duration | Preview |
| --- | ---: | --- | ---: | --- |
| `git lex --help` | 1 | False | 6 ms | `git: 'lex' is not a git command. See 'git --help'.

The most similar command is
	help` |
| `git-lex --help` | None | False | 1 ms | `[Errno 2] No such file or directory: 'git-lex'` |

## Main-repo `.lex` Guard

| Check | Result |
| --- | --- |
| `.lex` absent before proof | `True` |
| `.lex` absent after proof | `True` |
| Guard safe | `True` |

## S05 Carry-forward Contract

- S05 contract status: `blocked`
- S05 workflow statuses: `{"extraction_projection_query_recovery": "pass", "lifecycle_proof_gate_profile_boundary": "pass", "main_repo_mutation_guard": "pass", "runtime_acquisition_and_adoption": "blocked", "typed_source_record_validation": "pass"}`

## Conclusion

Runtime git-lex remains blocked/deferred when the local executable is unavailable. This is not a failed ACP-native deterministic proof and not adoption evidence. The main checkout stayed free of `.lex` state.
