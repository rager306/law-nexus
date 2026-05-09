# 2. Архитектура системы

## Назначение

Архитектура описывает систему подготовки, хранения и использования нормативных актов в **FalkorDB agentic temporal graph knowledge database** с дополнительным слоем **Legal Nexus + Legal KnowQL**.

Главная задача архитектуры — минимизировать влияние LLM на юридически проверяемых участках и заменить его:

- графовыми структурами FalkorDB;
- GraphBLAS-алгоритмами;
- детерминированными UDF/procedures;
- формальным query planning;
- evidence verification;
- citation-safe retrieval.

## High-level architecture

```mermaid
flowchart TB
    U[User / Agent / Application] --> MOD[Legal Nexus Module]
    API --> QP[Legal KnowQL Planner]
    QP --> POL[LLM Control Policy]

    QP --> UDF[Deterministic Legal UDF Library]
    QP --> GBLAS[GraphBLAS Algorithm Layer]
    QP --> CYPHER[FalkorDB Cypher Queries]
    QP --> RET[Hybrid Retrieval Layer]

    RET --> BM25[BM25 / Full-text]
    RET --> VEC[Vector Search]
    RET --> YAKE[Legal YAKE Keyphrase Layer]
    RET --> GR[Graph Relevance Scoring]

    UDF --> FDB[(FalkorDB)]
    GBLAS --> FDB
    CYPHER --> FDB
    BM25 --> FDB
    VEC --> FDB
    YAKE --> FDB
    GR --> FDB

    FDB --> EV[Evidence Verification]
    EV --> EP[Verified Evidence Pack]
    EP --> LLM[Optional LLM Composer]
    EP --> OUT[Deterministic Answer]
    LLM --> OUT
    OUT --> U
```

## Основные слои

### 1. Ingestion / ETL Layer

Отвечает за преобразование исходного ODT (OpenDocument Text) в нормализованные блоки и графовые сущности.

Вход:

- ODT-файл нормативного акта;
- имя файла;
- MIME type: `application/vnd.oasis.opendocument.text`;
- источник: Гарант;
- дата импорта.

Выход:

- `SourceDocument`;
- `SourceBlock`;
- cleaned text;
- legal structure;
- evidence spans;
- graph nodes and relationships;
- import package для FalkorDB.

```mermaid
flowchart TD
    A[ODT файл (Гарант)] --> B[Source metadata + SHA-256]
    B --> C[ODT block extractor (odfpy)]
    C --> D[SourceBlock JSONL]
    D --> E[Text cleaner]
    E --> F[Metadata extractor]
    E --> G[Structure parser]
    G --> H[Temporal extractor]
    G --> I[Reference extractor]
    G --> J[Term / entity extractor]
    G --> K[NormStatement extractor]
    G --> L[Legal YAKE extractor]
    G --> M[Chunk builder]
    H --> N[FalkorDB export package]
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N
```

### 2. Authoritative Graph Layer

FalkorDB хранит authoritative legal graph.

Основные labels:

```text
SourceDocument
SourceBlock
LegalDocument
LegalAct
ActEdition
Chapter
Article
Part
Clause
SubClause
Paragraph
EvidenceSpan
TextChunk
NormStatement
LegalTerm
LegalSubject
LegalConcept
ContentDomain
Condition
Exception
Deadline
Reference
KeyPhrase
AutoTag
```

`LegalDocument` is the base graph label for authored legal or practice documents. In FalkorDB it is modeled as a **multi-label base type**, not as a separate inheritance node: each `LegalAct`, later `CaseLaw`, and later `PracticeDocument` node also carries `LegalDocument` and has a required `document_type` property (`legal_act`, `case_law`, `practice_document`). `ContentDomain` is a first-class node; every `LegalDocument` must have at least one `HAS_DOMAIN` relationship, defaulting to `normative_acts` for the 44-ФЗ MVP import.

Основные relationships:

