---
name: git-lex
description: law-nexus PROFILE OVERRIDE of the generic git-lex skill. Applies law-nexus-specific constraints (R035/R037/R038, Russian legal evidence, FalkorDB, Garant ODT parser, citation-safe retrieval, generated-Cypher safety) on top of the generic git-lex guidance. Generic guidance (runtime findings, workflows, claim-language) lives in the external reusable core at /root/git-lex-kit-acp/skills/git-lex/SKILL.md. Use when work mentions git-lex, git-lex-kit-base, semantic kits, ontology projection, ACP RDF/OWL/SPARQL/JSON-LD, .lex state, or git-lex runtime adoption in the law-nexus context.
---

<profile_override_binding>
This is the **law-nexus profile override** of the generic git-lex skill.

- **Generic git-lex guidance** (runtime findings M051/S10 smoke, M064 SHACL
  internals, M065 release install, 4 workflows inspect-base-kit/classify-evidence/
  review-acp-claim/plan-adapter-spike, claim-language safe/unsafe wording,
  claim-review template, claude-logs boundary, knowledge-delta contract,
  runtime-adoption-gates generic mechanics, ontology-map, source-inventory generic,
  acp-boundaries generic rules) is **authoritative in the external reusable core**:
  `/root/git-lex-kit-acp/skills/git-lex/SKILL.md`. Load it for generic git-lex
  behavior.
- This override applies **law-nexus-specific constraints** on top: profile-owned
  requirements (R035/R037/R038), domain-specific evidence (Russian legal / Garant
  ODT / FalkorDB / citation-safe retrieval / generated-Cypher safety),
  project-specific routing (`legalgraph-architecture-verification`), and
  project-specific verification (`verify-m0xx-*.py`, `gitnexus` repo `law-nexus`).
- See `prd/architecture/PROFILE-ADAPTER.md` for the full binding contract.
- **Drift discipline:** generic guidance is referenced, not duplicated. If the
  external generic changes, law-nexus inherits it.
</profile_override_binding>

<anti_drift_enforcement>
**D098 — anti-drift enforcement role.** This skill (and ACP/git-lex overall)
exists to PREVENT project drift, not to build endless infrastructure. See
`prd/architecture/PROFILE-ADAPTER.md` § Anti-drift enforcement role.

**Mandatory lifecycle tagging in state claims.** When stating the status of any
artifact/capability/milestone/requirement, TAG the lifecycle state explicitly:

```text
[bounded]   — bounded proof on a narrow fixture/scope, NOT production
[smoke]     — runtime/mechanics smoke only, NOT quality/correctness
[validated] — met a proof gate with durable evidence (cite it)
[proposed]  — planned/contracted, not yet executed
[deferred]  — explicitly deferred to a later milestone
```

NEVER smooth a bounded/smoke proof into "validated" or "ready". The exact drift
pattern this prevents: calling bounded retrieval "validated" when the evidence
is mechanics-only. If you cannot cite a durable evidence anchor + proof gate for
a `[validated]` claim, it is `[bounded]` or `[smoke]`, not `[validated]`.

**Record rule on architectural/requirement/state claims** (not every prose
statement): source category + lifecycle + evidence anchor + proof gate. Not
prose-only.

**Meta-work budget:** ACP/git-lex is FROZEN until parser data is ready (M034
Consultant XML Parser Hardening executed). Do not propose ACP/git-lex expansion
unless drift is detected+logged OR the user explicitly directs it. "ACP could be
extended" is the meta-drift pattern to prevent.

**Checkpoint, not gate:** detect+log+flag drift; do NOT block product work.
</anti_drift_enforcement>

<objective>
Use this law-nexus profile override when work touches git-lex, `git-lex-kit-base`, semantic kits, RDF/OWL/SPARQL/JSON-LD interoperability claims, `.lex` repository state, or ACP integration decisions **in the law-nexus context**. For generic git-lex behavior (runtime mechanics, claim language, workflows), first load the external generic skill at `/root/git-lex-kit-acp/skills/git-lex/SKILL.md`; then apply the law-nexus-specific constraints below. The goal is to advance git-lex for ACP through real source evidence while preserving the boundary between semantic-kit evidence, derived projections, runtime proof, and authoritative law-nexus product/legal proof.
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
When work needs a local `git-lex` / `git-lex-serve` binary, use this order before claiming runtime availability.

