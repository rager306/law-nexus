---
appliesTo:
  - type: capability
    id: inspect-document
  - type: capability
    id: replay-edition
  - type: capability
    id: resolve-subordinates
---

# Every report ends with an explicit non-claims list

The inspect, replay, and subordinates reports each end with a `non_claims`
list stating what the run does not claim.

## Rationale

The product claims no legal correctness, no citation authority, no corpus
completeness, and no five-clock assignment; every unknown is a visible
counter or status (Unknown, unavailable, no_edition_day), never silence.
