# Representative parser golden-corpus acceptance protocol

**Status:** `[bounded]` process/evidence contract  
**Authority:** ADR-0013, ADR-0015 and `prd/ARCHITECTURE.md` set the ceilings  
**Scope:** Rust `ln-decode` structural parser evidence only  
**Non-authority:** this protocol does not decide legal meaning, accept product behavior, satisfy a requirement or promote an ADR lifecycle  

## 1. Purpose

This protocol defines how law-nexus may assemble, execute and report a
representative parser golden corpus without smoothing synthetic, self-derived or
single-fixture evidence into parser completeness.

It answers one bounded question:

> Did the declared provider-isolated corpus produce the expected structural
> decode, span, candidate, abstention and diagnostic outcomes with deterministic
> evidence and explicit non-claims?

It does not answer whether the parsed text is legally applicable, whether a
reference resolves authoritatively, whether a deontic phrase is a legal norm, or
whether retrieval can produce a citation-safe answer.

## 2. Current evidence ceiling

Current Rust evidence is `[bounded]`:

- one tracked real Consultant WordML document is bound to
  `crates/ln-decode/tests/consultant_real_tracer.rs`;
- one tracked real Garant ODT document is bound to
  `crates/ln-decode/tests/garant_real_tracer.rs`;
- both provider families have independent positive and hostile tests;
- shared hierarchy and lexical layers have deterministic synthetic contracts;
- `golden_real_enrichment.rs` derives annotations from the same parser output
  under test and therefore proves self-consistency only.

The tracked source corpus contains additional documents, but corpus existence is
not parser proof. No current result establishes representative multi-fixture
quality, Consultant/Garant parity, legal resolution, citation mapping or parser
completeness.

## 3. Provider strata

Provider strata MUST remain independent.

| Stratum | Family format | Source coordinate stream | Active adapter boundary |
|---------|---------------|--------------------------|-------------------------|
| Consultant WordML | `family:consultant-wordml` | `artifact:whole` | `ConsultantWordMlBlockDecoder` |
| Garant ODT | `family:garant-odt` | `package-member:content.xml` | `GarantOdtBlockDecoder` after bounded package extraction |

A fixture, oracle, style map or provider-specific failure expectation from one
stratum MUST NOT satisfy the other stratum. A foreign-family request MUST fail
as `UnsupportedFormat` before provider parsing.

Inventory `document_type` labels are title/path metadata only. They MAY guide a
human corpus-selection review but MUST NOT be treated as parser assertions or as
proof that a corpus is representative.

## 4. Corpus manifest contract

Every acceptance run MUST use a tracked manifest. Every entry MUST contain:

| Field | Contract |
|-------|----------|
| `case_id` | stable unique identifier |
| `provider_stratum` | `consultant-wordml` or `garant-odt` |
| `source_path` | tracked repository-relative path under `law-source/` |
| `source_sha256` | hash of the exact source bytes used by the run |
| `byte_count` | exact source byte count |
| `runtime_fingerprint` | decoder/runtime fingerprint when the adapter exposes one |
| `role` | `positive`, `hostile`, `structural-golden` or `smoke` |
| `case_classes` | closed set of expected structural outcomes |
| `annotation_provenance` | `human-reviewed`, `parser-self-derived` or `synthetic` |
| `lifecycle_ceiling` | `[smoke]` or `[bounded]` unless a separate human decision permits more |
| `non_claims` | non-empty blocked-claim list |

Missing paths, hash drift, duplicate case IDs, unknown provider strata, absent
annotation provenance, empty non-claims or an unsupported lifecycle value MUST
fail closed before scoring.

Untracked, ignored, archive-only or absolute paths MUST NOT be durable corpus
anchors. Raw legal text MUST NOT be copied into the manifest or unbounded
failure diagnostics.

## 5. Current real-fixture regression anchors

These anchors describe current one-document regression tests. They do not make
the corpus representative.

