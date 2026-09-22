# M209/S01 punkt registry-admission decision checkpoint

**admission: not-adopted**
**recorded:** 2026-09-22
**milestone / slice:** M209-2yg6ix / S01
**classification:** source-bound punkt registry-admission checkpoint, fail-closed
**scope:** punkt as a registry admission identity only. The scope is the
`level: punkt` row family of `prd/architecture/kb-hierarchy-registry-admissions.yaml`
for three `document_groups` profiles: `federal_law@v1` (punkt ladder token, role
`subunit`, recursive, `max_depth: 2`), `government_resolution` (punkt is the
group granularity; ladder token role `unit`, recursive, `max_depth: 3`) and
`departmental_order` (punkt is the group granularity; ladder token role `unit`,
recursive, `max_depth: 4`). Out of scope: punkt as YAML granularity and ladder
token (validated, R087), fixture-scale ComponentConcept minting (validated,
R087), and punkt identities inside the 44-FZ registry projection (flat by
D192/D430).
**admission_basis:** No tracked owner admission that names a punkt registry
scope exists. D426 leaves punkt unadmitted until a separate tracked CC identity
decision exists; D192 keeps the 44-FZ registry flat (8 glava + 94 statya) and
D430 keeps R035 active with punkt named as a separate later wave; RC28-F16
requires punkt admission to carry its own decision before execution. The
admission source states in its own header "Punkt candidates stay unadmitted; no
ComponentConcept is minted here" (a comment-wrapped sentence: the raw file
breaks it between "Punkt" and "candidates" behind `#` markers, so the claim is
verifiable only after stripping comment markers and normalizing whitespace) and
carries 166 admission rows: 14
`level: glava`, 152 `level: statya`, 0 `level: punkt`. The registry projection
contains no punkt binding row. `m202-s03` reports `punkt_rows_admitted: 0`, and
`m202-s04` reports `mapping_counts.punkt_admitted: 0` with `admitted_cc` of
length 3. The candidate artifact does carry three nested punkt candidates
(`key_path` values such as `statya-4/punkt-1`), but candidates are explicitly
never admitted and never mint ComponentConcept identifiers, so a candidate
`key_path` is not an admission.
**owner_admission_ref:** none
**contract:** scripts/m209_s01_punkt_decision_contract.test.mjs
**punkt_admission:** not-adopted
**punkt_rows_admitted:** 0
**runtime_stop:** remains active for punkt registry admission; this record lifts
nothing.

## Purpose and boundary

RC28-F16 requires that "Punkt admission requires its own decision before
execution". D540 fixes what M209/S01 may lawfully do about that requirement:
record a separate source-bound decision surface with an honest fail-closed
verdict, and mint no authorization. This document is that surface.

`not-adopted` is the terminal lawful outcome of S01 T03, not a failure. The
fail-closed admission vocabulary forbids deriving an admission from YAML pins,
from an integrity PASS, or from a GSD lock, and no re-readable owner admission
for the punkt scope was found in the tracked corpus. Therefore the honest
recorded verdict is `not-adopted`, with `owner_admission_ref: none` and a named
resume condition, and `punkt_rows_admitted` stays `0`.

This record is a checkpoint, not a grant and not a decision. It is not an
approval, not a waiver, not a requirement closure, not a Review Case
disposition, not a legal conclusion, and not a lifecycle promotion. It does not
add a `level: punkt` admission row, it does not mint a `cc:` identity, and it
does not pre-authorize S02 (or any later slice) to admit punkt.

The grammar of this record deliberately matches the M208 admission checkpoints
(`prd/architecture/m208-s01-runtime-admission.md` and its S02-S04 siblings):
exactly one verdict line of the form `**admission: granted**` or
`**admission: not-adopted**`, parsed by the same expression
`/^\*\*admission: (granted|not-adopted)\*\*$/m`, plus bold header fields and
level-`##` sections.

## Sources checked

Each row is repository-relative and byte-bound: the recorded digest is compared
against the live file content by `scripts/m209_s01_punkt_decision_contract.test.mjs`.
Any later content change to a cited source invalidates this record and requires
a fresh checkpoint rather than an edit of the verdict here.

Quoted claims taken from comment blocks (the YAML headers) are normalized before
matching: comment markers are stripped and run-together lines are joined with a
single space. A literal substring test against the raw bytes of a line-wrapped
comment will not match the quoted sentence.

