---
scope: The product CLI law-nexus-inspect and its storage ports and in-memory adapters.
method: Static inspection of the CLI source, its contract tests, and the storage adapters.
covered:
  - description: The law-nexus-inspect binary, its five subcommands (health, inspect, replay, subordinates, reference-package), reports, and failure records.
    paths: [crates/ln-product-cli/]
  - description: The reference-package build and check subcommands composing the ln-consultant-parser reference_layer (ADR-0031) over a corpus directory and a catalog.
    paths: [crates/ln-product-cli/]
  - description: Storage and embedding ports, the in-memory vector and graph store adapters, and cosine retrieval.
    paths: [crates/ln-storage/]
exclusions:
  - description: Hostile-contract runner binaries (hc01-hc20), executable evidence tooling rather than a user-facing product surface.
    paths: [crates/ln-hc01-runner/, crates/ln-hc02-runner/, crates/ln-hc03-runner/, crates/ln-hc04-runner/, crates/ln-hc05-runner/, crates/ln-hc06-runner/, crates/ln-hc07-runner/, crates/ln-hc08-runner/, crates/ln-hc09-runner/, crates/ln-hc10-runner/, crates/ln-hc11-runner/, crates/ln-hc12-runner/, crates/ln-hc13-runner/, crates/ln-hc14-runner/, crates/ln-hc15-runner/, crates/ln-hc16-runner/, crates/ln-hc17-runner/, crates/ln-hc18-runner/, crates/ln-hc19-runner/, crates/ln-hc20-runner/]
  - description: The Python repository-control harness and repository verification scripts, which shell out beside the product and are not product behavior.
    paths: [src/, scripts/]
unmapped:
  - description: Decode, ontology, temporal, and query crate behavior beyond what the CLI reports expose (parsing semantics, hierarchy and edition-day registries, temporal fold, CTV resolution).
    paths: [crates/ln-decode/, crates/ln-consultant-parser/, crates/ln-kb-ontology/, crates/ln-query/, crates/ln-temporal/]
limitations:
  - description: Registry-backed inspect and replay paths depend on registry data absent in this environment; their behavior was established from source and contract tests, not executed against registries.
    paths: [crates/ln-kb-ontology/src/registry/]
---

# Coverage
