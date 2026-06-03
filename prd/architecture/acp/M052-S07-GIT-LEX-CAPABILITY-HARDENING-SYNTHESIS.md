# M052 S07 Git Lex Capability Hardening Synthesis

## Status

In progress for `M052-idogd6 / S07`.

S07 closes the M052 hardening loop. It compares the M051 final baseline with S01-S06 evidence, marks each weak surface as `upgraded`, `still blocked`, or `rejected`, and recommends the next iteration without promoting git-lex beyond the evidence.

## Guardrails

- ACP source/proof authority remains ACP-native.
- git-lex runtime remains `adapter-later` unless a later isolated adapter milestone proves otherwise.
- Main repository `.lex` adoption is not approved.
- git-lex outputs are derived diagnostics/recovery/projection evidence, not requirement-validation proof by themselves.
- R035, R037, and R038 remain outside git-lex proof authority.

## T01: Updated capability coverage table

### Evidence baseline and inputs

Baseline:

- `prd/architecture/acp/M051-S12-GIT-LEX-FINAL-RECONCILIATION.md`

M052 inputs:

- `prd/architecture/acp/M052-S01-SHACL-NEGATIVE-VALIDATION.md`
- `prd/architecture/acp/M052-S02-JSON-LD-RUNTIME-CAPABILITY.md`
- `prd/architecture/acp/M052-S03-SPARQL-STAR-RUNTIME-PROOF.md`
- `prd/architecture/acp/M052-S04-SERVE-VIZ-LISTEN-RUNTIME-PROOF.md`
- `prd/architecture/acp/M052-S05-REMAINING-CLI-COMMAND-MATRIX.md`
- `prd/architecture/acp/M052-S06-PRODUCTION-READINESS-PROVENANCE.md`

Marker extraction anchor:

```text
.gsd/exec/5b9f77b3-df8e-4a8a-b009-505b6fd1815f.stdout
```

### Coverage table

