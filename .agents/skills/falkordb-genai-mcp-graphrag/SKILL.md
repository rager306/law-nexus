---
name: falkordb-genai-mcp-graphrag
description: Build and evaluate FalkorDB GenAI, MCP, and GraphRAG integrations. Use when the user asks about FalkorDB GraphRAG-SDK, LangChain, LangGraph, LlamaIndex, GraphRAG Toolkit, MCP Server, Code-Graph, QueryWeaver, agent memory, or retrieval pipelines over FalkorDB.
---

<essential_principles>
## falkordb-genai-mcp-graphrag Operating Rules

### 1. Keep retrieval quality claims separate from database capability claims.
### 2. Cite docs and versions because GenAI/MCP surfaces move quickly.
### 3. Evaluation must include answer quality, citation/traceability, and failure modes, not just successful connection.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: GraphRAG-SDK, AG2, LangChain, LangGraph, LlamaIndex, GraphRAG Toolkit, MCP Server, Code-Graph, QueryWeaver, graph-backed agent memory, retrieval evals, and tool configuration.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, May 2026 evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Design or Evaluate FalkorDB GenAI/MCP/GraphRAG.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or product-adjacent feature drift.
- Gives concrete verification steps.
- Separates documented support from runtime or quality proof.
</success_criteria>
