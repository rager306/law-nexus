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

### Dual tokenizer (living, 2026-09-05, D380/D381)

Two scanners remain in `ln-decode` on purpose. They are not aliases:

- **`lex(&str)`** — public covering lexer, closed nine-kind set, byte-span
  invariant (`text == concat(lexemes)`). LawRef capture/resolve and the
  corpus sweep consume this stream only.
- **`tokenize(&str)`** — private alphabetic splitter (non-letters are
  delimiters, lowercase, no covering). Still the input of
  `extract_reference_mentions`, `extract_temporal_phrases`, and
  `collect_unknown_forms_from_text`. On `ст. 5` it yields the stem
  `ст`; `lex` mints one `Abbrev{st}` and never a `Word`.

Morphology (`find_legal_markers`) reads **covering `Word` tokens only**
(alphabetic `Word`, spans from `lex`, lowercase, `ё`/`е` not folded).
It must not see Abbrev stems. Do not collapse the two scanners into one
call: a 1:1 `tokenize` → `lex` Word projection would drop `ст` from the
alphabetic consumers and is rejected until those consumers are rewritten
over `TokenKind` (not this ADR revision).

`lex` stays metadata-free (`&str` only). Current-document requisites
(kind, issuer, date, number, title, family) are a sidecar for capture,
resolve, and any LLM metaprompt — never lexer input (D381).

### Pullenti orientation (development-stage only, D380)

