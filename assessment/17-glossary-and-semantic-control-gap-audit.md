# Glossary and semantic-control gap audit

**Assessment date:** 2026-08-12  
**Audited base:** `fcbadbe06fc8eaee46888e4118ed82f13191c0b6` plus the uncommitted glossary-control remediation reviewed here  
**Lifecycle:** `[bounded]` repository-document/process assessment  
**Role:** non-authoritative audit; not successor acceptance or product proof  

## 1. Recovered primary criticism

The primary 2026-08-11 criticism was recovered from the local GSD session log:

```text
/root/.gsd/sessions/--root-law-nexus--/
2026-08-11T06-29-40-606Z_019fef83-327e-7121-ab8a-6dfe6e6a0cf0.jsonl
zero-based line: 857
message id: 74d2bfcf
role: user
timestamp: 2026-08-11T10:33:40.517Z
reviewed revision: 60fd8245ace999f3f29911844375dd7cc36a2a38
```

The critique body starts with `# Итоговая оценка`. This is the primary content
source. `assessment/13-current-head-gap-audit.md`, later assessments and
`.gsd/continue.md` are recovery/status summaries, not substitutes.

The literal label `C32` does not occur in the primary criticism. It is a later
reconstruction. The original §14.1 asks for a self-contained
`prd/temporal-legal-model.md` contract with fourteen areas: glossary, entity
model, event taxonomy, temporal axes, applicability DSL, status, provenance,
conflict, correction, invariants, deterministic API, golden cases, error
taxonomy and proof gates.

The local session file is not a portable tracked proof anchor. This assessment
preserves only the location and bounded disposition; it cannot make the session
log architecture authority.

## 2. Glossary disposition

At the audited base, `prd/temporal-legal-model.md` already contained a 29-row
crosswalk, but the machine catalog controlled only 10 high-risk rows. A green
Governor result therefore proved a subset without enforcing that the catalog
covered the whole table. No tracked contract explained how terms reach coding
agents or how glossary changes propagate.

This remediation establishes:

- a complete machine inventory of every current glossary row;
- exact TSG-ID inventory continuity;
- an explicit non-authoritative governance contract;
- tracked coding-agent read/injection rules;
- companion freshness for model/catalog/register changes;
- advisory detection of unqualified deprecated aliases;
- explicit stop-sign rows for load-bearing critique vocabulary that remains
  undefined.

The glossary remains `[proposed]` design projection. Inventory completeness is
not semantic completeness and does not close TSG-001.

## 3. Contradictions corrected

| Surface | Earlier inconsistency | Bounded correction |
|---------|-----------------------|--------------------|
| ADR-0018 | Decision/Status still trained `NormativeStatus` as primary despite EA-04 | canonical public name normalized to `NormativeState`; alias remains only in explicit deprecated clarification |
| ADR-0020 | practice boundary referred to `NormativeStatus` without qualifier | normalized to `NormativeState` |
| M111 baseline | `legal_act_effect` included “scoped applicability” | aligned to legal-order event and explicit not-case-applicability boundary |
| living architecture | future `EvidenceSpan`/`SourceBlock` could look like existing contracts | marked future-schema and `deferred-undefined` |
| local Russian legal skill | defined future `SourceBlock`/`EvidenceSpan` semantics and edition fields beyond glossary ceiling | local operational copy aligned to `SourceBlockRecord`, deferred terms and five clocks; skill remains gitignored/local |

## 4. Missed or still partial primary-critique items

