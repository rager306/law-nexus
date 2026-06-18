#!/usr/bin/env python3
"""Generate the M065 S02 git-lex release-install manifest.

This is the manifest-continuation of M051/S09 §T04 "source-build manifest".
It records the installed-binary identity (sha256/size/mode/mtime) and the
builder/toolchain record (rustc version, OS, canonical install command, rc,
duration) for the Stage 2 release install performed in S02/T01.

It is a deterministic inspection surface (stdlib only, dataclass Diagnostic
style matching ``verify-m065-s01-install-contract.py``). It does NOT run
``git lex``, does NOT initialize ``.lex``, does NOT build, and does NOT mutate
the main law-nexus checkout. It re-reads the read-only vendor checkout to
confirm provenance and inspects the two installed release binaries.

Builder record (install_rc, duration_ms, rustc/cargo version, command) comes
from the build-record file written by the build wrapper, because those values
cannot be recomputed from inspected state. Everything else (provenance hashes,
git HEAD, binary identity) is recomputed from the filesystem.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VENDOR_ROOT = Path("/root/vendor-source/git-lex")
DEFAULT_CARGO_BIN = Path.home() / ".cargo" / "bin"
DEFAULT_OUTPUT = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s02" / "install-manifest.json"
DEFAULT_BUILD_RECORD = Path("/tmp/m065-s02-t01-build-record.txt")

# Source-provenance trust anchors reused from S01 D089 / M051-S09 / M051-S10 /
# M052-S06 / M054-S01 D077. Recomputed from the vendor checkout to confirm
# byte-for-byte equality (provenance reuse, not re-derivation).
EXPECTED_SOURCE_COMMIT = "eaa4b24d144a78a8b8e4969404d74cf22267df1f"
EXPECTED_CARGO_TOML_SHA256 = "2746659bd6a0441f2873fb59b4cc69434a0ac28b0d1ee76b9c15a5022d67a7a6"
EXPECTED_CARGO_LOCK_SHA256 = "3fbb6976b85c003fa50f6918f0aaa844665fd2d721dc2a6d7d5526fbbce793d7"
SOURCE_REMOTE = "https://github.com/repolex-ai/git-lex"
PROVENANCE_REUSED_FROM = [
    "M051-S09",
    "M051-S10",
    "M052-S06",
    "M054-S01 D077",
    "S01 D089",
]

CANONICAL_COMMAND = "cargo install --path . --locked"
BINARIES = ("git-lex", "git-lex-serve")

SCHEMA_VERSION = "m065-s02-install-manifest/v1"

DIAGNOSTIC_IDS = (
    "vendor_source_missing",
    "provenance_drift",
    "build_record_missing",
    "build_record_parse_error",
    "install_failed",
    "binary_missing",
    "binary_not_executable",
)


@dataclass(frozen=True)
class Diagnostic:
    diagnostic_id: str
    path: str
    line: int
    message: str
    text: str


def _diagnostic(diagnostic_id: str, path: Path | str, line_no: int, message: str, text: str = "") -> Diagnostic:
    try:
        rel = str(Path(path).relative_to(ROOT))
    except (ValueError, TypeError):
        rel = str(path)
    return Diagnostic(
        diagnostic_id=diagnostic_id,
        path=rel,
        line=line_no,
        message=message,
        text=text.strip(),
    )


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(vendor_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(vendor_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip()


def check_vendor_provenance(vendor_root: Path) -> tuple[dict[str, str | None], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    actual: dict[str, str | None] = {}
    if not vendor_root.exists():
        diagnostics.append(_diagnostic("vendor_source_missing", vendor_root, 0, f"vendor source checkout is missing: {vendor_root}"))
        return actual, diagnostics

    actual["source_commit"] = _git_head(vendor_root)
    actual["cargo_toml_sha256"] = _sha256(vendor_root / "Cargo.toml")
    actual["cargo_lock_sha256"] = _sha256(vendor_root / "Cargo.lock")

    expected = {
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "cargo_toml_sha256": EXPECTED_CARGO_TOML_SHA256,
        "cargo_lock_sha256": EXPECTED_CARGO_LOCK_SHA256,
    }
    for field, want in expected.items():
        got = actual.get(field)
        if got is None:
            diagnostics.append(_diagnostic("provenance_drift", vendor_root, 0, f"could not recompute {field} from {vendor_root}"))
        elif got != want:
            diagnostics.append(_diagnostic("provenance_drift", vendor_root, 0, f"{field} drift: expected {want} but vendor source recomputes to {got}"))
    return actual, diagnostics


def parse_build_record(record_path: Path) -> tuple[dict[str, str], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    if not record_path.exists():
        diagnostics.append(_diagnostic("build_record_missing", record_path, 0, f"build record file is missing: {record_path}"))
        return {}, diagnostics
    raw = record_path.read_text(encoding="utf-8")
    record: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            record[key.strip()] = value.strip()
    required = ("START_MS", "END_MS", "DURATION_MS", "INSTALL_RC", "BUILD_DIR", "COMMAND", "RUSTC_VERSION", "CARGO_VERSION")
    for key in required:
        if key not in record:
            diagnostics.append(_diagnostic("build_record_parse_error", record_path, 0, f"build record is missing required field: {key}"))
    return record, diagnostics


def check_install_rc(record: dict[str, str], record_path: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    rc = record.get("INSTALL_RC")
    if rc is not None and str(rc) != "0":
        diagnostics.append(_diagnostic("install_failed", record_path, 0, f"canonical install did not exit 0: INSTALL_RC={rc} (BLOCKER per S01 §1)"))
    return diagnostics


def inspect_binary(name: str, cargo_bin: Path) -> tuple[dict[str, object], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    path = cargo_bin / name
    identity: dict[str, object] = {"name": name}
    if not path.exists():
        diagnostics.append(_diagnostic("binary_missing", path, 0, f"installed binary is missing: {path}"))
        identity["path"] = str(path)
        return identity, diagnostics
    stat = path.stat()
    sha = _sha256(path)
    identity.update(
        {
            "path": str(path),
            "sha256": sha,
            "size_bytes": stat.st_size,
            "mode": oct(stat.st_mode & 0o777),
            "mtime": int(stat.st_mtime),
            "profile": "release",
        }
    )
    if not os.access(path, os.X_OK):
        diagnostics.append(_diagnostic("binary_not_executable", path, 0, f"installed binary is not executable: {path}"))
    return identity, diagnostics


def build_manifest(
    record: dict[str, str],
    provenance: dict[str, str | None],
    binaries: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp": _iso_utc(),
        "purpose": (
            "Stage 2 release-install manifest for git-lex + git-lex-serve. "
            "Records installed-binary identity and builder/toolchain record as "
            "the manifest-continuation of M051/S09 §T04 source-build manifest. "
            "This is an install-proof, not an install-claim."
        ),
        "source": {
            "source_remote": SOURCE_REMOTE,
            "source_commit": provenance.get("source_commit"),
            "cargo_toml_sha256": provenance.get("cargo_toml_sha256"),
            "cargo_lock_sha256": provenance.get("cargo_lock_sha256"),
            "provenance_reused_from": list(PROVENANCE_REUSED_FROM),
        },
        "install": {
            "command": CANONICAL_COMMAND,
            "profile": "release",
            "build_dir": record.get("BUILD_DIR", str(DEFAULT_VENDOR_ROOT)),
            "rustc_version": record.get("RUSTC_VERSION"),
            "cargo_version": record.get("CARGO_VERSION"),
            "os": platform.platform(),
            "duration_ms": _to_int(record.get("DURATION_MS")),
            "install_rc": _to_int(record.get("INSTALL_RC")),
        },
        "binaries": binaries,
        "version_gap": {
            "note": (
                "git-lex exposes no --version flag; binary identity (sha256) is the "
                "version surrogate (reused M051-S09 + M064-S03 convention). "
                "version_flag_rc is filled in T02's install-proof."
            ),
            "version_flag_rc": None,
        },
        "manifest_continuation_of": "M051-S09 §T04 source-build manifest",
    }


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _iso_utc() -> str:
    import datetime as _dt

    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.path
    if diagnostic.line:
        location = f"{location}:{diagnostic.line}"
    suffix = f"\n  {diagnostic.text}" if diagnostic.text else ""
    return f"{diagnostic.diagnostic_id}: {location}: {diagnostic.message}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the M065 S02 git-lex release-install manifest.")
    parser.add_argument("--vendor-root", type=Path, default=DEFAULT_VENDOR_ROOT)
    parser.add_argument("--cargo-bin", type=Path, default=DEFAULT_CARGO_BIN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-record", type=Path, default=DEFAULT_BUILD_RECORD)
    parser.add_argument("--check", action="store_true", help="inspect and report diagnostics without writing the manifest")
    args = parser.parse_args(argv)

    diagnostics: list[Diagnostic] = []

    provenance, prov_diags = check_vendor_provenance(args.vendor_root)
    diagnostics.extend(prov_diags)

    record, rec_diags = parse_build_record(args.build_record)
    diagnostics.extend(rec_diags)

    diagnostics.extend(check_install_rc(record, args.build_record))

    binaries: dict[str, dict[str, object]] = {}
    for name in BINARIES:
        identity, bin_diags = inspect_binary(name, args.cargo_bin)
        binaries[name] = identity
        diagnostics.extend(bin_diags)

    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1

    if args.check:
        print(f"M065 S02 install-manifest check passed: binaries={len(binaries)} diagnostics=0 (no write)")
        return 0

    manifest = build_manifest(record, provenance, binaries)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"M065 S02 install-manifest written: {args.output} binaries={len(binaries)} diagnostics=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
