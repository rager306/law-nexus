# Model Crystal — Reviews 10–14 projection

**Status:** `[proposed]` documentation-only projection. **Non-canon.** This file
amends no ADR, promotes no lifecycle, mints no Rust type, closes no TSG row.
Part D candidates of the source stay candidates until human disposition G0
(ADR-0024 L2).

**Source (immutable L0):** `doc/review/review-25-08-2026.md` (Review 14,
consolidating Reviews 10–13 + external critique) —
sha256:c438ddfbe67181d439b5ed69a91e0adca833a9b84d26f1f2d85ea848070ea1b8
**Created:** 2026-08-20 at git HEAD `b4c0d33` (pre-G0 anchoring). After G0 and
P0 canonization, one mechanical pass re-grounds anchors onto ADR-0017/0018/0016
amendments and re-versions this file (see Grounding log).

**Verification:** governor check `model-crystal-anchors` (advisory `[bounded]`)
verifies the source digest and every `<!-- anchor: ... -->` quote below
verbatim against the L0 source. Drift = visible warning, never silent.

**Reading contract:** inject Layer 0 always; Layer 1 by topic; read the source
reviews only on demand via anchors. Cite IDs (`INV-02`, `AXIS-4`, `OP-T`,
`RES-OrderingConflict`) in task briefs and slice plans instead of pasting
review prose. IDs are navigation anchors of this projection, not new domain
vocabulary: no `prd/temporal-legal-model.md` §3 row is created or amended.

---

## Layer 0 — always-inject core

### MC-F. Formula

<!-- anchor: review-25 §A.2 "официальные доказательства (Evidence Vault)" -->

```text
Evidence Vault
+ append-only bitemporal ledger of LegalEventAssertion
+ typed amendment algebra (Instrument → Provision → MicroOperation → Effect)
+ deterministic amendment compiler
= projections: lossless CST (green) + semantic legal AST (red)
  + temporal structure / reference graph
+ deterministic checkout(legal_as_of, known_as_of, view_mode)
```

Target name: **Bitemporal Legislative Event Compiler with Persistent Legal
Syntax DAG**. Git is an analogy of useful properties (content-addressing,
Merkle root, structural sharing), not domain identity:
`hash ≠ ComponentId`, `path ≠ ComponentId`, `similarity ≠ identity continuity`.

Three hard «no» of the formula:

<!-- anchor: review-25 §A.2 "Snapshot ≠ commit" -->

1. **Snapshot ≠ commit** — a consolidated edition is an oracle/checksum
   (exam), never the source of history.
2. Extracted event ≠ legal fact — canon is a ledger of *assertions* with
   evidence span, status and `recorded_at`; late correction never rewrites
   past knowledge.
3. Projection ≠ truth — CST/AST/graph/slice are a deterministic fold of the
   ledger; root hash is reproducible; rebuild is equivalent.

### MC-AXES. Seven independent axes (anti-drift core)

| ID | Axis | Answers | Never answers |
|----|------|---------|---------------|
| AXIS-1 | ComponentIdentity (opaque `ComponentId`) | which piece, forever | number/path (that is DesignationVersion), force |
| AXIS-2 | TextVersion (CTV) | which wording between strikes | force, applicability |
| AXIS-3 | OperativeMembership | in the operative tree at t? | force by text, documentary presence |
| AXIS-4 | DocumentaryPresence | Tombstone / Present / Absent | legal force |
| AXIS-5 | ForceStatus (interval set) | InForce / NotYetInForce / Suspended / Repealed / … | text, applicability |
| AXIS-6 | TransitionConstraint | for which old relations the old version still applies | slot resurrection |
| AXIS-7 | Reference Mention/Binding/Semantics | who cited what, binding, mode | `amends`, target force, editorial re-pointing |

<!-- anchor: review-25 §A.3 "DocumentaryPresence" -->

Inequalities (verbatim, unsimplifiable):

<!-- anchor: review-25 §A.3 "TransitionConstraint" -->

```text
текст существует        ≠  действует
принят/опубликован      ≠  вступил в силу          (vacatio: 44-ФЗ ст. 114)
действует               ≠  применим к делу         (ADR-0023)
компонент существует    ≠  входит в состав
ссылка существует       ≠  цель действует
Repealed-цель           ≠  сломанный биндинг
публикация              ≠  система знает
```

### MC-INV. Metamorphic acceptance invariants (INV-01..INV-10)

