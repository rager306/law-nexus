# Recursive whole-document analysis patterns without an LLM runtime

**Date:** 2026-09-04  
**Status:** `[proposed]` architecture assessment  
**Decision:** D386  
**Constraint:** no LLM, RLM runtime, prompt, REPL, or model call participates in product capture, inheritance, binding, or identity

## 1. Pattern being adopted

The useful pattern commonly illustrated by Recursive Language Models is not
the model call. It is the control architecture:

1. keep a large context in an external addressable environment;
2. inspect and partition it programmatically;
3. turn missing information into smaller dependent queries;
4. recursively solve only those dependencies;
5. reduce the returned evidence into the parent result;
6. memoize, bound, and trace the computation.

In Law Nexus every step is deterministic. `DocumentStructureIndex` is the
external environment. Covering lexer, local reference grammar, document
context, and resolver are specialized operators. `ContextView` is the bounded
projection supplied to one operator. No raw full-document prompt exists.

## 2. Mapping to the NPA architecture

| Recursive-context pattern | Law Nexus realization |
|---|---|
| Externalized long context | version-bound `DocumentStructureIndex` |
| Programmatic inspection | typed structural query API |
| Decomposition | local grammar emits incomplete frames plus `ContextRequest` dependencies |
| Recursive subproblem | resolve an ancestor, series head, alias declaration, structural owner, or explicit anchor request |
| Local result | provenance-bearing `SemanticFieldClaim` or typed unresolved result |
| Reduction | deterministic claim compatibility/conflict reducer |
| Memory | memo table keyed by document version + request + source frame |
| Trace | derivation graph from local mention through context requests to claims/binding |
| Termination | visited set, cycle detection, monotone state, depth/cardinality budgets |

## 3. Four useful recursion axes

### 3.1 Structural recursion

Traverse the document hierarchy:

```text
document → division → chapter → article → part → item
```

A local mention can ask for its nearest typed owner or complete ancestor path.
This is ordinary tree recursion and is safe when every node belongs to one
document version and parent edges are acyclic.

### 3.2 Grammar recursion

Legal expressions nest:

```text
amendment block
  → act requisite series
    → structural designation
      → range endpoints
```

A grammar frame may contain child frames, but the source span remains local
and immutable. Child results are reduced into roles/values, not concatenated
into a synthetic source string.

### 3.3 Context-dependency recursion

An incomplete frame emits typed requests, for example:

```text
NeedSeriesHead(frame=087, fields=[type, org, geo])
NeedStructuralOwner(frame=X, roles=[article, clause])
NeedScopedAlias(alias="Положение", at=block_Y)
NeedCurrentDocumentRequisites(fields=[type, number])
NeedExplicitAnchor(designation="статья 19")
```

A resolved request may expose another dependency. For example, a continuation
edge points to a prior frame whose issuer itself depends on the document head.
This is graph recursion, not nearest-neighbour text lookup.

### 3.4 Resolution recursion

Aliases, anaphora, and nested structural references can form chains. Each hop
must preserve the original ReferenceMention and add a new derivation edge.
Cycles and conflicting targets produce a typed unresolved result; no chain is
collapsed into a fabricated unique target.

## 4. Prefer a worklist/fixpoint engine over stack recursion

The conceptual computation is recursive, but a product implementation should
use an explicit deterministic worklist:

```text
index complete document
produce all local frames
enqueue their ContextRequests
while work remains:
  reject or reuse visited/memoized request
  execute one typed query/operator
  add provenance-bearing claims or diagnostics
  enqueue newly exposed dependencies within bounds
reduce claims for each frame
project contour A/B
resolve bindings
```

Advantages over direct function recursion:

- complete trace of why a field was inherited;
- stable ordering and deterministic replay;
- memoization of shared requisites/owners/aliases;
- explicit cycle and resource-limit diagnostics;
- no stack-depth dependency;
- document-wide forward and backward access after indexing is complete.

This is a bounded monotone derivation, not unconstrained iterative guessing.
An existing explicit claim never becomes less explicit. New evidence may add a
compatible derivation, expose a conflict, or leave the result unresolved; it
must not silently overwrite the source mention.

## 5. Request and result contracts

### `ContextRequest`

Design-only fields:

- `request_kind`;
- `document_version_ref`;
- `origin_frame_ref`;
- `requested_roles_or_fields`;
- `structural_scope`;
- `explicit_key`, when applicable;
- `path_so_far`;
- `budget_remaining`;
- `evidence_requirement`.

Request kinds remain closed and typed. An operator cannot issue an arbitrary
"find something relevant" request.

### `ContextResult`

- `request_ref`;
- `status`: resolved / partial / conflicting / unavailable / cycle / limit;
- `candidate_claims[]`;
- `source_anchors[]`;
- `derivation_edges[]`;
- `diagnostics[]`.

A result is not automatically a `SemanticFieldClaim`. The claim reducer checks
role compatibility, scope, precedence, and conflicts first.

## 6. Reduction rules

Reduction is field-wise and provenance-preserving:

1. explicit member claims cannot be overwritten;
2. compatible same-frame head claims may fill absent fields;
3. a proven series continuation may supply only roles declared by that edge;
4. CurrentDocumentRequisites may supply only constructions that explicitly
   authorize current-document context;
5. equal values from independent paths retain both evidence paths;
6. unequal applicable values create `conflicting`, not a winner;
7. unresolved dependencies remain visible after the document pass.

A child result never edits its parent. The reducer derives a new parent state.

## 7. Cycle and explosion controls

Potential cycles include aliases referring to aliases, malformed hierarchy,
series-continuation loops, and an inherited claim being reused as a new source.
Controls:

- memo key includes document version, request kind, explicit key/scope, and
  source frame;
- visited-path detection returns `cycle` with the traversed evidence path;
- inherited claims cannot silently become inheritance authorities;
- Cartesian frame expansion is delayed and bounded;
- every operator declares fan-out and admissible successor request kinds;
- reaching a limit returns partial/conflicting, never a truncated unique answer.

Concrete numeric limits remain `deferred-undefined`; runtime work must stop
until hostile contracts select them.

## 8. Where the pattern applies

| Plane | Recursive pattern |
|---|---|
| Decoder / structure | recursively build and validate hierarchy |
| Local grammar | recursively compose nested role/value frames |
| Document context | demand-driven graph traversal and dependency solving |
| Contour A | no context recursion; preserve literal mention projection |
| Contour B | reduce compatible field claims, without creating identity |
| Resolver | bounded alias/anaphora/endpoint binding traversal |
| Identity | consumes resolved claims; does not recursively search text |

## 9. Explicit non-adoption

The architecture does **not** adopt:

- a model deciding how to partition the document;
- recursive model calls;
- natural-language summaries as context authority;
- a code-generating REPL in the parser;
- whole-document prompt injection;
- vector similarity as a recursive edge;
- unconstrained self-calls or open-ended tool choice.

The only imported idea is externalized context plus bounded recursive
decomposition and reduction. Product semantics remain rule/data driven,
source-anchored, deterministic, and fail-closed.
