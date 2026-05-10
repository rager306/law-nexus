# FalkorDB Skill Authoring Notes

## Local PI/GSD template result

PI/GSD already provides native skill-authoring guidance and templates in the installed package:

- `/usr/lib/node_modules/gsd-pi/dist/resources/skills/create-skill/SKILL.md`
- `/usr/lib/node_modules/gsd-pi/dist/resources/skills/create-skill/templates/router-skill.md`
- `/usr/lib/node_modules/gsd-pi/dist/resources/skills/create-skill/references/gsd-skill-ecosystem.md`

This FalkorDB skill follows that PI-compatible router pattern rather than copying Anthropic's skill format wholesale.

## Anthropic skill-creator findings

Anthropic's `skills/skill-creator` is useful as process prior art:

- capture intent and trigger conditions
- write a draft
- create test prompts/evals
- evaluate qualitative and quantitative behavior
- iterate based on real runs
- optimize description for triggering

For PI/GSD, adapt the loop but keep PI constraints: YAML frontmatter, `SKILL.md`, `.agents/skills/{name}/`, optional `workflows/`, `references/`, `templates/`, and `/reload`/auto-discovery behavior.

## neo4j-skills findings

`neo4j-contrib/neo4j-skills` is useful structurally:

- many narrow skills around coherent work units
- strong descriptions that include trigger contexts
- `When to Use` / `When NOT to Use`
- preflight steps
- decision tables
- runnable snippets
- references for deeper details

For FalkorDB, use this as shape only. Do not copy Neo4j-specific assumptions such as APOC, GDS, Aura, GenAI plugin, Neo4j driver APIs, or Neo4j vector syntax without FalkorDB evidence.

## Vercel AGENTS.md lesson

Vercel's eval found passive compressed docs indexes in `AGENTS.md` more reliable than relying on skill auto-triggering for broad framework knowledge. Applied here by keeping a compact retrieval index directly in `SKILL.md` and using a pushy description. For a future distributable FalkorDB package, consider also shipping an optional `AGENTS.md` snippet that points agents to installed FalkorDB skill/reference files.

## AgentSkills best-practice lesson

AgentSkills recommends:

- start from real expertise and real tasks
- add what the agent lacks, omit what it already knows
- design coherent units
- aim for moderate detail
- use progressive disclosure
- favor procedures over declarations
- include gotchas, templates, checklists, and validation loops

This skill therefore uses a router plus focused workflows/references/templates rather than one exhaustive FalkorDB manual.

## May 2026 skill pack decision

Research in `.gsd/research/falkordb-skill-pack-may-2026.md` found that FalkorDB's May 2026 surface is broad enough for a focused skill pack. Keep `.agents/skills/falkordb/` as the router/index and split high-signal tasks into Phase 1 sibling skills:

- `falkordb-cypher`
- `falkordb-modeling`
- `falkordb-python`
- `falkordb-ops-debug`
- `falkordb-index-search`
- `falkordb-capability-evidence`

Do not clone Neo4j's pack 1:1. Phase 2 adds evidence-bounded skills for algorithms, UDF/FLEX, integrations, GenAI/MCP/GraphRAG, and Browser/REST:

- `falkordb-algorithms`
- `falkordb-udf-flex`
- `falkordb-ingest-integrations`
- `falkordb-genai-mcp-graphrag`
- `falkordb-browser-rest`

Add future language-specific or deployment-specific skills only when each has its own evidence-backed references and evals.

## Future eval prompts

Use these to refine the skill:

1. "Design a FalkorDB graph model for invoices, payments, and disputes with query examples."
2. "Does FalkorDB support vector search in my target runtime? Give proof steps."
3. "Convert this Neo4j Cypher using APOC to a FalkorDB-safe plan."
4. "Write Python code that inserts and queries a small FalkorDB graph safely."
5. "Debug this slow FalkorDB query and identify missing indexes/fan-out."