| Surface | M051 baseline | M052 evidence | Final M052 status | Next action |
|---|---|---|---|---|
| SHACL negative validation | Unproven; malformed/weak fixture did not establish failure behavior. | S01 source trace plus isolated positive/negative matrix for `squad`, `soul`, and `autoknow`; negative fixtures exited `1` with concrete `sh:minCount`, `sh:in`, and `sh:datatype` violations. Source still has fail-open/skipped setup paths. | `upgraded` for shape-derived valid-frontmatter violations; `still blocked` as standalone ACP proof gate. | Future adapter must wrap `validate` and hard-fail missing shapes, skipped files, parse/load/processor diagnostics, and unexpected validated-file counts. |
| JSON-LD runtime import/export | Unproven; M051 S08 JSON-LD sample was static ACP-native prototype evidence only. | S02 found no observed CLI/server/import/export route for JSON-LD RDF support. `.jsonld` is treated as file language metadata; Cargo transitive `oxjsonld` presence is not a runtime surface. | `rejected` for current git-lex JSON-LD RDF import/export claim; ACP JSON-LD remains ACP-native static interchange/prototype evidence. | Do not claim git-lex JSON-LD runtime support. Reopen only if a concrete JSON-LD route is implemented and runtime-proven. |
| SPARQL-star user-facing queries | Unproven; history graph internals hinted quoted triples but no user-facing runtime proof. | S03 proved explicit `<<( ?s ?p ?o )>>` SELECT/ASK over history graph `rdf:reifies` annotations in isolated synced repo. `query --json` returns non-standard `{ "type": "triple" }` bindings. | `upgraded` for narrow history-graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK patterns; `still blocked` for full RDF-star/SPARQL-star parity. | Use only the narrow safe wording. Do not rely on broad RDF-star semantics or production compatibility. |
| `git-lex-serve viz` / browser UI | Unproven browser-facing runtime surface; M051 had no real browser assertions. | S04 source trace, local `viz` server, browser assertions, and API checks passed for `/`, `/api/query`, `/api/run-and-push`, and `/api/scene`. Browser diagnostics found `/api/store-info` 404. | `upgraded` to local runtime/browser smoke with a known diagnostics gap; `still blocked` for production/browser exposure. | Keep localhost-only; require endpoint coverage, browser diagnostics, process cleanup, and security policy before adapter/server use. |
| `listen` SSE/notify | Unproven. | S04 proved `/notify` and `/events` in copied short-kit workspace; standard `git-lex init --kit squad` writes fully-qualified kit string and `listen` rejects it. | `upgraded` for implementation under short-kit config; `still blocked` for standard initialized repos. | Fix kit-string detection or define adapter repo.yml policy before relying on `listen`. |
| Remaining CLI commands | Incomplete coverage; `init/sync/query/list/validate` were the known core smoke surfaces. | S05 mapped `create`, `save`, `join`, `parse`, `nuke`, `kit-update`, `display`, `raw backfill`, hidden `extract`, `validate`, and `hook`. Disposable runtime proofs identified side effects and hazards. | `upgraded` for command behavior knowledge; `still blocked` for unattended ACP automation of workflow/destructive commands. | Minimal future adapter allowlist: `init`, `sync`, `query`, `list --json`, `validate` wrapper. Deny `nuke`, `kit-update`, `join`, `raw backfill`, `save`, and `create` by default. |
| `create/save` authoring workflow | Not assessed as adapter hazard. | S05 showed `create` can produce SHACL-invalid content; `save` can fail after staging derived `.lex/extract` sidecars. | `still blocked` for unattended ACP automation. | Only use in explicit authoring workflow with fill/validate/cleanup semantics and git-status recovery. |
| `nuke` | Not assessed. | S05 proved destructive `.lex`/`.git/lex` removal, local commit, and source attempts `git push`. | `rejected` for automated ACP use. | Never run automatically; require disposable/no-remote repo or explicit human confirmation and remote policy. |
| Raw payload mirroring | Not assessed. | S05 showed `raw backfill` copies machine-state harness payloads to `Raw/<Harness>/` when configured. | `still blocked` for durable ACP proof anchors. | Keep raw payloads out of durable anchors unless sanitized and explicitly approved. |
| Production readiness and binary provenance | M051 found debug runtime smoke and prebuilt binary inventory but no production adoption proof. | S06 traced build/release workflows, plugin binary sync, source/lock/toolchain identity, local debug build hashes, missing tags/releases, and missing attestations/SBOM/signatures. | `still blocked`; local debug build identity is `pass-smoke` only. | Require release artifact provenance, full source/build manifest, binary attestation, reproducibility boundary, version identity, security/rollback/observability gates. |
| ACP authority / R035 R037 R038 | M051 final: not validated by git-lex. | S01-S06 preserve boundary; S06 production gate explicitly keeps ACP-native authority unchanged. | `still blocked` for git-lex validation of these requirements. | Validate via ACP-native registry/runtime/legal evidence, not git-lex projection/runtime alone. |
| Main repo `.lex` adoption | Not approved; all runtime proofs isolated. | S01-S06 checks kept `/root/law-nexus/.lex` absent. | `still blocked` / not approved. | Continue isolated `/tmp` or future explicit worktree-only adapter proof; no main `.lex` without adoption decision. |

### Knowledge-delta ledger

| ID | Prior assumption/open question | Evidence anchor | Proof class | Updated conclusion | Remaining boundary | Downstream implication |
|---|---|---|---|---|---|---|
| KD15 | Could git-lex negative SHACL validation actually fail on invalid records? | `M052-S01-SHACL-NEGATIVE-VALIDATION.md`; `.gsd/exec/8be9e02b-3e9b-47f9-9807-44cc1f84cf2e.stdout` | Isolated runtime matrix plus source trace | Yes, for shape-derived valid-frontmatter negative fixtures. | Fail-open/skipped setup paths require wrapper gates. | Future adapter can include `validate`, but only behind wrapper checks. |
| KD16 | Does git-lex support JSON-LD RDF import/export at runtime? | `M052-S02-JSON-LD-RUNTIME-CAPABILITY.md`; `.gsd/exec/f69474d4-239d-466e-8206-14088173c214.stdout` | Source/runtime absence proof | No observed runtime surface; `.jsonld` is metadata-only. | Static ACP JSON-LD remains ACP-native prototype/interchange evidence. | Remove/avoid git-lex JSON-LD runtime claims. |
| KD17 | Are user-facing SPARQL-star queries supported? | `M052-S03-SPARQL-STAR-RUNTIME-PROOF.md`; `.gsd/exec/e7418ecc-ce38-4ec7-8acc-253bd5f6e7c8.stdout` | Isolated runtime query proof | Yes, narrowly for history graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK. | Broad RDF-star parity and production compatibility unproven. | Safe wording must stay narrow; query contracts should avoid broad RDF-star assumptions. |
| KD18 | Do serve/viz/listen work as real local browser/server surfaces? | `M052-S04-SERVE-VIZ-LISTEN-RUNTIME-PROOF.md`; browser timeline/debug bundle; `.gsd/exec/93bc741b-6ccd-4b49-9dd0-273a298c8bb3.stdout` | Source trace plus local server/browser/SSE proof | `viz` works as local smoke; `listen` works under short-kit config. | `/api/store-info` 404; standard init kit-string mismatch; no production hardening. | Browser/server claims require real browser evidence, cleanup, and explicit security gates. |
| KD19 | What remaining CLI commands are safe for ACP automation? | `M052-S05-REMAINING-CLI-COMMAND-MATRIX.md`; `.gsd/exec/a0dc6473-7094-463e-a698-cb94d57d9604.stdout`; `.gsd/exec/f4a34fdf-8fd8-400a-8f3e-85ee0b612cb3.stdout`; `.gsd/exec/2df18944-60b6-4731-ba18-7efaf9e3bb5d.stdout` | Disposable runtime matrix | Command behavior is much better known; only a small subset is plausible for adapter automation. | Workflow/destructive commands remain unsafe by default. | Future adapter should use allowlist + denylist, not general CLI exposure. |
| KD20 | Does local build/release evidence support production adoption? | `M052-S06-PRODUCTION-READINESS-PROVENANCE.md`; `.gsd/exec/541a46b9-a676-4c2b-981f-6b1f76862dd4.stdout` | Source/workflow trace and local debug build identity | No; production remains blocked. | Missing release provenance, attestation, reproducibility, version identity, security/rollback gates. | Next implementation, if any, must be an isolated minimal adapter spike with manifest/provenance gates. |

