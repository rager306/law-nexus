---
acp.EvidenceAnchor.identifier: "example-evidence-anchor-missing-source-artifact"
---

# Example EvidenceAnchor (missing sourceArtifact, true-negative)

This example is synthetic ACP-kit shape evidence only. It is not an accepted ACP source record, not validation evidence, and not proof for R035/R037/R038.

It demonstrates an EvidenceAnchor with an absent `sourceArtifact` field, intended to trip the generated `sh:minCount 1` constraint on EvidenceAnchor as a true-negative fixture.
