---
name: acp
description: law-nexus PROFILE OVERRIDE of the generic ACP skill. Applies law-nexus-specific constraints (R035/R037/R038 profile-owned requirements, Russian legal evidence, FalkorDB, Garant ODT parser, citation-safe retrieval, generated-Cypher safety, legalgraph-architecture-verification routing) on top of the generic ACP governance guidance. Generic guidance (ACP record rule, ACP-kit rule K0-K7, source-truth hierarchy) lives in the external reusable core at /root/git-lex-kit-acp/skills/acp/SKILL.md. Use when work mentions ACP source records, proof gates, architecture binding, ACP-kit, lifecycle/health findings, source-truth boundaries, profile constraints, or validation claims in the law-nexus context.
---

<profile_override_binding>
This is the **law-nexus profile override** of the generic ACP skill.

- **Generic ACP guidance** (ACP record rule: source category + lifecycle state +
  evidence anchor + proof gate + projection status; ACP-kit rule K0-K7 roadmap;
  source-truth hierarchy; ACP→git-lex routing) is **authoritative in the external
  reusable core**: `/root/git-lex-kit-acp/skills/acp/SKILL.md`. Load it for
  generic ACP governance mechanics.
- This override applies **law-nexus-specific constraints**: profile-owned
  requirements (R035/R037/R038 and other law-nexus R-IDs), domain-specific
  evidence (Russian legal / Garant ODT / FalkorDB / citation-safe retrieval /
  generated-Cypher safety), project-specific routing
  (`legalgraph-architecture-verification`), and project-specific verification
  (`verify-m0xx-*.py`, `gitnexus` repo `law-nexus`).
- ACP stays **bound to git-lex**: route git-lex runtime and `.lex` adoption
  questions to the law-nexus `git-lex` profile override (which references the
  external generic git-lex skill).
- See `prd/architecture/PROFILE-ADAPTER.md` for the full binding contract.
- **Drift discipline:** generic guidance is referenced, not duplicated.
</profile_override_binding>

<anti_drift_enforcement>
**D098 — anti-drift enforcement role.** ACP exists to PREVENT project drift, not
to build endless infrastructure. See `prd/architecture/PROFILE-ADAPTER.md` §
Anti-drift enforcement role.

**Mandatory lifecycle tagging in state claims.** When stating the status of any
artifact/capability/milestone/requirement, TAG the lifecycle state explicitly:

```text
[bounded]   — bounded proof on a narrow fixture/scope, NOT production
[smoke]     — runtime/mechanics smoke only, NOT quality/correctness
[validated] — met a proof gate with durable evidence (cite it)
[proposed]  — planned/contracted, not yet executed
[deferred]  — explicitly deferred to a later milestone
```

NEVER smooth a bounded/smoke proof into "validated" or "ready". If you cannot
cite a durable evidence anchor + proof gate for a `[validated]` claim, it is
`[bounded]` or `[smoke]`, not `[validated]`.

**Record rule on architectural/requirement/state claims** (the ACP record rule
itself): source category + lifecycle + evidence anchor + proof gate. Not
prose-only. This is the ACP record rule from the generic skill, applied as
anti-drift enforcement.

**Meta-work budget:** ACP/git-lex is FROZEN until parser data is ready (M034
Consultant XML Parser Hardening executed). Do not propose ACP expansion unless
drift is detected+logged OR the user explicitly directs it. "ACP could be
extended" is the meta-drift pattern to prevent.

**Checkpoint, not gate:** detect+log+flag drift (via ACP HealthFinding); do NOT
block product work.
</anti_drift_enforcement>

<objective>
Use this law-nexus profile override for ACP-native architecture governance and ACP-kit work **in the law-nexus context**. For generic ACP mechanics (record rule, kit rule, source-truth hierarchy), first load the external generic skill at `/root/git-lex-kit-acp/skills/acp/SKILL.md`; then apply the law-nexus-specific constraints below. Keep ACP source truth, lifecycle states, evidence anchors, proof gates, validation claims, health findings, projections, and law-nexus profile boundaries explicit. Route git-lex runtime and `.lex` adoption questions to the law-nexus `git-lex` skill, but keep ACP-kit semantic design here.
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