| Original criticism | Current disposition |
|--------------------|---------------------|
| first-class NormRule graph with Condition/LegalEffect/Exception/Defeater roles | open; terms now explicit `deferred-undefined` stop-signs, TSG-005 remains `[deferred]` |
| typed TextChangeEvent versus NormativeEffectEvent | open; explicit deferred terms, TSG-002 |
| ComponentMembershipVersion and scope-aware CTV reconstruction | open; deferred term plus TSG-003/013 |
| LegalList/ListEntry/ClassifierCode versioning | open; deferred terms plus TSG-013 |
| ApplicabilitySelector AST/DSL | open; ADR-0023 owns protocol boundary only; runtime and AST remain deferred |
| ProcurementCase and ProcurementRegimeResolution | open; deferred profile/application vocabulary, TSG-010 |
| typed practice coverage outcomes | open; deferred vocabulary, TSG-008 |
| bitemporal correction ledger | open; five-clock safety is bounded, executable ledger remains TSG-011 |
| split transition resolution and risk | open; ADR-0021 still combines both design concerns, TSG-009 |
| competence/jurisdiction graph | open; ADR-0019 remains proposed, TSG-007 |
| deterministic API/error taxonomy | partial/open, TSG-014 |
| 20–30 executable golden temporal cases | partial: paper cases only, not legal gold; TSG-015 |
| full self-contained temporal contract | partial: current document is a crosswalk with paper gates, not an executable normative contract |
| post-M165 implementation sequence | human-owned and still unselected |

The deferred rows intentionally do not adopt the critique's names as final
ontology. A future human-owned ADR may rename, split, reject or define them.

## 5. Governor controls added

### `temporal-vocabulary-contract`

Deterministic repository-structure check:

- catalog schema and `authoritative: false`;
- declared complete-glossary coverage mode;
- one catalog row per glossary row;
- required vocabulary/lifecycle fragments;
- exact TSG identifier set;
- governance-surface non-authority/runtime boundaries.

Malformed or unreadable inputs remain structured tool errors. Missing rows or
fragments remain advisory findings. Passing means structure only.

### `temporal-vocabulary-drift`

Heuristic advisory check over a fixed living/ADR path allowlist. It detects an
unqualified deprecated `NormativeStatus` alias. It does not infer semantic
equivalence, rewrite ADRs or fail preflight by default.

### Freshness companions

Dirty-tree changes to the glossary, catalog, gap register or governance contract
require a distinct companion review surface. This remains working-tree diagnostics only; clean-tree
comparison base and periodic/external freshness remain unresolved policy.

## 6. Additional Governor backlog

Safe next advisory checks, not implemented in this slice:

1. deferred-term-as-implemented-type scan over a narrow living-entrypoint and
   local-skill allowlist;
2. sixth-clock-like name detection with explicit qualifier support;
3. `edition_date` or static effective interval presented as source truth;
4. parser term isolation (`SourceBlockRecord` versus future `SourceBlock`);
5. L1–L7/O1–O7 alias-note continuity;
6. commit-range/clean-tree glossary freshness after a human comparison-base
   policy is chosen;
7. bounded human disposition ledger for Stage D heuristic findings.

These checks have higher false-positive or policy risk and must remain advisory
until reviewed against real findings.

## 7. Processes Governor must not automate

Governor must not:

- decide legal equivalence or final canonical ontology names;
- define the future `SourceBlock`, `EvidenceSpan`, NormRule or applicability AST;
- determine correct legal dates, normative state or applicability;
- accept disputed source spans or parser gold;
- choose corpus representativeness or quality thresholds;
- close TSG rows;
- promote ADR/product lifecycle;
- select the post-M165 implementation sequence;
- treat an LLM semantic review as authority or a blocking product verdict.

## 8. Remaining process gaps

- The complete temporal contract remains partial despite complete vocabulary
  inventory.
- Local skills are gitignored, so portable CI cannot prove their contents;
  tracked `AGENTS.md` and governance instructions are the clone-safe injection
  path.
- D150 remains bound to revision `120d44be610b20ee537f402140eb3828e8e9a0f4`;
  this assessment is not successor acceptance.
- Clean-tree/commit-range freshness base, periodic external review and Stage D
  consumer/disposition remain human-owned.
- Historical/quarantined derived reports still impose cold-reader cost even
  though they are not authoritative.
- Product/runtime semantic core remains implementation work: CTV, NormRule,
  applicability, procurement timeline, practice coverage and correction ledger.

## 9. Bounded conclusion

The glossary requirement was real and materially under-implemented as a
process: a partial crosswalk existed, but machine coverage, update governance
and coding injection were incomplete. The remediation closes those structural
control gaps only. It also recovers several primary-critique terms that later
summaries had compressed away, while marking them undefined rather than
inventing semantics.

No glossary row, Governor pass or assessment validates product behavior, legal
correctness or ontology readiness.
