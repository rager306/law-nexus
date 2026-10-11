# Intermediate-source consumer acceptance contract (tokenizer + graph projection)

**Status:** `[bounded]`
**Owning slice:** M223-d2q075 / S07 — design pin for
`crates/ln-decode/src/reader_tokenizer.rs` (`reader_tokenizer`, T02); tests
`crates/ln-decode/tests/reader_tokenizer.rs`;
`crates/ln-decode/src/npa_graph_projection.rs` (`npa_graph_projection`, T03);
tests `crates/ln-decode/tests/npa_graph_projection.rs`; counts-only consumer
binary `crates/ln-decode/src/bin/consumer-run.rs` (T04); corpus harness
`scripts/m223_s07_corpus_run.py` + `scripts/test_m223_s07_corpus_run.py` (T04);
final full-corpus acceptance run (T05); slice battery
`scripts/test_m223_s07_contract.py` (T06)
**Upstream wire contracts (frozen, `[bounded]`):**
`prd/architecture/source-jsonl-contract.md`,
`prd/architecture/reader-view-contract.md`,
`prd/architecture/reader-projection-contract.md`,
`prd/architecture/cleaned-projection-contract.md`,
`prd/architecture/npa-analysis-jsonl-contract.md`
**Upstream acceptance contract:** `prd/architecture/intermediate-source-acceptance-contract.md`
(§2 accepted base revision, §4 reading order versus record order, §5 composite
provenance, §6 graph document identity, §7 consumers without XML reparsing,
§8 whole-corpus acceptance boundary incl. §8.4 independent oracle/holdout and
§8.6 resumability, §10 non-claims)
**Upstream slice contracts:** `prd/architecture/intermediate-source-reading-order-contract.md`
(S04 `reader_reading_order` / `reader_composite`),
`prd/architecture/intermediate-source-clean-view-contract.md` (S05
`reader_clean_view` / `reader_clean_profile/v1`),
`prd/architecture/intermediate-source-navigation-contract.md` (S06
`reader_navigation`)
**Authority:** ADR-0013 (universal multi-source parser architecture), ADR-0015
(hexagonal verification architecture), ADR-0016, ADR-0028 (dual tokenizer —
three deliberate token producers), ADR-0029 (requisites-anchored member
assembly), D631 (S02 reader coordinate base), D633 (S03 reader content seal),
D634 (independent verifier recomputes from the substrate), D639/D640 (cleaned
JSONL envelope and non-cyclic seals), D602/D328 (serde stays module-scoped to
`source_package`), D724 (acceptance-contract pin), D729/D730/D731/D732 (S03
resumable baseline: harness architecture, terminal partition, edition-2024
rebuild, published counts), D733 (S04 reading-order/composite pin),
D734/D735 (S05 clean-view pin and its R1000 supporting-only reconciliation),
D736 (S06 navigation pin), **D737 (this design pin: consumer acceptance —
tokenizer + graph projection, additive-only)**
**Lifecycle ceiling:** this is a bounded design pin plus two read-only
consumers over already-verified decoded source and one acceptance run. It is
**not** an R1000 closure artifact, not semantic/legal interpretation, not
authenticity evidence, not normalization, not physical pagination, and not an
un-parking of any parked downstream program. It closes no requirement. R1000
stays active/unclosed.

## 1. Purpose and non-claims

### 1.1 Purpose

S03 delivered the frozen reader projection (view forest with `parent_view` and
ordered `children`, ordered source-fragment and derived segments, unresolved
reference records, source positions) and its independent verifier. S04 delivered
`reader_reading_order` (per-view reading order re-derived from the substrate
event walk) and `reader_composite` (composite coordinates). S05 delivered the
filtered clean view (`reader_clean_view` / `reader_clean_profile/v1`). S06
delivered the navigation index (`reader_navigation`).

Acceptance contract §7 assigns the **tokenizer** and **graph projection** the
final two projection-only surfaces:

> The three consumers — **navigation**, the **tokenizer**, and **graph
> projection** — read the materialized JSONL layers only. They must not re-open
> the source XML to recover structure, reading order, provenance, or identity.
>
> | Consumer | Reads | Must not |
> |---|---|---|
> | Tokenizer (S07) | clean text channel + source fragment/spans + derived controls (kind + source element, no fragment) + document identity | re-parse XML for text or boundaries; invent a fragment/span for a derived control |
> | Graph projection (S07) | document identity + typed members/relations | key by local fragment id; re-parse XML for relation endpoints |

