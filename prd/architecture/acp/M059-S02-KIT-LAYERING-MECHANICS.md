# M059/S02: Kit layering mechanics proof

## Status

Source-backed mechanics proof in progress. Runtime proof is not required for the core dependency-chain answer because the source path is explicit: git-lex currently installs base plus one configured domain kit, not an arbitrary native dependency chain.

## Scope and authority boundary

This artifact inspects git-lex kit mechanics as runtime/source observation. It does not create law-nexus-kit, does not change external repositories, does not initialize or mutate main `.lex`, does not approve ACP-kit or git-lex source-truth migration, does not approve production adoption, and does not validate R035, R037, or R038.

GitNexus source indexing for the git-lex reference repository was not available in the current environment, so this proof uses focused local source inspection as runtime observation. No external absolute source path is used as a durable proof anchor.

## Question being answered

Target layering hypothesis:

```text
git-lex -> base-kit -> acp-kit -> law-nexus-kit
```

S02 asks whether this is:

```text
A. native runtime dependency layering supported by git-lex kit install; or
B. architectural/static packaging where one configured domain kit contains/imports the needed profile semantics while base remains implicit.
```

## Source inspection findings

### 1. Kit spec resolution supports short form or owner/repo form

Observed behavior:

```text
short spec: soul -> repolex-ai/git-lex-kit-soul
full spec: owner/repo -> owner/repo, short name strips git-lex-kit-
```

Implication:

```text
For ACP runtime work, continue using the explicit full spec `rager306/git-lex-kit-acp`. Short `acp` is not canonical for this project.
```

For a future law-nexus-kit, explicit full owner/repo spec should be preferred unless the intended repository is published under the default short-name mapping.

### 2. Init installs base plus one domain kit

The init path states and implements:

```text
Every repo gets the base kit.
If --kit is specified, that kit is installed alongside base, not instead of it.
The repo.yml kit field records the domain kit.
Base is implicit and always present.
```

Installation flow:

```text
1. resolve configured kit spec
2. fetch/install base kit
3. if configured kit differs from base, fetch/install that one additional kit
4. install scaffold files from base and domain kit
5. write repo.yml kit: <configured domain kit>
6. generate SHACL shapes for the configured kit
7. create type folders for the configured kit
```

Implication:

```text
git-lex currently has base-plus-one-domain-kit install semantics, not arbitrary multi-kit dependency semantics.
```

### 3. kit.yml is read only for the configured kit

The folder/type creation path reads:

```text
install folders
folder base
folder ontology
init_prompts
adaptive
```

from the configured kit's installed `kit.yml`.

Implication:

```text
law-nexus-kit v0 should have its own deterministic kit.yml. It should not assume git-lex will read an ACP-kit dependency's kit.yml as part of a chain.
```

### 4. Ontology install behavior depends on static versus adaptive kit

Static kits:

```text
ontology/ -> .lex/ontology/
```

Adaptive kits:

```text
ontology/ -> _ontology/
```

with different overwrite behavior.

Implication:

```text
law-nexus-kit v0 should remain static/deterministic. It should avoid adaptive ontology behavior for v0.
```

### 5. Shape generation loads only the configured kit ontology

Shape generation flow:

```text
find the configured kit TTL
load that TTL into an in-memory RDF store
derive classes and properties from that store
write <short>-shapes.ttl next to the kit TTL
```

The shape generator derives:

```text
classes: owl:Class in the kit namespace
properties: owl:DatatypeProperty or owl:ObjectProperty with rdfs:domain
required fields: owl:Restriction with minCardinality/cardinality
node kind: ObjectProperty -> sh:nodeKind sh:IRI
enums: rdfs:Datatype owl:oneOf -> sh:in
datatypes: xsd non-string ranges -> sh:datatype
```

Implication:

```text
If law-nexus-kit needs generated shapes for law-nexus classes and properties, those terms need to live in the law-nexus-kit ontology and have explicit domain/range/restriction declarations. Merely relying on an upstream ACP-kit ontology is not enough unless the relevant triples are loaded in the configured kit's TTL graph.
```

### 6. Runtime type operations use shapes as the source of runtime type information

Runtime class/type operations parse installed `*-shapes.ttl` files.

