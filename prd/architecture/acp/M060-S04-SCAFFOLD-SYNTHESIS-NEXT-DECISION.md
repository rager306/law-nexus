# M060/S04: Scaffold synthesis and next decision

## Status

Final synthesis for M060 law-nexus-kit v0 isolated scaffold proof.

## Scope and authority boundary

This artifact synthesizes M060/S01, M060/S02, and M060/S03. It does not publish law-nexus-kit, does not initialize or mutate main `.lex`, and keeps source-truth migration blocked, production adoption blocked, and R035/R037/R038 validation blocked.

M060 remains a local scaffold proof milestone:

```text
repository-local scaffold + isolated local-equivalent runtime proof
```

not:

```text
external kit publishing
main repository adoption
production ACP backend adoption
```

## Executive decision

M060 result:

```text
PROCEED to review and scaffold hardening for law-nexus-kit v0.
```

But proceed only under these boundaries:

```text
- local-equivalent scaffold proof succeeded
- field-specific validation constraints are proven only for selected fields
- full owner/repo remote install remains unproven
- production adoption remains blocked
- main `.lex` adoption remains blocked
- source-truth migration remains blocked
- R035/R037/R038 validation remains blocked
```

The next work should not be adapter adoption. The next planned sequence remains:

```text
M061: ACP-kit validation strengthening
M062: Git-lex diagnostic adapter decision
```

A separate publishing/review decision may be planned later if the user explicitly approves external repository work.

## What M060 proved

| Area | Result | Evidence |
|---|---|---|
| Scaffold contract | Proven | S01 defined files, fixtures, blocked content, and proof gates. |
| Repository-local scaffold | Proven | S02 created `git-lex-kit-law-nexus/` with deterministic files and synthetic examples. |
| Configured-domain-kit stance | Proven as design/runtime-compatible | S01/S02 kept law-nexus-kit as configured domain kit, not ACP-kit dependency child. |
| Local-equivalent install | Proven | S02 installed scaffold into a disposable repo as `local/git-lex-kit-law-nexus`. |
| Generated-style shapes | Proven for proof setup | S02/S03 used generated-style multiline SHACL shapes for runtime parsing. |
| Class discovery | Proven | S02 `git-lex list --json` discovered 11 law-nexus classes. |
| Positive validation | Proven | S02 validated 11 synthetic files with all pass. |
| Sync/query/frontmatter retrieval | Proven | S02 sync/query succeeded and retrieved `Synthetic Legal Document` via `fm:title`. |
| Required-field negative | Proven for one field | S03 missing `LegalDocument.synthetic` produced exit 1 and violation output. |
| Enum negative | Proven for one field | S03 invalid `LegalDocument.proofStatus` produced exit 1 and violation output. |
| DateTime negative | Proven for one field | S03 invalid `ParserRun.observedAt` produced exit 1 and `Expected datatype: xsd:dateTime`. |
| Main checkout cleanliness | Proven | S01/S02/S03 no-main-state checks passed. |

## What remains unproven

| Area | Status | Consequence |
|---|---|---|
| Full owner/repo remote install | Unproven | Publishing/review must be a separate explicit decision. |
| Native dependency inheritance from ACP-kit | Unproven/blocked | law-nexus-kit remains configured-domain-kit, not ACP-kit child. |
| Object-link correctness | Unproven | S03 object-link negative candidate passed; do not claim object-link enforcement. |
| General validation correctness | Unproven | Claims must remain field-specific. |
| Datatype behavior across all fields | Unproven | Only `ParserRun.observedAt` dateTime negative is proven. |
| Generated shapes from ontology without local proof shaping | Partially proven | S02/S03 used generated-style runtime shapes; future hardening should align ontology generation and runtime shapes. |
| Production readiness | Unproven/blocked | M060 is not production adoption. |
| ACP backend/adoption fitness | Unproven/blocked | M062 owns adapter decision. |

## Blocked claims

Future artifacts must keep these blocked unless a later milestone explicitly proves and decides otherwise:

```text
Blocked: law-nexus-kit validates R035/R037/R038
```

```text
Blocked: git-lex validation proves LegalGraph parser completeness, FalkorDB behavior, citation safety, or Legal KnowQL quality
```

```text
Blocked: M060 approves main `.lex` adoption
```

```text
Blocked: M060 approves production adoption
```

```text
Blocked: M060 approves ACP source-truth migration
```

```text
Blocked: M060 approves external publishing or GitHub state changes
```

## Bounded validation claims allowed

Safe wording:

```text
M060 proved local-equivalent positive runtime compatibility for the repository-local law-nexus-kit v0 scaffold.
```

```text
M060 proved output-sensitive true negatives for selected generated-style constraints: `LegalDocument.synthetic` minCount, `LegalDocument.proofStatus` enum, and `ParserRun.observedAt` xsd:dateTime.
```

```text
Object-link correctness remains unproven because a literal-looking provider value passed validation.
```

Unsafe wording:

```text
Unsafe wording: law-nexus-kit validates all fields correctly
```

```text
Unsafe wording: law-nexus-kit is ready for production
```

```text
Unsafe wording: git-lex can now be adopted as ACP backend
```

## Implementation hardening recommendations

Before any publishing or external review, perform a hardening pass:

```text
1. align `law-nexus.ttl` ontology declarations with the generated-style runtime shape profile proven in S02/S03
2. ensure shape generation emits multiline parser-compatible `sh:targetClass` blocks
3. preserve synthetic/non-authoritative example policy
4. decide whether object-link constraints need a different true negative fixture strategy
5. add a small verifier script for scaffold file inventory, blocked content, and required shape terms
6. keep remote install proof separate until a full owner/repo target is explicitly approved
```

## Recommended next milestones

### M061: ACP-kit validation strengthening

Use M060 lessons, but keep the track separate:

```text
- domain/range/restriction/enum-generated SHACL proof
- positive validation proof
- output-sensitive true negative validation proof
- hard claims limited to proven constraints
```

M061 should not make law-nexus-kit a production backend or validate R035/R037/R038.

### M062: Git-lex diagnostic adapter decision

Use M060/M061 evidence to decide:

```text
- whether git-lex may be connected as an L2 diagnostic backend
- which evidence categories are allowed
- which categories remain ACP-native only
- state ownership, rollback, residue, and failure visibility contract
```

M062 should decide adapter fitness before any adapter implementation milestone.

## Final M060 decision

M060 is successful as a local scaffold proof:

```text
law-nexus-kit v0 scaffold: proceed to review/hardening
```

M060 is not sufficient for:

```text
remote install approval (blocked)
external publishing (blocked)
production adoption (blocked)
main `.lex` adoption (blocked)
source-truth migration (blocked)
general validation correctness (blocked)
R035/R037/R038 validation (blocked)
```

The safe next action is to carry M060 evidence into M061 validation strengthening and M062 adapter decision, while keeping law-nexus-kit publishing or adapter implementation behind explicit future confirmation and proof gates.
