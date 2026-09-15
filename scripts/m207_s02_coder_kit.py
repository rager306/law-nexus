#!/usr/bin/env python3
"""Deterministic two-pass coder kit builder and leak gate for M207 S02 (T02).

The coder kit is the **only** authorized way a coder receives a case
(``prd/annotation/m207-s02-coder-protocol.md`` section 6, D478).  This script
builds it as a *deterministic projection* of the frozen S01 case manifest -- the
kit is regenerated from frozen bytes, never from a previously emitted kit, so
poisoning a tracked kit cannot propagate into its regeneration.

Design invariants (each enforced, not merely documented):

* **Source-bound projection.**  Every kit case carries exactly ``case_id``,
  ``fragment_id``, ``fragment_path``, ``fragment_sha256``, ``byte_len``,
  ``span_offered_for_coding``, ``alternative_classes`` and
  ``abstention_available`` -- the closed case key set frozen in
  ``prd/annotation/m207-s02-schemas.json`` (``schemas.coder_kit``).  The frozen
  surface itself is sha256-pinned, so a byte of drift in the case manifest, the
  codebook, the S01 schemas, the S02 schemas or the M199 seed stops the gate
  (``FROZEN_SOURCE_DRIFT``).
* **No decoded text is duplicated.**  Decoded fragment text is never inlined
  (codebook section 1, D478): every case is probed *and* every kit string value
  is probed against the frozen fragment bytes, the four forbidden case keys are
  refused at any nesting depth, and the eight M199 slot names are refused as
  keys.  Any hit is ``KIT_TEXT_INLINED``.
* **No predicted answers.**  ``work_family`` and slot values never enter the
  kit; ``alternative_classes`` is the codebook's closed pole enumeration
  (``alternative_axes``), compared pole-by-pole and value-by-value against the
  frozen codebook contract (``ALTERNATIVE_DRIFT``) -- an enumeration of poles,
  never an answer.
* **Source binding is proven, not assumed.**  The fragment file exists, its byte
  length equals the case ``byte_len`` and its sha256 is pinned into the kit; any
  desync is ``FRAGMENT_PIN_DRIFT``.  The 180-fragment seed stays closed: an
  enlarged or undeclared fixture tree is ``SEED_ENLARGED``.
* **Pass 1 and pass 2 differ in the header only.**  The two kits differ exactly
  in ``coder_pass`` and ``submission_id`` -- and in nothing else, including the
  echoed header inside ``submission_template``.  A pair that drifts anywhere
  else is ``KIT_CROSS_PASS_INVARIANT``, as is an on-disk kit that is not the
  byte-exact deterministic regeneration.
* **The delivered form is the frozen S01 form.**  The kit embeds an empty
  ``submission_template`` whose ``schema`` is ``m207-s01-coding-submission/v1``
  (reused verbatim, D475) while the kit's own ``schema`` is
  ``m207-s02-coder-kit/v1``; the two ids must differ.  An untouched template (or
  a kit handed in as a submission) is ``UNFILLED_SUBMISSION``, and a foreign
  form id is ``SUBMISSION_SCHEMA_DRIFT``.

No annotation, span, slot value or agreement number is created, inferred or
repaired here: this gate only reads frozen bytes and refuses drift.  ``check``
re-derives both kits and byte-compares them to the tracked artifacts, printing
the status line ``M207_S02_CODER_KIT_OK`` with the counters ``cases=40 kits=2
cross_pass=identical fragments_pinned=40``; ``run`` re-emits the two tracked kits
as a pure projection (it never reads them, so regeneration after poisoning stays
byte-identical); ``selftest`` additionally proves every hostile path on a
temporary copy and prints ``M207_S02_SELFTEST_OK``.  Every failure is a non-zero
exit with a named diagnostic from the closed S02 diagnostic table on stderr.

This tool binds the upstream frozen sources by content digest (S01 case manifest,
S01 codebook, S01 schemas, M199 seed manifest) and binds this slice's own closed
schema structurally, so the kit shape stays frozen while the slice keeps room to
extend its own schema in a later task.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MARKER = "M207_S02_CODER_KIT_OK"
SELFTEST_MARKER = "M207_S02_SELFTEST_OK"
GATE = "M207_S02_CODER_KIT_GATE"

KIT_SCHEMA_ID = "m207-s02-coder-kit/v1"
KIT_SCHEMA_VERSION = 1
SUBMISSION_SCHEMA_ID = "m207-s01-coding-submission/v1"
SUBMISSION_SCHEMA_VERSION = 1

CASES_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
KIT_PASS1_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json"
KIT_PASS2_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass2.json"
SEED_MANIFEST_REL = "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json"
SCHEMAS_REL = "prd/annotation/m207-s02-schemas.json"
S01_SCHEMAS_REL = "prd/annotation/m207-s01-schemas.json"
CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
ANNOTATION_PREFIX = "prd/annotation/"
FIXTURE_DIR_REL = "crates/ln-decode/tests/fixtures/npa-lawref"

CODEBOOK_CONTRACT_HEADING = "Machine-readable codebook contract"
FENCE_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Every frozen input the kit rests on, pinned by content digest.  Two frozen
# sources must also agree with each other on the case manifest digest (checked
# below), so neither can be "improved" underneath a human pilot.
CASES_SHA256 = "9b0b6bc6bd8eadf9eb86886e45eb756ebade654e96ac3a84132ed9452bdeb9ad"
S01_SCHEMAS_SHA256 = "63a4bc6629bade752f9fa02d1dd5fa6bbf21238e20772d2ba5b74f88ecca3682"
CODEBOOK_SHA256 = "1a1bfe944207e69cb5fb507e94d680384dadecf7ac98ac29b1de4932d7cb76c6"
SEED_MANIFEST_SHA256 = "134751f49db1858329248be1857ada669097f1860609090028c7b5af8975574f"

CASE_COUNT = 40
CASE_COUNT_RANGE = (20, 40)
WORK_FAMILY_CAP = 4
FIXTURE_TXT_COUNT = 180
FROZEN_CASE_DRAW_SEED = 20260915
FROZEN_SOURCE_DRAW_SEED = 20260903
FROZEN_SOURCE_DOCUMENTS = 40
FROZEN_SOURCE_FRAGMENTS = 180
SEED_SCHEMA = "npa-lawref-sample/v1"
SEED_LIFECYCLE = "[bounded]"

CODER_PASSES = (1, 2)
SUBMISSION_IDS = {1: "m207-s02-submission-pass-1", 2: "m207-s02-submission-pass-2"}
NORMALIZED_HEADER = "<cross-pass-normalized>"

# Closed wire shape (mirrors prd/annotation/m207-s02-schemas.json, restated as a
# hand-rolled floor so that a schema edited to *allow* a leak still fails).
KIT_CLOSED_KEYS = (
    "schema",
    "schema_version",
    "codebook",
    "coder_pass",
    "submission_id",
    "submission_schema_id",
    "case_count",
    "work_family_cap",
    "cases",
    "submission_template",
    "non_claims",
    "lifecycle",
)
CASE_CLOSED_KEYS = (
    "case_id",
    "fragment_id",
    "fragment_path",
    "fragment_sha256",
    "byte_len",
    "span_offered_for_coding",
    "alternative_classes",
    "abstention_available",
)
# Keys the frozen source manifest must carry for the projection to be complete.
SOURCE_CASE_REQUIRED_KEYS = (
    "case_id",
    "fragment_id",
    "byte_len",
    "span_offered_for_coding",
    "alternative_classes",
    "abstention_available",
)
FORBIDDEN_CASE_KEYS = ("fragment_text", "slot_values", "slots", "work_family")
TEMPLATE_CLOSED_KEYS = (
    "schema",
    "schema_version",
    "codebook",
    "submission_id",
    "coder_id",
    "coder_pass",
    "provenance",
    "cases",
    "non_claims",
    "lifecycle",
)
M199_SLOT_NAMES = (
    "marker_chain",
    "hier_nums",
    "date",
    "doc_no",
    "law_code",
    "anaphora",
    "range",
    "quoted_enum",
)
# A decoded fragment shorter than this is too small to probe meaningfully; a kit
# value shorter than this is an identifier, not duplicated legal text.
MIN_FRAGMENT_PROBE_CHARS = 12
MIN_VALUE_PROBE_CHARS = 24

# Diagnostics this tool is allowed to speak.  The table is closed (T01) and the
# live gate refuses to emit a name that is not in the frozen S02 table.
LOCAL_DIAGNOSTICS = (
    "ALTERNATIVE_DRIFT",
    "CASE_COUNT_OUT_OF_RANGE",
    "DIAGNOSTIC_TABLE_DRIFT",
    "DUPLICATE_JSON_KEY",
    "FRAGMENT_PIN_DRIFT",
    "FROZEN_SOURCE_DRIFT",
    "KIT_CROSS_PASS_INVARIANT",
    "KIT_TEXT_INLINED",
    "MISSING_ARTIFACT",
    "MISSING_SECTION",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "SEED_ENLARGED",
    "SUBMISSION_SCHEMA_DRIFT",
    "UNFILLED_SUBMISSION",
    "UNKNOWN_CASE_ID",
    "UNSAFE_PATH",
    "WORK_FAMILY_DOMINANCE",
)

Failures = list[tuple[str, str]]
NonClaims = list[str]
Lifecycle = dict[str, Any]


class GateError(Exception):
    """Fatal, named gate failure that stops the run immediately."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