S07 delivers those two consumer surfaces **and** the final whole-corpus
acceptance run that D638/D735 named as the R1000 remainder. The concrete
surfaces this document fixes:

- **`reader_tokenizer`** (T02): a public, `std`-only, `serde`-free consumer that
  turns the **saved cleaned wire JSONL** into an ordered token stream. Each token
  carries **composite provenance** (§4): a source token carries
  `fragment_ref` + `slot` + `span` + `element_ref` + `source_pos`; a derived
  control carries `kind` + `element_ref` + `source_pos` and **no** fragment/span;
  a token that crosses several source/derived units is a **composite range** of
  ordered units. Document identity binds every token to one verified document.
  XML is never opened.
- **`npa_graph_projection`** (T03): a public consumer of the saved
  `npa-analysis` JSONL that projects typed members, relations, and
  classifications into a graph whose nodes, edges, and member keys are the
  **composite document identity** `SourceIdentity ⊕ DocumentVersionRef` (§5),
  never a bare local `tN` / `eN` / `member_id`. A record whose parent identity
  differs from the unit's pinned identity is **refused** (`CrossDocument` /
  `SourceIdentityMismatch`) and never rebased. **Repeat import is idempotent**:
  importing the same JSONL twice yields byte-identical graph counts and no
  duplicate nodes/edges/members. XML is never opened.
- **`consumer-run`** (T04): a counts-only binary that runs both consumers over
  one document and emits **exactly one** JSON counts document (schema
  `m223-s07-consumer-counts/v1`) with closed exit codes and **no raw decoded
  text**.
- **Corpus harness** `scripts/m223_s07_corpus_run.py` (T04/T05): the resumable,
  hash-bound full-corpus acceptance run over the S02 manifest
  (`prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl`), one terminal
  consumer outcome per entry, with restart (resume) and repeat import.

### 1.2 Non-claims

- **Not** an R1000 closure artifact. S07 delivers the two consumer surfaces and
  the full-corpus acceptance run that supports the wider R1000 program; closure
  is owned by M223 as a whole and is an evidence-gated decision M223 does not
  unilaterally take. R1000 stays `active/unclosed` (§10; precedent S03–S06,
  D735).
- **Not** semantic or legal. A token stream and a member/relation graph assert
  *document structure and identity*, never legal authority, legal completeness,
  or normative citation resolution. The tokenizer's `kind` labels stay **working
  labels** (acceptance contract §10; npa-analysis contract §6 rule 6), never
  adopted legal TYPE vocabulary.
- **Not** authenticity. Any `source.sha256` / seal / `content_hash` pin is an
  integrity/version pin; a party controlling the bytes can recompute it
  (acceptance contract §6, §10).
- **Not** normalization. The tokenizer reads the lossless cleaned envelope's
  text channel and the projection's segments verbatim; it does not normalize,
  case-fold, or transliterate, and it does not re-describe the S05 clean view.
- **Not** physical pagination. A derived `page_break` stays a derived control
  (`kind = page_break`); it is never a page boundary, never a page number, and
  never an input to graph identity. No page model exists in this contract.
- **Not** an XML re-parse. Every token and every graph key is read from the
  materialized JSONL layers only (§3). Detecting XML re-parsing by a consumer is
  part of the S07 acceptance.
- **Not** a corpus result restated as semantics. The S03 baseline (§9) is an
  acceptance/integrity baseline, not a semantic oracle (acceptance contract
  §8.2).
- **Not** an un-parking. No parked downstream milestone (M208-wrz6fg, M215–M220,
  and any other parked consumer program) is resumed, reopened, or bound
  (acceptance contract §8.7).
- **Not** a new wire contract. S07 is additive-only over the five frozen wire
  contracts (§6); it registers modules, adds tests, a counts-only binary, and
  scripts, and edits no frozen contract silently.
- Read-only: neither consumer mutates, reseals, or re-bases the projection, the
  reading-order index, the clean view, or the analysis envelope.

## 2. Composite provenance (acceptance contract §5)

No single identifier is sufficient provenance. A token carries **exactly one of
two provenance forms**, one per unit kind, and a consumer must use the right one:

**Source token** (a source-fragment unit; `ReaderSegmentKind::Text`, `origin =
source_fragment`):

