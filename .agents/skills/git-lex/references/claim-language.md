# Safe claim language for git-lex and ACP

Use this reference when converting broad claims into evidence-bounded statements.

## Examples

| Unsafe wording | Safe wording |
|---|---|
| “git-lex proves ACP architecture is valid.” | “git-lex base ontology provides semantic vocabulary that can inform ACP-native records; ACP validity still depends on tracked source evidence and proof gates.” |
| “RDF projection validates the requirement.” | “RDF projection is a derived recovery/interoperability view; it does not validate requirements by itself.” |
| “We can adopt git-lex now.” | “Current evidence supports semantic-kit mapping and possible ACP-native absorption; runtime adoption requires isolated executable proof and an accepted decision.” |
| “Built on RDF/OWL/SPARQL/JSON-LD means no lock-in is proven.” | “The inspected base kit contains RDF/Turtle and OWL/RDFS vocabulary and SPARQL-oriented UI/query assumptions; JSON-LD and no-lock-in require exporter/context/roundtrip proof.” |
| “Frontmatter extraction works.” | “`fm.ttl` defines frontmatter predicates and documents intended auto-extraction; actual extraction requires runtime proof.” |
| “Quoted triples solve ACP provenance.” | “`lex.ttl` defines quoted-triple provenance vocabulary; parser/store/query support must be proven before ACP relies on it.” |
| “The git-lex UI proves backend support.” | “The web UI reveals expected API contracts; it does not prove the backend endpoints exist or behave correctly.” |

## Preferred verbs

Use:

- defines
- declares
- models
- suggests
- can inform
- can be projected
- is compatible in vocabulary shape with
- requires runtime proof
- remains derived
- remains blocked pending proof

Avoid unless proven:

- validates
- proves
- adopts
- guarantees
- authoritative
- source truth
- production-ready
- runtime-supported
- legal proof
