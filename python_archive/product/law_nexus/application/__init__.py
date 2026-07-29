"""law_nexus.application — use cases (D046 onion application layer).

Pure orchestration: use cases depend on :mod:`law_nexus.ports` protocols and
:mod:`law_nexus.domain` models, never on concrete adapters or infrastructure.
Adapters are wired in at the composition root (:mod:`law_nexus.composition`).
"""

from __future__ import annotations
