# Pullenti semantic and morphology synthesis for the NPA reference cycle

**Date:** 2026-09-04  
**Status:** `[proposed]` design assessment; no Rust types or runtime claim  
**Scope:** Pullenti 4.34 architecture as NC/commercial prior-art orientation; no code, dictionaries, generated tables, thresholds, or runtime dependency are adopted

## 1. Finding

The coordinating-list weakness is not primarily a tokenizer defect.
Pullenti succeeds where the current seven LawRef matchers and LLM extraction
fail because it has four distinct planes:

1. a text-token chain carrying multiple morphological alternatives;
2. local grammars that compose temporary DecreeToken / PartToken nodes;
3. referent assembly that separates written extent from semantic slots;
4. analyzer context that can re-enter a coordinating tail and reuse a list head.

Law Nexus currently has (1) covering lexical evidence, a limited morphology
consumer, (3) direct contour-A capture, and resolution. It lacks an explicit,
immutable representation of (2). The minimum synthesis is therefore a **local
reference grammar** between `lex` / morphology evidence and contours A/B. It
must be a proposed derivation layer, not a second tokenizer and not an
identity layer.

## 2. Pullenti pipeline reconstructed from source

### 2.1 Morphology does not decide the entity

`MorphologyService.process` produces MorphToken records with a collection of
MorphWordForm alternatives. `AnalysisKit` wraps these in a linked TextToken
stream and performs token-chain normalization and contextual reduction of
some alternatives. TextToken copies all surviving word forms into a
MorphCollection. Local grammars query that collection; the morphological
result is evidence available to a parser, not a Decree or identity assertion.

This is the relevant reusable principle. The dictionary engine, binary
`m_ru.dat`, reduction heuristics, and exact grammeme implementation are not
reusable under the product and license constraints.

### 2.2 MetaToken is a local grammar node, not a lexical kind

Pullenti analyzers do not widen the primitive tokenizer every time they learn
a legal construction. Termin collections and parser helpers consume the
TextToken chain and create MetaToken-derived temporary nodes over begin/end
tokens. DecreeToken and PartToken are such local syntactic-semantic nodes.
ReferentToken is produced only after an analyzer assembles semantic slots.

This explains why `TokenKind` must remain closed in Law Nexus. The analogous
concept belongs above the covering token stream and must remain projectional:
it references source-local spans rather than replacing source tokens.

### 2.3 Coordinating acts are parsed as a list, then assembled in passes

`DecreeToken.try_attach_list` starts with a TYP token and appends DATE and
NUMBER items. Its comma-after-NUMBER branch accepts another DATE, and the
DATE-to-NUMBER branch continues the same `dts` list. Thus

```text
Федеральных законов от D1 N1, от D2 N2
```

is first represented as one local sequence approximately
`[TYP, DATE, NUMBER, DATE, NUMBER]`.

`DecreeAnalyzer.__try_attach` then assembles a DecreeReferent from that list.
When a second DATE is encountered after a complete first requisite group, the
assembler closes the first referent and processes the remaining tail. The
observed second referent has the list-head TYPE even though its literal span
starts at `от D2`. TYPE inheritance is therefore not tokenization and not a
surface-span rewrite; it is semantic assembly under a coordinating-list
context.

### 2.4 A structural range is one multi-valued local node

For

```text
частями 2.1 - 2.3 статьи 19
```

PartToken recognizes PART, collects multiple PartValue entries, and treats the
hyphen as an intra-node value separator under bounded numeric guards. The
following CLAUSE/ARTICLE owner is another PartToken role in the local part
sequence. `DecreeAnalyzer._try_attach_parts` enumerates combinations of the
multi-valued temporary nodes and creates endpoint DecreePartReferent records;
each endpoint receives CLAUSE=19. A later fallback copies a known clause from
the first result only when an assembled result lacks it.

The useful idea is not "split at a hyphen." It is:

- one written local mention;
- one grammar node with a role and several values;
- explicit ownership constraints;
- bounded expansion into several target-designation candidates.

Law Nexus should keep the written range as one ReferenceMention/capture and
produce endpoint bindings later. The endpoint candidates are not additional
source mentions.

### 2.5 Analyzer initialization failures are accidental coupling

PersonAnalyzer initialization populates analyzer data / local ontology used by
person-aware paths reached during Decree parsing. MailAnalyzer initialization
populates static termin collections such as MailLine.M_FROM_WORDS. Missing
initialization produces None dereferences rather than an explicit
"capability unavailable" result.

