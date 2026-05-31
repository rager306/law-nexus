---
name: git-lex
description: Guides law-nexus agents through git-lex semantic-kit inspection, ACP mapping, RDF/OWL/SPARQL/JSON-LD claim review, runtime-adoption boundaries, and overclaim prevention. Use when work mentions git-lex, git-lex-kit-base, semantic kits, ontology projection, ACP RDF/OWL/SPARQL/JSON-LD, .lex state, or git-lex runtime adoption.
---

<objective>
Use this project-local router when work touches git-lex, `git-lex-kit-base`, semantic kits, RDF/OWL/SPARQL/JSON-LD interoperability claims, `.lex` repository state, or ACP integration decisions. The goal is to advance git-lex for ACP through real source evidence while preserving the boundary between semantic-kit evidence, derived projections, runtime proof, and authoritative ACP/product/legal proof.
</objective>

<quick_start>
Start from the local vendor checkouts and GitNexus indexes, not memory or marketing prose:

```text
/root/vendor-source/git-lex                    # Rust CLI/server; GitNexus repo: git-lex-reference
/root/vendor-source/git-lex-kit-base           # base semantic kit: lex/git/fm ontologies + web UI
/root/vendor-source/git-lex-kit-squad          # squad domain kit: content + squad ontology
/root/vendor-source/subtext-mcp                # TypeScript MCP/CLI wrapper; GitNexus repo: subtext-mcp-reference
```

For code behavior, use GitNexus before reading many files:

```json
{"repo":"git-lex-reference","query":"sync extraction RDF SPARQL ontology kit serve CLI"}
{"repo":"subtext-mcp-reference","query":"MCP server git-lex binary CLI tools broker"}
```

For semantic-kit evidence, inspect:

```text
/root/vendor-source/git-lex-kit-base/kit.yml
/root/vendor-source/git-lex-kit-base/ontology/lex/lex.ttl
/root/vendor-source/git-lex-kit-base/ontology/git/git.ttl
/root/vendor-source/git-lex-kit-base/ontology/fm/fm.ttl
/root/vendor-source/git-lex-kit-squad/ontology/squad/squad.ttl
```

Then compare any ACP adoption claim against the current project boundaries:

```text
prd/architecture/acp/M045-RDF-PROJECTION-CONTRACT.md
prd/architecture/acp/M048-S08-GIT-LEX-CAPABILITY-MATRIX.md
prd/architecture/acp/M048-S10-GIT-LEX-ADOPTION-DECISION.md
```

If the request is broad or unfamiliar, first use GitNexus on `git-lex-reference`/`subtext-mcp-reference`, then follow `workflows/inspect-base-kit.md`; if it asks whether a claim is safe, follow `workflows/review-acp-claim.md`.
</quick_start>

<essential_guardrails>
- Do not run `git lex init` in the main repository and do not create or mutate main-repo `.lex` state without an isolated proof and explicit adoption decision.
- Semantic-kit evidence from `ontology/*.ttl` proves vocabulary/model availability only; it does not prove CLI availability, extractor behavior, store behavior, SPARQL backend behavior, or ACP runtime adoption.
- RDF, OWL, SHACL, SPARQL, JSON-LD, JSONL, dashboards, and recovery views are derived governance/recovery surfaces unless tied to an accepted ACP source category, lifecycle state, evidence anchor, and proof gate or accepted decision.
- Do not validate R035, R037, or R038 from ACP/git-lex/projection evidence alone.
- Treat git-lex as a strong semantic substrate candidate for ACP, not as accepted core backend, until runtime acquisition, isolated operations, rollback, and `.lex` state policy are proven.
- Keep reusable ACP ontology separate from law-nexus profile constraints; Russian legal evidence, FalkorDB runtime, parser completeness, citation safety, and retrieval quality require their own proof paths.
</essential_guardrails>

<runtime_build_playbook>
When work needs a local `git-lex` / `git-lex-serve` binary, use this order before claiming runtime availability:

1. Check upstream first: inspect `repolex-ai/git-lex` issues/releases/README/workflows and relevant dependency issues for `oxrocksdb-sys`, RocksDB, `stdbool.h`, clang/sysroot, C++20, and locked Cargo build failures.
2. Run read-only local diagnostics before remediation: record `rustc -vV`, `cargo --version`, `cc/gcc/g++/clang/clang++/cmake/make/pkg-config` availability, `stdbool.h` locations, and whether both `cc` and `clang` can preprocess `#include <stdbool.h>`.
3. If `oxrocksdb-sys` fails with `rocksdb/include/rocksdb/c.h:65:10: fatal error: 'stdbool.h' file not found` wrapped in `ClangDiagnostic`, do not treat that as missing GCC by default. In M051/S10, GCC/G++ and GCC-visible `stdbool.h` were present; the fix was installing/exposing clang/libclang and cmake so bindgen could resolve the standard headers.
4. With user approval for system package changes, the proven Ubuntu remediation was:

```bash
apt-get update
apt-get install -y clang cmake
```

5. Verify remediation before rebuilding:

```bash
clang --version
clang++ --version
cmake --version
printf '#include <stdbool.h>\n' | clang -x c -E - >/tmp/clang-stdbool.i
```

6. Build from the pinned vendor checkout with the lockfile, not an unlocked install:

```bash
cd /root/vendor-source/git-lex
cargo build --locked --bins --message-format=short
```

