#!/usr/bin/env python3
"""M223/S02 full-run feasibility decision (evidence-only, no corpus run).

This helper turns the two S02 measurements into one recorded decision:

* the authoritative corpus inventory manifest (T01) — per-file ``source.sha256``
  and byte counts for all 43,785 pinned XML entries;
* the cleaned-path resource probe (T02) — export *and* read-back wall time, peak
  RSS, output bytes and the deterministic stratified sample definition.

It projects the *full-corpus* wall time (export + read-back + a stated
reconciliation/uncertainty overhead) and cleaned-layer volume by a single,
explicit method (decile-stratified body extrapolation plus the measured largest
tail, §8.5), compares them against **stop thresholds** and disk, and picks one
verdict from a closed vocabulary.  It runs no corpus pass, edits no Rust code,
and persists only this evidence JSON.  R1000 is untouched and stays
active/unclosed.

Projection method (deterministic, reproducible from the two artifacts alone):

* files are ranked by ``(bytes, relative_path)`` and split into ten deciles with
  the same rule the probe's sampler uses;
* the largest ``tail_n`` files are *measured* in the probe (they are force-
  included by the sampler), so their export wall, read-back wall and output
  bytes are summed exactly — this is the tail contribution;
* every other corpus file (the body) is projected per decile as
  ``mean(measured value) * body_units`` (files for time, bytes for the layer);
  a decile with no body sample falls back to the global body mean and is flagged;
* the projected cleaned-layer volume is also cross-checked with the aggregate
  output/input ratio over the sample times total corpus bytes, and the
  conservative projection is the larger of the two;
* export and read-back are projected separately and summed; a **stated**
  reconciliation overhead (independent verification + receipts + hashing) and an
  uncertainty margin are then applied and reported as fractions, not as measured
  costs.

What this evidence does *not* claim (see ``non_claims``): the stop thresholds are
enforced by polling and are not hard caps of actual consumption; the measured RSS
tail is a sample, not a corpus upper bound; and the decision authorises a
*conditional attempt*, gated on a mandatory preflight that re-checks actual free
disk and available memory.  Only paths, counts and hashes reach the evidence —
never raw decoded text.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = "m223-s02-corpus-feasibility/v1"
VERSION = 2
MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"
PROBE_SCHEMA = "m223-s02-clean-path-probe/v1"

DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
DEFAULT_PROBE = ROOT / "prd/migration/rust-evidence/m223-s02-clean-path-probe.json"
DEFAULT_OUT = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-feasibility.json"
CONTRACT = ROOT / "prd/architecture/intermediate-source-acceptance-contract.md"

# Closed decision vocabulary (§9).  ``bounded-partial`` is never auto-selected:
# §8.1 requires every manifest entry to reach a terminal outcome, so a partial
# corpus sweep is not a full-run feasibility verdict.
DECISIONS = ("full-persist", "full-stream-discard", "bounded-partial", "requires-disk-expansion")

DECILE_COUNT = 10
TAIL_STRATUM = "tail_largest"

# Runtime stop thresholds.  These are *stop* thresholds enforced by polling, not
# promised upper bounds of actual consumption: the run is killed when a polled
# value crosses the threshold, so observed consumption may overshoot by up to one
# poll interval.  The preflight must confirm the projected run fits before the
# attempt starts.
WALL_STOP_THRESHOLD_S = 4 * 3600
RSS_STOP_THRESHOLD_KB = 6 * 1024 * 1024
SINGLE_ARTIFACT_STOP_THRESHOLD_BYTES = 2 * 1024**3

# Stated, deliberately conservative overheads on top of the measured export +
# read-back projection.  They are declared as fractions, not derived from a
# measurement, and are reported separately so the raw projection stays visible.
RECONCILIATION_OVERHEAD_FRACTION = 0.25  # independent verification + receipts + hashing
UNCERTAINTY_FRACTION = 0.25  # sampling / machine variance margin

PERSIST_HEADROOM_FRACTION = 0.20
MIN_FREE_DISK_SAFETY_BYTES = 1 * 1024**3

EXIT_MISSING_INPUT = 2
EXIT_BAD_INPUT = 3
EXIT_OUT_UNWRITABLE = 4

# Complex classes the probe could not measure without a new XML parser; recorded
# so the projection's blind spots are explicit, not silent.
UNMEASURED_CLASSES = ("per-document nesting depth", "per-document table count/density")


class FeasibilityError(Exception):
    """Typed input failure: the decision is not emitted on bad inputs."""


# --------------------------------------------------------------- loading #


def _load_probe_module() -> Any:
    """Load the sibling T02 probe module by path (no package assumption)."""
    path = Path(__file__).with_name("m223_s02_probe.py")
    spec = importlib.util.spec_from_file_location("m223_s02_probe", path)
    if spec is None or spec.loader is None:
        raise FeasibilityError(f"cannot load probe module at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _rel(path: Path) -> str:
    """Repo-relative when possible, else the absolute form (hermetic fixtures)."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_manifest(path: Path) -> tuple[dict[str, Any], list[Any]]:
    """Reuse the T02 parser so deciles and manifests stay consistent."""
    probe = _load_probe_module()
    try:
        header, entries = probe.parse_manifest(path)
    except ValueError as exc:
        raise FeasibilityError(f"malformed manifest {path}: {exc}") from exc
    if header.get("schema") != MANIFEST_SCHEMA:
        raise FeasibilityError(f"unexpected manifest schema: {header.get('schema')!r}")
    if not entries:
        raise FeasibilityError("manifest has no entries")
    return header, entries


