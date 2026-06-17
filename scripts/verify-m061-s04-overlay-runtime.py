#!/usr/bin/env python3
"""Run M061/S04 ACP core plus law-nexus profile overlay runtime proof.

This harness is intentionally main-repo safe:
- git-lex runtime commands run only in /tmp/s061-s04-* workspaces;
- every command is wrapped by pre/post checks that the main checkout has no
  .lex, Squad, Raw, or .artifacts residue;
- ACP-kit init uses the explicit canonical kit spec
  rager306/git-lex-kit-acp, never the short acp alias;
- law-nexus-kit is installed through the local-equivalent configured-kit path
  used by M060/S02, not through publishing or remote mutation.

The generated diagnostics are runtime-smoke/profile-proof evidence only. They
are not ACP source truth, not main .lex adoption, and not validation proof for
R035/R037/R038.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "prd/architecture/acp/runtime/m061-s04"
DIAGNOSTICS_PATH = ARTIFACT_DIR / "diagnostics.jsonl"
FIXTURES_DIR = ARTIFACT_DIR / "fixtures"
SHAPES_DIR = ARTIFACT_DIR / "shapes"
NEGATIVE_CASES_DIR = ARTIFACT_DIR / "negative-cases"

ACP_KIT_SPEC = "rager306/git-lex-kit-acp"
LAW_NEXUS_LOCAL_KIT = "local/git-lex-kit-law-nexus"
GIT_LEX_BIN_DIR = Path("/root/vendor-source/git-lex/target/debug")
MAIN_RESIDUE_NAMES = (".lex", "Squad", "Raw", ".artifacts")
OUTPUT_LIMIT = 2048

RunCommand = Callable[[Sequence[str], Path, dict[str, str]], "CommandResult"]


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    cwd: str
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class NegativeCase:
    case_id: str
    class_path: str
    filename: str
    query: str
    replacements: tuple[tuple[str, str], ...]


POSITIVE_FIXTURES: dict[str, str] = {
    "ACP/ProofGate/example-profile-proof-gate.md": """---
title: Example Profile Proof Gate
acp.ProofGate.identifier: example-profile-proof-gate
acp.ProofGate.nonAuthoritative: true
acp.ProofGate.sourceArtifact: prd/architecture/acp/M061-S03-ACP-PROFILE-OVERLAY-SHACL-MECHANICS.md
acp.ProofGate.proofLevel: runtime-smoke
acp.ProofGate.verdict: not-applicable
---

# Example Profile Proof Gate

Synthetic ACP proof-gate fixture for M061/S04 profile overlay runtime validation. It is non-authoritative and does not approve main `.lex`, source-truth migration, production adoption, or R035/R037/R038 validation.
""",
    "ACP/ValidationClaim/example-profile-validation-claim.md": """---
title: Example Profile Validation Claim
acp.ValidationClaim.identifier: example-profile-validation-claim
acp.ValidationClaim.nonAuthoritative: true
acp.ValidationClaim.verdict: pass
acp.ValidationClaim.hasLifecycleState: example-validated-runtime-smoke
acp.ValidationClaim.hasAuthorityClass: profile-proof
acp.ValidationClaim.sourceArtifact: prd/architecture/acp/runtime/m061-s04/diagnostics.jsonl
---

# Example Profile Validation Claim

Synthetic validation-claim fixture proving only that the composed ACP plus law-nexus profile shape can be exercised in an isolated runtime workspace.
""",
    "ACP/EvidenceAnchor/example-profile-evidence-anchor.md": """---
title: Example Profile Evidence Anchor
acp.EvidenceAnchor.identifier: example-profile-evidence-anchor
acp.EvidenceAnchor.sourceArtifact: prd/architecture/acp/runtime/m061-s04/diagnostics.jsonl
acp.EvidenceAnchor.nonAuthoritative: true
---

# Example Profile Evidence Anchor

