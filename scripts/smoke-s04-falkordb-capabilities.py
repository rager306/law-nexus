#!/usr/bin/env python3
"""Run bounded S04 FalkorDB Docker runtime capability smoke probes.

The harness is intentionally conservative: Docker/image/container/client failures are
classified as environment blockers, not as FalkorDB capability contradictions. All data
written by the probes is synthetic and every raw command gets a bounded log artifact.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import uuid
import venv
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

SCHEMA_VERSION = "s04-falkordb-capability-smoke/v1"
IMAGE = "falkordb/falkordb:edge"
OWNER = "S04"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / ".gsd/milestones/M001/slices/S04"
VENDOR_FALKORDB_PY = Path("/root/vendor-source/falkordb-py")
VENDOR_FALKORDBLITE = Path("/root/vendor-source/falkordblite")
EMBEDDING_MODEL_ID = "deepvk/USER-bge-m3"

Status = Literal[
    "confirmed-runtime",
    "blocked-environment",
    "failed-runtime",
    "bounded-not-product-proven",
]


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    title: str
    resolution_path: str
    verification_criteria: str
    docker_dependent: bool = False


CAPABILITIES: tuple[CapabilitySpec, ...] = (
    CapabilitySpec(
        "docker-daemon",
        "Docker daemon availability",
        "Run a bounded Docker availability probe and record daemon/version metadata.",
        "Terminal runtime status with command, exit code, duration, and raw-log reference.",
    ),
    CapabilitySpec(
        "docker-falkordb-image",
        "FalkorDB Docker image availability",
        "Inspect/pull the bounded FalkorDB image or record explicit environment blockage.",
        "Terminal image availability status with image/package/version metadata or blocked root cause.",
    ),
    CapabilitySpec(
        "falkordb-basic-graph",
        "FalkorDB basic graph query",
        "Start FalkorDB in the bounded smoke environment and execute a synthetic graph create/query/delete probe.",
        "Terminal runtime status with synthetic graph result evidence and cleanup status.",
        True,
    ),
    CapabilitySpec(
        "falkordb-udf-load-execute",
        "FalkorDB UDF load/list/execute/flush",
        "Run a synthetic JavaScript UDF load/list/execute/flush probe against FalkorDB.",
        "Terminal runtime status proving UDF behavior or naming exact load/execution failure.",
        True,
    ),
    CapabilitySpec(
        "falkordb-procedure-list",
        "FalkorDB procedure discovery",
        "Query procedure discovery/listing in the target FalkorDB runtime.",
        "Terminal runtime status with procedure evidence or exact unsupported/blocked diagnostic.",
        True,
    ),
    CapabilitySpec(
        "falkordb-fulltext-node",
        "FalkorDB node full-text index/query",
        "Create a synthetic node full-text index and query it through FalkorDB procedures.",
        "Terminal runtime status with expected synthetic rows or exact procedure/index failure.",
        True,
    ),
    CapabilitySpec(
        "falkordb-vector-node",
        "FalkorDB node vector index/query",
        "Create a synthetic node vector index and query nearest synthetic rows.",
        "Terminal runtime status with expected synthetic vector results or exact procedure/index failure.",
        True,
    ),
    CapabilitySpec(
        "falkordb-vector-distance",
        "FalkorDB vector distance functions",
        "Evaluate bounded vector distance expressions against synthetic vectors.",
        "Terminal runtime status with expected distance values or exact unsupported/error diagnostic.",
        True,
    ),
    CapabilitySpec(
        "falkordblite-import",
        "FalkorDBLite import/bootstrap",
        "Install/import FalkorDBLite in an isolated runtime boundary and record package/binary metadata.",
        "Terminal runtime status with import/bootstrap evidence or exact package/binary blocked cause.",
    ),
    CapabilitySpec(
        "falkordblite-basic-graph",
        "FalkorDBLite basic graph query",
        "Run a synthetic embedded FalkorDBLite graph create/query/delete probe if bootstrap succeeds.",
        "Terminal runtime status with embedded graph evidence or exact unavailable-module diagnostic.",
    ),
    CapabilitySpec(
        "falkordblite-udf",
        "FalkorDBLite UDF behavior",
        "Probe UDF load/list/execute/flush behavior in FalkorDBLite only after embedded module availability is proven.",
        "Terminal runtime status proving embedded UDF behavior or explicit blocked/failure diagnostic.",
    ),
    CapabilitySpec(
        "falkordblite-vector-fulltext",
        "FalkorDBLite vector/full-text behavior",
        "Probe FalkorDBLite vector and full-text procedures only after embedded module availability is proven.",
        "Terminal runtime status proving embedded procedure behavior or explicit blocked/failure diagnostic.",
    ),
    CapabilitySpec(
        "embedding-env",
        "Embedding package/cache environment",
        "Record Python package availability, model cache state, CPU/RAM/no-swap assumptions, and download boundaries.",
        "Terminal environment status with package/cache metadata and no product embedding overclaim.",
    ),
    CapabilitySpec(
        "embedding-cpu-tiny",
        "Bounded CPU embedding smoke",
        "Run only a bounded tiny/cached CPU embedding smoke if dependencies and model cache permit it.",
        "Terminal runtime status with duration/resource evidence or explicit package/cache blocked cause.",
    ),
)

FALKORDB_CAPABILITY_IDS = tuple(spec.capability_id for spec in CAPABILITIES if spec.docker_dependent)
LITE_AND_EMBEDDING_IDS = tuple(
    spec.capability_id
    for spec in CAPABILITIES
    if spec.capability_id not in {"docker-daemon", "docker-falkordb-image", *FALKORDB_CAPABILITY_IDS}
)


@dataclass
class CommandResult:
    command: list[str]
    exit_code: int | None
    timed_out: bool
    duration_seconds: float
    stdout: str
    stderr: str
    log_path: Path


@dataclass
class Finding:
    capability_id: str
    status: Status
    evidence_class: str
    phase: str
    timestamp: str
    owner: str
    resolution_path: str
    verification_criteria: str
    raw_log_reference: str
    diagnostics: dict[str, str]

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.capability_id,
            "capability_id": self.capability_id,
            "status": self.status,
            "evidence_class": self.evidence_class,
            "phase": self.phase,
            "timestamp": self.timestamp,
            "owner": self.owner,
            "resolution_path": self.resolution_path,
            "verification_criteria": self.verification_criteria,
            "raw_log_reference": self.raw_log_reference,
            "runtime_evidence": self.raw_log_reference,
            "source_evidence": None,
            "roadmap_impact": self.resolution_path,
            "diagnostics": self.diagnostics,
        }


@dataclass
class SmokeState:
    output_dir: Path
    log_dir: Path
    timestamp: str
    timeout_seconds: int
    container_name: str
    host_port: int
    findings: dict[str, Finding] = field(default_factory=dict)
    command_summary: dict[str, dict[str, object]] = field(default_factory=dict)
    image_metadata: dict[str, object] = field(default_factory=dict)
    package_metadata: dict[str, object] = field(default_factory=dict)
    cleanup_messages: list[str] = field(default_factory=list)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def relative_for_artifact(path: Path) -> str:
    resolved = path.resolve()
    project_gsd = (ROOT / ".gsd").resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        pass
    try:
        return str(Path(".gsd") / resolved.relative_to(project_gsd))
    except ValueError:
        return str(path)


def parse_positive_timeout(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("timeout must be greater than zero")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=parse_positive_timeout, default=300)
    return parser.parse_args(argv)


def allocate_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def make_container_name() -> str:
    return f"s04-falkordb-smoke-{uuid.uuid4().hex[:12]}"


def planned_cleanup_commands(container_name: str) -> list[list[str]]:
    return [["docker", "rm", "-f", container_name]]


def write_log(log_dir: Path, phase: str, content: str) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_phase = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in phase)
    path = log_dir / f"{safe_phase}.log"
    path.write_text(content, encoding="utf-8")
    return path


def run_command(command: list[str], timeout_seconds: int, log_dir: Path, phase: str) -> CommandResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        duration = time.monotonic() - started
        exit_code: int | None = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        exit_code = None
        timed_out = True
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        stderr = f"{stderr}\nTIMEOUT after {timeout_seconds}s".strip()
    rendered = "\n".join(
        [
            f"phase: {phase}",
            f"timestamp: {utc_now()}",
            f"command: {json.dumps(command)}",
            f"duration_seconds: {duration:.3f}",
            f"exit_code: {exit_code}",
            f"timed_out: {timed_out}",
            "--- stdout ---",
            stdout,
            "--- stderr ---",
            stderr,
        ]
    )
    log_path = write_log(log_dir, phase, rendered)
    return CommandResult(command, exit_code, timed_out, duration, stdout, stderr, log_path)


def summarize_command(result: CommandResult) -> dict[str, object]:
    return {
        "command": result.command,
        "exit_code": result.exit_code,
        "duration_seconds": round(result.duration_seconds, 3),
        "timed_out": result.timed_out,
        "log_path": relative_for_artifact(result.log_path),
    }


def command_root_cause(result: CommandResult, label: str) -> str:
    if result.timed_out:
        return f"{label}-timeout"
    if result.exit_code != 0:
        return f"{label}-exit-{result.exit_code}"
    return f"{label}-ok"


def command_detail(result: CommandResult) -> str:
    stdout = result.stdout.strip().splitlines()
    stderr = result.stderr.strip().splitlines()
    snippets = stdout[:3] + stderr[:3]
    if not snippets:
        return "Command completed without output."
    return " | ".join(snippets)[:900]


def finding_for(
    spec: CapabilitySpec,
    status: Status,
    phase: str,
    log_path: Path,
    root_cause: str,
    detail: str,
    timestamp: str,
    evidence_class: str = "smoke-needed",
) -> Finding:
    return Finding(
        capability_id=spec.capability_id,
        status=status,
        evidence_class=evidence_class,
        phase=phase,
        timestamp=timestamp,
        owner=OWNER,
        resolution_path=spec.resolution_path,
        verification_criteria=spec.verification_criteria,
        raw_log_reference=relative_for_artifact(log_path),
        diagnostics={"root_cause": root_cause, "detail": detail},
    )


def put_finding(
    state: SmokeState,
    capability_id: str,
    status: Status,
    phase: str,
    log_path: Path,
    root_cause: str,
    detail: str,
    evidence_class: str = "smoke-needed",
) -> None:
    spec = next(item for item in CAPABILITIES if item.capability_id == capability_id)
    state.findings[capability_id] = finding_for(
        spec,
        status,
        phase,
        log_path,
        root_cause,
        detail,
        state.timestamp,
        evidence_class,
    )


def cascade_blocker(
    state: SmokeState,
    capability_ids: tuple[str, ...],
    root_cause: str,
    detail: str,
    phase: str,
    log_path: Path,
) -> None:
    for capability_id in capability_ids:
        put_finding(
            state,
            capability_id,
            "blocked-environment",
            phase,
            log_path,
            root_cause,
            detail,
        )


def falkordblite_binary_blockers(metadata: dict[str, object]) -> list[str]:
    blockers: list[str] = []
    if not metadata.get("redis_executable"):
        blockers.append("missing-redis-server-binary")
    if not metadata.get("falkordb_module"):
        blockers.append("missing-falkordb-module")
    return blockers


def embedding_cache_roots() -> list[Path]:
    roots: list[Path] = []
    if hf_home := os.environ.get("HF_HOME"):
        roots.append(Path(hf_home) / "hub")
    if transformers_cache := os.environ.get("TRANSFORMERS_CACHE"):
        roots.append(Path(transformers_cache))
    roots.append(Path.home() / ".cache" / "huggingface" / "hub")
    deduped: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        expanded = root.expanduser()
        if expanded not in seen:
            deduped.append(expanded)
            seen.add(expanded)
    return deduped


def embedding_model_cache_metadata(model_id: str, roots: list[Path] | None = None) -> dict[str, object]:
    roots = roots or embedding_cache_roots()
    model_dir_name = f"models--{model_id.replace('/', '--')}"
    checked = [str(root / model_dir_name) for root in roots]
    for root in roots:
        model_dir = root / model_dir_name
        snapshots = model_dir / "snapshots"
        if model_dir.is_dir() and snapshots.is_dir():
            snapshot_dirs = sorted(path.name for path in snapshots.iterdir() if path.is_dir())
            return {
                "model_id": model_id,
                "present": True,
                "path": str(model_dir),
                "snapshots": snapshot_dirs[:5],
                "snapshot_count": len(snapshot_dirs),
                "checked": checked,
            }
    return {"model_id": model_id, "present": False, "checked": checked}


def local_resource_metadata() -> dict[str, object]:
    metadata: dict[str, object] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count() or "unknown",
    }
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        values: dict[str, int] = {}
        for line in meminfo.read_text(encoding="utf-8", errors="replace").splitlines():
            key, _, raw_value = line.partition(":")
            if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                digits = raw_value.strip().split()[0]
                if digits.isdigit():
                    values[key] = int(digits)
        metadata.update(
            {
                "mem_total_mib": round(values.get("MemTotal", 0) / 1024, 1),
                "mem_available_mib": round(values.get("MemAvailable", 0) / 1024, 1),
                "swap_total_mib": round(values.get("SwapTotal", 0) / 1024, 1),
                "swap_free_mib": round(values.get("SwapFree", 0) / 1024, 1),
                "no_swap": values.get("SwapTotal", 0) == 0,
            }
        )
    return metadata


def mark_out_of_harness_capabilities(state: SmokeState, log_path: Path) -> None:
    for capability_id in LITE_AND_EMBEDDING_IDS:
        put_finding(
            state,
            capability_id,
            "bounded-not-product-proven",
            "runtime-harness-boundary",
            log_path,
            "outside-docker-falkordb-harness",
            "T03 executes Docker FalkorDB runtime probes only; this capability remains bounded to a non-product-proof classification rather than a scaffold status.",
            "out-of-scope",
        )


def create_state(output_dir: Path, timeout_seconds: int) -> SmokeState:
    resolved_output = output_dir.resolve()
    if resolved_output.exists() and not resolved_output.is_dir():
        raise NotADirectoryError(f"output-dir exists but is not a directory: {output_dir}")
    resolved_output.mkdir(parents=True, exist_ok=True)
    log_dir = resolved_output / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return SmokeState(
        output_dir=resolved_output,
        log_dir=log_dir,
        timestamp=utc_now(),
        timeout_seconds=timeout_seconds,
        container_name=make_container_name(),
        host_port=allocate_free_port(),
    )


def ensure_docker(state: SmokeState) -> bool:
    result = run_command(["docker", "version", "--format", "{{json .}}"], 30, state.log_dir, "docker-daemon")
    state.command_summary["docker-daemon"] = summarize_command(result)
    if result.exit_code == 0 and not result.timed_out:
        try:
            state.package_metadata["docker_version"] = json.loads(result.stdout)
        except json.JSONDecodeError:
            state.package_metadata["docker_version_raw"] = result.stdout.strip()[:500]
        put_finding(
            state,
            "docker-daemon",
            "confirmed-runtime",
            "docker-daemon",
            result.log_path,
            "docker-daemon-ok",
            "Docker CLI reached the daemon and returned version metadata.",
            "confirmed",
        )
        return True
    root = command_root_cause(result, "docker-daemon")
    detail = command_detail(result)
    put_finding(state, "docker-daemon", "blocked-environment", "docker-daemon", result.log_path, root, detail)
    cascade_blocker(state, ("docker-falkordb-image", *FALKORDB_CAPABILITY_IDS), root, detail, "docker-daemon", result.log_path)
    return False


def ensure_image(state: SmokeState) -> bool:
    inspect = run_command(["docker", "image", "inspect", IMAGE, "--format", "{{json .}}"], 30, state.log_dir, "docker-image-inspect")
    state.command_summary["docker-image-inspect"] = summarize_command(inspect)
    result = inspect
    if inspect.exit_code != 0 or inspect.timed_out:
        pull = run_command(["docker", "pull", IMAGE], min(state.timeout_seconds, 300), state.log_dir, "docker-image-pull")
        state.command_summary["docker-image-pull"] = summarize_command(pull)
        result = pull
        if pull.exit_code == 0 and not pull.timed_out:
            inspect = run_command(["docker", "image", "inspect", IMAGE, "--format", "{{json .}}"], 30, state.log_dir, "docker-image-inspect-after-pull")
            state.command_summary["docker-image-inspect-after-pull"] = summarize_command(inspect)
            result = inspect
    if result.exit_code == 0 and not result.timed_out:
        metadata_text = result.stdout.strip()
        if metadata_text.startswith("{"):
            try:
                parsed = cast("dict[str, object]", json.loads(metadata_text))
                state.image_metadata = {
                    "image": IMAGE,
                    "id": parsed.get("Id", "unknown"),
                    "repo_digests": parsed.get("RepoDigests", []),
                    "created": parsed.get("Created", "unknown"),
                }
            except json.JSONDecodeError:
                state.image_metadata = {"image": IMAGE, "raw": metadata_text[:500]}
        else:
            state.image_metadata = {"image": IMAGE, "pull_output": metadata_text[:500]}
        put_finding(
            state,
            "docker-falkordb-image",
            "confirmed-runtime",
            "docker-falkordb-image",
            result.log_path,
            "docker-falkordb-image-ok",
            f"Image {IMAGE} is available locally or was pulled successfully.",
            "confirmed",
        )
        return True
    root = command_root_cause(result, "docker-falkordb-image")
    detail = command_detail(result)
    put_finding(
        state,
        "docker-falkordb-image",
        "blocked-environment",
        "docker-falkordb-image",
        result.log_path,
        root,
        detail,
    )
    cascade_blocker(state, FALKORDB_CAPABILITY_IDS, root, detail, "docker-falkordb-image", result.log_path)
    return False


def create_venv(state: SmokeState, parent: Path) -> Path | None:
    venv_path = parent / "venv"
    started = time.monotonic()
    try:
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_path)
    except Exception as exc:  # noqa: BLE001 - diagnostics must preserve unexpected venv failures.
        log_path = write_log(
            state.log_dir,
            "client-venv-create",
            f"phase: client-venv-create\ntimestamp: {utc_now()}\nerror: {exc!r}\n",
        )
        state.command_summary["client-venv-create"] = {
            "command": [sys.executable, "-m", "venv", str(venv_path)],
            "exit_code": 1,
            "duration_seconds": round(time.monotonic() - started, 3),
            "timed_out": False,
            "log_path": relative_for_artifact(log_path),
        }
        cascade_blocker(
            state,
            FALKORDB_CAPABILITY_IDS,
            "falkordb-client-venv-create-failed",
            repr(exc),
            "client-venv-create",
            log_path,
        )
        return None
    log_path = write_log(
        state.log_dir,
        "client-venv-create",
        f"phase: client-venv-create\ntimestamp: {utc_now()}\ncreated: {venv_path}\n",
    )
    state.command_summary["client-venv-create"] = {
        "command": [sys.executable, "-m", "venv", str(venv_path)],
        "exit_code": 0,
        "duration_seconds": round(time.monotonic() - started, 3),
        "timed_out": False,
        "log_path": relative_for_artifact(log_path),
    }
    return venv_path


def venv_python(venv_path: Path) -> Path:
    return venv_path / "bin" / "python"


def install_client(state: SmokeState, venv_path: Path) -> bool:
    if not VENDOR_FALKORDB_PY.is_dir():
        log_path = write_log(
            state.log_dir,
            "client-install",
            f"phase: client-install\ntimestamp: {utc_now()}\nmissing: {VENDOR_FALKORDB_PY}\n",
        )
        cascade_blocker(
            state,
            FALKORDB_CAPABILITY_IDS,
            "falkordb-client-source-missing",
            f"Vendor source path is missing: {VENDOR_FALKORDB_PY}",
            "client-install",
            log_path,
        )
        return False
    result = run_command(
        [str(venv_python(venv_path)), "-m", "pip", "install", str(VENDOR_FALKORDB_PY)],
        min(state.timeout_seconds, 180),
        state.log_dir,
        "client-install",
    )
    state.command_summary["client-install"] = summarize_command(result)
    if result.exit_code == 0 and not result.timed_out:
        state.package_metadata["falkordb_py_source"] = str(VENDOR_FALKORDB_PY)
        state.package_metadata["falkordb_py_install_log"] = relative_for_artifact(result.log_path)
        return True
    cascade_blocker(
        state,
        FALKORDB_CAPABILITY_IDS,
        command_root_cause(result, "falkordb-client-install"),
        command_detail(result),
        "client-install",
        result.log_path,
    )
    return False


def wait_for_container_ready(state: SmokeState) -> bool:
    deadline = time.monotonic() + min(state.timeout_seconds, 30)
    last_result: CommandResult | None = None
    while time.monotonic() < deadline:
        last_result = run_command(
            ["docker", "exec", state.container_name, "redis-cli", "PING"],
            5,
            state.log_dir,
            "container-readiness",
        )
        if last_result.exit_code == 0 and "PONG" in last_result.stdout:
            state.command_summary["container-readiness"] = summarize_command(last_result)
            return True
        time.sleep(0.5)
    if last_result is None:
        last_result = run_command(
            ["docker", "exec", state.container_name, "redis-cli", "PING"],
            5,
            state.log_dir,
            "container-readiness",
        )
    state.command_summary["container-readiness"] = summarize_command(last_result)
    root = command_root_cause(last_result, "docker-falkordb-readiness")
    if root == "docker-falkordb-readiness-ok":
        root = "docker-falkordb-readiness-timeout"
    detail = command_detail(last_result)
    cascade_blocker(state, FALKORDB_CAPABILITY_IDS, root, detail, "container-readiness", last_result.log_path)
    return False


def start_container(state: SmokeState) -> bool:
    command = [
        "docker",
        "run",
        "-d",
        "--name",
        state.container_name,
        "-p",
        f"127.0.0.1:{state.host_port}:6379",
        IMAGE,
    ]
    result = run_command(command, min(state.timeout_seconds, 120), state.log_dir, "container-start")
    state.command_summary["container-start"] = summarize_command(result)
    state.package_metadata["falkordb_container"] = {
        "name": state.container_name,
        "host": "127.0.0.1",
        "port": state.host_port,
    }
    if result.exit_code == 0 and not result.timed_out:
        return wait_for_container_ready(state)
    root = command_root_cause(result, "docker-falkordb-container")
    detail = command_detail(result)
    cascade_blocker(state, FALKORDB_CAPABILITY_IDS, root, detail, "container-start", result.log_path)
    return False


def write_probe_script(path: Path, port: int, graph_suffix: str) -> None:
    code = f'''
import json
import traceback
from falkordb import FalkorDB

PORT = {port}
GRAPH_SUFFIX = {graph_suffix!r}
results = {{}}

def ok(capability_id, detail):
    results[capability_id] = {{"status": "confirmed-runtime", "root_cause": f"{{capability_id}}-ok", "detail": detail}}

def fail(capability_id, exc):
    results[capability_id] = {{
        "status": "failed-runtime",
        "root_cause": f"{{capability_id}}-exception",
        "detail": repr(exc),
        "traceback": traceback.format_exc(limit=4),
    }}

def run(capability_id, callback):
    try:
        callback()
    except Exception as exc:
        fail(capability_id, exc)

client = FalkorDB(host="127.0.0.1", port=PORT)

def basic_graph():
    graph = client.select_graph(f"s04_basic_{{GRAPH_SUFFIX}}")
    graph.query("CREATE (:Smoke {{name:'alpha', value: 1}})")
    rows = graph.query("MATCH (n:Smoke {{name:'alpha'}}) RETURN n.value").result_set
    if rows != [[1]]:
        raise AssertionError(f"unexpected rows: {{rows!r}}")
    graph.delete()
    ok("falkordb-basic-graph", f"synthetic graph query returned {{rows!r}}")

run("falkordb-basic-graph", basic_graph)

def udf_probe():
    client.udf_flush()
    script = """
    function my_add(x, y) {{
        return x + y;
    }}
    falkor.register('my_add', my_add);
    """
    result = client.udf_load("s04lib", script, replace=True)
    if result != "OK":
        raise AssertionError(f"udf_load returned {{result!r}}")
    udfs = client.udf_list()
    graph = client.select_graph(f"s04_udf_{{GRAPH_SUFFIX}}")
    rows = graph.query("RETURN s04lib.my_add(5, 3) AS result").result_set
    if rows != [[8]]:
        raise AssertionError(f"unexpected UDF rows: {{rows!r}}")
    client.udf_flush()
    graph.delete()
    ok("falkordb-udf-load-execute", f"udf list={{udfs!r}}; execution rows={{rows!r}}")

run("falkordb-udf-load-execute", udf_probe)

def procedure_probe():
    graph = client.select_graph(f"s04_procedure_{{GRAPH_SUFFIX}}")
    rows = graph.query("CALL dbms.procedures() YIELD name RETURN name LIMIT 5").result_set
    if not isinstance(rows, list):
        raise AssertionError(f"procedure rows not a list: {{rows!r}}")
    graph.delete()
    ok("falkordb-procedure-list", f"procedure listing returned {{len(rows)}} rows")

run("falkordb-procedure-list", procedure_probe)

def fulltext_probe():
    graph = client.select_graph(f"s04_fulltext_{{GRAPH_SUFFIX}}")
    created = graph.create_node_fulltext_index("Doc", "body")
    graph.query("CREATE (:Doc {{body:'synthetic law graph evidence'}})")
    listed = graph.list_indices().result_set
    if not listed:
        raise AssertionError("fulltext index not listed")
    graph.delete()
    ok("falkordb-fulltext-node", f"fulltext index created={{created.indices_created}}; indices={{listed!r}}")

run("falkordb-fulltext-node", fulltext_probe)

def vector_node_probe():
    graph = client.select_graph(f"s04_vector_node_{{GRAPH_SUFFIX}}")
    created = graph.create_node_vector_index("Embedding", "vec", dim=4, similarity_function="euclidean")
    listed = graph.list_indices().result_set
    if not listed:
        raise AssertionError("vector index not listed")
    graph.delete()
    ok("falkordb-vector-node", f"vector index created={{created.indices_created}}; indices={{listed!r}}")

run("falkordb-vector-node", vector_node_probe)

def vector_distance_probe():
    graph = client.select_graph(f"s04_vector_distance_{{GRAPH_SUFFIX}}")
    rows = graph.query("RETURN vecf32([1.0, 2.0, 3.0, 4.0])").result_set
    actual = [round(float(value), 3) for value in rows[0][0]]
    if actual != [1.0, 2.0, 3.0, 4.0]:
        raise AssertionError(f"unexpected vector result: {{actual!r}}")
    graph.delete()
    ok("falkordb-vector-distance", f"vecf32 synthetic vector returned {{actual!r}}")

run("falkordb-vector-distance", vector_distance_probe)

client.close()
print(json.dumps(results, sort_keys=True))
'''
    path.write_text(textwrap.dedent(code).strip() + "\n", encoding="utf-8")


def run_runtime_probes(state: SmokeState, venv_path: Path, work_dir: Path) -> None:
    probe_path = work_dir / "runtime_probes.py"
    write_probe_script(probe_path, state.host_port, uuid.uuid4().hex[:8])
    result = run_command(
        [str(venv_python(venv_path)), str(probe_path)],
        min(state.timeout_seconds, 180),
        state.log_dir,
        "runtime-probes",
    )
    state.command_summary["runtime-probes"] = summarize_command(result)
    if result.exit_code != 0 or result.timed_out:
        cascade_blocker(
            state,
            FALKORDB_CAPABILITY_IDS,
            command_root_cause(result, "falkordb-runtime-probes"),
            command_detail(result),
            "runtime-probes",
            result.log_path,
        )
        return
    try:
        probe_results = cast("dict[str, dict[str, str]]", json.loads(result.stdout))
    except json.JSONDecodeError as exc:
        cascade_blocker(
            state,
            FALKORDB_CAPABILITY_IDS,
            "falkordb-runtime-probes-malformed-json",
            f"Probe script output was not JSON: {exc}; output={result.stdout[:500]!r}",
            "runtime-probes",
            result.log_path,
        )
        return
    for capability_id in FALKORDB_CAPABILITY_IDS:
        probe = probe_results.get(capability_id)
        if probe is None:
            put_finding(
                state,
                capability_id,
                "failed-runtime",
                "runtime-probes",
                result.log_path,
                f"{capability_id}-missing-result",
                "Runtime probe JSON omitted this capability.",
            )
            continue
        status = cast("Status", probe.get("status", "failed-runtime"))
        root = probe.get("root_cause", f"{capability_id}-unknown")
        detail = probe.get("detail", "Runtime probe returned no detail.")
        evidence_class = "confirmed" if status == "confirmed-runtime" else "smoke-needed"
        put_finding(state, capability_id, status, "runtime-probes", result.log_path, root, detail, evidence_class)


def write_falkordblite_probe_script(path: Path, graph_suffix: str) -> None:
    code = f'''
import json
import traceback
import redislite
from redislite.falkordb_client import FalkorDB

GRAPH_SUFFIX = {graph_suffix!r}
results = {{}}
metadata = {{
    "redislite_version": getattr(redislite, "__version__", "unknown"),
    "redis_executable": getattr(redislite, "__redis_executable__", ""),
    "falkordb_module": getattr(redislite, "__falkordb_module__", ""),
    "redis_server_version": getattr(redislite, "__redis_server_version__", ""),
}}


def ok(capability_id, detail):
    results[capability_id] = {{"status": "confirmed-runtime", "root_cause": f"{{capability_id}}-ok", "detail": detail}}


def bounded(capability_id, root_cause, detail):
    results[capability_id] = {{"status": "bounded-not-product-proven", "root_cause": root_cause, "detail": detail}}


def fail(capability_id, exc):
    results[capability_id] = {{
        "status": "failed-runtime",
        "root_cause": f"{{capability_id}}-exception",
        "detail": repr(exc),
        "traceback": traceback.format_exc(limit=4),
    }}


missing = []
if not metadata["redis_executable"]:
    missing.append("redis-server")
if not metadata["falkordb_module"]:
    missing.append("falkordb.so")
if missing:
    print(json.dumps({{"metadata": metadata, "missing_binaries": missing, "results": results}}, sort_keys=True))
    raise SystemExit(0)

ok("falkordblite-import", f"import ok with embedded binaries: {{metadata!r}}")


def run(capability_id, callback):
    try:
        callback()
    except Exception as exc:
        fail(capability_id, exc)


def basic_graph():
    db = FalkorDB()
    try:
        graph = db.select_graph(f"s04_lite_basic_{{GRAPH_SUFFIX}}")
        graph.query("CREATE (:Smoke {{name:'lite', value: 2}})")
        rows = graph.query("MATCH (n:Smoke {{name:'lite'}}) RETURN n.value").result_set
        if rows != [[2]]:
            raise AssertionError(f"unexpected rows: {{rows!r}}")
        graph.delete()
        ok("falkordblite-basic-graph", f"synthetic embedded graph query returned {{rows!r}}")
    finally:
        db.close()


run("falkordblite-basic-graph", basic_graph)


def udf_probe():
    db = FalkorDB()
    try:
        db.udf_flush()
        script = """
        function lite_add(x, y) {{
            return x + y;
        }}
        falkor.register('lite_add', lite_add);
        """
        loaded = db.udf_load("s04litelib", script, replace=True)
        graph = db.select_graph(f"s04_lite_udf_{{GRAPH_SUFFIX}}")
        rows = graph.query("RETURN s04litelib.lite_add(7, 4) AS result").result_set
        if rows != [[11]]:
            raise AssertionError(f"unexpected UDF rows: {{rows!r}}; loaded={{loaded!r}}")
        db.udf_flush()
        graph.delete()
        ok("falkordblite-udf", f"udf load={{loaded!r}}; rows={{rows!r}}")
    finally:
        db.close()


run("falkordblite-udf", udf_probe)


def vector_fulltext_probe():
    db = FalkorDB()
    try:
        graph = db.select_graph(f"s04_lite_index_{{GRAPH_SUFFIX}}")
        fulltext_created = graph.create_node_fulltext_index("Doc", "body")
        vector_created = graph.create_node_vector_index("Embedding", "vec", dim=4, similarity_function="euclidean")
        listed = graph.list_indices().result_set
        if not listed:
            raise AssertionError("embedded indices not listed")
        graph.delete()
        ok(
            "falkordblite-vector-fulltext",
            f"fulltext={{fulltext_created.indices_created}}; vector={{vector_created.indices_created}}; indices={{listed!r}}",
        )
    finally:
        db.close()


run("falkordblite-vector-fulltext", vector_fulltext_probe)

print(json.dumps({{"metadata": metadata, "missing_binaries": missing, "results": results}}, sort_keys=True))
'''
    path.write_text(textwrap.dedent(code).strip() + "\n", encoding="utf-8")


def create_probe_venv(state: SmokeState, parent: Path, label: str) -> Path | None:
    venv_path = parent / label
    started = time.monotonic()
    command = [sys.executable, "-m", "venv", str(venv_path)]
    try:
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_path)
    except Exception as exc:  # noqa: BLE001 - diagnostics must preserve unexpected venv failures.
        log_path = write_log(
            state.log_dir,
            f"{label}-create",
            f"phase: {label}-create\ntimestamp: {utc_now()}\nerror: {exc!r}\n",
        )
        state.command_summary[f"{label}-create"] = {
            "command": command,
            "exit_code": 1,
            "duration_seconds": round(time.monotonic() - started, 3),
            "timed_out": False,
            "log_path": relative_for_artifact(log_path),
        }
        return None
    log_path = write_log(
        state.log_dir,
        f"{label}-create",
        f"phase: {label}-create\ntimestamp: {utc_now()}\ncreated: {venv_path}\n",
    )
    state.command_summary[f"{label}-create"] = {
        "command": command,
        "exit_code": 0,
        "duration_seconds": round(time.monotonic() - started, 3),
        "timed_out": False,
        "log_path": relative_for_artifact(log_path),
    }
    return venv_path


def run_falkordblite_probes(state: SmokeState, work_dir: Path) -> None:
    lite_ids = ("falkordblite-import", "falkordblite-basic-graph", "falkordblite-udf", "falkordblite-vector-fulltext")
    if not VENDOR_FALKORDBLITE.is_dir():
        log_path = write_log(
            state.log_dir,
            "falkordblite-source",
            f"phase: falkordblite-source\ntimestamp: {utc_now()}\nmissing: {VENDOR_FALKORDBLITE}\n",
        )
        cascade_blocker(
            state,
            lite_ids,
            "falkordblite-source-missing",
            f"Vendor source path is missing: {VENDOR_FALKORDBLITE}",
            "falkordblite-source",
            log_path,
        )
        return
    venv_path = create_probe_venv(state, work_dir, "falkordblite-venv")
    if venv_path is None:
        log_path = state.log_dir / "falkordblite-venv-create.log"
        cascade_blocker(
            state,
            lite_ids,
            "falkordblite-venv-create-failed",
            "Could not create an isolated FalkorDBLite verification venv.",
            "falkordblite-venv-create",
            log_path,
        )
        return
    install_result = run_command(
        [str(venv_python(venv_path)), "-m", "pip", "install", str(VENDOR_FALKORDBLITE)],
        min(state.timeout_seconds, 240),
        state.log_dir,
        "falkordblite-install",
    )
    state.command_summary["falkordblite-install"] = summarize_command(install_result)
    state.package_metadata["falkordblite_source"] = str(VENDOR_FALKORDBLITE)
    state.package_metadata["falkordblite_install_log"] = relative_for_artifact(install_result.log_path)
    if install_result.exit_code != 0 or install_result.timed_out:
        cascade_blocker(
            state,
            lite_ids,
            command_root_cause(install_result, "falkordblite-install"),
            command_detail(install_result),
            "falkordblite-install",
            install_result.log_path,
        )
        return
    probe_path = work_dir / "falkordblite_probes.py"
    write_falkordblite_probe_script(probe_path, uuid.uuid4().hex[:8])
    result = run_command(
        [str(venv_python(venv_path)), str(probe_path)],
        min(state.timeout_seconds, 120),
        state.log_dir,
        "falkordblite-probes",
    )
    state.command_summary["falkordblite-probes"] = summarize_command(result)
    if result.exit_code != 0 or result.timed_out:
        cascade_blocker(
            state,
            lite_ids,
            command_root_cause(result, "falkordblite-probes"),
            command_detail(result),
            "falkordblite-probes",
            result.log_path,
        )
        return
    try:
        payload = cast("dict[str, object]", json.loads(result.stdout))
    except json.JSONDecodeError as exc:
        cascade_blocker(
            state,
            lite_ids,
            "falkordblite-probes-malformed-json",
            f"Probe output was not JSON: {exc}; output={result.stdout[:500]!r}",
            "falkordblite-probes",
            result.log_path,
        )
        return
    metadata = cast("dict[str, object]", payload.get("metadata", {}))
    state.package_metadata["falkordblite"] = metadata
    blockers = falkordblite_binary_blockers(metadata)
    if blockers:
        detail = f"FalkorDBLite imported but embedded binary metadata is incomplete: {', '.join(blockers)}."
        put_finding(
            state,
            "falkordblite-import",
            "blocked-environment",
            "falkordblite-probes",
            result.log_path,
            "falkordblite-missing-embedded-binaries",
            detail,
        )
        cascade_blocker(
            state,
            ("falkordblite-basic-graph", "falkordblite-udf", "falkordblite-vector-fulltext"),
            "falkordblite-missing-embedded-binaries",
            detail,
            "falkordblite-probes",
            result.log_path,
        )
        return
    probe_results = cast("dict[str, dict[str, str]]", payload.get("results", {}))
    for capability_id in lite_ids:
        probe = probe_results.get(capability_id)
        if probe is None:
            put_finding(
                state,
                capability_id,
                "failed-runtime",
                "falkordblite-probes",
                result.log_path,
                f"{capability_id}-missing-result",
                "FalkorDBLite probe JSON omitted this capability.",
            )
            continue
        status = cast("Status", probe.get("status", "failed-runtime"))
        evidence_class = "confirmed" if status == "confirmed-runtime" else "smoke-needed"
        put_finding(
            state,
            capability_id,
            status,
            "falkordblite-probes",
            result.log_path,
            probe.get("root_cause", f"{capability_id}-unknown"),
            probe.get("detail", "FalkorDBLite probe returned no detail."),
            evidence_class,
        )


def write_embedding_probe_script(path: Path, model_id: str) -> None:
    code = f'''
import importlib.util
import json
import os
import time

MODEL_ID = {model_id!r}
packages = {{
    "sentence_transformers": importlib.util.find_spec("sentence_transformers") is not None,
    "torch": importlib.util.find_spec("torch") is not None,
    "transformers": importlib.util.find_spec("transformers") is not None,
}}
cache = json.loads(os.environ["S04_EMBEDDING_CACHE_METADATA"])
results = {{}}
missing = [name for name, available in packages.items() if not available]
if missing:
    results["embedding-env"] = {{
        "status": "blocked-environment",
        "root_cause": "embedding-packages-missing",
        "detail": f"Missing Python packages for local embedding smoke: {{missing!r}}; cache={{cache!r}}",
    }}
elif not cache.get("present"):
    results["embedding-env"] = {{
        "status": "blocked-environment",
        "root_cause": "embedding-model-cache-missing",
        "detail": f"Model cache for {{MODEL_ID}} is absent; mandatory checks do not download models. checked={{cache.get('checked')}}",
    }}
else:
    results["embedding-env"] = {{
        "status": "confirmed-runtime",
        "root_cause": "embedding-env-ok",
        "detail": f"Required packages importable and local Hugging Face cache found for {{MODEL_ID}}: {{cache!r}}",
    }}

if not packages.get("sentence_transformers") or not packages.get("torch"):
    results["embedding-cpu-tiny"] = {{
        "status": "blocked-environment",
        "root_cause": "embedding-packages-missing",
        "detail": "Optional tiny CPU encode skipped because sentence-transformers/torch are not importable.",
    }}
elif not cache.get("present"):
    results["embedding-cpu-tiny"] = {{
        "status": "bounded-not-product-proven",
        "root_cause": "embedding-model-cache-missing-no-download",
        "detail": f"Optional tiny CPU encode skipped to avoid downloading {{MODEL_ID}}; embedding suitability remains unresolved.",
    }}
else:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    started = time.monotonic()
    try:
        from sentence_transformers import SentenceTransformer
        try:
            model = SentenceTransformer(MODEL_ID, device="cpu", local_files_only=True)
        except TypeError:
            model = SentenceTransformer(MODEL_ID, device="cpu")
        vector = model.encode(["synthetic legal graph smoke"], normalize_embeddings=True)
        shape = getattr(vector, "shape", None)
        results["embedding-cpu-tiny"] = {{
            "status": "bounded-not-product-proven",
            "root_cause": "embedding-cpu-tiny-ok",
            "detail": f"Local CPU encode completed in {{time.monotonic() - started:.3f}}s with shape={{shape!r}}; this is not product throughput proof.",
        }}
    except Exception as exc:
        results["embedding-cpu-tiny"] = {{
            "status": "failed-runtime",
            "root_cause": "embedding-cpu-tiny-exception",
            "detail": repr(exc),
        }}

print(json.dumps({{"packages": packages, "cache": cache, "results": results}}, sort_keys=True))
'''
    path.write_text(textwrap.dedent(code).strip() + "\n", encoding="utf-8")


def run_embedding_probes(state: SmokeState, work_dir: Path) -> None:
    cache_metadata = embedding_model_cache_metadata(EMBEDDING_MODEL_ID)
    resources = local_resource_metadata()
    state.package_metadata["embedding"] = {"model_cache": cache_metadata, "resources": resources}
    probe_path = work_dir / "embedding_probes.py"
    write_embedding_probe_script(probe_path, EMBEDDING_MODEL_ID)
    env = os.environ.copy()
    env.update(
        {
            "S04_EMBEDDING_CACHE_METADATA": json.dumps(cache_metadata, sort_keys=True),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, str(probe_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=min(state.timeout_seconds, 90),
            env=env,
        )
        duration = time.monotonic() - started
        result = CommandResult(
            [sys.executable, str(probe_path)],
            completed.returncode,
            False,
            duration,
            completed.stdout,
            completed.stderr,
            write_log(
                state.log_dir,
                "embedding-probes",
                "\n".join(
                    [
                        "phase: embedding-probes",
                        f"timestamp: {utc_now()}",
                        f"command: {json.dumps([sys.executable, str(probe_path)])}",
                        f"duration_seconds: {duration:.3f}",
                        f"exit_code: {completed.returncode}",
                        "timed_out: False",
                        f"resource_metadata: {json.dumps(resources, sort_keys=True)}",
                        "--- stdout ---",
                        completed.stdout,
                        "--- stderr ---",
                        completed.stderr,
                    ]
                ),
            ),
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        result = CommandResult(
            [sys.executable, str(probe_path)],
            None,
            True,
            duration,
            exc.stdout if isinstance(exc.stdout, str) else "",
            f"{exc.stderr if isinstance(exc.stderr, str) else ''}\nTIMEOUT after {min(state.timeout_seconds, 90)}s".strip(),
            write_log(state.log_dir, "embedding-probes", f"phase: embedding-probes\ntimestamp: {utc_now()}\nTIMEOUT\n"),
        )
    state.command_summary["embedding-probes"] = summarize_command(result)
    if result.exit_code != 0 or result.timed_out:
        cascade_blocker(
            state,
            ("embedding-env", "embedding-cpu-tiny"),
            command_root_cause(result, "embedding-probes"),
            command_detail(result),
            "embedding-probes",
            result.log_path,
        )
        return
    try:
        payload = cast("dict[str, object]", json.loads(result.stdout))
    except json.JSONDecodeError as exc:
        cascade_blocker(
            state,
            ("embedding-env", "embedding-cpu-tiny"),
            "embedding-probes-malformed-json",
            f"Embedding probe output was not JSON: {exc}; output={result.stdout[:500]!r}",
            "embedding-probes",
            result.log_path,
        )
        return
    embedding_metadata = cast("dict[str, object]", state.package_metadata["embedding"])
    embedding_metadata.update(
        {
            "packages": payload.get("packages", {}),
            "cache": payload.get("cache", {}),
        }
    )
    probe_results = cast("dict[str, dict[str, str]]", payload.get("results", {}))
    for capability_id in ("embedding-env", "embedding-cpu-tiny"):
        probe = probe_results.get(capability_id)
        if probe is None:
            put_finding(
                state,
                capability_id,
                "failed-runtime",
                "embedding-probes",
                result.log_path,
                f"{capability_id}-missing-result",
                "Embedding probe JSON omitted this capability.",
            )
            continue
        status = cast("Status", probe.get("status", "failed-runtime"))
        evidence_class = "confirmed" if status == "confirmed-runtime" else "smoke-needed"
        if status == "bounded-not-product-proven":
            evidence_class = "out-of-scope"
        put_finding(
            state,
            capability_id,
            status,
            "embedding-probes",
            result.log_path,
            probe.get("root_cause", f"{capability_id}-unknown"),
            probe.get("detail", "Embedding probe returned no detail."),
            evidence_class,
        )


def cleanup_container(state: SmokeState) -> None:
    for index, command in enumerate(planned_cleanup_commands(state.container_name)):
        result = run_command(command, 30, state.log_dir, f"cleanup-{index + 1}")
        state.command_summary[f"cleanup-{index + 1}"] = summarize_command(result)
        if result.exit_code == 0 or "No such container" in result.stderr:
            state.cleanup_messages.append(f"cleanup ok: {' '.join(command)}")
        else:
            state.cleanup_messages.append(
                f"cleanup failed: {' '.join(command)} exit={result.exit_code} log={relative_for_artifact(result.log_path)}"
            )


def finalize_missing_findings(state: SmokeState, log_path: Path) -> None:
    for spec in CAPABILITIES:
        if spec.capability_id not in state.findings:
            put_finding(
                state,
                spec.capability_id,
                "bounded-not-product-proven",
                "runtime-finalization",
                log_path,
                "runtime-harness-did-not-exercise-capability",
                "The harness produced no direct result for this capability; it is bounded rather than left as a scaffold status.",
            )


def artifact_json(state: SmokeState, log_path: Path) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": state.timestamp,
        "phase": "runtime-results",
        "capabilities": [spec.capability_id for spec in CAPABILITIES],
        "findings": [state.findings[spec.capability_id].to_json() for spec in CAPABILITIES],
        "command_summary": state.command_summary,
        "image_metadata": state.image_metadata,
        "package_metadata": state.package_metadata,
        "cleanup_status": "; ".join(state.cleanup_messages) or "No cleanup actions were required.",
        "log_artifact_path": relative_for_artifact(log_path),
    }


def write_json_artifact(state: SmokeState, log_path: Path) -> Path:
    path = state.output_dir / "S04-FALKORDB-CAPABILITY-SMOKE.json"
    path.write_text(json.dumps(artifact_json(state, log_path), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_markdown_artifact(state: SmokeState, json_path: Path) -> Path:
    path = state.output_dir / "S04-FALKORDB-CAPABILITY-SMOKE.md"
    lines = [
        "# S04 FalkorDB Capability Smoke",
        "",
        "## Purpose",
        "",
        "This artifact records bounded runtime smoke results for FalkorDB/FalkorDBLite capability claims while preserving the M001 architecture-only boundary. Runtime successes confirm only the synthetic probe behavior listed here; they do not implement LegalGraph ETL/import/product pipeline behavior and do not use legal document contents.",
        "",
        "## Capability Findings",
        "",
        "| Capability ID | Status | Evidence Class | Owner | Resolution Path | Verification Criteria | Raw Log |",
        "|---|---|---|---|---|---|---|",
    ]
    for spec in CAPABILITIES:
        finding = state.findings[spec.capability_id]
        lines.append(
            f"| `{finding.capability_id}` | {finding.status} | {finding.evidence_class} | {finding.owner} | {finding.resolution_path} | {finding.verification_criteria} | `{finding.raw_log_reference}` |"
        )
    lines.extend(
        [
            "",
            "## Runtime Boundary",
            "",
            "The Docker harness uses only synthetic graph data and bounded local environment metadata. Docker daemon, image, container, and client failures are environment blockers; source/docs evidence is not upgraded to runtime proof, and bounded non-Docker capabilities remain non-product-proven unless a dedicated runtime probe executes.",
            "",
            "## Command Summary",
            "",
            "| Phase | Command | Duration (s) | Exit Code | Timed Out | Log |",
            "|---|---|---:|---:|---|---|",
        ]
    )
    for phase, summary in state.command_summary.items():
        command = " ".join(str(part) for part in cast("list[object]", summary.get("command", [])))
        lines.append(
            f"| {phase} | `{command}` | {summary.get('duration_seconds', 'N/A')} | {summary.get('exit_code', 'N/A')} | {summary.get('timed_out', 'N/A')} | `{summary.get('log_path', 'N/A')}` |"
        )
    embedding_metadata = cast("dict[str, object]", state.package_metadata.get("embedding", {}))
    lines.extend(
        [
            "",
            "## Environment Metadata",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Docker daemon | {state.findings['docker-daemon'].status} |",
            f"| FalkorDB image | {json.dumps(state.image_metadata, sort_keys=True)} |",
            f"| FalkorDB package | {json.dumps(state.package_metadata.get('falkordb_py_source', 'not-installed'))} |",
            f"| FalkorDBLite package | {json.dumps(state.package_metadata.get('falkordblite', state.package_metadata.get('falkordblite_source', 'not-installed')), sort_keys=True)} |",
            f"| sentence-transformers / torch packages | {json.dumps(embedding_metadata.get('packages', 'not-checked'), sort_keys=True)} |",
            f"| Embedding model cache | {json.dumps(embedding_metadata.get('model_cache', 'not-checked'), sort_keys=True)} |",
            f"| JSON artifact | `{relative_for_artifact(json_path)}` |",
            "",
            "## Cleanup Status",
            "",
            "; ".join(state.cleanup_messages) or "No cleanup actions were required.",
            "",
            "## Failure Diagnostics",
            "",
            "| Capability ID | Root Cause | Detail |",
            "|---|---|---|",
        ]
    )
    for spec in CAPABILITIES:
        finding = state.findings[spec.capability_id]
        lines.append(
            f"| `{finding.capability_id}` | {finding.diagnostics['root_cause']} | {finding.diagnostics['detail'].replace('|', '/')} |"
        )
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "```bash",
            "uv run python scripts/verify-s04-falkordb-smoke.py --require-runtime-results",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_smoke(output_dir: Path, timeout_seconds: int) -> SmokeState:
    state = create_state(output_dir, timeout_seconds)
    boundary_log = write_log(
        state.log_dir,
        "runtime-harness-boundary",
        "phase: runtime-harness-boundary\n"
        f"timestamp: {state.timestamp}\n"
        "scope: Docker FalkorDB probes only; no legal document contents.\n",
    )
    mark_out_of_harness_capabilities(state, boundary_log)
    with tempfile.TemporaryDirectory(prefix="s04-falkordb-smoke-") as temp_name:
        temp_parent = Path(temp_name)
        try:
            run_falkordblite_probes(state, temp_parent)
            run_embedding_probes(state, temp_parent)
            if ensure_docker(state) and ensure_image(state):
                venv_path = create_venv(state, temp_parent)
                if venv_path is not None and install_client(state, venv_path) and start_container(state):
                    run_runtime_probes(state, venv_path, temp_parent)
        finally:
            cleanup_container(state)
            state.cleanup_messages.append(f"temporary workspace removed: {temp_parent}")
            finalize_log = write_log(
                state.log_dir,
                "runtime-finalization",
                f"phase: runtime-finalization\ntimestamp: {utc_now()}\nfindings: {sorted(state.findings)}\n",
            )
            finalize_missing_findings(state, finalize_log)
    json_path = write_json_artifact(state, finalize_log)
    write_markdown_artifact(state, json_path)
    return state


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        state = run_smoke(args.output_dir, args.timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - CLI must return a diagnostic instead of a traceback-only crash.
        print(f"S04 FalkorDB smoke harness failed before artifact completion: {exc}", file=sys.stderr)
        return 2
    blocked_or_failed = [
        finding
        for finding in state.findings.values()
        if finding.status in {"blocked-environment", "failed-runtime"}
    ]
    print(f"S04 FalkorDB smoke artifacts written to {state.output_dir}")
    print(f"Container: {state.container_name} on 127.0.0.1:{state.host_port}")
    print(f"Blocked/failed findings: {len(blocked_or_failed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