def read_probe(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FeasibilityError(f"unreadable probe {path}: {exc}") from exc
    if payload.get("schema") != PROBE_SCHEMA:
        raise FeasibilityError(f"unexpected probe schema: {payload.get('schema')!r}")
    if payload.get("run", {}).get("status") != "complete":
        raise FeasibilityError("probe run is not complete; refusing to project")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise FeasibilityError("probe has no records")
    required = ("run", "manifest", "sample", "aggregates")
    missing = [key for key in required if key not in payload]
    if missing:
        raise FeasibilityError(f"probe missing required sections: {missing}")
    return payload


# ------------------------------------------------------------- projection #


def _decile_members(entries: list[Any]) -> list[list[Any]]:
    by_size = sorted(entries, key=lambda entry: (entry.bytes, entry.relative_path))
    total = len(by_size)
    if total == 0:
        raise FeasibilityError("cannot stratify an empty corpus")
    deciles: list[list[Any]] = [[] for _ in range(DECILE_COUNT)]
    for index, entry in enumerate(by_size):
        deciles[min(DECILE_COUNT - 1, index * DECILE_COUNT // total)].append(entry)
    return deciles


def _export_metric(record: dict[str, Any], key: str) -> float | None:
    export = record.get("export")
    if not isinstance(export, dict):
        return None
    value = export.get(key)
    return float(value) if value is not None else None


def _readback_wall_s(record: dict[str, Any]) -> float | None:
    readback = record.get("readback")
    if not isinstance(readback, dict):
        return None
    value = readback.get("wall_s")
    return float(value) if value is not None else None


def _ratio(record: dict[str, Any]) -> float | None:
    output = record.get("output_bytes")
    input_bytes = record.get("input_bytes")
    if output is None or not input_bytes:
        return None
    return float(output) / float(input_bytes)


def _output_bytes(record: dict[str, Any]) -> float | None:
    value = record.get("output_bytes")
    return float(value) if value is not None else None


def _stats(values: list[float]) -> dict[str, float | None]:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0, "min": None, "median": None, "p95": None, "max": None}

    def percentile(q: float) -> float:
        if len(ordered) == 1:
            return float(ordered[0])
        position = (len(ordered) - 1) * q
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = position - lower
        return float(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)

    return {
        "count": len(ordered),
        "min": float(ordered[0]),
        "median": percentile(0.5),
        "p95": percentile(0.95),
        "max": float(ordered[-1]),
    }


def _split(
    deciles: list[list[Any]],
    by_path: dict[str, dict[str, Any]],
    tail_paths: set[str],
    value_fn: Any,
    *,
    units: str,
    tail_fn: Any | None = None,
) -> dict[str, Any]:
    """Measured-tail + decile-stratified-body projection for one metric.

    ``value_fn`` is the per-record *model* value used to extrapolate the body
    (for the cleaned layer this is the dimensionless output/input ratio, matched
    against body bytes).  The measured tail is summed with ``tail_fn`` when it
    differs — for the layer the tail contribution is the actual ``output_bytes``,
    never a sum of ratios.  ``tail_fn`` defaults to ``value_fn``.
    """
    tail_value = tail_fn if tail_fn is not None else value_fn

    def weight(bucket: list[Any]) -> float:
        if units == "files":
            return float(len(bucket))
        return float(sum(entry.bytes for entry in bucket))

    body_records = [
        record for record in by_path.values() if record["relative_path"] not in tail_paths
    ]
    global_values = [value for record in body_records if (value := value_fn(record)) is not None]
    global_mean = statistics.fmean(global_values) if global_values else 0.0

    per_decile: list[dict[str, Any]] = []
    body_total = 0.0
    for index, bucket in enumerate(deciles):
        body = [entry for entry in bucket if entry.relative_path not in tail_paths]
        sampled = [by_path[entry.relative_path] for entry in body if entry.relative_path in by_path]
        values = [value for record in sampled if (value := value_fn(record)) is not None]
        fallback: dict[str, str] = {}
        if values:
            mean = statistics.fmean(values)
        else:
            mean = global_mean
            fallback["value"] = "global_body_mean"
        projected = mean * weight(body)
        body_total += projected
        per_decile.append(
            {
                "decile": index,
                "body_units": weight(body),
                "body_files": len(body),
                "sampled": len(sampled),
                "mean": round(mean, 6),
                "projected": round(projected, 6),
                "fallback": fallback,
            }
        )

    measured_tail = sorted(tail_paths & set(by_path))
    tail_total = sum(tail_value(by_path[path]) or 0.0 for path in measured_tail)
    return {
        "units": units,
        "tail_measured": round(float(tail_total), 6),
        "body_projected": round(float(body_total), 6),
        "total": round(float(tail_total + body_total), 6),
        "per_decile": per_decile,
    }


def compute_projections(
    header: dict[str, Any], entries: list[Any], probe_payload: dict[str, Any]
) -> dict[str, Any]:
    """Project full-corpus wall time (export+read-back), layer, RSS tail and disk."""
    records = probe_payload["records"]
    accepted = [record for record in records if record.get("outcome") == "accepted"]
    if not accepted:
        raise FeasibilityError("probe has no accepted records to project from")
    by_path = {record["relative_path"]: record for record in accepted}

    tail_paths = {
        record["relative_path"]
        for record in records
        if TAIL_STRATUM in (record.get("strata") or [])
    }
    tail_missing = sorted(tail_paths - set(by_path))

    deciles = _decile_members(entries)
    total_files = len(entries)
    total_bytes = sum(entry.bytes for entry in entries)

    export = _split(
        deciles, by_path, tail_paths, lambda record: _export_metric(record, "wall_s"), units="files"
    )
    readback = _split(deciles, by_path, tail_paths, _readback_wall_s, units="files")
    layer = _split(
        deciles,
        by_path,
        tail_paths,
        _ratio,
        units="bytes",
        tail_fn=_output_bytes,
    )

    combined_s = export["total"] + readback["total"]
    overhead_s = combined_s * RECONCILIATION_OVERHEAD_FRACTION
    subtotal_s = combined_s + overhead_s
    uncertainty_s = subtotal_s * UNCERTAINTY_FRACTION
    projected_total_s = subtotal_s + uncertainty_s

    accepted_input = sum(float(record.get("input_bytes") or 0) for record in accepted)
    accepted_output = sum(float(record.get("output_bytes") or 0) for record in accepted)
    aggregate_ratio = accepted_output / accepted_input if accepted_input else 0.0
    aggregate_layer_bytes = aggregate_ratio * total_bytes
    conservative_layer_bytes = max(layer["total"], aggregate_layer_bytes)

    ratio_stats = _stats([r for record in accepted if (r := _ratio(record))])
    worst_case_layer_bytes = float(ratio_stats["max"] or 0.0) * total_bytes

    rss_stats = _stats(
        [float(record["export"]["peak_rss_kb"]) for record in accepted if record.get("export")]
    )
    output_stats = _stats([float(record.get("output_bytes") or 0) for record in accepted])

    disk_before = probe_payload["run"].get("disk_before", {})
    free_disk_bytes = int(disk_before.get("free_bytes") or 0)
    total_disk_bytes = int(disk_before.get("total_bytes") or 0)
    if free_disk_bytes <= 0:
        raise FeasibilityError("probe does not record positive free disk")

    persist_safety_bytes = max(
        MIN_FREE_DISK_SAFETY_BYTES, int(conservative_layer_bytes * PERSIST_HEADROOM_FRACTION)
    )
    persist_required_bytes = conservative_layer_bytes + persist_safety_bytes

    return {
        "manifest_counts": header.get("counts"),
        "manifest_pins": header.get("pins"),
        "total_files": total_files,
        "total_bytes": total_bytes,
        "sample": {
            "seed": probe_payload.get("sample", {}).get("seed"),
            "count": len(records),
            "accepted": len(accepted),
            "tail_files": len(tail_paths),
            "tail_measured": len(tail_paths & set(by_path)),
            "tail_missing": tail_missing,
        },
        "wall_s": {
            "method": (
                "export and read-back projected separately as [exactly measured largest-tail "
                "sum + decile-stratified body (mean measured per decile times body file count)], "
                "then summed and multiplied by the stated reconciliation overhead and "
                "uncertainty margins"
            ),
            "export": export,
            "readback": readback,
            "combined_s": round(combined_s, 6),
            "reconciliation_overhead_fraction": RECONCILIATION_OVERHEAD_FRACTION,
            "reconciliation_overhead_s": round(overhead_s, 6),
            "subtotal_s": round(subtotal_s, 6),
            "uncertainty_fraction": UNCERTAINTY_FRACTION,
            "uncertainty_s": round(uncertainty_s, 6),
            "projected_total_s": round(projected_total_s, 6),
            "projected_total_h": round(projected_total_s / 3600.0, 6),
            "stop_threshold_s": WALL_STOP_THRESHOLD_S,
        },
        "cleaned_layer_bytes": {
            "method": (
                "decile-stratified body projection (mean measured output/input ratio per "
                "decile times body bytes) plus the exactly measured largest-tail sum; "
                "cross-checked with aggregate ratio times total bytes; the conservative "
                "projection is the larger"
            ),
            "tail_measured_bytes": int(layer["tail_measured"]),
            "body_projected_bytes": int(layer["body_projected"]),
            "total_bytes": int(layer["total"]),
            "aggregate_ratio": round(aggregate_ratio, 6),
            "aggregate_ratio_bytes": int(aggregate_layer_bytes),
            "conservative_bytes": int(conservative_layer_bytes),
            "ratio": ratio_stats,
            "worst_case_bytes": int(worst_case_layer_bytes),
        },
        "peak_rss_kb": {
            "method": (
                "measured peak RSS over the sample; the largest tail is fully measured. This is "
                "a sample tail, not a corpus upper bound"
            ),
            **{key: value for key, value in rss_stats.items()},
            "stop_threshold_kb": RSS_STOP_THRESHOLD_KB,
        },
        "output_bytes": output_stats,
        "disk": {
            "free_bytes": free_disk_bytes,
            "total_bytes": total_disk_bytes,
            "conservative_layer_bytes": int(conservative_layer_bytes),
            "persist_safety_bytes": int(persist_safety_bytes),
            "persist_required_bytes": int(persist_required_bytes),
            "headroom_bytes": int(free_disk_bytes - conservative_layer_bytes),
            "single_artifact_measured_max_bytes": int(output_stats["max"] or 0),
            "single_artifact_stop_threshold_bytes": SINGLE_ARTIFACT_STOP_THRESHOLD_BYTES,
            "min_free_disk_safety_bytes": MIN_FREE_DISK_SAFETY_BYTES,
        },
    }


# ---------------------------------------------------------------- decision #


def stop_thresholds() -> dict[str, Any]:
    """Runtime stop thresholds, explicitly not promises about consumption."""
    return {
        "kind": "stop_threshold",
        "enforcement": "polled while the run is live; a crossing stops the run (SIGKILL)",
        "not_an_upper_bound": True,
        "overshoot_note": (
            "observed consumption may overshoot a stop threshold by up to one poll interval; "
            "the run is stopped, not capped in advance"
        ),
        "wall_s": WALL_STOP_THRESHOLD_S,
        "peak_rss_kb": RSS_STOP_THRESHOLD_KB,
        "single_artifact_bytes": SINGLE_ARTIFACT_STOP_THRESHOLD_BYTES,
    }


def preflight_requirements(projections: dict[str, Any]) -> list[dict[str, Any]]:
    """Mandatory checks the S03 run must pass before any attempt starts."""
    disk = projections["disk"]
    return [
        {
            "check": "free_disk_bytes >= single_artifact_stop_threshold_bytes + safety",
            "threshold_bytes": (
                disk["single_artifact_stop_threshold_bytes"] + disk["min_free_disk_safety_bytes"]
            ),
        },
        {
            "check": "available_memory_bytes >= peak_rss_stop_threshold_kb * 1024",
            "threshold_bytes": projections["peak_rss_kb"]["stop_threshold_kb"] * 1024,
        },
        {
            "check": "projected_total_wall_s < wall_stop_threshold_s",
            "threshold_s": WALL_STOP_THRESHOLD_S,
        },
        {
            "check": "conservative_layer_bytes < free_disk_bytes (required only for full-persist)",
            "threshold_bytes": disk["conservative_layer_bytes"],
        },
    ]


def decide(projections: dict[str, Any]) -> dict[str, Any]:
    """Pick one closed-vocabulary verdict with stop thresholds and a change condition."""
    projected_total_s = projections["wall_s"]["projected_total_s"]
    rss_max_kb = projections["peak_rss_kb"]["max"] or 0.0
    layer_bytes = projections["cleaned_layer_bytes"]["conservative_bytes"]
    disk = projections["disk"]
    free_bytes = disk["free_bytes"]
    persist_required_bytes = disk["persist_required_bytes"]

    persist_feasible = free_bytes >= persist_required_bytes
    fits_declared = (
        projected_total_s <= WALL_STOP_THRESHOLD_S
        and rss_max_kb <= RSS_STOP_THRESHOLD_KB
        and disk["single_artifact_measured_max_bytes"] <= free_bytes - MIN_FREE_DISK_SAFETY_BYTES
    )

    if persist_feasible:
        verdict = "full-persist"
        rationale = (
            "free disk covers the conservative projected cleaned layer plus the "
            "safety/headroom margin, so the full corpus run can persist the layer"
        )
    elif fits_declared:
        verdict = "full-stream-discard"
        rationale = (
            "the projected total wall (export + read-back + stated overhead) and the sampled "
            "RSS tail fit inside the stop thresholds and one artifact fits on disk, but the "
            "projected cleaned layer plus headroom exceeds free disk; the run must stream and "
            "discard each artifact, persisting per-file receipts only"
        )
    elif free_bytes < disk["single_artifact_measured_max_bytes"] + MIN_FREE_DISK_SAFETY_BYTES:
        verdict = "requires-disk-expansion"
        rationale = (
            "free disk cannot even hold one largest observed artifact plus the safety "
            "margin; the run needs disk expansion before any full pass"
        )
    else:
        verdict = "requires-disk-expansion"
        rationale = (
            "the projected run does not fit the declared stop thresholds at the current "
            "resources; disk expansion (or a lower declared threshold) is required"
        )

    return {
        "verdict": verdict,
        "vocabulary": list(DECISIONS),
        "decided_from": {
            "projected_total_wall_s": projected_total_s,
            "projected_export_wall_s": projections["wall_s"]["export"]["total"],
            "projected_readback_wall_s": projections["wall_s"]["readback"]["total"],
            "projected_layer_bytes": layer_bytes,
            "measured_peak_rss_kb": rss_max_kb,
            "free_disk_bytes": free_bytes,
            "persist_required_bytes": int(persist_required_bytes),
            "single_artifact_measured_max_bytes": disk["single_artifact_measured_max_bytes"],
        },
        "stop_thresholds": stop_thresholds(),
        "preflight_requirements": preflight_requirements(projections),
        "authorization": {
            "kind": "conditional_attempt_authorization",
            "scope": (
                "one attempt at a full pass over every manifest entry (§8.1); entries are "
                "processed until done or until a stop threshold halts the attempt"
            ),
            "granted_when": "all preflight_requirements pass at attempt start",
            "on_stop": (
                "a stop threshold halts the attempt; a halted or interrupted attempt is not a "
                "success, and a partial pass is never reported as full (§8.1). Resume re-checks "
                "the preflight, skips entries with current receipts, and re-attempts the rest"
            ),
            "partial_is_not_full": True,
        },
        "resume_semantics": {
            "bound_to": [
                "input: per-file source.sha256 + bytes (inventory manifest)",
                "code: source revision of the reader/admission pipeline actually executed",
                "rules: decoder/cleaner profile and contract version",
            ],
            "resume_requires": "all three hash families match the recorded receipts (§8.6)",
            "partial_run_label": (
                "not full; corpus statistics report accepted / refused / incomplete separately"
            ),
        },
        "condition_that_changes_decision": {
            "to": "full-persist",
            "requires_free_disk_bytes": int(persist_required_bytes),
            "statement": (
                f"If free disk at run time is >= {int(persist_required_bytes)} B "
                f"(conservative projected layer {int(layer_bytes)} B + safety/headroom "
                f"{int(disk['persist_safety_bytes'])} B), the run may persist the full cleaned "
                "layer and the decision changes to full-persist"
            ),
        },
        "rationale": rationale,
        "rejected": [
            {
                "verdict": "bounded-partial",
                "why": (
                    "rejected: §8.1 requires every manifest entry to reach a terminal "
                    "outcome; a partial sweep is silent descoping, not a feasibility verdict"
                ),
            }
        ],
    }


# ------------------------------------------------------------------ output #


def build_feasibility(manifest_path: Path, probe_path: Path) -> dict[str, Any]:
    """Pure builder: the evidence is a deterministic function of the two inputs."""
    header, entries = read_manifest(manifest_path)
    probe_payload = read_probe(probe_path)
    projections = compute_projections(header, entries, probe_payload)
    decision = decide(projections)

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "inputs": {
            "manifest": {
                "path": _rel(manifest_path),
                "sha256": sha256_file(manifest_path),
                "inventory_digest": header.get("inventory_digest"),
                "counts": header.get("counts"),
                "pins": header.get("pins"),
            },
            "probe": {
                "path": _rel(probe_path),
                "sha256": sha256_file(probe_path),
                "schema": probe_payload.get("schema"),
                "run_status": probe_payload.get("run", {}).get("status"),
                "seed": probe_payload.get("sample", {}).get("seed"),
                "sample_count": probe_payload.get("sample", {}).get("count"),
                "manifest_sha256": probe_payload.get("manifest", {}).get("sha256"),
                "inventory_digest": probe_payload.get("manifest", {}).get("inventory_digest"),
            },
        },
        "projections": projections,
        "decision": decision,
        "blind_spots": list(UNMEASURED_CLASSES),
        "evidence_pointers": [
            _rel(manifest_path),
            _rel(probe_path),
            str(CONTRACT.relative_to(ROOT)),
        ],
        "r1000_status": "active/unclosed",
        "non_claims": [
            "Not a corpus run: projections are conditional extrapolations from a bounded "
            "stratified sample (300 files), not measured full-corpus facts.",
            "Not semantic acceptance: resource feasibility only; integrity is not semantics.",
            "R1000 stays active/unclosed: this decision closes no requirement and no M223 "
            "slice closes R1000.",
            "Stop thresholds are polled enforcement points, not hard caps; observed consumption "
            "may overshoot by up to one poll interval, so the thresholds are not upper bounds of "
            "actual consumption.",
            "The sampled peak RSS is a tail of the sample, not a corpus upper bound.",
            "The reconciliation/uncertainty margins are stated fractions, not measured costs.",
            "The decision authorises a conditional attempt, not a guaranteed fit: the preflight "
            "must confirm actual free disk and available memory before the attempt starts.",
            "A halted or partial pass is not full coverage; partial results are never reported "
            "as full (§8.1).",
            "Per-document nesting depth and table count/density are not measured (no product "
            "surface without a new XML parse); density and size stand in for them.",
            "Disk, wall and RSS projections are point-in-time: a changed corpus, binary, "
            "machine or free disk changes the verdict.",
            "No raw decoded text in evidence: paths, counts and hashes only.",
        ],
    }


def write_evidence(payload: dict[str, Any], path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    os.replace(tmp, path)


# -------------------------------------------------------------------- cli #


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    for label, path in (("manifest", args.manifest), ("probe", args.probe)):
        if not path.is_file():
            print(f"{label} missing: {path}", file=sys.stderr)
            return EXIT_MISSING_INPUT
    try:
        payload = build_feasibility(args.manifest, args.probe)
    except FeasibilityError as exc:
        print(f"feasibility input error: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT

    decision = payload["decision"]
    projections = payload["projections"]
    print(
        "m223-s02-feasibility: "
        f"verdict={decision['verdict']} "
        f"projected_total={projections['wall_s']['projected_total_h']:.3f}h "
        f"(export={projections['wall_s']['export']['total']:.1f}s "
        f"readback={projections['wall_s']['readback']['total']:.1f}s) "
        f"layer={projections['cleaned_layer_bytes']['conservative_bytes']}B "
        f"free={projections['disk']['free_bytes']}B "
        f"persist_required={projections['disk']['persist_required_bytes']}B "
        f"peak_rss={projections['peak_rss_kb']['max']:.0f}KiB",
        file=sys.stderr,
    )
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        write_evidence(payload, args.out)
    except OSError as exc:
        print(f"cannot write evidence {args.out}: {exc}", file=sys.stderr)
        return EXIT_OUT_UNWRITABLE
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover - thin CLI guard
    raise SystemExit(main())
