"""law_nexus.adapters — infrastructure adapters (D046 onion outer ring).

Adapters implement the :class:`law_nexus.ports` protocols against real
infrastructure. They are the only layer allowed to perform I/O (filesystem,
network, DB, model calls). Domain and ports stay infrastructure-free.
"""

from __future__ import annotations