```text
HAS_BLOCK
HAS_EDITION
HAS_DOMAIN
DERIVED_FROM
CONTAINS
NEXT
PREVIOUS
SUPPORTED_BY
LOCATED_IN
HAS_CHUNK
DEFINES
USES_TERM
REFERS_TO
APPLIES_TO
HAS_CONDITION
HAS_EXCEPTION
HAS_DEADLINE
HAS_KEYPHRASE
TAGGED_WITH
CANDIDATE_FOR
VERSION_OF
SUPERSEDES
AMENDED_BY
```

`HAS_BLOCK`, `HAS_EDITION`, `HAS_DOMAIN`, `DERIVED_FROM`, `CONTAINS`, `SUPPORTED_BY`, `HAS_CHUNK`, `DEFINES`, `USES_TERM`, `REFERS_TO`, `APPLIES_TO`, `HAS_CONDITION`, `HAS_EXCEPTION`, `HAS_DEADLINE`, `HAS_KEYPHRASE`, `TAGGED_WITH`, and `CANDIDATE_FOR` are part of the target model below. `NEXT`, `PREVIOUS`, and `LOCATED_IN` are structural navigation relationships for linear/source ordering. `VERSION_OF`, `SUPERSEDES`, and `AMENDED_BY` are reserved for post-MVP temporal/versioning work and remain deferred until S08/later temporal modeling defines exact event semantics.

## Целевая графовая модель

```mermaid
flowchart TB
    SD[SourceDocument] -->|HAS_BLOCK| SB[SourceBlock]
    LA[LegalDocument:LegalAct] -->|HAS_DOMAIN| CD[ContentDomain]
    LA -->|HAS_EDITION| ED[ActEdition]
    ED -->|DERIVED_FROM| SD
    ED -->|CONTAINS| CH[Chapter]
    CH -->|CONTAINS| AR[Article]
    AR -->|CONTAINS| PT[Part]
    PT -->|CONTAINS| CL[Clause]
    CL -->|CONTAINS| SCL[SubClause]

    PT -->|HAS_CHUNK| TC[TextChunk]
    PT -->|SUPPORTED_BY| EV[EvidenceSpan]
    EV -->|DERIVED_FROM| SB

    NS[NormStatement] -->|DERIVED_FROM| PT
    NS -->|SUPPORTED_BY| EV
    NS -->|APPLIES_TO| LS[LegalSubject]
    NS -->|HAS_CONDITION| COND[Condition]
    NS -->|HAS_EXCEPTION| EXC[Exception]
    NS -->|HAS_DEADLINE| DL[Deadline]

    AR -->|DEFINES| LT[LegalTerm]
    NS -->|USES_TERM| LT
    PT -->|REFERS_TO| REF[Reference]
    REF -->|REFERS_TO| TARGET[LegalDocument / LegalUnit]

    PT -->|HAS_KEYPHRASE| KP[KeyPhrase]
    TC -->|TAGGED_WITH| AT[AutoTag]
    KP -->|CANDIDATE_FOR| LC[LegalConcept]
```

### 2a. NormStatement verification contract

`NormStatement` is a verified semantic claim derived from one or more legal units, not an authoritative source by itself. The source authority remains `LegalUnit -> EvidenceSpan -> SourceBlock -> SourceDocument`.

Required MVP properties:

| Property | Contract |
|---|---|
| `norm_type` | One of FR-14 `type`; describes legal function (`definition`, `requirement`, `prohibition`, etc.). |
| `modality` | One of FR-14 `modality`; describes force (`must`, `must_not`, `may`, `is_defined_as`, etc.). |
| `extraction_method` | `deterministic`, `llm_candidate`, or `manual`. LLM output is never final authority. |
| `verification_status` | `unverified`, `verified`, `rejected`, or `needs_manual_review`. Only `verified` may support answers. |
| `source_unit_ids` | One or more source legal-unit IDs; supports norms spanning multiple parts or clauses. |
| `evidence_span_ids` | One or more EvidenceSpan IDs proving the extracted statement. |

Compatibility matrix:

| `norm_type` | Allowed `modality` values | Notes |
|---|---|---|
| `definition` | `is_defined_as`, `unknown` | `unknown` allowed only before verification. |
| `requirement`, `obligation`, `procedure`, `competence` | `must`, `unknown` | `must` is expected after verification. |
| `prohibition`, `liability` | `must_not`, `must`, `unknown` | `liability` may describe a sanction that must be applied; verifier records rationale. |
| `permission` | `may`, `unknown` | `may` is expected after verification. |
| `exception`, `condition`, `scope` | `applies_to`, `does_not_apply_to`, `unknown` | Must link to the affected statement or legal unit. |
| `deadline`, `reference` | `must`, `applies_to`, `unknown` | Depends on source wording; verifier records rationale. |

Verification flow:

```mermaid
flowchart TD
    LU[LegalUnit(s)] --> CAND[NormStatement candidate]
    EV[EvidenceSpan(s)] --> CAND
    CAND --> VAL[Compatibility validator]
    VAL --> SRC[Source text check]
    SRC -->|pass| OK[verification_status=verified]
    SRC -->|fail| REJ[verification_status=rejected]
    SRC -->|ambiguous| REVIEW[verification_status=needs_manual_review]
```

## 3. Temporal Layer

Temporal layer отвечает за применимость норм во времени.

Каждая юридическая единица должна иметь:

```json
{
  "edition_date": "2025-12-28",
  "valid_from": null,
  "valid_to": null,
  "effective_from": null,
  "effective_to": null,
  "status": "active",
  "temporal_confidence": "unknown"
}
```

### 3a. Temporal field glossary

- `edition_date` — дата редакции, зафиксированная источником (`SourceDocument.source_system`, например Гарант). Она выбирает конкретный `ActEdition`, но сама по себе не доказывает период юридической силы нормы.
- `valid_from` / `valid_to` — период юридической силы нормы или редакции: от вступления нормы в силу до утраты силы. `valid_to = null` means no end date was extracted or verified, not permanent validity.
- `effective_from` / `effective_to` — период практического применения нормы when transitional provisions, delayed application, or special applicability windows differ from formal validity. If not independently extracted, these fields remain `null` and must not be inferred from `valid_*` by LLM.
- `status` is derived by deterministic temporal logic from the query date, `valid_*`, `effective_*`, explicit repeal/entry markers, and `temporal_confidence`. `unknown` must be returned when the evidence is insufficient.

Статусы:

```text
active
expired
future
partially_active
unknown
```

Temporal-проверка выполняется детерминированно через UDF:

```text
legal.active_at(node_id, date) → active / inactive / unknown
```

```mermaid
flowchart LR
    Q[Query date] --> UDF[legal.active_at]
    N[LegalUnit] --> UDF
    ED[ActEdition] --> UDF
    TM[Temporal markers] --> UDF
    UDF --> R{Active?}
    R -->|yes| A[Include in retrieval]
    R -->|no| X[Exclude / mark expired]
    R -->|unknown| W[Include with warning]
```

## 3b. Candidate Temporal Versioning Improvements Requiring Validation

The following temporal-model ideas are valuable but are **not yet confirmed implementation requirements**. They must be researched and validated during the architecture review and later proof slices before becoming product commitments:

| Candidate idea | Why it may matter | Validation owner / proof needed |
|---|---|---|
| Act editions as aggregations rather than full document snapshots | A new `ActEdition` could reference updated legal units while reusing unchanged units, reducing duplication and improving historical traceability. | S07/S08 should classify the PRD impact; a later implementation milestone must prove stable IDs, import idempotency, and query simplicity. |
| Action nodes for amendments, repeal, publication, entry into force, and expiration | Change events would make temporal reasoning explainable: why a norm changed, which act changed it, and when it became effective. | S07/S08 should add this to architecture findings; later parser/import work must prove event extraction and evidence links. |
| Source provenance classes | The graph should distinguish official publication, open reconstructed corpus, commercial consolidated version, legacy prior art, and generated summaries. | S05/S07/S08 should verify source classes against real ODT evidence, PRD consistency, and future source strategy. |

These ideas preserve the existing temporal-first direction, but they must not be treated as proven behavior until source/parser/runtime evidence exists.

### 3c. Source provenance classes and import lifecycle