| Source | sha256 | What it records |
| --- | --- | --- |
| `prd/architecture/kb-hierarchy-registry-admissions.yaml` | `1707330b202d336046deaf4e94c3836bf8194d16b0f8b9e2fea3bd317ab94b19` | Canonical admission source for the kb-hierarchy registry projection (M202/S03, D426/D427). Header states "Punkt candidates stay unadmitted; no ComponentConcept is minted here" (comment-wrapped: the raw comment breaks between "Punkt" and "candidates"; normalize before matching) and "R035 stays active for S04". `lifecycle: "[proposed]"`, `authoritative: false`. The `admissions:` list holds 166 rows: 14 `level: glava`, 152 `level: statya`, 0 `level: punkt`. Its header also binds the candidate artifact by `candidate_artifact_sha256`. |
| `prd/architecture/kb-hierarchy-registry.yaml` | `6d7952b716b60d3b15ce302833323375e4964b70bb36b20a608331cfa3193c38` | The 44-FZ registry projection (8 glava + 94 statya bindings). It contains no punkt binding entry; the only occurrence of the token is the header comment recording "scope glava+statya only, Chast/Punkt stay Unknown (KBO-R042 precedent)", i.e. the D192 flat anchor. |
| `prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json` | `50946d813412315632214bdfe6f6300e5d5fa8372ab14900002ade2ded5adef6` | Candidate extraction artifact (schema `law-nexus-hierarchy-candidate-artifact/v1`, `lifecycle: "[proposed]"`, `authoritative: false`) whose digest the admissions header binds. Counts: 7 extracted, 6 unique, 1 duplicate, `by_level.punkt` 3 with nested `key_path` values. Its non-claims state that candidates never mint ComponentConcept identifiers and are "never admitted to the registry: admission is a separate human-gated step". |
| `prd/migration/rust-evidence/m202-s03-registry-regeneration.json` | `7d27652eafb410cab1b394830a2458aaa10815236e090e45badd8058e6049b0e` | Registry regeneration evidence. `output.punkt_rows_admitted` is `0`; the write/check modes are recorded with `check.bytes_unchanged: true` and `check.non_mutating: true`. Non-claims repeat "Punkt candidates stay unadmitted; key_path stays admission-source-only and is not rendered into the registry" and "Regeneration is not R035 validation; R035 stays active for S04". |
| `prd/migration/rust-evidence/m202-s04-r035-proof-gate.json` | `4e95a20e774fa9e551921922cedde7e6bcdd9fbdceb87d2c640ed5795859ca83` | R035 proof-gate record. `mapping_counts.punkt_admitted` is `0`; `admitted_cc` has length 3 (`cc:44-fz:glava-1`, `cc:44-fz:statya-4`, `cc:44-fz:statya-5`); `disposition: active` with `disposition_decision: D430` and `authoritative: false`; the seven `promotion_gates` all carry `gate_verdict: unsatisfied`. |
| `prd/architecture/kb-ontology.yaml` | `f6ee818296143047dce2543fc539dab009224c038ef867756d68e67ac25d47c4` | The document_groups catalog. `punkt` remains a declared hierarchy level and ladder token for exactly three profiles: `federal_law@v1` (granularity `statya`; token role `subunit`, recursive, `max_depth: 2`), `government_resolution` (granularity `punkt`; token role `unit`, recursive, `max_depth: 3`) and `departmental_order` (granularity `punkt`; token role `unit`, recursive, `max_depth: 4`). This is the granularity surface that stays valid (R087); it is not a registry admission. |
| `prd/architecture/capability-promotion-board.md` | `e8817c5940a8253a8668c47750b67f585804d476e7847994ca99f35845063eb5` | Promotion board. The "Punkt/subunit text-CTV axis (M172 S03, intra-S3 step)" entry records `PP_60` with YAML mint level `punkt` granularity, `ctv_resolved>0`, `membership_committed=0` and local fixture-CC only, and explicitly is "**not** a promotion to S4". The support-act table repeats punkt granularity for `government_resolution` and an inline-fixture proof for `departmental_order`. This is fixture-scale structure evidence, not registry admission identity. |
| `prd/architecture/review-cases/rc28-remediation-program.md` | `8ae51137a5ead37a761cff59e87d5a8747a348ee9b21ea0855bd60ca6b82232f` | The RC28 remediation program. It maps M209-2yg6ix to F16-F17 and records for F16: "M209/S01-S02,S04. Required proof: each R035 gate plus extractor/admission/regeneration; punkt decision before admission." |
| `prd/architecture/m206-s05-runtime-admission.md` | `ed7bac704a2184ff3f052f0065af99a76b2366c4f64e9f2892c6ba749f6b5751` | The tracked source-bound runtime admission that exists for this area. Its admitted scope is RC28-F06..F12 for M206/S05. It does not name a punkt registry admission, and it lifts `runtime_stop` for M206/S05 only, so it is not a basis for punkt. |
| `prd/architecture/m208-s01-runtime-admission.md` | `aad5f2800dfa7eaec61e79e364e80902af12b83617a22089bd576b3136e9b60e` | The M208/S01 admission checkpoint (RC28-F13), whose scope is local quoted change operands and the five local source operations. Its recorded verdict is `not-adopted` with `owner_admission_ref: none` and `runtime_work: not-started`. It is the grammar precedent for this record, and it does not name a punkt registry admission. |
| `prd/temporal-legal-model.md` | `a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6` | The living temporal/legal model. `punkt` and `podpunkt` are declared hierarchy levels, and the CC-path entry defines a recursive structural locator `cc:...:statya-93/punkt-4/punkt-4.2` as a `[proposed]` design term that is "not a new identity canon". So the punkt-shaped identity form is design vocabulary, not an admission. |
| `prd/architecture/assembly-pipeline-map.md` | `8f47368698fc0c4f2b7ce2a47e5a0753812d45e0fcb019c40acaaa25f02d1989` | The assembly pipeline map. The `S_bind` row keeps "Chast/Punkt/Paragraph of 44-FZ remain `Unknown` (own bounded wave); registry is a design inventory, not store types". The group table records punkt-unit granularity for `government_resolution` and `departmental_order` while the executed registry binds glava+statya only. |

