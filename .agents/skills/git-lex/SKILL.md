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
/root/vendor-source/git-lex-kit-soul           # soul domain kit: prompt-handled personal/agent memory ontology + harness prior art
/root/vendor-source/git-lex-kit-autoknow       # autoknow adaptive Source/Entity kit + subagent extraction prior art
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
/root/vendor-source/git-lex-kit-soul/ontology/soul/soul.ttl
/root/vendor-source/git-lex-kit-autoknow/ontology/autoknow/autoknow.ttl
```

Then compare any ACP adoption claim against the current project boundaries:

```text
prd/architecture/acp/M045-RDF-PROJECTION-CONTRACT.md
prd/architecture/acp/M048-S08-GIT-LEX-CAPABILITY-MATRIX.md
prd/architecture/acp/M048-S10-GIT-LEX-ADOPTION-DECISION.md
prd/architecture/acp/M051-S05-GIT-LEX-ACP-INTEGRATION-DECISION.md
prd/architecture/acp/M051-S08-ACP-ONTOLOGY-PROTOTYPE.md
prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md
prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md
prd/architecture/acp/M055-S05-GIT-LEX-BACKEND-NEXT-DECISION.md
prd/architecture/acp/M049-S05-GIT-LEX-ACP-KIT-INTEGRATION-ROADMAP.md
```

If the request is broad or unfamiliar, first use GitNexus on `git-lex-reference`/`subtext-mcp-reference`, then follow `workflows/inspect-base-kit.md`; if it asks whether a claim is safe, follow `workflows/review-acp-claim.md`.
</quick_start>

<essential_guardrails>
- Do not run `git lex init` in the main repository and do not create or mutate main-repo `.lex` state without an isolated proof and explicit adoption decision.
- Semantic-kit evidence from `ontology/*.ttl` proves vocabulary/model availability only; it does not prove CLI availability, extractor behavior, store behavior, SPARQL backend behavior, or ACP runtime adoption.
- RDF, OWL, SHACL, SPARQL, JSON-LD, JSONL, dashboards, and recovery views are derived governance/recovery surfaces unless tied to an accepted ACP source category, lifecycle state, evidence anchor, and proof gate or accepted decision.
- Do not validate R035, R037, or R038 from ACP/git-lex/projection evidence alone.
- Treat git-lex as a strong semantic substrate candidate for ACP, not as accepted core backend, until runtime acquisition, isolated operations, rollback, and `.lex` state policy are proven.
- Treat ACP-kit as the next semantic-kit integration track, not as backend/source-truth promotion: ACP-kit v0 packages ACP core vocabulary over `git-lex-kit-base`, remains derived/non-authoritative, and should precede L2 operational diagnostic integration.
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
- Negative SHACL validation remains unproven; a later malformed fixture did not trigger failure.
- JSON-LD import/export support remains unproven.
- Explicit user-facing SPARQL-star query compatibility remains unproven.
- `history-verify` was later proven only as bounded isolated smoke in corrected committed/synced base/squad/soul/autoknow repos.
- Production readiness, LegalGraph semantic correctness, parser behavior, FalkorDB ingestion, ACP runtime adoption, and R035/R037/R038 validation remain unproven.

Operational note: init by absolute binary path emitted a non-fatal warning that `git-lex` was not on `PATH` or in the subtext plugin cache. For follow-up runtime proofs, set `PATH=/root/vendor-source/git-lex/target/debug:$PATH` before running commands that may trigger hooks or subprocesses.
</runtime_smoke_findings>

<final_m051_runtime_matrix>
Refined by M051/S10 T08-T11 after the initial smoke above:

- `git-lex list --json` is the supported runtime class-discovery surface. It reads installed SHACL shape files, not Oxigraph `owl:Class` triples.
- `git-lex query` uses Oxigraph data with default named-graph union semantics. Prefix injection (`lex:`, `git:`, `fm:`, `owl:`, `xsd:`, and kit prefix) does not load ontology facts into the store.
- `SELECT ?c WHERE { ?c a owl:Class }` and `SELECT ?c WHERE { ?shape sh:targetClass ?c }` are expected-empty by default unless ontology/shapes are explicitly loaded as graph facts.
- Corrected isolated runtime matrix passed for `base`, `squad`, `soul`, and `autoknow`: init, committed `sync`, graph inventory, `query --json` SELECT/ASK, git/frontmatter/probe queryability, `.spo` sidecars, `dump`, and `history-verify` equivalence.
- `autoknow` emitted `Adaptive shapes: 1 built, 0 failed`; treat that as isolated adaptive-shape smoke, not ACP adoption or authority for `_ontology/` mutation.
- Negative validation remains unproven: a malformed fixture failed to fail, so future claims need a stronger shape-specific invalid fixture and non-zero `git-lex validate` result.
- JSON-LD import/export and explicit user-facing SPARQL-star query compatibility remain unproven.
- S08 created a proposed ACP ontology/static-check scaffold and JSON-LD sample; it is non-authoritative and does not prove git-lex JSON-LD support.
</final_m051_runtime_matrix>

<claude_logs_to_git_feature_boundary>
M053/S05 verified an interesting git-lex/Claude Code harness feature, but classified it as ACP-nonfit by default.

Runtime-backed in isolated smoke:

- `git lex save` resolves agent identity from `GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL` or `.claude/settings.json`.
- `git lex save` calls `harness::sync(root, "claude")`, then `raw_mirror::run(root)`, then `git add -A`, then `git commit --author ...`.
- With explicit `raw-mirror` config, sanitized fake Claude/session `*.jsonl` files were copied byte-faithfully into `Raw/ClaudeCodeSessionLog/<date>-<session>.jsonl` and committed with agent identity in an isolated `/tmp` repo.
- The mirror uses per-machine state (`$XDG_STATE_HOME/git-lex/raw-mirror-state.json` or `~/.local/share/git-lex/...`) for first-seen dates.

ACP boundary:

- Treat this as git-lex/harness prior art and skill knowledge, not ACP capability evidence by default.
- Raw session logs may contain prompts, tool outputs, provider payloads, secrets, personal data, and machine-local paths; do not use them as durable ACP proof anchors unless a later explicit human decision approves a redaction/proof policy.
- `git lex save` stages broadly with `git add -A` and commits; it is not an ACP-safe adapter primitive without a scoped staging/rollback design.
- This feature does not validate ACP source truth, LegalGraph requirements, Russian legal evidence, parser quality, FalkorDB behavior, R035/R037/R038, or production adoption.

Safe wording:

```text
git-lex has a runtime-backed Claude Code/session Raw mirroring feature for harness workflows, proven only in isolated smoke with sanitized fake logs.
```

Unsafe wording:

```text
Claude Code logs are ACP proof evidence by default.
```

```text
git lex save is ACP-safe without scoped staging, redaction, and proof-anchor policy.
```
</claude_logs_to_git_feature_boundary>

<knowledge_delta_contract>
For M051/S06 and S07, do not merely restate conclusions. Record a knowledge-delta ledger entry whenever the skill or synthesis changes a git-lex claim. Each entry should include: prior assumption/open question, evidence anchor, proof class, updated conclusion, remaining boundary, and downstream implication. This implements requirement R058.
</knowledge_delta_contract>

<routing>
- If the user asks what git-lex base contains, what `git-lex-kit-base` proves, or how RDF/OWL/SPARQL is represented, follow `workflows/inspect-base-kit.md` and read `references/source-inventory.md` plus `references/ontology-map.md`.
- If the user asks whether wording like “git-lex proves ACP” or “semantic web stack validates the requirement” is safe, follow `workflows/review-acp-claim.md` and use `templates/claim-review.md`.
- If the user asks to adopt git-lex runtime, use `.lex`, initialize a repo, build an adapter, or run CLI proof, follow `workflows/plan-adapter-spike.md`.
- If the user provides an artifact and asks what it can prove, follow `workflows/classify-evidence.md`.
- If the user asks to design or maintain ACP-native source truth, proof gates, ACP-kit, ACP lifecycle states, or ACP/law-nexus profile boundaries, route to the project-local `acp` skill when available; keep this `git-lex` skill for git-lex runtime, semantic-kit evidence, RDF/SPARQL/JSON-LD claim safety, and `.lex` adoption boundaries.
- For general ACP registry/verifier/proof-level questions not specific to git-lex and before the `acp` skill is available, route to `legalgraph-architecture-verification` after preserving the git-lex boundaries above.
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
