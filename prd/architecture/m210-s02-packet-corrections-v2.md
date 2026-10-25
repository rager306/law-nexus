# M210 S02 decision packet corrections v2

Status: correction record for the S02 owner-decision packet. It is
non-authoritative by itself: it changes no adoption state, lifts no
runtime stop, writes no Review Case event and touches no section 3 row.

## Lineage policy

This record follows RC28-F19: corrections append or explicitly supersede;
they never silently rewrite history.

- `prd/architecture/m210-s02-owner-decision-packet.json` (v1) stays
  byte-identical and stays hash-bound in
  `prd/architecture/m210-s02-adoption-checkpoint.md`.
- `prd/architecture/m210-s02-owner-decision-packet-v2.json` supersedes v1
  for any future re-presentation of the owner decision. It carries
  `supersedes.sha256` of the exact v1 bytes.
- `prd/architecture/m210-s02-owner-decision-presentation-v2.md` is the
  matching human-readable entry for v2.
- The checkpoint verdict `admission: not-adopted`, the active
  `runtime_stop`, `f13_status: hold` and `review_case_events_written: 0`
  are unchanged. A future adoption requires a real interactive owner
  reference, a verified governing surface and a NEW source-bound
  checkpoint that explicitly supersedes this one.

## Review input

Two external reviews (2026-09-24) plus a repository re-check at head
`f15612b2034ce71c9109326173c5e8a3b8a86b76`. Their accepted findings and
the repository verification are summarized in section 11 of
`prd/architecture/m210-s02-external-analysis-brief.md`.

## Correction map

| Correction id | Finding | Fix in v2 |
|---|---|---|
| verdict-semantics-split | candidate verdicts {Unknown, Conflict} were conflated with provenance link verdicts {resolved, unresolved, conflicted} | `verdict_semantics` block declares both domains and four separate dimensions; verified anchor never raises legal status |
| absence-semantics | absence of a record could be read as absence of a norm (misreading of variant A) | `absence_semantics` block: absence yields Unknown for every variant |
| c-rationale-minimal-surface | C rationale sounded like "the only safe representation" | rationale rewritten to smallest-new-surface and abstention-first staging |
| spine-status-prototype | NormRule spine presented as near-reusable model | `spine_status` block documents the four algebra defaults verified in `crates/ln-applicability/src/domain.rs` |
| probe-evidence-status | S01 corpus probes could be read as demonstrated extraction | `probe_evidence_status` block: coverage labels over [0,4096); anchors are review/glossary/gap-register |
| adoption-evidence-chain | UUID named as valid interactive ref without the authentication boundary | conduit requirements named: authenticated subjective-UAT criterion id, receipt bound to shown revision, separated acceptance roles |

## What does not change

- The question set: `m210-s02-ir-question` with options A, B, C,
  reject_all, defer, and the separate `m210-s02-f13-question`.
- Option labels and consequences texts (copied byte-equal from v1).
- The answer conduit requirements and the read-back discipline.
- v1 artifacts, the checkpoint, the gated dictionary delta and the
  section 3 pin `a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6`.

## Re-presentation requirements (unchanged, now on v2)

1. Run `node scripts/m210_s02_rebind.mjs --check` so the shown revision
   re-derives live per-input hashes.
2. Use an authenticated interactive conduit (subjective-UAT criterion id);
   a bare UUID is not proof of a human decision.
3. Read the answers back verbatim before anything is recorded.
4. Any adoption outcome requires a new source-bound checkpoint that
   supersedes the current `not-adopted` record.
