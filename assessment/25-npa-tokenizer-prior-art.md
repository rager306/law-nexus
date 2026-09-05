# NPA tokenizer / LawRef FSM — prior-art research and metrics framework

Status: research record for the M198 planning wave (corpus-scale lexicon
validation → N2 LawRef FSM). Sources verified 2026-09-03 via Consensus MCP
(peer-reviewed) and web (standards, implementations). Companion to
ADR-0028; does not modify any lifecycle status.

## 1. Sources

Scientific (Consensus search, peer-reviewed):

- Cushman Jr. et al., "eyecite: A tool for parsing legal citations",
  J. Open Source Softw. 2021, DOI 10.21105/joss.03617 — open-source citation
  extractor (Free Law Project), tested on 55M+ citations, runs CourtListener
  and Caselaw Access Project annotation.
- Waltl et al. 2018, "Rule-based Information Extraction: Advantages,
  Limitations, and Perspectives" — canonical rule-based legal-IE trade-off
  analysis (39 citations).
- Pinto et al. 2023 (WCGE) — head-to-head ML vs rules on official-gazette
  legal-entity recognition: for formally structured documents rule-based IE
  is lower-cost, simpler, and more efficient.
- Artstein & Poesio 2008, "Inter-Coder Agreement for Computational
  Linguistics", Computational Linguistics (1,873 citations) — annotation
  agreement mathematics (Krippendorff's alpha, Scott's pi, Cohen's kappa).
- Golev et al. 2025 — linguistic variation ("new variantology") in Russian
  normative acts, regional-law corpus.

Standards:

- Akoma Ntoso (OASIS LegalDocML) + Akoma Ntoso Naming Convention v1.0 —
  FRBR layering (Work / Expression / Manifestation), hierarchical `eId`
  identifiers (`art_2/par_3/sub_1/pnt_b`, dot-separated inside XML),
  global vs local IRI references.
- ELI (European Legislation Identifier) + ELI subdivisions spec v2 (AKN4EU):
  canonical identifiers vs *user references*; subdivision codes
  (art/par/sub/pnt/cpt/tis); rule that references to an article or anything
  below it start at the article level (continuous numbering — chapters are
  not part of a below-article reference path); FRBR-based ontology
  (LegalResource / LegalExpression / Format).

Implementations:

- eyecite architecture (tokenizers.py, models.py): regex **extractors**
  produce typed `Token` objects with `groups` dicts (volume/reporter/page…);
  token stream keeps a **covering invariant** (inter-match text is preserved
  as word/space tokens); overlaps resolved by sort `(start, -end)` + merge +
  specific-beats-nominative precedence; performance via Aho-Corasick
  prefilter or Hyperscan single pass; downstream `resolve_citations()`
  aggregates short-form / supra / id citations to antecedents; annotation
  re-inserts markup via diff-match-patch.

## 2. Approach model (what this means for law-nexus)

Three candidate approaches were modeled:

- **A. Rule / FSM corpus-calibrated (chosen, current course).** Typed lexer
  (M197, done) → LawRef FSM over token stream (N2) → act tree (N4).
- B. ML sequence labeling (CRF/transformer) over annotated corpus.
- C. Hybrid: rules first, ML fallback for the unknown tail.

Decision: **stay with A** for N2. Grounds: (i) NPA text is formally
structured — Pinto 2023 shows rules win exactly there; (ii) eyecite
demonstrates rules scaling to 55M+ citations with maintenance as the main
cost — our lexicon/lexeme tables already embody that maintenance;
(iii) B requires annotated data we do not have; our golden sidecar
(1,321 pinned spans) plus C1–C3 sweeps are the seed eyecite-style corpus
that could later train B (eyecite itself is used as an ML training-data
generator — same option stays open). C is the natural extension of A:
the unknown-token tail from corpus sweeps is precisely the ML-fallback
candidate list.

Direct architecture borrowings for N2 (LawRef FSM), from eyecite:

1. Extractor → typed token with named **groups** (our analog: LawRef fields
   `tome/article/part/point/subpoint` captured from the token stream).
2. **Resolution layer after extraction** — Russian anaphora equivalents of
   supra/id: «части 1–3 настоящей статьи», «пунктом 5 того же раздела»,
   short references «ч. 1 ст. 42» resolving against a document-context
   stack. This is a separate N2 stage, not lexer work.
3. **Annotation layer** — span re-insertion into the original text; our
   byte-exact `TextSpan` sidecar already provides the coordinate system.
4. Precedence table for overlapping matches (Date beats HierNum etc.)
   formalized as in eyecite's tokenizer — M197 does this ad hoc in the
   matcher order; N2 should expose it as data, not code order.

Standards alignment for the LawRef output schema:

- Model resolved references on **AKN eId semantics** (`art/par/sub/pnt`
  chain) — a ready canonical target schema, avoids inventing one.
- Keep the **ELI canonical-vs-user-reference distinction**: the text as
  written (user reference, "ч. 1 ст. 42") is what we extract; the resolved
  anchor (canonical path) is what resolution produces. Both belong in the
  LawRef object.
- Russian-specific rule to encode: article numbering is continuous, so a
  canonical path for below-article subdivisions starts at the article
  (mirrors ELI 5.4.1) — «ч. 1 ст. 42» → `art_42/par_1`, not
  `razd_X/glava_Y/art_42/par_1`.

## 3. Metrics framework (built for C1–C3 cycles and N2)

Layer 1 — corpus sweep (cycles C1–C3, no annotation needed):

- `marker_coverage` — share of unit-lemma tokens classified by morphology
  (the M197 pre-census metric: was ~59%, gap 243K markers).
- `unknown_rate` — unclassified tokens per 10K decoded tokens, trend across
  cycles.
- `lexicon_hit_distribution` — hits per abbrev id (drives D329 revision:
  the forbidden-9 verdict was made on a 122-file subset; the full 43,785-XML
  corpus may flip it).
- `shape_census` — HierNum/Date/DocNo/EnumMarker shape inventory (feeds №
  and format decisions).
- **Convergence criterion**: cycle over cycle, `Δmarker_coverage < 0.5 pp`
  AND unknown-tail composition stable (no new top-10 candidates).

Layer 2 — annotation quality (before N2 acceptance):

- Dual-annotate a stratified gold sample (per document type strata);
  agreement via **Krippendorff's alpha ≥ 0.8** (Artstein & Poesio;
  alpha-like preferred for multi-class token labeling).
