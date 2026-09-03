# M199 S01 — Layer-2 gold-sample annotation protocol (`npa-lawref-sample/v1`)

**Status:** `[bounded]` annotation/evidence contract
**Milestone:** M199-3q54bv / S01 / T01
**Authority chain:** D363 (Layer-1 closed; Layer-2 stratified gold sample is the one
authorized next action), ADR-0028 (evaluation discipline, 30–50 act envelope),
assessment/25 §4–§5.2 (Layer-2 protocol, Ding 2025 citation), D350 (ELI
canonical-vs-user-reference duality)
**Executable schema:** `crates/ln-decode/tests/npa_lawref_support/mod.rs` (fail-closed
loader) + `crates/ln-decode/tests/npa_lawref_sample_contract.rs` (hostile schema pins)
**Non-authority:** this protocol does not decide legal meaning, does not validate the
NPA engine, does not promote ADR-0028 lifecycle, does not close R070 / R035 / R074,
and never labels the sample "G0" (§3).

## 1. Purpose

D363 closed Layer-1 (corpus sweep, C1–C3 convergence) and requires a dual-annotated
stratified gold sample **before any FSM code**. This document is the codebook that
makes the Layer-2 sample construction executable and auditable:

- it fixes the unit of coding and the closed slot set (§4–§5);
- it fixes the machine-readable manifest schema `npa-lawref-sample/v1` that S01/T02
  fills and the fail-closed loader enforces (§13–§14);
- it is what S04 later reads as the α codebook (§9).

The rule-seed (T03) is a deterministic scanner over the frozen C2 lexer — it is
distant supervision, not an annotator and not gold (§10–§11).

## 2. Mandatory non-claims on every derived artifact

Every artifact derived from this protocol (manifest, seed JSONL, reports) carries
`non_claims` covering, at minimum, the substrings pinned by the loader
(`SAMPLE_REQUIRED_NON_CLAIMS`):

1. **not official-publication provenance** — the sample is a Consultant-export draw,
   not a pravo.gov.ru publication record; R070 stays open;
2. **not amendment provenance** — spans do not establish which amendment introduced
   which text (R070);
3. **not LawRef / act-tree / clause segmentation** — no `LawRef` type may exist in
   `src/` during S01; slot annotations are not the N2 product schema;
4. **not the N2-gate acceptance decision** — a filled sample is not an N2 acceptance;
5. **not legal interpretation** — spans mark reference *shapes as written*, never
   legal meaning or applicability.

The loader rejects empty `non_claims` and `non_claims` missing any required
substring, fail-closed.

## 3. Naming discipline: the sample is never "G0"

`G0` has three unrelated meanings in this project (MEM1111): corpus-tier G0 Shape,
the parser G0–G3 evidence ladder, and disposition G0(a–g). This sample is **none of
them**. It must be called the "Layer-2 gold sample" or the "`npa-lawref` sample" —
never "G0". Downstream artifacts must not inherit the label.

## 4. Unit of coding

One coding unit = one **user-reference span** on **decoded UTF-8 block text**
(the ELI *user-reference* half of D350: the reference exactly as written, before any
canonical resolution).

- Fragment text comes only from `ConsultantWordMlBlockDecoder` decoded blocks
  (`block.text()`); never a naive `w:t` join (WordML runs drop inter-run spaces) and
  never Garant ODT (Consultant ≠ Garant).
- The span coordinate system is the fragment `.txt` file itself: a non-empty
  half-open byte range `[start, end)` on UTF-8 char boundaries. Lexemes are
  reconstructed by slicing `text[start..end]` — never duplicated into JSON.
- **Covering invariant with the fragment text:** the manifest pins
  `byte_len` equal to the fragment file's byte length, and every seed span must
  satisfy `start < end`, `end <= byte_len`, and char-boundary alignment
  (loader-enforced). There is deliberately no token-concat covering check on the
  Layer-2 manifest: fragments are plain decoded text, not a TokenKind sidecar.
- One fragment carries zero or more annotated spans; a fragment with no reference is
  coded `not_a_reference` (§5), not left empty by omission.

## 5. Closed slot set

