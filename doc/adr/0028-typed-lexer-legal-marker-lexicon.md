---
id: ADR-0028
title: Typed lexer and legal-marker lexicon for the NPA document engine
status: Proposed
lifecycle: "[proposed]"
date: 2026-09-01
supersedes: none
related: [ADR-0025, ADR-0027, ADR-0013, ADR-0024]
---

# ADR-0028: Typed lexer and legal-marker lexicon for the NPA document engine

## Status

**Proposed [proposed]** — the approach is owner-approved (workspace
placement, Apache-2.0 reserved on extraction, morphology deferred), no engine
code has landed yet beyond the bounded layers this ADR builds on
(`tokenizer.rs`, `morphology.rs`, M171 decode ladder, ADR-0027 templates).

## Context

Four verified facts from the 2026-08-30/09-01 model session (fz44 edition
walk, M196) and the NPA-engine review (assessment/24):

1. **The tokenizer is alphabetic-only.** `ln-decode/tokenizer.rs` splits on
   non-alphabetic characters and lowercases: `ст.` breaks into `ст`, and
   `15.1`, dates (`27.07.2006`), `№ 149-ФЗ` are not tokens at all. A typed
   lexer is a prerequisite for every reference- and structure-level feature.
2. **Free-text marker coverage is narrow.** `morphology.rs` (bounded, M131)
   knows only статья ×8 word forms and пункт ×10 plus deontic lexemes.
   глава/часть/подпункт/раздел have **zero** free-text forms. The decode
   ladder covers them only as nominative-case headings ×3 casings
   (`decode_marker_prefixes`) — correct for headings, silent for
   cross-references.
3. **razdel / natasha (MIT) and mawo-razdel (MIT fork) are news-domain
   split-then-rejoin segmenters.** In NPA text the period is usually not a
   sentence boundary: `ст. 15.1`, `п. 2.3`, `подп. "б"`, `от 27.07.2006`,
   `№ 149-ФЗ`, `в ред.`, `1.` / `а)` enumerations; the semicolon separates
   пункт lines. They also lack the document-structure layer entirely
   (статья → части → пункты → подпункты → абзацы per the State Duma drafting
   methodology), and Consultant/Garant editorial insertions
   (`(в ред. …)`) are a separate span kind, not ordinary text.
4. **Licensing.** razdel/natasha and mawo-razdel are MIT (fork with notice is
   formally clean); **UD Russian-SynTagRus is CC BY-NC-SA 4.0** — shipping
   its texts or patterns inside a commercial engine is a non-starter.
   Legal-marker word lists and abbreviation vocabularies are facts of legal
   drafting practice (юртехника), not razdel IP.

Acquisition path verified: the official publication section exposes a
**documented read-only JSON API** (`publication.pravo.gov.ru`: PublicBlocks,
Categories, document lists/files) plus RSS and PDF downloads; third-party
compiled datasets may carry CC-BY-SA — acquire from the official source
(official law texts are not copyrightable objects). Portal availability is
mediocre (state system, no SLA) — local caching and retries are mandatory.

Owner decisions (2026-08-31/09-01): `npa-*` modules live in this workspace
(extraction to a standalone Apache-2.0 crate reserved, not done); morphology
is deferred until links/structure are stable.

## Decision

1. **Bounded typed-lexer evolution inside `ln-decode`** — no parallel
   `npa-*` universe, no razdel/mawo fork. `TokenKind`:
   `Word | Abbrev{id} | HierNum | Date | DocNo | EnumMarker | LawCode |
   Punct | Space | Editorial`; byte UTF-8 spans (`text ==
   &src[start..end]`). `HierNum` (`15.1`, `2.3.1`) is one token.
2. **Legal-marker lexicon from legal drafting practice**, tracked as data
   with provenance next to `decode_marker_prefixes` in the ontology catalog:
   structural (`ст.`, `ст.ст.`, `ч.`, `п.`, `пп.`, `подп.`, `абз.`, `гл.`,
   `разд.`, `прил.`, `прим.`), requisites (`ред.`, `изм.`, `утв.`, `см.`,
   `ср.`), acts (`ФЗ`, `ФКЗ`, `ГК РФ`…), ambiguous (`г.` — year/city,
   context-resolved). Not sourced from razdel/mawo/SynTagRus.
3. **LawRef FSM** — the legal reference becomes a first-class span:
   `Ref := Marker HierNum (Marker HierNum)* (ActName)? (от Date)?
   (№ DocNo)? (Editorial)?`. It feeds ADR-0027 Layer 3 classification and
   the M186 hierarchy resolution (`map_hierarchy_marker`, fail-closed
   `Unknown`).
