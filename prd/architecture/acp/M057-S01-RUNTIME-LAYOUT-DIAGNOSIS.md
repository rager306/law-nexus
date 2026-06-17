# M057/S01: ACP-kit runtime layout and class discovery diagnosis

## Status

T01 complete. Full-spec ACP-kit init succeeds in a disposable workspace and records a bounded installed layout.

## Scope and authority boundary

This artifact records isolated runtime observations for ACP-kit diagnostics. It is not ACP source truth, not production evidence, not main `.lex` adoption, and not validation evidence for R035, R037, or R038.

Canonical ACP-kit invocation for this project:

```text
git-lex init --kit rager306/git-lex-kit-acp <disposable-workspace>
```

Do not use short `--kit acp` as the law-nexus proof command.

Durable proof anchors are tracked repository-relative paths only:

- `git-lex-kit-acp/README.md`
- `git-lex-kit-acp/kit.yml`
- `git-lex-kit-acp/ontology/acp/acp.ttl`
- `git-lex-kit-acp/content/AGENTS.md`
- `prd/architecture/acp/M057-S01-RUNTIME-LAYOUT-DIAGNOSIS.md`

Environment-local workspaces, binary paths, and command scratch output are runtime observations only, not durable ACP proof anchors.

## T01 isolated init evidence

### Preconditions

```text
pre_no_main_state=yes
git_lex_bin=yes
accepted_kit_remote_head=949553b2ad4a24fe51a07d9c800aca8db95a43da
```

The accepted kit remote head points to the published `rager306/git-lex-kit-acp` README commit that documents the explicit full-spec invocation.

### Command

```text
git init <disposable-workspace>
git-lex init --kit rager306/git-lex-kit-acp <disposable-workspace>
```

### Result

```text
init_code=0
workspace_removed=yes
post_no_main_state=yes
```

### Init stdout summary

```text
Downloading base kit repolex-ai/git-lex-kit-base...
Base kit installed.
Downloading additional kit rager306/git-lex-kit-acp...
Additional kit installed.
Installed 16 scaffold file(s) from kit(s)
SHACL shapes generated: acp-shapes.ttl
Created class templates
Initialized .lex/ in disposable workspace
Installed pre-commit hook (extract + validate on commit)
Committed git-lex setup files.
Committed existing content.
Identity: <disposable first commit hash>
```

### Init stderr summary

```text
Commit existing files to the repository? [Y/n]
Extracted in runtime smoke
Validated 3 files in runtime smoke — all pass ✓
Extracted in runtime smoke
Validated 3 files in runtime smoke — all pass ✓
```

## Installed repository state

### `.lex/repo.yml` summary

```yaml
kit: rager306/git-lex-kit-acp
first_commit: <disposable first commit hash>
```

### Disposable git history

The runtime created three commits inside the disposable repository:

```text
git lex init
Initial content
git lex identity
```

This broad local commit behavior is acceptable only because it happened in a disposable workspace. It must not be used as evidence that `git lex save` or broad staging is safe for the main law-nexus checkout.

### Hook behavior

The disposable workspace installed a real pre-commit hook:

```text
.git/hooks/pre-commit
```

This is a runtime observation. Main checkout hook mutation remains blocked unless a later adoption decision approves it.

## Installed file layout summary

### Top-level installed content

```text
.claude/CLAUDE.md
.gitkeep
AGENTS.md
ACP/.gitkeep
ACP/Decision/example-decision.md
ACP/ProofGate/example-proof-gate.md
ACP/SourceRecord/example-source-record.md
.lex/README.md
.lex/repo.yml
```

### Installed ACP kit files under `.lex/kit`

```text
.lex/kit/rager306/git-lex-kit-acp/README.md
.lex/kit/rager306/git-lex-kit-acp/content/ACP/.gitkeep
.lex/kit/rager306/git-lex-kit-acp/content/ACP/Decision/example-decision.md
.lex/kit/rager306/git-lex-kit-acp/content/ACP/ProofGate/example-proof-gate.md
.lex/kit/rager306/git-lex-kit-acp/content/ACP/SourceRecord/example-source-record.md
.lex/kit/rager306/git-lex-kit-acp/content/AGENTS.md
.lex/kit/rager306/git-lex-kit-acp/kit.yml
.lex/kit/rager306/git-lex-kit-acp/ontology/acp/acp.ttl
.lex/kit/rager306/git-lex-kit-acp/www/.gitkeep
```