`SourceDocument` must carry a source provenance class so downstream verification can distinguish legal authority, reconstruction, and generated context. MVP source classes are:

| `source_provenance_class` | Meaning | Evidence rule |
|---|---|---|
| `official_publication` | Official state publication source | Preferred when available; can be authoritative if source authenticity is verified. |
| `commercial_consolidated` | Commercial consolidated edition such as Гарант | Usable as source evidence for M001/MVP import, but must be labelled and not conflated with official publication. |
| `open_reconstructed` | Open corpus reconstructed from public materials | Requires reconstruction metadata and lower confidence until audited. |
| `legacy_prior_art` | Legacy project artifacts such as `Old_project/` | Prior art only; cannot become source evidence without re-extraction from a current source document. |
| `generated_summary` | LLM or human-generated summary | Never legal authority; can only be explanatory context after evidence verification. |

Import lifecycle is keyed by `sha256`, `source_provenance_class`, `act_number`, and `edition_date`. Re-importing the same SHA is an idempotent no-op for graph facts; importing a changed SHA for the same act and edition creates a new source revision that must preserve old evidence until explicitly superseded by validation.

## 4. Evidence Layer

Evidence layer нужен для grounding.

### EvidenceSpan lifecycle

`EvidenceSpan` is immutable for a specific `SourceDocument.sha256`, `SourceBlock`, byte/character span, legal unit, and `ActEdition`. When a source file changes and produces a new SHA, import must create new EvidenceSpan IDs for spans derived from the new source revision. Old spans are retained for audit and marked with lifecycle status rather than overwritten.

Lifecycle statuses:

```text
current
superseded_by_new_sha
orphaned_by_parser_change
rejected_by_validation
archived
```

Rules:

- same SHA + same span mapping → keep existing EvidenceSpan and reuse relationships;
- same SHA + parser mapping change → block import unless validation explicitly records `orphaned_by_parser_change` and the new mapping;
- new SHA + same `act_number` + same `edition_date` → create a new source revision and new EvidenceSpan set, then mark replaced spans `superseded_by_new_sha` only after validation passes;
- new `edition_date` → create a separate `ActEdition` and EvidenceSpan set; never mutate old edition evidence;
- generated summaries and legacy prior art cannot create authoritative EvidenceSpan records.

Основная цепочка доказательства:

```text
NormStatement / TextChunk / Answer
  → EvidenceSpan
  → LegalUnit
  → SourceBlock
  → SourceDocument
```

```mermaid
flowchart TD
    ANS[Answer claim] --> VER[legal.verify_evidence]
    VER --> EV[EvidenceSpan]
    EV --> LU[Article / Part / Clause]
    EV --> SB[SourceBlock]
    SB --> SD[SourceDocument]
    LU --> ED[ActEdition]
    VER --> VR[VerificationResult]
    VR -->|verified| OK[May be used in answer]
    VR -->|failed| NO[Reject / no_answer]
```

## 5. Legal Nexus Layer

Legal Nexus — orchestration layer между пользователем, агентом и FalkorDB.

Функции:

- intent detection;
- KnowQL parsing;
- deterministic query planning;
- вызов UDF;
- запуск GraphBLAS algorithms;
- hybrid retrieval;
- evidence verification;
- формирование citation-safe context;
- контроль использования LLM.

## 6. Legal KnowQL

Legal KnowQL — декларативный DSL для юридических запросов.

Canonical MVP syntax is the FR-22 subset. Architecture examples must use the same style: command + object, `WHERE key = value` predicates, optional `IN act = value`, optional `AT "YYYY-MM-DD"`, explicit `RETURN` fields. Older examples using `FOR subject "..."` or `AT date "..."` are illustrative only and are not accepted by the MVP parser.

EBNF sketch for the MVP parser:

