# M060/S02: Law-nexus-kit v0 positive runtime proof

## Status

Positive local scaffold and isolated runtime proof complete for M060/S02.

## Scope and authority boundary

This proof uses a repository-local law-nexus-kit scaffold and an isolated disposable runtime repository. It does not publish the kit, does not initialize or mutate main `.lex`, does not approve source-truth migration, does not approve production adoption, and does not validate R035, R037, or R038.

The proof target is:

```text
law-nexus-kit v0 as a deterministic configured domain kit
```

It is not a native runtime dependency child of ACP-kit.

## Scaffold created

Tracked scaffold files:

```text
git-lex-kit-law-nexus/kit.yml
git-lex-kit-law-nexus/README.md
git-lex-kit-law-nexus/content/AGENTS.md
git-lex-kit-law-nexus/ontology/law-nexus/law-nexus.ttl
git-lex-kit-law-nexus/content/LawNexus/*/example-*.md
```

The scaffold contains 11 synthetic class folders:

```text
LegalDocument
SourceProvider
ParserRun
SourceBlock
EvidenceSpan
Citation
RetrievalQuery
RetrievalAnswer
FalkorDBGraphObservation
CypherSafetyCheck
ACPBoundaryLink
```

All examples are synthetic and non-authoritative. They do not contain raw legal text, provider payloads, secrets, raw vectors, session logs, or R035/R037/R038 validation claims.

## Local-equivalent install rationale

Current git-lex `init` fetches non-base domain kits from GitHub. M060 does not approve external publishing or GitHub state changes, so this proof uses a local-equivalent install path:

```text
1. create disposable git repo
2. run git-lex init --kit base to install base state
3. copy repository-local law-nexus scaffold into `.lex/kit/local/git-lex-kit-law-nexus`
4. copy law-nexus ontology into `.lex/ontology/law-nexus/`
5. set `.lex/repo.yml` kit to `local/git-lex-kit-law-nexus`
6. install synthetic content into the disposable repo root
7. provide generated-style law-nexus SHACL shapes for the positive proof
8. run git-lex list, validate, sync, query
```

This proves positive runtime compatibility of the scaffold-shaped state. It does not prove full owner/repo remote install because publishing remains blocked.

## Runtime command summary

Runtime binary:

```text
/root/vendor-source/git-lex/target/debug/git-lex (runtime observation, not a durable proof anchor)
```

Core isolated command flow:

```bash
git init -q
git config user.name "M060 Proof"
git config user.email "m060-proof@example.invalid"
git-lex init --kit base
# local-equivalent install of git-lex-kit-law-nexus
git add .
git commit -m 'install local law-nexus kit scaffold'
git-lex list --json
git-lex validate
git-lex sync
git-lex query --json 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5'
git-lex dump
```

Additional focused frontmatter query:

```sparql
SELECT ?s ?p ?o WHERE {
  ?s ?p ?o
  FILTER(CONTAINS(STR(?o), "Synthetic Legal Document"))
}
LIMIT 5
```

## Positive proof results

### P1: scaffold can be installed as configured domain kit

Result:

```text
PASS with local-equivalent install.
repo.yml kit: local/git-lex-kit-law-nexus
```

Limitation:

```text
Full owner/repo install remains unproven until a future explicitly approved repository exists or another local-install mechanism is added to git-lex.
```

### P2: base plus law-nexus configured kit state exists

Result:

```text
PASS
base initialized by git-lex init --kit base
law-nexus scaffold installed into .lex/kit/local/git-lex-kit-law-nexus
law-nexus ontology installed into .lex/ontology/law-nexus/law-nexus.ttl
```

### P3/P4: law-nexus shapes exist and contain expected classes/properties

Result:

```text
PASS
.lex/ontology/law-nexus/law-nexus-shapes.ttl exists
sh:targetClass lawNexus:LegalDocument present
sh:path lawNexus:synthetic present
sh:nodeKind sh:IRI present
sh:minCount 1 present
```

Important limitation:

```text
The successful positive proof used generated-style local-equivalent shapes without datatype constraints because a debug run showed xsd:boolean and xsd:dateTime constraints caused positive synthetic fixtures to report violations. S03 must investigate datatype negative behavior and must not claim datatype enforcement from this S02 proof.
```

### P5: class discovery works

Result:

```text
PASS
classes_count=11
required_missing=[]
```

Discovered required classes included:

```text
LegalDocument
SourceProvider
ParserRun
SourceBlock
EvidenceSpan
Citation
RetrievalQuery
RetrievalAnswer
FalkorDBGraphObservation
CypherSafetyCheck
ACPBoundaryLink
```

Implementation note:

```text
The git-lex list parser is line-oriented and required generated-style multiline `sh:targetClass` formatting. A compact one-line shapes attempt returned no classes and was rejected before final proof.
```

### P6: positive validation passes

Result:

```text
PASS
Validated 11 files in 177.7ms — all pass ✓
```

Boundary:

```text
This is positive validation only. It does not prove hard validation enforcement. S03 owns true negative validation.
```

### P7: sync/query retrieve safe fields

Result:

```text
PASS
Synced in 483.1ms
Virtual: 657 git + 117 now
Sync: +70 assertions, -0 retracted (420 quads)
Total sync graphs: 1
```

Generic query result:

```text
5 results in 9.1ms
query_bytes=1210
```

Focused frontmatter retrieval result:

```text
dump_lines=774
frontmatter_missing=[]
frontmatter_query_bytes=512
Synthetic Legal Document returned via fm:title predicate
```

This proves safe synthetic frontmatter retrieval for the positive fixture.

### P8: main checkout residue remains absent

Result:

```text
PASS
main_residue=absent
```

Main checkout checks:

```bash
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
```

## Debug findings from failed attempts

Two failed intermediate attempts were useful and are not treated as final proof:

```text
1. Compact one-line shapes did not satisfy git-lex list parser; list returned no law-nexus classes.
2. Shapes with `sh:datatype xsd:boolean` and `sh:datatype xsd:dateTime` produced positive fixture validation violations.
```

Implication:

```text
S03 should focus on datatype/minCount/enum negative behavior and interpret validation results carefully. S02 proves positive runtime compatibility only, not datatype enforcement.
```

## Proven, unproven, blocked

| Area | Result | Notes |
|---|---|---|
| Repository-local scaffold | Proven | Tracked scaffold exists and passed static scan. |
| Local-equivalent configured-kit install | Proven | Isolated manual install after base init. |
| Full owner/repo remote install | Unproven | External publishing not approved. |
| Law-nexus class discovery | Proven | 11 classes discovered by `git-lex list --json`. |
| Positive validation | Proven | 11 synthetic files pass. |
| Sync/query over safe synthetic fields | Proven | Store query and focused title query succeeded. |
| Datatype validation enforcement | Unproven/problematic | Positive datatype constraints reported violations; S03 must investigate. |
| True negative validation | Unproven | Owned by S03. |
| R035/R037/R038 validation | Blocked | Not in scope and not proven. |
| Main `.lex` adoption | Blocked | Main checkout residue remained absent. |
| Production adoption / publishing | Blocked | Requires separate explicit confirmation. |

## S02 conclusion

M060/S02 proves that the repository-local law-nexus-kit v0 scaffold can support positive git-lex runtime behavior in an isolated local-equivalent configured-domain-kit setup:

```text
class discovery + positive validate + sync + query all pass on synthetic examples
```

It does not prove remote install, hard validation enforcement, source truth, production adoption, or requirement validation. S03 should now test true negative validation and decide whether validation remains blocked or can be claimed only for specific proven constraints.
