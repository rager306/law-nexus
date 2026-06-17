# M059/S04: Layering synthesis and next gates

## Status

Final M059 synthesis for git-lex kit layering and law-nexus-kit feasibility.

## Scope and authority boundary

This artifact synthesizes M059/S01, M059/S02, and M059/S03. It does not implement law-nexus-kit, does not initialize or mutate main `.lex`, does not change external repositories, does not approve ACP-kit or git-lex source-truth migration, does not approve production adoption, and does not validate R035, R037, or R038.

## Executive conclusion

M059 supports proceeding to a future isolated law-nexus-kit scaffold proof, but only under a configured-domain-kit interpretation.

Proven safe interpretation:

```text
git-lex engine
+ implicit base kit
+ law-nexus-kit as the one configured deterministic domain kit
+ static/profile law-nexus semantics
+ diagnostic ACP boundary links
```

Not proven and not approved:

```text
git-lex engine
+ base-kit
+ ACP-kit as native installed dependency layer
+ law-nexus-kit as native dependency child
```

The architectural layering remains useful:

```text
git-lex -> base-kit -> ACP governance core -> law-nexus profile evidence projection
```

But it must be implemented as static/profile packaging and proof-boundary design, not assumed native runtime dependency inheritance.

## Proven, unproven, blocked matrix

| Area | M059 result | Evidence | Consequence |
|---|---|---|---|
| Existing kit prior art | Proven enough for pattern selection | S01 | Reuse deterministic domain-kit pattern; block Raw/adaptive/session authority patterns. |
| Base-kit role | Proven as substrate pattern | S01/S02 | Treat base as implicit mechanics, not ACP/law-nexus authority. |
| Native multi-kit dependency layering | Not proven | S02 | Do not design law-nexus-kit as a native child of ACP-kit. |
| Configured-domain-kit fallback | Proven as safest mechanics-aligned design | S02/S03 | Future scaffold should install law-nexus-kit as the configured kit. |
| law-nexus-kit v0 vocabulary | Designed, not implemented | S03 | Proceed only to isolated scaffold proof; no production adoption is approved. |
| ACP boundary links | Designed as diagnostic/navigation links | S03 | They may support review but cannot validate requirements by themselves. |
| Generated-shape hard validation | Still unproven | M058/S02/S03 | Required-field/enum claims need future true negative proof. |
| Main `.lex` adoption | Blocked | Existing gates | No main checkout git-lex state. |
| R035/R037/R038 validation | Blocked | Project boundary | Requires independent source/runtime/legal proof paths. |
| External publishing or GitHub changes | Not approved | Hard rule | Requires explicit user confirmation in a future step. |

## Safe proceed recommendation

Proceed to a future scaffold milestone only if it is explicitly scoped as:

```text
isolated disposable runtime proof of law-nexus-kit v0 scaffold
```

Allowed future scaffold work:

```text
1. create a deterministic law-nexus-kit scaffold in an isolated workspace or explicitly approved repo
2. use explicit full owner/repo kit spec for runtime proof
3. install only in disposable target repositories
4. prove generated classes/shapes from law-nexus ontology
5. prove positive validate/sync/query on synthetic examples
6. prove at least one true negative validation fixture before any hard validation claim
7. preserve no-main `.lex`, no Raw, no provider payload, no raw legal text, no ignored/local proof anchors
```

Do not proceed directly to:

```text
production adoption (blocked; do not proceed directly)
main repository `.lex` initialization (blocked)
ACP source-truth migration (blocked; do not proceed directly)
R035/R037/R038 validation claims (blocked)
external publishing without explicit confirmation (blocked)
```

## Separate track recommendation: ACP-kit validation strengthening

ACP-kit strengthening should remain a separate track from law-nexus-kit scaffold proof.

Why separate:

```text
M058 showed current ACP generated shapes are underconstrained.
S02 showed configured-kit shape generation depends on domain/range/restriction triples visible in the configured kit ontology.
S03 uses ACP links diagnostically and should not wait on ACP-kit becoming a hard validator.
```

ACP-kit strengthening gates:

```text
1. add generated-shape-relevant domain/range/restriction/enum declarations or generator support
2. regenerate ACP shapes
3. prove sh:datatype, sh:in, and sh:minCount appear where intended
4. prove true negative validation failures in isolated runtime fixtures
5. update wording from underconstrained diagnostic validation to hard validation only for proven constraints
```

This track may inform law-nexus-kit design, but it should not be bundled with the first law-nexus-kit scaffold proof unless explicitly planned.

## Future law-nexus-kit scaffold proof gates

A future scaffold milestone should pass these gates before any implementation closeout:

```text
G1: repository or workspace is isolated from main law-nexus checkout
G2: explicit full kit spec install succeeds
G3: install creates base plus law-nexus configured kit state
G4: generated law-nexus shapes contain expected target classes and properties
G5: git lex list --json discovers law-nexus classes
G6: synthetic examples validate positively
G7: sync/query retrieve safe frontmatter fields
G8: a true negative validation fixture fails non-zero or emits a clearly failing validation result
G9: no main `.lex`, Squad, Raw, or `.artifacts` residue appears
G10: no raw legal text, provider payloads, secrets, absolute local anchors, or ignored/local proof anchors become durable evidence
```

If the scaffold includes static ACP imports or copied ACP terms, add:

```text
G11: generated shapes see exactly the intended ACP-linked triples
G12: ACP-linked terms remain diagnostic and do not validate law-nexus profile requirements
```

## Blocked wording checklist

Future artifacts must not say:

```text
Unsafe wording: law-nexus-kit validates R035/R037/R038
```

```text
ACP proof gates are satisfied because a law-nexus-kit projection exists
```

```text
git-lex native dependency layering is proven for ACP-kit -> law-nexus-kit
```

```text
git-lex validation proves parser completeness, FalkorDB behavior, citation safety, or Legal KnowQL quality
```

```text
Unsafe wording: main `.lex` adoption or production adoption is approved by M059
```

Safe wording:

```text
M059 supports a future isolated scaffold proof for law-nexus-kit as a deterministic configured domain kit with diagnostic ACP boundary links.
```

## M059 decision summary

M059 should close with these decisions:

```text
1. Use base-kit as implicit substrate only.
2. Treat ACP-kit as reusable governance core and boundary reference.
3. Treat law-nexus-kit v0 as a deterministic configured domain kit.
4. Do not assume native dependency inheritance from ACP-kit.
5. Keep law-nexus-kit records diagnostic/profile-oriented unless accepted by separate proof gates.
6. Split future scaffold proof from ACP-kit validation strengthening.
7. Keep main `.lex`, source-truth migration, production adoption, and R035/R037/R038 validation blocked.
```

## Final M059 conclusion

The layering hypothesis is feasible only as a bounded architectural/static packaging strategy:

```text
git-lex -> implicit base substrate -> law-nexus configured domain kit
```

with ACP concepts retained as governance-core references:

```text
law-nexus observation -> diagnostic ACP boundary link -> ACP proof review
```

M059 does not authorize implementation in the main checkout. It authorizes planning the next isolated proof step.
