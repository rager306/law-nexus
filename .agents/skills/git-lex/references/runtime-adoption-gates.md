# git-lex runtime adoption gates

Runtime adoption means using git-lex executable behavior, store behavior, extractors, `.lex` state, sync/query operations, or backend APIs as part of ACP. It is stricter than semantic-kit mapping.

## Required gates

1. Explicit user/adoption decision for the proof path.
2. Isolated workspace outside the main law-nexus checkout.
3. No main-repo `.lex` mutation before proof passes and adoption is explicitly accepted.
4. Reproducible acquisition:
   - source repository/package;
   - pinned commit/version;
   - build/install command;
   - license and dependency notes.
5. Smoke operations:
   - help/version command;
   - init in temporary repository;
   - sync or equivalent extraction;
   - query over generated graph;
   - frontmatter extraction with known and unknown keys;
   - git provenance extraction;
   - failure behavior and cleanup.
6. Semantic-web operations if claimed:
   - RDF/Turtle parse;
   - SPARQL named graph query;
   - RDF 1.2/SPARQL-star quoted-triple parse/query if used for ACP provenance;
   - JSON-LD context/export/import/roundtrip if JSON-LD interoperability is claimed.
7. ACP safety checks:
   - no source/projection authority inversion;
   - R035/R037/R038 not validated from projection/runtime evidence alone;
   - tracked repository-relative proof anchors only;
   - rollback plan and state cleanup.
8. Final per-capability disposition:
   - `use git-lex runtime`;
   - `absorb approach`;
   - `implement ACP-native`;
   - `adapter later`;
   - `reject`;
   - `blocked`.

## Baseline before gates pass

Use ACP-native records, ACP-native validation/lifecycle/proof/recovery, ordinary git, and derived semantic projections. Treat git-lex runtime as optional adapter-later until gates pass.


## M051 S10 refined gate outcomes

S10 opened the binary gate for source-built debug runtime smoke on this host:

- Source commit: `eaa4b24d144a78a8b8e4969404d74cf22267df1f`.
- Build blocker reproduced as `oxrocksdb-sys` / RocksDB bindgen `stdbool.h` ClangDiagnostic.
- Proven remediation on this host: install/expose `clang` and `cmake`, then run `cargo build --locked --bins --message-format=short`.
- Runtime matrix passed only in isolated `/tmp` repositories for base/squad/soul/autoknow.
- Main checkout `/root/law-nexus/.lex` remained absent.

Runtime-backed after S10:

- debug binary help/init/sync/query/dump/validate smoke;
- `list --json` shape-driven class discovery;
- named graph inventory after committed sync;
- JSON SELECT/ASK query output;
- `.spo` sidecar emission;
- `history-verify` equivalence in corrected committed/synced isolated repos;
- autoknow adaptive shape generation in isolation.

Still blocked or unproven:

- production binary/distribution fitness;
- negative validation behavior;
- JSON-LD import/export;
- explicit user-facing SPARQL-star query compatibility;
- ACP runtime adoption;
- any R035/R037/R038 validation.

## R058 knowledge-delta rule

For future work, every promotion from blocked/source-only to runtime-backed must be recorded as a knowledge-delta entry with:

1. prior assumption or open question;
2. evidence anchor;
3. proof class;
4. updated conclusion;
5. remaining boundary;
6. downstream implication for skill, ACP roadmap, or adoption gates.
