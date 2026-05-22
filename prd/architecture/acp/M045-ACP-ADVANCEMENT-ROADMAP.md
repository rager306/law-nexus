# ACP Advancement Roadmap

## Status

Accepted planning roadmap for ACP work after M044 and during M045. This roadmap is a GSD-tracked planning artifact, not implementation proof and not architecture source truth.

## Current baseline

ACP currently has the following established baseline:

- M044 adopted bounded default ACP governance inclusion in the canonical architecture extractor.
- The default architecture registry has 63 items and 98 edges.
- The default architecture verifier is green on the current baseline.
- M045 S01 defined a custom-only RDF/SHACL/SPARQL projection contract.
- M045 S02 T01 checked the Turtle/SHACL/SPARQL output design before exporter implementation.

ACP remains an architecture governance and recovery/control-plane layer. It is not legal truth, not product runtime evidence, not accepted architecture doctrine by itself, and not a source-of-truth replacement.

## Guardrails for every phase

Every ACP phase below must preserve these rules:

- PRD/GSD/ADR/source/runtime evidence remains authoritative.
- Generated JSONL, graph reports, RDF, SHACL, SPARQL, dashboards, and recovery views remain derived and non-authoritative.
- Do not hand-edit `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl` to make a claim appear true.
- Do not initialize `git lex` in the main repository without a separate isolated proof.
- Do not use RDF, SHACL, SPARQL, or dashboard output to validate requirements.
- Do not treat `decision_candidate` records as accepted decisions without a later explicit decision workflow.
- Do not treat proof-gate records as proof-gate satisfaction.
- Do not emit secrets, raw provider payloads, raw vectors, raw legal text, local absolute paths, or `.gsd/exec` proof anchors.

This roadmap does not validate R035.

This roadmap does not validate R037.

This roadmap does not validate R038.

This roadmap does not prove parser completeness, legal correctness, graph-vector retrieval quality, FalkorDB ingestion/runtime loading, production readiness, independent external review, ontology correctness, RDF completeness, SHACL completeness, SPARQL engine correctness, or product Legal KnowQL behavior.

## Phase 1: Finish M045 custom RDF projection proof

### Goal

Prove a deterministic custom-only RDF/SHACL/SPARQL projection from the default architecture registry.

### Work

1. Implement `scripts/export-architecture-rdf-projection.py`.
2. Generate:
   - `prd/architecture/acp/derived/architecture-projection.ttl`
   - `prd/architecture/acp/derived/architecture-projection.shacl.ttl`
   - `prd/architecture/acp/derived/architecture-projection.sparql`
   - `prd/architecture/acp/derived/architecture-projection-rdf-report.json`
3. Add `tests/test_architecture_rdf_projection.py`.
4. Verify write/check determinism, stale-output detection, canonical-path refusal, source-anchor safety, ACP non-claims, decision-candidate authority requirement, and report counts.
5. Close M045 with a decision on whether the projection remains custom-only, becomes a default generated artifact, or is deferred.

### Verification

Run at minimum:

```bash
uv run python scripts/export-architecture-rdf-projection.py
uv run python scripts/export-architecture-rdf-projection.py --check
uv run pytest tests/test_architecture_rdf_projection.py
uv run python scripts/extract-prd-architecture-items.py --check
uv run python scripts/build-architecture-graph.py --check
uv run python scripts/verify-architecture-graph.py
uv run ruff check scripts/export-architecture-rdf-projection.py tests/test_architecture_rdf_projection.py
```

### Preferred M045 decision

Keep RDF/SHACL/SPARQL projection custom-only at first, unless S02 produces strong evidence that a default generated projection path is needed immediately.

## Phase 2: Harden the RDF projection surface

### Goal

Turn the custom projection into a stable diagnostic/export surface with clearer failure modes.

### Work

- Add richer report diagnostics.
- Add stable diagnostic classes:
  - `duplicate-id`
  - `missing-endpoint`
  - `unsafe-source-anchor`
  - `missing-non-claim`
  - `authority-required`
  - `forbidden-output-path`
  - `forbidden-marker`
  - `stale-output`
- Consider `--diff` mode for previewing generated output changes.
- Add vocabulary notes for `lgarch:` and `acp:` predicates.

### Outputs

Possible artifacts:

- `prd/architecture/acp/M046-RDF-VOCABULARY-NOTES.md`
- updated `scripts/export-architecture-rdf-projection.py`
- updated projection tests

### Verification

Projection `--check`, focused tests, ruff, LSP diagnostics, default architecture verifier, and GitNexus change detection.

## Phase 3: Optional RDF engine spike

### Goal

Decide whether dependency-backed RDF/SPARQL/SHACL execution adds enough value to justify dependency and maintenance cost.

### Options

1. Stay stdlib-only.
2. Add `rdflib` for Turtle parsing and SPARQL smoke queries.
3. Add `pyshacl` only if real SHACL validation is needed.

### Recommended order

1. Finish stdlib custom projection proof.
2. If useful, run a separate `rdflib` spike.
3. Add `pyshacl` only behind a separate decision and proof gate.

### Non-claims

