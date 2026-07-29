"""Source hierarchy use case.

[bounded] M076 S04 application seam. This use case delegates deterministic
paragraph-to-hierarchy generation to an injected port implementation. It keeps
application code free of Consultant-specific parsing, filesystem I/O, CLI
freshness checks, and report rendering.
"""

from __future__ import annotations

from law_nexus.ports.source_hierarchy import (
    SourceHierarchyBuilder,
    SourceHierarchyRequest,
    SourceHierarchyResult,
)


class SourceHierarchyUseCase:
    """Build source hierarchy records through an injected builder port."""

    def __init__(self, builder: SourceHierarchyBuilder) -> None:
        self._builder = builder

    def build_records(self, request: SourceHierarchyRequest) -> SourceHierarchyResult:
        """Return hierarchy parser records and diagnostics for ``request``."""

        return self._builder.build_records(request)
