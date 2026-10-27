---
kind: primary
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect subordinates with a kind of resolution or order and the path of a Garant ODT act
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
  - text: The Product reads the document and records its path, byte size, content fingerprint, and source family
    kind: product
    actor: operator
    entities:
      - entity: document
        effect: reads
        facts: [Path, Byte size, Content fingerprint, Source family]
    contexts:
      cli:
        place: terminal::document-report
  - text: The Product binds the document group, counts punkt units, mints fixture component identities, and resolves text versions on the effect day
    kind: product
    actor: operator
    entities:
      - entity: document
        effect: reads
        facts: [Source family]
    contexts:
      cli:
        place: terminal::document-report
  - text: The report prints with status ok, the group and counter results, and the non-claims list
    kind: condition
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
---

# Resolve the punkt structure of a subordinate act

## Trigger

The operator wants the punkt units, fixture identities, and text versions of
one subordinate act.

## Outcome

The report prints bounded JSON with the bound group (or an explicit Unknown or
Conflict quarantine), punkt unit and fixture identity counts, resolved and
conflicting text versions, the effect day, and the non-claims list.

## Edge cases

- An unbound group is a visible Unknown or Conflict quarantine counter, never silence.
