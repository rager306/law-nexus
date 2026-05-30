<workflow>
<required_reading>
- `references/runtime-adoption-gates.md`
- `references/acp-boundaries.md`
- `prd/architecture/acp/M048-S08-GIT-LEX-CAPABILITY-MATRIX.md`
- `prd/architecture/acp/M048-S10-GIT-LEX-ADOPTION-DECISION.md`
</required_reading>

<process>
1. Confirm whether the request is semantic-kit integration, adapter planning, or runtime adoption.
2. For runtime adoption, require an isolated workspace outside the main checkout and a written `.lex` state policy before running commands.
3. Define the acquisition proof:
   - repository/package/source of git-lex runtime;
   - pinned commit/version;
   - installation/build commands;
   - license and reproducibility notes.
4. Define representative operations:
   - help/version command;
   - init in temporary repo;
   - sync or equivalent extraction;
   - query over generated graph;
   - frontmatter extraction proof;
   - quoted-triple/SPARQL-star proof if ACP claim provenance depends on it;
   - JSON-LD export/import proof if JSON-LD is claimed;
   - validation failure and rollback/cleanup.
5. Require no main-repo `.lex` mutation before an explicit adoption decision.
6. Classify final disposition per capability: `use git-lex runtime`, `absorb approach`, `implement ACP-native`, `adapter later`, `reject`, or `blocked`.
</process>

<verification>
- The plan never instructs blind `git lex init` in the main repository.
- The plan keeps ACP-native records and validation as the baseline until runtime proof passes.
- The plan states which claims remain unproven after the spike.
</verification>
</workflow>