Byte-binding inventory (derived restatement of the digests recorded above;
the table is authoritative for the contract):

```text
sha256: 1707330b202d336046deaf4e94c3836bf8194d16b0f8b9e2fea3bd317ab94b19  prd/architecture/kb-hierarchy-registry-admissions.yaml
sha256: 6d7952b716b60d3b15ce302833323375e4964b70bb36b20a608331cfa3193c38  prd/architecture/kb-hierarchy-registry.yaml
sha256: 50946d813412315632214bdfe6f6300e5d5fa8372ab14900002ade2ded5adef6  prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json
sha256: 7d27652eafb410cab1b394830a2458aaa10815236e090e45badd8058e6049b0e  prd/migration/rust-evidence/m202-s03-registry-regeneration.json
sha256: 4e95a20e774fa9e551921922cedde7e6bcdd9fbdceb87d2c640ed5795859ca83  prd/migration/rust-evidence/m202-s04-r035-proof-gate.json
sha256: f6ee818296143047dce2543fc539dab009224c038ef867756d68e67ac25d47c4  prd/architecture/kb-ontology.yaml
sha256: e8817c5940a8253a8668c47750b67f585804d476e7847994ca99f35845063eb5  prd/architecture/capability-promotion-board.md
sha256: 8ae51137a5ead37a761cff59e87d5a8747a348ee9b21ea0855bd60ca6b82232f  prd/architecture/review-cases/rc28-remediation-program.md
sha256: ed7bac704a2184ff3f052f0065af99a76b2366c4f64e9f2892c6ba749f6b5751  prd/architecture/m206-s05-runtime-admission.md
sha256: aad5f2800dfa7eaec61e79e364e80902af12b83617a22089bd576b3136e9b60e  prd/architecture/m208-s01-runtime-admission.md
sha256: a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6  prd/temporal-legal-model.md
sha256: 8f47368698fc0c4f2b7ce2a47e5a0753812d45e0fcb019c40acaaa25f02d1989  prd/architecture/assembly-pipeline-map.md
```

## Required decision fields

A future individual owner decision must carry each of the following fields
explicitly. None of them may be inferred from a design pin, from an integrity
PASS, from a GSD lock, from this checkpoint, or from a slice closeout; a grant
missing any listed field is not applicable and must be rejected rather than
completed by guesswork.

1. `verdict_line` — exactly one line matching `/^\*\*admission: (granted|not-adopted)\*\*$/m`.
   For a grant the value is `granted`; the value `not-adopted` records a
   checkpoint, not a grant.
2. `granted_by` — the owner interaction that grants the admission: an
   interaction id with a timestamp, or an authenticated subjective-UAT
   criterion id. A bare name, a role title, a milestone closeout or a GSD lock
   is not a grantor reference.
3. `scope` — the named `document_groups` profiles and the exact punkt level the
   grant covers: ladder token, role (`unit` or `subunit`), recursion flag and
   `max_depth`, for each of `federal_law@v1`, `government_resolution` and
   `departmental_order` where the grant applies.
4. `cc_identity_form` — the declared form of the `cc:` identifiers that would
   be minted for the admitted punkt rows (for example the
   `cc:work:statya-N/punkt-M` form named by R087), including the exact minting
   procedure and its human gate.
5. `admission_rows` — the exact rows to be appended to
   `prd/architecture/kb-hierarchy-registry-admissions.yaml`, each with
   `path_needle`, `number`, `key_path` and `provenance`.
6. `declared_denominator` — the denominator the grant is scored against: the
   act plus the number of candidates considered. An inventory counter
   (`registry_rows`, `legacy_human`, `candidates_extracted`, `fz44_glava`, ...)
   does not satisfy this field.
7. `selected_gates` and `deferred_gates` — which R035 gates the grant claims
   and which stay deferred, by `GATE-*` identifier.