```
document identity  (§5)
  ⊕ element_ref   (capture owner, eN)
  ⊕ slot          (text | tail)
  ⊕ fragment_ref  (tN)
  ⊕ span          (half-open UTF-8 byte range [start, end) over the fragment's decoded value)
  ⊕ source_pos    (owner element pre-order index)
```

**Derived control** (`ReaderSegmentKind::Derived` from `tab` / `br` / `cr`,
`origin = derived:<kind>`):

```
document identity  (§5)
  ⊕ element_ref   (the documented control element, eN)
  ⊕ source_pos    (control element pre-order index)
  ⊕ derived kind  (tab | line_break | page_break)
  ⊕ rule/profile  (the versioned derivation rule that produced the literal)
```

Load-bearing rules:

1. **A token wholly inside one Source-unit** localizes as `fragment_ref` + `slot`
   + `span`, where `span` is the fragment's decoded span offset by the token's
   local offset within that unit: `token_span.start = span.start + local_start`,
   `token_span.end = span.start + local_end`. The token never invents a
   `fragment_ref`; it copies the unit's.
2. **A token that crosses a unit boundary** (several fragments, or a fragment and
   a derived separator, or several derived controls) is a **composite range**: an
   ordered list of source sub-spans plus the derived kinds between them, carried
   as ordered `output_start` / `output_end` units over the owning primary view —
   never a single fictitious fragment slice (acceptance contract §5;
   `reader_composite::CompositeRange`).
3. **A derived control has no `fragment_ref` and no `span` by construction**
   (`reader_projection.rs:926`–`944`; reader-projection contract §3.2). A
   consumer must **never** invent one. A token made only of a derived control
   carries the derived form and nothing else.
4. **The composite is read-only.** A consumer may project it into its own
   coordinates, but may not rebase it onto a different source, drop the owner,
   invent a fragment for a derived control, or re-derive it from XML.
   Reassigning a fragment to the wrong owner or view is a
   `fragment_in_wrong_view` / `segment_owner_mismatch` defect and is refused by
   the reader verifier.

`reader_tokenizer` copies provenance verbatim from the frozen reader projection
segments (and the S04 composite coordinates for cross-unit tokens); it re-derives
nothing from XML and never fabricates a coordinate.

## 3. Graph document identity (acceptance contract §6)

The graph projection keys nodes, members, and relations by **document
identity**, never by a fragment id alone: fragment ids (`tN`, `eN`) and member
ids (`mt:<index>`, `ml:<member_id>`, `r:<index>`, `c:<member_id>`) are local to
one document and collide across the corpus.

The identity is the composite pinned by the analysis contract §4.1/§4.2 and
represented in code by `analysis_source_mapping::{SourceIdentity, DocumentVersionRef}`:

- `SourceIdentity` — `source_sha256` (64 lowercase hex, copied from the parent
  manifest, never recomputed) + `source_bytes` + `parent_schema` +
  `records_seal_hash` (or `None`) + `manifest_hash` (or `None`); integrity
  evidence, not authenticity;
- `DocumentVersionRef` — the triple (`document_version_ref`, `source_revision`,
  `decoder_profile`).

The graph key is the **pair** `SourceIdentity ⊕ DocumentVersionRef`. Binding
rules:

1. All records in one unit belong to exactly one document version.
2. Two units sharing `document_version_ref` but differing in `source_revision`
   or `decoder_profile` are **different versions** and must not be merged.
3. A record citing a fragment (or member) whose parent identity differs from the
   unit's pinned identity is **refused** (`CrossDocument` /
   `SourceIdentityMismatch`) and is **never rebased** onto the unit's source.
4. **Repeat import is idempotent.** Importing the same analysis JSONL twice into
   the same graph produces byte-identical node/edge/member counts and no
   duplicates: an already-present identity key is a no-op, not a second node.
   Idempotency is defined over the identity key, so a re-import of the *same*
   document version is a no-op while a genuinely different version is a distinct
   key, never a collision.
5. Cross-document relations remain out of scope unless a later slice owns them
   explicitly.

## 4. Consumers without XML re-parse (acceptance contract §7)

Both S07 consumers read only the materialized JSONL layers. They must not
re-open the source XML to recover text, boundaries, provenance, or identity:

| Consumer | Reads | Must not |
|---|---|---|
| Tokenizer (S07) | cleaned wire JSONL text channel (clean text) + reader-projection segments (`fragment_ref` / `slot` / `span` / `element_ref` / `source_pos`) + derived controls (kind + source element, no fragment) + document identity | re-parse XML for text or boundaries; invent a fragment/span for a derived control |
| Graph projection (S07) | `npa-analysis` JSONL document identity + typed members / relations / classifications | key by local fragment/member id; re-parse XML for relation endpoints |

