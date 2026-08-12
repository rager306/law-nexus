"""Root-confined filesystem adapters for Review Case ports.

Outer I/O only. Pure domain/application/ports remain free of pathlib and codec
imports. Packet bytes always round-trip through the Pydantic codec adapter.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from law_nexus_harness.review_case.adapters.pydantic_codec import (
    ReviewCaseCodecError,
    dump_packet,
    load_packet,
)
from law_nexus_harness.review_case.domain import ReviewPacket
from law_nexus_harness.review_case.ports import ReviewCasePortError

_PACKET_ID_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_ALLOWED_PACKETS_ROOT = "prd/architecture/review-cases/packets"
_FORBIDDEN_PREFIXES = (
    ".gsd/",
    ".agents/",
    "old_project/",
    "python_archive/",
    "prd/archive/",
)
_FORBIDDEN_EXACT = frozenset(
    {
        ".gsd",
        ".agents",
        "old_project",
        "python_archive",
        "prd/archive",
    }
)


def _port_error(*, code: str, operation: str, message: str) -> ReviewCasePortError:
    return ReviewCasePortError(code=code, operation=operation, message=message)


def _validate_repo_relative_path(path: str, *, operation: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise _port_error(
            code="invalid_path",
            operation=operation,
            message="path must be non-empty repository-relative POSIX",
        )
    if (
        "\\" in path
        or ":" in path
        or any(character.isspace() for character in path)
        or path.startswith("/")
        or path.startswith("~")
    ):
        raise _port_error(
            code="invalid_path",
            operation=operation,
            message="path must be repository-relative POSIX without absolute prefix",
        )
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise _port_error(
            code="invalid_path",
            operation=operation,
            message="path must not contain empty, '.', or '..' segments",
        )
    lowered = path.lower()
    if lowered in _FORBIDDEN_EXACT or any(
        lowered == prefix.rstrip("/") or lowered.startswith(prefix)
        for prefix in _FORBIDDEN_PREFIXES
    ):
        raise _port_error(
            code="invalid_path",
            operation=operation,
            message="path targets a local-only or historical surface",
        )
    return path


def _resolve_under_root(root: Path, repo_relative_path: str, *, operation: str) -> Path:
    """Resolve a repo-relative path without following any symlink component."""

    relative = _validate_repo_relative_path(repo_relative_path, operation=operation)
    current = root
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise _port_error(
                code="symlink_rejected",
                operation=operation,
                message="symlinks are rejected for review-case filesystem access",
            )
        # Keep confinement even for not-yet-created paths by normalizing lexically
        # under the already-resolved root.
        try:
            current.relative_to(root)
        except ValueError as error:
            raise _port_error(
                code="path_escape",
                operation=operation,
                message="resolved path escapes repository root",
            ) from error
    return current


class FilesystemReviewSourceReader:
    """Read immutable review source bytes under a repository root."""

    def __init__(self, repository_root: Path | str) -> None:
        root = Path(repository_root).resolve(strict=True)
        if not root.is_dir():
            raise _port_error(
                code="invalid_root",
                operation="__init__",
                message="repository root must be an existing directory",
            )
        self._root = root

    @property
    def repository_root(self) -> Path:
        return self._root

    def read_bytes(self, repo_relative_path: str) -> bytes:
        operation = "read_bytes"
        target = _resolve_under_root(self._root, repo_relative_path, operation=operation)
        if not target.exists():
            raise _port_error(
                code="source_not_found",
                operation=operation,
                message="source path is missing",
            )
        if not target.is_file():
            raise _port_error(
                code="source_not_file",
                operation=operation,
                message="source path is not a regular file",
            )
        try:
            return target.read_bytes()
        except OSError as error:
            raise _port_error(
                code="source_read_failed",
                operation=operation,
                message="failed to read source bytes",
            ) from error


class FilesystemReviewPacketStore:
    """Persist versioned review packets as atomic JSON files under a root."""

    def __init__(
        self,
        repository_root: Path | str,
        *,
        packets_dir: str = "prd/architecture/review-cases/packets",
    ) -> None:
        root = Path(repository_root).resolve(strict=True)
        if not root.is_dir():
            raise _port_error(
                code="invalid_root",
                operation="__init__",
                message="repository root must be an existing directory",
            )
        self._root = root
        relative = _validate_repo_relative_path(packets_dir, operation="__init__")
        if relative != _ALLOWED_PACKETS_ROOT and not relative.startswith(
            f"{_ALLOWED_PACKETS_ROOT}/"
        ):
            raise _port_error(
                code="invalid_store_path",
                operation="__init__",
                message="packet store must stay under the dedicated non-authoritative packets root",
            )
        self._packets_dir_rel = relative
        self._packets_dir = _resolve_under_root(root, relative, operation="__init__")
        # Directory may not exist yet; create only on first successful add.

    @property
    def repository_root(self) -> Path:
        return self._root

    @property
    def packets_dir(self) -> Path:
        return self._packets_dir

    def _packet_path(self, packet_id: str, *, operation: str) -> Path:
        if _PACKET_ID_SAFE.fullmatch(packet_id) is None:
            raise _port_error(
                code="invalid_packet_id",
                operation=operation,
                message="packet_id is not a safe filesystem identifier",
            )
        return self._packets_dir / f"{packet_id}.json"

    def _ensure_packets_dir(self, *, operation: str) -> None:
        try:
            self._packets_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise _port_error(
                code="store_unavailable",
                operation=operation,
                message="failed to create packet store directory",
            ) from error
        if self._packets_dir.is_symlink():
            raise _port_error(
                code="symlink_rejected",
                operation=operation,
                message="packet store directory must not be a symlink",
            )
        if not self._packets_dir.is_dir():
            raise _port_error(
                code="store_unavailable",
                operation=operation,
                message="packet store path is not a directory",
            )

    def add(self, packet: ReviewPacket) -> None:
        operation = "add"
        if not isinstance(packet, ReviewPacket):
            raise _port_error(
                code="invalid_packet",
                operation=operation,
                message="store accepts pure ReviewPacket values only",
            )
        target = self._packet_path(packet.packet_id, operation=operation)
        self._ensure_packets_dir(operation=operation)
        if target.exists() or target.is_symlink():
            raise _port_error(
                code="duplicate_packet",
                operation=operation,
                message="packet already exists",
            )
        try:
            payload = dump_packet(packet)
        except ReviewCaseCodecError as error:
            raise _port_error(
                code=error.code,
                operation=operation,
                message=error.message,
            ) from error

        # Unique temp name avoids leftover-temp collisions and concurrent writers.
        # Publish via os.link so an existing final path fails closed instead of
        # being overwritten by os.replace.
        tmp_path = (
            self._packets_dir / f".{packet.packet_id}.{os.getpid()}.{os.urandom(4).hex()}.json.tmp"
        )
        try:
            with open(tmp_path, "xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(tmp_path, target)
            tmp_path.unlink()
        except FileExistsError as error:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            raise _port_error(
                code="duplicate_packet",
                operation=operation,
                message="packet path already exists during atomic write",
            ) from error
        except OSError as error:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            raise _port_error(
                code="store_write_failed",
                operation=operation,
                message="failed to write packet bytes atomically",
            ) from error

    def get(self, packet_id: str) -> ReviewPacket:
        operation = "get"
        target = self._packet_path(packet_id, operation=operation)
        if target.is_symlink():
            raise _port_error(
                code="symlink_rejected",
                operation=operation,
                message="symlinks are rejected for review-case filesystem access",
            )
        if not target.exists():
            raise _port_error(
                code="packet_not_found",
                operation=operation,
                message="packet is missing",
            )
        if not target.is_file():
            raise _port_error(
                code="packet_not_file",
                operation=operation,
                message="packet path is not a regular file",
            )
        try:
            data = target.read_bytes()
        except OSError as error:
            raise _port_error(
                code="store_read_failed",
                operation=operation,
                message="failed to read packet bytes",
            ) from error
        try:
            return load_packet(data)
        except ReviewCaseCodecError as error:
            raise _port_error(
                code="corrupt_packet",
                operation=operation,
                message=error.message,
            ) from error

    def list_all(self) -> tuple[ReviewPacket, ...]:
        operation = "list_all"
        if not self._packets_dir.exists():
            return ()
        if self._packets_dir.is_symlink():
            raise _port_error(
                code="symlink_rejected",
                operation=operation,
                message="packet store directory must not be a symlink",
            )
        if not self._packets_dir.is_dir():
            raise _port_error(
                code="store_unavailable",
                operation=operation,
                message="packet store path is not a directory",
            )
        try:
            names = sorted(
                path.name
                for path in self._packets_dir.iterdir()
                if path.is_file()
                and not path.is_symlink()
                and path.name.endswith(".json")
                and not path.name.startswith(".")
            )
        except OSError as error:
            raise _port_error(
                code="store_list_failed",
                operation=operation,
                message="failed to list packet store",
            ) from error

        packets: list[ReviewPacket] = []
        for name in names:
            packet_id = name[: -len(".json")]
            packets.append(self.get(packet_id))
        return tuple(packets)