The Layer-2 label space is **closed** — exactly these eight slots plus the empty
marker. No annotator or tool may invent a ninth slot; schema evolution means a new
`schema_version`, not extra keys (the loader rejects unknown keys fail-closed).

| Slot | Type | Meaning |
|---|---|---|
| `marker_chain` | array of abbrev ids | the marker chain as written (`st`, `stst`, `ch`, `p`, `pp`, `podp`, `abz`, `gl`, `razd`), each occurrence in order |
| `hier_nums` | array of hier numbers | dotted hier numbers paired positionally with the chain (`15.1`, `2.3.1`) |
| `date` | string or null | `dd.mm.yyyy` requisite when part of the reference |
| `doc_no` | string or null | document number token (`44-ФЗ` shape) when part of the reference |
| `law_code` | string or null | lone `ФЗ` / `ФКЗ` law code when part of the reference |
| `anaphora` | string or null | **unresolved** anaphora marker (`настоящей`, `того же` class) — recorded, never resolved here |
| `range` | object or null | **unresolved** range endpoints as written — recorded, never expanded here |
| `quoted_enum` | string or null | quoted subpoint label (`"а"`) when part of the reference |
| `not_a_reference` | bool | the fragment contains no user reference at all |

Fullword reference tails (`статьи`, `пункта`, `закона`, `года` adjacent to a hier
number or doc number) are coded through `marker_chain = []` + the paired
`hier_nums`/`doc_no`, and additionally flagged `fullword-ref` in the rule-seed
pattern id — they are **not** Abbrev markers (the C2 lexer classifies them as Word;
the seed must observe that, not retag it).

## 6. Anaphora and range are unresolved slots, never canonical anchors

Anaphora (`части 1–3 настоящей статьи`, `пунктом 5 того же раздела`) and ranges
(`пункты 1 - 4.1`) are recorded **as written**, in the `anaphora` / `range` slots.
Coding an anaphora or a range MUST NOT:

- resolve it to a canonical article/part/point anchor (resolution is N2/S03 work);
- expand a range into its members (expansion is S03 work);
- mint a canonical eId path (D350 canonical half — not a Layer-2 concern).

The slots exist so S03/S04 can measure how much unresolved material the sample
actually contains without pretending it was already resolved.

## 7. Annotator independence; adjudication is S04

Two annotators code the sample **independently**, each from this protocol alone:

- no shared or visible annotations before both passes are committed;
- `rule-seed` spans must not be used as guidance during an independent pass; seed
  prefill is permitted only after the S01 DS-noise report (§11) exists, and only
  with explicit provenance recording (§10);
- disagreement adjudication is an **S04** activity — it does not happen inside S01,
  and no S01 artifact may present an adjudicated annotation as independently agreed.

## 8. Span-exact match rule

A span (seed or human) matches another iff **(start, end, kind)** are all equal:

- byte-exact boundaries (`[start, end)` on the fragment text);
- the same reference-vs-not decision (`not_a_reference` matches only
  `not_a_reference`);
- partial overlaps, shifted boundaries, or same-position/different-slot codings are
  disagreements, not matches. This is the rule S04 will use for span-exact
  precision/recall and for agreement coding; S01 only records spans that satisfy it.

## 9. Agreement metric: α belongs to S04, not S01

Agreement is planned as nominal/multi-label agreement over the closed slots
(Krippendorff α; Artstein & Poesio 2008). The **formula and the ≥ 0.8 threshold are
S04 gates**. S01 computes **no α**:

- no second independent annotator exists in-process yet;
- computing agreement against the rule-seed would measure seed precision, not
  inter-coder agreement, and would launder distant-supervision noise into the
  Layer-2 gate.

Any S01/S02/S03 artifact that reports an α number for this sample is invalid by
construction.

## 10. Provenance: `rule-seed` vs `human-reviewed`

Exactly two provenance values exist for spans:

| Value | Meaning |
|---|---|
| `rule-seed` | deterministic scanner output over the frozen C2 lexer (T03). Distant labels; **never gold**. |
| `human-reviewed` | a human annotator's committed coding (S04 and any later human pass). |

Every span in the seed sidecar carries `provenance=rule-seed` until a human
confirms it. Downstream consumers must never treat `rule-seed` spans as gold,
regardless of how plausible they look.

