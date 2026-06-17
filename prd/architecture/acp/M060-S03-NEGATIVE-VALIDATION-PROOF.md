# M060/S03: Output-sensitive negative validation proof

## Status

Negative validation proof complete for the local law-nexus-kit v0 scaffold.

## Scope and authority boundary

This proof uses isolated disposable runtime repositories and the repository-local `git-lex-kit-law-nexus` scaffold. It does not publish the kit, does not initialize or mutate main `.lex`, does not approve source-truth migration, does not approve production adoption, and does not validate R035, R037, or R038.

The proof is output-sensitive:

```text
validation exit code and validation output are both recorded
```

This is required because earlier M060/S02 debugging showed validation behavior can be misleading if only one signal is considered.

## Runtime setup

The S03 runtime proof recreated the M060/S02 local-equivalent setup in disposable repositories:

```text
1. git init disposable repo
2. git-lex init --kit base
3. copy repository-local law-nexus scaffold into `.lex/kit/local/git-lex-kit-law-nexus`
4. copy law-nexus ontology into `.lex/ontology/law-nexus/`
5. set `.lex/repo.yml` kit to `local/git-lex-kit-law-nexus`
6. install synthetic content
7. write generated-style law-nexus SHACL shapes
8. run git-lex validate with stdout/stderr captured
```

Runtime binary was the same local debug binary used in S02; the path is a runtime observation, not a durable proof anchor.

## Shape profiles tested

### Baseline profile

The baseline shape profile included:

```text
sh:targetClass for all 11 law-nexus classes
sh:minCount 1 for LegalDocument.synthetic
sh:minCount 1 for ParserRun.observedAt
sh:in for proofStatus values: example-only, observed-runtime, blocked
sh:nodeKind sh:IRI for object-link properties
no datatype constraints
```

Purpose:

```text
Prove minCount and enum behavior without reintroducing datatype sensitivity into the positive baseline.
```

### Datatype probe profile

The datatype probe shape profile included:

```text
LegalDocument.synthetic -> sh:datatype xsd:boolean + sh:minCount 1
ParserRun.observedAt -> sh:datatype xsd:dateTime + sh:minCount 1
```

Purpose:

```text
Test whether datatype constraints can produce an output-sensitive true negative without breaking the positive baseline.
```

## Probe results

### Baseline positive validation

Fixture set:

```text
11 synthetic scaffold examples
```

Result:

```text
VALIDATE[baseline]_CODE=0
Validated 11 files ... all pass ✓
```

Interpretation:

```text
Positive baseline still passes with minCount, enum, and object-link shape profile.
```

### N1: Required/minCount negative

Malformed fixture:

```yaml
title: Negative Missing Synthetic
law-nexus.LegalDocument.nonAuthoritative: true
law-nexus.LegalDocument.proofStatus: example-only
law-nexus.LegalDocument.documentId: negative-missing-synthetic
```

Missing field:

```text
law-nexus.LegalDocument.synthetic
```

Result:

```text
VALIDATE[mincount]_CODE=1
LawNexus/LegalDocument/negative-missing-synthetic.md — 1 violation(s)
Validated 12 files ... 1 violation(s) in 1 file(s)
```

Interpretation:

```text
PASS: minCount enforcement produced both non-zero exit code and violation output for this specific required field.
```

Bounded claim allowed:

```text
The local law-nexus generated-style shapes can enforce `sh:minCount 1` for `LegalDocument.synthetic` in this isolated setup.
```

### N2: Enum negative

Malformed fixture:

```yaml
title: Negative Invalid Proof Status
law-nexus.LegalDocument.synthetic: true
law-nexus.LegalDocument.nonAuthoritative: true
law-nexus.LegalDocument.proofStatus: definitely-invalid
law-nexus.LegalDocument.documentId: negative-invalid-proof-status
```

Invalid field:

```text
law-nexus.LegalDocument.proofStatus
```

Allowed values in shape:

```text
example-only
observed-runtime
blocked
```

Result:

```text
VALIDATE[enum]_CODE=1
LawNexus/LegalDocument/negative-invalid-proof-status.md — 1 violation(s)
Validated 12 files ... 1 violation(s) in 1 file(s)
```

Interpretation:

```text
PASS: enum `sh:in` enforcement produced both non-zero exit code and violation output for this specific field.
```

Bounded claim allowed:

```text
The local law-nexus generated-style shapes can enforce bounded `proofStatus` values in this isolated setup.
```

### N3: Object-link negative candidate

Malformed candidate fixture:

```yaml
title: Negative Object Link Candidate
law-nexus.LegalDocument.synthetic: true
law-nexus.LegalDocument.nonAuthoritative: true
law-nexus.LegalDocument.proofStatus: example-only
law-nexus.LegalDocument.documentId: negative-object-link
law-nexus.LegalDocument.provider: "not an iri with spaces"
```