# --------------------------------------------------------------------------- #
# Frozen-source loading, path safety and closed JSON.
# --------------------------------------------------------------------------- #


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def resolve_artifact(
    root: Path, raw: str, label: str, *, suffix: str | None = None, prefix: str | None = None
) -> Path:
    """Resolve a repository-relative path, fail-closed on escapes."""
    if (
        not raw
        or "\x00" in raw
        or raw.startswith("/")
        or "\\" in raw
        or (len(raw) > 1 and raw[1] == ":")
    ):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must be a POSIX relative path")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} may not escape the repository")
    if suffix is not None and relative.suffix != suffix:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must have suffix {suffix}")
    if prefix is not None and not relative.as_posix().startswith(prefix):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must live under {prefix}")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    if not candidate.is_relative_to(root_resolved):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_resolved}")
    return candidate


def safe_fragment_name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "/" in value or "\\" in value or ".." in value:
        raise GateError("UNSAFE_PATH", f"{label}={value!r} is not a flat fragment name")
    if value.startswith("/") or (len(value) > 1 and value[1] == ":"):
        raise GateError("UNSAFE_PATH", f"{label}={value!r} must not be absolute")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise GateError("DUPLICATE_JSON_KEY", f"duplicate object key {key!r}")
        seen[key] = value
    return seen


def load_json_text(text: str, label: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not closed JSON: {exc}") from exc


def load_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise GateError("MISSING_ARTIFACT", f"{label} not found at {path}")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} carries a UTF-8 BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not UTF-8: {exc}") from exc
    return load_json_text(text, label)


def extract_fenced_contract(text: str, heading: str, label: str) -> dict[str, Any]:
    index = text.find(f"## {heading}")
    if index < 0:
        raise GateError("MISSING_SECTION", f"{label} carries no section '## {heading}'")
    match = FENCE_RE.search(text[index:])
    if match is None:
        raise GateError("MISSING_SECTION", f"{label} section '## {heading}' carries no json block")
    contract = load_json_text(match.group(1), f"{label} {heading}")
    if not isinstance(contract, dict):
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} contract is not an object")
    return contract


def require_digest(path: Path, expected: str, label: str, failures: Failures) -> bool:
    if not path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"{label} not found at {path}")
        return False
    digest = sha256_file(path)
    if digest != expected:
        _fail(failures, "FROZEN_SOURCE_DRIFT", f"{label} sha256 {digest} != pinned {expected}")
        return False
    return True


# --------------------------------------------------------------------------- #
# Deterministic projection: fragment binding, cases, template, kit.
# --------------------------------------------------------------------------- #


def fixture_bytes_for(
    fixture_dir: Path, seed_fragments: dict[str, Any], failures: Failures
) -> dict[str, bytes]:
    """Load the frozen fragment bytes and refuse an enlarged fixture tree."""
    payload: dict[str, bytes] = {}
    if not fixture_dir.is_dir():
        _fail(failures, "MISSING_ARTIFACT", f"fixture directory {fixture_dir} does not exist")
        return payload
    declared = {fragment.get("file") for fragment in seed_fragments.values()}
    on_disk = {path.relative_to(fixture_dir).as_posix() for path in fixture_dir.rglob("*.txt")}
    if len(on_disk) != FIXTURE_TXT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"fixture tree holds {len(on_disk)} .txt files, expected {FIXTURE_TXT_COUNT}",
        )
    for extra in sorted(on_disk - declared):
        _fail(failures, "SEED_ENLARGED", f"fixture file {extra} is not declared by the M199 seed")
    for fragment_id, fragment in sorted(seed_fragments.items()):
        name = fragment.get("file")
        try:
            safe_name = safe_fragment_name(name, f"seed fragment {fragment_id} file")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        path = fixture_dir / safe_name
        if not path.is_file():
            _fail(failures, "MISSING_ARTIFACT", f"frozen fragment file {safe_name} is absent")
            continue
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf"):
            _fail(failures, "FROZEN_SOURCE_DRIFT", f"fragment {safe_name} carries a UTF-8 BOM")
            continue
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            _fail(failures, "FROZEN_SOURCE_DRIFT", f"fragment {safe_name} is not UTF-8: {exc}")
            continue
        if fragment.get("byte_len") != len(data):
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"fragment {fragment_id} byte_len drifted: seed {fragment.get('byte_len')} "
                f"!= file {len(data)}",
            )
        payload[fragment_id] = data
    return payload


