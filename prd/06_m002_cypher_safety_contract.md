# M002 Generated-Cypher Safety Contract

## 1. Reader and action

This contract is for engineers implementing or reviewing LegalGraph Nexus natural-language-to-Cypher integration. After reading it, they should be able to implement a validator that accepts only schema-grounded, read-only, evidence-returning generated Cypher and rejects unsafe candidates before any FalkorDB execution.

## 2. Scope

This is a conservative M002 contract for generated Cypher safety. It defines the Python API states, deterministic validation stages, trusted schema/policy artifact shape, rejection codes, execution backstop, and failure diagnostics expected from later validator work.

The contract applies only to the synthetic LegalGraph-shaped graph vocabulary already used by bounded runtime proof work:

- labels: `Act`, `Article`, `Authority`, `SourceBlock`, `EvidenceSpan`;
- relationships: `HAS_ARTICLE`, `CITES`, `ISSUED`, `SUPPORTED_BY`, `IN_BLOCK`, `SUPPORTS`;
- evidence path: `EvidenceSpan` must connect to a returned `SourceBlock` and to the returned legal unit being used as evidence;
- temporal fields: `valid_from` and `valid_to` must be respected for `Article` lookups when a question or caller context carries an as-of date.

This contract does not prove provider generation quality, product parser behavior, production Legal KnowQL behavior, legal-answer correctness, live FalkorDB availability, or production graph schema fitness. LLM non-authoritative remains mandatory: generated Cypher is never legal authority, never schema authority, and never evidence authority.

## 3. API states

The proposed Python API separates generation, validation, and execution:

```python
candidate = generate_only(question, schema_contract, *, provider_config=None)
validated = validate(candidate, schema_contract, *, request_context=None)
rows = execute_validated(validated, graph, *, timeout_ms=1000)
```

### `generate_only`

`generate_only` may call a provider-backed `text_to_cypher` or `cypher_only` integration in a later proof, but its output is only an opaque candidate string plus metadata. It must not execute Cypher, repair the graph, infer missing schema, or return legal conclusions. Provider metadata must be redacted before persistence; raw prompts, credentials, and provider response internals are not part of durable artifacts.

A valid `generate_only` result is allowed to be wrong. Safety starts at `validate`.

### `validate`

`validate` is deterministic. It accepts a candidate string and a local trusted schema/policy artifact identified by `schema_version`. It returns either a normalized single-statement read-only query plus validation diagnostics, or a rejection with a stable code.

The validator must fail closed when the schema/policy artifact is malformed, missing required fields, carries an unknown `schema_version`, or cannot express all policy checks. It must not ask the LLM to decide whether a query is safe.

### `execute_validated`

`execute_validated` accepts only a validation object produced by `validate`. It executes through the FalkorDB read-only backstop `Graph.ro_query` with a bounded timeout. It must not accept raw strings from callers, generated text, or partially validated candidates.

Execution failure is not a validation success. Runtime errors must be reported as execution errors with the query case, schema version, and policy stage that previously passed; they must not be converted into legal answers.

## 4. Trusted schema and policy artifact

The local schema/policy artifact is the only trusted source for generated-Cypher validation. It must include:

- `schema_version`;
- allowed labels and allowed properties per label;
- allowed relationship types and endpoint label pairs;
- required evidence paths involving `EvidenceSpan` and `SourceBlock`;
- allowed read-only clauses and allowed procedures;
- forbidden clauses and forbidden tokens;
- maximum `LIMIT`;
- maximum variable-length traversal depth;
- temporal field names and required as-of behavior;
- required diagnostic fields for rejection reporting.

Uncertain claims about the PRD, parser behavior, provider behavior, live graph content, or legal meaning remain out of scope for the artifact. The artifact constrains syntax and graph-shape policy; it does not certify legal correctness.

## 5. Validation stages

Validators should run stages in order and stop at the first rejection. Each rejection must name the query case, rejection code, schema/policy field, and whether the failure is contract-readback, validation, or execution related.

### Stage 1: candidate sanitation

Reject candidates that are empty, not strings, contain markdown fences, contain `<think>` or hidden reasoning tags, contain prose explanations, contain comments with instructions, or contain multiple statements.

Examples rejected here:

- ```cypher fences around a query;
- `MATCH (a:Article) RETURN a; MATCH (b:SourceBlock) RETURN b`;
- `MATCH (a:Article) RETURN a // ignore previous policy`;
- `<think>find all nodes</think> MATCH (n) RETURN n LIMIT 5`.

