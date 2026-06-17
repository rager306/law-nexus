# SHAPE-BASELINE — acp.ttl current constraint surface (M058 baseline)

> Milestone M064-4aierx, slice S01, task T01.
> Pins the **'before' snapshot** of the SHACL constraint surface the git-lex shape
> generator can produce from `acp.ttl` at `owl:versionInfo "0.1.0"`, so S02
> (strengthen acp.ttl) and S03 (regenerate shapes) measure change against a
> documented, cross-checkable baseline instead of against memory.

## Purpose

The M058 root cause this baseline pins is:

> *Generated ACP shapes are underconstrained — no `sh:datatype` / `sh:in` /
> `sh:minCount` reaches any class shape.*

T01 fixes the 'before' numbers. T02 authors the strengthening contract
(`SHAPE-CONTRACT.md`); S02 implements it in acp.ttl; S03 regenerates and proves
the numbers move.

## Proof boundary (read first)

This baseline is a **static structural audit** grounded in:

- the current text of `git-lex-kit-acp/ontology/acp/acp.ttl` (264 lines), and
- the generator's **documented** domain-driven emission rule, established in
  `.gsd/milestones/M064-4aierx/slices/S01/S01-RESEARCH.md` from a read of the
  git-lex generator source.

It does **NOT**:

- run the git-lex generator (no binary is installed in this tree; git-lex is an
  external vendor dependency and is not executed here),
- reference or modify any path outside `/root/law-nexus`,
- validate R035/R037/R038, promote any record to ACP source truth, or approve
  main-`.lex` / production adoption.

**Empirical regenerate-and-inspect proof is S03's scope, not T01's.** The causal
link stated in §5 is a documented-rule argument, not a fresh runtime observation.

## Snapshot method

Counts are taken with `rg` against `acp.ttl` in this checkout (commands listed in
"Cross-check"). The numbers below are the literal output of those commands.

## 1. Enum-like datatypes: 3 declared, 1 wired, 2 orphaned

acp.ttl declares exactly **3 `rdfs:Datatype`s via `owl:oneOf`**:

| Datatype | `owl:oneOf` values | used as a property `rdfs:range`? |
|---|---|---|
| `acp:VerdictValue` | pass, fail, needs-attention, needs-remediation, blocked, not-applicable | **YES** — `acp:verdict rdfs:range acp:VerdictValue` |
| `acp:LifecycleStateValue` | proposed, active, validated, deferred, blocked, rejected, superseded | **NO** — orphaned (no property ranges over it) |
| `acp:AuthorityClassValue` | source, derived, diagnostic, runtime-smoke, profile-proof, blocked | **NO** — orphaned (no property ranges over it) |

**Lifecycle/authority distinction (the subtle point):** `LifecycleState` and
`AuthorityClass` are modeled as **`owl:Class`s** reached via **object
properties**, not as enum datatypes.

- `acp:hasLifecycleState` is an `owl:ObjectProperty`, `rdfs:range acp:LifecycleState`
  (an `owl:Class`). Its 7 named individuals (`ProposedState` … `SupersededState`)
  are written `a acp:LifecycleState` — i.e. **instances of the class**.
- `acp:hasAuthorityClass` is an `owl:ObjectProperty`, `rdfs:range acp:AuthorityClass`
  (an `owl:Class`). Its 6 named individuals (`SourceAuthority` … `BlockedAuthority`)
  are written `a acp:AuthorityClass` — i.e. **instances of the class**.

Consequence for the generator: object properties emit `sh:nodeKind sh:IRI` (an IRI
link to an individual), **not** `sh:in (...)` (an enum literal set). So even the
lifecycle/authority individuals can only ever produce `sh:nodeKind sh:IRI`. Only a
**datatype property** ranging over a `rdfs:Datatype` (i.e. `verdict` →
`VerdictValue`) could yield `sh:in`, and that path is blocked by the domain gap
(§4/§5).

Net: the two orphaned datatypes (`LifecycleStateValue`, `AuthorityClassValue`)
never reach any property at all; `VerdictValue` is wired to `verdict` but `verdict`
has no `rdfs:domain`. **Zero of the three enum datatypes currently reach a class
shape.**

## 2. `rdfs:domain` inventory: exactly 3, all object properties

Only **3 of 22 properties** carry `rdfs:domain` today, and all three are
**object properties**:

| Property | `rdfs:domain` | kind | `rdfs:range` |
|---|---|---|---|
| `acp:blocksClaim` | `acp:HealthFinding` | ObjectProperty | `acp:ValidationClaim` |
| `acp:validatesRequirement` | `acp:ValidationClaim` | ObjectProperty | `acp:Requirement` |
| `acp:doesNotValidateRequirement` | `acp:ValidationClaim` | ObjectProperty | `acp:Requirement` |

`rg -c 'rdfs:domain' acp.ttl` → **3**. Because these are object properties with
domains, the generator emits **`sh:nodeKind sh:IRI`** for each — and nothing else.
This is exactly the M058 observation (only 3 `sh:nodeKind sh:IRI` constraints reach
a class shape). The 1:1 mapping between these 3 domain'd properties and the 3
generated node-kind constraints is the confirmation of the root cause
(per S01-RESEARCH).

## 3. `owl:Restriction` / `owl:minCardinality` inventory: 0 / 0

- `rg -c 'owl:Restriction' acp.ttl` → **0**
- `rg -c 'owl:minCardinality' acp.ttl` → **0**

There are **no cardinality axioms anywhere** in acp.ttl. The generator's
`owl:Restriction` + `owl:minCardinality` → `sh:minCount` translation (Query 4) has
nothing to consume. **No `sh:minCount` is possible from the current file.**

