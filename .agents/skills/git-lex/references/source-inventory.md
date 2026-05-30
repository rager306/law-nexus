# git-lex source inventory for law-nexus ACP work

## Local vendor checkouts

| Repo | Path | Commit observed | Evidence class | Notes |
|---|---|---:|---|---|
| `repolex-ai/git-lex` | `/root/vendor-source/git-lex` | `eaa4b24` | runtime/code source | Rust CLI/server implementation. GitNexus index: `git-lex-reference` with 970 nodes, 1,904 edges, 84 flows. |
| `repolex-ai/git-lex-kit-base` | `/root/vendor-source/git-lex-kit-base` | `b835c78` | semantic-kit source | Base kit shipping system ontologies and web UI, with no content folders installed. |
| `repolex-ai/git-lex-kit-squad` | `/root/vendor-source/git-lex-kit-squad` | `3298b9a` | domain-kit source | Squad domain kit with `ontology/squad/squad.ttl`, content guidance, and harness breadcrumb. |
| `repolex-ai/subtext-mcp` | `/root/vendor-source/subtext-mcp` | `bac5529` | MCP/wrapper code source | TypeScript MCP/CLI wrapper with bundled host binaries. GitNexus index: `subtext-mcp-reference` with 173 nodes, 228 edges, 5 flows. |

## GitNexus starting points

Use these before reading many code files:

```json
{"repo":"git-lex-reference","query":"sync extraction RDF SPARQL ontology kit serve CLI"}
{"repo":"subtext-mcp-reference","query":"MCP server git-lex binary CLI tools broker"}
```

Known indexed entry points:

- `git-lex-reference`: `src/main.rs::main` calls `cmd_init`, `cmd_save`, `cmd_validate`, `cmd_parse`, `cmd_extract`, `cmd_sync`, `cmd_query`, `cmd_history_verify`, `cmd_kit_update`, and N-Quads generators.
- `git-lex-reference`: `src/nquad.rs::generate_frontmatter_nquads` and related flows are relevant for frontmatter extraction proof.
- `subtext-mcp-reference`: `server.ts::main` calls `setupHostBinaries`, `ensureBroker`, broker fetch, git-root/TTY detection, and summary helpers.

## Files to inspect first

| File | What it supports | What it does not prove |
|---|---|---|
| `/root/vendor-source/git-lex/README.md` and `docs/*.md` | Declared runtime model, design history, architecture intent, and command semantics. | Correct implementation behavior without code/runtime proof. |
| `/root/vendor-source/git-lex/src/main.rs` | CLI command routing and high-level runtime operations. | ACP suitability without tracing callees/tests. |
| `/root/vendor-source/git-lex/src/nquad.rs` | Git/frontmatter/RDF/N-Quads generation behavior. | Store/query behavior by itself. |
| `/root/vendor-source/git-lex/src/kit.rs` | Kit install/update/resolve behavior. | Safety of adopting `.lex` in main repo. |
| `/root/vendor-source/git-lex/src/shacl.rs` | SHACL/OWL-lossless validation behavior. | Full semantic-web validation or ACP proof-gate satisfaction. |
| `/root/vendor-source/git-lex-kit-base/kit.yml` | Kit identity: `name: base`; scope: system ontologies + web UI; no content folders. | Runtime CLI availability, extraction behavior, or ACP adoption. |
| `/root/vendor-source/git-lex-kit-base/ontology/lex/lex.ttl` | Universal `lex:` ontology: upper classes, generic relations, extraction/linking vocabulary, quoted-triple provenance vocabulary. | Runtime RDF 1.2/SPARQL-star parser behavior, proof-gate satisfaction, or source truth. |
| `/root/vendor-source/git-lex-kit-base/ontology/git/git.ttl` | `git:` vocabulary for commits, actors, blobs, refs, branches, tags, changesets, files, paths, hashes, authors, dates. | Actual git graph extraction or store freshness. |
| `/root/vendor-source/git-lex-kit-base/ontology/fm/fm.ttl` | `fm:` vocabulary for YAML frontmatter keys and common metadata fields. | Dynamic frontmatter extraction behavior until `git lex sync` or equivalent runtime is proven. |
| `/root/vendor-source/git-lex-kit-squad/ontology/squad/squad.ttl` | Example domain kit showing how a kit subclasses/extends base ontology. | ACP domain model correctness. |
| `/root/vendor-source/subtext-mcp/server.ts` | MCP server behavior and binary setup flow. | Direct ACP backend suitability without runtime proof. |
| `/root/vendor-source/subtext-mcp/lib/host-binaries.ts` | Host binary resolution/setup for bundled `git-lex`/`git-lex-serve`. | Safety of using binaries inside law-nexus without isolated smoke tests. |

## Current ACP boundary files

| File | Role |
|---|---|
| `prd/architecture/acp/M045-RDF-PROJECTION-CONTRACT.md` | Existing contract that RDF/SHACL/SPARQL outputs are derived, non-authoritative projection/recovery aids. |
| `prd/architecture/acp/M048-S08-GIT-LEX-CAPABILITY-MATRIX.md` | M048 capability matrix for required git-lex/ACP capabilities and dispositions. |
| `prd/architecture/acp/M048-S10-GIT-LEX-ADOPTION-DECISION.md` | M048 closure decision: do not adopt runtime git-lex as ACP core backend from M048 evidence; preserve ACP-native implementation and optional future adapter path. |

## Evidence status summary

- Runtime/source code exists in `/root/vendor-source/git-lex` and is indexed as `git-lex-reference`.
- Bundled binary/MCP wrapper code exists in `/root/vendor-source/subtext-mcp` and is indexed as `subtext-mcp-reference`.
- RDF/Turtle ontology files are present in base and squad kits.
- OWL/RDFS vocabulary declarations are present.
- SPARQL query assumptions are present in docs/UI/code and must be traced in `git-lex-reference`.
- JSON-LD support remains unproven until main repo docs/code prove context/export/import behavior.
- Main-repo `.lex` safety remains unproven until isolated smoke tests pass and an explicit adoption decision exists.