The no-reparse rule is the whole point of materializing an intermediate source:
if a consumer needs a fact that is absent from the JSONL, the fix is to extend
the producer under a tracked contract, never to add a hidden XML pass. **S07
acceptance detects XML re-parsing by a consumer**: the T02/T03 tests assert the
consumers build from read-back JSONL only (wire read-back parity: export →
`read_cleaned_wire` / analysis read-back → consumer output == the direct build),
and a consumer that opened the source XML would be a recorded failure.

## 5. Independent oracle / holdout (acceptance contract §8.4)

Corpus-wide outcomes (§8.1) and independent semantic checking (§8.2) are
**separate deliverables with separate evidence**. S07 builds its oracle/holdout
from **human- or independently-authored expectations**, never from the
producer's own output and never from the producer's helper functions. The holdout
set is withheld from any tuning and reported as a **distinct result set** in its
own channel:

- Tokenizer oracle: handwritten expected token streams (kind + provenance form)
  over tracked fixtures, authored independently of `reader_tokenizer`.
- Graph oracle: handwritten expected identity keys and relation endpoints over
  the tracked analysis fixtures, authored independently of
  `npa_graph_projection`.
- A holdout fixture is withheld from tuning; a producer-derived expectation is
  **never** accepted as an oracle.

## 6. Whole-corpus acceptance boundary (acceptance contract §8.1 / §8.6)

### 6.1 Every input has a terminal outcome; refusal is not success

The full pinned corpus is processed under the S02 inventory manifest
(`prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl`), and every
manifest entry reaches **exactly one** terminal consumer outcome:

- `accepted` — the consumer binary produced a counts document with recorded
  identity/seals; **or**
- `refused` — a typed, bounded refusal (a closed reason class), which is **not**
  a functional success and is never counted as one; **or**
- `incomplete` — a harness class (timeout / signal / limit / usage error), which
  is **non-terminal** and always re-attempted on resume.

Corpus statistics report `accepted`, `refused` (by closed reason class), and
`incomplete` separately; a run with refusals does not "pass" merely because it
did not crash. A partial run is **never** reported as full
(`partial_is_not_full=true`).

### 6.2 Resumability tied to input, code, rules, and binary hashes

A resumable corpus run binds each receipt to the hash families that determine its
meaning (acceptance contract §8.6):

- **input**: the per-file `source.sha256` (and byte count) from the inventory
  manifest;
- **code**: the source revision of the consumer pipeline actually executed (the
  aggregate content hash over tracked files, never a guess from HEAD);
- **rules**: the decoder/cleaner profile and contract version
  (`reader_wordml_profile/v1`, `npa_analysis_jsonl` version `1`,
  `cleaned_projection_wordml/v1`);
- **binary**: the sha256 of the `consumer-run` binary actually executed.

Resume is valid only when **all** families match. A receipt whose input hash
matches but whose code/rules/binary hash has moved is **stale** and must be
recomputed. `run --resume` reports `complete` only when every entry has a current
terminal receipt (no silent skip and no silent limit). Interruption (SIGTERM
preserving completed receipts), same-ledger resume, and repeat-import
byte-identical counts are demonstrated end-to-end and published as
`m223-s07-resume-proof.json` and `m223-s07-repeat-import-proof.json`.

## 7. Additive-only over the five frozen wire contracts

This design is **additive-only**. The five upstream wire contracts below are
frozen as of the S07 design. The sha256 of each tracked file **at design time**
is pinned in the machine-readable inventory block. **No upstream contract is
changed silently.** Any extension to one of them is a recorded revision or a
recorded decision — never a quiet edit. T06's slice battery recomputes these
hashes and fails on drift; a drift is an explicit re-pin, not a silent update.

Frozen upstream wire-contract inventory (design-time sha256):

