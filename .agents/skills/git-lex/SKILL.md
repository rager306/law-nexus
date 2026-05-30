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
