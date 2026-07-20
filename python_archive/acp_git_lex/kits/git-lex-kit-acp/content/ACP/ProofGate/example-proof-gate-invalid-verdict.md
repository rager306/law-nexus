---
acp.ProofGate.identifier: "example-proof-gate-invalid-verdict"
acp.ProofGate.proofLevel: "synthetic-example"
acp.ProofGate.verdict: "totally-bogus"
---

# Example ProofGate (invalid verdict, true-negative)

This example is synthetic ACP-kit shape evidence only. It is not an accepted ACP source record, not validation evidence, and not proof for R035/R037/R038.

It demonstrates a ProofGate carrying a `verdict` value outside the VerdictValue enum, intended to trip the generated `sh:in` constraint on ProofGate as a true-negative fixture.