| Contract | sha256 |
|---|---|
| `prd/architecture/source-jsonl-contract.md` | `2ddfe7da95e3adc0c341965f709001e2cdd67ccca3b22b7970ee06ad1dc0d9f6` |
| `prd/architecture/reader-view-contract.md` | `80a846fffedace7d78ef0b80faf14085eb05037a4aa7baca92de415f1b7d1b7d` |
| `prd/architecture/reader-projection-contract.md` | `95d0f127f8b1cf72dc2dcaec97271c408ca0543cb8487f7839af57553c6eec3e` |
| `prd/architecture/cleaned-projection-contract.md` | `7d167e434c4640b539406ddd5de39286d30b1e2efeb43bfdaa603b76b0313c4e` |
| `prd/architecture/npa-analysis-jsonl-contract.md` | `a3f51100679613a7f76c84a7282b50a5e31dc43abc4f652e221fd745136f00cb` |

Machine-readable form (T06 parses this block; keep one entry per line):

```
<!-- frozen-contract-inventory:begin -->
sha256:2ddfe7da95e3adc0c341965f709001e2cdd67ccca3b22b7970ee06ad1dc0d9f6 prd/architecture/source-jsonl-contract.md
sha256:80a846fffedace7d78ef0b80faf14085eb05037a4aa7baca92de415f1b7d1b7d prd/architecture/reader-view-contract.md
sha256:95d0f127f8b1cf72dc2dcaec97271c408ca0543cb8487f7839af57553c6eec3e prd/architecture/reader-projection-contract.md
sha256:7d167e434c4640b539406ddd5de39286d30b1e2efeb43bfdaa603b76b0313c4e prd/architecture/cleaned-projection-contract.md
sha256:a3f51100679613a7f76c84a7282b50a5e31dc43abc4f652e221fd745136f00cb prd/architecture/npa-analysis-jsonl-contract.md
<!-- frozen-contract-inventory:end -->
```

### 7.1 Immutability of the six §2 files and the frozen JSONL

The **six tracked §2 files** named by the acceptance contract (the accepted base
revision) are **not** modified by S07. Their design-time sha256 pins:

| File | sha256 |
|---|---|
| `crates/ln-decode/src/reader_projection.rs` | `0d4e9f40d8d85da1b55496cc0f843aa7b837e1ffcdae1b40b9dfd51e0f997246` |
| `crates/ln-decode/src/reader_verifier.rs` | `3b9f3b267f57892216038fd19ff692d051c3868aa41140b59a9fe04314498c5f` |
| `crates/ln-decode/src/npa_analysis_wire.rs` | `80cbe03e5425cd4981242043dd9a822f9546994b2309e83a66d8b38f03663f88` |
| `crates/ln-decode/tests/reader_tail_semantics.rs` | `eba6187abcd813dfd9b71010d489fd645a2ae5a9bb2f8f2bcb29e3bd5f423c2c` |
| `crates/ln-decode/tests/npa_analysis_strict_admission.rs` | `6be0a721be429ea2f447aec80426e44f2a9b741416e693a7ce3797513c768e43` |
| `crates/ln-decode/tests/m222_f07_audit.rs` | `019136892dfa5acbe4ec028e42eb8ec552c2c48fb0fe0c1f74cdbbebd006be64` |

The frozen `prd/architecture/*.jsonl` tracked artifacts are **not** modified:

| File | sha256 |
|---|---|
| `prd/architecture/architecture_items.jsonl` | `3ef86ce1e2c8969d4f919b3cae31621acf0fb3d6d49334bbc05d89ab9c85d966` |
| `prd/architecture/architecture_edges.jsonl` | `ce53dc0e1e4d2851aac538827ced9a9e007e4af3ce54d2b98b780b7739616818` |

Machine-readable form (T06 parses this block; keep one entry per line):

```
<!-- immutability-pins:begin -->
sha256:0d4e9f40d8d85da1b55496cc0f843aa7b837e1ffcdae1b40b9dfd51e0f997246 crates/ln-decode/src/reader_projection.rs
sha256:3b9f3b267f57892216038fd19ff692d051c3868aa41140b59a9fe04314498c5f crates/ln-decode/src/reader_verifier.rs
sha256:80cbe03e5425cd4981242043dd9a822f9546994b2309e83a66d8b38f03663f88 crates/ln-decode/src/npa_analysis_wire.rs
sha256:eba6187abcd813dfd9b71010d489fd645a2ae5a9bb2f8f2bcb29e3bd5f423c2c crates/ln-decode/tests/reader_tail_semantics.rs
sha256:6be0a721be429ea2f447aec80426e44f2a9b741416e693a7ce3797513c768e43 crates/ln-decode/tests/npa_analysis_strict_admission.rs
sha256:019136892dfa5acbe4ec028e42eb8ec552c2c48fb0fe0c1f74cdbbebd006be64 crates/ln-decode/tests/m222_f07_audit.rs
sha256:3ef86ce1e2c8969d4f919b3cae31621acf0fb3d6d49334bbc05d89ab9c85d966 prd/architecture/architecture_items.jsonl
sha256:ce53dc0e1e4d2851aac538827ced9a9e007e4af3ce54d2b98b780b7739616818 prd/architecture/architecture_edges.jsonl
<!-- immutability-pins:end -->
```