```ebnf
query          = get_query | find_query | check_query | expand_query ;
get_query      = "GET" object where_clause [ at_clause ] [ return_clause ] ;
find_query     = "FIND" object where_clause [ in_clause ] [ at_clause ] [ return_clause ] ;
check_query    = "CHECK" status_object "OF" string [ at_clause ] [ return_clause ] ;
expand_query   = "EXPAND" "references" "FROM" string [ depth_clause ] [ at_clause ] [ return_clause ] ;
where_clause   = "WHERE" predicate { "AND" predicate } ;
predicate      = identifier "=" value ;
in_clause      = "IN" "act" "=" value ;
at_clause      = "AT" date_string ;
return_clause  = "RETURN" identifier { "," identifier } ;
depth_clause   = "DEPTH" integer ;
value          = string | identifier | integer ;
date_string    = string ;  (* YYYY-MM-DD validated semantically *)
```

KnowQL errors return structured diagnostics: `syntax_error`, `unknown_identifier`, `unknown_legal_unit`, `ambiguous_reference`, `unsupported_pattern`, or `execution_error`, each with `message`, `span`, `hint`, and optional `candidate_citations`.

Примеры:

```sql
GET norm
WHERE act = "44-ФЗ" AND article = "31" AND part = "1"
AT "2025-12-28"
RETURN text, status, citation, evidence
```

```sql
FIND norm_statements
WHERE norm_type = "requirement" AND subject = "участник закупки"
IN act = "44-ФЗ"
AT "2025-12-28"
RETURN statement, source_path, evidence
```

```sql
CHECK status
OF "п. 4 ч. 1 ст. 31 44-ФЗ"
AT "2025-12-28"
RETURN status, temporal_evidence
```

## KnowQL execution flow

```mermaid
sequenceDiagram
    participant User
    participant Nexus as Legal Nexus API
    participant Planner as KnowQL Planner
    participant UDF as Legal UDF
    participant G as FalkorDB / GraphBLAS
    participant V as Evidence Verifier
    participant LLM as Optional LLM Composer

    User->>Nexus: Natural language query or KnowQL
    Nexus->>Planner: Parse intent and build plan
    Planner->>UDF: Resolve citation / temporal / structure
    UDF->>G: Execute deterministic graph operations
    G-->>UDF: Candidate legal units
    UDF-->>Planner: Structured results
    Planner->>V: Verify evidence and citations
    V-->>Planner: Verified evidence pack
    alt Explanation needed
        Planner->>LLM: Compose answer using only verified evidence
        LLM-->>Nexus: Draft answer with citations
    else Deterministic answer enough
        Planner-->>Nexus: Direct answer with citations
    end
    Nexus-->>User: Grounded answer
```

## 7. Deterministic operation contracts

`legal.*` names are public operation names, but the implementation layer is explicit. JavaScript UDFs inside FalkorDB are limited to bounded deterministic graph lookups and formatting. Python LegalNexus methods perform orchestration, multi-step traversal, evidence verification, ranking, context assembly, and any operation that may need retries, larger memory, or external policy checks.

