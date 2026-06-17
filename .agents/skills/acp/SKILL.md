---
name: acp
description: Guides law-nexus agents through ACP-native architecture governance, source truth, lifecycle states, evidence anchors, proof gates, ACP-kit planning, profile boundaries, and verifier-safe synthesis. Use when work mentions ACP source records, proof gates, architecture binding, ACP-kit, lifecycle/health findings, source-truth boundaries, profile constraints, or validation claims.
---

<objective>
Use this project-local skill for ACP-native architecture governance and ACP-kit work. Keep ACP source truth, lifecycle states, evidence anchors, proof gates, validation claims, health findings, projections, and profile boundaries explicit. Route git-lex runtime and `.lex` adoption questions to the `git-lex` skill, but keep ACP-kit semantic design here.
</objective>

<quick_start>
Start from tracked ACP artifacts, not generated projections or memory alone:

```text
.gsd/REQUIREMENTS.md
.gsd/DECISIONS.md
prd/architecture/acp/M048-S10-ACP-CLOSURE-PACKAGE.md
prd/architecture/acp/M051-S08-ACP-ONTOLOGY-PROTOTYPE.md
prd/architecture/acp/M049-S05-GIT-LEX-ACP-KIT-INTEGRATION-ROADMAP.md
prd/architecture/acp/M049-S05-FINAL-BINDING-SYNTHESIS.md
prd/architecture/acp/M056-S01-BASE-DOMAIN-KIT-INSPECTION.md
prd/architecture/acp/M056-S02-ACP-ONTOLOGY-EXTRACTION.md
prd/architecture/acp/M056-S05-ISOLATED-RUNTIME-PROOF.md
prd/architecture/acp/M056-S06-ACP-KIT-FINAL-SYNTHESIS.md
git-lex-kit-acp/kit.yml
git-lex-kit-acp/ontology/acp/acp.ttl
git-lex-kit-acp/content/AGENTS.md
```

For law-nexus binding work, also read:

```text
prd/architecture/acp/M049-S01-BINDING-INPUT-AUDIT.md
prd/architecture/acp/M049-S02-PROFILE-ADAPTER-BOUNDARY.md
prd/architecture/acp/M049-S03-REGISTRY-SOURCE-MAPPING.md
prd/architecture/acp/M049-S04-BINDING-VERIFIER-CHECKS.md
```

Then load the relevant reference:

```text
references/source-truth-and-proof-gates.md
references/acp-kit-roadmap.md
```
</quick_start>

<essential_guardrails>
- ACP-native records, accepted decisions, tracked source artifacts, tests, runtime observations, and proof gates remain authoritative; projection shape alone is never authority.
- An ACP validation claim needs source category, lifecycle state, evidence anchor, and proof gate or accepted decision.
- RDF/OWL/SHACL/SPARQL/JSON-LD/JSONL dashboards and recovery views are derived unless explicitly tied to ACP source/proof machinery.
- ACP-kit is a semantic-kit implementation track over `git-lex-kit-base`, not immediate git-lex backend/source-truth promotion.
- Do not initialize or mutate main-repo `.lex`, `Squad`, `Raw`, or raw/session payload paths for ACP work without explicit future adoption decision and isolated proof.
- Do not validate R035, R037, or R038 from ACP-kit, git-lex, RDF, SPARQL, JSON-LD, verifier shape, or projection evidence alone.
- Keep reusable ACP core separate from law-nexus profile proof: Russian legal evidence, Garant parser, FalkorDB, retrieval, citation safety, and generated-Cypher safety remain profile-owned.
</essential_guardrails>

