#!/usr/bin/env python3
r"""Versioned, Pi-free source snapshot verifier (MIGRATION.md section 4.3).

Successor to ``scripts/m204_s08_source_revision.mjs``, which imported the
frozen GSD-Pi engine (``verification-source-integrity.js`` and
``preferences.js``) at runtime. This tool is repository-control tooling only
(ADR-0007): no product logic, no Pi/GSD_HOME dependency, standard library
only.

Snapshot document
-----------------
The tool emits (and ``--check`` consumes) a JSON document:

    {
      "schema": "law-nexus-source-snapshot/v2",
      "algorithm": "sha256+sorted-paths/v1",
      "head": "<git commit sha or null>",
      "generated_at": "<iso8601 utc timestamp>",
      "files": [<file entries>],
      "aggregate": "<sha256 hex digest>"
    }

Each file entry records the repo-relative POSIX ``path``, a ``status`` of
``tracked-clean``, ``tracked-dirty`` (worktree differs from the git index),
``untracked``, or ``deleted`` (in the index, absent from the worktree;
``sha256`` and ``bytes`` are null), the ``sha256`` over raw bytes, and the
byte length ``bytes``. Symlinks hash the link target string obtained via
readlink (the link is never followed) and additionally carry ``"type":
"symlink"``. ``head`` is ``git rev-parse HEAD`` or null when the repository
has no commits.

Enumeration population
----------------------
``git ls-files --cached --others --exclude-standard`` run from the repository
root: every tracked file plus every untracked-but-not-ignored file. The
``--out``/``--check`` target itself, when it resolves inside the repository,
is excluded from enumeration in that same run, so writing a snapshot into the
repository and re-checking it are idempotent.

Aggregate — stability contract
------------------------------
Files are sorted by the UTF-8 byte order of their path. For each file, in
that order, emit exactly one line

    f"{path}\0{status}\0{sha256 or '-'}\0{bytes or '-'}\n"

where ``sha256``/``bytes`` are the recorded hex digest / decimal byte length
and ``-`` stands in for null values (deleted entries). ``aggregate`` is the
sha256 hex digest of the concatenation of those lines, encoded as UTF-8.
This rule is the compatibility contract between snapshot producers; changing
it requires a new schema and algorithm identifier.

Exit codes
----------
0 success (write or matching check); 1 operational error (git failure,
unreadable or malformed stored snapshot, unwritable output); 2 usage error
(argparse); 3 ``--check`` found that the stored snapshot differs from a
freshly computed one, with a bounded changed/added/removed summary on stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_ID = "law-nexus-source-snapshot/v2"
ALGORITHM_ID = "sha256+sorted-paths/v1"
DIFF_LISTING_CAP = 50
DEFAULT_REPO = Path(__file__).resolve().parents[1]

STATUS_TRACKED_CLEAN = "tracked-clean"
STATUS_TRACKED_DIRTY = "tracked-dirty"
STATUS_UNTRACKED = "untracked"
STATUS_DELETED = "deleted"

EXIT_OK = 0
EXIT_OPERATIONAL = 1
EXIT_MISMATCH = 3


class SnapshotError(Exception):
    """Operational failure (exit 1): bad repository state or unusable snapshot I/O."""


@dataclass(frozen=True)
class FileEntry:
    """One enumerated repository path."""

    path: str
    status: str
    sha256: str | None
    size: int | None
    kind: str | None

    def canonical_line(self) -> str:
        digest = self.sha256 if self.sha256 is not None else "-"
        size = str(self.size) if self.size is not None else "-"
        return f"{self.path}\0{self.status}\0{digest}\0{size}\n"

    def signature(self) -> tuple[str, str | None, int | None, str | None]:
        return (self.status, self.sha256, self.size, self.kind)

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "path": self.path,
            "status": self.status,
            "sha256": self.sha256,
            "bytes": self.size,
        }
        if self.kind is not None:
            payload["type"] = self.kind
        return payload


@dataclass(frozen=True)
class Snapshot:
    """A computed or stored snapshot; ``generated_at`` is added at serialization."""

    head: str | None
    files: list[FileEntry]
    aggregate: str

    def to_json(self) -> dict[str, object]:
        return {
            "schema": SCHEMA_ID,
            "algorithm": ALGORITHM_ID,
            "head": self.head,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "files": [entry.to_json() for entry in self.files],
            "aggregate": self.aggregate,
        }


@dataclass(frozen=True)
class SnapshotDiff:
    """Differences between a stored and a freshly computed snapshot."""

    head_changed: bool
    changed: list[str]
    added: list[str]
    removed: list[str]

    def is_empty(self) -> bool:
        return not (self.head_changed or self.changed or self.added or self.removed)


def run_git(repo: Path, args: list[str]) -> bytes:
    """Run git inside ``repo`` and return raw stdout; raise SnapshotError on failure."""
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise SnapshotError(f"git {' '.join(args)} failed with exit {proc.returncode}: {detail}")
    return proc.stdout


def git_path_list(repo: Path, args: list[str]) -> list[str]:
    """Run a git command that emits NUL-terminated paths and decode them."""
    output = run_git(repo, [*args, "-z"])
    return [os.fsdecode(item) for item in output.split(b"\0") if item]


def git_head(repo: Path) -> str | None:
    """Return ``git rev-parse HEAD`` or None when the repository has no commits."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, check=False
    )
    if proc.returncode != 0:
        return None
    head = proc.stdout.decode("utf-8", "replace").strip()
    return head or None