### T01 conclusion

M052 meaningfully improves capability coverage, but not production adoption. The correct final disposition is:

```text
upgraded: SHACL negative validation narrow, SPARQL-star narrow, viz local smoke, listen short-kit smoke, remaining CLI behavior knowledge
still blocked: production readiness, release/binary adoption, broad SPARQL-star, standalone validation proof, standard listen, browser/server production exposure, raw/save/create workflows, ACP requirement validation
rejected: current JSON-LD runtime import/export claim, automated ACP use of nuke
```

## T02: Durable git-lex guidance updates

T02 updated only durable references whose standing guidance changed after M052 evidence.

Updated files:

- `.agents/skills/git-lex/references/runtime-adoption-gates.md`
- `.agents/skills/git-lex/references/ontology-map.md`
- `.agents/skills/git-lex/references/source-inventory.md`

### Reference changes

| Reference | Update | Boundary preserved |
|---|---|---|
| `runtime-adoption-gates.md` | Added M052 S02 JSON-LD runtime update and M052 S06 production provenance update. | JSON-LD runtime support is not claimed; production adoption remains blocked. |
| `ontology-map.md` | Added M052 S02 JSON-LD runtime boundary with safe/unsafe wording. | Static ACP JSON-LD remains separate from git-lex runtime capability. |
| `source-inventory.md` | Added compact M052 capability-hardening status with S01-S06 outcomes and final production boundary. | Main `.lex` adoption remains not approved; R035/R037/R038 are not validated from git-lex evidence. |

### T02 conclusion

The durable guidance now matches M052 evidence:

```text
JSON-LD runtime claim: rejected / unsupported-not-observed
production adoption: blocked
minimal adapter candidates: init, sync, query, list --json, validate-wrapper
unsafe unattended commands: nuke, kit-update, join, raw backfill, save, create
ACP authority: unchanged, ACP-native
```

## T03: Next git-lex iteration recommendation

### Recommendation

Recommended next iteration, if the user wants implementation work:

```text
M053: Isolated minimal ACP git-lex adapter spike
```

The goal should be narrow: prove whether git-lex can act as a non-authoritative diagnostic adapter around ACP records without mutating the main repository and without using release/prebuilt binaries as trusted production inputs.

This is **not** a production adoption milestone. It is an implementation spike that must either produce a bounded adapter contract or reject adapter implementation as too costly/risky.

### Proposed M053 scope

Allowed scope:

1. Build/acquire git-lex from pinned source commit with manifest:
   - source repository;
   - full commit;
   - Cargo.lock hash;
   - build command;
   - toolchain identity;
   - binary hashes;
   - explicit attestation/provenance absence note.
2. Use only isolated fixture/worktree state.
3. Create `.lex` only outside the main checkout or in an explicitly isolated worktree.
4. Allowlist only:
   - `init`;
   - `sync`;
   - `query`;
   - `list --json`;
   - wrapped `validate`.