8. `sources_checked` — byte-bound rows: repository-relative path with a
   recorded `sha256:` for every source the decision read, each of them tracked
   and none of them ignored or absolute.
9. `fail_closed_boundary` — the code set the decision contract must keep
   rejecting, restated for the granted case.
10. `non_claims` — what the grant still does not claim, including that it is
    not a legal conclusion and not a lifecycle promotion.
11. `owning_surfaces` — the repository surfaces that own the minted concepts
    and the admission rows (paths, not prose), so the grant is actionable
    without re-deriving scope.
12. `supersede_rebind` — the clause that this checkpoint is superseded by the
    grant and that the grant re-binds the hashes of every source it cites.

## Resume condition

Punkt registry admission becomes permitted only when a new source-bound owner
grant appears in the tracked repository and names: (a) the punkt scope by
`document_groups` profile and punkt level, (b) the admission rows to be added
with their `path_needle`/`number`/`key_path`/`provenance` and the declared
`cc:` identity form, and (c) the declared denominator (act plus candidate
count). The grantor must be identified by an owner interaction id with a
timestamp or an authenticated subjective-UAT criterion id, and it must be
byte-bound to the sources it cites.

Once such a grant exists, a fresh checkpoint supersedes this document and
re-binds the `sha256:` digests of every source it cites; the verified-and-green
state of `scripts/m209_s01_punkt_decision_contract.test.mjs` is then re-pointed
at the new verdict by that fresh checkpoint. As of 2026-09-22 no such grant
exists, so the resume condition is unmet and the verdict stays `not-adopted`.

## Fail-closed boundary

`scripts/m209_s01_punkt_decision_contract.test.mjs` must reject each of the
following conditions with its own named code, empirically, against a mutated
copy of this document or of a cited source:

- verdict shape: `verdict_missing`, `verdict_ambiguous`, `verdict_not_adopted`,
  `section_missing`.
- minting from a non-decision: `self_minted_adoption`, `contract_pass_as_admission`,
  `integrity_pass_as_admission`, `lock_as_admission`,
  `metric_baseline_relabelled_as_admission`.
- cross-slice authorization: `s02_preauthorized`, `s02_punkt_admission_authorized`,
  `cross_slice_authorization_granted`, `punkt_admission_gate_claimed`.
- owner provenance: `owner_admission_ref_missing`, `required_decision_fields_missing`.
- sources: `sources_insufficient`, `source_unresolved`, `source_not_tracked`,
  `source_hash_mismatch`, `ignored_path_as_source`, `absolute_path_as_source`.
- punkt facts: `punkt_row_admitted_without_decision`, `punkt_rows_mismatch`,
  `admitted_cc_mismatch`, `denominator_missing`.
- frozen-input drift: `m202_s03_modified`, `admissions_yaml_modified`.
- semantics: `granularity_confused_with_registry_admission`, `r087_invalidated`.
- resume surface: `resume_condition_missing`.

Note for the contract author: required-field assertions must parse the anchored
bold field lines (`**field:** value`), not bare substring presence. The code
names listed in this section (for example `owner_admission_ref_missing`)
themselves contain the field names, so a substring test can never fail closed;
only an anchored match of the field line is evidence.

## Marker semantics

The punkt contract prints its punkt-specific markers only after a fully green
run: `M209_S01_PUNKT_OK`, `M209_S01_PUNKT_NOT_ADOPTED`,
`M209_S01_PUNKT_ROWS_ZERO`, plus the key-value lines
`punkt_admission=not-adopted` and `punkt_rows_admitted=0`. These markers belong
to that contract's own run.

This document emits nothing. It is a recorded checkpoint, not a runner, and it
does not emit the M209/S01 slice verification marker; the slice marker is owned
by the S01 closeout, not by this record.

## Non-claims

- This document is a checkpoint: not a grant, not an approval, not a waiver,
  not a requirement closure, not a Review Case disposition, not a legal
  conclusion, and not a lifecycle promotion.
- No `level: punkt` admission row is added here; `punkt_rows_admitted` stays
  `0` and `punkt_admitted` stays `0`.
- S02 is not pre-authorized to admit punkt, and no cross-slice authorization is
  granted by this record.
- Punkt as YAML granularity and ladder token, and fixture-scale ComponentConcept
  minting, remain validated (R087) and are not inverted by this document.
- R035 remains `active` (D430). R070 is untouched by this document.
- The candidate `key_path` values in `m202-s02` are candidates only; they are
  not admission, not identity, and not evidence of a punkt registry binding.
- No corpus content, raw legal text, PII or secret is quoted here; sources are
  cited by repository-relative path and digest only.
- The PASS state of any contract, any integrity PASS, the D499 milestone lock,
  a milestone completion, or a GSD lock is not an admission and must never be
  read as one.
