# ACP source truth and proof gates

## Authority hierarchy

ACP authority is explicit and proof-bound:

1. Authoritative source evidence: PRD, GSD, ADR, source code, tests, runtime observations, and real-document evidence.
2. Accepted decisions and requirements with tracked proof anchors.
3. ACP source records with lifecycle state, evidence anchor, and proof gate.
4. Derived JSONL/RDF/OWL/SHACL/SPARQL/JSON-LD/recovery/dashboard views.
5. Agent prose, skill text, summaries, and UI views as guidance or diagnostics only.

## Authority rule

An ACP statement becomes authoritative only when these pieces are present:

```text
source category + lifecycle state + evidence anchor + proof gate or accepted decision
```

Shape alone is not authority. A Turtle triple, JSON-LD object, SPARQL result, dashboard node, or GSD summary can imitate authority unless tied back to accepted source/proof machinery.

## Source record checklist

For every ACP source record or validation claim, check:

| Field | Required meaning |
|---|---|
| Source category | PRD/GSD/ADR/source/test/runtime/real-document/decision. |
| Lifecycle state | active, validated, deferred, blocked, rejected, or superseded. |
| Evidence anchor | Tracked repository-relative path. |
| Proof gate | Executable/checkable proof or accepted decision. |
| Authority class | source, derived, diagnostic, runtime-smoke, profile-proof, or blocked. |
| Profile ownership | ACP core or a named profile such as law-nexus. |

If any field is missing, the safe status is proposed, diagnostic, derived, blocked, or needs proof.

## Durable evidence anchor policy

Accepted durable anchors are tracked repository-relative paths such as:

```text
prd/architecture/acp/M049-S04-BINDING-VERIFIER-CHECKS.md
scripts/verify-m049-binding.py
tests/test_verify_m049_binding.py
```

Rejected durable anchors:

```text
absolute local paths
.gsd/exec outputs
ignored local artifacts
.artifacts/browser bundles
raw provider/session payloads
raw vectors
secrets
unnecessary raw legal text
```

Rejected anchors may appear only as policy examples, verifier patterns, or unsafe test fixtures.

## Projection boundary

RDF, OWL, SHACL, SPARQL, JSON-LD, JSONL, dashboards, and recovery views are useful for interoperability, audit, recovery, queryability, and diagnostics. They remain derived unless a specific record is tied to ACP source category, lifecycle state, accepted anchor, and proof gate.

Safe wording:

```text
This projection represents the ACP record shape and can support diagnostics.
```

Unsafe wording:

```text
This projection validates the requirement by itself.
```

## Proof gate boundary

A proof gate is an executable or checkable process. Examples:

```text
uv run python scripts/verify-m049-binding.py
uv run pytest tests/test_verify_m049_binding.py
git diff --check
gitnexus_detect_changes(repo="law-nexus", scope="all")
```

A placeholder proof gate is not proof. A diagnostic pass is not requirement validation unless the requirement's accepted proof path says that diagnostic class is sufficient.

## law-nexus profile boundary

Reusable ACP core may define:

```text
SourceRecord
Requirement
Decision
EvidenceAnchor
ProofGate
HealthFinding
Projection
LifecycleState
AuthorityClass
ValidationClaim
ProfileConstraint
RuntimeAdapter
```

law-nexus profile owns substantive proof for:

```text
Russian legal evidence
Garant ODT parser behavior
FalkorDB runtime and ingest behavior
retrieval quality
citation safety
generated-Cypher safety
R035/R037/R038 validation
```

Do not validate R035, R037, or R038 from ACP-kit, git-lex, RDF, SPARQL, JSON-LD, verifier shape, dashboard, or projection evidence alone.

## Main-state boundary

ACP work must not introduce these into the main checkout unless a future explicit adoption decision and isolated proof approve them:

```text
.lex
Squad
Raw
.artifacts
```

For current ACP/git-lex work, final verification should include:

```bash
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
```

## Safe synthesis pattern

When synthesizing ACP work, use this structure:

```text
What is now supported:
- <bounded claim>
- evidence: <tracked paths and commands>

What remains blocked or future:
- <blocked claim>
- missing proof: <proof gate or evidence class>

What must not be inferred:
- projection/source-truth promotion
- profile requirement validation
- production/runtime adoption
```