- Token-level **span-exact precision/recall/F1 per TokenKind** against the
  sidecar (covering-invariant violations are hard failures — already
  enforced by the M197 loader).

Layer 3 — reference resolution (N2 acceptance, eyecite-style):

- **Resolution accuracy**: % of extracted references resolving to the
  correct canonical anchor (gold sample).
- Anaphora resolution accuracy for «настоящей статьи» / «того же раздела»
  class.
- Regression pin: pinned fz44 contracts stay green (statya-5 InForce,
  statya-93 Repealed, aggregate Fold 8 Unknown+conflict).

## 4. Plan impact (M198 shape, research-informed)

- S01: corpus sweep harness (streaming Rust bin over 43,785 XMLs,
  ConsultantWordMlBlockDecoder provenance, aggregate JSONL out) — C1.
- S02: corrections wave driven by C1 findings (lexicon/morphology TDD,
  D329 revision decision, № decision) — C2.
- S03: full re-sweep, convergence report against the Layer-1 metrics — C3;
  gate for N2.
- N2 (next milestone) starts with the gold-sample dual annotation (Layer 2)
  before any FSM code, per the metrics above.

## Non-claims

Consensus/keenable MCP results were used as literature pointers; no paper's
claims were adopted without reading the primary text where load-bearing
(eyecite whitepaper and AKN naming convention were read; Waltl and Pinto
abstracts only — sufficient for the rule-vs-ML direction, insufficient for
detailed technique borrowing). No lifecycle statuses changed.

## 5. Post-M198 audit (2026-09-03): implementation vs recommendations, metric tuning

Trigger: N2 gate PASS (D363); owner-directed audit before the N2 wave.

### 5.1 Implementation audit (lexer.rs 506 loc, morphology.rs 111, npa_sweep.rs 1049)

Recommendation-by-recommendation:

- Covering invariant: **implemented** (every `lex()` token consumes >= 1
  char; pos advances; sidecar loader enforces byte-exact reconstruction).
- Data-driven lexemes, longest-first, fail-closed parse panic: **implemented**
  (`NPA_ABBREV_IDS` + embedded-YAML `AbbrevEntry`, `OnceLock`).
- C2 Unicode fold with fail-closed contour: **implemented** (>= 2 alphabetic
  chars fold case; 1-letter lexemes lowercase-exact — hostile initials
  `Ч.`/`П.` stay Word+Punct, protecting the LawRef contour).
- Precedence as data (eyecite-style): **NOT yet** — precedence is the
  `lex()` match chain (whitespace → abbrev → enum-letter → lawcode → date →
  hier → docno → enum-digits → word → punct). Correct behavior today, but
  N2 must lift it into data (a precedence table) so Date-beats-HierNum etc.
  remain auditable when the FSM adds capture matchers.