## 11. DS-NER noise taxonomy: incomplete vs inaccurate

The rule-seed is distant supervision, so its error must be measured before anyone
calls it gold. Citation: Ding 2025 (DS-NER, IEEE TKDE) **via assessment/25 §5.2**;
the primary PDF was not retrieved, which is recorded as a bounded literature gap.
No Ding-specific formulas (confidence reweighting, teacher–student, GCE loss) are
claimed or used — S01 has no trainer. The operationalized taxonomy is the standard
DS-NER noise split documented in SANTA (Zhang et al., arXiv:2305.04076) and RoSTER
(Meng et al. 2021):

- **Incomplete** (false negative): a human-visible user-reference span the seed
  missed (fullword tails, uppercase enum markers, anaphora, ranges).
- **Inaccurate** (false positive / wrong slot): a seed span that is not a reference
  at all, or carries a wrong slot (a Date tagged as HierNum, `руб.` tagged as
  Abbrev, a hostile initial tagged as a marker).

T03 reports both rates on a deterministic nested subsample (20 fragments, ≥ 2 per
primary family), plus slot-confusion notes, with the explicit verdict
**do-not-treat-as-gold / pre-annotation**. One rater vs a machine is not
inter-coder agreement — no α is computed there. LLM pre-annotation is out of scope
(assessment/25 §6.4: deterministic pipeline; an LLM pass would add a second noise
source requiring its own Ding-style measurement).

## 12. D358 KEEP binds the M197 44-ФЗ sidecar, not this sample

The D358/D329 KEEP (no `гл.` / `абз.` / `утв.` / `podp` / `razd` / ... goldens)
binds the tracked **M197 44-ФЗ TokenKind sidecar** (`tests/fixtures/npa/`, frozen).
The C1 sweep over the full 43 785-XML corpus refuted "the nine never occur" as a
global claim (utv 3464, podp 1352, gl 1195, abz 1574, razd 163 hits).

Therefore: the **Layer-2 sample MAY contain real `гл.` / `абз.` / `утв.` /
`подп.` occurrences** drawn from the export. That is not a D358 violation — D358
binds the 44-ФЗ TokenKind goldens, not the Layer-2 draw, and N2 must learn exactly
these markers. Executors must not "KEEP" themselves out of abbreviations the sample
needs. The M197 sidecar itself remains frozen and is never written to.

## 13. Sample frame: the D367 quota table (9 strata, 40 documents)

`npa` is the oversampled primary (family dilution: fas 30 399 vs npa 916 in the
C3 census). The 118 44-ФЗ editions are **one Work** sampled as one cluster cell
(R081), not 118 strata. Frozen frame:

| Stratum | family | `doc_type` label | quota |
|---|---|---|---|
| Federal laws (non-44-ФЗ) | `npa` | `law` | 8 |
| 44-ФЗ edition cluster (one Work; ≥ 1 tracked `law-source/consultant/…44-fz…` member so the M197 sidecar stays a subset check) | `npa` | `law-44fz` | 4 |
| Orders (приказы) | `npa` | `order` | 6 |
| Resolutions (постановления) | `npa` | `resolution` | 4 |
| Directives (распоряжения) | `npa` | `directive` | 3 |
| Decree+document tail (honesty cell) | `npa` | `decree-document` | 1 |
| Courts practice | `courts` | `courts-unspecified` | 5 |
| FAS decisions | `fas` | `fas-unspecified` | 5 |
| Residual nested Consultant XML | `xml` | `xml-unspecified` | 4 |

Total: **40 documents** (8+4+6+4+3+1+5+5+4). Target: 3–5 reference-bearing decoded
fragments per document → **120–200 fragments**. Fragments are counted as fragments,
never as acts. If anaphora/range candidates land < 5, T02 tops up by swapping
fragments **inside** the same 40 documents (`note_kind=pattern-boost`), never by
growing the frame.

Closed vocabularies (loader-enforced): families `{npa, courts, fas, xml}`;
`note_kind` `{enacting, provider_note, hostile-control, pattern-boost}`; fragment
`status` `{seed}`. `hostile-control` rows sit outside the D367 quotas and exist to
pin negative behavior (T03). `provider_note` is a fragment provenance role from
Consultant notes — it never mints a lexer kind (`Editorial` remains absent from the
TokenKind set, and the loader rejects it by name).