| Stratum | Tracked fixture | Runtime fingerprint | Blocks | Hierarchy nodes | Evidence class |
|---------|-----------------|---------------------|--------|-----------------|----------------|
| Consultant WordML | `law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml` | `fnv1a64:d7697a0ea8cc3970` | 167 | 119 | tracked real tracer, one fixture `[bounded]` |
| Garant ODT | `law-source/garant/44-fz.odt` | `fnv1a64:d4143a172688f8c3` | 5124 | 140 | tracked real tracer, one fixture `[bounded]` |

The Consultant `119` count is the current `EXPECTED_HIERARCHY_COUNT` in
`crates/ln-decode/tests/consultant_real_tracer.rs`. It includes numbered
sub-article candidates (`1.`, `1)`, `а)`) from the bounded hierarchy layer.
Those candidates are structural decode markers only; they do not prove legal
hierarchy correctness, article/part/item identity, or citation completeness.

A new fixture MUST be registered and reviewed independently for its own stratum.
The counts above MUST NOT be generalized into a quality threshold, provider
parity metric or legal-document-type expectation.

## 6. Structural case classes

The protocol recognizes two related but distinct surfaces.

### 6.1 Record-level case classes

The thin record/staging contract may use:

- `evidence-present`;
- `no-answer`;
- `candidate-only`;
- `unresolved-reference`;
- `non-authoritative`.

These states describe bounded evidence handling only.

### 6.2 Decode-layer golden classes

Rust structural golden annotations may cover:

- hierarchy marker spans;
- reference mention spans;
- temporal phrase spans and candidate kinds;
- deontic lexeme spans and candidate kinds;
- unknown-form discovery kinds.

They MUST NOT contain authoritative target resolution, five-clock facts,
`NormStatement`, applicability outcomes, legal hierarchy decisions or promoted
publication state.

## 7. Positive and hostile gates

Every provider stratum claimed by a run MUST have both positive and hostile
coverage.

### 7.1 Positive requirements

A positive fixture MUST prove:

- provider-family dispatch succeeds only for its declared family;
- repeated decode yields identical `ParsedBlock` values and deterministic
  fingerprints/counts;
- emitted blocks have non-empty decoded text where the domain contract requires
  it;
- artifact and decoded-text spans satisfy their own coordinate contracts;
- expected structural annotations refer to existing blocks and valid UTF-8
  `TextSpan` ranges;
- diagnostics and durable results preserve hashes/IDs rather than unbounded raw
  legal text.

### 7.2 Hostile requirements

The suite MUST cover the applicable failure classes:

- wrong provider family;
- malformed or truncated provider input;
- invalid ZIP, missing/duplicate/unsafe `content.xml` for ODT;
- unsupported namespace/topology/entity/doctype structures;
- invalid, empty, reversed or out-of-bounds spans;
- partial-output attempts after malformed input;
- canary or raw-source leakage in diagnostics;
- candidate promotion to an authoritative relation;
- missing manifest entry or source hash drift.

Hostile failure MUST be typed and atomic: no partially admitted block vector,
invented structure or upgraded candidate may survive the failure.

## 8. Span and provenance contract

`SourceSpan` and `TextSpan` are different coordinate systems.

- `SourceSpan` is a non-empty half-open byte range in the declared provider
  stream.
- `TextSpan` is a non-empty half-open UTF-8 byte range in decoded block text.
- Consultant WordML uses the whole artifact stream.
- Garant ODT uses the bounded `content.xml` package-member stream.
- An artifact span MUST NOT be reused as a decoded marker span.
- This protocol does not define a source-to-decoded coordinate translation and
  does not turn either span into citation authority.

Every durable annotation MUST identify its block and coordinate type. Span
validation failure is a hard contract failure.

## 9. Annotation independence

`annotation_provenance` is mandatory.

### `parser-self-derived`

Annotations produced by running the same extractors being evaluated are a
self-oracle. They may demonstrate deterministic wiring and self-consistency only.
They MUST remain `[smoke]` or narrowly `[bounded]` and MUST NOT be described as
independent golden quality.

