#!/usr/bin/env python3
"""Repository script shim for ``python -m law_nexus_harness``."""

from law_nexus_harness.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
