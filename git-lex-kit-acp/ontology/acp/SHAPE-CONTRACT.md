# SHAPE-CONTRACT — acp.ttl strengthening contract for S02

> Milestone M064-4aierx, slice S01 ("Shape-strengthening design"), task T02.
>
> This is **D084 Stage 1, Design B** (decision **D085**). It converts the
> `S01-RESEARCH.md` Design-B recommendation + D1–D7 decision tree into the
> **authoritative, S02-consumable spec**: the exact `rdfs:domain` lists and the
> two `owl:Restriction`/`owl:minCardinality 1` blocks S02 must add to
> `git-lex-kit-acp/ontology/acp/acp.ttl` so the git-lex shape generator emits
> meaningful `sh:datatype` / `sh:in` / `sh:minCount` constraints. S02 implements
> this verbatim; S03 regenerates + builds the true-negative fixtures; S04 proves
> `validate` rejects bad / accepts good and closes M058.
>
> Companion baseline: `SHAPE-BASELINE.md` (T01) pins the **before** snapshot
> (0/0/0 datatype/in/minCount). This contract pins the **target** snapshot S03
> must reach.

## Proof boundary (read first)

This contract is a **static design document** grounded in:

- the current text of `acp.ttl` (`owl:versionInfo "0.1.0"`),
- the proven reference template `git-lex-kit-law-nexus/ontology/law-nexus/law-nexus.ttl`, and
- the git-lex generator's **documented** domain-driven emission rule (established
  in `S01-RESEARCH.md` from a read of `/root/vendor-source/git-lex/src/shacl.rs`,
  `ontology.rs`, `extraction.rs`).

It does **NOT**:

- run the git-lex generator (git-lex is an external vendor dependency; empirical
  regenerate-and-inspect proof is **S03's** scope, not T02's),