| ID | Invariant (one line) |
|----|----------------------|
| INV-01 | Repeated replay → same root hash. |
| INV-02 | Permutation of independent events does not change the snapshot. |
| INV-03 | Permutation of dependent events is forbidden or `OrderingConflict`. |
| INV-04 | Future effects never affect a historical checkout. |
| INV-05 | Assertion correction never rewrites the `known_as_of` past. |
| INV-06 | Changing a reference target does not change the source mention. |
| INV-07 | Changing source text closes the occurrence, may keep continuity. |
| INV-08 | Every snapshot node carries provenance or a typed Unknown. |
| INV-09 | Exact-text reconstruction reproduces the official artifact (via CST). |
| INV-10 | No `None` ever replaces a legally meaningful typed non-success. |

<!-- anchor: review-25 §C "Повторный replay → тот же root hash" -->
<!-- anchor: review-25 §C "Перестановка независимых событий не меняет snapshot" -->

---

## Layer 1 — inject by topic

### MC-PIPE. Pipeline 0→8

<!-- anchor: review-25 §B.1 "SourceArtifact + artifact_hash" -->

```mermaid
flowchart TD
    P0["0 act profile YAML"] --> P1["1 ingest official artifacts"]
    P1 --> P2["2 parse to candidates Proposed"]
    P2 --> P3["3 legal formula to micro-operations"]
    P3 --> P4["4 assertion ledger append-only"]
    P4 --> P5["5 deterministic compiler fold"]
    P5 --> P6["6 projections CST green AST red graph"]
    P6 --> P7["7 oracle exam scoped discrepancy"]
    P7 --> P8["8 bitemporal checkout"]
    P7 -.->|"discrepancy = parse gap, not photo erasure"| P2
```

Stage bans (full table in source §B.2): candidate ≠ fact; no rewrite-in-place
in ledger; no hidden side effects in compiler; no oracle-tree-back as canon;
checkout never serves "latest" and never substitutes `None` for typed
non-success.

### MC-OPS. Closed operation registry (P1)

<!-- anchor: review-25 §B.4 "Text:         ReplaceText / InsertText / DeleteText / SubstituteRange / CorrectText" -->

| Family | Operations (names only) |
|--------|------------------------|
| OP-T (Text) | ReplaceText, InsertText, DeleteText, SubstituteRange, CorrectText |
| OP-S (Structural) | Attach, Detach, Move, Renumber, Redesignate, Split, Join, ReplaceStructure, ReserveDesignation |
| OP-F (Force) | Commence, Suspend, Resume, Repeal, Expire, Invalidate, Restore |
| OP-P (Prospective) | ScheduleEffect, ModifyPendingEffect, CancelPendingEffect |
| OP-L (Table/List) | InsertEntry, DeleteEntry, SplitEntry, MergeEntries, ReclassifyEntry |

Every operation carries: target selector, expected base version,
precondition, payload, effect selector, scope, postcondition, evidence span.

### MC-RES. Typed apply results (closed set)

`Applied | TargetNotFound | AmbiguousTarget | PreconditionMismatch |
BaseVersionMismatch | OrderingConflict | UnknownEffect |
UnsupportedOperation | IncompleteSource`

<!-- anchor: review-25 §B.4 "OrderingConflict" -->

### MC-SEL. EffectSelector modes

At / AfterPublication / OnEvent / OnCondition / ForRelationsAfter /
RetroactiveTo / Unknown. These are projections of the five-clock roles
(ADR-0009), **not a sixth clock**.

### MC-DAG. Causal order — DAG, not queue

<!-- anchor: review-25 §A.6 "Instrument → Provision → MicroOperation → Effect" -->

```mermaid
flowchart TD
    I["AmendmentInstrument"] --> P["AmendingProvision"]
    P --> M["MicroOperation<br/>preconditions + effect selector"]
    M --> E["LegalEffect<br/>Text Membership Designation Force Reference Transition"]
    E -.->|"depends_on supersedes cancels modifies_pending_effect"| E2["LegalEffect"]
    M2["MicroOperation"] -.->|"non-commuting underdetermined = OrderingConflict"| E
```

Linear order is only a proven projection of the DAG; never order by act
number.

### MC-SEED. Seed = four different events

<!-- anchor: review-25 §A.5 "EntryIntoForceEvent" -->

AdoptionEvent (created text) / OfficialPublicationEvent (authoritative
expression) / EntryIntoForceEvent(s) (per-component commence) /
ApplicabilityConstraint (out of this contour, ADR-0023). Default seed force:
`NotYetInForce` or `Unknown` — **never** automatic `InForce`. Text can already
be amended during vacatio (44-ФЗ art. 114 + 188-ФЗ).

### MC-REPEAL. Repeal = four axes, not detach