def hash_regular_file(path: Path) -> tuple[str, int]:
    """Stream-hash raw file bytes; return the hex digest and byte length."""
    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            hasher.update(chunk)
            size += len(chunk)
    return hasher.hexdigest(), size


def classify_path(repo_root: Path, path: str, tracked: bool, dirty: set[str]) -> FileEntry:
    """Build the file entry for one enumerated path."""
    absolute = repo_root / path
    if not os.path.lexists(absolute):
        if not tracked:
            raise SnapshotError(f"enumerated path vanished before hashing: {path}")
        return FileEntry(path, STATUS_DELETED, None, None, None)
    if not tracked:
        status = STATUS_UNTRACKED
    elif path in dirty:
        status = STATUS_TRACKED_DIRTY
    else:
        status = STATUS_TRACKED_CLEAN
    if absolute.is_symlink():
        target = os.fsencode(os.readlink(absolute))
        return FileEntry(path, status, hashlib.sha256(target).hexdigest(), len(target), "symlink")
    if absolute.is_file():
        digest, size = hash_regular_file(absolute)
        return FileEntry(path, status, digest, size, None)
    raise SnapshotError(f"enumerated path is neither a regular file nor a symlink: {path}")


def compute_snapshot(repo_root: Path, excluded: frozenset[str]) -> Snapshot:
    """Enumerate the repository and build the snapshot data."""
    tracked = set(git_path_list(repo_root, ["ls-files", "--cached"]))
    untracked = set(git_path_list(repo_root, ["ls-files", "--others", "--exclude-standard"]))
    dirty = set(git_path_list(repo_root, ["diff", "--name-only"]))

    population = sorted((tracked | untracked) - excluded, key=os.fsencode)
    entries = [classify_path(repo_root, path, path in tracked, dirty) for path in population]

    hasher = hashlib.sha256()
    for entry in entries:
        hasher.update(entry.canonical_line().encode("utf-8", "surrogateescape"))
    return Snapshot(head=git_head(repo_root), files=entries, aggregate=hasher.hexdigest())


def resolve_repo_root(requested: Path) -> Path:
    """Resolve the git work tree root for the requested ``--repo`` directory.

    The requested path must be the work tree root itself: a plain directory
    nested inside a repository is not an addressable snapshot scope, because
    ``git ls-files`` always enumerates the whole work tree. Accepting a nested
    path would silently snapshot a different population than the caller named.
    """
    top = run_git(requested, ["rev-parse", "--show-toplevel"]).decode("utf-8", "replace").strip()
    if not top:
        raise SnapshotError(f"git did not report a work tree root for {requested}")
    resolved = Path(top).resolve()
    if requested.resolve() != resolved:
        raise SnapshotError(
            f"--repo must be the git work tree root ({resolved}), not a nested path ({requested})"
        )
    return resolved


def repo_relative_exclusion(repo_root: Path, target: Path | None) -> frozenset[str]:
    """Map an --out/--check target that lives inside the repository to its exclusion path."""
    if target is None:
        return frozenset()
    resolved = target.resolve()
    if resolved == repo_root or not resolved.is_relative_to(repo_root):
        return frozenset()
    return frozenset((resolved.relative_to(repo_root).as_posix(),))


def parse_stored_entry(item: object, index: int) -> FileEntry:
    """Validate one ``files[i]`` object from a stored snapshot document."""
    if not isinstance(item, dict):
        raise SnapshotError(f"stored files[{index}] is not a JSON object")
    path = item.get("path")
    status = item.get("status")
    sha256 = item.get("sha256")
    size = item.get("bytes")
    kind = item.get("type")
    if not isinstance(path, str) or not isinstance(status, str):
        raise SnapshotError(f"stored files[{index}] has a non-string path or status")
    if sha256 is not None and not isinstance(sha256, str):
        raise SnapshotError(f"stored files[{index}] has a non-string sha256")
    if size is not None and not isinstance(size, int):
        raise SnapshotError(f"stored files[{index}] has a non-integer bytes value")
    if kind is not None and not isinstance(kind, str):
        raise SnapshotError(f"stored files[{index}] has a non-string type value")
    return FileEntry(path, status, sha256, size, kind)