### Installed ontology and generated shapes

```text
.lex/ontology/acp/acp.ttl
.lex/ontology/acp/acp-shapes.ttl
.lex/ontology/fm/fm.ttl
.lex/ontology/git/git.ttl
.lex/ontology/lex/lex.ttl
```

### Extraction sidecars

```text
.lex/extract/ACP/Decision/example-decision.md.fm.spo
.lex/extract/ACP/ProofGate/example-proof-gate.md.fm.spo
.lex/extract/ACP/SourceRecord/example-source-record.md.fm.spo
```

## T01 interpretation

Supported:

- Full-spec ACP-kit installation works in a disposable workspace.
- ACP scaffold content is installed into top-level `ACP/` and guidance files.
- The ACP ontology is installed into `.lex/ontology/acp/acp.ttl`.
- A generated `.lex/ontology/acp/acp-shapes.ttl` file exists.
- Runtime extraction/validation hooks run inside the disposable workspace and report positive validation for the three bundled example files.
- The main checkout remains free of `.lex`, `Squad`, `Raw`, and `.artifacts` residue.

Not supported yet:

- `git-lex list --json` class discovery behavior.
- `git-lex sync` graph visibility for ACP records.
- `git-lex query` over ACP records.
- Negative validation behavior.
- Main `.lex` adoption, source-truth migration, production adoption, or R035/R037/R038 validation.

## T02 class discovery diagnosis

### Command

```text
git-lex list --json
git-lex list
```

### Result

```text
list_json_code=0
list_text_code=0
list_json=[]
list_text=No classes found. Install a kit with `git lex init --kit <name>` or add shapes under _ontology/.
workspace_removed=yes
post_no_main_state=yes
```

### Generated shape evidence

Installed generated shape file:

```text
.lex/ontology/acp/acp-shapes.ttl
```

The generated shape file contains only prefixes and comments; no `sh:NodeShape` or `sh:targetClass` entries were generated.

```text
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix acp: <https://repolex.ai/ontology/kit/acp/> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .

# Auto-generated SHACL shapes from rager306/git-lex-kit-acp ontology.
# Do not hand-edit — regenerate with: git lex kit-update
```

### Ontology evidence

Installed ACP ontology contains `owl:Class` declarations such as:

```text
acp:SourceRecord a owl:Class
acp:Requirement a owl:Class
acp:Decision a owl:Class
acp:EvidenceAnchor a owl:Class
acp:ProofGate a owl:Class
acp:HealthFinding a owl:Class
acp:Projection a owl:Class
acp:LifecycleState a owl:Class
acp:AuthorityClass a owl:Class
acp:ValidationClaim a owl:Class
acp:ProfileConstraint a owl:Class
acp:RuntimeAdapter a owl:Class
```

### Likely cause

The git-lex SHACL generator queries loaded kit ontology for `?class a owl:Class`, then filters class IRIs by the kit namespace. For the `acp` short name it looks for a prefix namespace matching the inspected kit convention:

```text
https://repolex.ai/ontology/kit/acp/
```

The current ACP ontology prefix is:

```text
@prefix acp: <https://legalgraph.example/ontology/acp/> .
```

Because generated class IRIs start with `https://legalgraph.example/ontology/acp/` rather than `https://repolex.ai/ontology/kit/acp/`, the generator filters them out and writes an empty shape file. `git-lex list` then reads installed shapes and reports no classes.

### S02 recommendation

S02 should minimally correct the ACP kit ontology namespace to the git-lex kit namespace convention:

```text
@prefix acp: <https://repolex.ai/ontology/kit/acp/> .
```

Then republish `rager306/git-lex-kit-acp`, mirror the change into `git-lex-kit-acp/` in law-nexus, rerun the static verifier, and rerun isolated full-spec init plus `git-lex list --json`.

This is a kit layout/namespace correction, not an ACP source-truth migration and not profile validation.