ForceStatus = Repealed; OperativeMembership = Absent; DocumentaryPresence =
Tombstone; TextAvailability = HistoricalOnly (last CTV stays citable). Child
cascade is a derived `RepealScope(parent, descendants=true)`, not physical
deletion of child ids.

<!-- anchor: review-25 §A.7 "HistoricalOnly" -->

### MC-ID. Identity floors

| Floor | Identity | Notes |
|-------|----------|-------|
| act | Work = number + date + authority (ADR-0016) | number alone is never identity |
| numbered component | opaque `ComponentId`; path/label/eId/wId = DesignationVersion | AKN wId/eId, ELI URI = compatibility projections (D046) |
| addressable unnumbered paragraph | `AddressableTextUnit` + `IdentityContinuityDecision` (SameComponent / SplitFrom / MergedFrom / ReplacedByNewIdentity / IdentityUncertain) | |
| word/phrase | version-local `TextAnchor` (token span + quoted_hash) | |

<!-- anchor: review-25 §A.4 "AddressableTextUnit" -->

### MC-LEDGER. Assertion lifecycle

<!-- anchor: review-25 §A.2 "Proposed/Validated/AuthoritativeInternal" -->

Statuses: Proposed / Validated / AuthoritativeInternal / Rejected /
Superseded, plus `recorded_at` and `asserted_by`. Correction = new immutable
assertion + rebuilt projection; never in-place rewrite.

### MC-CHECKOUT. Bitemporal checkout

<!-- anchor: review-25 §B.3 "Snapshot = fold" -->

```text
Snapshot = fold(
    assertions
    where recorded_at <= known_as_of
      and status in {Validated, AuthoritativeInternal}
      and effect_selector satisfied for legal_as_of
)
```

```mermaid
flowchart LR
    LA["legal_as_of"] --> C["checkout fold"]
    KA["known_as_of"] --> C
    VM["view_mode + scope"] --> C
    C --> OUT["view + root_hash + coverage<br/>+ applied / excluded_future effects<br/>+ conflicts + unknowns + provenance"]
```

Views: VIEW-Promulgated (authoritative text), VIEW-Operative (in force at t),
VIEW-HistoricalCitation (incl. repealed + tombstone), VIEW-Reference
(mentions/bindings/target states); VIEW-CaseApplicable — later, ADR-0023
runtime.

<!-- anchor: review-25 §C "PromulgatedTextView" -->

### MC-REF. Reference binding modes

Mention (span + wording in a specific CTV) / Binding (candidate or confirmed
target + evidence + status; a successful binding is not destroyed by a
Repealed target) / Semantics modes: IdentityAmbulatory / DesignationLiteral /
FixedExpression / AsOfSpecifiedDate / EventRelative / **Unclassified
(default)**.

<!-- anchor: review-25 §A.8 "IdentityAmbulatory / DesignationLiteral / FixedExpression / AsOfSpecifiedDate" -->

### MC-GOLDEN. Golden list (P0 item 9, list only)

15–20 golden cases: vacatio (44-ФЗ/188-ФЗ), prospective effect, identity
collision, bitemporal correction, tombstone, ambulatory vs fixed cites, two
events on the same day. Semantic-shape oracles, not legal truth.

---

## Reality boundary (on crystal creation HEAD)

On HEAD there is **no** ledger, no compiler, no CST, no bitemporal checkout,
no resolver phases 2–3, no `NotYetInForce` in runtime. Present: oracle-anchored
assembly `S_ready_bounded` (drift=0), mention phase 1 `[bounded]`, YAML edge
vocabulary, `amends` constructors, bounded force-timeline in `ln-temporal`.

<!-- anchor: review-25 §Non-claims "NotYetInForce" -->

## Non-claims

- This file is a projection. It does not accept the model (G0 pending), does
  not amend ADR-0016..0023, does not close TSG-002/003/012/013/017, does not
  move `fsm.current` / O3 / TSG-017 S4.
- IDs are citation anchors of this projection, not glossary rows; no public
  contract or Rust type may be inferred from them.
- Mermaid diagrams are shape aids; the algebra lives in the source and in the
  tables above.
- The governor check is advisory (`warn`); it never blocks and never promotes.

## Grounding log

| Version | Date | Anchored to | Source digest | HEAD |
|---------|------|-------------|---------------|------|
| v1 | 2026-08-20 | review-25 (pre-G0) | sha256:c438ddfbe67181d439b5ed69a91e0adca833a9b84d26f1f2d85ea848070ea1b8 | b4c0d33 |

Next entry: v2 after G0 — anchors move to ADR-0017/0018/0016 amendments in one
mechanical pass; governor warns about stale anchors until then.

<!-- anchor: review-25 §Non-claims "Git не хранится" -->