Synthetic evidence-anchor fixture. The sourceArtifact is a tracked repository-relative diagnostics path, not a local `.lex` path, raw provider payload, vector, secret, or legal text.
""",
    "LawNexus/ParserRun/example-parser-run.md": """---
title: Example Parser Run
law-nexus.ParserRun.synthetic: true
law-nexus.ParserRun.nonAuthoritative: true
law-nexus.ParserRun.proofStatus: example-only
law-nexus.ParserRun.sourcePath: prd/architecture/acp/M061-S03-ACP-PROFILE-OVERLAY-SHACL-MECHANICS.md
law-nexus.ParserRun.provider: synthetic-profile-provider
law-nexus.ParserRun.observedAt: 2026-06-15T00:00:00Z
law-nexus.ParserRun.parserName: synthetic-profile-parser
law-nexus.ParserRun.supportsAcpGate: example-profile-proof-gate
---

# Example Parser Run

Synthetic parser-run profile fixture. It does not prove parser quality, real-document behavior, FalkorDB ingestion, retrieval quality, or legal citation safety.
""",
    "LawNexus/ACPBoundaryLink/example-acp-boundary-link.md": """---
title: Example ACP Boundary Link
law-nexus.ACPBoundaryLink.synthetic: true
law-nexus.ACPBoundaryLink.nonAuthoritative: true
law-nexus.ACPBoundaryLink.proofStatus: example-only
law-nexus.ACPBoundaryLink.sourcePath: prd/architecture/acp/M061-S03-ACP-PROFILE-OVERLAY-SHACL-MECHANICS.md
law-nexus.ACPBoundaryLink.supportsAcpGate: example-profile-proof-gate
law-nexus.ACPBoundaryLink.diagnostic: profile-overlay-boundary-only
---

# Example ACP Boundary Link

Synthetic boundary-link fixture. It records diagnostic profile-to-ACP navigation metadata only; object-link enforcement remains blocked by IRI normalization behavior.
""",
    "LawNexus/LegalDocument/example-legal-document.md": """---
title: Example Legal Document
law-nexus.LegalDocument.synthetic: true
law-nexus.LegalDocument.nonAuthoritative: true
law-nexus.LegalDocument.proofStatus: example-only
law-nexus.LegalDocument.documentId: synthetic-profile-doc-001
law-nexus.LegalDocument.sourcePath: prd/architecture/acp/M061-S03-ACP-PROFILE-OVERLAY-SHACL-MECHANICS.md
law-nexus.LegalDocument.provider: synthetic-profile-provider
---

# Example Legal Document

Synthetic legal-document metadata fixture. It contains no legal text and does not validate parser completeness, Russian legal evidence, retrieval quality, or R035/R037/R038.
""",
}

LAW_NEXUS_DISCOVERY_SHAPES_TTL = """@prefix lawNexus: <https://repolex.ai/ontology/kit/law-nexus/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

# M061/S04 local-equivalent generated-style discovery shapes.
# These target-class shapes let git-lex list discover the law-nexus profile
# classes in the disposable workspace without publishing a domain kit.

lawNexus:SourceProviderShape a sh:NodeShape ;
  sh:targetClass lawNexus:SourceProvider .

lawNexus:SourceBlockShape a sh:NodeShape ;
  sh:targetClass lawNexus:SourceBlock .

lawNexus:EvidenceSpanShape a sh:NodeShape ;
  sh:targetClass lawNexus:EvidenceSpan .

lawNexus:CitationShape a sh:NodeShape ;
  sh:targetClass lawNexus:Citation .

lawNexus:RetrievalQueryShape a sh:NodeShape ;
  sh:targetClass lawNexus:RetrievalQuery .

lawNexus:RetrievalAnswerShape a sh:NodeShape ;
  sh:targetClass lawNexus:RetrievalAnswer .