S07 adds new files (`reader_tokenizer.rs`, `npa_graph_projection.rs`, their
tests, the `consumer-run` binary, the corpus harness, the slice battery, the
evidence artifacts) and registers two modules (`pub mod reader_tokenizer;`,
`pub mod npa_graph_projection;`) plus one `[[bin]]` in
`crates/ln-decode/Cargo.toml` — additive edits only.

### 7.2 Machine-readable consumer model block

T06 parses this block and fails on drift between it and the `reader_tokenizer` /
`npa_graph_projection` source declarations. Exactly one line per model element:

```
<!-- consumer-model:begin -->
provenance:source_fragment fields:document_identity,element_ref,slot,fragment_ref,span,source_pos
provenance:derived_control fields:document_identity,element_ref,source_pos,derived_kind,rule_profile
provenance:composite_range units:source_subspan,derived_control
derived_kind:tab
derived_kind:line_break
derived_kind:page_break
graph_identity:SourceIdentity
graph_identity:DocumentVersionRef
graph_identity:composite_source_identity_xor_document_version_ref
graph_node:member
graph_node:fragment
graph_node:classification
graph_edge:relation
graph_refusal:cross_document
graph_refusal:source_identity_mismatch
graph_refusal:document_version_mismatch
graph_refusal:unknown_fragment
<!-- consumer-model:end -->
```

## 8. S03 reconciliation

S07 reconciles with the S03 baseline
(`prd/migration/rust-evidence/m223-s03-baseline-run.json`, schema
`m223-s03-baseline-run/v1`):

| fact | value |
|---|---|
| corpus entries | 43785 |
| accepted | 43785 |
| refused | 0 |
| incomplete | 0 |
| R1000 status | `active/unclosed` |

The two consumers are defined and exercised **per accepted document** on tracked
fixtures and a bounded seeded real-corpus sample; the **full** whole-corpus
materialization of the tokenizer and graph projection over all 43 785 accepted
documents is the S07 T05 final run. S07 must not restate S03's integrity/count
result as a semantic or legal claim: the S03 run is an acceptance/integrity
baseline, not a semantic oracle (acceptance contract §8.2).
`s03_baseline_reconciled` in the S07 evidence artifact records the four numbers
and `r1000_status` above, and nothing more.

## 9. Slice boundaries S06 / S07 and S07 / milestone

| Surface | Disposition |
|---|---|
| navigation model (address spaces, nodes, links, index), structure / path / siblings, neighbours, subtree text, reference resolution, typed errors | S06 (T01–T03) — `reader_navigation`; **consumed read-only by S07 where shared** |
| bounded seeded real-corpus navigation census (counts only, redacted) | S06 (T04) |
| tokenizer consumer (clean text channel + reader segments + derived controls + composite provenance, no XML re-parse) | S07 (T02) — `reader_tokenizer` |
| graph projection keyed by `SourceIdentity ⊕ DocumentVersionRef` (idempotent repeat import, no XML re-parse) | S07 (T03) — `npa_graph_projection` |
| counts-only consumer binary + resumable corpus harness with restart and repeat import | S07 (T04) — `consumer-run`, `scripts/m223_s07_corpus_run.py` |
| full-corpus consumer acceptance run (43785 terminal outcomes) + restart + repeat import | S07 (T05) |
| design pin + additive-only + S03 reconciliation + slice battery | S07 (T01/T06) |
| whole-corpus materialization of navigation | S05–S07 |
| R1000 closure, legal completeness, source authenticity, normative citation resolution, normalization, physical pagination, temporal structure, cross-document relations, un-parking parked downstream | not S07; remains out of scope |

S07 consumes the S05 clean view (text channel) and the S04 composite coordinates
read-only for the tokenizer, and the frozen reader projection for both consumers.
It does **not** re-open, extend, or re-describe the S05 rule profile or the S06
navigation index. Out of scope for S07: normalization, XML re-parse, temporal
`StructuralAst`/CST/CTV, physical pagination, cross-document links, CLI beyond
the counts-only consumer binary and the harness subcommands, and any R1000
closure. R1000 stays active.