Shape constraint:

```text
lawNexus:provider -> sh:nodeKind sh:IRI
```

Result:

```text
VALIDATE[object]_CODE=0
Validated 12 files ... all pass ✓
```

Interpretation:

```text
BLOCKED: object-link nodeKind enforcement is not proven by this negative candidate.
```

Likely explanation:

```text
As in M058, object-property frontmatter values may be normalized to IRIs for validation. Therefore literal-looking object-link values are not reliable true negatives.
```

Blocked claim:

```text
Do not claim law-nexus-kit validates object-link correctness from this proof.
```

### N4: Datatype positive and negative probe

Datatype positive fixture set:

```text
11 synthetic scaffold examples
```

Datatype positive result:

```text
VALIDATE[datatype_positive]_CODE=0
Validated 11 files ... all pass ✓
```

Datatype negative fixture:

```yaml
title: Negative Invalid Date
law-nexus.ParserRun.synthetic: true
law-nexus.ParserRun.nonAuthoritative: true
law-nexus.ParserRun.proofStatus: example-only
law-nexus.ParserRun.observedAt: not-a-date
```

Datatype negative result:

```text
VALIDATE[datatype_negative]_CODE=1
LawNexus/ParserRun/negative-invalid-date.md — 1 violation(s)
→ Expected datatype: xsd:dateTime
Validated 12 files ... 1 violation(s) in 1 file(s)
```

Interpretation:

```text
PASS for `ParserRun.observedAt` dateTime in this isolated datatype probe.
```

Caution:

```text
S02 had an earlier datatype-shaped debug attempt that produced positive fixture violations. S03's generated-style datatype probe passed the positive baseline and failed the invalid date fixture. Therefore datatype enforcement is promising for generated-style shapes, but claims must remain field-specific until S04 synthesis and any future implementation hardening.
```

Bounded claim allowed:

```text
The local law-nexus generated-style shapes can enforce `xsd:dateTime` for `ParserRun.observedAt` in this isolated setup.
```

## Main checkout residue

Result:

```text
MAIN_RESIDUE=absent
```

Main checkout checks:

```bash
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
```

## Proven, unproven, blocked matrix

| Constraint / claim | Result | Allowed wording |
|---|---|---|
| Positive baseline with minCount/enum/object-link profile | Proven | 11 synthetic examples pass validation in isolated setup. |
| `sh:minCount 1` on `LegalDocument.synthetic` | Proven for this field | Required-field validation can catch missing `LegalDocument.synthetic` in isolated setup. |
| `sh:in` on `LegalDocument.proofStatus` | Proven for this field | Enum validation can catch out-of-set proofStatus in isolated setup. |
| `xsd:dateTime` on `ParserRun.observedAt` | Proven for this field | Datatype validation can catch invalid observedAt dateTime in isolated setup. |
| `xsd:boolean` on `LegalDocument.synthetic` | Partially exercised, not negative-proven here | Positive baseline can pass; no malformed boolean negative was used in final S03 proof. |
| `sh:nodeKind sh:IRI` on object-link values | Not proven by negative candidate | Do not claim object-link correctness enforcement from S03. |
| General git-lex validation correctness | Not proven | Claims must remain constraint-specific. |
| Full owner/repo remote install | Unproven | M060 used local-equivalent install because publishing is blocked. |
| Source-truth migration | Blocked | Not approved. |
| Production adoption | Blocked | Not approved. |
| R035/R037/R038 validation | Blocked | Not in scope and not proven. |

## Claim language

Safe wording:

```text
M060/S03 proved output-sensitive true negative validation for selected generated-style law-nexus constraints: required `LegalDocument.synthetic`, bounded `LegalDocument.proofStatus`, and `ParserRun.observedAt` dateTime.
```

```text
Object-link correctness remains unproven because a literal-looking provider value still passed validation.
```

Unsafe wording:

```text
Unsafe wording: law-nexus-kit validates all fields correctly
```

```text
Unsafe wording: git-lex validation now proves ACP or LegalGraph requirements
```

```text
Unsafe wording: law-nexus-kit validates R035/R037/R038
```

```text
Unsafe wording: M060 approves main `.lex`, production adoption, or source-truth migration
```

## S03 conclusion

M060/S03 upgrades law-nexus-kit v0 from positive-only validation evidence to bounded output-sensitive negative validation evidence for specific generated-style constraints:

```text
minCount: proven for LegalDocument.synthetic
sh:in: proven for LegalDocument.proofStatus
xsd:dateTime: proven for ParserRun.observedAt
```

It also keeps important limits explicit:

```text
object-link correctness remains unproven
full remote install remains unproven
general validation correctness remains unproven
source-truth migration, production adoption, and R035/R037/R038 validation remain blocked
```

S04 should synthesize M060 as a successful local scaffold proof with bounded validation evidence, not as production or ACP backend adoption.
