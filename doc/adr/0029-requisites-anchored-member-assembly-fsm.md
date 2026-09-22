---
id: ADR-0029
title: Requisites-anchored member-assembly FSM for NPA reference capture (M207 model)
status: Proposed
lifecycle: "[proposed]"
date: 2026-09-18
supersedes: none
related: [ADR-0028, ADR-0027, ADR-0016, ADR-0019, ADR-0020, ADR-0013, ADR-0004]
---

# ADR-0029: Requisites-anchored member-assembly FSM for NPA reference capture (M207 model)

## Status

**Proposed [proposed]** — design decision for the future Rust implementation
of reference capture. No Rust engine code has landed for this layer; the
evidence base is the M207 Python prototype (`scripts/m207_context_graph_demo.py`)
and corpus-scale censuses described below. Demo-only evidence does not close
product requirements and does not promote any claim beyond `[proposed]`
(R035-class honesty).

## Context

Facts from the M207 prototype sessions (45 iterations; gold battery of 40
 Consultant/Garant editions from
`prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json`; corpus
censuses over ~43k XML files and ~430k parsed members; raw orphan rates
npa 6,4% / fas 7,6% / courts 24,5% / xml.law 1,2%):

1. **Requisites anchors are unambiguous; attachment is the hard part.**
   `date + N` pairs identify candidate members with near-zero ambiguity
   (P1). The hard problem is attaching the TYPE slot (nearest preceding
   marker without crossing another anchor), the issuer, and the approver —
   narrower than a morphology-first token pipeline (ADR-0028 supplies the
   lexer and LawRef spans; assembly sits above them).
2. **The monolithic TYPE_HEAD regex is at its limit** (~60 alternation
   branches): greedy run-ons needed stop-words, case-sensitive capitals
   `(?-i:)`, bounded dot-free gaps, and title-stem blocks. A lexicon must be
   data, not code (P2 of the pattern catalogue below).
3. **Greedy cross-date attachment steals types across two acts in one
   paragraph** («жалоба от … N 1, направленная … Постановления от … N 16-П»).
   Gold series tails («в ред. … от N 59, от N 29, от N 32») depend on
   same-paragraph inheritance, so inheritance cannot be disabled — attachment
   must be resolved as a hypothesis at paragraph end instead.
4. **Letterhead outranks body mentions.** Letterhead kind-words
   (РЕШЕНИЕ / ПРЕДПИСАНИЕ / ОПРЕДЕЛЕНИЕ / ПОСТАНОВЛЕНИЕ + «по делу N» /
   МЕЖДУНАРОДНЫЕ ДОГОВОРЫ), issuer letterheads, approver lines, and Минюст
   registration provenance form a document-head recognizer. The court-guard
   zone is the letterhead (first paragraphs), not the body: FAS RNP decisions
   citing «арбитражных судах» in body text were misclassified as court
   documents until the zone was narrowed.
5. **Work ≠ утверждающий акт (ADR-0016).** Named-annex members carry the
   approver citation, never the approver's Work. Нарицательные lowercase
   mentions («положением о закупках АО») are not named annexes — a
   capitalization gate on uncited annexes removes the noise class
   (fas uncited annexes −81/1000 files) without touching cited gold annexes.
6. **Fail-closed four-valued classification.** Every member lands in
   `identifying_act | hold | overlay | refuse` with axes (B legal_class,
   C competence, E issuer, F normativity, G binding, H admin) and an
   `identity_key` from `prd/architecture/npa-classification-axes.yaml`.
   Missing TYPE means `refuse` («узел не строим»); missing dest stays
   unprojected; N is never invented (P7).
7. **Quoted requisites in amendment prose** («слова "(далее - постановление
   … от 11 марта 2011 г. N 156, …)" заменить словами "(…)"») duplicated
   members until a `(date, number)` dedup preferring the typed copy. Per
   ADR-0019 these quoted requisites are ReferenceMentions, not Bindings;
   the member kind is carried from the amended document's head family.
8. **Judicial/FAS practice is overlay (ADR-0020).** Пленум ВС/ВАС,
   решения/постановления ФАС-УФАС «по делу N», ГОСТ/ИСО standards overlay
   the graph with `identity_key=overlay_not_rank|do_not_project`, never rank
   edges.

## Decision

1. **Anchor-first member-assembly FSM** `[proposed]` — the paragraph is an
   explicit state machine `Scan → Anchor(date) → AttachType → AnnexGate →
   Dedup → Buffer`, with hypothesis resolution at paragraph end
   (`ResolveHypotheses`) before linker passes. Transitions carry rule
   provenance (the Python `type_why` strings become trace records).
