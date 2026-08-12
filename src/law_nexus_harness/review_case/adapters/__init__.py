"""Outer Review Case adapters.

Vendor codecs and filesystem adapters live here. Pure domain/application/ports
remain free of pydantic/pathlib/CLI/Governor/GSD imports.
"""

from law_nexus_harness.review_case.adapters.pydantic_codec import (
    ReviewCaseCodecError,
    dump_packet,
    generated_wire_schema,
    load_packet,
)

__all__ = [
    "ReviewCaseCodecError",
    "dump_packet",
    "generated_wire_schema",
    "load_packet",
]
