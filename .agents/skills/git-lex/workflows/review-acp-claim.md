<workflow>
<required_reading>
- `references/acp-boundaries.md`
- `references/ontology-map.md`
- `references/claim-language.md`
- `templates/claim-review.md`
</required_reading>

<process>
1. Quote the exact claim being reviewed.
2. Split it into claim atoms:
   - semantic vocabulary or ontology claim;
   - projection/interoperability claim;
   - validation or authority claim;
   - runtime/CLI/store/extractor claim;
   - requirement-validation claim.
3. Map each atom to evidence classes:
   - authoritative source evidence;
   - accepted decision;
   - proof-gate result;
   - semantic-kit ontology evidence;
   - derived projection;
   - diagnostic/recovery surface;
   - runtime proof;
   - blocked or insufficient evidence.
4. Apply hard boundaries:
   - ontology files do not prove runtime behavior;
   - projections do not become source truth by being RDF/OWL/SPARQL/JSON-LD;
   - R035/R037/R038 are not validated from ACP/git-lex/projection evidence alone;
   - no main-repo `.lex` mutation without isolated proof and accepted adoption decision.
5. Return a verdict: `safe`, `bounded`, `overclaim`, or `blocked`.
6. Rewrite unsafe wording into bounded wording and name the next proof needed.
</process>

<verification>
- The output names the inspected evidence.
- The safe restatement does not imply runtime adoption unless runtime proof exists.
- The forbidden inference section explicitly blocks any source/projection authority inversion.
</verification>
</workflow>
