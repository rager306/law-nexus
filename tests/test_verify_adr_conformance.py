from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-adr-conformance.py"


def load_verifier_module() -> Any:
    spec = importlib.util.spec_from_file_location("verify_adr_conformance", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )


def write_file(path: Path, content: str) -> str:
    path.write_text(content, encoding="utf-8")
    return content


# ---------------------------------------------------------------------------
# Pure-function claim detection over synthetic in-memory content
# ---------------------------------------------------------------------------


def test_clean_tagged_claim_with_adr_ref_is_not_flagged() -> None:
    verifier = load_verifier_module()
    text = "law-nexus uses FalkorDB for the legal graph `[bounded]` (see ADR-0001).\n"
    findings = verifier.find_claim_findings("prd/ARCHITECTURE.md", text)
    assert findings == []


def test_untagged_architectural_claim_is_flagged() -> None:
    verifier = load_verifier_module()
    # Untagged claim in a non-ADR file: the lifecycle-tag check fires. (It also
    # carries a missing-adr-ref, tested separately; here we isolate untagged-claim.)
    text = "law-nexus uses FalkorDB for the legal graph.\n"
    findings = verifier.find_claim_findings("prd/ARCHITECTURE.md", text)

    untagged = [finding for finding in findings if finding.kind == "untagged-claim"]
    assert len(untagged) == 1
    finding = untagged[0]
    assert finding.file == "prd/ARCHITECTURE.md"
    assert finding.line == 1
    assert "lifecycle tag" in finding.message
    assert "uses FalkorDB" in finding.snippet


def test_missing_adr_ref_in_non_adr_file_is_flagged() -> None:
    verifier = load_verifier_module()
    # Tagged claim but no ADR reference, in a non-ADR file.
    text = "law-nexus uses FalkorDB `[bounded]` for the legal graph.\n"
    findings = verifier.find_claim_findings("prd/ARCHITECTURE.md", text)

    assert len(findings) == 1
    assert findings[0].kind == "missing-adr-ref"
    assert findings[0].line == 1
    assert "must reference an ADR" in findings[0].message


def test_plain_prose_is_not_flagged_as_a_claim() -> None:
    verifier = load_verifier_module()
    # Narrative prose with no binding adoption/structure verb -> no findings.
    text = (
        "This section describes the ADR standard and its workflow.\n"
        "The README states that ADRs follow the MADR format.\n"
        "It shows an example table and explains the numbering scheme.\n"
    )
    findings = verifier.find_claim_findings("doc/adr/README.md", text)
    assert findings == []


def test_multiple_findings_aggregate_per_line() -> None:
    verifier = load_verifier_module()
    text = (
        "# Architecture\n"
        "law-nexus uses FalkorDB.\n"  # untagged + missing-adr-ref (2 findings, 1 line)
        "The ingest pipeline is built on stdlib xml.etree `[bounded]` (ADR-0001).\n"  # clean
        "We adopt Pydantic for the domain forms.\n"  # untagged + missing-adr-ref
    )
    findings = verifier.find_claim_findings("prd/02_architecture.md", text)

    kinds = sorted(finding.kind for finding in findings)
    assert kinds == ["missing-adr-ref", "missing-adr-ref", "untagged-claim", "untagged-claim"]
    assert {finding.line for finding in findings} == {2, 4}
    assert all(finding.line != 3 for finding in findings)  # clean line untouched


def test_claim_inside_adr_file_does_not_require_an_separate_adr_ref() -> None:
    verifier = load_verifier_module()
    text = (
        "---\n"
        "id: ADR-0001\n"
        "title: Example\n"
        "status: Accepted\n"
        'lifecycle: "[validated]"\n'
        "---\n"
        "\n"
        "We adopt Pydantic v2 for the domain forms `[proposed]`.\n"
    )
    findings = verifier.find_claim_findings("doc/adr/0001-example.md", text)

    # Tagged, inside an ADR file -> the file's own id satisfies the ADR-ref rule.
    assert findings == []


def test_untagged_claim_inside_adr_file_is_still_flagged() -> None:
    verifier = load_verifier_module()
    text = (
        "---\n"
        "id: ADR-0001\n"
        "title: Example\n"
        "status: Accepted\n"
        'lifecycle: "[validated]"\n'
        "---\n"
        "\n"
        "We adopt Pydantic v2 for the domain forms.\n"
    )
    findings = verifier.find_claim_findings("doc/adr/0001-example.md", text)

    # Lifecycle tagging is mandatory even inside an ADR; ADR-ref is satisfied by the file.
    assert len(findings) == 1
    assert findings[0].kind == "untagged-claim"
    assert findings[0].line == 8


