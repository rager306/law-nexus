# Architecture Control Plane Fixtures

This directory contains the first minimal Architecture Control Plane (ACP) fixture chain for `law-nexus`.

## Scope

The fixture proves ACP record mechanics only:

```text
ArchitecturePromptRecord
  -> ArchitectureProposal
  -> DecisionCandidate
  -> ProofGate
  -> ArchitectureHealthFinding
```

It is intentionally small, source-linked, and safe. It does not initialize `git lex`, run Understand-Anything, modify the existing architecture registry, or resume the parser roadmap.

## Source of truth boundary

Authoritative project evidence remains in tracked PRD, GSD, source, test, runtime, and accepted decision artifacts. ACP fixtures are source records for a governance-system proof. Any generated recovery view is derived and non-authoritative.

The canonical architecture verifier remains:

```bash
uv run python scripts/verify-architecture-graph.py
```

A passing verifier confirms static architecture checks only. It does not prove runtime behavior, parser completeness, retrieval quality, legal-answer correctness, FalkorDB production behavior, or independent external review.

## Record kinds

The minimal proof uses five record kinds:

| Record kind | Purpose |
| --- | --- |
| `architecture_prompt_record` | Captures architecture-relevant intent after profile policy checks. |
| `architecture_proposal` | Structures a proposal using ACP/Spec Architect rubric fields. |
| `decision_candidate` | Represents a significant decision under review, not accepted doctrine. |
| `proof_gate` | Defines required evidence before a claim can be upgraded. |
| `architecture_health_finding` | Records blocked action, missing evidence, drift, or overclaim risk. |

## Non-goals

This fixture does not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

## Safety policy

Fixture records must not contain:

- secrets or credentials;
- provider payloads;
- raw vectors;
- unnecessary raw legal text;
- local absolute paths;
- durable anchors into transient GSD execution-log directories;
- claims that product, parser, legal, FalkorDB, retrieval, or independent-review proof has been completed.

## Current fixture chain

The current chain is under `fixtures/minimal-chain/`:

- `APR-0001.md`
- `AP-0001.md`
- `DC-0001.md`
- `PG-0001.md`
- `AHF-0001.md`

It demonstrates one safe governance decision: validate ACP fixtures before adding any runtime dashboard or broader registry integration.