## 14. Manifest schema `npa-lawref-sample/v1` (machine-readable)

Hand-rolled JSON only (D328: stdlib parser, closed keys, fail-closed extras — a
helpful `comment` field fails like D353). Root object — exact key set:

| Key | Contract |
|---|---|
| `schema` | exactly `"npa-lawref-sample/v1"` |
| `schema_version` | exactly `1` |
| `lifecycle` | exactly `"[bounded]"` |
| `draw_seed` | non-negative integer (u64), pinned by T02 so the draw is reproducible |
| `strata` | array of `{family, doc_type, quota}` rows; the multiset must equal the D367 table of §13 exactly |
| `documents` | non-empty array of document objects (below) |
| `fragments` | non-empty array of fragment objects (below) |

Document object — exact key set `{doc_id, source_path, source_sha256, byte_count,
family, doc_type, decoder, fragment_ids, non_claims}`:

- `doc_id` non-empty, unique; `source_path` repo- or export-relative (not absolute);
- `source_sha256` exactly 64 hex chars; `byte_count` ≥ 1;
- `family` ∈ closed set; `decoder` exactly `ConsultantWordMlBlockDecoder`
  (a Garant decoder value is rejected — `garant-odt` is a different provider
  stratum and is likewise rejected as a family);
- `(family, doc_type)` must appear in `strata`;
- `fragment_ids` non-empty, unique, referencing declared fragments;
- `non_claims` per §2 (loader requires the `official-publication`, `R070`,
  `LawRef`, `N2-gate`, `legal interpretation` substrings).

Fragment object — exact key set `{id, file, doc_id, source_block_index, note_kind,
byte_len, status}` plus the **optional** `{kind, start, end}` `seed_span`:

- `file` is a safe `*.txt` name (`npa-law-001.txt` style); the loader enforces a
  bijection `fragment.file ↔ *.txt` on disk (extra file or missing file fails);
- `byte_len` must equal the fragment file's byte length; text is UTF-8, no BOM, LF only;
- `status` exactly `seed` (anything else — including `gold` — fails: seed is not gold, §10);
- `note_kind` ∈ closed set (§13); an `Editorial` note_kind fails by name;
- `seed_span` when present: `kind` must be a closed C2 `TokenKind` name
  (`Word|Abbrev|HierNum|Date|DocNo|EnumMarker|LawCode|Punct|Space`). The loader
  rejects `Editorial` by name and rejects `LawRef` explicitly — `LawRef` is a
  product type, not a TokenKind, and must not leak into Layer-2 span fields. Spans
  obey §4 (`start < end`, `end <= byte_len`, char boundaries — past-EOF fails).

The tracked evidence copy of the manifest is
`prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json`; fragment texts
and the seed sidecar live under `crates/ln-decode/tests/fixtures/npa-lawref/`
(created by T02 — never in T01, and never inside `tests/fixtures/npa/`).

## 15. Verification routes

```bash
cargo test -p ln-decode --offline --test npa_lawref_sample_contract
cargo fmt --all --check && cargo check --workspace --offline
```

T01 pins the **schema, not the fill**: a minimal inline 1-doc/1-fragment manifest
loads; every hostile mutation (extra key, unknown family, empty/short non_claims,
`Editorial`, `LawRef`-as-kind, past-EOF span, wrong lifecycle, quota drift,
`garant-odt`, bijection violation, non-seed status) fails the loader closed; the
`src/` tree contains no `struct|enum|type LawRef`. Quota fill (40 docs,
120–200 fragments) is asserted only from T02 onward.

## 16. Protocol-level non-claims

This protocol alone proves nothing about the NPA engine. It does not establish
parser completeness, corpus representativeness, reference resolution, citation
safety, temporal applicability, or requirement closure. The sample is `[bounded]`
span/slot evidence inside ADR-0028's evaluation discipline; ADR-0028 stays
`[proposed]` and R070 / R035 / R074 stay open regardless of how the sample is
filled.