- Token `groups` (structured capture, eyecite-style): **NOT yet** —
  `NpaToken` is kind+span+abbrev_id; HierNum segments (15.1 → [15,1]) are
  re-derivable but not captured. N2 needs a capture layer; do not retrofit
  `NpaToken` — a LawRef-level struct per D350 is the right home.
- LawRef schema stub: **absent** (expected; N2 scope).
- Resolution layer: **absent** (expected; N2 stage 2).

Verdict: no misimplementations found; the open items are exactly the N2
scope. The C2 fold contour (1-letter exact) is load-bearing for LawRef and
must be pinned by an N2 contract test (hostile initials must not become
references).

### 5.2 Metric tuning (Layer-1 corrections; Layer-2/3 unchanged)

- **D353 unit fix**: C1 artifacts carried a ppm field rendered as "240.53%"
  — inconsistent units across artifacts. D353 (percent of word tokens that
  are marker-class) is correct; the JSONL field name should be
  `marker_coverage_pct` going forward (cosmetic, batch with next render
  change).
- **Per-family coverage split** (new, required): C1 showed family dilution
  (fas 30,399 / courts 5,667 / xml 6,803 / npa 916). Corpus-level coverage
  mixes genres; N2 gates must read **npa-family coverage** as the primary
  number, corpus-level as secondary (the C2 npa-baseline sweep already
  implements the split).
- **Tail-stability index stays** (C3: 50/50 kept, 0/0 moved — gate passed).
- **Layer-2 (annotation)**: protocol = dual annotation of a stratified
  sample, Krippendorff alpha >= 0.8 (Artstein); rule-annotated pre-seed is
  legitimate but requires **noise assessment** (DS-NER latent-noise
  framework, Ding 2025) before alpha measurement.
- **Layer-3 (N2) metric set adopted from bundesrecht** (Darji et al. 2026,
  arXiv:2605.31338 — closest prior art; German statutory references):
  strict exact-match + micro-IE metrics over annotated references, plus
  **canonical-deduplication quality** (normalized references grouping
  surface variants — validates D350's ELI canonical/user duality
  empirically: bundesrecht shows normalized forms group real citation
  variants far better than string matching).

### 5.3 Additional pattern research for the Russian-NPA case

New scientific anchors (Consensus, 2026-09-03):

- **bundesrecht** (Darji, Heckelmann, Kratsch, de Melo 2026, arXiv:2605.31338):
  end-to-end pipeline parse → normalize → resolve → link for German federal
  statutes. Surface-form challenges map 1:1 onto Russian practice: compact
  combined references («п. 5 ч. 1 ст. 42» ≈ «§ 823 Abs. 1 BGB»), multiple
  targets, ranges («пункты 1 - 4.1» ≈ «§§ 1-2»), special abbreviations
  («i.V.m.» ≈ «в соответствии с»), lower-level units (Buchstabe ≈
  подпункт/буква). Their levels Absatz/Satz/Nummer/Buchstabe mirror
  ч./абз./подпункт/подпункт-"а".
- **RuLegalNER** (Shaheen et al. 2023): Russian legal NER dataset,
  rule-based expert annotation feeding RuBERT+CRF — precedent for
  rule-annotated seed + ML evaluation (our approach-A/fallback-B split).
- **Sukthanker 2018 / Mitkov 2020**: anaphora resolution survey baseline
  set for the N2 resolution layer (Russian «настоящей статьи» /
  «того же раздела» are document-scoped anaphora, best handled by
  document-context stack rather than general coreference models).
- **Ding 2025 (DS-NER, IEEE TKDE)**: latent-noise framework for
  rule/distant annotations — required before treating sweep-annotated
  spans as gold.

Russian-NPA surface patterns to encode in N2 (from C1/C3 tails + drafting
practice): uppercase single-letter markers `А)` `Б)` (old-GOST enum),
fullword tails `ст. 5 закона № 33-ФЗ`, date+number requisite blocks
(`от 27.07.2006 № 149-ФЗ`), quoted labels `подпункт "а" пункта 5`
(lexer already splits the quote), ranges `пункты 1 - 4.1`, currency `руб.`
(TokenKind decision: Word is correct; exclusion from tail by lexeme
allowlist, not by kind).

### 5.4 Additional-research verdict

