#!/usr/bin/env python3
"""Compose/check the M204 S09 validate deadlock evidence without opening gsd.db."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTE = ROOT / "prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json"
TRIGGERS = ROOT / "prd/migration/rust-evidence/m204-s09-trigger-sql.json"
SCHEMA = "law-nexus/gsd-validate-deadlock/v1"
ABORT = "technical verdict requires the current criterion and matching settled attempt"


def runtime_snapshot() -> dict:
    script = r"""
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const root = process.env.GSD_HOME
  ? path.join(process.env.GSD_HOME, "agent", "extensions", "gsd")
  : path.join(os.homedir(), ".gsd", "agent", "extensions", "gsd");
function trigger(text, name) {
  const re = new RegExp("CREATE\\s+TRIGGER(?:\\s+IF\\s+NOT\\s+EXISTS)?\\s+" + name + "[\\s\\S]*?END(?:;)?", "m");
  const m = text.match(re);
  if (!m) throw new Error(`missing runtime trigger ${name}`);
  return m[0];
}
const files = {
  v34: "db-lifecycle-foundation-schema.js",
  v42: "db-milestone-validation-schema.js",
};
const names = {
  v34: "trg_workflow_attempt_result_requires_settlement",
  v42: "trg_workflow_technical_verdict_scope",
};
const out = {};
for (const [version, file] of Object.entries(files)) {
  const absolute = path.join(root, file);
  const text = fs.readFileSync(absolute, "utf8");
  out[version] = {
    trigger_name: names[version],
    source_file: path.relative(process.env.GSD_HOME || path.join(os.homedir(), ".gsd"), absolute),
    create_trigger_sql: trigger(text, names[version]),
  };
}
process.stdout.write(JSON.stringify({source_root: root, snapshots: out}));
"""
    env = os.environ.copy()
    completed = subprocess.run(
        ["node", "--input-type=commonjs", "-e", script],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def compose() -> None:
    runtime = runtime_snapshot()
    note = {
        "schema": SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S09",
        "task": "T01",
        "abort_message": ABORT,
        "activity_census": {
            "minimum_observed_rows": 31,
            "basis": "tracked S01 upstream-debt inventory",
        },
        "validation_projection_present": False,
        "statuses": {"engine_fix": "not_fixed", "upstream_issue": "not_filed"},
        "law_nexus_fixable": False,
        "trigger_name": "trg_workflow_technical_verdict_scope",
        "writer_order": [
            "milestone.validate attempt must settle",
            "technical verdict must reference the current criterion and matching settled attempt",
            "validation projection may be emitted only after the verdict is durably accepted",
        ],
        "loop_mechanism": "validate-milestone retries the same verdict write, while the v42 trigger rejects it before a validation projection can be persisted",
        "c4_remains": {"operational_acceptance": "non-pass", "disposition": "unchanged"},
        "evidence_boundary": "This note records an engine defect; it does not patch SQLite, call gsd_validate_milestone, or promote C4.",
    }
    trigger_doc = {
        "schema": "law-nexus/gsd-trigger-sql-snapshot/v1",
        "milestone": "M204-w2ktfw",
        "slice": "S09",
        "read_only": True,
        "source_files_relative_to_GSD_HOME": True,
        "runtime_source_root": runtime["source_root"],
        "snapshots": runtime["snapshots"],
    }
    NOTE.parent.mkdir(parents=True, exist_ok=True)
    NOTE.write_text(json.dumps(note, indent=2, ensure_ascii=False) + "\n")
    TRIGGERS.write_text(json.dumps(trigger_doc, indent=2, ensure_ascii=False) + "\n")


def check() -> None:
    note = json.loads(NOTE.read_text())
    triggers = json.loads(TRIGGERS.read_text())
    assert note["schema"] == SCHEMA
    assert note["abort_message"] == ABORT
    assert note["activity_census"]["minimum_observed_rows"] >= 31
    assert note["validation_projection_present"] is False
    assert note["statuses"] == {"engine_fix": "not_fixed", "upstream_issue": "not_filed"}
    assert note["law_nexus_fixable"] is False
    assert note["trigger_name"] == "trg_workflow_technical_verdict_scope"
    assert note["c4_remains"]["operational_acceptance"] == "non-pass"
    assert triggers["source_files_relative_to_GSD_HOME"] is True
    for version in ("v34", "v42"):
        snap = triggers["snapshots"][version]
        assert snap["create_trigger_sql"].startswith("CREATE TRIGGER")
        assert "END" in snap["create_trigger_sql"]
    assert (
        "trg_workflow_technical_verdict_scope" in triggers["snapshots"]["v42"]["create_trigger_sql"]
    )
    print("S09 T01 OK: deadlock note and runtime trigger snapshots are valid")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        compose()
    check()


if __name__ == "__main__":
    main()