## 4. Datatype properties: 10, all `rdfs:range`, none `rdfs:domain`

Every one of the **10 `owl:DatatypeProperty`s** defines a `rdfs:range` but **no
`rdfs:domain`**:

| DatatypeProperty | `rdfs:range` | has domain? | generator could emit (if domain'd) |
|---|---|---|---|
| `acp:identifier` | xsd:string | no | — (string skipped) |
| `acp:sourcePath` | xsd:string | no | — |
| `acp:selector` | xsd:string | no | — |
| `acp:nonAuthoritative` | xsd:boolean | no | `sh:datatype xsd:boolean` |
| `acp:blockedRequirementValidation` | xsd:string | no | — |
| `acp:proofLevel` | xsd:string | no | — |
| `acp:verdict` | `acp:VerdictValue` (enum) | no | `sh:in (...)` |
| `acp:sourceArtifact` | xsd:string | no | — |
| `acp:allowedNextAction` | xsd:string | no | — |
| `acp:blockedAction` | xsd:string | no | — |

Per the documented emission rule, **`xsd:string` ranges are skipped** — they
produce no `sh:datatype` at all. So even after a domain is added, the string-range
properties yield only structural/presence constraints, never datatype constraints.
Only `nonAuthoritative` (xsd:boolean) and `verdict` (enum) carry a non-trivial
range worth constraining.

Because **none of these 10 has a domain, none is visible to shape generation**
(see §5). No `sh:datatype` and no `sh:in` reaches any class shape today.

## 5. The M058 mechanism: domain-driven emission

The causal link from the structural facts above to the M058 symptom is the
generator's **domain-driven emission rule** (documented in S01-RESEARCH from the
git-lex generator source):

> The generator emits a property constraint for a class shape **iff** that property
> has `rdfs:domain <that class>`. Query 2 of `generate_shapes_from_store` puts
> `?prop rdfs:domain ?domain` in the **mandatory** WHERE clause (not `OPTIONAL`).
> A property with no `rdfs:domain` is therefore **invisible to shape generation**.

Combined with the three downstream translations (also documented there):

- `owl:oneOf` on a `rdfs:Datatype` → `sh:in (...)`,
- `owl:Restriction` + `owl:minCardinality`/`owl:cardinality ≥ 1` under
  `rdfs:subClassOf` → `sh:minCount 1`,
- non-string `xsd:` range → `sh:datatype xsd:{type}`,

the baseline explains M058 completely:

- **No `sh:datatype`** — the only non-string datatype property with a meaningful
  range is `nonAuthoritative` (xsd:boolean); it has no domain, so it is invisible.
  (xsd:string ranges are skipped regardless of domain.)
- **No `sh:in`** — the only enum-typed property is `verdict` → `VerdictValue`; it
  has no domain, so it is invisible. The other two enum datatypes are orphaned.
- **No `sh:minCount`** — there are 0 `owl:Restriction` / 0 `owl:minCardinality`.
- **Only `sh:nodeKind sh:IRI`** — produced by the exactly-3 object properties that
  do have domains (§2).

A property with no domain is invisible to shape generation; that single rule is why
the entire datatype/enum surface of acp.ttl never reaches a class shape.

## 6. Baseline counts (for S03's before/after diff)

| Generated-constraint kind | Baseline count | source of the zero |
|---|---|---|
| `sh:datatype` | **0** | no domain'd datatype property with a non-string range |
| `sh:in` | **0** | `verdict` (the only enum property) has no domain; the other two enums are orphaned |
| `sh:minCount` | **0** | 0 `owl:Restriction` / 0 `owl:minCardinality` |
| `sh:nodeKind sh:IRI` | **3** | the 3 domain'd object properties (§2) |

S02 adds enumerated `rdfs:domain` lists + 2 conservative
`owl:Restriction`/`owl:minCardinality 1` (per `SHAPE-CONTRACT.md`, T02); S03
regenerates and expects the first three rows to become **> 0** while the 3 existing
ACP positive fixtures still pass. This baseline fixes the "0/0/0" that S03 must
flip.

## Cross-check (run against acp.ttl in this checkout)

```
rg -c 'rdfs:domain'            git-lex-kit-acp/ontology/acp/acp.ttl   # expect 3
rg -c 'owl:Restriction'        git-lex-kit-acp/ontology/acp/acp.ttl   # expect 0 (no match)
rg -c 'owl:minCardinality'     git-lex-kit-acp/ontology/acp/acp.ttl   # expect 0 (no match)
rg -c 'owl:oneOf'              git-lex-kit-acp/ontology/acp/acp.ttl   # expect 3
rg -c 'a owl:DatatypeProperty' git-lex-kit-acp/ontology/acp/acp.ttl   # expect 10
rg -c 'a owl:ObjectProperty'   git-lex-kit-acp/ontology/acp/acp.ttl   # expect 12
```

Symbols cited (verify each is present / domain-less as claimed):
`acp:blocksClaim`, `acp:validatesRequirement`, `acp:doesNotValidateRequirement`
(the 3 domain'd properties); `acp:verdict` (only enum-typed property, no domain);
`acp:nonAuthoritative` (only boolean-typed property, no domain);
`acp:VerdictValue` / `acp:LifecycleStateValue` / `acp:AuthorityClassValue`
(the 3 `owl:oneOf` datatypes, of which only `VerdictValue` is referenced by a
property range).

## Explicitly NOT in this baseline's scope

- Empirical shape regeneration (S03) — this is a documented-rule argument only.
- The constraint-strengthening contract itself (T02 → `SHAPE-CONTRACT.md`).
- Authority-model enforcement, source-truth promotion, and R035/R037/R038
  validation — all deferred (D084 Stage 5 / D072) per the M064 vision and
  S01-RESEARCH.
