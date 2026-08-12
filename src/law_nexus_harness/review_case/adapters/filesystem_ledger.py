"""Append-only filesystem event ledger for Review Case packets.

Outer adapter only. Stores one immutable envelope file per sequence under the
dedicated non-authoritative packets root. Does not rewrite history, create GSD
work, or promote authority.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from law_nexus_harness.review_case.adapters.filesystem import (
    _ALLOWED_PACKETS_ROOT,
    _resolve_under_root,
    _validate_repo_relative_path,
)
from law_nexus_harness.review_case.adapters.pydantic_codec import (
    ReviewCaseCodecError,
    dump_envelope,
    dump_event,
    envelope_body_bytes,
    load_envelope,
)
from law_nexus_harness.review_case.domain import EventLedgerEnvelope, ReviewEvent
from law_nexus_harness.review_case.ports import ReviewCasePortError

_PACKET_ID_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_EVENT_ID_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_ENVELOPE_NAME = re.compile(r"^(\d{6})-([A-Za-z0-9][A-Za-z0-9._-]{0,127})\.json$")
_GIT_REV = re.compile(r"^[a-f0-9]{40}$")


def _port_error(*, code: str, operation: str, message: str) -> ReviewCasePortError:
    return ReviewCasePortError(code=code, operation=operation, message=message)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FilesystemEventLedger:
    """Root-confined append-only envelope ledger under packets/<id>/events/."""

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
        relative = _validate_repo_relative_path(packets_dir, operation="__init__")
        if relative != _ALLOWED_PACKETS_ROOT and not relative.startswith(
            f"{_ALLOWED_PACKETS_ROOT}/"
        ):
            raise _port_error(
                code="invalid_store_path",
                operation="__init__",
                message="event ledger must stay under the dedicated non-authoritative packets root",
            )
        self._root = root
        self._packets_dir_rel = relative
        self._packets_dir = _resolve_under_root(root, relative, operation="__init__")

    @property
    def repository_root(self) -> Path:
        return self._root

    @property
    def packets_dir(self) -> Path:
        return self._packets_dir

    def _require_packet_id(self, packet_id: str, *, operation: str) -> str:
        if _PACKET_ID_SAFE.fullmatch(packet_id) is None:
            raise _port_error(
                code="invalid_packet_id",
                operation=operation,
                message="packet_id is not a safe filesystem identifier",
            )
        return packet_id

    def _events_dir(self, packet_id: str, *, operation: str) -> Path:
        self._require_packet_id(packet_id, operation=operation)
        rel = f"{self._packets_dir_rel}/{packet_id}/events"
        return _resolve_under_root(self._root, rel, operation=operation)

    def _ensure_events_dir(self, packet_id: str, *, operation: str) -> Path:
        target = self._events_dir(packet_id, operation=operation)
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise _port_error(
                code="ledger_unavailable",
                operation=operation,
                message="failed to create event ledger directory",
            ) from error
        if target.is_symlink():
            raise _port_error(
                code="symlink_rejected",
                operation=operation,
                message="event ledger directory must not be a symlink",
            )
        if not target.is_dir():
            raise _port_error(
                code="ledger_unavailable",
                operation=operation,
                message="event ledger path is not a directory",
            )
        return target

    def _envelope_path(
        self,
        packet_id: str,
        sequence: int,
        event_id: str,
        *,
        operation: str,
    ) -> Path:
        if _EVENT_ID_SAFE.fullmatch(event_id) is None:
            raise _port_error(
                code="invalid_event_id",
                operation=operation,
                message="event_id is not a safe filesystem identifier",
            )
        events_dir = self._events_dir(packet_id, operation=operation)
        return events_dir / f"{sequence:06d}-{event_id}.json"

    def _list_envelope_paths(self, packet_id: str, *, operation: str) -> list[Path]:
        events_dir = self._events_dir(packet_id, operation=operation)
        if not events_dir.exists():
            return []
        if events_dir.is_symlink():
            raise _port_error(
                code="symlink_rejected",
                operation=operation,
                message="event ledger directory must not be a symlink",
            )
        if not events_dir.is_dir():
            raise _port_error(
                code="ledger_unavailable",
                operation=operation,
                message="event ledger path is not a directory",
            )
        try:
            names = sorted(
                path.name
                for path in events_dir.iterdir()
                if path.is_file()
                and not path.is_symlink()
                and path.name.endswith(".json")
                and not path.name.startswith(".")
            )
        except OSError as error:
            raise _port_error(
                code="ledger_list_failed",
                operation=operation,
                message="failed to list event ledger",
            ) from error
        paths: list[Path] = []
        for name in names:
            match = _ENVELOPE_NAME.fullmatch(name)
            if match is None:
                raise _port_error(
                    code="corrupt_ledger",
                    operation=operation,
                    message="ledger contains an unexpected file name",
                )
            paths.append(events_dir / name)
        return paths

    def _load_path(self, path: Path, *, operation: str) -> EventLedgerEnvelope:
        if path.is_symlink():
            raise _port_error(
                code="symlink_rejected",
                operation=operation,
                message="symlinks are rejected for review-case filesystem access",
            )
        if not path.exists():
            raise _port_error(
                code="envelope_not_found",
                operation=operation,
                message="envelope is missing",
            )
        if not path.is_file():
            raise _port_error(
                code="envelope_not_file",
                operation=operation,
                message="envelope path is not a regular file",
            )
        try:
            data = path.read_bytes()
        except OSError as error:
            raise _port_error(
                code="ledger_read_failed",
                operation=operation,
                message="failed to read envelope bytes",
            ) from error
        try:
            envelope = load_envelope(data)
        except ReviewCaseCodecError as error:
            raise _port_error(
                code="corrupt_envelope",
                operation=operation,
                message=error.message,
            ) from error
        # Integrity: durable bytes must match declared envelope hash over body.
        expected_body = envelope_body_bytes(envelope)
        if _sha256_hex(expected_body) != envelope.envelope_sha256:
            raise _port_error(
                code="envelope_hash_mismatch",
                operation=operation,
                message="envelope_sha256 does not match canonical body",
            )
        expected_event = dump_event(envelope.event)
        if _sha256_hex(expected_event) != envelope.event_sha256:
            raise _port_error(
                code="event_hash_mismatch",
                operation=operation,
                message="event_sha256 does not match canonical event bytes",
            )
        return envelope

    def list_envelopes(self, packet_id: str) -> tuple[EventLedgerEnvelope, ...]:
        operation = "list_envelopes"
        paths = self._list_envelope_paths(packet_id, operation=operation)
        envelopes: list[EventLedgerEnvelope] = []
        previous_hash: str | None = None
        for index, path in enumerate(paths, start=1):
            envelope = self._load_path(path, operation=operation)
            if envelope.packet_id != packet_id:
                raise _port_error(
                    code="packet_id_mismatch",
                    operation=operation,
                    message="envelope packet_id does not match ledger path",
                )
            if envelope.sequence != index:
                raise _port_error(
                    code="ledger_gap_or_fork",
                    operation=operation,
                    message="envelope sequence is not contiguous from 1",
                )
            if envelope.previous_envelope_sha256 != previous_hash:
                raise _port_error(
                    code="ledger_chain_break",
                    operation=operation,
                    message="previous_envelope_sha256 chain is broken",
                )
            match = _ENVELOPE_NAME.fullmatch(path.name)
            assert match is not None
            if (
                int(match.group(1)) != envelope.sequence
                or match.group(2) != envelope.event.event_id
            ):
                raise _port_error(
                    code="envelope_name_mismatch",
                    operation=operation,
                    message="envelope filename does not match sequence/event_id",
                )
            if any(item.event.event_id == envelope.event.event_id for item in envelopes):
                raise _port_error(
                    code="duplicate_event_id",
                    operation=operation,
                    message="ledger contains duplicate event_id",
                )
            envelopes.append(envelope)
            previous_hash = envelope.envelope_sha256
        return tuple(envelopes)

    def append(
        self,
        packet_id: str,
        event: ReviewEvent,
        *,
        source_revision: str,
    ) -> EventLedgerEnvelope:
        operation = "append"
        if not isinstance(event, ReviewEvent):
            raise _port_error(
                code="invalid_event",
                operation=operation,
                message="ledger accepts pure ReviewEvent values only",
            )
        if not isinstance(source_revision, str) or _GIT_REV.fullmatch(source_revision) is None:
            raise _port_error(
                code="invalid_source_revision",
                operation=operation,
                message="source_revision must be a 40-char lowercase git sha",
            )
        events_dir = self._ensure_events_dir(packet_id, operation=operation)
        existing = self.list_envelopes(packet_id)
        if any(item.event.event_id == event.event_id for item in existing):
            raise _port_error(
                code="duplicate_event_id",
                operation=operation,
                message="event_id already exists in ledger",
            )
        sequence = len(existing) + 1
        previous = existing[-1].envelope_sha256 if existing else None
        try:
            event_bytes = dump_event(event)
        except ReviewCaseCodecError as error:
            raise _port_error(
                code=error.code,
                operation=operation,
                message=error.message,
            ) from error
        event_sha256 = _sha256_hex(event_bytes)
        provisional = EventLedgerEnvelope(
            packet_id=packet_id,
            sequence=sequence,
            previous_envelope_sha256=previous,
            event=event,
            event_sha256=event_sha256,
            source_revision=source_revision,
            envelope_sha256="0" * 64,
        )
        body = envelope_body_bytes(provisional)
        envelope = EventLedgerEnvelope(
            packet_id=packet_id,
            sequence=sequence,
            previous_envelope_sha256=previous,
            event=event,
            event_sha256=event_sha256,
            source_revision=source_revision,
            envelope_sha256=_sha256_hex(body),
        )
        try:
            payload = dump_envelope(envelope)
        except ReviewCaseCodecError as error:
            raise _port_error(
                code=error.code,
                operation=operation,
                message=error.message,
            ) from error
        target = self._envelope_path(
            packet_id,
            sequence,
            event.event_id,
            operation=operation,
        )
        if target.exists() or target.is_symlink():
            raise _port_error(
                code="ledger_fork",
                operation=operation,
                message="target envelope path already exists",
            )
        # Detect concurrent append to next sequence under a different event_id.
        for path in events_dir.iterdir() if events_dir.exists() else ():
            match = _ENVELOPE_NAME.fullmatch(path.name)
            if match is not None and int(match.group(1)) == sequence:
                raise _port_error(
                    code="ledger_fork",
                    operation=operation,
                    message="sequence already claimed by another envelope",
                )
        tmp_path = (
            events_dir
            / f".{sequence:06d}-{event.event_id}.{os.getpid()}.{os.urandom(4).hex()}.json.tmp"
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
                code="ledger_fork",
                operation=operation,
                message="envelope path already exists during atomic write",
            ) from error
        except OSError as error:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            raise _port_error(
                code="ledger_write_failed",
                operation=operation,
                message="failed to write envelope bytes atomically",
            ) from error
        # Re-list to fail closed if a concurrent writer forked the chain.
        listed = self.list_envelopes(packet_id)
        if listed[-1] != envelope:
            raise _port_error(
                code="ledger_fork",
                operation=operation,
                message="append race detected after publish",
            )
        return envelope