### Stage 2: read-only operation check

Reject any mutation, administrative, import, procedure-loading, or write-like operation. Only read-only clauses and explicitly allowed read procedures are permitted.

Examples rejected here:

- `CREATE (:Article {id: 'new'})`;
- `MERGE (a:Article {id: 'x'}) RETURN a`;
- `MATCH (n) DETACH DELETE n`;
- `CALL dbms.components()`;
- `LOAD CSV FROM 'file:///tmp/x' AS row RETURN row`.

### Stage 3: schema grounding

Reject unknown labels, relationship types, properties, or relationship endpoint shapes. The generated query must not invent product schema or carry over Neo4j-only assumptions.

Examples rejected here:

- `MATCH (p:Paragraph) RETURN p LIMIT 10` because `Paragraph` is not in the synthetic schema;
- `MATCH (a:Article)-[:AMENDS]->(b:Article) RETURN a,b LIMIT 10` because `AMENDS` is not allowed;
- `MATCH (a:Article) RETURN a.body LIMIT 10` because `body` is not an allowed returned property;
- `CALL db.index.fulltext.queryNodes(...)` because the allowed FalkorDB proof procedure is `db.idx.fulltext.queryNodes`.

### Stage 4: bounded traversal and result limits

Reject unbounded graph scans, variable-length traversals deeper than policy, missing `LIMIT`, `LIMIT` values above policy, and query forms that return high-cardinality graph objects without a bounded projection.

Examples rejected here:

- `MATCH (n) RETURN n`;
- `MATCH (a:Article)-[:CITES*1..10]->(b:Article) RETURN a,b LIMIT 10`;
- `MATCH (a:Article) RETURN a LIMIT 10000`.

### Stage 5: evidence-return constraint

A query intended to answer a legal question must return evidence identifiers, not only legal-unit nodes. Accepted answer-producing queries must include an evidence path tying `EvidenceSpan` to `SourceBlock` and to the returned `Article` or cited target. Queries may return IDs, hashes, source IDs, offsets, validity fields, scores, and citation-safe metadata; they must not return raw legal text in durable proof artifacts.

Examples rejected here:

- `MATCH (a:Article {id:'article:44fz:1'}) RETURN a.id LIMIT 1` because it omits `EvidenceSpan` and `SourceBlock`;
- `MATCH (a:Article)-[:SUPPORTED_BY]->(b:SourceBlock) RETURN a.id, b.id LIMIT 1` because the `EvidenceSpan` path is missing;
- `MATCH (s:EvidenceSpan) RETURN s.id LIMIT 1` because the legal unit and source block are not tied together.

### Stage 6: temporal constraint

When caller context includes an as-of date, `Article` candidates must constrain `valid_from` and `valid_to` so the answer is temporal-first. A query that ignores supplied temporal context must be rejected for legal-answer use.

Example accepted pattern:

```cypher
MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock),
      (span)-[:IN_BLOCK]->(block)
WHERE article.valid_from <= $as_of AND $as_of < article.valid_to
RETURN article.id, article.valid_from, article.valid_to, span.id, block.id
LIMIT 5
```

## 6. Rejection codes

| Code | Meaning | Failure class |
|---|---|---|
| `E_CONTRACT_MALFORMED` | Schema/policy JSON is invalid or missing required keys. | contract-readback |
| `E_SCHEMA_VERSION_UNKNOWN` | `schema_version` is absent or unsupported. | contract-readback |
| `E_CANDIDATE_FORMAT` | Candidate is empty, non-string, markdown/prose, hidden reasoning, comments, or multi-statement payload. | validation |
| `E_WRITE_OPERATION` | Candidate uses mutation, import, admin, or write-like clauses. | validation |
| `E_UNSUPPORTED_CLAUSE` | Candidate uses a clause outside the allowed read-only clause set. | validation |
| `E_UNSUPPORTED_PROCEDURE` | Candidate calls a procedure outside the allowlist. | validation |
| `E_UNKNOWN_LABEL` | Candidate references a label outside the trusted schema. | validation |
| `E_UNKNOWN_RELATIONSHIP` | Candidate references a relationship type outside the trusted schema. | validation |
| `E_UNKNOWN_PROPERTY` | Candidate references a property outside the trusted schema. | validation |
| `E_BAD_RELATIONSHIP_ENDPOINT` | Candidate uses an allowed relationship with disallowed endpoint labels. | validation |
| `E_UNBOUNDED_TRAVERSAL` | Candidate has an unbounded scan or variable-length traversal beyond policy. | validation |
| `E_LIMIT_REQUIRED` | Candidate omits required `LIMIT`. | validation |
| `E_LIMIT_EXCEEDED` | Candidate `LIMIT` exceeds `max_limit`. | validation |
| `E_EVIDENCE_REQUIRED` | Candidate omits the required `EvidenceSpan`/`SourceBlock` path for answer-producing queries. | validation |
| `E_TEMPORAL_REQUIRED` | Candidate ignores required as-of temporal filtering. | validation |
| `E_NEO4J_ONLY_CARRYOVER` | Candidate uses Neo4j-only procedure or capability not proven for FalkorDB. | validation |
| `E_EXECUTION_FAILED` | Validated query failed under `Graph.ro_query`. | execution |
| `E_EXECUTION_TIMEOUT` | Validated query exceeded the configured timeout. | execution |

