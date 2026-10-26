---
kind: primary
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect replay with a seed path and a target path
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::replay-report
  - text: The Product reads the seed document and the target document and records each path, byte size, content fingerprint, and source family
    kind: product
    actor: operator
    entities:
      - entity: document
        as: seed
        effect: reads
        facts: [Path, Byte size, Content fingerprint, Source family]
      - entity: document
        as: target
        effect: reads
        facts: [Path, Byte size, Content fingerprint, Source family]
    contexts:
      cli:
        place: terminal::replay-report
  - text: The Product diffs the marker sets, drafts attach and detach changes with text-facet drafts, applies them, and verifies the drift, missing, and phantom counters
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::replay-report
  - text: The replay report prints with status ok and the verify counters
    kind: condition
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::replay-report
---

# Replay reproduces the target edition

## Trigger

The operator wants to check that a seed edition carries over into the target
edition.

## Outcome

The replay report prints with status ok; when the seed equals the target, the
diff, the drafts, and the verify counters are all zero.

## Edge cases

- A read error on either file prints one error record on stderr and exits 1.