Observed behavior:

```text
get_kit_types(kit) reads the configured kit's shape file.
create/templates use the configured kit's shape file.
frontmatter extraction uses object-property and datatype metadata from the configured kit's shape file.
```

Implication:

```text
For law-nexus-kit records, runtime behavior will be strongest when law-nexus-kit itself is the configured domain kit and its generated shape file contains the profile classes/properties.
```

### 7. `git lex list` is broader than configured-kit create/validate behavior

Class discovery via `list` walks every installed shape file under:

```text
.lex/ontology/**/*-shapes.ttl
_ontology/**/*-shapes.ttl
```

Implication:

```text
`git lex list` can show classes from all installed/adaptive shape files, but that does not mean create, validation, or frontmatter conversion use all kits as an inheritance chain. List is a whole-repo discovery surface; configured-kit operations remain centered on repo.yml's kit.
```

### 8. Validation centers on the configured kit shape plus adaptive shapes

Validation behavior:

```text
reads repo.yml kit
loads .lex/ontology/<short>/<short>-shapes.ttl for that kit
also concatenates adaptive _ontology/*/*-shapes.ttl
runs per-file frontmatter_to_turtle validation
```

Implication:

```text
Validation does not automatically validate against base-kit plus ACP-kit plus law-nexus-kit as a dependency stack. For law-nexus-kit validation, the configured kit's generated shapes must contain the constraints that matter.
```

## Answer to the layering question

The desired hierarchy is correct architecturally:

```text
git-lex -> base-kit -> acp-kit -> law-nexus-kit
```

But current git-lex mechanics support it as:

```text
git-lex engine
+ implicit base kit
+ one configured domain/profile kit
+ optional adaptive _ontology shapes
```

Therefore the safe implementation interpretation is:

```text
git-lex -> base-kit -> law-nexus-kit-as-configured-domain-kit
```

where law-nexus-kit statically imports or includes the ACP governance concepts it needs, while preserving ACP-kit as the reusable governance design source.

Do not assume native runtime install dependency chain:

```text
base installed -> acp installed as dependency -> law-nexus installed as dependency
```

unless a future git-lex change proves explicit dependency support.

## Fallback strategy for law-nexus-kit v0

Recommended safe fallback:

```text
1. Keep ACP-kit as reusable governance core and proof-boundary reference.
2. Make law-nexus-kit a deterministic configured domain kit.
3. Include law-nexus profile vocabulary in law-nexus ontology.
4. Reference/import ACP concepts conceptually or through static Turtle declarations only if source inspection/runtime proof shows shape generation can see them.
5. Define generated-shape-relevant law-nexus properties with explicit rdfs:domain and rdfs:range.
6. Avoid adaptive ontology mutation, Raw/session payloads, source-truth migration, production adoption claims, and R035/R037/R038 validation claims.
```

Practical v0 stance:

```text
law-nexus-kit should be installable as the configured domain kit. It can represent links to ACP proof gates and evidence concepts diagnostically, but ACP-native artifacts remain authoritative.
```

## Implications for ACP-kit strengthening

M058 remains relevant:

```text
ACP-kit generated shapes are underconstrained because many datatype/enum/required-field semantics are not attached as generated-shape constraints.
```

S02 mechanics explain the path to strengthen ACP-kit or law-nexus-kit:

```text
Add rdfs:domain, rdfs:range, owl:oneOf, and owl:Restriction triples in the configured kit ontology so the generator can emit sh:datatype, sh:in, and sh:minCount.
```

This should be verified with true negative runtime fixtures before any hard proof-gate claim.

## S02 conclusion

Current evidence supports this conclusion:

```text
The hierarchy is architecturally valid, but native multi-kit runtime dependency layering is not proven and should not be assumed. For implementation, law-nexus-kit v0 should be designed as a deterministic configured domain kit that statically carries or imports the law-nexus profile semantics it needs, with ACP-kit retained as reusable governance core and authority-boundary reference.
```

No runtime proof is required to answer the core mechanics question, because the source path explicitly shows base-plus-one-domain-kit behavior. Runtime smoke may still be useful in a future scaffold milestone after law-nexus-kit v0 exists.
