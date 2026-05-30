# M051 S01 Git Lex Source Inventory

Status: verified on 2026-05-30 from local vendor checkouts under `/root/vendor-source` without invoking `git` commands. Commit anchors were read from checkout metadata (`.git/HEAD`, refs, packed refs, and config). GitNexus index state was read from `npx gitnexus list`.

## Vendor repository anchors

| Repository | Local path | Remote URL | Branch | Commit | Inventory summary | Classification |
|---|---|---|---|---|---|---|
| `git-lex` | `/root/vendor-source/git-lex` | `https://github.com/repolex-ai/git-lex` | `main` | `eaa4b24d144a78a8b8e4969404d74cf22267df1f` | 61 files excluding `.git`/build caches. Top file classes: Markdown 21, Rust 15, TTL 11, no extension 4, JSON 3, YAML 2, lock 1, TOML 1, HTML 1, CSS 1. Root executable signals: `Cargo.toml`. | Executable code repository. Rust project plus semantic `.ttl` content and documentation. |
| `git-lex-kit-base` | `/root/vendor-source/git-lex-kit-base` | `https://github.com/repolex-ai/git-lex-kit-base` | `main` | `b835c781221843682f261fae1c1238754a95ac08` | 10 files excluding `.git`/build caches. Top file classes: TTL 3, no extension 2, YAML 1, Markdown 1, HTML 1, CSS 1, JavaScript 1. Root executable signals: none. | Semantic kit content only for ACP purposes; contains vocabulary/data assets and light static/demo material, not a primary executable codebase. |
| `git-lex-kit-squad` | `/root/vendor-source/git-lex-kit-squad` | `https://github.com/repolex-ai/git-lex-kit-squad` | `main` | `3298b9a7b74a78cb3f70064b9e8626323e3bf68f` | 9 files excluding `.git`/build caches. Top file classes: Markdown 5, no extension 2, YAML 1, TTL 1. Root executable signals: none. | Semantic kit content only. No root package/build manifest was found. |
| `subtext-mcp` | `/root/vendor-source/subtext-mcp` | `https://github.com/repolex-ai/subtext-mcp` | `main` | `bac5529bb1fdc0ee5c0d9d081a0208f2fefca005` | 33 files excluding `.git`/build caches. Top file classes: no extension 9, Markdown 9, JSON 7, TypeScript 7, lock 1. Root executable signals: `package.json`, `tsconfig.json`. | Executable code repository. TypeScript MCP server/project with package and TypeScript configuration. |

## GitNexus index state

The code repositories needed for downstream GitNexus analysis are indexed and their indexed commits match the local checkout anchors by short commit prefix.

| GitNexus repo name | Indexed path | Indexed at | Indexed commit | Local commit anchor | Index stats | Freshness assessment |
|---|---|---:|---|---|---|---|
| `git-lex-reference` | `/root/vendor-source/git-lex` | 2026-05-30 14:09:17 | `eaa4b24` | `eaa4b24d144a78a8b8e4969404d74cf22267df1f` | 42 files, 970 symbols/nodes, 1904 edges, 33 clusters, 84 flows | Fresh enough for this slice: indexed short commit matches the local checkout commit prefix. |
| `subtext-mcp-reference` | `/root/vendor-source/subtext-mcp` | 2026-05-30 14:09:21 | `bac5529` | `bac5529bb1fdc0ee5c0d9d081a0208f2fefca005` | 11 files, 173 symbols/nodes, 228 edges, 7 clusters, 5 flows | Fresh enough for this slice: indexed short commit matches the local checkout commit prefix. |

No GitNexus indexes were required for `git-lex-kit-base` or `git-lex-kit-squad` in this task because they were classified as semantic kit content rather than primary code repositories for code-flow analysis.

## Main repository `.lex` guard

Result: `no-main-repo` guard passed on 2026-05-30. `/root/law-nexus/.lex` does not exist, so this milestone has not mutated or reused a main-repository Lex runtime/state directory before downstream runtime proof tasks.

Guard command: `test ! -e .lex` from `/root/law-nexus`.

Failure policy: if `/root/law-nexus/.lex` appears later, stop before mutation and treat it as a blocker requiring explicit review, because this slice is only allowed to inventory upstream sources and preserve the main repository safety boundary.

## Reproduction notes

- Vendor anchor evidence command: `gsd_exec` run `56d41e0c-362c-4cbd-bf5f-6bfb6a32c597` (`/root/law-nexus/.gsd/exec/56d41e0c-362c-4cbd-bf5f-6bfb6a32c597.stdout`).
- GitNexus index evidence command: `gsd_exec` run `0b2fde55-8ab2-47b5-92d3-0b50dcddb24e` (`/root/law-nexus/.gsd/exec/0b2fde55-8ab2-47b5-92d3-0b50dcddb24e.stdout`).
- Main repository `.lex` guard evidence command: `gsd_exec` run `e09eeb85-40d7-4c53-9864-7db4cae62293` (`/root/law-nexus/.gsd/exec/e09eeb85-40d7-4c53-9864-7db4cae62293.stdout`).