| Operation | Layer | Implementation | Return contract | Versioning owner |
|---|---|---|---|---|
| `legal.active_at(node_id, date)` | JavaScript UDF | FalkorDB JS UDF | `TemporalStatus { status: active|inactive|unknown|partially_active, reason, evidence_ids[] }` | UDF API v1 |
| `legal.format_citation(node_id)` | JavaScript UDF | FalkorDB JS UDF | `Citation { citation_label, citation_key, path }` | UDF API v1 |
| `legal.get_norm_id(act, article, part?, clause?, date?)` | JavaScript UDF | FalkorDB JS UDF | `NormRef { node_id, citation_key, status }` or `null` | UDF API v1 |
| `legal.resolve_citation(citation, edition_date?)` | Python LegalNexus | `LegalNexus.resolve_citation` | `CitationResolution { candidates[], selected?, ambiguity }` | Nexus API v1 |
| `legal.get_norm(act, article, part?, clause?, date?)` | Python LegalNexus | `LegalNexus.get_norm` | `EvidencePack { legal_units[], evidence_spans[], temporal_status }` | Nexus API v1 |
| `legal.get_article(act, article, edition_date?)` | Python LegalNexus | `LegalNexus.get_article` | `EvidencePack` | Nexus API v1 |
| `legal.get_definition(term, date?)` | Python LegalNexus | `LegalNexus.get_definition` | `EvidencePack` | Nexus API v1 |
| `legal.find_requirements(subject, act?, date?)` | Python LegalNexus | `LegalNexus.find_requirements` | `EvidencePack { norm_statements[], citations[], verification }` | Nexus API v1 |
| `legal.find_obligations(subject, act?, date?)` | Python LegalNexus | `LegalNexus.find_obligations` | `EvidencePack` | Nexus API v1 |
| `legal.find_prohibitions(subject, act?, date?)` | Python LegalNexus | `LegalNexus.find_prohibitions` | `EvidencePack` | Nexus API v1 |
| `legal.find_exceptions(scope, date?)` | Python LegalNexus | `LegalNexus.find_exceptions` | `EvidencePack` | Nexus API v1 |
| `legal.find_deadlines(scope, date?)` | Python LegalNexus | `LegalNexus.find_deadlines` | `EvidencePack` | Nexus API v1 |
| `legal.expand_references(node_id, depth, date?)` | Python LegalNexus | `LegalNexus.expand_references` | `ReferenceExpansion { nodes[], edges[], evidence_spans[] }` | Nexus API v1 |
| `legal.verify_evidence(claim, evidence_ids)` | Python LegalNexus | `LegalNexus.verify_evidence` | `VerificationResult { status, checked_at, failures[], evidence_ids[] }` | Nexus API v1 |
| `legal.rank_candidates(query, candidates, date?)` | Python LegalNexus | `LegalNexus.rank_candidates` | `RankedCandidates { candidates[], scoring_trace }` | Nexus API v1 |
| `legal.build_context(query, candidates, max_scope)` | Python LegalNexus | `LegalNexus.build_context` | `AnswerContext { evidence_pack, citations, llm_allowed }` | Nexus API v1 |

Versioning rule for G-003: operation names are stable within an API major version. Breaking input/return changes create `api_version = v2` in the LegalNexus method contract and a migration note; JS UDF v1 remains backward-compatible or is exposed under an explicit v2 name.

## 8. GraphBLAS Algorithm Layer

GraphBLAS используется для вычислимых графовых операций:

- controlled graph expansion;
- relevance propagation;
- reference closure;
- temporal subgraph filtering;
- graph-distance scoring;
- concept-neighborhood search;
- centrality scoring for norms;
- orphan node detection;
- duplicate / near-duplicate detection.

Пример relevance propagation:

```mermaid
flowchart LR
    Q[Query seed nodes] --> T[Matched Terms]
    Q --> S[Matched Subjects]
    Q --> A[Matched Articles]
    T --> M[Graph adjacency matrices]
    S --> M
    A --> M
    M --> P[Score propagation]
    P --> R[Ranked LegalUnits]
    R --> E[Evidence verification]
```

## 9. Hybrid Retrieval Layer

Retrieval состоит из нескольких источников сигналов.

```text
final_score =
    0.25 * structural_match
  + 0.20 * graph_relevance
  + 0.15 * bm25_score
  + 0.15 * vector_score
  + 0.10 * yake_keyphrase_match
  + 0.10 * temporal_validity
  + 0.05 * evidence_confidence
```

```mermaid
flowchart TD
    Q[Query] --> SR[Structural resolver]
    Q --> TF[Temporal filter]
    Q --> BM[BM25]
    Q --> VS[Vector search]
    Q --> YK[Legal YAKE match]
    Q --> GS[GraphBLAS scoring]

    SR --> SC[Candidate scorer]
    TF --> SC
    BM --> SC
    VS --> SC
    YK --> SC
    GS --> SC

    SC --> TOP[Top candidates]
    TOP --> EV[Evidence verification]
    EV --> CTX[Citation-safe context]
```

## 9b. Retrieval and Answering Improvements Requiring Validation

The following retrieval and answering improvements are strong candidates for the target architecture, but they require source/runtime evaluation before they become firm implementation requirements:

