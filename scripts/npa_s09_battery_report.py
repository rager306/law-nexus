#!/usr/bin/env python3
"""Validate the governor JSON report for the S09 evidence battery."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_report(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        # Keep the harness tolerant of a short preamble, but never of a
        # malformed report: use the last complete JSON object only.
        decoder = json.JSONDecoder()
        candidates: list[dict[str, Any]] = []
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                candidate, end = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and not text[index + end :].strip():
                candidates.append(candidate)
        if not candidates:
            raise ValueError(f"no JSON governor report in {path}")
        value = candidates[-1]
    if not isinstance(value, dict):
        raise ValueError("governor report is not an object")
    return value


def find_checks(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if value.get("check_id") == "npa-promotion-control":
            found.append(value)
        for child in value.values():
            found.extend(find_checks(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(find_checks(child))
    return found


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: npa_s09_battery_report.py GOVERNOR_JSON", file=sys.stderr)
        return 2
    try:
        report = load_report(Path(sys.argv[1]))
        checks = find_checks(report)
        if len(checks) != 1:
            raise ValueError(f"expected one npa-promotion-control check, found {len(checks)}")
        check = checks[0]
        status = str(check.get("status", check.get("result", "unknown"))).lower()
        print(f"npa-promotion-control={status}")
        if status != "pass":
            return 1
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"npa_s09_battery_report: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
