# Architecture Control Plane

ACP means **Architecture Control Plane**.

It is a reusable architecture-governance layer for architecture construction and recovery. `law-nexus` is the first proving ground, not the intended limit of the concept.

## Why ACP exists

Large proof-heavy projects accumulate decisions, proposals, gates, non-claims, and drift risks. Plain prose makes it hard for future agents to know:

- what is accepted;
- what is only proposed;
- what proof is still required;
- what actions are blocked;
- what can be safely said;
- what must not be claimed.

ACP gives those concerns a structured control-plane shape.

## Current ACP record chain

The current minimal ACP fixture chain is:

```text
ArchitecturePromptRecord
→ ArchitectureProposal
→ DecisionCandidate
→ ProofGate
→ ArchitectureHealthFinding
```

See `prd/project-state/diagrams/acp-control-plane.mmd`.

## Current ACP state

Current state from `prd/project-state/data/acp-state.json`:

| Capability | State |
|---|---|
| Fixture chain | complete |
| Schema extension | complete |
| Canonical registry projection | complete |
| Default registry integration | complete for current bounded ACP governance rows |
| Recovery view | complete |
| Architecture projection preview | complete |
| RDF/SHACL/SPARQL projection | custom-only complete |
| RDF projection hardening | complete |
| Decision lifecycle workflow | not started |
| CI quality gate | not started |
| External package split | not started |
| Runtime dashboard | not started |

## Current counts

- Architecture items: 63.
- Architecture edges: 98.
- ACP items: 5.
- ACP edges: 7.
- RDF resources: 161.
- Turtle statements: 422.
- RDF diagnostics: 0.

## Current outputs

Key ACP/projection artifacts:

- `prd/architecture/acp/M046-RDF-PROJECTION-HARDENING-CONTRACT.md`
- `prd/architecture/acp/M046-RDF-PROJECTION-HARDENING-DECISION.md`
- `prd/architecture/acp/derived/recovery-view.json`
- `prd/architecture/acp/derived/architecture-projection.preview.json`
- `prd/architecture/acp/derived/architecture-projection.ttl`
- `prd/architecture/acp/derived/architecture-projection.shacl.ttl`
- `prd/architecture/acp/derived/architecture-projection.sparql`
- `prd/architecture/acp/derived/architecture-projection-rdf-report.json`

## RDF/SHACL/SPARQL projection status

The projection is custom-only, derived, and non-authoritative.

It supports:

```bash
uv run python scripts/export-architecture-rdf-projection.py
uv run python scripts/export-architecture-rdf-projection.py --check
uv run python scripts/export-architecture-rdf-projection.py --diff
```

The `--diff` mode is non-writing. It reports whether outputs are current, missing, or stale with byte and SHA-256 metadata.

## Non-claims

ACP fixtures and projections do not validate:

- R035;
- R037;
- R038;
- product readiness;
- legal correctness;
- parser completeness;
- FalkorDB runtime loading;
- retrieval quality;
- RDF completeness;
- SHACL completeness;
- SPARQL engine correctness.

ACP `decision_candidate` rows are not accepted decisions. ACP `proof_gate` rows are not proof-gate satisfaction.

## Main remaining gap

The main ACP gap is **Decision Lifecycle Workflow**.

That future milestone should define safe movement from `decision_candidate` into accepted, deferred, rejected, or superseded states. It should enforce authority requirements, proof-gate coverage, blocked actions, source-anchor safety, non-claim preservation, and R038-aware independent review evidence.

## Secondary future options

Only choose these if they become more important than lifecycle governance:

- RDF engine spike;
- SHACL engine spike;
- isolated git-lex alignment spike;
- ACP recovery/dashboard views;
- externalizable ACP core/profile split.