## 10. Threat surface

- **Untrusted JSONL input → fail-closed.** Both consumers validate identity,
  provenance, and closed reasons; a malformed or identity-mismatched record is a
  typed refusal, never a partial or clamped graph. `CrossDocument` /
  `SourceIdentityMismatch` / `DocumentVersionMismatch` are closed refusals, not
  silent rebases.
- **Replay / repeat import — mitigated.** Repeat import is idempotent by identity
  key, and the harness re-validates the input/code/rules/binary hash bindings on
  `--resume` (no blind skip of a receipt whose binding drifted; acceptance
  contract §8.6).
- **Parameter tampering — partially mitigated.** Closed runner exit codes,
  frozen-pin drift detection, and S03 reconciliation (43785/0/0) constrain
  tampering. The harness invokes the binary with an **argv array** — no
  shell-string interpolation of corpus paths (D574).
- **No invented coordinate.** A derived control never receives a fabricated
  `fragment_ref` / span; a cross-unit token is a composite range, never a single
  fictitious fragment slice.
- **Decoded legal text is not a secret, but counts artifacts are redacted.** The
  layers the consumers read carry verbatim decoded legal text (acceptance
  contract §3 lossless envelope), so redaction is **not** automatic. All S07
  evidence artifacts (`m223-s07-corpus-run.json`, `…-receipts.jsonl`,
  `…-resume-proof.json`, `…-repeat-import-proof.json`, `…-acceptance-battery.json`)
  carry only **paths, counters, and hashes** — no raw decoded text. Decoded text
  is permitted only inside Rust tests over the tracked fixtures. The slice
  battery asserts an `assert_no_raw_text`-style redaction invariant over **all**
  S07 artifacts, including any holdout fixtures.
- **Not authenticity.** Carried forward (acceptance contract §10): consumer
  outputs are not tamper-proof; a party controlling the bytes can recompute any
  pin.
- **Inputs are admission-verified.** Both consumers read an already-verified
  reader projection / analysis envelope; they do not re-parse XML, do not
  re-open the corpus, and do not relax S03 admission.
- **No rebasing / silent loss.** Provenance and identity are copied, not
  re-based; a record with no valid endpoint is retained with an explicit closed
  reason, not dropped.

## 11. Requirement impact

- **R1000 — supporting-only. Do not close.** S07 delivers the two consumers
  (`reader_tokenizer`, `npa_graph_projection`) and the full-corpus acceptance run
  that D638/D735 named as the R1000 remainder; it is not an R1000 closure
  artifact and must not be reported as one. R1000 stays `active/unclosed`
  (acceptance contract §10; precedent S03–S06, D735). Closure is a separate,
  evidence-gated decision M223 does not unilaterally take.
- **R1001 — not touched** (`npa_analysis_wire.rs` is a frozen §2 file, §7.1).
- **R066 — not touched** (anti-feature).
- No other R-ID is bound or re-labelled by S07. S07 adds no new requirement and
  advances no requirement to `validated`.

## 12. Verification surface

- `crates/ln-decode/src/reader_tokenizer.rs` (T02) inline unit tests: provenance
  forms, single-unit span offset arithmetic, composite range across a unit
  boundary, derived-control-without-fragment, and the absence of a `serde`
  dependency.
- `crates/ln-decode/tests/reader_tokenizer.rs` (T02): handwritten oracles over
  the tracked fixtures (kind + provenance form), wire read-back parity
  (export → read-back → tokenizer output == the direct build), and the negative
  that no XML is opened.
- `crates/ln-decode/src/npa_graph_projection.rs` (T03) inline unit tests: identity
  key composition, member/relation/classification node construction, idempotent
  repeat import (no duplicates), and closed refusals.
- `crates/ln-decode/tests/npa_graph_projection.rs` (T03): handwritten identity/
  endpoint oracles; negatives (identity mismatch → `CrossDocument` /
  `SourceIdentityMismatch`, duplicate import → identical counts, no reparse).
- `crates/ln-decode/src/bin/consumer-run.rs` + `scripts/m223_s07_corpus_run.py`
  (T04): exactly one counts document (schema `m223-s07-consumer-counts/v1`) with
  closed exit codes and no raw text; the resumable harness over the S02 manifest
  emits `prd/migration/rust-evidence/m223-s07-corpus-run.json`,
  `…-receipts.jsonl`, `…-resume-proof.json`, `…-repeat-import-proof.json`
  (counters, hashes, closed outcomes; no raw text).