Even if RDF dependencies parse/execute the projection, that does not prove ontology correctness, legal correctness, product runtime behavior, FalkorDB ingestion, retrieval quality, or production readiness.

## Phase 4: Isolated git-lex alignment spike

### Goal

Assess whether ACP identity, RDF projection, and provenance chain can align with git-lex concepts without changing the main repository runtime.

### Hard boundary

Do not run `git lex init` in the main repository.

### Safe approach

Use an isolated temporary workspace or dedicated spike worktree. Treat vendor/git-lex material as context and prior art, not authority over law-nexus architecture.

### Questions

- Can ACP record identity map to git-lex style identity without losing repository-local stability?
- Can ACP Markdown records map to RDF resources while preserving source-truth boundaries?
- Can PHR/ADR-inspired provenance be represented without blindly storing raw prompts?
- Can generated RDF be imported into a git-lex-like flow without becoming source truth?

### Output

A future spike assessment artifact, for example:

- `prd/architecture/acp/M0XX-GIT-LEX-SPIKE-ASSESSMENT.md`

## Phase 5: ACP recovery and dashboard views

### Goal

Make ACP useful for future agents as a recovery and next-action surface.

### Derived views

Possible generated outputs:

- `prd/architecture/acp/derived/acp-recovery-dashboard.json`
- `prd/architecture/acp/derived/acp-next-actions.md`
- `prd/architecture/acp/derived/acp-blockers.md`

### Questions the view should answer

- What is the current architecture governance state?
- Which decisions are accepted, candidates, deferred, rejected, or blocked?
- Which proof gates are open?
- Which health findings block next actions?
- Which actions are allowed next?
- Which actions are explicitly blocked?
- Which claims are unsafe to assert?
- What verification must run before promotion?

### Boundary

Dashboard and recovery views are derived decision-support surfaces, not authority and not proof.

## Phase 6: ACP decision lifecycle workflow

### Goal

Move from static ACP records to a safe lifecycle workflow:

```text
prompt_record -> proposal -> decision_candidate -> accepted/deferred/rejected decision -> proof gate -> verification evidence
```

### Work

- Define a command or workflow for creating ACP records.
- Define lifecycle transition checks.
- Require explicit human authority for accepted decisions.
- Require proof-gate linkage before promotion.
- Preserve supersession, rejection, and defer rationale.

### Possible command shape

```bash
uv run python scripts/acp-record-decision.py \
  --candidate ACP-DC-0001 \
  --status accepted \
  --decision-id DEC-...
```

This command shape is illustrative only. It must not be implemented or treated as accepted without a separate design and proof milestone.

## Phase 7: ACP core/profile split

### Goal

Make ACP reusable beyond law-nexus while preserving strict law-nexus profile rules.

### Core concepts

ACP core should contain reusable concepts:

- prompt record
- proposal
- decision candidate
- proof gate
- health finding
- allowed and blocked actions
- provenance chain
- recovery view
- projection and validation mechanics

### Law-nexus profile concepts

The law-nexus profile should contain project-specific constraints:

- Russian legal evidence boundaries
- FalkorDB capability proof boundaries
- parser completeness boundaries
- R035/R037/R038 non-claims
- LegalGraph Nexus proof gates
- no managed embedding API fallback for embedding evaluation

### Success condition

Another repository should be able to adopt ACP core without inheriting law-nexus legal/FalkorDB/parser constraints, while law-nexus retains its strict profile.

## Phase 8: ACP CI and quality gates

### Goal

Make ACP drift and unsafe architecture claims fail early.

### Candidate gate commands

```bash
uv run python scripts/verify-acp-records.py
uv run python scripts/export-acp-recovery-view.py --check
uv run python scripts/extract-prd-architecture-items.py --check
uv run python scripts/build-architecture-graph.py --check
uv run python scripts/verify-architecture-graph.py
uv run python scripts/export-architecture-rdf-projection.py --check
```

### Gate categories

- freshness drift
- schema validity
- source-anchor safety
- duplicate IDs
- missing proof gates
- unsafe promotion
- overclaim detection
- RDF projection currentness

### Success condition

A future PR or local quality gate cannot pass with stale architecture projections or unsafe architecture claims.

## Immediate recommended sequence

1. Commit the M045 RDF projection design check.
2. Record this ACP advancement roadmap through GSD.
3. Test a tiny GSD-auto-compatible task path before relying on auto-mode for the larger exporter work.
4. Implement M045 S02 exporter with deterministic stdlib generation.
5. Add focused tests and verification.
6. Close M045 with a final projection adoption decision.

## Tiny auto-mode compatibility check

Before using GSD auto for larger ACP implementation, use a very small task that only touches a harmless planning/proof artifact and has a simple verification command.

Suggested tiny task:

- create or update a small marker artifact under `prd/architecture/acp/`;
- verify it with a marker scan;
- ensure GSD task completion does not try to stage `.gsd/...` symlink paths;
- confirm `git status` remains understandable and no source code is accidentally changed.

This checks the practical GSD-auto path without risking exporter implementation, canonical registry drift, or generated artifact churn.