def test_code_fence_lines_are_not_flagged() -> None:
    verifier = load_verifier_module()
    text = (
        "```python\n"
        "import falkordb\n"
        "# The parser uses xml.etree.ElementTree\n"
        "client = falkordb.FalkorDB()\n"
        "```\n"
        "law-nexus uses FalkorDB `[bounded]` (ADR-0001).\n"
    )
    findings = verifier.find_claim_findings("prd/02_architecture.md", text)

    # The "uses" inside the code fence is not a claim; the tagged line is clean.
    assert findings == []


def test_front_matter_and_table_separators_are_skipped() -> None:
    verifier = load_verifier_module()
    text = (
        "---\n"
        "id: ADR-0001\n"
        "title: Uses Pydantic\n"  # "uses" in front matter must be ignored
        "---\n"
        "\n"
        "| Layer | Status |\n"
        "| --- | --- |\n"
        "| domain | uses Pydantic |\n"  # table row claim, untagged
    )
    findings = verifier.find_claim_findings("doc/adr/0001-example.md", text)

    # Only the table-row claim on the last line is flagged (untagged); the
    # front-matter "uses" and the separator are not.
    assert len(findings) == 1
    assert findings[0].kind == "untagged-claim"
    assert findings[0].line == 8


def test_all_lifecycle_tags_are_accepted_case_insensitively() -> None:
    verifier = load_verifier_module()
    tags = ["proposed", "bounded", "smoke", "validated", "deferred", "VALIDATED"]
    for tag in tags:
        text = f"law-nexus uses FalkorDB `[{tag}]` (ADR-0001).\n"
        findings = verifier.find_claim_findings("prd/ARCHITECTURE.md", text)
        assert findings == [], f"tag {tag!r} should be accepted"


def test_binding_verbs_trigger_claim_detection() -> None:
    verifier = load_verifier_module()
    verbs = [
        "law-nexus uses FalkorDB.",
        "law-nexus adopts Pydantic v2.",
        "law-nexus depends on FalkorDB.",
        "law-nexus relies on FalkorDB.",
        "The parser is implemented as an adapter.",
        "The stack is built on FalkorDB.",
        "The model is based on BGE-M3.",
        "We chose Pydantic for the forms.",
        "We decided to use FalkorDB.",
    ]
    for line in verbs:
        findings = verifier.find_claim_findings("prd/02_architecture.md", line + "\n")
        assert any(f.kind == "untagged-claim" for f in findings), (
            f"verb line not detected: {line!r}"
        )


def test_lowercase_targets_and_prose_are_not_false_positives() -> None:
    # Real-world prose that previously caused false positives. None are claims.
    verifier = load_verifier_module()
    prose = [
        "satisfy but only one adapter and one use case exercise them so far.",
        "adapters into use cases. It is not a dependency-injection framework.",
        "value depends on it).",
        "| `deadline` | `must` | Depends on source wording; verifier records rationale. |",
        "The README states that ADRs follow the MADR format.",
    ]
    for line in prose:
        findings = verifier.find_claim_findings("prd/02_architecture.md", line + "\n")
        assert findings == [], f"prose falsely flagged as claim: {line!r}"


def test_imperative_decision_claim_is_detected() -> None:
    verifier = load_verifier_module()
    text = (
        "---\n"
        "id: ADR-0001\n"
        "title: Example\n"
        "status: Accepted\n"
        'lifecycle: "[validated]"\n'
        "---\n\n"
        "## Decision\n\n"
        "Adopt a dependency-directed onion package structure.\n"
    )
    findings = verifier.find_claim_findings("doc/adr/0001-example.md", text)

    # Imperative decision claim in a Decision section is flagged (untagged).
    # It is inside an ADR file, so no missing-adr-ref is raised.
    untagged = [f for f in findings if f.kind == "untagged-claim"]
    assert len(untagged) == 1
    assert untagged[0].line == 10
    assert "onion package structure" in untagged[0].snippet
    assert all(f.kind != "missing-adr-ref" for f in findings)


def test_imperative_claim_tagged_is_clean() -> None:
    verifier = load_verifier_module()
    text = (
        "---\n"
        "id: ADR-0001\n"
        "title: Example\n"
        "status: Accepted\n"
        'lifecycle: "[validated]"\n'
        "---\n\n"
        "## Decision\n\n"
        "Adopt a dependency-directed onion structure `[validated]`.\n"
    )
    findings = verifier.find_claim_findings("doc/adr/0001-example.md", text)
    assert findings == []


