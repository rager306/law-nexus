# FalkorDB GenAI/MCP/GraphRAG Reference Notes

## Scope

GraphRAG-SDK, AG2, LangChain, LangGraph, LlamaIndex, GraphRAG Toolkit, MCP Server, Code-Graph, QueryWeaver, graph-backed agent memory, retrieval evals, and tool configuration.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed surfaces include FalkorDB core v4.18.x, FalkorDB docs updated 2026-05-09, falkordb-py v1.6.x, and FalkorDB Browser v2.x where applicable. Do not treat Neo4j documentation as FalkorDB evidence.

## Gotchas

- Do not claim legal/factual answer quality from graph retrieval mechanics alone.
- MCP server setup is an integration surface, not proof of useful tools.
- Separate graph query correctness from LLM generation behavior.
- Evaluate retrieval quality with held-out questions, expected source nodes/edges, citation checks, and traceability from answer to graph evidence.
- A passing connection smoke test proves connectivity only; it does not prove answer quality, grounding, or safety.

## Required answer shape

- State the task scope and target FalkorDB version/surface.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, query, request, or fixture when applicable.
- Provide verification and rollback/cleanup where writes, operations, generated output, or external integrations are involved.