This is evidence against copying Pullenti's global analyzer registry. It is
not evidence that legal-act semantics inherently depends on Person or Mail.
A Law Nexus local grammar must declare its inputs and optional capabilities;
missing morphology, organization, or GEO evidence must yield a typed
unresolved/partial hypothesis, never a crash or silent global-order effect.

## 3. Mapping to Law Nexus planes

| Behavior | Owning plane | Must not own it |
|---|---|---|
| Lossless bytes and primitive classes | covering `lex(&str)` | morphology, resolver |
| Lemma/grammeme alternatives and their provenance | morphology evidence | tokenizer truth, identity |
| `TYPE + DATE/N, DATE/N` grouping | local reference grammar | LLM, primitive TokenKind |
| `PART values + CLAUSE owner` grouping | local reference grammar | integer range expansion |
| Literal local span and written wording | contour A / ReferenceMention | inherited slots |
| TYPE/ORG/GEO/DATE/NUMBER field claims | contour B assembly | surface-span mutation |
| Target binding and endpoint pair expansion | resolve | tokenizer/local grammar |
| Work identity | identity plane via OfficialIdentityClaim | grammar frame |

This preserves the model-crystal separation among mention, binding, and
semantics; source mention immutability (INV-06); provenance on derived nodes
(INV-08); candidate-not-fact discipline (MC-PIPE / MC-LEDGER); Unclassified or
unresolved defaults (MC-REF); and the distinction between natural-key claims
and opaque identity (MC-ID).

## 4. Boundary options

| Option | Benefit | Failure |
|---|---|---|
| Add comma/range logic directly to contour-A matchers | smallest diff | duplicates context logic, confuses mention with inherited fields, cannot represent morphology ambiguity or cross-block continuation |
| Recreate Pullenti's mutable MetaToken/analyzer pipeline | expressive, known behavior | port-shaped architecture, global initialization/order coupling, mutable source chain, license and observability risks |
| **Immutable local reference grammar + field-claim projection** | preserves covering lex, provenance, ambiguity, and bounded composition | adds one explicit design layer and needs contracts before runtime types |

The third option is recommended.

## 5. Design-only intermediate records

These names describe YAML records, not Rust types.

### `MorphEvidenceSet`

- `token_ref`: fragment-local covering-token reference;
- `alternatives[]`: lemma plus selected grammeme claims;
- `origin`: dictionary / rule / surface-only;
- `status`: available / ambiguous / unavailable;
- `evidence`: source anchors.

Morphology can constrain compatibility. It cannot authorize TYPE, ORG, GEO,
ownership, binding, or identity.

### `CoordinatingFrame`

- `frame_kind`: `act_requisites | structural_designation`;
- `local_anchor`: one fragment-local TextAnchor;
- `head_roles[]`: explicit roles in this local fragment;
- `members[]`: fragment-local member anchors and explicit values;
- `separators[]`: comma, conjunction, hyphen, brackets;
- `continuation`: optional edge to another frame, with evidence and direction;
- `alternatives[]`: competing parses;
- `bounds`: member count and expansion cardinality;
- `status`: proposed / ambiguous / rejected.

A WordML sequence such as 096-099 never owns one cross-block surface span.
Each block has a local anchor. A `continues` edge connects frames when block
order, punctuation, and an open coordinating head provide evidence.

### `SemanticFieldClaim`

- `field`: type / org / geo / date / number / marker / owner;
- `value`;
- `source`: explicit-member / same-series-head / prior-frame /
  current-document-requisites;
- `source_anchor` or sidecar record reference;
- `compatibility_basis`;
- `status`: explicit / inherited / conflicting / unresolved.

This is not an IdentifyingAct and has no Work identity. Contour B may assemble
an IdentifyingAct candidate only from compatible claims. OfficialIdentityClaim
remains the external natural-key claim; opaque identity remains downstream.

### `StructuralDesignationFrame`

A specialization/profile of CoordinatingFrame with:

- `marker` and its morphology evidence;
- `values[]` as written;
- `owner_path[]` as written or inherited inside the frame;
- `expansion_policy: endpoint_pair`;
- `local_anchor` for the complete written expression.

It yields one written ReferenceMention and bounded endpoint binding candidates.
It never integer-enumerates a decimal legal designation.

## 6. Inheritance authority and failure rules

Inheritance is a typed derivation, not nearest-text copying.