- edit `acp.ttl` (that is **S02's** scope),
- reference or modify any path outside `/root/law-nexus`,
- validate R035/R037/R038, promote any record to ACP source truth, approve
  main-`.lex` / production adoption, or approve authority-model enforcement.

The strengthened `acp.ttl` and its generated SHACL shapes remain **derived /
non-authoritative** (R046). Strengthening constraints does **not** make the
ontology ACP source truth.

## Skills applied (locked from research)

- **design-an-interface** — the 3+ radically-different-designs contrast (A/B/C/D)
  was run in `S01-RESEARCH.md`; Design B was chosen. The contrast and the reason
  B wins are recorded in §2 below (the value was the contrast, not the first
  draft).
- **grill-me** — the D1–D7 decision tree from research is **locked** into §3.
  Every open branch is resolved; S02 implements against the resolutions, not
  against new design questions.
- **api-design** — adding SHACL constraints is a **tightening** change for
  existing data (additive-ish, but any previously-passing record that now
  violates a constraint breaks). The 3 committed examples are verified
  compatible (§6); the version is bumped 0.1.0 → 0.2.0 (§9).

---

## 1. Design contrast (Design It Twice — locked as D085)

Four approaches were contrasted in `S01-RESEARCH.md`. Condensed:

| Design | Shape | Why it loses / wins |
|---|---|---|
| **A — Minimal (domains only)** | Add `rdfs:domain` to underconstrained props; rely on existing enums + xsd ranges. | Loses: produces `sh:datatype` + `sh:in` but **no `sh:minCount`** → the `acp-missing-source-artifact` true-negative (one of the 5 target probes) cannot be built. Insufficient for the 5-probe target. |
| **B — Domain + OWL Restrictions** ✅ | A **plus** `owl:Restriction`/`owl:minCardinality 1` on selected authority fields, mirroring law-nexus.ttl. | **WINS — chosen (D085).** Only approach that (a) produces all three constraint kinds via the generator, (b) stays inside acp.ttl (S02 scope), (c) matches a proven local template, (d) keeps acp.ttl universally reusable (R048). |
| **C — Hand-author SHACL / bypass generator** | Ship a hand-written `acp-shapes.ttl`. | Loses: **defeats M064's purpose** — the milestone goal is that the *generated* shapes (the path `git lex kit-update` actually regenerates) are meaningful. Hand-authored shapes silently diverge on regen and violate R046. Rejected; named only to rule it out. |
| **D — Modify the generator** | Edit `/root/vendor-source/git-lex/src/shacl.rs`. | Loses: out of scope (external vendor dependency; D084 Stage 2); affects every kit (R048); supply-chain/binary-trust concerns. Possible future hardening once git-lex is pinned. |

**Why B wins:** it is the only approach that yields `sh:datatype` + `sh:in` +
`sh:minCount` *through the generator*, from ontology axioms S02 owns, matching a
proven template, with no external-dependency mutation and no reusability loss.

## 2. Decision tree (grill-me — locked, no open branches)

| # | Question | Locked resolution |
|---|---|---|
| **D1** | Ontology-only vs generator change? | **Ontology-only (Design B).** git-lex is an external vendor dependency; S02 is scoped to acp.ttl; a generator change affects all kits. law-nexus.ttl proves the ontology-only path. |
| **D2** | Mechanism per field type? | enum → existing `owl:oneOf` (needs domain) → `sh:in`; non-string xsd range → `sh:datatype`; **xsd:string is SKIPPED** (no `sh:datatype`, only structure/minCount); minCount → `owl:Restriction`+`owl:minCardinality 1`. |
| **D3** | Enumerate classes in `rdfs:domain` vs rely on superclass inheritance? | **ENUMERATE (mandatory).** The ACP hierarchy is flat: `ProofGate ⊑ lex-o:Process`, `EvidenceAnchor ⊑ lex-o:Reference`, etc. — only `Requirement`/`Decision` subclass `SourceRecord`. `rdfs:domain acp:SourceRecord` reaches **only** the SourceRecord NodeShape (no subclass expansion in Query 2). List every target class, comma-separated — exactly the law-nexus.ttl convention. |
| **D4** | How aggressive on minCount? | **Conservative.** Require minCount only where (a) all existing examples satisfy it, or (b) the class has no current example. Defer full authority-model minCount to D084 Stage 5 / D072. |
| **D5** | Which true-negative fixtures? | The 2 acp-kit-owned MEM539 scalar probes: `acp-invalid-verdict` (enum), `acp-missing-source-artifact` (minCount). Object-link negatives are OUT (D5/MEM538). |
| **D6** | Example-fixture compatibility? | **Hard gate:** all 3 ACP examples must still PASS after strengthening (proof in §6). If a constraint breaks an example, soften the constraint — never silently widen the ontology. |
| **D7** | law-nexus-kit generated shapes? | Treat law-nexus.ttl as the reference template; do **not** assume its generator output is correct until S03 tests it. (Law-nexus probe fixtures are out of acp.ttl scope; this is forward intelligence, not an S02 task.) |

---

## 3. Per-class domain table (S02 adds these `rdfs:domain` lists)

**Rule (D3):** every class that should carry the constraint is listed explicitly,
comma-separated, mirroring law-nexus.ttl (`rdfs:domain A, B, C ;`). Do **not**
rely on `SourceRecord` superclass expansion — enumerate `Requirement`/`Decision`
separately.

**Emission rule (D2):** `xsd:string` range → property shape with **NO
`sh:datatype`** (generator skips string); `xsd:boolean` → `sh:datatype
xsd:boolean`; enum `rdfs:Datatype` (`owl:oneOf`) → `sh:in (...)`; object property
→ `sh:nodeKind sh:IRI`.

### 3a. Datatype properties — add `rdfs:domain`

| Property | range | `rdfs:domain` (enumerate) | emits |
|---|---|---|---|
| `acp:nonAuthoritative` | xsd:boolean | `acp:SourceRecord, acp:Requirement, acp:Decision, acp:EvidenceAnchor, acp:ProofGate, acp:ValidationClaim, acp:HealthFinding, acp:Projection` | **`sh:datatype xsd:boolean`** (survives: ill-typed bool) |
| `acp:verdict` | `acp:VerdictValue` (enum) | `acp:ProofGate, acp:ValidationClaim` | **`sh:in (...)`** (survives: bad enum value) |
| `acp:identifier` | xsd:string | `acp:SourceRecord, acp:Requirement, acp:Decision` | structure only (string skipped) |
| `acp:sourcePath` | xsd:string | `acp:EvidenceAnchor, acp:SourceRecord` | structure only |
| `acp:sourceArtifact` | xsd:string | `acp:EvidenceAnchor, acp:ProofGate` | structure only + **minCount** via §4 on EvidenceAnchor |
| `acp:proofLevel` | xsd:string | `acp:ProofGate` | structure only |
| `acp:selector` | xsd:string | `acp:EvidenceAnchor` | structure only |
| `acp:blockedRequirementValidation` | xsd:string | `acp:HealthFinding, acp:ValidationClaim` | structure only |
| `acp:allowedNextAction` | xsd:string | `acp:HealthFinding` | structure only |
| `acp:blockedAction` | xsd:string | `acp:HealthFinding` | structure only |

> **NOTE (xsd:string gets no `sh:datatype`):** `identifier`, `sourcePath`,
> `sourceArtifact`, `proofLevel`, `selector`, `blockedRequirementValidation`,
> `allowedNextAction`, `blockedAction` are all `xsd:string`. After a domain is
> added, the generator emits a property shape for them **but skips the datatype
> map entry** (`prop.range != xsd:string` guard in `shacl.rs`). So they yield
> only structural presence / minCount — **never** a string-format/datatype
> constraint. Do not promise string validation. This is why `sourceArtifact`'s
> true-negative uses `sh:minCount` (§4), not a datatype.

> **NOTE on `blockedRequirementValidation`:** the `example-source-record.md`
> SourceRecord fixture carries this field, but `SourceRecord` is **intentionally
> not** in its domain (its semantic home is `ValidationClaim`/`HealthFinding`:
> "requirement whose validation is blocked/not-proven by this record"). On the
> SourceRecord NodeShape the field is therefore unconstrained and passes through
> — by design, no constraint added where none is warranted.

### 3b. Object properties — add `rdfs:domain` (→ `sh:nodeKind sh:IRI`)

These complete each class shape with an IRI-link property shape. **They are NOT
true-negatives (MEM538):** `frontmatter_to_turtle` normalizes any object-property
frontmatter value to a `urn:entity:{slug}` IRI, so a bad link **passes**, not
fails. They exist for nodeKind honesty + shape completeness, not rejection.

| Property | range | `rdfs:domain` (enumerate) |
|---|---|---|
| `acp:hasEvidenceAnchor` | `acp:EvidenceAnchor` | `acp:SourceRecord, acp:ValidationClaim` |
| `acp:requiresProofGate` | `acp:ProofGate` | `acp:Requirement, acp:ValidationClaim` |
| `acp:satisfiesProofGate` | `acp:ProofGate` | `acp:EvidenceAnchor, acp:ValidationClaim` |
| `acp:hasLifecycleState` | `acp:LifecycleState` | `acp:SourceRecord, acp:ValidationClaim, acp:HealthFinding` |
| `acp:hasAuthorityClass` | `acp:AuthorityClass` | `acp:SourceRecord, acp:ValidationClaim, acp:HealthFinding, acp:Projection` |
| `acp:derivedFrom` | (none) | `acp:Projection` |
| `acp:constrainedByProfile` | `acp:ProfileConstraint` | `acp:SourceRecord` |
| `acp:implementedByAdapter` | `acp:RuntimeAdapter` | `acp:HealthFinding` |
| `acp:observedInCommit` | `git:Commit` | `acp:SourceRecord, acp:Requirement, acp:Decision, acp:EvidenceAnchor, acp:ProofGate` |

> `implementedByAdapter` (range `RuntimeAdapter`) is scoped to `HealthFinding`,
> the diagnostic-finding record that a runtime adapter implements (comment:
> "diagnostic process or record"). `observedInCommit` (range `git:Commit`) is the
> optional git-provenance helper (comment: "must not replace evidence anchors");
> its domain is the tracked-record surface that most carries provenance. Both are
> low-stakes for the generator (object props only ever emit `sh:nodeKind sh:IRI`)
> and are assigned for shape completeness, not rejection.

**Already domain'd (leave as-is — 3, the baseline nodeKind producers):**
`acp:blocksClaim`→`acp:HealthFinding`, `acp:validatesRequirement`→`acp:ValidationClaim`,
`acp:doesNotValidateRequirement`→`acp:ValidationClaim`.

**Domain-count arithmetic:** 10 datatype + 9 new object = **19 `rdfs:domain`
additions** (+3 existing = 22 total). law-nexus.ttl carries 16 for comparison.

---

## 4. Two conservative minCount restrictions (exactly 2)

Mirror law-nexus.ttl exactly: an `owl:Restriction` + `owl:minCardinality 1` under
the class's `rdfs:subClassOf`. The generator's Query 4 translates this to
`sh:minCount 1`.

**Restriction 1 — `verdict` on `ProofGate`:**
```turtle
acp:ProofGate rdfs:subClassOf [
  a owl:Restriction ;
  owl:onProperty acp:verdict ;
  owl:minCardinality 1
] .
```
Example compatibility (D4a): `example-proof-gate.md` has `verdict: "not-applicable"`
→ minCount 1 satisfied → still passes. Gives the `acp-invalid-verdict`
true-negative (§7).

**Restriction 2 — `sourceArtifact` on `EvidenceAnchor`:**
```turtle
acp:EvidenceAnchor rdfs:subClassOf [
  a owl:Restriction ;
  owl:onProperty acp:sourceArtifact ;
  owl:minCardinality 1
] .
```
Example compatibility (D4b): **no `EvidenceAnchor` example exists today** →
nothing to break → safe. S03 adds an `EvidenceAnchor` positive fixture (with
`sourceArtifact`) so the constraint has a passing counterpart. Gives the
`acp-missing-source-artifact` true-negative (§7).

**Intentionally NOT added (stay conservative — research D4):**
- Mandatory `nonAuthoritative` minCount on record classes — would over-constrain;
  `nonAuthoritative` is a *marker*, not a structural requirement.
- The optional `ValidationClaim rdfs:subClassOf [ … verdict … minCardinality 1 ]`
  (mentioned in research) is **dropped** to keep the set at exactly two. No
  `ValidationClaim` example exists today; if S03 adds one, it can revisit.
- **Full authority-model minCount** (mandatory `hasLifecycleState` +
  `hasAuthorityClass` + `hasEvidenceAnchor` on authoritative records) is
  **deferred to D084 Stage 5 / D072** (§8). It would break the 3
  non-authoritative examples and pull in authority-model scope the roadmap assigns
  to a later stage.

The contract therefore defines **exactly 2** `owl:Restriction`/`owl:minCardinality`
blocks (matching law-nexus.ttl's count of 2).

---

## 5. Authority-class mapping (design-level R041/R042 support)

This is a **DESIGN MAPPING ONLY**, not enforcement. It documents which constrained
fields carry which authority semantics, so the eventual Stage-5 authority model
(D072) has a field-to-authority table to build on. S02 does **not** implement
enforcement from this; it only adds the domains + 2 restrictions of §3–§4.

| Authority semantics | Constrained fields (from §3/§4) | why |
|---|---|---|
| **Source authority** | `sourceArtifact`, `sourcePath`, `selector`, `hasEvidenceAnchor` | point at a tracked repository-relative source / proof pointer (`EvidenceAnchor`, `SourceRecord`). These are the "where is the source?" surface. |
| **Profile-proof authority** | `verdict`, `requiresProofGate`, `satisfiesProofGate`, `proofLevel` | gate/claim verdict + the proof-gate machinery that must be satisfied before a claim validates (`ProofGate`, `ValidationClaim`). These are the "was it proven?" surface. |
| **Authority-declaration marker** | `nonAuthoritative` | explicit boolean marker that a record is an example / projection / prototype and is **not** authoritative until lifecycle + evidence + proof-gate requirements are met. |
| **Lifecycle / classification** | `hasLifecycleState`, `hasAuthorityClass` | object links to the `LifecycleState` / `AuthorityClass` individuals (currently `sh:nodeKind sh:IRI` only; their enum datatypes `LifecycleStateValue`/`AuthorityClassValue` are orphaned and out of M064 scope). |

**R041/R042 status:** this mapping *supports* the source-record / lifecycle-health
authority model at the design level. Full enforcement (mandatory authority fields
on authoritative records) is Stage 5 / D072 (§8).

---

## 6. Positive-fixture compatibility proof (D6 hard gate)

For each committed ACP example, show every **set** field is permitted and every
**required** field under the strengthened set is satisfied, so all 3 still
validate. Verified against the actual frontmatter in this checkout.

### example-source-record.md (`acp:SourceRecord`)
Set fields: `identifier="example-source-record"`, `sourcePath="…M049-S05…"`,
`nonAuthoritative=true`, `blockedRequirementValidation=[R035,R037,R038]`.
- `nonAuthoritative=true` → SourceRecord ∈ domain → `sh:datatype xsd:boolean`; `true` is well-typed → **passes**.
- `identifier`, `sourcePath` → xsd:string, structure only (no datatype) → **pass**.
- `blockedRequirementValidation` → not in SourceRecord domain (§3a note) → unconstrained on SourceRecord NodeShape → **passes** (emitted as plain string literals).
- No minCount restriction targets SourceRecord → nothing required-absent. **✓ PASS.**

### example-decision.md (`acp:Decision`)
Set fields: `identifier="example-decision"`, `sourcePath="…ROADMAP…"`,
`nonAuthoritative=true`.
- `nonAuthoritative=true` → Decision ∈ domain → `sh:datatype xsd:boolean`; `true` → **passes**.
- `identifier`, `sourcePath` → string, structure only → **pass**.
- No minCount restriction targets Decision → nothing required-absent. **✓ PASS.**

### example-proof-gate.md (`acp:ProofGate`)
Set fields: `identifier`, `proofLevel="synthetic-example"`,
`verdict="not-applicable"`, `nonAuthoritative=true`,
`blockedAction=[main runtime state adoption, source-truth migration, profile requirement validation]`.
- `verdict="not-applicable"` → ProofGate ∈ domain → `sh:in` VerdictValue; `"not-applicable"` ∈ {pass, fail, needs-attention, needs-remediation, blocked, not-applicable} → **passes**.
- `verdict` minCount 1 (Restriction 1) → present → **satisfied**.
- `nonAuthoritative=true` → ProofGate ∈ domain → `sh:datatype xsd:boolean`; `true` → **passes**.
- `proofLevel`, `blockedAction` → string, structure only → **pass**.
- `identifier` → string, structure only → **pass**. **✓ PASS.**

**No example lacks a now-required field.** All 3 committed ACP examples validate
under the strengthened set. S03/S04 must keep this as a regression assertion.

---

## 7. True-negative plan (for S03) — 2 probes + explicit exclusions

S03 builds exactly **2** acp-kit true-negative fixtures (the acp-kit-owned MEM539
scalar probes). Each must cause `git-lex validate` to exit **≠ 0** with a
per-result SHACL violation message (the linchpin for S04's closeout).

| Probe | Fixture shape | Constraint violated | why it survives frontmatter → turtle |
|---|---|---|---|
| **`acp-invalid-verdict`** | `acp:ProofGate` with `verdict: "totally-bogus"` | `sh:in` (VerdictValue) | `frontmatter_to_turtle` emits a bad enum value as a **plain string literal** `"totally-bogus"`; the `sh:in` set rejects it. **SURVIVES.** |
| **`acp-missing-source-artifact`** | `acp:EvidenceAnchor` **without** `sourceArtifact` | `sh:minCount 1` (Restriction 2) | field absent → minCount violation. **SURVIVES.** (No EvidenceAnchor example today; S03 adds a passing EvidenceAnchor fixture alongside this failing one.) |

### Explicitly EXCLUDED true-negatives (do NOT build these — they will not fail)

- **Object-link negatives (MEM538 block).** `frontmatter_to_turtle`
  (`extraction.rs`) classifies a property as object-property iff the generated
  shapes mark it `sh:nodeKind sh:IRI`, and **normalizes** any such value to a
  `urn:entity:{slug}` IRI. So a wrong/broken object link (`hasEvidenceAnchor`,
  `requiresProofGate`, `satisfiesProofGate`, `hasLifecycleState`,
  `hasAuthorityClass`, `derivedFrom`, `constrainedByProfile`,
  `implementedByAdapter`, `observedInCommit`) **passes** (becomes a well-formed
  IRI), not fails. Do not use object-property constraints as true-negatives.
- **xsd:string-only properties.** `identifier`, `sourcePath`, `proofLevel`,
  `selector`, `blockedRequirementValidation`, `allowedNextAction`,
  `blockedAction` have no `sh:datatype` (string is skipped) and no minCount, so a
  bad/missing string value has **no constraint to violate**. Do not build
  string-only negatives.

The surviving negative kinds are therefore exactly: **enum (`sh:in`)** and
**required-field (`sh:minCount`)** — the 2 probes above. (A boolean
`sh:datatype` negative is theoretically possible but **at-risk** — see §10 R2 —
and is not in the 2-probe acp-kit set.)

---

## 8. Explicit deferrals (out of M064 scope)

The following are **NOT** delivered by this contract / M064 and must not be
claimed as validated:

- **Full authority-model enforcement** (mandatory `hasLifecycleState` +
  `hasAuthorityClass` + `hasEvidenceAnchor` on authoritative records) → **deferred
  to D084 Stage 5 / D072.** M064 is scoped to "meaningful constraints +
  true-negative proof", not authority-model enforcement.
- **R035 / R037 / R038** are **NOT validated** by M064 (roadmap vision states
  this explicitly). Strengthened acp.ttl does not validate profile-owned
  requirements.
- **`acp.ttl` remains derived / non-authoritative (R046).** Constraint
  strengthening does not promote the ontology (or its generated shapes) to ACP
  source truth.
- **NO law-nexus-specific constraints enter `acp.ttl` (R048).** FalkorDB, parser,
  Russian-legal-evidence, retrieval, citation, generated-Cypher, and
  R035/R037/R038 constraints belong in `law-nexus.ttl`, not the reusable core.
  `acp.ttl` must stay **universally reusable**.
- **Enum coverage of lifecycle/authority.** The orphaned enum datatypes
  `LifecycleStateValue` / `AuthorityClassValue` are left as-is (lifecycle/authority
  are modeled as object properties → `sh:nodeKind sh:IRI`). Wiring them is out of
  scope.
- **git-lex generator change (Design D).** Out of scope; possible future hardening
  once git-lex is pinned (D084 Stage 2).

---

## 9. S02 implementation checklist (directly implementable, no further design)

S02 edits **only** `git-lex-kit-acp/ontology/acp/acp.ttl`. Build order (each step
independently committable), taken from `S01-RESEARCH.md` "Forward Intelligence":

1. **(tripwire, before editing acp.ttl)** Run the First Proof: init
   `git-lex-kit-law-nexus` in a disposable `/tmp` workspace and confirm the
   generated `law-nexus-shapes.ttl` contains `sh:datatype xsd:boolean` /
   `sh:in (` / `sh:minCount 1`. If law-nexus does **not** generate constraints
   despite having the right axioms, STOP and surface the generator bug before
   editing acp.ttl (MEM541 trap). *[This is S02's first action, not S01's.]*
2. Add the **10 datatype-property `rdfs:domain`** lists (§3a).
3. Add the **9 object-property `rdfs:domain`** lists (§3b).
4. Add the **2 `owl:Restriction`/`owl:minCardinality 1`** blocks (§4).
5. Bump `owl:versionInfo` **"0.1.0" → "0.2.0"** and note the constraint set in the
   ontology header comment (api-design: tightening change → version bump +
   documented contract).
6. Re-init acp-kit in a disposable ws; assert the generated `acp-shapes.ttl`
   contains `sh:datatype xsd:boolean` (nonAuthoritative), `sh:in (` (verdict),
   `sh:minCount 1` (verdict on ProofGate, sourceArtifact on EvidenceAnchor), and
   that the 3 examples still pass (§6 regression). Leave no main-repo
   `.lex`/`Squad`/`Raw`/`.artifacts` residue (MEM538, R047).

**What S02 must NOT do:** edit the generator; commit a `-shapes.ttl` (always
regenerated, never committed); hand-author SHACL (Design C); add any minCount
beyond the 2 in §4; add any law-nexus-specific constraint (R048); touch
`SHAPE-BASELINE.md` or M058 synthesis (R3 — S04 owns the wording-guard
reconciliation).

---

## 10. Risks carried forward (S02/S03/S04 own the empirical resolution)

- **R1 — xsd:string gets no `sh:datatype`.** Generator `prop.range != xsd:string`
  guard. Mitigated: the `sourceArtifact` negative uses `sh:minCount`, not a
  datatype. Do not promise string validation.
- **R2 — boolean `sh:datatype` negative is at-risk (unproven).**
  `frontmatter_to_turtle` emits `"not-a-boolean"^^xsd:boolean`; whether oxigraph
  `ReaderMode::Strict` parse-rejects it or `sh:datatype` flags the bad lexical form
  must be confirmed in S03. The `sh:in` (verdict) and `sh:minCount`
  (sourceArtifact) negatives are robust regardless, which is why they are the 2
  chosen probes.
- **R3 — M058 CI wording guard goes stale at closeout.**
  `scripts/verify-acp-ci-contract.py` requires `M058-S03-…md` to contain the
  literal "current generated ACP shapes are too underconstrained". **S01/S02 must
  NOT touch M058-S03** (would break the guard mid-milestone). S04 owns the
  synthesis + guard reconciliation.
- **R4 — flat ACP hierarchy mandates enumeration (D3).** Do not set
  `rdfs:domain acp:SourceRecord` expecting ProofGate/EvidenceAnchor coverage — it
  will not reach them. Enumerate every target class.
- **R5 — the "never executed the named fix" trap (MEM541).** M064 must actually
  execute: strengthen acp.ttl **and** regenerate **and** prove non-zero exit. The
  First Proof (§9 step 1) is the cheap tripwire.
- **R6 — single-kit validate limitation (D7).** `cmd_validate` loads one kit's
  shapes; the law-nexus probes need law-nexus-kit shapes, run per-kit.
- **R7 — tightening change / versioning (api-design).** Constraints are breaking
  for any record that previously passed but now violates. Today only the 3
  non-authoritative examples exist (verified compatible §6). Version bump +
  documented contract (§9 step 5) communicate the v0.2 contract to future
  reusers.

---

## Failure Modes

This task (T02) authors a **static design contract**; it performs no runtime,
network, or subprocess work. Its dependencies and their failure paths:

- **Input-file staleness (filesystem).** The contract is grounded in the current
  text of `acp.ttl` (`owl:versionInfo "0.1.0"`), `law-nexus.ttl`, the 3 example
  fixtures, and `SHAPE-BASELINE.md`. If any is edited between T02 and S02, the
  contract's domain tables / compat proof go stale. **Mitigation:** the contract
  pins the exact baseline counts (§SHAPE-BASELINE cross-check: 3 domain / 0
  restriction / 0 minCardinality / 3 oneOf / 10 datatype / 12 object) and the
  version (0.1.0); S02's step 6 re-derives against the regenerated shapes, and
  any drift surfaces there.
- **Generator-behavior assumption (external vendor dependency).** The contract's
  emission predictions rest on the git-lex generator's **documented**
  domain-driven rule (read from `/root/vendor-source/git-lex/src/shacl.rs`). If
  the installed/pinned git-lex behaves differently (namespace detection, Query 2
  change, `xsd:string` guard removed), S02 would "implement constraints" that
  still produce empty shapes — reproducing the MEM541 trap. **Mitigation:** §9
  step 1 mandates the First Proof (regenerate law-nexus shapes in a disposable
  workspace) **before** editing acp.ttl; if the generator does not emit
  constraints from law-nexus.ttl's existing axioms, S02 stops and surfaces the
  bug rather than propagating it.
- **Tightening-change breakage (downstream).** Adding constraints is breaking for
  any previously-passing record that now violates one. **Mitigation:** §6 proves
  the 3 committed examples still validate; no other records exist in the kit
  today; version is bumped 0.1.0 → 0.2.0 (§9 step 5).

This task has no network, API, or long-running-subprocess dependencies.

## Load Profile

Not applicable. T02 produces a static markdown contract; there is no runtime load
surface (no throughput, concurrency, memory, or request volume dimension). The
downstream artifact it specifies (`acp.ttl` + generated SHACL) is a build-time
ontology, not a serving path — its "load" is a one-shot `git lex kit-update`
regeneration sized by the fixed ontology, not by external traffic.

## Negative Tests

The contract's own verification (DONE-WHEN) and the negative tests it **designs**
for S03/S04:

- **Contract artifact verification (this task):** `test -f
  git-lex-kit-acp/ontology/acp/SHAPE-CONTRACT.md && rg -q 'ProofGate' … && rg -q
  'EvidenceAnchor' … && rg -q 'invalid-verdict' … && rg -q 'missing-source-artifact'
  …` — asserts the contract covers the two target classes and names both
  true-negative probes. (Run in §Verification below.)
- **Positive-fixture regression (§6, S03/S04):** `git-lex validate` on the 3 ACP
  examples must exit 0 after strengthening — guards against a constraint that
  wrongly rejects a good record.
- **True-negative fixtures the contract specifies for S03 (§7):**
  - `acp-invalid-verdict` — `ProofGate` with `verdict: "totally-bogus"` → must
    exit ≠ 0 via `sh:in` violation (boundary: a value outside the 6-element
    VerdictValue enum).
  - `acp-missing-source-artifact` — `EvidenceAnchor` without `sourceArtifact` →
    must exit ≠ 0 via `sh:minCount 1` violation (boundary: required field absent).
  - **Excluded negatives (asserted as non-failing):** object-link probes (would
    pass via `urn:entity:*` IRI normalization — MEM538) and xsd:string-only
    properties (no constraint to violate). These are named so S03 does not waste a
    fixture on a non-failing case.

S04 closes M058 by flipping the 2 scalar probes to non-zero exit while the 3
positive examples stay at exit 0.

## Verification

Cross-checked against the live checkout (commands run in this task):

- `acp.ttl` baseline counts confirmed: 3 `rdfs:domain`, 0 `owl:Restriction`, 0
  `owl:minCardinality`, 3 `owl:oneOf`, 10 `a owl:DatatypeProperty`, 12
  `a owl:ObjectProperty` — matches `SHAPE-BASELINE.md`.
- `law-nexus.ttl` reference pattern confirmed: 16 `rdfs:domain`, 2
  `owl:Restriction`, 2 `owl:minCardinality` — the comma-list + oneOf + Restriction
  pattern S02 mirrors.
- All 3 example fixtures read; frontmatter fields match the §6 compat proof
  (`example-source-record`: identifier/sourcePath/nonAuthoritative/blockedRequirementValidation;
  `example-decision`: identifier/sourcePath/nonAuthoritative; `example-proof-gate`:
  identifier/proofLevel/verdict="not-applicable"/nonAuthoritative/blockedAction).
- Contract artifact present and section-complete (DONE-WHEN rg checks).