**Two runtime levels now exist:** the M051/S10 DEBUG source-build at `target/debug/` (steps below) for source-build recon, and the M065/S02 RELEASE install at `~/.cargo/bin/` on PATH — the preferred runtime path for S03/S04 rehearsal proofs (see `<m065_stage2_release_install>`). The release install already exists; prefer it for any PATH-resolved runtime claim.

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
NOTE: these M051/S10 findings used the source-built DEBUG binary at `target/debug/`. M065/S02 later shipped a RELEASE install to `~/.cargo/bin/` on PATH — see `<m065_stage2_release_install>` for the current cold-PATH install proof (incl. the `git lex --help` rc=16 man-dispatch gotcha). The release install is the preferred runtime path for future proofs.

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

<m064_shacl_validate_internals>
M064 (ACP-kit SHACL strengthening, M058 root-cause closeout) read the git-lex
Rust source directly and ran isolated `/tmp` runtime recon. These are durable
git-lex behavioral facts (source-anchored, `main.rs`/`extraction.rs`/`ontology.rs`/
`shacl.rs`), valid for the source-built debug binary at
`/root/vendor-source/git-lex/target/debug/git-lex`. They RESOLVE the M051 open
item "Negative validation remains unproven: a malformed fixture failed to fail."

**cmd_validate shape loading is additive over static + adaptive (the linchpin).**
`cmd_validate` (main.rs ~1216+) collects SHACL from BOTH the static kit shapes
`.lex/ontology/{short}/{short}-shapes.ttl` AND every `_ontology/{name}/{name}-shapes.ttl`
(any `*-shapes.ttl` under `_ontology/`), `join("\n")` into ONE shapes graph, and
compiles via `ShaclSchemaIR::compile`. SHACL validates a node against ALL shapes
that target it, so adding adaptive shapes only TIGHTENS. Consequence: a
strengthened ontology seeded as an adaptive ontology is enforced on top of the
(published) static shapes — no generator change or static-overlay fight needed.

**Detection reads STATIC shapes; enforcement reads static+adaptive — a version
mismatch.** `frontmatter_to_turtle` (extraction.rs ~160-275) classifies each
property value using `get_object_properties`/`get_property_datatypes`, which
read shapes via `read_kit_shapes`/`all_shape_files` (ontology.rs ~27-38): these
walk `.lex/ontology/` FIRST then `_ontology/`, sorted, returning the FIRST match
→ the STATIC (published) shapes govern DETECTION. But `cmd_validate` ENFORCEMENT
concatenates static + adaptive. So if an adaptive ontology adds a `sh:datatype`
the static shapes lack, extraction still emits an UNTYPED literal while validate
rejects it → SPURIOUS violation. CONCRETE (M064 S03, MEM551): the strengthened
`acp.ttl` v0.2.0 emits `sh:datatype xsd:boolean` for `nonAuthoritative` on the
adaptive shapes, but extraction reads static v0.1.0 (no datatype) and emits
`nonAuthoritative` as a plain string `"true"` → EVERY record with
`nonAuthoritative: true` gets a spurious "Expected datatype: xsd:boolean"
violation under the overlay. Boolean/dateTime false-positives follow the same
mechanic. **Do not assume detection and enforcement read the same shapes file.**

**`git-lex sync` MUST run before `git-lex validate` for adaptive constraints.**
The only `build_adaptive_shapes()` call is at the top of `cmd_sync`
(main.rs ~1605-1614); `cmd_validate` only reads pre-built `_ontology/*/*-shapes.ttl`.
If those files are absent at validate time, validate silently falls back to
static-only shapes → every adaptive-only negative PASSES (silent failure, exit 0).
Always run `sync` between seeding an adaptive ontology and `validate`.

