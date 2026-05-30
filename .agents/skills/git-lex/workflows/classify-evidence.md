<workflow>
<required_reading>
- `references/acp-boundaries.md`
- `references/source-inventory.md`
- `references/claim-language.md`
</required_reading>

<process>
1. Identify the artifact path, source, and type.
2. Classify the artifact as one or more of:
   - authoritative source evidence;
   - accepted decision;
   - proof-gate result;
   - semantic-kit ontology evidence;
   - derived projection;
   - diagnostic/recovery surface;
   - runtime proof;
   - blocked or insufficient evidence.
3. State allowed uses: what this evidence may support in ACP reasoning.
4. State forbidden uses: what this evidence must not be used to claim.
5. If the artifact is projection or semantic-kit evidence, explicitly block promotion to source truth unless an accepted ACP rule plus proof gate supports it.
</process>

<verification>
- The classification names what can and cannot be proven.
- Requirement validation claims are separated from interoperability and projection claims.
- Runtime claims are separated from ontology/schema claims.
</verification>
</workflow>