<routing>
- For ACP source truth, lifecycle states, evidence anchors, proof gates, validation claims, health findings, architecture binding, or verifier-safe synthesis, read `references/source-truth-and-proof-gates.md`.
- For ACP-kit design, git-lex-kit-base packaging, M051/S08 ontology extraction, K0-K7 roadmap, or ACP-kit v0 boundaries, read `references/acp-kit-roadmap.md`.
- For git-lex executable behavior, `.lex` state, source-built binary proof, sync/query/validate runtime, JSON-LD runtime support, SPARQL-star runtime claims, or production/provenance adoption, use the `git-lex` skill.
- For law-nexus substantive proof, keep ACP routing but use profile-specific evidence: real legal documents, parser tests, FalkorDB runtime proof, retrieval/citation evidence, and generated-Cypher safety proof.
- For architecture registry verifier implementation details, combine this skill with `legalgraph-architecture-verification` after preserving ACP source/proof boundaries.
</routing>

<acp_record_rule>
Before saying an ACP claim is authoritative, check all fields:

```text
source category: PRD | GSD | ADR | source | test | runtime | real-document | accepted decision
lifecycle state: active | validated | deferred | blocked | rejected | superseded
evidence anchor: tracked repository-relative path
proof gate: executable/checkable gate or accepted decision
projection status: source | derived | diagnostic | runtime-smoke | profile-proof
```

If any required field is missing, state the claim as proposed, diagnostic, derived, blocked, or needs proof.
</acp_record_rule>

<acp_kit_rule>
Treat ACP-kit as a controlled packaging of ACP core semantics:

```text
K0 static ontology prototype: M051/S08 done
K1 ACP-kit v0 package: static scaffold ready with verifier
K2 isolated ACP-kit runtime proof: use explicit `rager306/git-lex-kit-acp` kit spec; short `--kit acp` is not canonical
K3 M049 binding projection through ACP-kit records: future proof after ACP runtime semantics gate
K4 L2 operational diagnostics: blocked if it depends on ACP-kit runtime behavior
K5 main .lex rehearsal: blocked until explicit decision
K6 source-truth migration: blocked
K7 production/provenance: blocked
```

ACP-kit v0 should be deterministic, non-adaptive, reusable ACP core. The current scaffold lives in:

```text
git-lex-kit-acp/kit.yml
git-lex-kit-acp/ontology/acp/acp.ttl
git-lex-kit-acp/content/AGENTS.md
```

The scaffold is static package evidence only and not runtime proof. Canonical ACP-kit runtime invocation must use the explicit repository spec: `git-lex init --kit rager306/git-lex-kit-acp <target-repo>`. Do not use short `--kit acp` as the project rule; it follows git-lex short-name resolution and may target `repolex-ai/git-lex-kit-acp`. Current status: full-spec init succeeds in a disposable workspace, but runtime semantics still need proof for class discovery, sync/query/validate, and negative validation. Do not claim main `.lex` safety, source-truth migration, production adoption, L2 runtime diagnostics readiness, or R035/R037/R038 validation from M056.
</acp_kit_rule>

<verification>
For ACP artifacts, verify the narrowest relevant surface:

```text
uv run python scripts/verify-m049-binding.py          # when M049 binding artifacts are affected
uv run python scripts/verify-m056-acp-kit.py          # when ACP-kit scaffold or guidance is affected
python3 -m py_compile <new verifier/test scripts>     # when scripts are added
uv run pytest <targeted tests>                        # when tests exist
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
git diff --check
gitnexus_detect_changes(repo="law-nexus", scope="all")
```

Use focused scans for unsafe anchors, projection-as-authority wording, forbidden R035/R037/R038 validation, generated registry freshness claims, and git-lex promotion beyond the proven boundary.
</verification>

<reference_index>
- `references/source-truth-and-proof-gates.md` explains ACP authority, validation, evidence anchors, profile boundaries, and safe/unsafe claim language.
- `references/acp-kit-roadmap.md` explains the corrected ACP-kit roadmap, v0 package shape, and relationship to git-lex L1/L2 adoption.
</reference_index>

<success_criteria>
Correct ACP work preserves source/proof authority, labels projections and diagnostics as derived, prevents R035/R037/R038 overclaiming, keeps law-nexus profile proof separate from ACP core, and uses ACP-kit as a semantic integration layer rather than as unproven runtime/source-truth adoption.
</success_criteria>