Sufficient for N2. Coverage: pipeline architecture (eyecite, bundesrecht),
standards (AKN, ELI), Russian domain (RuLegalNER, Golev), methodology
(Artstein, Ding), trade-offs (Waltl, Pinto). Remaining unknowns are
project-internal (the gold sample and the npa-family split), not
literature gaps. No further research passes before the improving loop.

## 6. Prior-art addendum: O-RAG (Adamchic, LinkedIn 2026-08-26) — proof-required candidates

Source: Irina Adamchic, "Ontology GraphRAG (O-RAG): Building a Legal Knowledge
Layer Through Dynamic Schema Retrieval" (LinkedIn, 2026-08-26; self-described
non-academic experiment on the German Civil Code). Read in full; classification
follows the project convention: transferable ideas are proof-required
candidates, not validated architecture (see the Habr Legal RAG precedent).

### 6.1 What the article does

Neo4j LPG with an OntologyLayer (~400 class nodes from LKIF + Akoma Ntoso +
RICS, bge-m3-embedded, vector-indexed); per text chunk, the top-K ontology
classes from vector search become the dynamic `allowed_nodes` schema slice
for an LLM extraction call (LangChain LLMGraphTransformer, Mistral Large 2,
temp 0), replacing a static full-schema list that degrades above ~50 types.
2x2 experiment on 309 BGB chunks (language: German vs English-translated;
granularity: full paragraph vs 3-sentence windows): EN-trigrams wins 87.7%
of chunks, mean top-3 cosine 0.795 vs 0.700 baseline. Reported effects:
granularity (+0.076) dominates language (+0.024); max-per-window aggregation
beats summing (generic concepts stop ranking high); top-3 average preferred
over top-1 (top-1 tends to generic classes).

### 6.2 Known confound (visible in the article's own comments)

A commenter (Sarvex Jatasra) notes that shrinking the embedded unit raises
cosine scores by itself: the 0.795-vs-0.700 gap and the 87.7% win rate are
argmax over the same raw scores, so the comparison may reflect the length
confound rather than better schema SELECTION. The decisive question — do the
top-3 SLICES differ, or only their scores? — is unanswered. The author's own
limitations section concedes: cosine is a proxy for extraction quality; the
gold-standard human-labelled evaluation is planned but not done; single
document (BGB), single embedding model (bge-m3); chunks < 150 chars are
unreliable regardless of strategy.

### 6.3 Transferable candidates for law-nexus (all proof-required)

1. **LLM pre-annotation of the N2 gold sample with a schema slice.** O-RAG's
   schema-slice pattern could accelerate Layer-2 gold preparation: embed the
   candidate span + AKN/ELI class definitions (D350 vocabulary is the
   OntologyLayer analog), let an LLM propose class labels, human verifies.
   Precondition per D351: the human double-annotation and alpha >= 0.8 gate
   stay authoritative; the LLM pass is triage only, and its noise must be
   measured (Ding 2025 latent-noise framework, §5.2 of this assessment).
2. **Unknown-tail triage at scale.** Today the tail is 50 entries
   (hand-classifiable); if a future corpus pass grows it to thousands, the
   embed-and-rank triage pattern becomes economic. Not needed at the
   current scale — re-evaluate on trigger, not on schedule.
3. **Chunking guidance for any future RuVector indexing (ADR-0014,
   [proposed])**: 3-sentence windows + max-aggregation beat whole-paragraph
   embeddings; length asymmetry between query and index units matters.
   Relevant only if/when the graph-vector wave starts; do not pull forward.
4. **AKN-in-ontology confirmation**: the article's OntologyLayer embeds
   Akoma Ntoso classes — independent confirmation that D350's AKN eId
   alignment matches industry practice.

### 6.4 Non-transferable for N2

LLMGraphTransformer extraction, Neo4j serving, cosine-as-acceptance-gate,
and translation preprocessing: the law-nexus product pipeline is
deterministic (FSM), carries no LLM dependency (ADR-0004/0007), and its
acceptance gates are span-determinism plus human-annotated alpha — cosine
proxies are explicitly not acceptance evidence. The article's own
limitations section supports this boundary.

Verdict: no changes to the N2 plan; two candidate tools recorded
(LLM pre-annotation triage; tail-scale triage pattern) with explicit
preconditions. Re-evaluate the second on tail-size trigger only.

## 7. Addendum 2026-09-05 — Pullenti orientation and dual tokenizer

