---
id: ADR-0031
title: Reference knowledge-layer contract over the XML→JSONL spine — digest timeline, qualified references, amend provenance, pageindex ladder
status: Proposed
lifecycle: "[proposed]"
date: 2026-10-14
supersedes: none
related: [ADR-0030, ADR-0016, ADR-0020, ADR-0009, ADR-0015]
---

# ADR-0031: Reference knowledge-layer contract over the XML→JSONL spine

## Status

`[proposed]` design decision, backed by an executed Python reference prototype
(scripts/m217_reference_jsonld.py + committed artifacts) and an independent
sandbox loop (8 cycles on the real 44-ФЗ corpus). No runtime adoption, no
semantic acceptance, no R1000 closure, no lifecycle promotion of ADR-0016..0030,
no parked milestone released. Rust port is planned (M2xx, GSD-planned) against
this contract; this ADR does not close it.

## Context

ADR-0030 defined the JSON-LD knowledge-layer family (G1–G4) as derived,
deterministic, reversible projections over the XML→JSONL spine, with legal
identity keys (URI/ELI-compatible) and source anchors. M224 landed the bounded
identity/edition layer (FRBR bridge) and the corpus amend-provenance question
remained open. D777 (2026-10-14) lifted the RDF/JSON-LD runtime ban (it was a
mis-cited prose clause). What was missing: a **measured, deterministic,
schema-validated reference contract** specifying exactly what the G-layer
contains, how it is derived from the spine, what it costs, and how drift is
detected — before any store choice (M217).

An 8-cycle Python prototype + reference module
(`scripts/m217_reference_jsonld.py`, `--check` byte-exact re-derivation) was
executed on the real 44-ФЗ corpus (118 editions, 142 articles, 16.7k digest
records, 18 593 amend markers) and independently reproduced the M224/M223
production pins (single non-monotonic residual 0036→0037 per D767; edition-81
structural break −40 articles = 476-ФЗ purge per M223 evidence).

## Decision

**D1 — Digest timeline is the persistent knowledge-identity layer.** One
record per (edition, article): `sha12` progressive text digest
(`H:` heading prefix, `"|"`-joined chunks), source anchors
(`source.sha256` of the edition file + paragraph span `p_start/p_end`),
effective day per D765 (from-date, else rev-date, else catalog document_date),
non-monotonic days clamped to the previous applied day and published as
documented residuals (D767). Digest identity is not text CTV resolution.

**D2 — Normalization is a versioned profile, not ambient behavior.** All text
transforms (nbsp→space, strip, skip-empty, join, digest scheme) are named
(`m217-norm/v1`) and carried inside the artifacts. Any normalization change is
a profile bump and an expected `--check` drift, never a silent shift.

**D3 — Amend provenance is a first-class layer.** Every edition marker
«(в ред. … от DD.MM.YYYY N X)» becomes a provenance record
(edition, article|act, date, number) with the changing act resolved against the
catalog (enacting-date identification). Measured corpus-wide: 18 593 markers,
62 amending laws, 100 % enacting-date resolution. Amendment semantics
interpretation stays out (M208 territory).

**D4 — Reference qualification is sentence-scoped with disambiguation.**
Internal references: sentence-level, external-law markers excluded unless
«настоящего/прежнему» present. External requisites (type+date+number) resolve
against the catalog (measured 609/611 exact-date on edition-50). Deep links
(requisite + foreign article number → node in the target act's pageindex)
require the temporal edition policy: target edition in force at the citing
act's effective date, never the enacting-date edition alone; own-edition
markers and amendment-fact sentences are routed to provenance, never deep
links (measured: 428 disambiguated, 0 true deep links on 44-ФЗ ed-50 — a
honest zero, mechanics proven).

**D5 — Pageindex is the structural contents ladder of the act.** Seven levels:
section → chapter/paragraph(§) → article → part → punkt (N)) → subpoint
(а)) → paragraph-block, with path-based ids (no cross-article collisions),
char offsets, and **executed** invariants: char conservation
(Σ node chars = corpus chars), single assignment, no article outside the
ladder, id uniqueness. Measured on ed-50: 8 chapters, 9 §, 141 articles,
1164 parts, 904 punkts, 108 subpoints, 669 paragraph blocks, depth 7.
Article-count variance across editions is law history (476-ФЗ purge band),
never parsing defect.

**D6 — Artifacts are schema-validated and byte-checked.** Draft-2020-12 subset
schemas (record_kind discriminator) validate every artifact before write and
inside `--check`; `--check` then byte-compares re-derivation
(exit 0 ok / 3 unreadable / 5 schema violation / 6 drift). Validation subset is
explicitly not a full JSON Schema implementation.

**D7 — G-layer text projection is on-demand.** Full-text JSON-LD for one
edition is generated on demand (`--g-layer <ed>`); the persistent layer is the
digest timeline. Measured: 2.1 MB per dense edition; ~173 MB text-inline for
the whole act; ~54 GB corpus-wide text-inline — the persistent text-inline
corpus layer is rejected by measurement.

