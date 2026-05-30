# ACP boundaries for git-lex work

## Source-truth hierarchy

1. Authoritative source evidence: PRD/GSD/ADR/source code/tests/runtime observations/real-document evidence.
2. Accepted decisions and requirements with tracked proof anchors.
3. ACP source records with explicit lifecycle state, evidence anchor, and proof gate.
4. Derived JSONL/RDF/OWL/SHACL/SPARQL/JSON-LD/recovery/dashboard views.
5. Agent prose, skill text, summaries, and UI views as guidance or diagnostics only.

## Authority rule

An ACP statement becomes authoritative only when all required pieces are present:

```text
source category + lifecycle state + evidence anchor + proof gate or accepted decision
```

Shape alone is not authority. A Turtle triple, JSON-LD object, SPARQL result, dashboard node, or GSD summary can imitate authority unless it is tied back to accepted source/proof machinery.

## Blocked claims without additional proof

Do not claim these from `git-lex-kit-base` ontology files or projections alone:

- Runtime git-lex is adopted as ACP core backend.
- `git lex sync` or frontmatter extraction works in this repository.
- Main-repo `.lex` mutation is safe.
- RDF/OWL/SPARQL/JSON-LD projection validates requirements.
- R035, R037, or R038 are validated.
- Russian legal correctness, parser completeness, FalkorDB runtime behavior, retrieval quality, generated-Cypher safety, product readiness, or LLM authority is proven.

## Safe default position

- git-lex base ontology is strong semantic-kit evidence and a useful design input for ACP.
- ACP may absorb the ontology approach and implement ACP-native records/checks first.
- Runtime git-lex adoption remains blocked or adapter-later until isolated executable proof passes.
- RDF/OWL/SPARQL/JSON-LD outputs are useful for interoperability, audit, recovery, and queryability; they remain derived unless explicitly promoted by ACP rules.

## law-nexus profile boundary

Reusable ACP may define generic source records, lifecycle states, evidence anchors, proof gates, health findings, projections, and claim boundaries. law-nexus profile work owns Russian legal evidence, FalkorDB-specific runtime claims, ODT/Garant parser proof, citation-safe retrieval, and R035/R037/R038 substantive validation.