Pullenti Lingvo 4.34 (snapshot under `/root/vendor-source/pullenti`,
[Download](https://www.pullenti.ru/Download)) is an **attribute/FSM
alphabet**, not a runtime, not an N2 rater, not a dual-coder. License:
Non-Commercial Freeware / Commercial Software — do not copy into crates,
CI, or `lex()`. Take:

- identifying act = TYPE + SOURCE + NUMBER + DATE as written;
- two contours: structural chain (`PartToken` ≈ our seven matchers) vs
  act identity (`DecreeToken`) vs this-act anaphora (`ThisDecree`);
- closed type list (приказ/письмо/закон/…) as data for contour B.

Do not take: `DecreeAnalyzer` port, `Order` lumping of prikaz+ukaz,
`DecreeChange*`, MorphEngine/`m_ru.dat`, Instrument tree as LawRef.
Diagnostic cover F1 0.56 on the 40 identifying fragments is a codebook
calibrator, not a recall sieve (Agnes→spark cover F1 0.84 on the same
set remains triage-only).

### Identifying span / CurrentDocumentRequisites (D381)

User-reference span for an act includes document **type** and, for
prikaz/pismo/agency documents, **issuer**, copied from the fragment.
Truncated fragments without type/issuer stay date+N tagged `truncated`.
Score **cover** (pred fully covers gold), not overlap (truncated date+N
was a false TP). No new S01 slot without `schema_version`. Do not expand
the 180-fragment Layer-2 sample; N2 remains blocked on a second human
rater, not on corpus size.

LawRef FSM next: keep contour A (seven YAML matchers). Add contour B
(act type + issuer) and ThisRef as **data in the precedence/resolution
tables**, fed by a requisites sidecar — not by widening `TokenKind` and
not by shipping Pullenti.

### Identifying cycle and GEO (D382)

GEO is **kept**. For non-federal acts it is jurisdiction of the issuing
organ (subject / city / municipality), a sibling of ORG, not a substitute
for it. Pullenti `SOURCE=город Челябинск` on «письмом Челябинского УФАС»
is collapsed ORG+GEO: repair by splitting (ORG=УФАС, GEO=Челябинск),
do not drop the GEO half. `ORGANIZATION.GEO` (Управление, область
Воронежская) is the honest pairing. STREET/ADDRESS is a location contour
(торги, площадка), never jurisdiction. Federal TYPE (ФЗ, кодекс, указ
президента, постановление Правительства РФ) implies GEO=РФ; that default
is not an identity distinguisher.

The cycle is data in `prd/architecture/npa-identifying-cycle.yaml`
(`[proposed]`, no Rust types minted):

```text
decode blocks
  → CurrentDocumentRequisites (type, org, geo, date, number, title)
  → left-context of the previous enacting block (ellipsis inherit)
  → lex(fragment) covering, metadata-free
  → contour A: seven matchers (PartToken)
  → contour B: IdentifyingAct {type, org, geo, date, number}
  → ThisRef binds «настоящего Кодекса» to current_requisites
  → resolve: eId reverse + OfficialIdentityClaim
```

Identity key: federal `{type, number}`; presidential/agency
`{type, org, date, number}`; regional/municipal `{type, org, geo, date,
number}` — GEO is load-bearing only in the last. `LawRefSlots` stays the
eight S01 protocol slots; identifying attributes live on the sidecar.
Ellipsis `от DATE N` (WordML clip of one «в ред.» list: 086+087, 096–099)
inherits TYPE+ORG+GEO from the opening NP or the document head — clip is
the input, not a model hole.

### Enumeration (D383) — the ident40 weak link

Coordinating lists of acts and of structural units are the next FSM row,
not an LLM job and not an eighth S01 slot. Contour A today matches **one**
`Date+DocNo` or **one** `HierNum - HierNum`. It does not walk a comma list.

Pullenti almost does: on `npa-frag-050` four DECREE, `TYPE=ФЕДЕРАЛЬНЫЙ
ЗАКОН` inherited onto elliptical `от DATE N` tails; on `005`/`032`/`166`
two DECREEPART endpoints with `CLAUSE`/`ITEM` inherited (`частями 2.1` +
`2.3 статьи 19` → both PART carry CLAUSE=19). Models do not: sol glues the
three FZ into one span; spark writes TYPE onto tails that do not carry it;
Agnes empty-parses the fenced JSON; all three drop the lemma (`статьями
7.29 - 7.32` → `7.29 - 7.32`) and miss `часть 4` next to a quoted digit
range.

Take Pullenti's **role/value separation, per-member slots, and
inheritance**, not its occurrence spans. Source inspection refines the output
observation: Pullenti first holds the range in one multi-valued PartToken;
DecreeAnalyzer later expands values and copies the following CLAUSE onto both
DecreePartReferent endpoints. The Law Nexus written range therefore stays one
capture with `slots.range` endpoints; resolve expands the endpoint pair
(`range_policy: expanded_pair`), never `7.29, 7.30, 7.31, 7.32`. Data:
`prd/architecture/npa-identifying-cycle.yaml` `enumeration:`.

### Local reference grammar (D384)

The Pullenti advantage is above tokenization. Its pipeline keeps morphology
alternatives on TextToken, composes temporary DecreeToken / PartToken grammar
nodes, and only then assembles Referent slots. In an FZ list, one local `dts`
sequence (`TYP, DATE, NUMBER, DATE, NUMBER`) is cut into successive referents;
TYPE on the elliptical tail is semantic assembly, not rewritten source text.

Law Nexus adopts the separation, not the implementation. A design-only,
immutable `local_reference_grammar` plane sits after covering `lex` and
morphology evidence, before contours A/B:

- `MorphEvidenceSet` retains lemma/grammeme alternatives and unavailable /
  ambiguous states; it can constrain compatibility but cannot authorize
  inheritance or identity;
- fragment-local `CoordinatingFrame` groups explicit roles, values,
  separators, alternatives, and bounded expansion;
- `SemanticFieldClaim` records each explicit/inherited field with source,
  source anchor, compatibility basis, and conflict state;
- `StructuralDesignationFrame` keeps one written structural mention with
  multiple endpoint values and owner path.

Contour A continues to preserve literal ReferenceMention spans and the closed
eight-slot LawRef protocol. Contour B assembles compatible field claims into a
**proposed** IdentifyingAct. Resolve binds targets and expands endpoint pairs.
Grammar frames are not identities or ledger facts.

WordML continuation never creates one cross-block TextAnchor. Each block keeps
a local anchor; a typed `continues` edge carries evidence from an opening frame
to an elliptical tail. Inheritance order is explicit member, same-series head,
proven prior frame, then **authorized** CurrentDocumentRequisites. Conflicts
remain competing proposals; proximity does not decide. An ordinary cited-act
tail cannot become the current act merely because the sidecar exists.

No mutable token replacement, global analyzer initialization order, Pullenti
code/dictionaries, or arithmetic expansion of decimal legal designations is
adopted. Runtime remains blocked while member/expansion bounds are
`deferred-undefined`. Evidence and synthesis:
`assessment/26-pullenti-semantic-morphology-synthesis.md`.

### Deterministic recursive context (D385/D386)

The analyzer requires whole-document reach, but not a whole-document parser
input. A version-bound `DocumentStructureIndex` is the external addressable
context. Local frames emit closed typed `ContextRequest` dependencies; a
bounded worklist traverses structural edges, memoizes results, detects cycles,
and reduces provenance-bearing claims. This imports only the
externalize/decompose/query/reduce pattern associated with RLM-style long
context processing. **No LLM, RLM runtime, prompt, REPL, or recursive model
call is in the product path.** Details:
`prd/architecture/npa-document-context.yaml` and
`assessment/27-recursive-document-analysis-patterns.md`.

### Process, meta, prompt, and FSM boundaries (D387)

The canonical order and guards are data in
`prd/architecture/npa-semantic-process.yaml`. It is a phased document process,
not one item-state chain: DocumentReadiness, Mention, ContextDependency, and
Binding are orthogonal monotone FSMs. A captured literal mention survives
partial/conflicting/unavailable/cycle/limit context. Base source structure is
separate from the post-local-analysis overlay. OfficialIdentityClaim is
projected once before identity-based resolution; resolver consumes it and
never mints WorkId.

The product FSM is deterministic. Meta owns schema/lifecycle/policy/bounds and
evidence checks, but cannot create legal semantics. Prompt/meta-prompt is
out-of-band annotation only: `AnnotationSuggestion` cannot drive transitions,
create claims/bindings/identity, count as a second human coder, or validate
R035/R070. Audit: `assessment/28-npa-process-fsm-meta-prompt-audit.md`.

### Pre-runtime contracts (D388)

Three open D387 gates are explicit data/contracts. Contour-A direct/frame
arbitration uses only fragment-local spans and the eight closed LawRefSlots;
unknown overlaps remain conflicts, never source-function-order winners
(`prd/architecture/npa-capture-arbitration.yaml`). CurrentDocumentRequisites
keeps document-head, filename, and catalog claims separate through
normalization and conflict reduction; there is no global source precedence
(`prd/architecture/current-document-requisites.yaml`). All numeric list,
context, alias, candidate, and fan-out bounds remain `deferred-undefined`
until a reproducible streaming scan of the full Consultant export and hostile
contracts support them (`assessment/29-npa-bounds-hostile-plan.md`).

### D388 closeout refinement (2026-09-05, M200 S04)

The M200 S04 closeout artifact
(`prd/migration/rust-evidence/m200-s04-contract-reconciliation.json`; D402
select-or-defer, D403 runtime-stop/no-wiring, D404 closeout-pin placement)
refines the D388 pre-runtime contract with closeout evidence; the accepted
S03 outlier review
(`prd/migration/rust-evidence/m200-s03-outlier-review.json`, `[proposed]`)
is the only policy input, and the ADR decision status is unchanged:

- **Full Consultant walk accepted `[diagnostic]`, not `[bounded]`.** The
  complete streaming corpus scan is accepted at 43785 files attempted,
  0 malformed, 0 unreadable; this measurement acceptance stays
  `[diagnostic]` and is not `[bounded]` runtime evidence.
- **S03 review is `[proposed]` select-or-defer (D402).** G01 keeps the
  grammar-hard categorical invariants, G02 records a numeric safety ceiling
  1024 with refusal diagnostic `candidate_limit_reached`, G14 keeps the
  categorical arbitration default actions; the other 13 gates remain
  `deferred-undefined`.
- **1024 is a revisable `[proposed]` safety ceiling** with at least 2x
  headroom over the observed maximum 504; it is not a legal-structure
  limit, is never lowered to the observed maximum or a p999 bucket edge,
  and the product path `capture_lawrefs` stays unwired (D403).
- **`runtime_stop.active` remains true `[proposed]`** (D403) because frame
  pair_policies, the requisites extractor, context/alias/fan-out numeric
  bounds, the N2 gate, R035, R070, and a local grammar runtime are still
  open; this is assessment/29 section 10 step 7, not step 8 (re-scan after
  product-path wiring) or step 9 (clearing the stop).
- **Architecture YAML files remain lifecycle `[proposed]`**; R035, R070,
  and the N2 gate stay open; the R038 standing gate was executed in S03 and
  stays active; closeout transition pins for all of the above live in the
  dedicated `npa_bounds_closeout_contract.rs` suite (D404).

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
`assessment/25-npa-tokenizer-prior-art.md` (§7 Pullenti / dual-tokenizer addendum, 2026-09-05). Related gsd-pi defects FILED:
(a) `env_git_remote` false-negative -> open-gsd/gsd-pi#2129, (b)
compat-marker quarantine blast radius -> open-gsd/gsd-pi#2130; evidence
comments added to #2127 (coordination-claim redispatch loop) and #1491
(pre-commit-hook closeout swallow, reopen requested).
radius, (c) headless coordination-claim finalize errors.