**D8 — Rust port contract.** The Rust implementation (ln-consultant-parser,
no new crate dependencies; hand-rolled WordML paragraph scanner replicating
ElementTree semantics: entity decoding, `<w:p/>` empty paragraphs, document-
order enumeration) must byte-match the committed Python artifacts
(digests, timeline counts, amend provenance) — parity against the committed
artifacts is the acceptance oracle. The Python module remains the reference;
the Rust port is the runtime-track implementation candidate for M217.

## Evidence boundary

Committed, byte-checked artifacts back **D3**
(`m217-reference-amend-provenance.json` counts), **D6** (the `--check` exit
contract), **D7** (`g_layer_volume` inside `m217-reference-timeline.json`) and the
digest timeline itself (`m217-reference-digests.jsonl`); the Rust port reproduces
all four artifacts byte for byte.

**D4** (external requisite resolution 609/611 exact-date on edition-50; 428
disambiguated, 0 true deep links) and **D5** (pageindex contents ladder, seven
levels, edition-50 counts) were measured in the uncommitted sandbox loop and have
**no committed artifact and no module code yet** —
`scripts/m217_reference_jsonld.py` derives neither, and
`scripts/m217_reference.schema.json` validates only the four artifact families
above. Until they are executed by the reference module and committed (M225/S02),
these two decisions are sandbox-measured design substance, not repository
evidence.

## Corpus scope and input contract (measured 2026-10-16)

**The corpus carries edition ordering for exactly one act.** Across all 36 989
`editions` rows (36 458 documents) only 401 documents have more than one edition
row, and of those exactly one — the 44-ФЗ act, 118 editions — has a populated
`edition_number` and distinguishable revision/`valid_from` days. The other 400
pair two export snapshots of the same act whose filenames both say `rev-unknown`
and whose catalog dates are equal: there is **no honest ordering and no in-force
day** for them. The digest timeline is therefore a **per-act contract exercised
in the corpus by one act only**; deriving it for those 400 documents would invent
the temporal order, which this contract does not do.

**Namespace scope.** The scanner is defined over the WordML 2003 namespace
(`http://schemas.microsoft.com/office/word/2003/wordml`), which every committed
edition uses. Both implementations now refuse a document that does not declare
it (exit 3) instead of silently deriving a different paragraph set.

**Unreadable input is an exit code, not a crash.** D6 fixes exit 3 for
unreadable inputs. Both implementations now honour it for an empty corpus
(including the loose-file `exports/npa` layout, where no `edition-*.xml` exists),
a missing directory, a missing or non-sqlite catalog, a 0-byte edition, malformed
or unclosed XML, an undeclared entity, a WordML 2006 document, a file name
without a numeric edition number, and duplicate edition numbers. Before this,
the Rust port panicked (exit 101) on five of those and the Python reference
raised uncaught `ParseError`/`sqlite3.Error`/`ZeroDivisionError`/`AttributeError`
(exit 1).

**The schema is not corpus-pinned.** `timeline.counts.editions` was
`const: 118`, so the Draft-2020-12 subset could only ever validate the 44-ФЗ
artifact set and reported any other act as a schema violation (exit 5) even when
the artifacts were correct. It is now `minimum: 1`, like the sibling counters.

**Extended-corpus parity is asserted, not assumed.** The 44-ФЗ artifacts remain
the oracle, and a labelled synthetic fixture corpus
(`crates/ln-consultant-parser/tests/fixtures/reference-layer/`, 18 cases) now
pins both implementations against each other: ten derivable cases must be
byte-identical, ten unreadable cases must fail closed with exit 3
(`scripts/test_m217_reference_parity.py`, plus the Rust-side
`tests/reference_layer_fail_closed.rs`).

## Rationale

The spine's strictness makes an evolvable knowledge layer safe (ADR-0030);
this contract converts that principle into measured artifacts: every semantic
rule (D765/D767 temporal policy, purge-band history, reference
disambiguation) is executed by code and pinned by committed bytes. The
prototype loop surfaced and fixed real model defects (NBSP headings, greedy
article-number regex, single-valued refs, missing punkt level, edition-policy
precedence) — each now encoded as invariant or rule.

## Consequences

- M217 bake-off proceeds against these artifacts and this contract
  (stores: Oxigraph / Kuzu+DuckPGQ / XTDB, per the research note).
- Python module stays the reference; Rust port must byte-match it, not
  reimplement different semantics.
- JSON-LD text projection stays on-demand until a store decision exists.
- Any normalization change requires a profile bump and artifact regeneration
  in the same change.

## Non-claims

Not semantic or legal acceptance; not authenticity evidence; not R1000
closure; not R035/R070 validation (both stay HOLD; deferred findings remain
deferred); no promotion of ADR-0030 beyond `[proposed]`; no parked milestone
released; digest identity is not text CTV resolution; amend provenance does
not interpret amendment semantics; corpus text-inline projection is rejected
as a persistent layer.

## References

ADR-0030 (knowledge layers, G1–G4), ADR-0016 (FRBR/ELI, R5-07), ADR-0020 (L5
practice overlay), ADR-0009 (five clocks), ADR-0015 (verification architecture);
D765–D777; M223/M224 artifacts (`prd/migration/rust-evidence/m223-*`,
`m224-*`); reference module `scripts/m217_reference_jsonld.py`; schemas
`scripts/m217_reference.schema.json`; research note
`phases/217-kbike0-graph-vector-crash-consistency-citation/217-RESEARCH.md`.