**cmd_validate document walk + exit-code mapping.** `walk_md` (main.rs ~1283)
recurses ALL `.md` files in the git root, SKIPPING dot-prefixed directories.
Class-template files shipped by kits (`__{Class}.md`) have EMPTY frontmatter
(`---\n---`) → emit no typed subject → never produce violations (safe to leave).
`cmd_validate` returns `bool`: `true` on all-pass, `false` on ≥1 violation; the
CLI maps `false` → NON-ZERO exit. "all pass" stderr: `Validated N files in Xms —
all pass ✓`; violation stderr: `Validated N files in Xms — V violation(s) in F
file(s)`, then per-file `  {relpath} — {n} violation(s):` and per-result `    → {message}`.

**Data graph is parsed `ReaderMode::Strict` → ill-typed literals are SKIPPED, not
flagged.** An ill-typed literal like `"xyz"^^xsd:boolean` or `"not-a-date"^^xsd:dateTime`
is parse-rejected by oxigraph Strict mode → the file is `continue`-skipped
(main.rs ~1348) → its violations never count → exit 0. So a parse-error skip is
INDISTINGUISHABLE from a pass in the exit code. Therefore datatype-ill-typed
literals are NOT usable as true-negatives; they silently pass.

**Which true-negatives actually reject (proven M064 S03, disposable `/tmp`).**
Given the detection/enforcement mismatch + Strict parsing, only TWO negative
kinds reliably produce a non-zero exit under the adaptive-overlay path:
  - ENUM (`sh:in`): a value outside the enum emitted as a plain string literal.
    (Detection does not read `sh:in`, so the generator's `sh:in` for an enum
    datatype still emits the value untyped → `sh:in` rejects it.) Example:
    `acp.ProofGate.verdict: "totally-bogus"` → `In constraint not satisfied`.
  - MINCOUNT (`sh:minCount 1`): a required field simply ABSENT. Example: an
    `EvidenceAnchor` with NO `sourceArtifact` → `MinCount(1) not satisfied`.
The following do NOT work as true-negatives: object-property links
(`frontmatter_to_turtle` normalizes them to `urn:entity:{slug}` IRIs that satisfy
`sh:nodeKind sh:IRI` → pass); xsd:string-only properties (no `sh:datatype`, no
constraint); boolean/dateTime ill-typed literals (Strict-parse skipped → exit 0).

**The proven clean proof mechanic (M064 S02/S03, MEM549).** To prove an ontology
change reaches generated shapes AND validate rejects negatives, in a disposable
`/tmp` git repo: (1) `git-lex init --kit {owner}/{repo}` (downloads published
kit; uses the FULL owner/repo spec — short aliases still resolve to the default
owner); (2) seed the strengthened `{short}.ttl` as an ADAPTIVE ontology at
`_ontology/{short}/{short}.ttl` — agent-owned, NEVER force-clobbered (init/
kit-update ALWAYS clobber the STATIC ontology at `.lex/ontology/{short}/{short}.ttl`
from the freshly-fetched tarball, ignoring `--force`; sync only regenerates
ADAPTIVE shapes, never static); (3) `git add -A && git commit --no-verify` to
seed HEAD (init's auto-commit fails because its pre-commit hook can't find
`git-lex` on PATH — use `--no-verify`); (4) `git-lex sync` (regenerates
`_ontology/{short}/{short}-shapes.ttl`); (5) `git-lex validate`. To keep the
proof isolated from detection/enforcement-mismatch noise, the proof workspace
may delete published records that carry a boolean/dateTime field the adaptive
shapes newly constrain. Always assert no main-repo `.lex`/`Squad`/`Raw`/`.artifacts`
residue before AND after.

**Boundary.** These facts describe git-lex's generation/validate mechanics under
the source-built debug binary and the adaptive-overlay path. They do NOT prove
ACP source truth, runtime/production adoption, main-`.lex` safety, object-link
correctness, general SHACL conformance, or R035/R037/R038 validation. The
boolean extraction/enforcement mismatch is an open git-lex behavior, not an
ACP-validated mechanism.
</m064_shacl_validate_internals>

