<workflow>
<required_reading>
- `references/source-inventory.md`
- `references/ontology-map.md`
- `references/acp-boundaries.md`
</required_reading>

<process>
1. Verify the vendor checkout exists at `/root/vendor-source/git-lex-kit-base`.
2. Read `kit.yml` before making scope claims. The base kit is system ontologies plus web UI, not domain content and not a runtime implementation.
3. Read the ontology files in this order:
   - `ontology/lex/lex.ttl` for upper ontology, generic relations, extraction vocabulary, and quoted-triple provenance vocabulary.
   - `ontology/git/git.ttl` for Git object/provenance vocabulary.
   - `ontology/fm/fm.ttl` for YAML frontmatter vocabulary.
4. Inspect `www/js/main.js` only for UI/API contracts: `/api/query`, `/api/sync`, `/api/store-info`, `/api/file`, WebSocket scene push, named graph assumptions, and history graph assumptions.
5. Classify each finding as one of:
   - semantic ontology evidence;
   - extraction/provenance vocabulary evidence;
   - UI/static asset evidence;
   - runtime/API contract expectation;
   - absent or unproven runtime behavior.
6. State ACP implications using bounded language: “can inform ACP ontology,” “can be projected,” “requires runtime proof,” “does not establish source truth.”
</process>

<verification>
- Every positive claim cites a file path.
- No finding implies executable `git lex` availability unless a runtime command was actually run in an isolated workspace.
- No finding treats `.lex` main-repo mutation as safe.
- JSON-LD is marked unproven unless a context/export/import path is inspected or created and tested.
</verification>
</workflow>
