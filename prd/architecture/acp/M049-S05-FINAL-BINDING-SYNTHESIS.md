# M049 S05 Final Binding Synthesis

## Status

Created for `M049 / S05 / T04`.

This artifact closes the M049 binding work at the synthesis level. It records what law-nexus can now claim through ACP, how the corrected git-lex to ACP roadmap changes the next integration step, and which claims remain blocked or profile-owned.

## Final synthesis

M049 binds law-nexus architecture into ACP through ACP-native source/proof machinery, not through git-lex authority.

Supported claim:

```text
law-nexus architecture can now be represented through ACP-native source records, lifecycle states, evidence anchors, proof gates, profile boundaries, and focused verifier checks without promoting git-lex or derived projections to source truth.
```

Supported next integration claim:

```text
The corrected next git-lex to ACP integration step is ACP-kit v0: a deterministic git-lex-compatible semantic kit over git-lex-kit-base that packages reusable ACP core vocabulary while preserving ACP-native authority.
```

Current git-lex status remains:

```text
L1 shadow diagnostic/projection support only.
```

## What M049 established

| Slice | Established result | Boundary preserved |
|---|---|---|
| S01 Binding input audit | M048-M055 inputs and requirements were classified into usable evidence versus blocked/non-authoritative evidence. | Unsafe anchors and R035/R037/R038 overclaim are rejected. |
| S02 Profile adapter boundary | Reusable ACP core is separated from law-nexus profile proof. | Russian legal evidence, Garant parser, FalkorDB, retrieval, citation safety, generated-Cypher safety, and R035/R037/R038 stay profile-owned. |
| S03 Registry source mapping | law-nexus architecture claims were mapped to ACP source records, lifecycle states, evidence anchors, and proof gates. | Generated registry JSONL/report freshness was not claimed. |
| S04 Binding verifier checks | `scripts/verify-m049-binding.py` and tests catch authority inversion, unsafe anchors, missing proof gates, forbidden git-lex promotion, R035/R037/R038 overclaim, profile/core drift, registry-currency overclaim, placeholder proof misuse, and main-state residue. | Focused verifier does not replace the canonical architecture verifier or validate profile claims. |
| S05 Final synthesis | Corrected roadmap and skill routing were added: ACP-kit becomes the semantic integration step before L2 diagnostics; git-lex and ACP guidance are separated into dedicated skills. | ACP-kit remains derived/non-authoritative until proof-gated; no main `.lex` or source-truth migration is approved. |

## Corrected git-lex to ACP roadmap

M049/S05 records this sequence:

```text
K0 M051/S08 static ACP ontology prototype
K1 ACP-kit v0 over git-lex-kit-base
K2 isolated ACP-kit runtime proof
K3 M049 binding projection through ACP-kit records
K4 L2 operational diagnostic integration
K5 isolated main `.lex` rehearsal
K6 ACP source-truth migration design
K7 production/provenance adoption
```

Current approved status:

| Stage | Current status |
|---|---|
| K0 | Done as M051/S08 static prototype. |
| K1 | Recommended next implementation milestone. |
| K2 | Future proof after K1. |
| K3 | Future projection proof after K1/K2 or as static-first fixture. |
| K4 | Future L2 operational diagnostic track after semantic contract and workflow gates. |
| K5 | Blocked until explicit human decision and isolated rehearsal. |
| K6 | Blocked until authority migration design and accepted decision. |
| K7 | Blocked until production/provenance/security/rollback gates pass. |

## Skill routing outcome

M049/S05 updates skill routing to prevent knowledge sprawl:

| Skill | Scope |
|---|---|
| `.agents/skills/git-lex` | git-lex runtime, semantic-kit evidence, RDF/SPARQL/JSON-LD claim safety, `.lex` state, source-built binary proof, adapter/provenance/runtime gates. |
| `.agents/skills/acp` | ACP-native source truth, lifecycle states, evidence anchors, proof gates, validation claims, health findings, ACP-kit roadmap/design, law-nexus profile boundaries, verifier-safe synthesis. |

This split keeps ACP-kit knowledge in ACP guidance while preserving git-lex runtime/adoption guardrails in the git-lex skill.

## What can now be claimed

Safe claims:

```text
M049 establishes an ACP binding boundary for law-nexus architecture.
```

```text
M049 provides a focused binding verifier and tests for key overclaim risks in M049 binding artifacts.
```

```text
M049/S05 identifies ACP-kit v0 as the next semantic integration step before L2 operational diagnostics.
```

```text
The project now has separate git-lex and ACP skills for future agents: one for git-lex runtime/adoption boundaries and one for ACP-native/ACP-kit proof semantics.
```

## What remains blocked or future

Blocked or future claims:

```text
main repository .lex approval
ACP source-truth migration
production git-lex runtime readiness
release/plugin-bundled binary trust
JSON-LD git-lex runtime support
broad SPARQL-star/RDF-star parity
raw/session/provider payload proof anchors
R035/R037/R038 validation from ACP-kit/git-lex/projection evidence
Russian legal evidence correctness
Garant ODT parser completeness
FalkorDB runtime behavior
retrieval quality or citation safety proof
generated-Cypher safety proof
canonical generated registry JSONL/report freshness
```

## Recommended next milestone

Create a dedicated ACP-kit implementation milestone after M049 closes:

```text
ACP-kit v0 over git-lex-kit-base
```

Recommended first slices:

1. Inspect exact base/squad/soul/autoknow kit mechanics and record ACP-kit packaging rules.
2. Convert M051/S08 prototype ontology into reusable `acp.ttl` without prototype-specific authority claims.
3. Create deterministic ACP-kit v0 scaffold with `kit.yml`, `ontology/acp/acp.ttl`, `content/ACP/*`, and guidance.
4. Add static verifier for required classes/folders, authority markers, unsafe anchors, and profile/core separation.
5. Run isolated runtime proof only after K1 passes, with no main-state residue and bounded diagnostics.

## Verification evidence for S05

Expected final verification:

```bash
uv run python scripts/verify-m049-binding.py
```

```bash
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
```

```bash
git diff --check
```

```text
gitnexus_detect_changes(repo="law-nexus", scope="all")
```

Focused scans should classify unsafe wording examples, blocked-claim lists, rejected-anchor policy, and verifier source/test patterns as allowed only when they are clearly negative examples, blocked lists, or implementation fixtures.
