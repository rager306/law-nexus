---
name: falkordb-algorithms
description: Use and verify FalkorDB graph algorithms. Use when the user asks about BFS, PageRank, Betweenness Centrality, CDLP, shortest paths, WCC, MSF, algorithm syntax, algorithm inputs/outputs, or whether FalkorDB algorithms are equivalent to Neo4j GDS.
---

<essential_principles>
## falkordb-algorithms Operating Rules

### 1. Treat FalkorDB algorithms as their own documented surface, not as Neo4j GDS by another name.
### 2. Always name the algorithm, graph shape, input parameters, expected output columns, and verification query.
### 3. Performance or quality claims need runtime/profile evidence, not just docs presence.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: BFS, Betweenness Centrality, Community Detection using Label Propagation (CDLP), PageRank, shortest path procedures, WCC, MSF, algorithm inputs/outputs, and verification fixtures.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, May 2026 evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Use or Verify FalkorDB Algorithms.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or product-adjacent feature drift.
- Gives concrete verification steps.
- Separates documented support from runtime or quality proof.
</success_criteria>
