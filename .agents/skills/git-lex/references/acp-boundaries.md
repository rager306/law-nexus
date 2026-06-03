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

## M053 adapter and provenance boundary

M053 advances git-lex adapter readiness, not ACP adoption.

M053 permits future discussion of only this diagnostic candidate set:

```text
isolated init
isolated sync
list --json
bounded query / query --json
validate behind fail-closed wrapper gates
```

M053 explicitly excludes these from ACP capability/proof scope by default:

```text
Claude/session logs-to-git
Raw/session logs as proof anchors
git lex save/create/raw backfill/join/kit-update/nuke
JSON-LD runtime import/export
broad RDF-star/SPARQL-star parity
release/bundled binary adoption
production ACP adapter adoption
main repository .lex
R035/R037/R038 validation
```

Production provenance remains blocked after M053/S07. A future implementation may use only a source-built isolated proof-only binary after an explicit pin-vs-update decision; it may not use release or plugin-bundled binaries as trusted ACP runtime inputs without a manifest, checksum/signature/SBOM/attestation, source/build/release binding, plugin license decision, rollback plan, and explicit human adoption decision.

Evidence anchors:

- `prd/architecture/acp/M053-S06-MINIMAL-ACP-ADAPTER-BOUNDARY.md`
- `prd/architecture/acp/M053-S07-PRODUCTION-PROVENANCE-RECHECK.md`

## M054 proof-only adapter boundary

M054 proves a useful wrapper/harness for isolated ACP diagnostics, not ACP adoption.

M054 may be cited for this narrow claim:

```text
A pinned source-built proof-only wrapper can run the minimal git-lex diagnostic subset in an isolated synthetic workspace and emit bounded non-authoritative JSON diagnostics while keeping the main checkout free of .lex/Squad/Raw residue.
```

M054 may not be cited for:

```text
ACP source truth transfer
production runtime readiness
release or plugin-bundled binary trust
main repository .lex adoption
R035/R037/R038 validation
Russian legal evidence correctness
FalkorDB runtime behavior
Garant ODT parser completeness
JSON-LD runtime support
broad RDF-star/SPARQL-star parity
real Claude/session logs safety
real legal payload ingestion
```

If future ACP work wants an implementation adapter, it should build from M054's wrapper and keep the same proof-only boundaries until a separate human adoption decision and production/provenance milestone changes them.

Evidence anchors:

- `prd/architecture/acp/M054-S04-PROOF-ONLY-ADAPTER-SPIKE-SYNTHESIS.md`
- `prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl`

## M055 L1 shadow backend boundary

M055 advances git-lex from proof-only adapter evidence to continued L1 shadow diagnostic/projection backend use, but only within the ACP authority hierarchy above.

M055 may be cited for this narrow claim:

```text
ACP can continue using a source-built git-lex adapter as an isolated, non-authoritative L1 shadow diagnostic/projection backend over ACP-shaped synthetic records, with bounded diagnostics and no main .lex/Squad/Raw residue.
```

M055 may not be cited for:

```text
ACP source truth transfer
L2 operational backend readiness
main repository .lex approval
production runtime readiness
release or plugin-bundled binary trust
JSON-LD runtime support
broad SPARQL-star/RDF-star parity
raw/session/provider payload safety
R035/R037/R038 validation
Russian legal evidence correctness
Garant ODT parser completeness
FalkorDB runtime behavior
```

Evidence anchors:

- `prd/architecture/acp/M055-S04-GIT-LEX-REMAINING-ADOPTION-GATES.md`
- `prd/architecture/acp/M055-S05-GIT-LEX-BACKEND-NEXT-DECISION.md`

## law-nexus profile boundary

Reusable ACP may define generic source records, lifecycle states, evidence anchors, proof gates, health findings, projections, and claim boundaries. law-nexus profile work owns Russian legal evidence, FalkorDB-specific runtime claims, ODT/Garant parser proof, citation-safe retrieval, and R035/R037/R038 substantive validation.
