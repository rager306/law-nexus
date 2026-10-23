#!/usr/bin/env python3
"""Manage the tracked template and the shared private Allspark settings.

init: create private settings once; leave an existing profile untouched.
apply: merge the tracked template into the existing private settings.
export-model: copy ONLY defaultProvider/defaultModel/defaultThinkingLevel from
the private settings into the tracked template. Never opens auth.json.
"""

from __future__ import annotations

import argparse
import json
import os
import runpy
import tempfile
from pathlib import Path

MODEL_KEYS = ("defaultProvider", "defaultModel", "defaultThinkingLevel")
THINKING = {"off", "minimal", "low", "medium", "high", "xhigh", "max"}


def read_object(path: Path, *, absent_ok: bool = False) -> dict:
    if absent_ok and not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"Cannot read settings object {path}: {type(error).__name__}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"Settings must be a JSON object: {path}")
    return value


def merge(base: dict, incoming: dict) -> dict:
    result = dict(base)
    for key, value in incoming.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def write_locked(path: Path, transform, *, private: bool) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise SystemExit(
            f"Settings are locked: {lock}. Retry when the other writer finishes."
        ) from error
    temp_name = None
    try:
        value = transform()
        if value is None:
            return False
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix="settings-", suffix=".tmp", delete=False
        ) as output:
            temp_name = output.name
            json.dump(value, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temp_name, 0o600 if private else 0o644)
        os.replace(temp_name, path)
        temp_name = None
        return True
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        lock.rmdir()


def main() -> None:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "apply", "export-model"))
    action = parser.parse_args().action
    script_root = Path(__file__).resolve().parents[2]
    helper = runpy.run_path(str(script_root / "scripts/ai/stack-env.py"))
    root = helper["canonical_root"](script_root)
    template_path = root / ".ai/allspark/settings.json"
    private_path = root / ".ai/local/allspark-home/.prime/agent/settings.json"
    if action in {"init", "apply"}:
        template = read_object(template_path)

        def update_private():
            if action == "init" and private_path.exists():
                return None
            return merge(read_object(private_path, absent_ok=True), template)

        changed = write_locked(private_path, update_private, private=True)
        print(
            "Private settings initialized/applied."
            if changed
            else "Existing private settings kept."
        )
        return

    private_settings = read_object(private_path)
    for key in ("defaultProvider", "defaultModel"):
        if not isinstance(private_settings.get(key), str) or not private_settings[key].strip():
            raise SystemExit("Select a model with /model in Allspark before export-model.")
    level = private_settings.get("defaultThinkingLevel")
    if level is not None and level not in THINKING:
        raise SystemExit("Private defaultThinkingLevel is not a pinned Allspark thinking level.")

    def update_template():
        template = read_object(template_path)
        for key in MODEL_KEYS:
            template.pop(key, None)
            if private_settings.get(key) is not None:
                template[key] = private_settings[key]
        return template

    write_locked(template_path, update_template, private=False)
    print("Exported only defaultProvider, defaultModel, and optional defaultThinkingLevel.")


if __name__ == "__main__":
    main()
