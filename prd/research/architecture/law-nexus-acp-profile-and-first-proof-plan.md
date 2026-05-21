# law-nexus ACP Profile and First Implementation Proof Plan

**Date:** 2026-05-21

## Status

Source-backed planning artifact for `M035-775l5y / S05`.

This artifact applies the reusable Architecture Control Plane (ACP) contract to `law-nexus` and defines the first minimal implementation-proof plan for a later milestone. It does not implement ACP runtime, initialize experimental tools in the main repository, or validate product/parser/FalkorDB/legal/retrieval readiness.

## Summary

`law-nexus` is the first proving ground for the reusable ACP. The project profile must be stricter than the generic core because it governs architecture work around Russian legal source evidence, parser proof boundaries, FalkorDB capability claims, non-authoritative LLM workflows, and GSD-managed milestone evidence.

The profile rule is simple:

```text
ACP may recover and govern architecture state.
ACP may not upgrade legal, parser, FalkorDB, retrieval, product, or independent-review claims without matching proof gates.
```

The first implementation proof should be deliberately tiny: one safe fixture chain from prompt provenance to proposal, decision candidate, proof gate, health finding, and derived recovery view. It should prove ACP mechanics only, not law-nexus product readiness.

## Source inputs

| Source | Role |
| --- | --- |
| `prd/research/architecture/architecture-control-plane-contract.md` | Reusable ACP core contract. |
| `prd/research/architecture/git-lex-mechanics-for-architecture-control-plane.md` | Typed Git-native record and projection mechanics. |
| `prd/research/architecture/spec-kit-plus-phr-adr-mechanics-for-architecture-control-plane.md` | PHR/ADR provenance and decision workflow mechanics. |
| `prd/research/architecture/understand-anything-visualization-fit-for-architecture-control-plane.md` | Derived visualization/recovery mechanics and warning model. |
| `prd/09_architecture_planning_verification_research.md` | Existing architecture planning verification context. |
| `prd/architecture/README.md` | Current architecture registry/report/verifier boundary. |
| `.agents/skills/legalgraph-architecture-verification/SKILL.md` | Project-local architecture verification routing rules. |
| `.agents/skills/legalgraph-nexus/SKILL.md` | Project-local LegalGraph boundary and terminology router. |

## Profile identity

```yaml
profile_id: law-nexus
profile_scope: first proving ground for reusable ACP
profile_mode: strict
architecture_verifier: uv run python scripts/verify-architecture-graph.py
execution_adapter: GSD
source_record_style: Markdown/frontmatter first, derived JSONL/RDF/dashboard later
visualization_authority: false
llm_authority: false
```

## Source-of-truth hierarchy for law-nexus

1. Tracked source evidence:
   - PRD files;
   - GSD milestones/slices/tasks/summaries;
   - accepted decisions;
   - source code and tests;
   - runtime smoke/integration/real-document proof;
   - curated research artifacts.
2. ACP typed records:
   - `ArchitecturePromptRecord`;
   - `ArchitectureProposal`;
   - `DecisionCandidate`;
   - `ArchitectureDecision`;
   - `ProofGate`;
   - `EvidenceAnchor`;
   - `ArchitectureHealthFinding`.
3. Derived projections:
   - architecture JSONL registry;
   - graph/report views;
   - RDF/N-Quads/SPARQL projection;
   - dashboard JSON;
   - recovery graph.
4. Diagnostics:
   - verifier output;
   - dashboard warnings;
   - scan reports;
   - GSD status.
5. External AI context:
   - MiniMax output;
   - GPT-5.5 review output;
   - Grok dialogue;
   - other external LLM discussions.

Derived projections and external AI context cannot override tracked source evidence.

## Profile-specific proof boundaries

### R035

R035 remains active/not validated unless separate proof exists for actual registry extractor integration, regenerated registry outputs, and accepted proof-gate evidence.

Blocked claim patterns:

- architecture research upgrades R035;
- ACP contract upgrades parser-completeness status;
- PHR/ADR/visualization proves registry integration.

Allowed claims:

- ACP can define a future proof gate for R035-related registry integration.
- ACP can show R035 remains blocked or active.

### R037

R037 remains not validated unless FalkorDB ingestion/runtime loading proof exists.

Blocked claim patterns:

- graph-context staging described as runtime FalkorDB loading;
- visual graph export described as runtime graph loading proof;
- architecture dashboard used as FalkorDB behavior proof.

Allowed claims:

- ACP can model FalkorDB ingestion as a proof gate.
- ACP can surface missing runtime evidence as a health finding.

### R038

R038 remains active/not validated unless independent external review proof exists.

Blocked claim patterns:

- external review pack upgrades R038;
- GPT-5.5 control over CLI outputs counted as independent external review;
- PHR/ADR counted as independent review proof.

Allowed claims:

- ACP can record external review packs as context/evidence candidates.
- ACP can require separate independent-review proof before validation.

## Legal and source evidence constraints

The profile must preserve source-role distinctions:

| Source role | Meaning | ACP handling |
| --- | --- | --- |
| `full-normative-act` | Primary Consultant XML source role for the full act. | May be referenced by role and bounded source path; not raw legal text by default. |
| `document-list-prior-art` | Consultant XML document-list prior-art source role. | Must not be conflated with full normative act evidence. |
| Garant ODT evidence | Separate source family. | Must not validate Consultant WordML/XML behavior. |
| Old_project prior art | Historical hints and comparison anchors. | Not trusted implementation; requires deterministic rederivation. |

The profile should not persist unnecessary raw legal text in ACP records. It may persist bounded source-role metadata, hashes, counts, relative references, parser fixture taxonomy, and evidence summaries.

## LLM and external-review constraints

### MiniMax

MiniMax remains non-authoritative. It may propose structures or candidates, but deterministic verifier/proof gates decide adoption.

### GPT-5.5

GPT-5.5 may be external control over CLI outputs or review packs. It is not a runtime judge and does not validate R038 unless a separate independent-review proof process is accepted.

### Grok and other AI dialogue

External AI dialogue is context-only. It may inform proposals but must be converted into source-backed ACP records and accepted decisions before affecting architecture state.

## GSD integration profile

GSD remains the execution/proof adapter.

Mapping:

| ACP record | law-nexus GSD mapping |
| --- | --- |
| `ArchitecturePromptRecord` | Captured architecture-relevant user intent, linked to milestone/slice/task when applicable. |
| `ArchitectureProposal` | Research artifact, context artifact, or milestone/slice plan. |
| `DecisionCandidate` | Proposed decision requiring authority or follow-up. |
| `ArchitectureDecision` | GSD decision plus ACP typed decision metadata when accepted. |
| `ProofGate` | Task/slice verification contract, gate result, or verifier command. |
| `EvidenceAnchor` | Repo-relative source/test/PRD/GSD summary artifact. |
| `ArchitectureHealthFinding` | GSD validation finding, reassessment, blocker, or follow-up. |

Important GSD operational constraint:

```text
Do not include .gsd/... paths in keyFiles for git closeout in law-nexus because .gsd is a symlink/ignored path.
```

Durable artifacts may reference `.gsd/...` as source evidence when appropriate, but closeout key files should use tracked non-`.gsd` files unless GSD internals handle the symlink safely.

## Canonical verifier profile

The canonical architecture verifier remains:

```bash
uv run python scripts/verify-architecture-graph.py
```

A passing verifier means static architecture registry/report/source-anchor/decision-fitness/claim-safety checks pass. It does not prove:

- runtime behavior;
- parser completeness;
- retrieval quality;
- FalkorDB production scale;
- legal-answer correctness;
- LLM authority;
- independent external review.

## Profile health checks

The law-nexus ACP profile should flag:

- accepted decision without provenance;
- accepted decision without proof gate for proof-sensitive claim;
- verified decision without evidence anchor;
- PHR with unsafe capture mode;
- PHR containing secrets/provider payloads/unnecessary raw legal text;
- external AI dialogue treated as authority;
- graph-context staging described as runtime FalkorDB loading;
- Consultant XML evidence and Garant ODT evidence mixed into one proof chain;
- Old_project treated as trusted implementation;
- R035/R037/R038 upgraded without matching proof;
- generated visualization described as validation;
- absolute local paths in durable records;
- `.gsd/exec` used as durable evidence anchor;
- missing source-role metadata for legal-source references.

## Blocked and allowed actions

### Allowed actions

- Capture architecture-relevant prompt intent as `ArchitecturePromptRecord` after safety filtering.
- Draft `ArchitectureProposal` from source-backed research.
- Create `DecisionCandidate` when significance gates pass.
- Link accepted decisions to GSD work and proof gates.
- Generate derived recovery views from ACP source records.
- Surface missing evidence as health findings.
- Keep parser roadmap paused while ACP design/proof work proceeds.

### Blocked actions

- Mark `R035`, `R037`, or `R038` validated from ACP research alone.
- Treat MiniMax/GPT/Grok output as authority.
- Treat PHR, ADR, GSD summary, verifier report, or visualization as runtime/legal/product proof.
- Initialize experimental architecture tools directly in the main repository without a safe spike.
- Merge Consultant XML evidence and Garant ODT evidence into one proof chain.
- Restart Consultant XML parsing from zero or discard the M009 baseline.
- Use raw secrets, provider payloads, raw vectors, or unnecessary raw legal text in ACP durable artifacts.

