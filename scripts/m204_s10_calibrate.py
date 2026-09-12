#!/usr/bin/env python3
"""Bounded sequential C4 calibration for M204/S10.

This is a process-only measurement helper.  It never edits the Rust contour,
never claims full-corpus acceptance, and records monotonic elapsed time from the
owned subprocess rather than deriving duration from timestamps.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "consru_export/consru_export/exports"
GARANT = ROOT / "law-source/garant"
CONTRACT = ROOT / "prd/architecture/npa-acceptance-contract.yaml"
PARSER = ROOT / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
OUT = ROOT / "prd/migration/rust-evidence/m204-s10-c4-calibration-jobs1-1000.json"
FROZEN_OUT = ROOT / "prd/migration/rust-evidence/m204-s10-frozen-hashes.json"
EXPECTED = 43_785
LIMIT = 1_000
FLOOR_MS = 3_600_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def toolchain() -> dict[str, Any]:
    result: dict[str, Any] = {"commands_exit_code": {}}
    for name in ("rustc", "cargo"):
        try:
            proc = subprocess.run(
                [name, "--version"], cwd=ROOT, capture_output=True, text=True, check=False
            )
            result[name] = (proc.stdout or proc.stderr).strip()
            result["commands_exit_code"][name] = proc.returncode
        except OSError as exc:
            result[name] = str(exc)
            result["commands_exit_code"][name] = 127
    return result


def parser_revision() -> str:
    marker = 'pub const PARSER_REVISION: &str = "'
    text = PARSER.read_text(encoding="utf-8")
    start = text.index(marker) + len(marker)
    return text[start : text.index('"', start)]


def frozen_paths() -> list[Path]:
    evidence = ROOT / "prd/migration/rust-evidence"
    patterns = (
        "m203-s08-*.json",
        "m203-s08-*.jsonl",
        "m203-s09-*.json",
        "m203-s09-*.jsonl",
        "m204-s06-*.json",
        "m204-s07-*.json",
        "m204-validation-battery-20260912.json",
    )
    paths = {path for pattern in patterns for path in evidence.glob(pattern) if path.is_file()}
    return sorted(paths, key=lambda path: path.as_posix())


def write_frozen_manifest() -> None:
    if FROZEN_OUT.exists():
        raise SystemExit(f"refusing to overwrite immutable output: {FROZEN_OUT}")
    files = frozen_paths()
    payload = {
        "schema": "m204-s10-frozen-hashes/v1",
        "created_at": utc_now(),
        "scope": [
            "m203-s08 JSON/JSONL",
            "m203-s09 receipts",
            "m204-s06 JSON",
            "m204-s07 JSON",
            "m204-validation-battery-20260912.json",
        ],
        "files": [
            {"path": rel(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}
            for path in files
        ],
        "non_claims": [
            "manifest proves byte identity only",
            "it does not validate semantic acceptance",
            "S10 outputs are outside this frozen boundary",
        ],
    }
    with FROZEN_OUT.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def verify_frozen_manifest() -> None:
    if not FROZEN_OUT.is_file():
        raise SystemExit(f"frozen manifest missing: {FROZEN_OUT}")
    payload = json.loads(FROZEN_OUT.read_text(encoding="utf-8"))
    if payload.get("schema") != "m204-s10-frozen-hashes/v1":
        raise SystemExit("frozen manifest schema mismatch")
    expected = {entry["path"]: entry["sha256"] for entry in payload.get("files", [])}
    actual = {rel(path): sha256(path) for path in frozen_paths()}
    if expected != actual:
        missing = sorted(set(expected) - set(actual))
        added = sorted(set(actual) - set(expected))
        changed = sorted(
            path for path in set(expected) & set(actual) if expected[path] != actual[path]
        )
        raise SystemExit(
            f"frozen boundary changed: missing={missing}, added={added}, changed={changed}"
        )


def inventory(path: Path) -> tuple[str | None, bool, int]:
    digest = None
    valid = True
    lines = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        lines += 1
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            valid = False
            continue
        if not isinstance(item, dict):
            valid = False
        elif digest is None and item.get("inventory_digest"):
            digest = item["inventory_digest"]
    return digest, valid and lines > 0, lines


def run_one(binary: Path, profile: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="m204-s10-calibration-", dir=ROOT) as directory:
        diagnostics = Path(directory) / "diagnostics.jsonl"
        stdout = Path(directory) / "stdout.log"
        stderr = Path(directory) / "stderr.log"
        argv = [
            str(binary),
            "--root",
            str(CORPUS),
            "--garant-root",
            str(GARANT),
            "--profile",
            "contour",
            "--jobs",
            "1",
            "--acceptance-contract",
            str(CONTRACT),
            "--source-revision",
            "m204-s10-c4-calibration-2026-09-12",
            "--out",
            str(diagnostics),
            "--limit",
            str(LIMIT),
        ]
        started_at = utc_now()
        monotonic_start = time.monotonic()
        terminal: dict[str, Any]
        with stdout.open("x", encoding="utf-8") as out, stderr.open("x", encoding="utf-8") as err:
            try:
                proc = subprocess.Popen(
                    argv, cwd=ROOT, stdout=out, stderr=err, start_new_session=True
                )
                try:
                    code = proc.wait(timeout=600)
                    terminal = {
                        "outcome": "complete" if code == 0 else "nonzero",
                        "exit_code": code,
                        "timeout": False,
                    }
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
                    terminal = {"outcome": "timeout", "exit_code": None, "timeout": True}
            except OSError as exc:
                terminal = {
                    "outcome": "launch_error",
                    "exit_code": None,
                    "timeout": False,
                    "error": str(exc),
                }
        duration_ms = int((time.monotonic() - monotonic_start) * 1000)
        digest, valid, lines = inventory(diagnostics) if diagnostics.is_file() else (None, False, 0)
        observed = lines
        return {
            "profile": profile,
            "binary": {"path": rel(binary), "sha256": sha256(binary)},
            "argv": argv,
            "argv_sha256": "sha256:"
            + hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest(),
            "started_at": started_at,
            "finished_at": utc_now(),
            "duration_ms": duration_ms,
            "extrapolated_full_corpus_ms": (duration_ms * EXPECTED) // LIMIT,
            "limit": LIMIT,
            "jobs": 1,
            "observed_jsonl_lines": observed,
            "inventory_digest": digest,
            "jsonl_valid": valid,
            "terminal": terminal,
            "stdout_sha256": sha256(stdout),
            "stderr_sha256": sha256(stderr),
            "operational_acceptance": "non-pass",
            "non_claims": [
                "bounded limit-1000 calibration is not a full-corpus attempt",
                "extrapolation is diagnostic and is not measured duration",
                "sample receipt does not establish operational acceptance",
                "debug timing is not a release performance claim",
            ],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if args.verify:
        verify_frozen_manifest()
        if not args.out.is_file():
            raise SystemExit(f"calibration output missing: {args.out}")
        payload = json.loads(args.out.read_text(encoding="utf-8"))
        if payload.get("schema") != "m204-s10-c4-calibration/v1":
            raise SystemExit("calibration schema mismatch")
        samples = payload.get("samples")
        if not isinstance(samples, list) or len(samples) != 2:
            raise SystemExit("expected release and debug samples")
        for sample in samples:
            if sample.get("jobs") != 1 or sample.get("limit") != LIMIT:
                raise SystemExit("calibration binding mismatch")
            if sample.get("operational_acceptance") != "non-pass":
                raise SystemExit("calibration must never claim operational pass")
            if sample.get("duration_ms", 0) < 0 or sample.get("extrapolated_full_corpus_ms", 0) < 0:
                raise SystemExit("invalid calibration duration")
        print("M204_S10_T01_CALIBRATION_OK")
        return 0
    if not args.write:
        parser.error("--write or --verify is required")
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite immutable output: {args.out}")
    binaries = [
        ("release", ROOT / "target/release/npa-contour-diagnostics"),
        ("debug", ROOT / "target/debug/npa-contour-diagnostics"),
    ]
    for _, binary in binaries:
        if not binary.is_file():
            raise SystemExit(f"missing binary: {binary}")
    samples = [run_one(binary, profile) for profile, binary in binaries]
    payload = {
        "schema": "m204-s10-c4-calibration/v1",
        "created_at": utc_now(),
        "calibration_contract": {
            "root": rel(CORPUS),
            "garant_root": rel(GARANT),
            "consultant_xml_count": EXPECTED,
            "limit": LIMIT,
            "jobs": 1,
            "profile": "contour",
            "duration_floor_ms": FLOOR_MS,
            "clock": "time.monotonic",
            "sample_is_operational_pass": False,
        },
        "toolchain": toolchain(),
        "parser_revision": parser_revision(),
        "build_inputs": {
            "contract": {"path": rel(CONTRACT), "sha256": sha256(CONTRACT)},
            "parser_source": {"path": rel(PARSER), "sha256": sha256(PARSER)},
        },
        "samples": samples,
        "selection": {
            "release_admissible": samples[0]["extrapolated_full_corpus_ms"] >= FLOOR_MS,
            "debug_admissible": samples[1]["extrapolated_full_corpus_ms"] >= FLOOR_MS,
            "recommended_profile": "release"
            if samples[0]["extrapolated_full_corpus_ms"] >= FLOOR_MS
            else ("debug" if samples[1]["extrapolated_full_corpus_ms"] >= FLOOR_MS else None),
            "recommended_jobs": 1,
            "reason": "choose release when bounded extrapolation reaches the floor; otherwise debug only as an explicit non-performance operational contour",
        },
        "claims": {
            "calibration_status": "bounded-diagnostic",
            "operational_acceptance": "non-pass",
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    write_frozen_manifest()
    print(
        json.dumps(
            {
                "output": rel(args.out),
                "samples": [
                    (s["profile"], s["duration_ms"], s["extrapolated_full_corpus_ms"])
                    for s in samples
                ],
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
