# Glossary governance and coding injection

**Status:** `[bounded]` repository-control contract  
**Semantic lifecycle ceiling:** inherited from each owning ADR and glossary row  
**Authority:** `prd/ARCHITECTURE.md` and active `doc/adr/**`  
**Non-authority:** this document, the vocabulary catalog, Governor output, skills, assessments and `.gsd/**`  

## 1. Purpose

This contract defines how temporal/legal terms reach maintainers and coding
agents, how vocabulary changes are reviewed and which consistency defects the
Governor may report. It does not define legal meaning, generate product code,
close semantic gaps or promote lifecycle.

The terminology projection lives in `prd/temporal-legal-model.md` §3. Each
substantive meaning remains owned by its cited ADR. The machine catalog
`temporal-vocabulary-contract.json` is a complete inventory of the glossary
table and TSG identifiers, but is deliberately non-authoritative.

## 2. Injection into coding work

For work that changes temporal, parser, evidence, citation, retrieval,
applicability, practice, risk or profile vocabulary, the required read order is:

1. `prd/ARCHITECTURE.md` for the living boundary and lifecycle ceiling;
2. the owning active ADR for substance;
3. `prd/temporal-legal-model.md` §3 for canonical name, alias/status and
   fail-closed boundary;
4. the relevant Rust skill and verification matrix;
5. current Rust domain/port contracts and tests.

Agents and maintainers must carry a term into code only when an owning ADR and
an active Rust contract exist. A `deferred-undefined` or `runtime deferred` row
is a stop signal, not a type-generation request. Unknown terms are owner-routed
instead of being normalized by analogy.

The glossary is injected through tracked instructions, skills, review and
Governor diagnostics only. Product crates must not read the JSON catalog,
generate Rust enums from it or treat it as runtime/legal authority.

## 3. Update protocol

| Change class | Required owner/evidence | Required companion review | Governor boundary |
|--------------|-------------------------|---------------------------|-------------------|
| editorial clarification with unchanged meaning | owning ADR remains unchanged; reviewer confirms no semantic delta | glossary row, catalog fragments and affected skill wording | structural presence and deprecated-alias advisory |
| canonical rename or alias change | human ADR amendment/clarification | glossary row, catalog, living entrypoints, skills and migration note | advisory only; Governor cannot decide equivalence |
| new proposed term | accepted owning ADR plus explicit non-claim | glossary row, TSG row where proof is absent, catalog inventory | structure only |
| `deferred-undefined` to proposed contract | human disposition on schema/ownership | ADR, glossary, product/requirement trace and hostile proof plan | lifecycle-sync checks may expose drift; no auto-promotion |
| proposed to bounded/validated | required Rust/adapter/real-document proof and human acceptance | ADR lifecycle, oracle, requirements, evidence anchors and non-claims | existing lifecycle/freshness controls only |
| TSG closure | named owner and proof required by the row | gap disposition plus successor assessment when required | Governor cannot close the row |

A glossary-only edit cannot create a product capability. A catalog edit cannot
change meaning. If glossary and ADR differ, the ADR wins and the projection must
be repaired.

## 4. Deterministic versus heuristic control

Governor may deterministically verify:

- catalog/schema readability and `authoritative: false`;
- complete one-to-one inventory of glossary table rows;
- exact inventory continuity of TSG identifiers;
- required row fragments and lifecycle/status markers;
- working-tree companion freshness.

Governor may only warn heuristically about:

- unqualified deprecated aliases on a bounded path allowlist;
- a deferred term presented with an implementation/publication cue;
- a sixth-clock-like label without a five-clock/projection qualifier;
- a static interval field presented with a strong source-truth cue;
- skill wording that appears stronger than the glossary ceiling.

The token, cue, qualifier and tracked-path policy for these presentation checks
lives in the non-authoritative vocabulary catalog rather than Python harness
source. This preserves the ADR-0007 process/product boundary. Catalog schema or
policy parse failures are tool errors; findings remain advisory and require
human disposition.

Heuristic findings require human disposition. They are non-blocking by default
and must not be converted into legal or semantic approval when absent.

Governor must never decide:

- legal equivalence of two terms;
- correctness of a date, applicability result or normative state;
- whether a disputed source span is gold;
- representativeness or metric thresholds;
- lifecycle promotion or TSG closure;
- whether a future `SourceBlock`, `EvidenceSpan`, NormRule or applicability
  schema should exist.

## 5. Current bounded debt

- `EvidenceSpan`, future `SourceBlock` and `edition_date` remain
  `deferred-undefined`.
- Applicability is a canonical design term while runtime remains `[deferred]`.
- `NormativeStatus` is a deprecated compatibility alias for canonical
  `NormativeState`, not a second dimension.
- The temporal model remains a `[proposed]` crosswalk, not the complete
  executable temporal contract requested by the 2026-08-11 assessment. Its
  fourteen-area completeness matrix must preserve `partial`, `absent` and
  `deferred-undefined` cells until governing decisions and executable proof exist.
- Skills may be absent in a clean clone; tracked process controls cannot claim
  full skill-surface coverage from local-only files.

## 6. Acceptance and non-claims

A green vocabulary check means only that the tracked rows, markers and gap IDs
remain structurally visible. It does not establish semantic completeness,
product implementation, legal correctness, parser quality, applicability,
citation safety or lifecycle readiness.

<!-- continuity-contract cross-check: gap-register disposition vs review residual -->

<!-- capability-promotion-board cross-check -->

<!-- TSG-003/013 S3 apply companion -->

<!-- TSG-004 force resolver companion -->

<!-- kb-ontology O1 companion -->

<!-- join_force_with_membership O2 companion -->

<!-- FRBR mint_work KBO-R011 S2 companion -->

<!-- ln-kb-ontology write-set companion -->

<!-- fold_membership_at StructuralAst companion -->

<!-- fold_expression_presence KBO-R023 companion -->

<!-- map_hierarchy_marker KBO-R024 companion -->

<!-- kb-ontology.yaml FSM catalog companion -->

<!-- decode_level_aliases KBO-R026 companion -->
