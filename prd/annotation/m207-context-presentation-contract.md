# M207 context presentation bridge

Status: [proposed]. Design contract only; not adopted for human coding, not a new
version of the frozen S01/S02/S03 schemas, not an admission or acceptance record.

Scope split (D519): the historical human protocol below (frozen S01–S04 pilot,
coder presentation, HUMAN_PILOT_ABSENT / human-absent facts) stays frozen and is
**not** a mandatory gate for new M207 work. The automated successor is a separate
versioned records contract: `prd/annotation/m207-hybrid-records-contract.md`,
validated by `scripts/m207_hybrid_eval_experiment.py --validate-records`. Do not
read the human-pilot sections as a requirement to run a human evaluation for S05.

## Purpose and authority

Provide sufficient source context without treating a fragment-local annotation
as a cross-block mention, or treating a series as one reference by default.
The existing `m207-s01-codebook.md` section 1 remains authoritative for the frozen
coding format. `prd/architecture/m207-unit-diagnosis.md` describes a broader
complete-reference/series goal; this bridge does not claim to reconcile that
semantic change merely by keeping the same JSON keys.

Inputs: frozen pilot cases and coder kits, original seed fixture bytes, and the
operator-only `prd/migration/rust-evidence/m207-context-inventory.json`.
The inventory's `adaptation.coding_unit` expresses the diagnosis goal, NOT an
adopted replacement for the codebook. Its eligibility and diagnostic labels are
not coder-facing instructions or reference answers.

## Three units, kept separate

| Unit | Meaning | Counting rule |
|---|---|---|
| Presentation bundle | Focus fragment plus permitted ordered source context | Not an extra coding or evaluation observation |
| Frozen coding case | Original case ID and fragment-local byte coordinates | Preserve the original 40 case identities; do not silently drop cases |
| Future parser occurrence or relation | Independently identified mention or relation endpoints | Requires a separate evaluator and reference contract; not an S03 denominator |

For the frozen pilot, additional context does not expand the offered focus span.
An act occurring only in a context fragment is not a new submission case.
A series can contain several acts; it is neither one automatically merged span
nor one automatically merged identity. Any decision to annotate all members as
separate units requires a successor protocol and explicit population mapping.

## Presentation rules

1. Show the original focus fragment distinctly from context-only fragments.
   Render only the pinned decoded source bytes. Do not substitute prototype text
   or concatenate fragments into a new input artifact with shared offsets.
2. Every displayed block has its own fragment ID, document ID, byte length and
   hash. Coordinates remain half-open UTF-8-aligned file-byte ranges.
3. Context membership must be supported by same-document and ordered-block
   evidence. Proximity of filenames is not sufficient. Do not invent missing
   blocks or silently fetch an unlimited document.
4. A diagnosed series authorizes candidate context references for operator
   review; it does not prove legal completeness or human readiness.
5. Both independent coding passes receive byte-identical presentation content
   and instructions, apart from their pass/session identifiers. Freeze a common
   presentation-manifest hash before either pass starts. Record this in a separate
   administration sidecar, not by adding keys to a frozen submission envelope.
6. No model outputs, expected TYPE, legal classification, resolved aliases,
   predicted genre, diagnosis verdict, correctness highlight, duplicate-case
   answer, or other coder's response may appear in a blind presentation.
   A neutral focus boundary is navigation, not a predicted answer span.
7. Context shown to the coder and context supplied to a future evaluated parser
   must be recorded separately. Scores across different input regimes are not
   directly comparable; widening context is an experimental change.

## Explicit release states

The inventory is operator-only. A future presentation implementation may track
these conceptual states outside frozen coding records:

- assembled: references and hashes are present;
- source-verified: bytes, local boundaries and document membership verified;
- context-review-required: completeness or contextual relevance is unresolved;
- release-authorized: source-bound protocol compatibility and release decision
  recorded for the entire pilot administration.

No current artifact constitutes `release-authorized`. A green inventory check
only establishes inventory consistency, not source semantics or human readiness.
An implementation must not infer release from absence of truncation flags.

## Current exceptions

- Cases 011, 015, 019 and 032: known multi-fragment series; review the complete
  presentation, preserving each member's local coordinates.
- Cases 006 and 025: missing heads are unresolved. Do not guess a head or label.
  A newly sourced head needs provenance and a permitted-context decision; it
  cannot silently enlarge the frozen seed or be pasted into a frozen fixture.
- Cases 013 and 018: other truncation signals; do not treat them as series by
  default. Context sufficiency requires assessment.
- Remaining 32: inventory-only, not automatically ready for release.
- Duplicate text groups: 009/040, 012/030 and 023/029. Keep their original case
  identities for the frozen protocol. Do not copy one coder response into another
  case or count repeated bytes as independent evidence of generalization.

If any required case remains unreleasable, do not silently launch a reduced pilot.
Record the blockage in the administration inventory. Do not fabricate a human
abstention to represent a machine-detected unavailable input.

## Denominators and exclusions

The existing S03 aspect rules remain unchanged and continue to measure human
passes against resolved reference observations, not system quality. Additional
presentation fragments add zero cases and zero slot observations to that format.

A missing-context administration state is not one of the human coding outcomes.
Abstention is recorded only when actually selected by a coder under the accepted
protocol. No unresolved case is dropped to improve a rate. A redesigned population,
series-level unit, genre-stratified analysis or deduplicated denominator must be
specified in a successor protocol, with a mapping back to the old cases and
explicit limits on comparability. No retrospective relabeling of prior evidence.

## Required verification before a presentation implementation is released

