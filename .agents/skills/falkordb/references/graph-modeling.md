# FalkorDB Graph Modeling Notes

## Model from questions, not nouns

Start with the queries the graph must answer. Extract:

- entities and identity keys
- relationships and direction
- cardinality and fan-out
- temporal/versioning needs
- provenance/evidence needs
- high-frequency lookup predicates
- write/update lifecycle

## Node vs relationship vs property

Use a node when the thing has identity, lifecycle, many relationships, or needs to be referenced independently.

Use a relationship when the thing is primarily a traversable connection between two nodes.

Use a relationship property when the property describes that specific edge and does not need independent identity.

Use an intermediate node when an edge needs many properties, provenance, versioning, evidence, or multiple participants.

## Labels

Use labels for stable categories and query routing. Avoid encoding high-cardinality values as labels unless there is a deliberate query reason.

## Indexes

Indexes are workload artifacts, not decorations. For each proposed index, state:

- query pattern it supports
- property/properties involved
- expected cardinality/selectivity
- verification query

Full-text/vector indexes are capability-sensitive: verify in the target FalkorDB runtime before relying on them.

## Anti-patterns

- Directly copying relational tables into node labels without traversal questions.
- Turning every enum into a node.
- Turning every value into a label.
- Modeling relationship facts as properties when they need provenance or lifecycle.
- Designing vector/full-text features before proving target runtime support.
