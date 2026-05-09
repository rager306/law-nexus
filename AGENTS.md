# Project-local agent instructions

## GitNexus repo name

This repository is indexed in GitNexus as **law-nexus** at `/root/law-nexus`.

Use `repo: "law-nexus"` for GitNexus tools in this project. Do **not** use the global `root` repo alias from `/root/AGENTS.md`; that alias points to `/root` and causes `gitnexus_detect_changes()` to run `git diff` outside this git repository with `Not a git repository`.

Examples:

```json
{"repo":"law-nexus","scope":"all"}
```

```json
{"repo":"law-nexus","target":"normalized_path","direction":"upstream"}
```