def build_cases(
    manifest: Any,
    *,
    fixture_bytes: dict[str, bytes],
    seed_fragments: dict[str, Any],
    alternative_axes: Any,
    failures: Failures,
) -> list[dict[str, Any]]:
    """Project the frozen case manifest into the closed kit case shape."""
    if not isinstance(manifest, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "case manifest is not an object")
        return []
    raw_cases = manifest.get("cases")
    if not isinstance(raw_cases, list):
        _fail(failures, "MISSING_ARTIFACT", "case manifest carries no cases array")
        return []
    listed = len(raw_cases)
    if listed != CASE_COUNT or manifest.get("case_count") != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"case manifest holds case_count={manifest.get('case_count')!r} cases={listed}, "
            f"expected {CASE_COUNT}",
        )
    if not CASE_COUNT_RANGE[0] <= listed <= CASE_COUNT_RANGE[1]:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"case manifest holds {listed} cases, outside {list(CASE_COUNT_RANGE)}",
        )
    if manifest.get("draw_seed") != FROZEN_CASE_DRAW_SEED:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"case draw_seed {manifest.get('draw_seed')!r} != frozen {FROZEN_CASE_DRAW_SEED}",
        )
    source_seed = manifest.get("source_seed")
    if not isinstance(source_seed, dict):
        _fail(failures, "SEED_ENLARGED", "case manifest carries no source_seed binding")
    else:
        if source_seed.get("draw_seed") != FROZEN_SOURCE_DRAW_SEED:
            _fail(
                failures,
                "SEED_ENLARGED",
                f"source_seed draw_seed {source_seed.get('draw_seed')!r} "
                f"!= frozen {FROZEN_SOURCE_DRAW_SEED}",
            )
        if source_seed.get("sha256") != SEED_MANIFEST_SHA256:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"source_seed sha256 {source_seed.get('sha256')!r} != M199 seed "
                f"{SEED_MANIFEST_SHA256}",
            )
        if source_seed.get("fragments") != FROZEN_SOURCE_FRAGMENTS:
            _fail(
                failures,
                "SEED_ENLARGED",
                f"source_seed fragments {source_seed.get('fragments')!r} "
                f"!= frozen {FROZEN_SOURCE_FRAGMENTS}",
            )
        if source_seed.get("documents") != FROZEN_SOURCE_DOCUMENTS:
            _fail(
                failures,
                "SEED_ENLARGED",
                f"source_seed documents {source_seed.get('documents')!r} "
                f"!= frozen {FROZEN_SOURCE_DOCUMENTS}",
            )
    if manifest.get("work_family_cap") != WORK_FAMILY_CAP:
        _fail(
            failures,
            "WORK_FAMILY_DOMINANCE",
            f"case manifest work_family_cap {manifest.get('work_family_cap')!r} "
            f"!= frozen {WORK_FAMILY_CAP}",
        )
    if not isinstance(alternative_axes, list) or not alternative_axes:
        _fail(failures, "ALTERNATIVE_DRIFT", "codebook contract carries no alternative_axes")
        alternative_axes = []

    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for position, raw in enumerate(raw_cases):
        label = f"case[{position}]"
        if not isinstance(raw, dict):
            _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} is not an object")
            continue
        missing = [key for key in SOURCE_CASE_REQUIRED_KEYS if key not in raw]
        if missing:
            _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} misses frozen keys {missing}")
            continue
        case_id = raw["case_id"]
        if not isinstance(case_id, str) or not case_id:
            _fail(failures, "UNKNOWN_CASE_ID", f"{label} carries case_id={case_id!r}")
            continue
        if case_id in seen_ids:
            _fail(failures, "UNKNOWN_CASE_ID", f"case id {case_id} is repeated in the manifest")
            continue
        seen_ids.add(case_id)
        try:
            fragment_id = safe_fragment_name(raw["fragment_id"], f"{case_id} fragment_id")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        if seed_fragments and fragment_id not in seed_fragments:
            _fail(
                failures,
                "UNKNOWN_CASE_ID",
                f"{case_id} references {fragment_id}, absent from the frozen M199 seed",
            )
            continue
        data = fixture_bytes.get(fragment_id)
        if data is None:
            _fail(
                failures,
                "FRAGMENT_PIN_DRIFT",
                f"{case_id} fragment {fragment_id} is not pinned in the frozen fixture tree",
            )
            continue
        declared_len = raw["byte_len"]
        if not isinstance(declared_len, int) or isinstance(declared_len, bool) or declared_len <= 0:
            _fail(
                failures,
                "FRAGMENT_PIN_DRIFT",
                f"{case_id} byte_len={declared_len!r} is not a positive int",
            )
            continue
        if declared_len != len(data):
            _fail(
                failures,
                "FRAGMENT_PIN_DRIFT",
                f"{case_id} byte_len {declared_len} != fragment file {len(data)}",
            )
            continue
        if raw["alternative_classes"] != alternative_axes:
            _fail(
                failures,
                "ALTERNATIVE_DRIFT",
                f"{case_id} alternative_classes are not the codebook alternative_axes",
            )
        cases.append(
            {
                "case_id": case_id,
                "fragment_id": fragment_id,
                "fragment_path": f"{FIXTURE_DIR_REL}/{fragment_id}.txt",
                "fragment_sha256": sha256_bytes(data),
                "byte_len": declared_len,
                "span_offered_for_coding": raw["span_offered_for_coding"],
                "alternative_classes": copy.deepcopy(raw["alternative_classes"]),
                "abstention_available": raw["abstention_available"],
            }
        )
    return cases


def build_submission_template(
    *,
    submission_id: str,
    coder_pass: int,
    non_claims: NonClaims,
    lifecycle: Lifecycle,
) -> dict[str, Any]:
    """The empty S01 submission form the coder fills: nothing is pre-answered."""
    return {
        "schema": SUBMISSION_SCHEMA_ID,
        "schema_version": SUBMISSION_SCHEMA_VERSION,
        "codebook": CODEBOOK_REL,
        "submission_id": submission_id,
        "coder_id": "",
        "coder_pass": coder_pass,
        "provenance": "",
        "cases": [],
        "non_claims": list(non_claims),
        "lifecycle": copy.deepcopy(lifecycle),
    }


def build_kit(
    *,
    coder_pass: int,
    cases: list[dict[str, Any]],
    work_family_cap: int,
    non_claims: NonClaims,
    lifecycle: Lifecycle,
) -> dict[str, Any]:
    submission_id = SUBMISSION_IDS[coder_pass]
    return {
        "schema": KIT_SCHEMA_ID,
        "schema_version": KIT_SCHEMA_VERSION,
        "codebook": CODEBOOK_REL,
        "coder_pass": coder_pass,
        "submission_id": submission_id,
        "submission_schema_id": SUBMISSION_SCHEMA_ID,
        "case_count": len(cases),
        "work_family_cap": work_family_cap,
        "cases": copy.deepcopy(cases),
        "submission_template": build_submission_template(
            submission_id=submission_id,
            coder_pass=coder_pass,
            non_claims=non_claims,
            lifecycle=lifecycle,
        ),
        "non_claims": list(non_claims),
        "lifecycle": copy.deepcopy(lifecycle),
    }