- Identical source content and context order across two blind passes.
- Missing reference, wrong hash, cross-document member, invalid UTF-8 endpoint,
  changed presentation after freeze, or introduced answer field fails closed.
- Each rendered block maps back to exactly one pinned fragment-local range.
- No merged TextAnchor and no inferred TYPE or relation enters a submission.
- Additional context does not change case counts or create synthetic responses.
- Duplicate navigation never copies annotations across case IDs.
- Operator diagnoses are excluded from coder-facing payloads and rendering.
- An unreleasable case blocks release rather than disappearing from the manifest.

These are acceptance requirements for future code, not claims of implemented
checks. The existing inventory tests cover only inventory construction and drift.

## Selected direction: hybrid successor

The owner selected the hybrid approach: present the complete supported context,
annotate individual occurrences with local source anchors, annotate relations and
field provenance separately, and measure both components and whole-bundle
correctness. This selects the development direction, not human answers, legal
labels, a finalized schema, or operational release.

The fragment-local rules above describe the frozen compatibility plane only.
They do not restrict the successor to annotating the focus fragment. In the
hybrid successor, the evaluated region must be declared before annotation;
context-only regions remain distinct. All target occurrences within the declared
region must be accounted for, rather than just the originally selected focus.

### Representation and alignment

- Presentation bundles are reading units, not act identities or denominators.
- Each occurrence retains one or more fragment-local source references. A
  distributed evidence set is not a fabricated continuous cross-block span.
- Written values, normalized values and inherited values must remain distinct.
  Inheritance records the actual source; a correct value with a wrong source is
  not fully correct.
- Relations name explicit endpoints and evidence references. A shared list head
  is a context source, not necessarily the first act in the list. An annex and
  its approving act remain separate occurrences.
- Match parser occurrences to reference occurrences using source-local evidence
  and a predeclared deterministic alignment policy, independently of the field
  under evaluation. Never align only by date/number or choose the mapping that
  maximizes TYPE accuracy. Unmatched and ambiguous mappings remain visible.
- Legacy case mapping is zero/one/many, not assumed one-to-one. Derive a frozen
  projection only where the conversion is lossless and semantically valid;
  otherwise publish an explicit non-projectable reason. Never manufacture a
  human submission from parser or synthetic records.

### Measurement and optimization

Keep separate measures for detection, field values, provenance/relations,
abstention/ambiguity and exact whole-bundle correctness. Report raw counts and
explicit denominators. A missed endpoint cannot silently disappear from relation
recall; also distinguish end-to-end relation performance from relation accuracy
conditional on correctly detected endpoints. Exact bundle match is supplementary,
not a replacement for component diagnostics.

Report occurrence-weighted and bundle-level summaries separately so long series
do not silently dominate the result. Repeated text is not automatically the same
semantic case: document context can change resolution. Preserve occurrences and
report document/family clustering; do not count duplicates as independent evidence
of generalization. Empty denominators yield not-measured, not perfect accuracy.

Optimize annotation burden through shared context display, navigation, schema
validation and disagreement triage, not by exposing machine predictions in blind
coding. Measure time, navigation and unresolved reasons in a real pilot before
claiming a workload reduction. Bounded progressive context is possible only with
recorded source references, a frozen policy and equal access for both passes;
never expand context covertly for just one coder or the evaluated parser.

### First executable design experiment

Use synthetic-only examples of (1) a shared-head series, (2) an agreement referring
to a contract, (3) an annex with an approving act and (4) alias/this-document
ambiguity. Inject missing/extra occurrences, wrong field values, wrong relation
endpoints, conflicting provenance and unavailable context. Verify that each
measurement plane detects its own errors without concealing the others.

Synthetic expected records are engineering fixtures, not human-reviewed data.
Keep them outside frozen seed and submission stores. This experiment validates
the successor's representation and evaluator semantics, not legal correctness.
The exact successor schema, label inventory, alignment policy and pilot release
still require source-bound contracts and verification. Parser implementation
continues in M211; no frozen M207 gate or pin is discharged by this selection.

## Automated successor (D519) versus historical human protocol

Two scopes share this document's hybrid *direction*, not one evaluation class.

Historical frozen human protocol (unchanged; not S05 acceptance):

- S01 codebook, schemas, and the original 40 case identities
- S02 coder protocol, kits, and the empty human submission store
- S03 rater-vs-resolved-reference metrics; machinery-green remains
  `HUMAN_PILOT_ABSENT` / `MACHINERY_GREEN_HUMAN_ABSENT`
- S04 C4 operational non-pass and `REPORT_WITHOUT_HUMAN_DATA`
- Presentation, blinding, and denominator rules in the sections above

New automated S05 scope (no mandatory human evaluation):

- Versioned hybrid records envelope `m207-hybrid-records/v1`
- Python verification harness only (ADR-0007); no Rust product in this slice
- Provenance origin closed as `synthetic` or `rust-runtime` — never a fake
  human-reviewed record
- The envelope is **closed per level** and its honesty keys
  (`lifecycle`/`authoritative`/`is_gold`/`not_human`/`not_s03_metrics`/
  `alignment_policy`) are enforced against fixed values, so synthetic bytes
  carrying `is_gold=true` are refused with `MALFORMED_REF` rather than
  reported as a validated record
- First Rust series is exported and validated as records, not as a coder
  submission and not as S03 rates
- Synthetic experiment JSON (`m207-hybrid-synthetic-experiment/v1`) stays a
  separate evaluator fixture; parser records stay in
  `prd/parser/parser_record_contract.md`

D519 removes the human pilot as a **future** M207 requirement. It does not
rewrite historical S01–S04 evidence, mint gold, or claim S05 lifecycle complete
from this contract text alone.