## First implementation proof plan

### Goal

Prove ACP mechanics on a tiny safe fixture chain without changing law-nexus product architecture or parser roadmap.

### Non-goals

The first proof will not:

- implement full git-lex integration;
- initialize `git lex` in the main repo;
- run Understand-Anything runtime in the main repo;
- validate R035/R037/R038;
- validate parser completeness;
- perform FalkorDB ingestion;
- generate legal answers;
- perform independent external review;
- modify Consultant XML parser behavior.

### Proposed future milestone or slice

Working title:

```text
ACP Minimal Fixture Chain Proof
```

Thin vertical slice:

```text
schema -> fixture records -> validator -> derived recovery JSON/report -> tests -> architecture verifier remains green
```

### Minimal fixture chain

Create a small fixture under a future tracked location such as:

```text
prd/architecture/acp/fixtures/minimal-chain/
```

Candidate records:

```text
APR-0001 ArchitecturePromptRecord
AP-0001 ArchitectureProposal
DC-0001 DecisionCandidate
PG-0001 ProofGate
AHF-0001 ArchitectureHealthFinding
```

Fixture topic should be self-referential and safe:

```text
Adopt ACP minimal fixture validation before any runtime dashboard/export integration.
```

This avoids legal source data, provider payloads, parser claims, FalkorDB runtime claims, and product readiness claims.

### Likely files for future implementation

Potential tracked files:

- `prd/architecture/acp/README.md`
- `prd/architecture/acp/schema.json`
- `prd/architecture/acp/fixtures/minimal-chain/*.md`
- `scripts/verify-acp-records.py`
- `scripts/export-acp-recovery-view.py`
- `tests/test_acp_records.py`
- `tests/test_acp_recovery_export.py`

This artifact does not create those files.

### Future validator responsibilities

`verify-acp-records.py` should check:

- valid record kinds;
- required fields;
- valid lifecycle status;
- no unresolved placeholders;
- repo-relative source refs;
- no local absolute paths;
- no `.gsd/exec` durable anchors;
- no secret/provider markers;
- capture mode and redaction status present;
- source-role metadata when legal sources are referenced;
- accepted/verified status rules;
- R035/R037/R038 cannot be marked validated by fixture proof.

### Future recovery exporter responsibilities

`export-acp-recovery-view.py` should produce a derived report or JSON showing:

- current architectural position;
- prompt-to-proposal-to-candidate chain;
- proof gates and status;
- health findings and blocked actions;
- allowed next actions;
- source record paths.

The exporter must be read-only relative to source records.

### Future verification commands

Expected future proof commands:

```bash
uv run python scripts/verify-acp-records.py
uv run python scripts/export-acp-recovery-view.py --check
uv run pytest tests/test_acp_records.py tests/test_acp_recovery_export.py
uv run python scripts/verify-architecture-graph.py
```

Exact commands may change during implementation, but equivalent proof must exist before any ACP implementation milestone is marked complete.

## First proof acceptance criteria

- Minimal ACP fixture chain exists and validates.
- Derived recovery view is generated from fixture records.
- Recovery view is read-only and source-linked.
- Tests pass.
- Existing architecture verifier remains green.
- No `R035`, `R037`, or `R038` validation claim is made.
- No parser/legal/FalkorDB/retrieval/product readiness claim is made.
- No raw secrets/provider payloads/unnecessary raw legal text are persisted.

## Recommended next milestone after M035

If the user chooses to proceed after M035, create a new GSD milestone for:

```text
ACP Minimal Fixture Chain Proof
```

The milestone should contain three thin slices:

1. **Schema and fixture records**
   - Define minimal schema and safe fixture records.
   - Verify shape and safety.
2. **Validator and recovery export**
   - Implement validator and derived recovery view.
   - Verify read-only source-linked output.
3. **GSD and architecture-verifier integration assessment**
   - Decide whether ACP records should feed current architecture registry or remain separate initially.
   - Keep current verifier green.

Do not start this implementation milestone until M035 is completed and the user explicitly approves moving from research/planning to implementation.

## Verification approach for S05

This S05 artifact should be checked by:

- focused marker scan for law-nexus profile concepts;
- forbidden marker scan for secrets and overclaims;
- canonical architecture verifier:

```bash
uv run python scripts/verify-architecture-graph.py
```

## Verification notes

This profile and plan are research/planning evidence only. They do not validate law-nexus parser completeness, legal correctness, FalkorDB ingestion, graph-vector retrieval quality, R035, R037, or R038. They do not make PHRs, ADRs, GSD summaries, external AI dialogue, generated visualizations, or verifier reports authoritative proof.
