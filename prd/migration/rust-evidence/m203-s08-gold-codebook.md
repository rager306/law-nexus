# M203 S08 C5 Codebook

**Schema:** `npa-c5-gold-coding/v1`  
**Status:** `[bounded]` deterministic double-coding envelope; not accepted gold

## Coding unit

One unit is one annotation over decoded block text: `document_relative_path`,
`content_hash`, `block_index`, and a non-empty half-open UTF-8 byte span
`[start, end)`. Both endpoints must be character boundaries and `end` must not
exceed the block byte length. The label is closed and layer-qualified.

## Closed labels

- **Parsing:** `HierarchyLevel` values (`Razdel`, `Glava`, `Paragraph`, `Statya`,
  `Chast`, `Punkt`, `Podpunkt`) plus existing decode classes `Article`, `Point`,
  `EntersIntoForce`, `LosesForce`, `Obligation`, `Permission`, `Prohibition`.
- **Semantic:** `Actor`, `Action`, `Object`, `Polarity`, `Condition`, `Exception`,
  `TemporalQualifier`, `Abstention`.
- **Identity:** existing `FieldKind`: `Type`, `Org`, `Geo`, `Date`, `Number`, `Name`.
- **Temporal:** existing lexical kinds `EntersIntoForce`, `LosesForce`, and
  pairing labels `AsOfPairing`, `EditionPairing`, `Abstention`.

No label outside these sets is accepted. Labels remain candidates and do not
assert legal interpretation, applicability, identity resolution, or authority.

## Independent passes

The envelope requires exactly two non-empty passes. Each pass has a distinct
non-empty `coder_id` and `coder_profile`; profiles are independent deterministic
derivation paths and must use different evidence ordering/selection logic.
The product extractor is not a coder. Human replacement is represented by a
new `coder_profile`, never by mutating a prior pass.

Units match only on `(document_relative_path, content_hash, block_index, start,
end)`. Missing anchors, shifted/overlapping spans, and different labels are
fail-closed disagreements.

## Agreement and adjudication

`percent agreement = matched / total`. Nominal Krippendorff alpha uses the
coincidence formula pinned by `krippendorff-nominal-two-rater-coincidence/v1`.
Perfect agreement is exactly 1; systematic disagreement is not positive. The
classification is always `proxy`, never exact human inter-coder agreement.

An adjudication returns a new envelope with an appended decision containing a
label and non-empty reason. Original passes and the prior envelope are
immutable; duplicate adjudications are rejected.

## Mandatory non-claims

`not_human_annotator_agreement`, `not_accepted_gold`, `not_legal_interpretation`,
and `vendor/full-walk_not_validated_gold` apply to every derived C5 artifact.
Full-corpus walks and vendor output are diagnostics only. This contract does not
close R035 or R070 and does not turn deterministic profiles into human labels.
