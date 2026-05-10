---
name: falkordb
description: General-purpose FalkorDB skill for graph schema design, Cypher query work, Python client usage, FalkorDBLite, capability verification, debugging, and performance review. Use whenever the user asks about FalkorDB, RedisGraph migration, FalkorDB Cypher, graph modeling, full-text/vector indexes, UDF/procedure support, FalkorDB Python client, or FalkorDBLite, even if they do not explicitly ask for a skill.
---

<essential_principles>
## FalkorDB Skill Operating Rules

### 1. FalkorDB-first, not Neo4j-by-copy
Use Neo4j skills only as structural prior art. Never carry over Neo4j-only procedures, APOC/GDS assumptions, Aura assumptions, Cypher version claims, or driver APIs unless FalkorDB docs/source/runtime evidence confirms the equivalent behavior.

### 2. Retrieval-led reasoning
Prefer source-backed or runtime-backed reasoning over model memory for FalkorDB tasks. First inspect the project context, then load the relevant workflow/reference below. If capability certainty matters, use `workflows/check-capability.md` before recommending implementation.

### 3. Separate claim classes
Classify FalkorDB statements as `runtime-confirmed`, `source-backed`, `docs-backed`, `smoke-needed`, `blocked-environment`, `neo4j-only`, `redisgraph-legacy`, or `unknown`. Unknown or smoke-needed claims need an owner, next proof command, and verification criterion.

### 4. Keep answers implementation-safe
For writes, migrations, schema changes, index creation, UDF/procedure work, or performance changes: explain risk, use test data first, and provide rollback/verification steps. Do not invent production guarantees from synthetic smoke tests.

### 5. Progressive disclosure
This SKILL.md is the always-loaded index. Load only the workflow/reference needed for the user's task.
</essential_principles>

<quick_reference>
## FalkorDB Retrieval Index

This is now the router/index for a focused Phase 1 FalkorDB skill pack. Prefer sibling focused skills when the user's intent is narrow:

- Cypher query authoring/review → `.agents/skills/falkordb-cypher/SKILL.md`; local fallback: `workflows/write-cypher.md`, `references/cypher-falkordb.md`, `templates/query-review.md`
- Graph model design/review → `.agents/skills/falkordb-modeling/SKILL.md`; local fallback: `workflows/design-graph-model.md`, `references/graph-modeling.md`, `templates/graph-model-review.md`
- Python client code → `.agents/skills/falkordb-python/SKILL.md`; local fallback: `workflows/use-python-client.md`, `references/python-client.md`
- Operational debugging/performance → `.agents/skills/falkordb-ops-debug/SKILL.md`; local fallback for Slow queries/errors/runtime failures: `workflows/debug-performance.md`, `references/troubleshooting.md`, `references/cypher-falkordb.md`
- Range/full-text/vector indexes and search → `.agents/skills/falkordb-index-search/SKILL.md`; local fallback: `references/indexes-search-vector.md`. For Vector/full-text/index/procedure/UDF claims, route through `workflows/check-capability.md` first.
- Capability verification / Neo4j drift control → `.agents/skills/falkordb-capability-evidence/SKILL.md`; local fallback: `workflows/check-capability.md`, `references/capability-evidence.md`, `templates/capability-answer.md`
- FalkorDBLite/embedded use → `workflows/use-falkordblite.md`, `references/falkordblite.md` until a separate focused skill is justified
- Algorithms → `.agents/skills/falkordb-algorithms/SKILL.md`
- UDF/FLEX functions → `.agents/skills/falkordb-udf-flex/SKILL.md`
- Ingest/integrations → `.agents/skills/falkordb-ingest-integrations/SKILL.md`
- GenAI/MCP/GraphRAG → `.agents/skills/falkordb-genai-mcp-graphrag/SKILL.md`
- Browser/REST → `.agents/skills/falkordb-browser-rest/SKILL.md`
- Skill design provenance → `references/skill-authoring-notes.md`
</quick_reference>

<routing>
| User intent | Load and follow |
|---|---|
| Design/review graph schema, labels, relationships, properties | `.agents/skills/falkordb-modeling/SKILL.md`, fallback `workflows/design-graph-model.md` |
| Write, translate, or review FalkorDB Cypher | `.agents/skills/falkordb-cypher/SKILL.md`, fallback `workflows/write-cypher.md` |
| Use `falkordb-py` / Python client | `.agents/skills/falkordb-python/SKILL.md`, fallback `workflows/use-python-client.md` |
| Use embedded FalkorDBLite | `workflows/use-falkordblite.md` |
| Use FalkorDB algorithms | `.agents/skills/falkordb-algorithms/SKILL.md` |
| Use UDF/FLEX functions | `.agents/skills/falkordb-udf-flex/SKILL.md` |
| Plan ingest/integrations | `.agents/skills/falkordb-ingest-integrations/SKILL.md` |
| Build GenAI/MCP/GraphRAG integrations | `.agents/skills/falkordb-genai-mcp-graphrag/SKILL.md` |
| Use Browser/REST API | `.agents/skills/falkordb-browser-rest/SKILL.md` |
| Ask whether FalkorDB supports a capability | `.agents/skills/falkordb-capability-evidence/SKILL.md`, fallback `workflows/check-capability.md` |
| Work with range/full-text/vector indexes or search | `.agents/skills/falkordb-index-search/SKILL.md`, fallback `workflows/check-capability.md` |
| Debug errors, slow queries, indexes, plans, runtime behavior | `.agents/skills/falkordb-ops-debug/SKILL.md`, fallback `workflows/debug-performance.md` |
| Build/refine this skill pack itself | `references/skill-authoring-notes.md` plus PI create-skill guidance |

If multiple rows match, inspect project context first, then choose the narrowest workflow that can answer safely.
</routing>

<reference_index>
Domain references in `references/`:
- `capability-evidence.md` — claim classes and proof protocol
- `cypher-falkordb.md` — FalkorDB Cypher writing and review guardrails
- `graph-modeling.md` — graph schema design heuristics
- `indexes-search-vector.md` — index/full-text/vector capability boundaries and proof steps
- `python-client.md` — `falkordb-py` usage patterns
- `falkordblite.md` — embedded FalkorDBLite use and caveats
- `troubleshooting.md` — runtime/debug/performance workflow notes
- `skill-authoring-notes.md` — PI/neo4j-skills/Vercel/AgentSkills/Anthropic design provenance
</reference_index>

<workflows_index>
| Workflow | Purpose |
|---|---|
| `design-graph-model.md` | Design or review a FalkorDB graph schema |
| `write-cypher.md` | Write/review FalkorDB Cypher safely |
| `use-python-client.md` | Implement or review Python client usage |
| `use-falkordblite.md` | Use FalkorDBLite for embedded/local workflows |
| `check-capability.md` | Verify support claims before relying on them |
| `debug-performance.md` | Debug runtime errors, slow queries, and plan/index issues |
</workflows_index>

<success_criteria>
A good FalkorDB answer:
- States whether each important claim is runtime-confirmed, source/docs-backed, smoke-needed, or unknown.
- Avoids Neo4j-only feature drift unless FalkorDB evidence confirms support.
- Gives runnable verification steps for capability-sensitive advice.
- Separates graph design, query syntax, client usage, and operational/runtime constraints.
- Produces a concrete next action rather than a generic graph database lecture.
</success_criteria>