| Candidate idea | Why it may matter | Validation owner / proof needed |
|---|---|---|
| Document-level and temporal pre-filter before BM25/vector search | Legal queries should first resolve the act, edition/date, and citation scope so retrieval does not mix same-number documents, stale editions, or irrelevant chapters. | S04/S07/S08 should verify the query-flow requirement; later Legal Nexus work must prove routing accuracy. |
| Clause/legal-unit chunking instead of sliding windows | Citation-safe retrieval depends on chunks aligned to legal units and EvidenceSpan, not arbitrary character windows that can cut conditions, exceptions, or temporal markers. | S05 must verify real ODT legal-unit boundaries; S07/S08 should classify PRD changes. |
| Evidence Auditor after optional LLM composition | Any LLM-produced wording should be checked back against EvidenceSpan, SourceBlock, ActEdition, temporal status, and citation labels before it is accepted. | S04/S07/S08 should specify verification behavior; later implementation must prove claim-to-evidence checks. |
| Deterministic fast-paths for citation/date/amount/deadline queries | Many legal questions can be answered through structured lookup or UDFs without LLM composition, reducing latency, cost, and hallucination risk. | S07/S08 should route this into future Legal KnowQL/Nexus planning; implementation must measure coverage and no-answer behavior. |

These candidates must remain subordinate to evidence verification: retrieval candidates and LLM drafts are not legal authority.

## 10. LLM Control Policy

LLM output is non-authoritative.

LLM запрещен для:

- structural lookup;
- temporal validity;
- citation resolution;
- evidence verification;
- status checks;
- source existence checks.

LLM разрешен для:

- natural language explanation;
- query rewrite candidate;
- ambiguous intent clarification;
- summarization of verified evidence;
- candidate semantic extraction with verification.

```mermaid
flowchart TD
    TASK[Task] --> C{Is task algorithmically verifiable?}
    C -->|yes| DET[Use UDF / GraphBLAS / Cypher]
    C -->|no or ambiguous| L[LLM candidate mode]
    L --> V[Verification required]
    V -->|verified| USE[Use result]
    V -->|failed| REJ[Reject / no_answer]
    DET --> USE
```

## 11. Import Package Architecture

Пакет импорта в FalkorDB:

```text
01_source_document.json
02_legal_act.json
03_source_blocks.jsonl
04_structure_nodes.jsonl
05_evidence_nodes.jsonl
06_norm_nodes.jsonl
07_entity_nodes.jsonl
08_term_nodes.jsonl
09_chunk_nodes.jsonl
10_keyphrase_nodes.jsonl
11_relationships.jsonl
12_embeddings.jsonl
13_import.cypher
14_validation_report.json
15_quality_report.json
16_retrieval_eval.json
17_cleaned.md
```

## 12. Validation Architecture

Перед импортом система должна валидировать пакет.

```mermaid
flowchart TD
    P[Import package] --> V1[Unique node IDs]
    P --> V2[Relationship endpoints exist]
    P --> V3[Required properties]
    P --> V4[Path and citation labels]
    P --> V5[Temporal fields]
    P --> V6[No orphan chunks]
    P --> V7[No empty evidence]
    P --> V8[Cypher syntax]
    V1 --> R[Validation report]
    V2 --> R
    V3 --> R
    V4 --> R
    V5 --> R
    V6 --> R
    V7 --> R
    V8 --> R
    R -->|passed| I[Import into FalkorDB]
    R -->|failed| F[Block import]
```

## 13. Deployment view

```mermaid
flowchart TB
    subgraph ETL[ETL Runtime]
        E1[ODT Parser (odfpy)]
        E2[Structure Parser]
        E3[Legal YAKE]
        E4[Exporter]
    end

    subgraph DB[FalkorDB]
        D1[Graph Store]
        D2[Vector Properties / External Vector IDs]
        D3[Indexes]
    end

    subgraph Nexus[Legal Nexus Service]
        N1[KnowQL Parser]
        N2[Query Planner]
        N3[UDF Gateway]
        N4[GraphBLAS Runner]
        N5[Evidence Verifier]
    end

    subgraph Optional[Optional Services]
        O1[Embedding Model]
        O2[LLM Composer]
    end

    ETL --> DB
    Nexus --> DB
    Nexus --> Optional
    Optional --> Nexus
```