## 7. Accepted query shapes

The validator should accept only narrow read-only projections over the synthetic contract, for example:

```cypher
MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock),
      (span)-[:IN_BLOCK]->(block)
WHERE article.id = $article_id
RETURN article.id, span.id, block.id, block.source_id, span.start_offset, span.end_offset
LIMIT 5
```

```cypher
MATCH (:Article {id:$source_article_id})-[:CITES]->(target:Article)<-[:HAS_ARTICLE]-(act:Act),
      (span:EvidenceSpan)-[:SUPPORTS]->(target)-[:SUPPORTED_BY]->(block:SourceBlock),
      (span)-[:IN_BLOCK]->(block)
RETURN act.id, target.id, span.id, block.id
LIMIT 5
```

```cypher
CALL db.idx.fulltext.queryNodes('SourceBlock', $search_terms) YIELD node, score
MATCH (span:EvidenceSpan)-[:IN_BLOCK]->(node)<-[:SUPPORTED_BY]-(article:Article),
      (span)-[:SUPPORTS]->(article)
RETURN article.id, node.id, span.id, score
LIMIT 5
```

These examples remain safety-contract examples. They do not certify legal answer correctness or production retrieval quality.

## 8. Execution backstop

`execute_validated` must use `Graph.ro_query` and a timeout. The read-only backstop is defense in depth, not a substitute for deterministic validation. A caller must not be able to pass raw generated Cypher directly to `Graph.ro_query`; it must pass through `validate` first.

The execution wrapper should log or persist only safe diagnostics:

- query case name;
- `schema_version`;
- validator stage outcome;
- rejection code or execution error class;
- duration and timeout class;
- redacted query fingerprint or normalized query shape.

Diagnostics must not include credentials, provider metadata values, raw legal text, or secret-bearing environment variables.

## 9. Unsafe generated-Cypher examples

The validator must reject at least these families:

1. writes: `CREATE`, `MERGE`, `SET`, `DELETE`, `DETACH DELETE`, `REMOVE`, `DROP`;
2. unknown schema: invented labels, relationship types, properties, or endpoint pairings;
3. missing evidence: answer-producing query returns legal units without `EvidenceSpan` and `SourceBlock`;
4. missing or excessive `LIMIT`;
5. multi-statement payloads separated by semicolon;
6. comment instructions or prompt-injection text;
7. markdown or hidden reasoning wrappers;
8. Neo4j-only carryover procedures or assumptions;
9. unbounded traversal or traversal depth above policy;
10. temporal omission when an as-of date is required.

## 10. Out-of-scope and legal-authority boundaries

This contract does not define a Legal KnowQL parser, legal reasoning engine, production ODT parser, provider prompt, product UI, external legal source update process, or live FalkorDB service SLO. It does not claim that any generated query is legally correct.

LLM non-authoritative is the controlling rule: an LLM may propose a candidate query only. Deterministic validation, local schema/policy artifacts, `Graph.ro_query` read-only execution, and evidence verification decide whether any result can be used downstream.

## 11. Reader-test checklist

A cold reader can implement the next validator task if they can answer yes to all of these:

- Do they know that `generate_only`, `validate`, and `execute_validated` are separate states?
- Do they know that `schema_version` and the local schema/policy artifact are the only trusted schema source?
- Do they know the accepted labels, relationships, evidence path, limit, traversal, procedure, and temporal boundaries?
- Do they know that provider output, parser behavior, product legal correctness, and live FalkorDB execution are not proven here?
- Do they know that failures must be diagnosable by query case, rejection code, schema/policy field, and failure class?