def render_kit(kit: dict[str, Any]) -> bytes:
    return (json.dumps(kit, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def normalize_cross_pass(kit: Any) -> Any:
    """Blank the two header fields (and their template echo) before comparing."""
    clone = copy.deepcopy(kit)
    if isinstance(clone, dict):
        clone["coder_pass"] = NORMALIZED_HEADER
        clone["submission_id"] = NORMALIZED_HEADER
        template = clone.get("submission_template")
        if isinstance(template, dict):
            if "coder_pass" in template:
                template["coder_pass"] = NORMALIZED_HEADER
            if "submission_id" in template:
                template["submission_id"] = NORMALIZED_HEADER
    return clone


def first_difference(left: Any, right: Any, path: str = "$") -> str:
    if type(left) is not type(right):  # noqa: E721 - a bool/int mismatch is a real drift
        return f"{path}: {left!r} ({type(left).__name__}) != {right!r} ({type(right).__name__})"
    if isinstance(left, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left:
                return f"{path}.{key}: missing on the left"
            if key not in right:
                return f"{path}.{key}: missing on the right"
            if left[key] != right[key]:
                return first_difference(left[key], right[key], f"{path}.{key}")
        return f"{path}: objects differ without a located field"
    if isinstance(left, list):
        if len(left) != len(right):
            return f"{path}: length {len(left)} != {len(right)}"
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            if a != b:
                return first_difference(a, b, f"{path}[{index}]")
        return f"{path}: lists differ without a located element"
    return f"{path}: {left!r} != {right!r}"


def iter_string_values(node: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield from iter_string_values(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_string_values(value, f"{path}[{index}]")
    elif isinstance(node, str):
        yield path, node


def iter_keys(node: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield f"{path}.{key}", key
            yield from iter_keys(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_keys(value, f"{path}[{index}]")


# --------------------------------------------------------------------------- #
# Inspection: closed shape, leakage, pass coupling, template handling.
# --------------------------------------------------------------------------- #


def check_projection_shape(kit: Any, label: str, failures: Failures) -> None:
    if not isinstance(kit, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", f"{label} is not an object")
        return
    missing = [key for key in KIT_CLOSED_KEYS if key not in kit]
    extra = [key for key in kit if key not in KIT_CLOSED_KEYS]
    if missing or extra:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label} key drift: missing={missing} extra={extra}",
        )
    if kit.get("schema") != KIT_SCHEMA_ID:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} schema={kit.get('schema')!r}")
    if kit.get("schema_version") != KIT_SCHEMA_VERSION:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} schema_version={kit.get('schema_version')!r}")
    if kit.get("submission_schema_id") != SUBMISSION_SCHEMA_ID:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"{label} submission_schema_id={kit.get('submission_schema_id')!r}",
        )
    if kit.get("schema") == kit.get("submission_schema_id"):
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"{label} kit schema id and submission schema id must differ",
        )
    if kit.get("codebook") != CODEBOOK_REL:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} codebook={kit.get('codebook')!r}")
    if kit.get("coder_pass") not in CODER_PASSES:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} coder_pass={kit.get('coder_pass')!r}")
    if kit.get("case_count") != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"{label} case_count={kit.get('case_count')!r} != {CASE_COUNT}",
        )
    if kit.get("work_family_cap") != WORK_FAMILY_CAP:
        _fail(
            failures,
            "WORK_FAMILY_DOMINANCE",
            f"{label} work_family_cap={kit.get('work_family_cap')!r} != {WORK_FAMILY_CAP}",
        )
    if not isinstance(kit.get("cases"), list):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} cases is not an array")
    elif len(kit["cases"]) != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"{label} carries {len(kit['cases'])} cases, expected {CASE_COUNT}",
        )
    check_template_shape(kit.get("submission_template"), label, failures)


def check_template_shape(template: Any, label: str, failures: Failures) -> None:
    if not isinstance(template, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} submission_template is not an object")
        return
    missing = [key for key in TEMPLATE_CLOSED_KEYS if key not in template]
    extra = [key for key in template if key not in TEMPLATE_CLOSED_KEYS]
    if missing or extra:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label} submission_template key drift: missing={missing} extra={extra}",
        )
    if template.get("schema") != SUBMISSION_SCHEMA_ID:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"{label} submission_template schema={template.get('schema')!r}",
        )


def check_case_shape(
    kit: Any, label: str, known_case_ids: set[str], failures: Failures
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    raw_cases = kit.get("cases") if isinstance(kit, dict) else None
    if not isinstance(raw_cases, list):
        return cases
    seen: set[str] = set()
    for position, case in enumerate(raw_cases):
        pointer = f"{label} cases[{position}]"
        if not isinstance(case, dict):
            _fail(failures, "SCHEMA_KEY_DRIFT", f"{pointer} is not an object")
            continue
        forbidden = [key for key in FORBIDDEN_CASE_KEYS if key in case]
        if forbidden:
            _fail(failures, "KIT_TEXT_INLINED", f"{pointer} carries forbidden keys {forbidden}")
        missing = [key for key in CASE_CLOSED_KEYS if key not in case]
        extra = [key for key in case if key not in CASE_CLOSED_KEYS]
        if missing or extra:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"{pointer} key drift: missing={missing} extra={extra}",
            )
        case_id = case.get("case_id")
        if case_id not in known_case_ids:
            _fail(failures, "UNKNOWN_CASE_ID", f"{pointer} case_id={case_id!r} is not frozen")
        elif case_id in seen:
            _fail(failures, "UNKNOWN_CASE_ID", f"{pointer} case_id={case_id} is repeated")
        else:
            seen.add(case_id)
        digest = case.get("fragment_sha256")
        if not isinstance(digest, str) or SHA256_RE.match(digest) is None:
            _fail(failures, "FRAGMENT_PIN_DRIFT", f"{pointer} fragment_sha256={digest!r}")
        cases.append(case)
    if known_case_ids and len(raw_cases) != len(seen):
        _fail(
            failures,
            "UNKNOWN_CASE_ID",
            f"{label} covers {len(seen)} distinct frozen case ids out of {len(raw_cases)} cases",
        )
    return cases


def check_no_inlined_text(
    kit: Any,
    *,
    label: str,
    fragment_texts: dict[str, str],
    skip_pointers: frozenset[str] = frozenset(),
    failures: Failures,
) -> None:
    """Refuse duplicated legal text and slot names anywhere in the kit."""
    for pointer, key in iter_keys(kit):
        if key in M199_SLOT_NAMES:
            _fail(
                failures,
                "KIT_TEXT_INLINED",
                f"{label} {pointer} names closed slot {key!r}; the kit carries no slot surface",
            )
    serialized = json.dumps(kit, ensure_ascii=False, sort_keys=True)
    for case_id, text in sorted(fragment_texts.items()):
        probe = text.strip()
        if len(probe) >= MIN_FRAGMENT_PROBE_CHARS and probe in serialized:
            _fail(
                failures,
                "KIT_TEXT_INLINED",
                f"{label} carries the decoded text of {case_id} verbatim",
            )
            break
    for pointer, value in iter_string_values(kit):
        if pointer in skip_pointers or len(value) < MIN_VALUE_PROBE_CHARS:
            continue
        if any(value in text for text in fragment_texts.values()):
            _fail(
                failures,
                "KIT_TEXT_INLINED",
                f"{label} {pointer} duplicates decoded fragment text ({value[:32]!r}...)",
            )
            break


def check_cross_pass(left: Any, right: Any, failures: Failures) -> bool:
    """Pass 1 and pass 2 may differ in the header fields only."""
    if normalize_cross_pass(left) == normalize_cross_pass(right):
        return True
    left_kit = left if isinstance(left, dict) else {}
    right_kit = right if isinstance(right, dict) else {}
    _fail(
        failures,
        "KIT_CROSS_PASS_INVARIANT",
        "pass-1 and pass-2 kits differ beyond coder_pass/submission_id: "
        + first_difference(normalize_cross_pass(left_kit), normalize_cross_pass(right_kit)),
    )
    return False