def load_stored_snapshot(path: Path) -> Snapshot:
    """Load and validate a stored snapshot document."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as err:
        raise SnapshotError(f"cannot read stored snapshot {path}: {err}") from err
    except json.JSONDecodeError as err:
        raise SnapshotError(f"stored snapshot {path} is not valid JSON: {err}") from err
    if not isinstance(raw, dict):
        raise SnapshotError(f"stored snapshot {path} is not a JSON object")
    if raw.get("schema") != SCHEMA_ID:
        raise SnapshotError(
            f"stored snapshot schema is {raw.get('schema')!r}, expected {SCHEMA_ID!r}"
        )
    if raw.get("algorithm") != ALGORITHM_ID:
        raise SnapshotError(
            f"stored snapshot algorithm is {raw.get('algorithm')!r}, expected {ALGORITHM_ID!r}"
        )
    head = raw.get("head")
    files_raw = raw.get("files")
    aggregate = raw.get("aggregate")
    if head is not None and not isinstance(head, str):
        raise SnapshotError(f"stored snapshot {path} has a non-string head")
    if not isinstance(files_raw, list):
        raise SnapshotError(f"stored snapshot {path} has no files list")
    if not isinstance(aggregate, str):
        raise SnapshotError(f"stored snapshot {path} has no aggregate digest")
    files = [parse_stored_entry(item, index) for index, item in enumerate(files_raw)]
    return Snapshot(head=head, files=files, aggregate=aggregate)


def diff_snapshots(stored: Snapshot, fresh: Snapshot) -> SnapshotDiff:
    """Compare snapshots per file signature (status, sha256, bytes, type) and head."""
    stored_by_path = {entry.path: entry.signature() for entry in stored.files}
    fresh_by_path = {entry.path: entry.signature() for entry in fresh.files}
    changed = [
        path
        for path, signature in fresh_by_path.items()
        if path in stored_by_path and stored_by_path[path] != signature
    ]
    added = [path for path in fresh_by_path if path not in stored_by_path]
    removed = [path for path in stored_by_path if path not in fresh_by_path]
    return SnapshotDiff(
        head_changed=stored.head != fresh.head,
        changed=sorted(changed, key=os.fsencode),
        added=sorted(added, key=os.fsencode),
        removed=sorted(removed, key=os.fsencode),
    )


def format_head(head: str | None) -> str:
    return head if head is not None else "null"


def print_diff_summary(diff: SnapshotDiff, stored: Snapshot, fresh: Snapshot) -> None:
    """Print the bounded changed/added/removed summary for a mismatching check."""
    bits: list[str] = []
    if diff.changed:
        bits.append(f"{len(diff.changed)} changed")
    if diff.added:
        bits.append(f"{len(diff.added)} added")
    if diff.removed:
        bits.append(f"{len(diff.removed)} removed")
    if diff.head_changed:
        bits.append("head changed")
    print(f"source snapshot mismatch: {', '.join(bits)}")
    listed: dict[str, list[str]] = {}
    budget = DIFF_LISTING_CAP
    for category, paths in (
        ("changed", diff.changed),
        ("added", diff.added),
        ("removed", diff.removed),
    ):
        listed[category] = paths[:budget]
        budget -= len(listed[category])
    for category, paths in listed.items():
        if paths:
            print(f"{category}: {', '.join(paths)}")
    if diff.head_changed:
        print(f"head: {format_head(stored.head)} -> {format_head(fresh.head)}")
    unlisted = len(diff.changed) + len(diff.added) + len(diff.removed) - (DIFF_LISTING_CAP - budget)
    if unlisted > 0:
        print(f"diff listing capped at {DIFF_LISTING_CAP} paths; {unlisted} more not listed")


def render_document(snapshot: Snapshot) -> bytes:
    """Serialize the snapshot to its JSON document as UTF-8 bytes."""
    return (json.dumps(snapshot.to_json(), indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8", "surrogateescape"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify-source-snapshot-v2",
        description=(
            "Compute or verify a versioned source snapshot of a git repository "
            f"({SCHEMA_ID}). Exit codes: 0 ok, 1 operational error, 2 usage error, "
            "3 stored snapshot differs."
        ),
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=DEFAULT_REPO,
        help="git repository root (default: the repository this script lives in)",
    )
    target = parser.add_mutually_exclusive_group()
    target.add_argument(
        "--out", type=Path, help="write the snapshot JSON document to this path (default: stdout)"
    )
    target.add_argument(
        "--check",
        type=Path,
        help="compare the stored snapshot at this path against a freshly computed one",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo.resolve())
    excluded = repo_relative_exclusion(repo_root, args.out) | repo_relative_exclusion(
        repo_root, args.check
    )
    fresh = compute_snapshot(repo_root, excluded)

    if args.check is not None:
        stored = load_stored_snapshot(args.check)
        diff = diff_snapshots(stored, fresh)
        if diff.is_empty():
            if stored.aggregate != fresh.aggregate:
                raise SnapshotError(
                    "stored aggregate does not match the recomputed snapshot despite identical files"
                )
            print(f"source snapshot matches (aggregate {fresh.aggregate})")
            return EXIT_OK
        print_diff_summary(diff, stored, fresh)
        return EXIT_MISMATCH

    document = render_document(fresh)
    if args.out is None:
        sys.stdout.buffer.write(document)
        sys.stdout.buffer.flush()
        return EXIT_OK
    try:
        args.out.write_bytes(document)
    except OSError as err:
        raise SnapshotError(f"cannot write snapshot to {args.out}: {err}") from err
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except SnapshotError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_OPERATIONAL


if __name__ == "__main__":
    raise SystemExit(main())