### `synthetic`

Synthetic annotations may prove port behavior, family isolation, span
validation and hostile rejection. They MUST NOT support representative-corpus
or real-document quality claims by themselves.

### `human-reviewed`

Any claim stronger than self-consistency requires independently authored and
reviewed structural annotations. Disputed spans, provider edge cases and corpus
representativeness remain human-owned. Human review of structure does not create
legal interpretation or citation authority.

## 10. Determinism and failure visibility

An acceptance result MUST be reproducible from the tracked manifest and source
revision. It MUST record:

- source revision and manifest digest;
- per-fixture source hash, byte count and runtime fingerprint;
- provider stratum and annotation provenance;
- positive/hostile case results;
- structural counts and metrics where applicable;
- typed failures and compact repository-relative evidence;
- lifecycle ceiling and non-claims.

Timing fields, absolute paths, secrets, raw embeddings and unbounded legal text
MUST NOT affect canonical result bytes. Repeated runs over identical inputs MUST
produce equal semantic results.

A setup/read/schema/hash error is `error`; a readable fixture that violates an
expected structural outcome is `fail`; a satisfied structural contract is
`pass`. No error may be converted into an empty-corpus PASS.

## 11. Evidence ladder

| Gate | Minimum evidence | Maximum claim |
|------|------------------|---------------|
| G0 synthetic/hostile | provider-isolated unit and port contracts; typed hostile rejection | `[bounded]` adapter/domain behavior only |
| G1 real tracer | at least one tracked real fixture for each claimed provider; deterministic decode, span and hostile proof | one-fixture-per-provider `[bounded]` behavior |
| G2 structural golden | multiple tracked fixtures per claimed provider, independently human-reviewed structural annotations, deterministic metrics and unknown-form reporting | representative structural parser evidence `[bounded]`; numeric quality acceptance still needs a human threshold decision |
| G3 lifecycle review | source-bound evidence packet, independent review and explicit human disposition under ADR-0012/0013 ceilings | any stronger parser lifecycle claim; not supplied by this protocol |

Current evidence reaches G1. `golden_real_enrichment.rs` remains a self-oracle
and does not satisfy G2.

## 12. Human-owned decisions

Agents and CI MUST NOT invent:

- which document types and fixture counts are representative enough for G2;
- precision, recall, F1 or unknown-form acceptance thresholds;
- disputed human structural annotations;
- new supported hierarchy levels beyond implemented bounded markers;
- ODT style-to-level mappings not already accepted by adapter contracts;
- cross-provider semantic parity criteria;
- legal resolution, citation authority, temporal applicability or deontic
  interpretation;
- promotion of ADR-0013 from `[bounded]` to `[validated]`.

Until those decisions exist, metrics are observability and regression signals,
not quality acceptance floors.

## 13. Required non-claims

Every corpus result MUST state that it does not prove:

- parser completeness or corpus completeness;
- Consultant/Garant semantic parity;
- legal correctness or authoritative interpretation;
- reference resolution or citation-safe answers;
- temporal applicability or NormativeState;
- retrieval quality, product ETL or graph readiness;
- production RuVector/TEI behavior;
- requirement satisfaction, release readiness or lifecycle promotion.

## 14. Current verification routes

Current bounded regression routes include:

```bash
cargo test -p ln-decode --offline
cargo test -p ln-testkit --test block_decoder_port_contracts --offline
```

The first command covers provider adapters, real tracers, structural layers,
golden mechanics and hostile cases in `ln-decode`. The second preserves shared
family-isolation contracts. The exact lightest command may be selected from the
ADR-0015 verification matrix, but compilation alone is never sufficient.

## 15. Adoption disposition

This document closes the missing protocol specification only. The project still
lacks G2 independent multi-fixture structural goldens and G3 human lifecycle
review. Existing tests and source files remain at their current `[smoke]` or
`[bounded]` ceilings.
