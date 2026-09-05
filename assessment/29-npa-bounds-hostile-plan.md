# NPA boundedness and hostile-contract measurement plan

**Date:** 2026-09-04  
**Status:** `[proposed]`; no measured limits or runtime readiness claim  
**Scope:** D383-D388 M2; full Consultant corpus measurement without changing N2

## 1. Verdict

No numeric runtime bound is currently evidence-backed. All declared member,
expansion, context, alias, and fan-out limits correctly remain
`deferred-undefined`. Pullenti thresholds are implementation observations, not
transferable evidence.

Some bounds are semantic/grammar invariants and can be fixed without corpus
statistics. Resource ceilings require a reproducible streaming measurement of
the full Consultant export plus hostile tests.

## 2. Grammar-hard invariants

These are categorical constraints rather than measured maxima:

| Invariant | Bound |
|---|---|
| Covering span | one fragment-local TextAnchor; never cross-block |
| Structural decimal range | exactly two endpoint candidates under `endpoint_pair` |
| Range semantics | no arithmetic enumeration of intermediate decimal designations |
| Request vocabulary | closed to the contract's named ContextRequest kinds |
| Context closure | one deterministic worklist-to-fixpoint run per document version |
| Source mutation | zero mutation of covering tokens, mentions, or base index |
| Prompt/model dependency | zero product dependencies |
| Provenance | every derived field retains every authorized hop |

These do not determine safe memory/time/cardinality ceilings.

## 3. Bounds requiring measurement

| Bound | Required evidence |
|---|---|
| `max_members` | distribution of members in coordinating act/structural frames |
| `max_expanded_candidates` | product of explicit multi-value roles before endpoint policy |
| contour-A candidate cardinality | candidates per fragment before/after arbitration |
| `adjacent_block_radius` | distance from elliptical tail to proven opening frame |
| `max_series_hops` | length of proven cross-block series chains |
| `max_alias_candidates` | scoped declarations matching one explicit alias key |
| `max_context_claims_per_field` | applicable evidence claims before reduction |
| worklist requests/fan-out | requests per frame/document and successor requests per kind |
| derivation depth | longest authorized context/provenance path |
| malformed-input budget | parser/index behavior on corrupt or incomplete XML/WordML |

No values may be selected before the measurement artifact exists.

## 4. Corpus source and isolation

Corpus-wide measurement must scan:

```text
consru_export/consru_export/exports/
```

Expected inventory is approximately 43,785 XML files / 3.7 GB, but the scan
must record its own observed file and byte counts. `law-source/consultant/` is
only a fragment and cannot support bounds.

This measurement does not alter or expand:

- the 180-fragment NPA sample;
- N2 annotation/gold;
- R035 or R070 status;
- product source or fixtures.

## 5. Safe streaming scan

The scanner is a temporary/read-only analysis tool until separately planned.
It should:

1. enumerate files deterministically by repository-relative path;
2. stream each XML document without loading the corpus or all documents into
   memory;
3. reuse or faithfully model Consultant WordML block boundaries;
4. derive ordered block metadata and candidate shape metrics only;
5. keep bounded histograms/quantile sketches and top-K anchored outliers;
6. record malformed/read failures explicitly;
7. avoid durable raw legal text; store hashes, paths, block IDs, offsets, and
   compact shape descriptions;
8. checkpoint progress so interruption cannot fabricate completeness;
9. include scanner source hash/profile, corpus root, start/end time, observed
   file/byte counts, and failure counts.

The scan must not silently treat XML tags as whitespace and then claim semantic
block distances: block measurements require decoder-compatible boundaries.

## 6. Metrics

Per document and construction kind:

- number of decoded blocks;
- local frame member count;
- explicit role/value count;
- direct/frame candidate count by pattern ID;
- same-span, containment, overlap, and conflict counts;
- expansion cardinality before and after endpoint policy;
- continuation distance in block edges;
- continuation chain length;
- alias candidates within structural scope;
- context claims per field/source;
- ContextRequest count, fan-out, memo hit, cycle, partial/conflict/limit status;
- maximum derivation depth;
- parser/index malformed or unavailable outcomes.

Report count, maximum, bounded histogram, and selected quantiles. Quantiles do
not replace review of every maximum/outlier anchor.

## 7. Durable evidence format

A tracked evidence artifact should contain:

```text
schema_version
lifecycle = [bounded]
source_revision
scanner_profile + scanner_source_hash
corpus_root (repository-relative)
observed_file_count / observed_bytes
success / malformed / unreadable counts
construction definitions
per-metric counts, histogram, quantiles, maximum
anchored top-K outliers without raw legal text
reproducibility command
limitations
candidate bound decision references
```

Raw logs and temporary text remain outside durable proof. Every selected bound
must cite the metric/outlier evidence and its refusal behavior.

## 8. Hostile contracts

### Coordinating lists

- comma list interrupted by heading or paragraph boundary;
- mixed act types inside one punctuation chain;
- date/number pairs that are case or address metadata;
- empty member, repeated comma, unclosed parenthesis;
- a member count beyond the selected ceiling.

### Structural ranges

- descending endpoints;
- non-comparable designation paths;
- quoted digit range next to a different `часть` reference;
- hyphen used linguistically rather than structurally;
- values producing Cartesian expansion beyond the ceiling.

### Cross-block continuation

- unrelated next paragraph starts with `от DATE N`;
- heading terminates an open series;
- two plausible opening frames in different containers;
- corrupt block order;
- a continuation cycle.

### Alias/context recursion

- alias chain cycle;
- alias outside declared scope;
- many same-word aliases in sibling sections;
- later explicit declaration requiring keyed forward lookup;
- context path exceeding depth/fan-out budget.

### Requisites

- head/filename/catalog conflicts;
- wrong catalog association;
- regional GEO/ORG collapse;
- complete identity requisites but absent temporal-edition provenance.

## 9. Bound selection and refusal

A bound decision must consider:

- observed maximum and every anchored outlier;
- high quantiles and tail shape;
- adversarial resource amplification;
- operational memory/time target;
- whether the construction is genuinely grammatical or noise.

A runtime limit is a safety ceiling, not a claim that larger legal structures
do not exist. Exceeding it must return an explicit `limit`/partial result with
source anchor and requested cardinality. Silent truncation, first-N selection,
or conversion to a unique answer is forbidden.

## 10. Acceptance sequence

1. Freeze metric definitions and scanner profile.
2. Validate scanner block semantics on existing fixtures without changing
   gold/N2.
3. Run the complete streaming corpus scan.
4. Review all maxima/outlier anchors and malformed failures.
5. Add hostile synthetic contracts beyond observed cases.
6. Choose bounds with explicit rationale and refusal semantics.
7. Pin YAML bounds and transition tests.
8. Re-run full measurement and prove zero silent truncation.
9. Only then remove the D387 runtime stop for the bounded slice.

Until steps 1-8 pass, all numeric values remain `deferred-undefined`.