def submission_form_diagnostics(
    candidate: Any,
    *,
    label: str,
    kit_schema_id: str,
    template: Any,
    failures: Failures,
) -> None:
    """Classify a candidate envelope against the frozen submission form."""
    if not isinstance(candidate, dict):
        _fail(failures, "MISSING_ARTIFACT", f"{label} is not a JSON object")
        return
    schema = candidate.get("schema")
    if schema == kit_schema_id:
        _fail(
            failures,
            "UNFILLED_SUBMISSION",
            f"{label} carries the coder-kit schema id {kit_schema_id!r}: a kit is not a submission",
        )
        return
    if schema != SUBMISSION_SCHEMA_ID:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"{label} schema={schema!r} != {SUBMISSION_SCHEMA_ID}",
        )
        return
    missing = [key for key in TEMPLATE_CLOSED_KEYS if key not in candidate]
    extra = [key for key in candidate if key not in TEMPLATE_CLOSED_KEYS]
    if missing or extra:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} key drift: missing={missing} extra={extra}")
        return
    if normalize_cross_pass(candidate) == normalize_cross_pass(template):
        _fail(
            failures,
            "UNFILLED_SUBMISSION",
            f"{label} is still the untouched submission_template of the kit",
        )
        return
    if not str(candidate.get("coder_id") or "").strip():
        _fail(failures, "UNFILLED_SUBMISSION", f"{label} carries no coder_id")
        return
    if not str(candidate.get("provenance") or "").strip():
        _fail(failures, "UNFILLED_SUBMISSION", f"{label} carries no provenance")
        return
    cases = candidate.get("cases")
    if not isinstance(cases, list) or not cases:
        _fail(failures, "UNFILLED_SUBMISSION", f"{label} carries no coded cases")
        return
    if candidate.get("coder_pass") not in CODER_PASSES:
        _fail(
            failures, "UNFILLED_SUBMISSION", f"{label} coder_pass={candidate.get('coder_pass')!r}"
        )


# --------------------------------------------------------------------------- #
# Gate run.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Paths:
    cases: str = CASES_REL
    fixture_dir: str = FIXTURE_DIR_REL
    kit_pass1: str = KIT_PASS1_REL
    kit_pass2: str = KIT_PASS2_REL
    schemas: str = SCHEMAS_REL
    s01_schemas: str = S01_SCHEMAS_REL
    codebook: str = CODEBOOK_REL
    seed_manifest: str = SEED_MANIFEST_REL
    submission: str | None = None


def check_schemas_binding(schemas: Any, failures: Failures) -> tuple[NonClaims, Lifecycle]:
    """Bind the kit shape to the frozen S02 closed schemas."""
    if not isinstance(schemas, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "S02 schemas document is not an object")
        return [], {}
    sub = (
        (schemas.get("schemas") or {}).get("coder_kit")
        if isinstance(schemas.get("schemas"), dict)
        else None
    )
    if not isinstance(sub, dict):
        _fail(failures, "MISSING_SECTION", "$.schemas.coder_kit is absent from the S02 schemas")
    else:
        expectations = (
            ("schema_id", KIT_SCHEMA_ID),
            ("case_count", CASE_COUNT),
            ("kits", len(CODER_PASSES)),
            ("work_family_cap", WORK_FAMILY_CAP),
            ("text_inlined", False),
        )
        for key, expected in expectations:
            if sub.get(key) != expected:
                _fail(
                    failures,
                    "SCHEMA_KEY_DRIFT",
                    f"$.schemas.coder_kit.{key}={sub.get(key)!r} != frozen {expected!r}",
                )
        for key, expected in (
            ("closed_keys", list(KIT_CLOSED_KEYS)),
            ("required_keys", list(KIT_CLOSED_KEYS)),
            ("case_closed_keys", list(CASE_CLOSED_KEYS)),
            ("case_required_keys", list(CASE_CLOSED_KEYS)),
            ("forbidden_case_keys", list(FORBIDDEN_CASE_KEYS)),
            ("template_closed_keys", list(TEMPLATE_CLOSED_KEYS)),
        ):
            if sorted(sub.get(key) or []) != sorted(expected):
                _fail(
                    failures,
                    "SCHEMA_KEY_DRIFT",
                    f"$.schemas.coder_kit.{key}={sub.get(key)!r} != frozen {expected!r}",
                )
    if schemas.get("submission_schema_id") != SUBMISSION_SCHEMA_ID:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"$.submission_schema_id={schemas.get('submission_schema_id')!r}",
        )
    if schemas.get("codebook") != CODEBOOK_REL:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"$.codebook={schemas.get('codebook')!r}")
    diagnostics = schemas.get("diagnostics")
    if not isinstance(diagnostics, list):
        _fail(failures, "DIAGNOSTIC_TABLE_DRIFT", "$.diagnostics is not an array")
    else:
        unknown = [name for name in LOCAL_DIAGNOSTICS if name not in diagnostics]
        if unknown:
            _fail(
                failures,
                "DIAGNOSTIC_TABLE_DRIFT",
                f"{unknown} are not in the frozen S02 diagnostic table",
            )
        frozen_sources = schemas.get("frozen_sources")
        declared = None
        if isinstance(frozen_sources, dict) and isinstance(
            frozen_sources.get("m207_s01_cases"), dict
        ):
            declared = frozen_sources["m207_s01_cases"].get("sha256")
        if declared is not None and declared != CASES_SHA256:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"S02 schemas declare case-manifest sha256 {declared!r} != pinned {CASES_SHA256}",
            )
    non_claims = schemas.get("non_claims")
    lifecycle = schemas.get("lifecycle")
    if not isinstance(non_claims, list) or not non_claims:
        _fail(failures, "MISSING_ARTIFACT", "$.non_claims is absent from the S02 schemas")
        non_claims = []
    if not isinstance(lifecycle, dict) or not lifecycle:
        _fail(failures, "MISSING_ARTIFACT", "$.lifecycle is absent from the S02 schemas")
        lifecycle = {}
    return list(non_claims), dict(lifecycle)