7. If the build passes, record binary identity before any runtime claim: source commit, `Cargo.lock` sha256, binary paths, mode, size, sha256, and `--help` output for both `target/debug/git-lex` and `target/debug/git-lex-serve`.
8. Only after binary identity and help checks pass, run `init`/`sync`/`query`/`validate` proofs in an isolated throwaway git repository. Check `test ! -e /root/law-nexus/.lex` before and after every runtime proof.

M051/S10 source-built debug anchors: `git-lex` at commit `eaa4b24d144a78a8b8e4969404d74cf22267df1f` built successfully after the clang/cmake remediation. Treat those local debug binaries as runtime-smoke candidates only; they do not by themselves prove semantic correctness, SHACL behavior, JSON-LD support, SPARQL-star compatibility, or ACP adoption fitness.
</runtime_build_playbook>

<runtime_smoke_findings>
M051/S10 upgraded several previously blocked git-lex runtime claims using source-built debug binaries in isolated `/tmp` repositories. These findings are smoke evidence only; keep ACP authority and main-repo `.lex` adoption separate.

Proven in isolated runtime smoke:

- `git-lex --help`, `git-lex init --help`, and `git-lex-serve --help` work from `/root/vendor-source/git-lex/target/debug`.
- `git-lex init --kit base` exits 0 in an isolated git repo and creates `.lex/repo.yml`, `.lex/extract/`, base kit files, `lex/git/fm` ontology TTL files, and web assets.
- `git-lex init --kit squad` exits 0 in a separate isolated git repo and creates base+squad kit state, `squad.ttl`, generated `squad-shapes.ttl`, and `Squad/{Bug, Freeform, Situation, Proclamation, Pod, Project, Task, Brief, Discovery, Decision, Message, Squaddie}` folders.
- With `PATH=/root/vendor-source/git-lex/target/debug:$PATH`, `git-lex list`, `sync`, `dump`, `query`, and `validate` run in the isolated squad workspace.
- `git-lex sync` created `.git/lex/oxigraph`, emitted `Virtual: 421 git + 77 now`, `+25 assertions`, `150 quads`, `2 commit(s)`, `25 events`, `29 annotations`, and `Total sync graphs: 1` on the S10 fixture.
- `git-lex dump` emitted 498 N-Quads lines including repo metadata, `git:Commit`, file/blob/path triples, and sidecar extraction references.
- SPARQL graph inventory returned 11 named graphs including `repo`, `refs`, `history`, `commits`, `filetree/...`, `changeset/...`, `sync/...`, `meta`, and `now`.
- SPARQL fixture/frontmatter query returned `fm:title = S10 Runtime Gate Decision` and fixture paths for `Squad/Decision/S10Decision.md` and `Squad/Task/S10Task.md`.
- Negative empty query returned 0 rows with exit 0.
- `git-lex validate` returned exit 0 with `Validated 1 files ... all pass` on the positive S10 fixture.
- `/root/law-nexus/.lex` remained absent before and after all isolated init/sync/query/validate runs.

Still unproven after M051/S10 smoke:

- SPARQL `owl:Class` inventory returned 0 rows, even though `git-lex list` listed squad classes from installed shapes. Do not claim ontology class triples are queryable with that query shape without further proof.
- Negative SHACL validation was not tested; only a positive validate pass is proven.
- JSON-LD import/export support remains unproven.
- SPARQL-star compatibility remains unproven.
- `history-verify` and history equivalence semantics remain unproven, despite sync emitting history events/annotations.
- Production readiness, LegalGraph semantic correctness, parser behavior, FalkorDB ingestion, ACP runtime adoption, and R035/R037/R038 validation remain unproven.

Operational note: init by absolute binary path emitted a non-fatal warning that `git-lex` was not on `PATH` or in the subtext plugin cache. For follow-up runtime proofs, set `PATH=/root/vendor-source/git-lex/target/debug:$PATH` before running commands that may trigger hooks or subprocesses.
</runtime_smoke_findings>

<routing>
- If the user asks what git-lex base contains, what `git-lex-kit-base` proves, or how RDF/OWL/SPARQL is represented, follow `workflows/inspect-base-kit.md` and read `references/source-inventory.md` plus `references/ontology-map.md`.
- If the user asks whether wording like “git-lex proves ACP” or “semantic web stack validates the requirement” is safe, follow `workflows/review-acp-claim.md` and use `templates/claim-review.md`.
- If the user asks to adopt git-lex runtime, use `.lex`, initialize a repo, build an adapter, or run CLI proof, follow `workflows/plan-adapter-spike.md`.
- If the user provides an artifact and asks what it can prove, follow `workflows/classify-evidence.md`.
- For general ACP registry/verifier/proof-level questions not specific to git-lex, route to `legalgraph-architecture-verification` after preserving the git-lex boundaries above.
</routing>

<reference_index>
- `references/source-inventory.md` records the local vendor checkout and the ACP files that currently bound git-lex adoption.
- `references/ontology-map.md` maps `lex:`, `git:`, `fm:`, SPARQL, and JSON-LD claims to ACP use and limits.
- `references/acp-boundaries.md` states source-truth hierarchy, authority rules, and blocked claims.
- `references/claim-language.md` gives safe and unsafe wording patterns.
- `references/runtime-adoption-gates.md` lists the gates before any git-lex runtime or `.lex` adoption.
</reference_index>

<success_criteria>
A correct use of this skill cites inspected git-lex files, distinguishes semantic-kit evidence from runtime proof, keeps git-lex/RDF/SPARQL/JSON-LD projections non-authoritative by default, prevents R035/R037/R038 overclaiming, and either advances ACP through bounded semantic integration or defines the next isolated proof needed for runtime adoption.
</success_criteria>