2. **Lexicon as data** `[proposed]` — TYPE/act/date/stop-word tables compile
   to an Aho-Corasick candidate finder plus small per-candidate validators;
   the monolithic regex alternation is retired. The lexicon sources stay
   tracked (`prd/architecture/npa-classification-axes.yaml`,
   `prd/annotation/m207-s01-codebook.md`).
3. **Hypothesis resolution** `[proposed]` — attachment hypotheses are kept
   per candidate until paragraph end; resolution prefers the typed copy,
   then nearest-preceding type without crossing another anchor. Same-
   paragraph series inheritance is preserved as the resolution outcome, not
   as eager state.
4. **Linker passes as pure functions** `[proposed]` — approver linking
   (windows ±450/700 chars, approver verb, «вместе с» lists), alias/short-ref
   resolution (scoped to declarations in the same document), this-document
   references, narrow context-carry clichés (each provenance-marked), and
   head-family carry for typeless quoted requisites.
5. **Letterhead recognizer with priority** `[proposed]` — kind-words, issuer
   letterheads, approver lines, «по делу N» case numbers, and Минюст
   provenance are recognized in the head zone; the recognizer result outranks
   body mentions. The court-guard zone is the letterhead paragraphs.
6. **Classification as an axes decision table** `[proposed]` — typed enums
   over the four-valued graph and axes; the table is data
   (`prd/architecture/npa-classification-axes.yaml`), fail-closed defaults.
7. **Work semantics per ADR-0016** `[proposed]` — annex members never merge
   with the approver's Work; quoted requisites are ReferenceMentions per
   ADR-0019 (head-family carry fills the ReferenceMention kind, never a
   Binding).
8. **Overlays per ADR-0020** `[proposed]` — judicial/FAS-practice members
   (`Пленум ВС/ВАС`, ФАС-УФАС «по делу», ГОСТ/ИСО) carry
   `overlay_not_rank | do_not_project` identity keys.
9. **Invariants audit as a first-class artifact** `[proposed]` — the six
   audit rules (identifying⇒B=npa; hold not on npa; overlay axis bounds;
   refuse⇒F≠yes; numbered⇒TYPE) run as a corpus gate, plus the gold
   40-edition battery as the test oracle (`chain=10, tails=56, orphans=0`).
10. **Prompt-FSM for the fail-closed residue** `[proposed]`, optional behind
    a feature flag — an LLM stage whose prompt is composed from the FSM's
    missing-slot state (exactly one slot per prompt, context window, allowed
    labels from the axes row); labels are accepted only after invariant
    validation and carry `provenance=llm`. Rejection lands back in
    fail-closed. Free-form LLM extraction stays out.

## Alternatives considered

- **Morphology-first token pipeline (full Pullenti-style)** — deferred:
  requisites anchors make token-NER unnecessary at this layer; ADR-0028
  already defers morphology until links/structure are stable. Pullenti's slot
  model and multi-hypothesis retention are adopted; its tokenizer is not.
- **Promoting the Python prototype to product** — rejected: product runtime
  is Rust-only (ADR-0004); the Python harness is the control plane (ADR-0007)
  and the prototype stays the executable spec.
- **LLM-first extraction** — rejected: fail-closed determinism is the
  contract; the LLM stage exists only as the validated residue FSM above.

## Consequences

- Deterministic, traceable identification: every member carries the rule
  provenance that produced it; the six invariants and the gold battery
  become CI gates.
- The regex retirement is real work: the lexicon tables and validators must
  reproduce the gold battery behavior before the regex path is deleted.
- The hypothesis buffer adds complexity to paragraph assembly but removes
  the documented cross-date steal limitation.
- Corpus censuses (per-corpus orphan rates and class buckets) become
  regression baselines; they are raw-parse metrics and do not include
  pipeline neighbor-inheritance.

## Evidence

- Prototype: `scripts/m207_context_graph_demo.py` (executable spec; control
  tables `СЛОИ/ЦЕПОЧКИ/КОНТРОЛЬ/DEST/КОДЕКСЫ БЕЗ N`).
- Gold corpus: `prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json`
  (40 editions); compact battery `chain=10, tails=56, orphans=0`.
- Axes and codebook: `prd/architecture/npa-classification-axes.yaml`,
  `prd/annotation/m207-s01-codebook.md`.

## Non-claims

This proposed ADR does not establish reference-capture correctness, parser
readiness, corpus completeness, or legal correctness, and it does not mint Rust
types or wire the FSM into any runtime. The prototype, the gold-sample manifest
and the chain/tail/orphan censuses are raw-parse diagnostics on fixture-sized
material, not gold-standard measures: they do not close R035 or R070, do not
authorize LLM/RLM runtime, whole-document recursion, cross-block anchors or
grammar-frame identity, and do not amend ADR-0028 or any earlier ADR. Human
adoption of the member-assembly vocabulary remains pending and is not implied by
this document.