def run_gate(mode: str, root: Path, paths: Paths) -> tuple[Failures, str]:
    if not root.is_dir():
        return [("MISSING_ARTIFACT", f"root {root} is not a directory")], ""
    try:
        cases_path = resolve_artifact(root, paths.cases, "cases", suffix=".json")
        kit1_path = resolve_artifact(root, paths.kit_pass1, "kit-pass1", suffix=".json")
        kit2_path = resolve_artifact(root, paths.kit_pass2, "kit-pass2", suffix=".json")
        schemas_path = resolve_artifact(
            root, paths.schemas, "schemas", suffix=".json", prefix=ANNOTATION_PREFIX
        )
        s01_path = resolve_artifact(
            root, paths.s01_schemas, "s01-schemas", suffix=".json", prefix=ANNOTATION_PREFIX
        )
        codebook_path = resolve_artifact(
            root, paths.codebook, "codebook", suffix=".md", prefix=ANNOTATION_PREFIX
        )
        seed_path = resolve_artifact(root, paths.seed_manifest, "seed-manifest", suffix=".json")
        fixture_dir = resolve_artifact(root, paths.fixture_dir, "fixture-dir")
        submission_path = (
            resolve_artifact(root, paths.submission, "submission", suffix=".json")
            if paths.submission
            else None
        )
    except GateError as exc:
        return [(exc.diagnostic, exc.detail)], ""

    failures: Failures = []
    manifest = schemas = seed = None
    if require_digest(cases_path, CASES_SHA256, "frozen case manifest", failures):
        try:
            manifest = load_json(cases_path, "case manifest")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    # The S02 schemas are this slice's own closed-schema artifact: it is bound
    # structurally (kit shape, diagnostic table, non-claims, lifecycle) and its
    # declared case-manifest pin is cross-checked, exactly as S01 binds its own
    # schema, so a later task may extend this slice's schema without tripping a
    # byte pin while the kit shape stays frozen.
    if not schemas_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"frozen S02 schemas not found at {paths.schemas}")
    else:
        try:
            schemas = load_json(schemas_path, "S02 schemas")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    if require_digest(s01_path, S01_SCHEMAS_SHA256, "frozen S01 schemas", failures):
        try:
            s01_schemas = load_json(s01_path, "S01 schemas")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
        else:
            check_s01_form_reuse(s01_schemas, failures)
    if require_digest(codebook_path, CODEBOOK_SHA256, "frozen codebook", failures):
        try:
            alternatives = extract_fenced_contract(
                codebook_path.read_text(encoding="utf-8"), CODEBOOK_CONTRACT_HEADING, "codebook"
            ).get("alternative_axes")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            alternatives = None
    else:
        alternatives = None
    if require_digest(seed_path, SEED_MANIFEST_SHA256, "frozen M199 seed manifest", failures):
        try:
            seed = load_json(seed_path, "M199 seed manifest")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
        else:
            check_seed_document(seed, failures)

    seed_fragments = seed_index(seed, failures)
    fixture_bytes = fixture_bytes_for(fixture_dir, seed_fragments, failures)
    non_claims, lifecycle = check_schemas_binding(schemas, failures)

    cases = build_cases(
        manifest,
        fixture_bytes=fixture_bytes,
        seed_fragments=seed_fragments,
        alternative_axes=alternatives,
        failures=failures,
    )
    fragment_texts: dict[str, str] = {}
    for case in cases:
        data = fixture_bytes.get(case["fragment_id"])
        if data is not None:
            try:
                fragment_texts[case["case_id"]] = data.decode("utf-8")
            except UnicodeDecodeError:
                continue

    work_family_cap = WORK_FAMILY_CAP
    expected_kits = {
        key: build_kit(
            coder_pass=key,
            cases=cases,
            work_family_cap=work_family_cap,
            non_claims=non_claims,
            lifecycle=lifecycle,
        )
        for key in CODER_PASSES
    }
    expected_bytes = {key: render_kit(kit) for key, kit in expected_kits.items()}
    known_case_ids = {case["case_id"] for case in cases}

    for key in CODER_PASSES:
        label = f"regenerated pass-{key}"
        check_projection_shape(expected_kits[key], label, failures)
        check_case_shape(expected_kits[key], label, known_case_ids, failures)
        check_case_pins(expected_kits[key], label, fixture_bytes, failures)
        check_no_inlined_text(
            expected_kits[key], label=label, fragment_texts=fragment_texts, failures=failures
        )
    check_cross_pass(expected_kits[1], expected_kits[2], failures)

    # ``run`` is a pure projection: it never reads a tracked kit, so poisoning a
    # pass artifact cannot propagate into its regeneration.  ``check`` re-reads
    # the artifacts through the same inspection path and byte-compares them.
    kits_on_disk: dict[int, Any] = {}
    if mode == "run":
        for key, path in ((1, kit1_path), (2, kit2_path)):
            if not failures:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected_bytes[key])
    else:
        for key, path in ((1, kit1_path), (2, kit2_path)):
            label = f"on-disk pass-{key}"
            declared = paths.kit_pass1 if key == 1 else paths.kit_pass2
            if not path.is_file():
                _fail(failures, "MISSING_ARTIFACT", f"{label} kit not found at {declared}")
                continue
            try:
                kits_on_disk[key] = load_json(path, f"{label} kit")
            except GateError as exc:
                _fail(failures, exc.diagnostic, exc.detail)
                continue
            check_projection_shape(kits_on_disk[key], label, failures)
            check_case_shape(kits_on_disk[key], label, known_case_ids, failures)
            check_case_pins(kits_on_disk[key], label, fixture_bytes, failures)
            check_no_inlined_text(
                kits_on_disk[key], label=label, fragment_texts=fragment_texts, failures=failures
            )
            if path.read_bytes() != expected_bytes[key]:
                _fail(
                    failures,
                    "KIT_CROSS_PASS_INVARIANT",
                    f"{label} is not the byte-exact deterministic regeneration of the frozen "
                    f"case manifest ({len(path.read_bytes())} vs {len(expected_bytes[key])} bytes)",
                )
        if len(kits_on_disk) == 2:
            check_cross_pass(kits_on_disk[1], kits_on_disk[2], failures)

    if submission_path is not None:
        try:
            candidate = load_json(submission_path, "candidate submission")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
        else:
            template = (
                kits_on_disk[1].get("submission_template")
                if isinstance(kits_on_disk.get(1), dict)
                else None
            )
            submission_form_diagnostics(
                candidate,
                label=paths.submission or "submission",
                kit_schema_id=KIT_SCHEMA_ID,
                template=template,
                failures=failures,
            )

    cross_pass_ok = not any(diagnostic == "KIT_CROSS_PASS_INVARIANT" for diagnostic, _ in failures)

    fragments_pinned = sum(
        1
        for case in cases
        if case["fragment_sha256"] == sha256_bytes(fixture_bytes.get(case["fragment_id"], b""))
        and case["byte_len"] == len(fixture_bytes.get(case["fragment_id"], b""))
    )
    summary = (
        f"{MARKER} cases={len(cases)} kits={len(expected_kits)} "
        f"cross_pass={'identical' if cross_pass_ok else 'drift'} "
        f"fragments_pinned={fragments_pinned} mode={mode} "
        f"coder_pass={list(CODER_PASSES)} "
        f"submission_schema={SUBMISSION_SCHEMA_ID} "
        f"text_inlined=false slot_values=0 header_only_diff=true"
    )
    return failures, summary


def check_case_pins(
    kit: Any,
    label: str,
    fixture_bytes: dict[str, bytes],
    failures: Failures,
) -> None:
    """The kit pins the fragment sha256 and byte length; verify the pin holds."""
    raw_cases = kit.get("cases") if isinstance(kit, dict) else None
    if not isinstance(raw_cases, list):
        return
    for position, case in enumerate(raw_cases):
        if not isinstance(case, dict):
            continue
        pointer = f"{label} cases[{position}]"
        fragment_id = case.get("fragment_id")
        data = fixture_bytes.get(fragment_id) if isinstance(fragment_id, str) else None
        if data is None:
            _fail(
                failures, "FRAGMENT_PIN_DRIFT", f"{pointer} fragment {fragment_id!r} is not frozen"
            )
            continue
        if case.get("fragment_sha256") != sha256_bytes(data):
            _fail(
                failures,
                "FRAGMENT_PIN_DRIFT",
                f"{pointer} fragment_sha256 does not pin {fragment_id}",
            )
        if case.get("byte_len") != len(data):
            _fail(
                failures,
                "FRAGMENT_PIN_DRIFT",
                f"{pointer} byte_len={case.get('byte_len')!r} != frozen fragment {len(data)} bytes",
            )
        expected_path = f"{FIXTURE_DIR_REL}/{fragment_id}.txt"
        if case.get("fragment_path") != expected_path:
            _fail(
                failures,
                "FRAGMENT_PIN_DRIFT",
                f"{pointer} fragment_path={case.get('fragment_path')!r} != {expected_path!r}",
            )


