---
kind: validation
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect replay without a seed or a target argument
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::replay-report
  - text: The Product prints the usage line on stderr and exits 2 before reading any file
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::replay-report
---

# Replay refuses missing arguments

## Trigger

The operator omits the seed or the target argument.

## Outcome

The usage line prints on stderr and the command exits 2; nothing is read or
processed.
