"""Outer Review Case adapters.

Vendor codecs and filesystem adapters live here. Pure domain/application/ports
remain free of pydantic/pathlib/CLI/Governor/GSD imports.
"""

from law_nexus_harness.review_case.adapters.filesystem import (
    FilesystemReviewPacketStore,
    FilesystemReviewSourceReader,
)
from law_nexus_harness.review_case.adapters.filesystem_ledger import FilesystemEventLedger
from law_nexus_harness.review_case.adapters.hashlib_adapter import HashlibContentHasher
from law_nexus_harness.review_case.adapters.pydantic_codec import (
    ReviewCaseCodecError,
    dump_envelope,
    dump_event,
    dump_packet,
    envelope_body_bytes,
    generated_wire_schema,
    load_envelope,
    load_event,
    load_packet,
)

__all__ = [
    "FilesystemEventLedger",
    "FilesystemReviewPacketStore",
    "FilesystemReviewSourceReader",
    "HashlibContentHasher",
    "ReviewCaseCodecError",
    "dump_envelope",
    "dump_event",
    "dump_packet",
    "envelope_body_bytes",
    "generated_wire_schema",
    "load_envelope",
    "load_event",
    "load_packet",
]