def check_s01_form_reuse(s01_schemas: Any, failures: Failures) -> None:
    """The submission form is reused verbatim; S02 adds no key to it."""
    if not isinstance(s01_schemas, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "S01 schemas document is not an object")
        return
    sub = (s01_schemas.get("schemas") or {}).get("coding_submission")
    if not isinstance(sub, dict):
        _fail(failures, "MISSING_SECTION", "$.schemas.coding_submission is absent from S01 schemas")
        return
    if sub.get("schema_id") != SUBMISSION_SCHEMA_ID:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"S01 submission schema_id={sub.get('schema_id')!r} != {SUBMISSION_SCHEMA_ID}",
        )
    if sorted(sub.get("closed_keys") or []) != sorted(TEMPLATE_CLOSED_KEYS):
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"S01 submission closed_keys={sub.get('closed_keys')!r} != S02 template keys "
            f"{list(TEMPLATE_CLOSED_KEYS)}",
        )
    if sorted(sub.get("coder_pass_values") or []) != sorted(CODER_PASSES):
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"S01 coder_pass_values={sub.get('coder_pass_values')!r} != {list(CODER_PASSES)}",
        )


def check_seed_document(seed: Any, failures: Failures) -> None:
    if not isinstance(seed, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "M199 seed manifest is not an object")
        return
    if seed.get("schema") != SEED_SCHEMA:
        _fail(failures, "FROZEN_SOURCE_DRIFT", f"M199 seed schema {seed.get('schema')!r} drifted")
    if seed.get("lifecycle") != SEED_LIFECYCLE:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"M199 seed lifecycle {seed.get('lifecycle')!r} != {SEED_LIFECYCLE!r}",
        )
    fragments = seed.get("fragments")
    documents = seed.get("documents")
    if not isinstance(fragments, list) or len(fragments) != FROZEN_SOURCE_FRAGMENTS:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"M199 seed declares {len(fragments) if isinstance(fragments, list) else None} "
            f"fragments, expected {FROZEN_SOURCE_FRAGMENTS}",
        )
    if not isinstance(documents, list) or len(documents) != FROZEN_SOURCE_DOCUMENTS:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"M199 seed declares {len(documents) if isinstance(documents, list) else None} "
            f"documents, expected {FROZEN_SOURCE_DOCUMENTS}",
        )


def seed_index(seed: Any, failures: Failures) -> dict[str, Any]:
    if not isinstance(seed, dict):
        return {}
    fragments = {
        fragment["id"]: fragment
        for fragment in seed.get("fragments") or []
        if isinstance(fragment, dict) and isinstance(fragment.get("id"), str)
    }
    if not fragments:
        _fail(failures, "SEED_ENLARGED", "M199 seed carries no fragments")
    return fragments


def report(failures: Failures, summary: str) -> int:
    if failures:
        seen: set[str] = set()
        for diagnostic, detail in failures:
            line = f"{diagnostic}: {detail}"
            if line in seen:
                continue
            seen.add(line)
            print(f"FAIL {line}", file=sys.stderr)
        print(f"FAIL {GATE}: {len(seen)} finding(s)", file=sys.stderr)
        return 1
    print(summary)
    return 0


# --------------------------------------------------------------------------- #
# Negative proof: every hostile path must produce its named diagnostic.
# --------------------------------------------------------------------------- #

Mutator = Callable[[Path], None]

SNAPSHOT_RELS = (
    CASES_REL,
    SEED_MANIFEST_REL,
    SCHEMAS_REL,
    S01_SCHEMAS_REL,
    CODEBOOK_REL,
    KIT_PASS1_REL,
    KIT_PASS2_REL,
)


