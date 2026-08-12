"""Outer SHA-256 adapter for Review Case ports."""

from __future__ import annotations

import hashlib

from law_nexus_harness.review_case.ports import ReviewCasePortError


class HashlibContentHasher:
    """stdlib hashlib-backed ContentHasher."""

    def sha256(self, data: bytes) -> str:
        if not isinstance(data, (bytes, bytearray)):
            raise ReviewCasePortError(
                code="invalid_hash_input",
                operation="sha256",
                message="hasher accepts bytes only",
            )
        try:
            return hashlib.sha256(bytes(data)).hexdigest()
        except Exception as error:  # pragma: no cover - defensive
            raise ReviewCasePortError(
                code="hash_failed",
                operation="sha256",
                message="failed to compute sha256",
            ) from error