4. **Two explicit segmentation modes**: `clause` (complete clause for
   search/embeddings) and `list_item` (element after `;` or `:` + marker).
   They are different outputs; neither is called "sentence". Boundary rules:
   `.` after Abbrev/HierNum/Date/DocNo is not a boundary; `;` after a list
   item is a `list_item` boundary; `:` before a list closes the preamble;
   `?!` carry low weight in NPA text.
5. **Act tree is a bounded extension of the M171 decode ladder** — add
   preamble/annex/signatures as meta nodes; rules from the State Duma
   drafting methodology (2021) and Минюст guidelines, not from SynTagRus.
   Requisites and signatures go to `meta`, not to clause streams.
6. **Evaluation discipline**: golden fragments from official publications
   (30–50 acts), baselines regex-dot / razdel / mawo-razdel on the same
   set, metric = errors/1000 per unit type plus LawRef precision/recall.
   Not «+25% on news».
7. **Morphology deferral**: full inflection tables are generated offline
   with provenance (dictionary-backed) AFTER links/structure are stable;
   when added, the ё/е doublet (статьёй/статьей, запрещён/запрещен) is
   pinned by tests.
8. **Non-goals**: no SynTagRus or NC/SA corpora shipped; no ONNX/Python
   runtime dependencies; no razdel fork; no generic "join if lowercase
   follows" core (in NPA text an uppercase word after a period is often a
   continued reference); fallback heuristics must be logged, otherwise the
   engine degrades into razdel.

### Research refinements (2026-09-03, prior-art pass)

Prior-art research (`assessment/25-npa-tokenizer-prior-art.md`; eyecite
JOSS 2021, Waltl 2018, Pinto 2023, Artstein & Poesio 2008, AKN Naming
Convention, ELI subdivisions spec v2) refines the N2+ waves without
changing the decision:

- **Approach confirmed**: rule/FSM first for NPA text (formal structure);
  ML sequence labeling stays a fallback candidate for the corpus-sweep
  unknown tail (eyecite itself doubles as an ML training-data generator).
- **LawRef output schema aligns to AKN `eId` semantics** (`art/par/sub/pnt`
  chain) and keeps the **ELI canonical-vs-user-reference duality**: the
  text as written is extracted, the resolved anchor is derived. Canonical
  paths for below-article subdivisions start at the article (ELI 5.4.1).
- **Resolution layer is a separate N2 stage** after extraction: Russian
  anaphora ("части 1–3 настоящей статьи", "пунктом 5 того же раздела")
  resolves against a document-context stack, eyecite-style.
- **Metrics gates**: sweep cycles run until Δ`marker_coverage` < 0.5 pp with
  a stable unknown-tail; N2 acceptance requires a dual-annotated gold
  sample at Krippendorff's alpha >= 0.8 plus span-exact P/R/F1 per
  TokenKind and eyecite-style resolution accuracy.

## Consequences

- **Positive**: LawRef spans and the act tree become the admission pipeline
  for the temporal model — real acts feed the three-canon log (M190), C1
  admission (M191), the effect ledger (M192) and edition deltas (M196) with
  real identities instead of synthetic ones (the fz44 edition walk proved
  the model holds; the missing piece was exactly this real-document front).
- **Costs**: bounded lexer and automaton work; fallback logging discipline;
  headless v1.17.0 coordination-claim finalize failures
  ("Task Attempt claim must activate exactly one matching coordination
  dispatch") add an acknowledge step per affected unit until the gsd-pi
  defect is fixed.
- **Risks and mitigations**: portal availability — cache and retry;
  history: 2,478 artifact rows with foreign-relative paths poisoned the
  compat marker (compat hygiene check landed in M195); per-unit liveness
  wedges are acknowledged only through honest rechecks.

## Companion / control

`adr-contract-change` freshness trigger satisfied by the `doc/adr/README.md`
index row added in the same commit. Review record:
`assessment/24-npa-engine-review.md`; prior-art research record:
`assessment/25-npa-tokenizer-prior-art.md`. Related gsd-pi defects FILED:
(a) `env_git_remote` false-negative -> open-gsd/gsd-pi#2129, (b)
compat-marker quarantine blast radius -> open-gsd/gsd-pi#2130; evidence
comments added to #2127 (coordination-claim redispatch loop) and #1491
(pre-commit-hook closeout swallow, reopen requested).
radius, (c) headless coordination-claim finalize errors.