def snapshot_tree(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for rel in SNAPSHOT_RELS:
        path = root / rel
        if path.is_file():
            snapshot[rel] = path.read_bytes()
    fixture_dir = root / FIXTURE_DIR_REL
    if fixture_dir.is_dir():
        for path in sorted(fixture_dir.glob("*.txt")):
            snapshot[path.relative_to(root).as_posix()] = path.read_bytes()
    return snapshot


def restore_tree(root: Path, snapshot: dict[str, bytes]) -> None:
    for rel, data in snapshot.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    fixture_dir = root / FIXTURE_DIR_REL
    if fixture_dir.is_dir():
        for path in sorted(fixture_dir.glob("*.txt")):
            rel = path.relative_to(root).as_posix()
            if rel not in snapshot:
                path.unlink()


def _edit_json(root: Path, rel: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = root / rel
    payload = load_json(path, rel)
    mutate(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _case_fragment_id(root: Path, rel: str, index: int) -> str:
    payload = load_json(root / rel, rel)
    return str(payload["cases"][index]["fragment_id"])


def run_selftest(root: Path, paths: Paths) -> int:
    if not (root / CASES_REL).is_file():
        print(f"FAIL MISSING_ARTIFACT: selftest baseline missing {CASES_REL}", file=sys.stderr)
        return 1
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="m207-s02-coder-kit-") as tmp:
        temp_root = Path(tmp)
        baseline_snapshot = snapshot_tree(root)
        baseline: dict[str, bytes] = {}
        for rel in SNAPSHOT_RELS:
            if rel not in baseline_snapshot and rel != CODEBOOK_REL:
                print(f"FAIL MISSING_ARTIFACT: selftest baseline missing {rel}", file=sys.stderr)
                return 1
        restore_tree(temp_root, baseline_snapshot)
        baseline = {
            rel: (temp_root / rel).read_bytes()
            for rel in SNAPSHOT_RELS
            if (temp_root / rel).is_file()
        }

        def fresh_gate(probe_paths: Paths | None = None) -> Failures:
            restore_tree(temp_root, baseline_snapshot)
            failures, _ = run_gate("check", temp_root, probe_paths or paths)
            return failures

        pristine = fresh_gate()
        if pristine:
            problems.append(f"pristine temp copy is not green: {sorted({d for d, _ in pristine})}")

        fragment_id = _case_fragment_id(temp_root, KIT_PASS1_REL, 0)
        long_fragment_id = _case_fragment_id(temp_root, KIT_PASS1_REL, 2)
        long_text = (temp_root / FIXTURE_DIR_REL / f"{long_fragment_id}.txt").read_text(
            encoding="utf-8"
        )
        template_json = json.dumps(
            load_json(temp_root / KIT_PASS1_REL, "kit")["submission_template"],
            ensure_ascii=False,
            indent=2,
        )

        def mutate_forbidden_key(target: Path) -> None:
            _edit_json(
                target,
                KIT_PASS1_REL,
                lambda kit: kit["cases"][0].update(
                    {"fragment_text": (target / FIXTURE_DIR_REL / f"{fragment_id}.txt").read_text()}
                ),
            )

        def mutate_inlined_value(target: Path) -> None:
            _edit_json(
                target,
                KIT_PASS1_REL,
                lambda kit: kit["submission_template"].update({"coder_id": long_text.strip()}),
            )

        def mutate_slot_key(target: Path) -> None:
            _edit_json(
                target,
                KIT_PASS1_REL,
                lambda kit: kit["cases"][1].update({"date": "2020-09-14"}),
            )

        def mutate_cross_pass(target: Path) -> None:
            _edit_json(
                target,
                KIT_PASS2_REL,
                lambda kit: kit["cases"][3].update({"byte_len": kit["cases"][3]["byte_len"] + 1}),
            )

        def mutate_unknown_case(target: Path) -> None:
            _edit_json(
                target,
                KIT_PASS1_REL,
                lambda kit: kit["cases"][5].update({"case_id": "m207-s01-case-999"}),
            )

        def mutate_case_count(target: Path) -> None:
            def mutate(kit: dict[str, Any]) -> None:
                kit["cases"] = kit["cases"][:-1]
                kit["case_count"] = len(kit["cases"])

            _edit_json(target, KIT_PASS1_REL, mutate)

        def mutate_seed_enlarged(target: Path) -> None:
            (target / FIXTURE_DIR_REL / "npa-frag-999.txt").write_text("x", encoding="utf-8")

        def mutate_fragment_pin(target: Path) -> None:
            path = target / FIXTURE_DIR_REL / f"{fragment_id}.txt"
            path.write_bytes(path.read_bytes() + b" ")

        def mutate_frozen_source(target: Path) -> None:
            cases = target / CASES_REL
            cases.write_bytes(cases.read_bytes() + b"\n")

        def mutate_undeclared_fragment(target: Path) -> None:
            (target / FIXTURE_DIR_REL / "npa-frag-001.txt").unlink()

        cases: tuple[tuple[str, Paths | None, Mutator | None, str], ...] = (
            ("kit-forbidden-key", None, mutate_forbidden_key, "KIT_TEXT_INLINED"),
            ("kit-inlined-value", None, mutate_inlined_value, "KIT_TEXT_INLINED"),
            ("kit-slot-key", None, mutate_slot_key, "KIT_TEXT_INLINED"),
            ("kit-cross-pass-drift", None, mutate_cross_pass, "KIT_CROSS_PASS_INVARIANT"),
            ("kit-unknown-case-id", None, mutate_unknown_case, "UNKNOWN_CASE_ID"),
            ("kit-case-count-out-of-range", None, mutate_case_count, "CASE_COUNT_OUT_OF_RANGE"),
            ("seed-enlarged", None, mutate_seed_enlarged, "SEED_ENLARGED"),
            ("seed-fragment-absent", None, mutate_undeclared_fragment, "SEED_ENLARGED"),
            ("fragment-pin-drift", None, mutate_fragment_pin, "FRAGMENT_PIN_DRIFT"),
            ("frozen-source-drift", None, mutate_frozen_source, "FROZEN_SOURCE_DRIFT"),
            (
                "unsafe-path-traversal",
                Paths(cases="../../etc/passwd.json"),
                None,
                "UNSAFE_PATH",
            ),
            (
                "unsafe-path-backslash",
                Paths(kit_pass1="prd\\migration\\rust-evidence\\kit.json"),
                None,
                "UNSAFE_PATH",
            ),
            ("unsafe-path-absolute", Paths(fixture_dir="/tmp/npa-lawref"), None, "UNSAFE_PATH"),
            (
                "unfilled-template-submission",
                Paths(submission="prd/migration/rust-evidence/m207-s02-kit-template-probe.json"),
                lambda target: (
                    target / "prd/migration/rust-evidence/m207-s02-kit-template-probe.json"
                ).write_text(template_json + "\n", encoding="utf-8"),
                "UNFILLED_SUBMISSION",
            ),
            (
                "kit-as-submission",
                Paths(submission=KIT_PASS1_REL),
                None,
                "UNFILLED_SUBMISSION",
            ),
        )
        for name, probe_paths, mutate, expected in cases:
            restore_tree(temp_root, baseline_snapshot)
            if mutate is not None:
                mutate(temp_root)
            failures, _ = run_gate("check", temp_root, probe_paths or paths)
            diagnostics = {diagnostic for diagnostic, _ in failures}
            if expected not in diagnostics:
                problems.append(f"{name}: expected {expected}, got {sorted(diagnostics)}")

        # Poisoning a tracked pass-1 kit must not leak into regeneration.
        restore_tree(temp_root, baseline_snapshot)
        mutate_cross_pass(temp_root)
        mutate_forbidden_key(temp_root)
        run_failures, _ = run_gate("run", temp_root, paths)
        if run_failures:
            problems.append(
                f"regeneration-after-poison: run reported {sorted({d for d, _ in run_failures})}"
            )
        for rel, data in baseline.items():
            if (temp_root / rel).read_bytes() != data:
                problems.append(f"regeneration-after-poison: {rel} is not byte-identical")

    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        print(f"FAIL {GATE}: selftest found {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print(SELFTEST_MARKER)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "run", "selftest"],
        help="'check' re-derives both kits read-only; 'run' writes them; "
        "'selftest' additionally proves the hostile paths",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    parser.add_argument("--cases", default=CASES_REL, help="frozen S01 pilot case manifest")
    parser.add_argument(
        "--fixture-dir", default=FIXTURE_DIR_REL, help="frozen fragment fixture dir"
    )
    parser.add_argument("--kit-pass1", default=KIT_PASS1_REL, help="pass-1 kit artifact path")
    parser.add_argument("--kit-pass2", default=KIT_PASS2_REL, help="pass-2 kit artifact path")
    parser.add_argument("--schemas", default=SCHEMAS_REL, help="frozen S02 closed schema path")
    parser.add_argument(
        "--s01-schemas", default=S01_SCHEMAS_REL, help="frozen S01 closed schema path"
    )
    parser.add_argument("--codebook", default=CODEBOOK_REL, help="frozen S01 codebook path")
    parser.add_argument(
        "--seed-manifest", default=SEED_MANIFEST_REL, help="frozen M199 seed manifest"
    )
    parser.add_argument(
        "--submission",
        default=None,
        help="optional candidate submission envelope checked against the frozen form",
    )
    args = parser.parse_args(argv)
    paths = Paths(
        cases=args.cases,
        fixture_dir=args.fixture_dir,
        kit_pass1=args.kit_pass1,
        kit_pass2=args.kit_pass2,
        schemas=args.schemas,
        s01_schemas=args.s01_schemas,
        codebook=args.codebook,
        seed_manifest=args.seed_manifest,
        submission=args.submission,
    )
    root = Path(args.root)
    if args.mode == "selftest":
        return run_selftest(root, paths)
    failures, summary = run_gate(args.mode, root, paths)
    if not failures and args.submission:
        summary = f"{summary} submission_form=ok"
    return report(failures, summary)


if __name__ == "__main__":
    raise SystemExit(main())