- `scripts/m223_s07_corpus_run.py` final full-corpus run (T05): 43785 terminal
  outcomes, one per manifest entry; `accepted` / `refused` / `incomplete`
  reported separately; counts reconciled to S03 (43785/0/0);
  `partial_is_not_full=true`; restart (SIGTERM + same-ledger resume) and repeat
  import (byte-identical counts) proven.
- `scripts/test_m223_s07_contract.py` (T06): (a) this document exists and carries
  the required sections/markers ("Purpose and non-claims", "Composite
  provenance", "Graph document identity", "Consumers without XML re-parse",
  "Independent oracle / holdout", "Whole-corpus acceptance boundary",
  "Additive-only", "S03 reconciliation", "Slice boundaries", "Threat surface",
  "Requirement impact", "Verification surface", `frozen-contract-inventory`
  block, `immutability-pins` block, `consumer-model` block, `active/unclosed`,
  `43785`, `reader_tokenizer`, `npa_graph_projection`); (b) the five pinned
  sha256 values match the tracked files **exactly** (drift → explicit re-pin,
  never silent); (c) the S03 baseline is reconciled (entries = accepted = 43785,
  refused = 0, incomplete = 0, R1000 active/unclosed, status `complete`);
  (d) the artifacts have schema v1, are redacted, and satisfy the consumer
  accounting invariants; (e) immutability: the six §2 files and the frozen
  `prd/architecture/*.jsonl` match the pinned sha256; (f) it emits
  `prd/migration/rust-evidence/m223-s07-acceptance-battery.json` (schema
  `m223-s07-acceptance-battery/v1`) with counters/hashes and `non_claims`,
  carrying only paths, counters, and hashes.
- Cleanliness battery: `cargo test -p ln-decode --offline --lib reader_tokenizer`;
  `cargo test -p ln-decode --offline --test reader_tokenizer`;
  `cargo test -p ln-decode --offline --lib npa_graph_projection`;
  `cargo test -p ln-decode --offline --test npa_graph_projection`;
  `cargo test -p ln-decode --offline`; `cargo fmt --all --check`;
  `cargo check --workspace --offline`;
  `cargo clippy --workspace --all-targets --offline -- -D warnings`;
  `uv run python scripts/verify-adr-conformance.py`.

## 13. References

- `prd/architecture/intermediate-source-acceptance-contract.md` §2 (accepted
  base revision), §4 (reading order versus record order), §5 (composite
  provenance), §6 (graph document identity), §7 (consumers without XML
  reparsing), §8 (whole-corpus acceptance boundary, §8.4 oracle/holdout, §8.6
  resumability), §10 (non-claims).
- `prd/architecture/intermediate-source-reading-order-contract.md` (S04
  `reader_reading_order` reading order and `reader_composite` coordinates).
- `prd/architecture/intermediate-source-clean-view-contract.md` (S05
  `reader_clean_view` / `reader_clean_profile/v1`; §9 hands S07 the clean view).
- `prd/architecture/intermediate-source-navigation-contract.md` (S06
  `reader_navigation`).
- `prd/architecture/npa-analysis-jsonl-contract.md` §4.1 (parent evidence
  identity), §4.2 (document version identity), §4.4 (cross-document refusal), §6
  (token views), §7 (outcomes and provenance), §8A.7 (record families).
- `prd/architecture/reader-projection-contract.md` §3.2 (`ProjectedSegment`),
  §5 (independent verifier semantics).
- `crates/ln-decode/src/analysis_source_mapping.rs` (`SourceIdentity`,
  `DocumentVersionRef`, `MappingRefusalKind::CrossDocument` /
  `SourceIdentityMismatch` / `DocumentVersionMismatch`).
- `crates/ln-decode/src/reader_composite.rs` (`CompositeAddress`,
  `CompositeUnit`, `CompositeRange`, `resolve_composite`).
- `crates/ln-decode/src/reader_contract.rs` (`ReaderViewKind`,
  `ReaderSegmentKind`, `ReaderSemantic`, `ReaderReferenceType`,
  `ReaderFragmentSpan`, `TextSlot`).
- `prd/migration/rust-evidence/m223-s03-baseline-run.json` (S03 baseline).
- `prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl` (S02 manifest
  consumed by the T04/T05 harness).

---