## 13b. Deployment Evolution

Поэтапный переход:

```text
Этап 1: FalkorDBLite (embedded)
  - Локальный режим без Docker
  - pip install falkordblite
  - Быстрый старт для разработки

Этап 2: Docker Compose
  - FalkorDB в контейнере
  - Персистентное хранение
  - Один docker-compose up

Этап 3: Python-модуль → FastAPI-обёртка
  - LegalNexus как Python-класс
  - REST API для integration
  - OpenAPI docs
```

## 13c. UDF Architecture

Два уровня UDF:

### JavaScript UDF в FalkorDB (простые graph-операции)

```javascript
legal.active_at(node_id, date)     // проверка temporal status
legal.format_citation(node_id)     // форматирование цитаты
legal.get_norm_id(act, article)    // быстрый lookup
```

Загружаются через `GRAPH.UDF LOAD`.

JS UDF constraints for R-003:

- no async I/O or external service calls;
- no unbounded cross-node traversal, recursive expansion, or large aggregation;
- no evidence-pack assembly, ranking, LLM context construction, or retry policy;
- return values must be small deterministic records or scalar IDs suitable for use inside Cypher plans.

### Python методы в LegalNexus (сложная оркестрация)

```python
class LegalNexus:
    def legal_find_requirements(self, subject, act, date):
        # orchestration + graph traversal + evidence gathering

    def legal_verify_evidence(self, claim, evidence_ids):
        # multi-step verification

    def legal_build_context(self, query, candidates):
        # context assembly for LLM
```

## 13d. Embedding Stack

```text
Model: sentence-transformers + deepvk/USER-bge-m3
Dimension: 1024
Language: optimized for Russian

Vector store: FalkorDB vector index
  - cosine similarity
  - dimension: 1024
  - no external vector store required
```

## 13e. Extensible Graph Model

```text
LegalDocument (base multi-label type)
  ├── LegalAct (federal law, law, decree)
  ├── CaseLaw (court decision, ruling, determination)
  └── PracticeDocument (fas_practice, audit_report, explanation)

Required document properties:
  - document_type: legal_act | case_law | practice_document

ContentDomain (first-class node)
  - normative_acts
  - case_law
  - fas_practice
  - procurement
  - construction
  - healthcare
  - budget_accounting

Required relationship:
  - (LegalDocument)-[:HAS_DOMAIN]->(ContentDomain)
  - Cardinality: M:N; each document has one or more domains
  - MVP default: normative_acts
```

ETL параметризован: `document_type` задаётся при загрузке, ядро не требует изменений. For the 44-ФЗ MVP import, document nodes are labeled `LegalDocument` and `LegalAct`, `document_type = legal_act`, and `HAS_DOMAIN` points to `normative_acts`.

## 13f. Rust Roadmap

```text
Долгосрочная цель: ETL-компоненты через PyO3

В MVP: только Python
  - Быстрая итерация
  - Простая отладка
  - Быстрый старт

Post-MVP: Rust для критичных ETL-компонентов
  - Парсинг ODT (через odfpy остаётся Python)
  - CPU-intensive text processing
  - PyO3 bindings
```

## 14. Архитектурный итог

Система реализует deterministic-first legal intelligence architecture:

- FalkorDB — authoritative legal knowledge substrate;
- FalkorDBLite → Docker Compose — deployment evolution;
- ODT/odfpy ingestion — source format from Гарант;
- sentence-transformers + deepvk/USER-bge-m3 — embeddings (1024-dim);
- FalkorDB vector index — cosine similarity, no external vector store;
- Legal Nexus Module — Python-класс для orchestration;
- JS UDF в FalkorDB — простые graph-операции;
- Python LegalNexus — сложная оркестрация;
- Legal KnowQL — формальный язык запросов;
- GraphBLAS — вычислимое графовое reasoning ядро;
- UDF/procedures — проверяемая юридическая логика;
- Legal YAKE — легкий explainable semantic layer;
- Extensible graph model — LegalDocument + ContentDomain;
- LLM — non-authoritative language interface.