| Source | Allowed when | Result |
|---|---|---|
| Explicit member | field is written in the member | explicit claim; cannot be overwritten |
| Same coordinating head | member belongs to the same proven frame | inherited claim with head anchor |
| Previous block/frame | a typed `continues` edge is proven and roles are compatible | inherited claim with both local anchors; no cross-block span |
| CurrentDocumentRequisites | the input contract explicitly authorizes current-document completion for that construction | sidecar-derived claim, never text evidence |
| No unique compatible source | always | unresolved or competing proposed frames |

A prior enacting block and CurrentDocumentRequisites are not unconditional
fallbacks. If both are applicable and disagree, neither wins by proximity.
The frame is conflicting and contour B must not mint a complete identity.
An ordinary cited-act tail must not silently become a reference to the current
document merely because a document sidecar exists.

Hostile cases that must remain fail-closed include unrelated comma lists,
dates and numbers in addresses/case metadata, nested amendment parentheses,
mixed act types in one sentence, headings between WordML blocks, a new
paragraph after an open list, `б/н`, `вх. N`, quoted digit ranges, and a list
whose Cartesian product exceeds the declared bound.

## 7. Boundedness and observability

Before runtime implementation, the data contract must define:

- maximum local members and maximum expanded candidates;
- no recursive inheritance and at most one proven continuation hop unless a
  block-level coordinator explicitly materializes a longer chain;
- deterministic alternative ordering without forced winner selection;
- per-field provenance and rejection reason;
- diagnostics for ambiguity, conflicting sources, truncated/open frames, and
  expansion-limit refusal;
- lifecycle `[proposed]` until contract, hostile, and WordML continuation proof
  exists.

Pullenti's numeric `max-min <= 200` is evidence that bounds matter, not a
threshold to copy. Legal decimal designations are paths, not arithmetic
intervals.

## 8. Source evidence anchors

| Source | Symbol / area | Observed role |
|---|---|---|
| `sdk-python/pullenti/morph/MorphologyService.py` | `process`, `tokenize` | morphology pass before NER analyzers |
| `sdk-python/pullenti/morph/MorphToken.py` | `word_forms` | retains alternative forms |
| `sdk-python/pullenti/ner/core/AnalysisKit.py` | `AnalysisKit.__init__` | creates and normalizes linked TextToken chain |
| `sdk-python/pullenti/ner/TextToken.py` | constructor / morph collection | projects surviving forms onto text tokens |
| `sdk-python/pullenti/ner/MetaToken.py` | `MetaToken` | temporary span-bearing composite above text tokens |
| `sdk-python/pullenti/ner/core/TerminCollection.py` | `try_parse` family | local grammar/termin matching |
| `sdk-python/pullenti/ner/decree/internal/DecreeToken.py` | `try_attach_list` around 1568, 1682, 1726 | one coordinating TYP/DATE/NUMBER sequence |
| `sdk-python/pullenti/ner/decree/DecreeAnalyzer.py` | `__try_attach` around 287-450 | closes one act and assembles referent slots |
| `sdk-python/pullenti/ner/decree/internal/PartToken.py` | value/range parsing around 940-980, list parsing around 1299 | one role-bearing node with multiple values |
| `sdk-python/pullenti/ner/decree/DecreeAnalyzer.py` | `_try_attach_parts` around 4595-4680 | bounded combination and per-endpoint slot assembly |
| `sdk-python/pullenti/ner/person/PersonAnalyzer.py` and `person/internal/PersonItemToken.py` | initialization / `local_ontology` use | accidental global capability dependency |
| `sdk-python/pullenti/ner/mail/MailAnalyzer.py` and `mail/internal/MailLine.py` | `initialize`, `M_FROM_WORDS` | accidental static termin initialization dependency |

## 9. Architecture impact

This finding refines ADR-0028 but does not yet justify a separate ADR. The
change is within its typed-lexer / legal-reference decision boundary:

- insert `morph_evidence` and `local_reference_grammar` after `lex`;
- make contour A a projection of either direct lexical matchers or grammar
  frames, while preserving the closed eight-slot protocol;
- make contour B consume SemanticFieldClaim records plus sidecar context;
- make cross-block ellipsis a frame-continuation relation, not a larger span;
- keep resolve responsible for target binding and endpoint-pair expansion.

A new ADR becomes warranted only if this layer becomes shared by non-reference
parsers, requires a repository-wide candidate lattice, or changes the ledger /
identity boundaries. Until then it remains design-only data under ADR-0028.