5. Add wrapper gates:
   - expected shapes present;
   - expected files counted;
   - setup/parser/processor diagnostics hard-fail;
   - before/after git status captured;
   - `.lex`/`.git/lex` lifecycle tracked;
   - generated sidecars tracked and cleaned.
6. Emit structured adapter observations, not authoritative ACP state.
7. End with a decision: `continue adapter`, `absorb patterns only`, or `reject adapter`.

Out of scope for M053:

- main repository `.lex` adoption;
- production binary/release adoption;
- `nuke`, `kit-update`, `join`, `raw backfill`, `save`, `create` in unattended automation;
- browser/server production exposure;
- validating R035/R037/R038 from git-lex output;
- Russian legal parser/FalkorDB/retrieval production claims.

### Alternative paths

| Option | When to choose | Pros | Cons |
|---|---|---|---|
| A. Stop after M052 | If git-lex was only research/provenance due diligence. | Avoids implementation cost; current evidence is enough to prevent overclaiming. | No practical adapter contract is produced. |
| B. M053 isolated minimal adapter spike | If the project wants a real integration proof while staying safe. | Turns evidence into concrete adapter skeleton/gates; keeps ACP authority intact. | Requires implementation and cleanup discipline; still not production adoption. |
| C. M053 production provenance hardening only | If binary/release trust is the blocker before any code integration. | Focuses on supply-chain/release manifest, reproducibility, signatures. | May require upstream changes; does not answer ACP adapter usefulness. |
| D. ACP-native only, no git-lex runtime | If avoiding runtime/dependency risk is more important than reuse. | Simplest authority model; no `.lex` lifecycle risk. | Leaves git-lex as prior art only and loses runtime diagnostic possibilities. |

### Recommended choice

Choose **B: M053 isolated minimal adapter spike** only if the user wants to continue from research into implementation.

Rationale:

- M052 upgraded enough runtime surfaces to justify a controlled adapter experiment.
- M052 also found enough hazards to forbid direct adoption.
- An isolated adapter spike is the smallest reversible next step that can retire the remaining integration unknowns without compromising ACP authority.

If the user does not need implementation now, stop after M052 and keep the evidence as the final hardening checkpoint.

### Acceptance criteria for M053

A future M053 should pass only if it proves all of the following:

1. Main `/root/law-nexus/.lex` remains absent.
2. Source/build manifest is generated and verified.
3. Adapter command allowlist is enforced.
4. Denylisted commands are unreachable through adapter paths.
5. `validate` wrapper catches at least one negative fixture and one fail-open/skipped setup class.
6. Adapter emits structured logs with command, cwd, source commit, exit code, stderr, before/after git status, generated artifacts, and cleanup result.
7. ACP records remain authoritative; git-lex output is stored or reported only as derived diagnostics.
8. Rollback/cleanup succeeds after success and after at least one forced failure.

### T03 conclusion

```text
Next iteration recommendation: M053 isolated minimal ACP git-lex adapter spike, only if implementation is desired.
Default if no implementation is desired: close M052 and stop; do not reopen M051/M052.
production adoption: blocked
runtime adoption: adapter-later
release/bundled binary adoption: blocked
main repository `.lex` adoption: not approved
```

## T04: Final M052 validation checks

### Verification anchors

Initial T04 verification intentionally failed because the report did not include an explicit `runtime adoption: adapter-later` marker:

```text
.gsd/exec/d7450767-4c65-4c35-b53c-94e17892bd29.stderr
```

After adding the missing marker, final verification passed:

```text
.gsd/exec/4d6b5a2b-027b-4a21-95a6-47b51b9c6db9.stdout
```

GitNexus change detection:

```text
gitnexus_detect_changes({repo: "law-nexus", scope: "all"})
summary: changed_count=0, affected_count=0, changed_files=3, risk_level=low
changed_symbols=[]
affected_processes=[]
```

GSD database checkpoint:

```text
gsd_checkpoint_db: WAL checkpoint complete
```

### Final checks performed

| Check | Result |
|---|---|
| Main `/root/law-nexus/.lex` absent | pass |
| Accidental main `Squad/` fixture absent | pass |
| `git diff --check` | pass |
| S01-S07 report artifacts present | pass |
| Core runtime/provenance proof anchors present | pass |
| S04 browser timeline/debug bundle present | pass |
| S07 final status markers present | pass |
| Background processes | none |
| GitNexus changed symbols / affected processes | none / none |
| GSD DB checkpoint | pass |

### T04 conclusion

M052 final validation is ready for slice and milestone closure. The milestone closes as a capability-hardening and next-iteration decision checkpoint, not as production adoption.