<m065_stage2_release_install>
M065/S02 (Stage 2 of D084) promoted git-lex from a source-built DEBUG binary (M051/S10) to a RELEASE install on PATH. Re-verified by fresh cold-PATH run (env -i, /tmp, no vendor-dir); all rc below match install-proof.json byte-for-byte.

**Install (T01, manifest-continuation of M051/S09 §T04):**
- `cargo install --path . --locked` from pinned `/root/vendor-source/git-lex` (commit `eaa4b24d144a78a8b8e4969404d74cf22267df1f`) installs BOTH `git-lex` + `git-lex-serve` to `~/.cargo/bin/` with `install.profile = release`, `install_rc = 0`.
- `--locked` is MANDATORY (rudof sibling-crate API coupling); an unlocked install / lockfile patch / silent debug-binary fallback = BLOCKER (S01 §1).
- `prd/architecture/acp/runtime/m065-s02/install-manifest.json` = binary identity anchor (sha256/size/mode/mtime + builder/toolchain record).
- `prd/architecture/acp/runtime/m065-s02/install-proof.json` = cold-PATH proof anchor.

**Cold-PATH proof (T02) — anchor on these, NOT on `git lex --help`:**
`git lex --help` exits **rc=16** with "No manual entry for git-lex": git intercepts `--help` for EXTERNAL subcommands (git-foo on PATH) and routes it to man(1) instead of pass-through. The proven cold-PATH help resolution rc=0 is the DIRECT binary:
- `git-lex --help`       → rc=0 + banner "Git extensions for knowledge graphs" (git_lex_direct_help)
- `git-lex-serve --help` → rc=0 + banner "Servers for git-lex knowledge graphs"
- `git lex` (no-args)    → rc=2 + banner (git found git-lex via cold PATH and dispatched 'lex' — dispatch PROVEN; clap printed banner+usage, missing required subcommand)
- `git lex --version` / `git-lex-serve --version` → rc=2 (version gap: git-lex exposes NO --version; binary sha256 is the version surrogate. NEVER claim/assert a version number)
A nonexistent subcommand (`git __nosuchcmd_xyz__ --help`) → rc=1 "is not a git command", proving git distinguishes a resolved 'lex' from not-found.

**Deterministic verifier (T03):** `scripts/verify-m065-s02-release-install.py` — stdlib-only inspection surface. Deliberately imports NO subprocess (cannot run git lex / build / mutate). Re-asserts: both binaries present + executable (X_OK) + sha256 byte-for-byte vs install-manifest.json (binary_identity_drift on mismatch), install-proof.json gate fields (git_lex_direct_help rc=0+banner, git_lex_serve_help rc=0+banner, git_subcommand_dispatch rc=2+banner, version_gap_confirmed true + git_lex_version_rc==2 + git_lex_serve_version_rc==2, residue_guard before/after all absent, cli_install_only_boundary.wont non-empty), S01 install-contract continuity (prd/.../m065-s01/install-contract.md), and R047 main-checkout residue guard (.lex/Squad/Raw/.artifacts absent). Checks the REAL key `git_lex_direct_help`, NOT a nonexistent `git_lex_help` (would falsely fail every correct install). Companion: `scripts/verify-m065-s01-install-contract.py` (S01 contract verifier, still green).

**Skill-use implication:** for any future runtime/rehearsal proof (S03/S04), the preferred `git-lex`/`git-lex-serve` on PATH is the Stage-2 RELEASE install at `~/.cargo/bin/` — not the M051/S10 debug binary at `target/debug/`. The cold-PATH dispatch proof anchors on `git lex` no-args (rc=2 + banner) and `git lex --version` (rc=2), never on `git lex --help`.

**Boundary (CLI-install-only, preserved):** no main-repo `.lex` initialization (R047), no R035/R037/R038 validation, no ACP-kit source truth, no single-repo/Stage-3 `.lex` adoption, no `serve`/`viz`/`listen` server exposure, no `nuke`/`kit-update`/`save`/`create`/`join`/`raw` mutating surfaces. This is an install-proof, not a production-readiness or capability claim.
</m065_stage2_release_install>

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