lawNexus:FalkorDBGraphObservationShape a sh:NodeShape ;
  sh:targetClass lawNexus:FalkorDBGraphObservation .

lawNexus:CypherSafetyCheckShape a sh:NodeShape ;
  sh:targetClass lawNexus:CypherSafetyCheck .
"""

COMPOSED_PROFILE_TTL = """@prefix acp: <https://repolex.ai/ontology/kit/acp/> .
@prefix lawNexus: <https://repolex.ai/ontology/kit/law-nexus/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# M061/S04 generated-style composed proof profile.
# Diagnostic runtime-smoke shape only; not ACP source truth or production packaging.

acp:ValidationClaimShape a sh:NodeShape ;
  sh:targetClass acp:ValidationClaim ;
  sh:property [
    sh:path acp:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path acp:verdict ;
    sh:in ("pass" "fail" "needs-attention" "needs-remediation" "blocked" "not-applicable") ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path acp:hasLifecycleState ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path acp:hasAuthorityClass ;
    sh:minCount 1 ;
  ] .

acp:ProofGateShape a sh:NodeShape ;
  sh:targetClass acp:ProofGate ;
  sh:property [
    sh:path acp:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path acp:sourceArtifact ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] .

acp:EvidenceAnchorShape a sh:NodeShape ;
  sh:targetClass acp:EvidenceAnchor ;
  sh:property [
    sh:path acp:sourceArtifact ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path acp:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] .

lawNexus:ParserRunShape a sh:NodeShape ;
  sh:targetClass lawNexus:ParserRun ;
  sh:property [
    sh:path lawNexus:synthetic ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:proofStatus ;
    sh:in ("example-only" "observed-runtime" "blocked") ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:observedAt ;
    sh:datatype xsd:dateTime ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:parserName ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:sourcePath ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] .

lawNexus:LegalDocumentShape a sh:NodeShape ;
  sh:targetClass lawNexus:LegalDocument ;
  sh:property [
    sh:path lawNexus:synthetic ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:proofStatus ;
    sh:in ("example-only" "observed-runtime" "blocked") ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:sourcePath ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] .

lawNexus:ACPBoundaryLinkShape a sh:NodeShape ;
  sh:targetClass lawNexus:ACPBoundaryLink ;
  sh:property [
    sh:path lawNexus:synthetic ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:proofStatus ;
    sh:in ("example-only" "observed-runtime" "blocked") ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:sourcePath ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] .
