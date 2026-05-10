#!/usr/bin/env python3
"""Run a bounded M002 PyO3 smoke for FalkorDB text-to-cypher.

The harness creates a proof-only temporary PyO3/maturin package, builds it in the
current Python environment, imports the resulting module, and calls only local
construction/serialization helpers. It intentionally skips provider-backed
NL-to-Cypher generation unless a later task explicitly adds secure secret handling.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import textwrap
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

SCHEMA_VERSION = "m002-text-to-cypher-pyo3-smoke/v1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / ".gsd/runtime-smoke/text-to-cypher-pyo3"
MODULE_NAME = "text_to_cypher_pyo3_smoke"
Status = Literal["confirmed-runtime", "blocked-environment", "failed-runtime", "skipped"]

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
)


@dataclass(frozen=True)
class CommandResult:
    phase: str
    command: list[str]
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    stdout: str
    stderr: str
    log_path: str


@dataclass
class SmokeState:
    output_dir: Path
    workspace_dir: Path
    log_dir: Path
    timeout_seconds: int
    falkordb_url: str
    phase_results: list[CommandResult] = field(default_factory=list)
    findings: dict[str, dict[str, object]] = field(default_factory=dict)


def parse_positive_timeout(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("timeout must be >= 1")
    return parsed


def redact(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: match.group(0).split("=", 1)[0] + "=<redacted>" if "=" in match.group(0) else "<redacted>", redacted)
    return redacted


def write_log(log_dir: Path, phase: str, stdout: str, stderr: str = "") -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{phase}.log"
    content = f"# phase: {phase}\n\n## stdout\n{redact(stdout)}\n\n## stderr\n{redact(stderr)}\n"
    path.write_text(content, encoding="utf-8")
    return path


def run_command(command: list[str], *, cwd: Path, state: SmokeState, phase: str) -> CommandResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=state.timeout_seconds,
            check=False,
        )
        timed_out = False
        exit_code: int | None = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        stderr = f"{stderr}\nTIMEOUT after {state.timeout_seconds}s".strip()
    duration_ms = int((time.monotonic() - started) * 1000)
    log_path = write_log(state.log_dir, phase, stdout, stderr)
    result = CommandResult(
        phase=phase,
        command=command,
        exit_code=exit_code,
        timed_out=timed_out,
        duration_ms=duration_ms,
        stdout=redact(stdout)[-4000:],
        stderr=redact(stderr)[-4000:],
        log_path=str(log_path.relative_to(state.output_dir)),
    )
    state.phase_results.append(result)
    return result


def classify_command_failure(result: CommandResult) -> str:
    if result.timed_out:
        return f"{result.phase}-timeout"
    return f"{result.phase}-exit-{result.exit_code}"


def put_finding(
    state: SmokeState,
    finding_id: str,
    status: Status,
    evidence_class: str,
    summary: str,
    diagnostics: dict[str, object] | None = None,
) -> None:
    state.findings[finding_id] = {
        "id": finding_id,
        "status": status,
        "evidence_class": evidence_class,
        "summary": summary,
        "diagnostics": diagnostics or {"root_cause": "none"},
    }


def create_smoke_project(workspace_dir: Path) -> Path:
    project_dir = workspace_dir / "text_to_cypher_pyo3_smoke"
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    (project_dir / "Cargo.toml").write_text(
        textwrap.dedent(
            f"""
            [package]
            name = "{MODULE_NAME}"
            version = "0.1.0"
            edition = "2021"
            publish = false

            [lib]
            name = "{MODULE_NAME}"
            crate-type = ["cdylib"]

            [dependencies]
            pyo3 = {{ version = "0.27", features = ["extension-module"] }}
            serde_json = "1"
            text-to-cypher = {{ version = "0.1.10", default-features = false }}
            tokio = {{ version = "1", features = ["rt-multi-thread"] }}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [build-system]
            requires = ["maturin>=1.0,<2.0"]
            build-backend = "maturin"

            [project]
            name = "text-to-cypher-pyo3-smoke"
            version = "0.1.0"
            requires-python = ">=3.13"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (src_dir / "lib.rs").write_text(
        textwrap.dedent(
            f'''
            use pyo3::prelude::*;
            use serde_json::json;
            use text_to_cypher::{{ChatMessage, ChatRequest, ChatRole, TextToCypherClient}};

            #[pyfunction]
            fn binding_metadata() -> PyResult<String> {{
                Ok(json!({{
                    "module": "{MODULE_NAME}",
                    "text_to_cypher_crate": "0.1.10",
                    "provider_calls": "skipped-by-design"
                }}).to_string())
            }}

            #[pyfunction]
            fn make_chat_request(question: String) -> PyResult<String> {{
                let request = ChatRequest {{
                    messages: vec![ChatMessage {{
                        role: ChatRole::User,
                        content: question,
                    }}],
                }};
                serde_json::to_string(&request).map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))
            }}

            #[pyfunction]
            fn construct_client_metadata(model: String, falkordb_connection: String) -> PyResult<String> {{
                let _client = TextToCypherClient::new(model.clone(), "__redacted_test_key__", falkordb_connection.clone());
                Ok(json!({{
                    "constructed": true,
                    "model": model,
                    "falkordb_connection": falkordb_connection,
                    "api_key": "<redacted>"
                }}).to_string())
            }}

            #[pymodule]
            fn {MODULE_NAME}(m: &Bound<'_, PyModule>) -> PyResult<()> {{
                m.add_function(wrap_pyfunction!(binding_metadata, m)?)?;
                m.add_function(wrap_pyfunction!(make_chat_request, m)?)?;
                m.add_function(wrap_pyfunction!(construct_client_metadata, m)?)?;
                Ok(())
            }}
            '''
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return project_dir


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def run_smoke(output_dir: Path, timeout_seconds: int, falkordb_url: str, keep_workspace: bool) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir = output_dir / "workspace"
    if workspace_dir.exists() and not keep_workspace:
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    state = SmokeState(
        output_dir=output_dir,
        workspace_dir=workspace_dir,
        log_dir=output_dir / "logs",
        timeout_seconds=timeout_seconds,
        falkordb_url=falkordb_url,
    )

    put_finding(
        state,
        "provider-backed-generation",
        "skipped",
        "out-of-scope",
        "Provider-backed cypher generation was skipped by design; this smoke must not require secrets.",
        {"root_cause": "provider-required-skipped"},
    )

    if not command_available("uvx"):
        put_finding(
            state,
            "maturin-build",
            "blocked-environment",
            "environment",
            "uvx is unavailable, so maturin could not be run without mutating project dependencies.",
            {"root_cause": "dependency-unavailable", "missing": "uvx"},
        )
    else:
        project_dir = create_smoke_project(workspace_dir)
        build = run_command(
            [
                "uvx",
                "--from",
                "maturin",
                "maturin",
                "develop",
                "--uv",
                "--manifest-path",
                "Cargo.toml",
                "--quiet",
            ],
            cwd=project_dir,
            state=state,
            phase="maturin-build",
        )
        if build.exit_code == 0 and not build.timed_out:
            put_finding(
                state,
                "maturin-build",
                "confirmed-runtime",
                "confirmed",
                "maturin built and installed the proof-only PyO3 module in the active Python environment.",
            )
            import_code = textwrap.dedent(
                f"""
                import json
                import {MODULE_NAME} as smoke

                metadata = json.loads(smoke.binding_metadata())
                request = json.loads(smoke.make_chat_request('Find cited evidence spans'))
                client = json.loads(smoke.construct_client_metadata('smoke-model', {state.falkordb_url!r}))
                assert metadata['provider_calls'] == 'skipped-by-design'
                assert request['messages'][0]['role'] == 'user'
                assert client['api_key'] == '<redacted>'
                print(json.dumps({{'metadata': metadata, 'request_role': request['messages'][0]['role'], 'constructed': client['constructed']}}, sort_keys=True))
                """
            ).strip()
            imported = run_command(
                [sys.executable, "-c", import_code],
                cwd=project_dir,
                state=state,
                phase="python-import",
            )
            if imported.exit_code == 0 and not imported.timed_out:
                put_finding(
                    state,
                    "python-import",
                    "confirmed-runtime",
                    "confirmed",
                    "Python imported the PyO3 module and exercised local serialization/construction helpers.",
                    {"root_cause": "none", "stdout_tail": imported.stdout[-500:]},
                )
            else:
                put_finding(
                    state,
                    "python-import",
                    "failed-runtime",
                    "contradicted",
                    "Python import or helper execution failed after a successful maturin build.",
                    {"root_cause": classify_command_failure(imported), "log": imported.log_path},
                )
        else:
            put_finding(
                state,
                "maturin-build",
                "failed-runtime",
                "contradicted",
                "maturin failed to build the proof-only PyO3 module.",
                {"root_cause": classify_command_failure(build), "log": build.log_path},
            )

    overall_status = payload_status(state.findings)
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": overall_status,
        "phase": "runtime-results",
        "python_executable": sys.executable,
        "falkordb_url": falkordb_url,
        "provider_calls": "skipped-by-design",
        "workspace_dir": str(workspace_dir),
        "findings": list(state.findings.values()),
        "commands": [asdict(result) for result in state.phase_results],
        "boundaries": {
            "proves": [
                "PyO3/maturin build status for a proof-only wrapper",
                "Python import status for local construction and serialization helpers",
            ],
            "does_not_prove": [
                "provider-backed NL-to-Cypher generation",
                "generated Cypher correctness or safety",
                "Legal KnowQL product behavior",
                "legal-answer correctness",
                "Garant ODT parsing or retrieval quality",
            ],
        },
    }
    write_artifacts(output_dir, payload)
    return payload


def payload_status(findings: dict[str, dict[str, object]]) -> Status:
    build = findings.get("maturin-build", {})
    imported = findings.get("python-import", {})
    if build.get("status") == "confirmed-runtime" and imported.get("status") == "confirmed-runtime":
        return "confirmed-runtime"
    if any(finding.get("status") == "failed-runtime" for finding in findings.values()):
        return "failed-runtime"
    return "blocked-environment"


def write_artifacts(output_dir: Path, payload: dict[str, object]) -> tuple[Path, Path]:
    json_path = output_dir / "TEXT-TO-CYPHER-PYO3-SMOKE.json"
    markdown_path = output_dir / "TEXT-TO-CYPHER-PYO3-SMOKE.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    findings = payload["findings"]
    assert isinstance(findings, list)
    lines = [
        "# M002 Text-to-Cypher PyO3 Smoke",
        "",
        f"- Schema: `{payload['schema_version']}`",
        f"- Status: `{payload['status']}`",
        f"- Provider calls: `{payload['provider_calls']}`",
        f"- FalkorDB URL: `{payload['falkordb_url']}`",
        "",
        "## Findings",
        "",
    ]
    for finding in findings:
        assert isinstance(finding, dict)
        diagnostics = finding.get("diagnostics", {})
        root_cause = diagnostics.get("root_cause") if isinstance(diagnostics, dict) else "unknown"
        lines.extend(
            [
                f"### `{finding['id']}`",
                "",
                f"- Status: `{finding['status']}`",
                f"- Evidence class: `{finding['evidence_class']}`",
                f"- Root cause: `{root_cause}`",
                f"- Summary: {finding['summary']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundaries",
            "",
            "This is bounded synthetic build/import evidence only. It does not prove provider-backed NL-to-Cypher generation, generated Cypher correctness or safety, Legal KnowQL product behavior, legal-answer correctness, Garant ODT parsing, or retrieval quality.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--timeout", type=parse_positive_timeout, default=240)
    parser.add_argument("--falkordb-url", default="falkor://127.0.0.1:6380")
    parser.add_argument("--keep-workspace", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_smoke(args.output_dir, args.timeout, args.falkordb_url, args.keep_workspace)
    print(json.dumps({"status": payload["status"], "output_dir": str(args.output_dir)}, sort_keys=True))
    return 0 if payload["status"] == "confirmed-runtime" else 1


if __name__ == "__main__":
    raise SystemExit(main())
