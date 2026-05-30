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
