---
kind: primary
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect health
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal
  - text: The Product prints one JSON status line naming the binary and the Rust runtime
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal
  - text: The command exits 0
    kind: condition
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal
---

# Health reports ok

## Trigger

The operator wants to confirm the product binary runs.

## Outcome

The status line prints with `status: ok`, naming `law-nexus-inspect` and the
Rust runtime, and the command exits 0.