Owner-directed pause of the LLM bake-off. Diagnostic artifacts stay under
`/tmp/npa-judge-bakeoff/` (not tracked, not N2 evidence). Pullenti Lingvo
4.34 was snapshotted from https://www.pullenti.ru/Download into
`/root/vendor-source/pullenti` (C# SDK + HTML docs + Python SDK). GSD D380
/ D381; ADR-0028 dual-tokenizer / Pullenti / identifying subsections.

### 7.1 Pullenti (development orientation only)

License: Non-Commercial Freeware / Commercial Software. **Not product
runtime, not `lex()`, not CI, not a dual-coder, not Layer-2 gold.**
Take the attribute alphabet: `DecreeReferent` slots TYPE / SOURCE / NUMBER
/ DATE / NAME; `PartToken.ItemType` for structural units; `ThisDecree`
(`HasThisRef` / `HasOtherRef`) for anaphora to the current act. Two
contours: structural chain vs identifying act. After `PersonAnalyzer`
init (required: `MailLine.parse` → `PersonItemToken.local_ontology`;
without it Decree crashed on ФЗ lists / prikaz and undercounted cover F1
0.56), diagnostic cover F1 0.82 P=0.99 R=0.70 on the same 40. That is a
harness fix, not a new corpus. Agnes→sol identifying-prompt cover F1 0.95
is still triage only.

Do not port `DecreeAnalyzer` (6843 lines), `DecreeChange*`, MorphEngine,
or lump prikaz+ukaz+rasporyazhenie into one `Order` kind. Take **slots**,
not occurrence spans: Pullenti joins `ред.` + title + `(далее …)` into
the Decree surface and prefixes DECREEPART with the clause chain.
`SOURCE=город Челябинск` on «челябинского УФАС» is collapsed
ORG+GEO — **split, do not drop GEO** (D382). GEO is jurisdiction of the
issuing organ (subject/city/municipality), load-bearing for non-federal
identity; STREET/ADDRESS is a location contour. `ORGANIZATION.GEO` is the
honest pairing.

### 7.2 Identifying spans and CurrentDocumentRequisites

Metodrekomendatsii-2021 §19 and RusLawOD: an act is identified by type +
date + number (+ issuer for agency documents). Score **cover**, not overlap.
Do not expand the 180-fragment sample. Requisites of the *current* document
feed capture/resolve and any LLM metaprompt; `lex(&str)` stays metadata-free.

### 7.3 Dual tokenizer (living)

`lex()` covering nine-kind stream is the LawRef text view. Private
`tokenize()` remains alphabetic for references / temporal / unknown_forms
(`ст. 5` → stem `ст`). Morphology reads covering **Word** tokens only so
fullword markers (`статьи`, `пункта`) share the same scanner as LawRef
without collapsing Abbrev stems. A 1:1 `tokenize`→`lex` Word projection
is rejected until alphabetic consumers are rewritten over `TokenKind`.

Russian code/data that informed the alphabet but is not shipped: RusLawOD
(CC-BY-NC extras), Dedoc FOIV vs simple-law trees, RuLegalNER (PERSON/ORG,
not requisites).

### 7.4 Clip is the input, not the model (ident40 raw log, 2026-09-05)

The 180 Layer-2 units are Consultant WordML **blocks**, not semantic
windows. Amendment lists are split on commas across `source_block_index`:

- npa-doc-020: 086 `(в ред. Постановлений Правительства РФ от 25.12.2014 N 1489,` + 087 `от 14.04.2017 N 446)` — same list, type only in 086; document head is 085 `Постановление Правительства РФ от 26.08.2013 N 728`.
- npa-doc-022: 096 opening NP + 097/098/099 elliptical `от DATE N` tails.

Feeding 087/099 to an LLM as a standalone document is asking it to invent
type+issuer. Spark DROP on 087 is more honest than sol KEEP of a clipped
date+N. Pullenti emits DATE only (no DECREE) — correct for that window,
wrong if identity is supposed to inherit from the previous block / document
head. Filename and `CurrentDocumentRequisites` already hold type+issuer+date+N
of the *current* act; they never reached the model.

Pullenti on **unclipped** hard cases is the better identifier: 050 four-
ФЗ coordinating list (TYPE restored in slots, surface left elliptical);
078 prikaz+issuer; 120 license+Rosgvardia; 128 Plenum+VS. Do not copy its
spans. Next product join is not another bake-off: left-context / requisites
sidecar into `capture_lawrefs` / resolve so elliptical `от DATE N` inherit
TYPE+ORG+GEO from the opening NP or the document head (D382 cycle in
`prd/architecture/npa-identifying-cycle.yaml`). `lex(&str)` stays
fragment-local. GEO stays on the sidecar for regional/municipal keys.