def test_rejected_alternatives_are_not_flagged_as_claims() -> None:
    verifier = load_verifier_module()
    text = (
        "---\n"
        "id: ADR-0001\n"
        "title: Example\n"
        "status: Accepted\n"
        'lifecycle: "[validated]"\n'
        "---\n\n"
        "## Alternatives Considered\n\n"
        "### Option B: Adopt a dependency-injection framework at the root\n\n"
        "A container could adopt auto-wiring adapters to ports.\n"
        "### Option C: Use dataclasses instead of Pydantic\n\n"
        "Dataclasses adopt no runtime validation.\n"
        "## Decision\n\n"
        "Adopt the onion structure `[validated]`.\n"
    )
    findings = verifier.find_claim_findings("doc/adr/0001-example.md", text)

    # The Decision imperative claim (tagged) is clean; every line inside the
    # Alternatives Considered section and the Option headers are not claims.
    assert findings == []


def test_untagged_imperative_in_decision_is_flagged_but_alternatives_are_not() -> None:
    verifier = load_verifier_module()
    text = (
        "---\n"
        "id: ADR-0001\n"
        "title: Example\n"
        "status: Accepted\n"
        'lifecycle: "[validated]"\n'
        "---\n\n"
        "## Alternatives Considered\n\n"
        "### Option B: Adopt a dependency-injection framework\n\n"
        "## Decision\n\n"
        "Establish two distinct enforcement mechanisms.\n"
    )
    findings = verifier.find_claim_findings("doc/adr/0001-example.md", text)

    untagged = [f for f in findings if f.kind == "untagged-claim"]
    assert len(untagged) == 1
    # The Decision imperative on the last line is the only finding.
    assert untagged[0].snippet.startswith("Establish two distinct")


# ---------------------------------------------------------------------------
# CLI behaviour
# ---------------------------------------------------------------------------


def test_cli_clean_file_exits_zero_with_ok_summary(tmp_path: Path) -> None:
    verifier = load_verifier_module()
    clean = tmp_path / "clean.md"
    write_file(clean, "law-nexus uses FalkorDB `[bounded]` (ADR-0001).\n")

    exit_code = verifier.run([str(clean)])

    assert exit_code == 0
    assert verifier.LAST_RESULT == []


def test_cli_violations_exit_nonzero_and_print_findings(tmp_path: Path) -> None:
    verifier = load_verifier_module()
    bad = tmp_path / "bad.md"
    write_file(bad, "law-nexus uses FalkorDB.\n")

    exit_code = verifier.run([str(bad)])

    assert exit_code == 1
    assert verifier.LAST_RESULT is not None
    kinds = sorted(finding.kind for finding in verifier.LAST_RESULT)
    assert kinds == ["missing-adr-ref", "untagged-claim"]


def test_cli_report_only_exits_zero_despite_findings(tmp_path: Path) -> None:
    verifier = load_verifier_module()
    bad = tmp_path / "bad.md"
    write_file(bad, "law-nexus uses FalkorDB.\n")

    exit_code = verifier.run(["--report-only", str(bad)])

    assert exit_code == 0
    assert verifier.LAST_RESULT is not None and verifier.LAST_RESULT != []


def test_cli_subprocess_summary_json_contract(tmp_path: Path) -> None:
    clean = tmp_path / "clean.md"
    write_file(clean, "law-nexus uses FalkorDB `[bounded]` (ADR-0001).\n")

    result = run_cli(str(clean))

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "ok"
    assert summary["finding_count"] == 0
    assert summary["files_scanned"] == 1
    assert "gate" in summary["boundary"].lower()


def test_cli_default_paths_scan_known_claim_files() -> None:
    # The default file set must include the ADR-0002 scope claim files.
    result = run_cli()

    summary = json.loads(result.stdout)
    # README + ARCHITECTURE + 02_architecture + at least ADR-0001/ADR-0002.
    assert summary["files_scanned"] >= 4
    # Exit code is nonzero iff there are findings (current baseline is expected
    # to have findings; T03 retags them). Either way the summary is well-formed.
    assert summary["status"] in {"ok", "fail"}
    if summary["finding_count"]:
        assert result.returncode == 1
        assert "kind=untagged-claim" in result.stderr or "kind=missing-adr-ref" in result.stderr
    else:
        assert result.returncode == 0