"""

SPARQL_PREFIXES = """PREFIX acp: <https://repolex.ai/ontology/kit/acp/>
PREFIX lawNexus: <https://repolex.ai/ontology/kit/law-nexus/>
"""


def with_prefixes(query_body: str) -> str:
    return f"{SPARQL_PREFIXES}{query_body}"


NEGATIVE_CASES = (
    NegativeCase(
        case_id="acp-invalid-verdict",
        class_path="ACP/ValidationClaim",
        filename="negative-invalid-verdict.md",
        query=with_prefixes("SELECT ?s WHERE { ?s a acp:ValidationClaim }"),
        replacements=(("acp.ValidationClaim.verdict: pass", "acp.ValidationClaim.verdict: bogus"),),
    ),
    NegativeCase(
        case_id="acp-missing-source-artifact",
        class_path="ACP/ProofGate",
        filename="negative-missing-source-artifact.md",
        query=with_prefixes("SELECT ?s WHERE { ?s a acp:ProofGate }"),
        replacements=(
            (
                "acp.ProofGate.sourceArtifact: prd/architecture/acp/M061-S03-ACP-PROFILE-OVERLAY-SHACL-MECHANICS.md\n",
                "",
            ),
        ),
    ),
    NegativeCase(
        case_id="law-nexus-invalid-observed-at",
        class_path="LawNexus/ParserRun",
        filename="negative-invalid-observed-at.md",
        query=with_prefixes("SELECT ?s WHERE { ?s a lawNexus:ParserRun }"),
        replacements=(
            (
                "law-nexus.ParserRun.observedAt: 2026-06-15T00:00:00Z",
                "law-nexus.ParserRun.observedAt: not-a-date",
            ),
        ),
    ),
    NegativeCase(
        case_id="law-nexus-missing-synthetic",
        class_path="LawNexus/LegalDocument",
        filename="negative-missing-synthetic.md",
        query=with_prefixes("SELECT ?s WHERE { ?s a lawNexus:LegalDocument }"),
        replacements=(("law-nexus.LegalDocument.synthetic: true\n", ""),),
    ),
    NegativeCase(
        case_id="law-nexus-invalid-proof-status",
        class_path="LawNexus/LegalDocument",
        filename="negative-invalid-proof-status.md",
        query=with_prefixes("SELECT ?s WHERE { ?s a lawNexus:LegalDocument }"),
        replacements=(
            (
                "law-nexus.LegalDocument.proofStatus: example-only",
                "law-nexus.LegalDocument.proofStatus: approved",
            ),
        ),
    ),
)

POSITIVE_QUERIES = (
    ("query-validation-claim", with_prefixes("SELECT ?s WHERE { ?s a acp:ValidationClaim }")),
    ("query-proof-gate", with_prefixes("SELECT ?s WHERE { ?s a acp:ProofGate }")),
    ("query-evidence-anchor", with_prefixes("SELECT ?s WHERE { ?s a acp:EvidenceAnchor }")),
    ("query-parser-run", with_prefixes("SELECT ?s WHERE { ?s a lawNexus:ParserRun }")),
    ("query-legal-document", with_prefixes("SELECT ?s WHERE { ?s a lawNexus:LegalDocument }")),
    ("query-acp-boundary-link", with_prefixes("SELECT ?s WHERE { ?s a lawNexus:ACPBoundaryLink }")),
)


def truncate_output(value: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n...[truncated {len(value) - limit} chars]"


def json_safe_output(value: str) -> str:
    return truncate_output(value.replace("\r\n", "\n"))


def main_residue_paths(root: Path = ROOT) -> list[Path]:
    return [root / name for name in MAIN_RESIDUE_NAMES]


def check_main_residue(root: Path = ROOT) -> dict[str, bool]:
    return {path.name: path.exists() for path in main_residue_paths(root)}


def assert_no_main_residue(root: Path = ROOT) -> None:
    residue = check_main_residue(root)
    present = [name for name, exists in residue.items() if exists]
    if present:
        joined = ", ".join(present)
        raise RuntimeError(f"main checkout residue present: {joined}")


def git_lex_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{GIT_LEX_BIN_DIR}:{env.get('PATH', '')}"
    return env


def default_run_command(command: Sequence[str], cwd: Path, env: dict[str, str]) -> CommandResult:
    completed = subprocess.run(  # noqa: S603 - commands are static harness inputs.
        list(command),
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return CommandResult(
        command=list(command),
        cwd=str(cwd),
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_checked_command(
    command: Sequence[str],
    cwd: Path,
    *,
    runner: RunCommand = default_run_command,
    root: Path = ROOT,
) -> tuple[CommandResult, dict[str, bool], dict[str, bool]]:
    assert_no_main_residue(root)
    pre = check_main_residue(root)
    result = runner(command, cwd, git_lex_env())
    post = check_main_residue(root)
    assert_no_main_residue(root)
    return result, pre, post


def command_to_string(command: Sequence[str]) -> str:
    return " ".join(command)


def row_count_from_query(stdout: str) -> int | None:
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, list):
        return len(parsed)
    if isinstance(parsed, dict):
        for key in ("rows", "results", "bindings"):
            value = parsed.get(key)
            if isinstance(value, list):
                return len(value)
        results = parsed.get("results")
        if isinstance(results, dict):
            bindings = results.get("bindings")
            if isinstance(bindings, list):
                return len(bindings)
    return None


def count_assertions(stdout: str) -> int | None:
    for token in stdout.replace("+", " ").replace(",", " ").split():
        if token.isdigit():
            return int(token)
    return None


def make_record(
    *,
    phase: str,
    step: str,
    result: CommandResult | None,
    workspace: Path,
    classification: str,
    pre_residue: dict[str, bool] | None = None,
    post_residue: dict[str, bool] | None = None,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "phase": phase,
        "step": step,
        "workspace": str(workspace),
        "classification": classification,
        "pre_residue": pre_residue if pre_residue is not None else check_main_residue(),
        "post_residue": post_residue if post_residue is not None else check_main_residue(),
    }
    if result is not None:
        record.update(
            {
                "command": command_to_string(result.command),
                "cwd": result.cwd,
                "exit_code": result.exit_code,
                "stdout": json_safe_output(result.stdout),
                "stderr": json_safe_output(result.stderr),
            }
        )
    else:
        record.update({"command": None, "cwd": str(workspace), "exit_code": None, "stdout": "", "stderr": ""})
    if details:
        record["details"] = details
    return record


def write_jsonl(records: Iterable[dict[str, object]], path: Path = DIAGNOSTICS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def reset_diagnostics(path: Path = DIAGNOSTICS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def ensure_artifact_dirs() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    SHAPES_DIR.mkdir(parents=True, exist_ok=True)
    NEGATIVE_CASES_DIR.mkdir(parents=True, exist_ok=True)


def write_runtime_inputs(base_dir: Path) -> list[Path]:
    written: list[Path] = []
    for relative, content in POSITIVE_FIXTURES.items():
        path = base_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    shape_path = base_dir / "shapes/composed-profile.ttl"
    shape_path.parent.mkdir(parents=True, exist_ok=True)
    shape_path.write_text(COMPOSED_PROFILE_TTL, encoding="utf-8")
    written.append(shape_path)
    return written


def create_workspace(workspace_dir: Path | None = None) -> tuple[Path, bool]:
    if workspace_dir is None:
        workspace = Path("/tmp") / f"s061-s04-{uuid.uuid4().hex[:12]}"
        workspace.mkdir(parents=True)
        return workspace, True
    workspace = workspace_dir.resolve()
    if not str(workspace).startswith("/tmp/s061-s04-"):
        raise ValueError("--workspace-dir must be under /tmp/s061-s04-*")
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace, False


def copy_kit_scaffold(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def set_repo_kit(repo_yml: Path, kit: str) -> None:
    lines = repo_yml.read_text(encoding="utf-8").splitlines()
    updated = []
    replaced = False
    for line in lines:
        if line.startswith("kit:"):
            updated.append(f"kit: {kit}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append(f"kit: {kit}")
    repo_yml.write_text("\n".join(updated) + "\n", encoding="utf-8")


def install_profile_overlay(workspace: Path) -> None:
    copied_root = workspace / ".m061-s04-kit-source"
    copy_kit_scaffold(ROOT / "git-lex-kit-acp", copied_root / "git-lex-kit-acp")
    copy_kit_scaffold(ROOT / "git-lex-kit-law-nexus", copied_root / "git-lex-kit-law-nexus")

    lex_local_kit = workspace / ".lex/kit/local/git-lex-kit-law-nexus"
    copy_kit_scaffold(copied_root / "git-lex-kit-law-nexus", lex_local_kit)

    law_ontology_dest = workspace / ".lex/ontology/law-nexus"
    law_ontology_dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        copied_root / "git-lex-kit-law-nexus/ontology/law-nexus/law-nexus.ttl",
        law_ontology_dest / "law-nexus.ttl",
    )

    (law_ontology_dest / "law-nexus-shapes.ttl").write_text(
        LAW_NEXUS_DISCOVERY_SHAPES_TTL, encoding="utf-8"
    )

    composed_dest = workspace / ".lex/ontology/m061-s04"
    composed_dest.mkdir(parents=True, exist_ok=True)
    (composed_dest / "composed-profile.ttl").write_text(COMPOSED_PROFILE_TTL, encoding="utf-8")
    (composed_dest / "m061-s04-shapes.ttl").write_text(COMPOSED_PROFILE_TTL, encoding="utf-8")
    set_repo_kit(workspace / ".lex/repo.yml", LAW_NEXUS_LOCAL_KIT)


def install_positive_fixtures(workspace: Path) -> None:
    # Keep a repo-path fixture copy for durable path parity and a class-folder copy
    # for git-lex document discovery in the isolated workspace.
    write_runtime_inputs(workspace / ARTIFACT_DIR.relative_to(ROOT))
    for relative, content in POSITIVE_FIXTURES.items():
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def replace_fixture_content(content: str, replacements: tuple[tuple[str, str], ...]) -> str:
    updated = content
    for old, new in replacements:
        if old not in updated:
            raise ValueError(f"negative fixture replacement target not found: {old!r}")
        updated = updated.replace(old, new)
    return updated


def install_negative_fixture(workspace: Path, case: NegativeCase) -> None:
    install_positive_fixtures(workspace)
    if case.class_path == "ACP/ValidationClaim":
        source = POSITIVE_FIXTURES["ACP/ValidationClaim/example-profile-validation-claim.md"]
    elif case.class_path == "ACP/ProofGate":
        source = POSITIVE_FIXTURES["ACP/ProofGate/example-profile-proof-gate.md"]
    elif case.class_path == "LawNexus/ParserRun":
        source = POSITIVE_FIXTURES["LawNexus/ParserRun/example-parser-run.md"]
    elif case.class_path == "LawNexus/LegalDocument":
        source = POSITIVE_FIXTURES["LawNexus/LegalDocument/example-legal-document.md"]
    else:  # pragma: no cover - guarded by static cases.
        raise ValueError(f"unsupported negative class path: {case.class_path}")
    content = replace_fixture_content(source, case.replacements)
    for base in (workspace, workspace / ARTIFACT_DIR.relative_to(ROOT) / "fixtures"):
        path = base / case.class_path / case.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def provision_workspace(
    workspace: Path,
    *,
    runner: RunCommand = default_run_command,
    phase: str = "setup",
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for command, step in (
        (["git", "init", "-q"], "git-init"),
        (["git", "config", "user.name", "M061 S04 Runtime Proof"], "git-config-name"),
        (["git", "config", "user.email", "m061-s04@example.invalid"], "git-config-email"),
    ):
        result, pre, post = run_checked_command(command, workspace, runner=runner)
        records.append(
            make_record(
                phase=phase,
                step=step,
                result=result,
                workspace=workspace,
                classification="pass" if result.exit_code == 0 else "blocked",
                pre_residue=pre,
                post_residue=post,
            )
        )
        if result.exit_code != 0:
            return records

    init_command = ["git-lex", "init", "--kit", ACP_KIT_SPEC, str(workspace)]
    result, pre, post = run_checked_command(init_command, workspace, runner=runner)
    records.append(
        make_record(
            phase=phase,
            step="git-lex-init-acp-explicit",
            result=result,
            workspace=workspace,
            classification="pass" if result.exit_code == 0 else "blocked",
            pre_residue=pre,
            post_residue=post,
            details={"kit_spec": ACP_KIT_SPEC},
        )
    )
    if result.exit_code != 0:
        return records

    install_profile_overlay(workspace)
    install_positive_fixtures(workspace)

    for command, step in (
        (["git", "add", "."], "git-add-fixtures"),
        (["git", "commit", "-m", "install m061 s04 overlay fixtures"], "git-commit-fixtures"),
    ):
        result, pre, post = run_checked_command(command, workspace, runner=runner)
        records.append(
            make_record(
                phase=phase,
                step=step,
                result=result,
                workspace=workspace,
                classification="pass" if result.exit_code == 0 else "blocked",
                pre_residue=pre,
                post_residue=post,
            )
        )
        if result.exit_code != 0:
            return records

    result, pre, post = run_checked_command(["git-lex", "list", "--json"], workspace, runner=runner)
    row_count = row_count_from_query(result.stdout)
    records.append(
        make_record(
            phase=phase,
            step="git-lex-list-json",
            result=result,
            workspace=workspace,
            classification="pass" if result.exit_code == 0 else "blocked",
            pre_residue=pre,
            post_residue=post,
            details={"class_count": row_count},
        )
    )
    return records


def run_positive(
    workspace_dir: Path | None = None,
    *,
    runner: RunCommand = default_run_command,
    cleanup: bool = True,
) -> list[dict[str, object]]:
    workspace, disposable = create_workspace(workspace_dir)
    records: list[dict[str, object]] = []
    try:
        records.extend(provision_workspace(workspace, runner=runner, phase="setup"))
        if records and records[-1]["classification"] == "blocked":
            return records

        for command, step in (
            (["git-lex", "validate"], "validate"),
            (["git-lex", "sync"], "sync"),
        ):
            result, pre, post = run_checked_command(command, workspace, runner=runner)
            classification = "pass" if result.exit_code == 0 else "blocked"
            details: dict[str, object] = {}
            if step == "sync":
                details["assertion_count_hint"] = count_assertions(result.stdout)
            records.append(
                make_record(
                    phase="positive",
                    step=step,
                    result=result,
                    workspace=workspace,
                    classification=classification,
                    pre_residue=pre,
                    post_residue=post,
                    details=details,
                )
            )
            if result.exit_code != 0:
                return records

        for step, query in POSITIVE_QUERIES:
            result, pre, post = run_checked_command(
                ["git-lex", "query", query, "--json"], workspace, runner=runner
            )
            rows = row_count_from_query(result.stdout)
            classification = "pass" if result.exit_code == 0 and rows is not None and rows >= 1 else "blocked"
            records.append(
                make_record(
                    phase="positive",
                    step=step,
                    result=result,
                    workspace=workspace,
                    classification=classification,
                    pre_residue=pre,
                    post_residue=post,
                    details={"row_count": rows, "query": query},
                )
            )
        return records
    finally:
        if cleanup and disposable and workspace.exists():
            shutil.rmtree(workspace)


def classify_negative(validate_result: CommandResult) -> str:
    combined = f"{validate_result.stdout}\n{validate_result.stderr}".lower()
    if validate_result.exit_code != 0:
        return "fail-closed"
    if "violation" in combined or "fail" in combined:
        return "fail-closed"
    return "pass-with-shape-violation"


def run_negative_case(
    case: NegativeCase,
    *,
    runner: RunCommand = default_run_command,
    cleanup: bool = True,
) -> list[dict[str, object]]:
    workspace, disposable = create_workspace(None)
    records: list[dict[str, object]] = []
    try:
        records.extend(provision_workspace(workspace, runner=runner, phase="setup"))
        if records and records[-1]["classification"] == "blocked":
            return records
        install_negative_fixture(workspace, case)
        result, pre, post = run_checked_command(["git", "add", "."], workspace, runner=runner)
        records.append(
            make_record(
                phase="negative",
                step=f"{case.case_id}:git-add-negative",
                result=result,
                workspace=workspace,
                classification="pass" if result.exit_code == 0 else "blocked",
                pre_residue=pre,
                post_residue=post,
                details={"case_id": case.case_id},
            )
        )
        if result.exit_code != 0:
            return records
        result, pre, post = run_checked_command(
            ["git", "commit", "-m", f"install {case.case_id}"], workspace, runner=runner
        )
        records.append(
            make_record(
                phase="negative",
                step=f"{case.case_id}:git-commit-negative",
                result=result,
                workspace=workspace,
                classification="pass" if result.exit_code == 0 else "blocked",
                pre_residue=pre,
                post_residue=post,
                details={"case_id": case.case_id},
            )
        )
        if result.exit_code != 0:
            return records

        validate_result, pre, post = run_checked_command(["git-lex", "validate"], workspace, runner=runner)
        classification = classify_negative(validate_result)
        records.append(
            make_record(
                phase="negative",
                step=f"{case.case_id}:validate",
                result=validate_result,
                workspace=workspace,
                classification=classification,
                pre_residue=pre,
                post_residue=post,
                details={"case_id": case.case_id},
            )
        )

        query_result, pre, post = run_checked_command(
            ["git-lex", "query", case.query, "--json"], workspace, runner=runner
        )
        rows = row_count_from_query(query_result.stdout)
        records.append(
            make_record(
                phase="negative",
                step=f"{case.case_id}:query",
                result=query_result,
                workspace=workspace,
                classification=classification,
                pre_residue=pre,
                post_residue=post,
                details={"case_id": case.case_id, "row_count": rows, "query": case.query},
            )
        )
        return records
    finally:
        if cleanup and disposable and workspace.exists():
            shutil.rmtree(workspace)


def run_negative(*, runner: RunCommand = default_run_command) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for case in NEGATIVE_CASES:
        records.extend(run_negative_case(case, runner=runner))
    records.append(
        make_record(
            phase="negative",
            step="object-link-negative",
            result=None,
            workspace=Path("/tmp/s061-s04-object-link-blocked"),
            classification="blocked",
            details={
                "case_id": "object-link-negative",
                "reason": "Deferred per M058/M060 because frontmatter object values can normalize to IRIs and produce false negatives.",
            },
        )
    )
    return records


def summarize(records: list[dict[str, object]]) -> dict[str, object]:
    by_phase: dict[str, int] = {}
    classifications: dict[str, int] = {}
    for record in records:
        phase = str(record["phase"])
        classification = str(record["classification"])
        by_phase[phase] = by_phase.get(phase, 0) + 1
        classifications[classification] = classifications.get(classification, 0) + 1
    return {
        "diagnostics_path": str(DIAGNOSTICS_PATH.relative_to(ROOT)),
        "records": len(records),
        "records_by_phase": by_phase,
        "classifications": classifications,
        "main_residue": check_main_residue(),
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--positive", action="store_true", help="run positive validate/sync/query proof")
    group.add_argument("--negative", action="store_true", help="run scalar negative validation probes")
    group.add_argument("--all", action="store_true", help="run positive and negative proof flows")
    parser.add_argument("--workspace-dir", type=Path, help="optional /tmp/s061-s04-* workspace for positive run")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    ensure_artifact_dirs()
    reset_diagnostics()
    records: list[dict[str, object]] = []
    try:
        assert_no_main_residue()
        if args.positive:
            records.extend(run_positive(args.workspace_dir))
        elif args.negative:
            records.extend(run_negative())
        else:
            records.extend(run_positive(args.workspace_dir))
            records.extend(run_negative())
        assert_no_main_residue()
    except Exception as exc:  # noqa: BLE001 - command harness must emit failure diagnostics.
        records.append(
            make_record(
                phase="harness",
                step="exception",
                result=None,
                workspace=args.workspace_dir or Path("/tmp/s061-s04-unallocated"),
                classification="blocked",
                details={"error": str(exc)},
            )
        )
        write_jsonl(records)
        print(json.dumps(summarize(records), ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    write_jsonl(records)
    summary = summarize(records)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if any(record["classification"] == "blocked" and record["phase"] != "negative" for record in records):
        return 1
    if args.positive or args.all:
        positive_blocked = [
            record
            for record in records
            if record["phase"] == "positive" and record["classification"] != "pass"
        ]
        if positive_blocked:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
