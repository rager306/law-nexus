#!/usr/bin/env python3
"""Offline fail-closed boundary verifier for the M207 S01 annotation pilot (T04).

The three per-task gates (``m207_s01_schemas.py``, ``m207_s01_select_cases.py``,
``m207_s01_prompt_packet.py``) each prove their own artifact.  This verifier
proves the *slice boundary*: that the frozen sources, the pilot artifacts and
the declared lifecycle markers agree, that no predicted answer leaked into any
payload, that the prompt boundary is structurally isolated from the product
crates, and that the pilot claims nothing it did not do.

It deliberately does **not** import the builder modules (no oracle collapse):
the frozen-source pins, the case/packet semantics and the leakage scan are
re-derived here, and the three gates are invoked as real subprocesses on the
same root, whose named diagnostics are re-emitted verbatim.

What it proves, against the frozen sources rather than against prose:

* frozen-source pins -- sha256 of the M199 seed manifest, the M199 protocol,
  the codebook, the closed schemas, the metaprompt contract, the case manifest,
  the prompt packets and the rollup of all 180 frozen fixture ``.txt`` files;
* counters -- 20..40 cases, exactly 180 fixture ``.txt`` files, no new fixture,
  fixture names equal to the seed fragment files, no case drawn twice;
* leakage -- no predicted-answer key or substring at any nesting depth in the
  case manifest, the packets, the schemas or the machine-readable contract
  blocks (``non_claims`` and the forbidden-key declaration lists are exempt,
  because they pin those words by value);
* prompt isolation -- no ``crates/**/*.rs`` and no ``crates/**/Cargo.toml``
  references ``m207-s01``/``m207_s01``/``prd/annotation`` or a pilot packet;
* honesty -- ``selected_d388_gates: none``, the ``G03-G13/G15/G16`` deferred
  set unchanged, ``human_adoption: pending``, ``runtime_stop_active: true``,
  requirement and review dispositions untouched, R035/R070/R074 still active;
* metadata honesty -- no path-derived year/type: ``metadata_source`` is only
  ``validated-manifest`` or ``unknown``, and ``unknown`` implies
  ``year: unknown`` and ``document_type: unknown``;
* no human coding exists anywhere in this slice, and none is required to pass.

Success prints exactly the marker ``M207_S01_PILOT_OK``.  Every failure is a
non-zero exit with a named diagnostic on stderr (``FROZEN_SOURCE_DRIFT``,
``SEED_ENLARGED``, ``CASE_COUNT_OUT_OF_RANGE``, ``LEAK_FORBIDDEN_KEY``,
``PROMPT_ISOLATION_VIOLATION``, ``AUTHORITY_CLAIM``, ``METADATA_PATH_DERIVED``,
``GATE_SELECTION_VIOLATION``, ``LIFECYCLE_MARKER_DRIFT``, ``UNSAFE_PATH``, ...).

``battery`` mode assembles ``prd/migration/rust-evidence/m207-s01-battery.json``
from a tab-separated result table produced by ``scripts/m207_s01_t04_verify.sh``
(``id<TAB>status<TAB>durationMs<TAB>command``) and refuses to accept a table
whose row is missing, malformed, or still failing.  The battery pins the frozen
sources, records ``human_pilot_performed: false`` (S02 performs the pilot) and
never hashes itself.

The battery is **read-only by default**: the freshly assembled payload is
compared byte-for-byte against the tracked JSON and a mismatch fails closed
with ``BATTERY_STALE``, so the closeout chain can run inside the host's
source-integrity window without mutating a tracked file.  ``--write`` (driven
only by ``M207_S01_WRITE_BATTERY=1``) is the single path that touches the
tracked artifact, and it skips the write entirely when the bytes already match.
Wall-clock durations are never persisted -- they are printed to stdout as
``M207_S01_BATTERY_TIMINGS`` so the durable exec log keeps them while the
tracked battery stays a pure function of the observed checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MARKER = "M207_S01_PILOT_OK"
GATE = "M207_S01_PILOT_GATE"
BATTERY_MARKER = "M207_S01_BATTERY_OK"
BATTERY_TIMINGS = "M207_S01_BATTERY_TIMINGS"
BATTERY_SCHEMA = "m207-s01-pilot-battery/v1"

CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
SCHEMAS_REL = "prd/annotation/m207-s01-schemas.json"
METAPROMPT_REL = "prd/annotation/m207-s01-metaprompt.md"
CASES_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
PACKETS_REL = "prd/migration/rust-evidence/m207-s01-prompt-packets.jsonl"
SEED_REL = "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json"
M199_PROTOCOL_REL = "prd/migration/rust-evidence/m199-s01-annotation-protocol.md"
METADATA_REL = "prd/migration/rust-evidence/m204-s02-c5-gold-manifest-400.json"
FIXTURE_DIR_REL = "crates/ln-decode/tests/fixtures/npa-lawref"
REQUIREMENTS_REL = "prd/REQUIREMENTS.md"
D388_ADMISSION_REL = "prd/architecture/m206-s07-runtime-admission.md"
REVIEW_PROGRAM_REL = "prd/architecture/review-cases/rc28-remediation-program.md"
BATTERY_REL = "prd/migration/rust-evidence/m207-s01-battery.json"

# Frozen-source pins: content sha256, never a git revision.
PINS: dict[str, tuple[str, str]] = {
    "codebook": (CODEBOOK_REL, "1a1bfe944207e69cb5fb507e94d680384dadecf7ac98ac29b1de4932d7cb76c6"),
    "schemas": (SCHEMAS_REL, "63a4bc6629bade752f9fa02d1dd5fa6bbf21238e20772d2ba5b74f88ecca3682"),
    "metaprompt": (
        METAPROMPT_REL,
        "d09d09fe9189a7f76b02f715eefa6ebd0c16a3b71ef7ff4b88f5f380af68a999",
    ),
    "seed_manifest": (
        SEED_REL,
        "134751f49db1858329248be1857ada669097f1860609090028c7b5af8975574f",
    ),
    "m199_protocol": (
        M199_PROTOCOL_REL,
        "eed922b02c1b89b8e51e8b342b1a9f113a8029b8a2fe0a1bee84f9f2035c6e3d",
    ),
    "cases": (CASES_REL, "9b0b6bc6bd8eadf9eb86886e45eb756ebade654e96ac3a84132ed9452bdeb9ad"),
    "packets": (PACKETS_REL, "d9d30bf24d40ab8abebb28c1a22692ae99ca029e1b4e2b032a4dae1137cc6b77"),
}
FIXTURE_ROLLUP_SHA256 = "50b48668cba5b89d75af0604a78004404310e36377679984273fa0a883053c9d"

SEED_SCHEMA = "npa-lawref-sample/v1"
SEED_DOCUMENT_COUNT = 40
SEED_FRAGMENT_COUNT = 180
FIXTURE_TXT_COUNT = 180
FIXTURE_ALLOWED_ENTRIES = frozenset({"lawref_seed.json"})
CASE_COUNT_RANGE = (20, 40)
WORK_FAMILY_CAP = 4
UNKNOWN = "unknown"
METADATA_SOURCES = ("validated-manifest", UNKNOWN)
CASE_PREFIX = "m207-s01-case-"
PACKET_PREFIX = "m207-s01-packet-"

M199_SLOT_SPACE = (
    "marker_chain",
    "hier_nums",
    "date",
    "doc_no",
    "law_code",
    "anaphora",
    "range",
    "quoted_enum",
)
DECISION_VALUES = ("reference", "not_a_reference")
ABSTENTION_VALUES = ("not-abstained", "ambiguous", "insufficient-context")
ALTERNATIVE_AXES = (
    ("reference_decision", ("reference", "not_a_reference")),
    ("slot_presence", ("slot_present", "slot_absent")),
    ("scope", ("scope_local", "scope_inherited")),
    ("binding", ("binding_explicit", "binding_unresolved")),
)
NON_CLAIMS = (
    "not official-publication provenance (R070 stays open)",
    "not amendment provenance (R070 stays open)",
    "not LawRef / act-tree / clause segmentation",
    "not the N2-gate acceptance decision",
    "not legal interpretation",
    "not gold: no S01 span or slot is a gold label",
    "not a human pilot: S01 performs no coding and reports no agreement",
    "not product authority: prompt output is AnnotationSuggestion only",
)
LIFECYCLE = {
    "human_adoption": "pending",
    "runtime_stop_active": True,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged",
}
OUTPUT_CONTRACT = {
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": False,
}
CASE_CLOSED_KEYS = (
    "case_id",
    "fragment_id",
    "doc_id",
    "source_path",
    "source_sha256",
    "byte_len",
    "source_block_index",
    "start",
    "end",
    "alternative_classes",
    "abstention_available",
    "span_offered_for_coding",
    "metadata_source",
    "year",
    "document_type",
    "draw_stratum",
    "work_family",
)
PACKET_CLOSED_KEYS = (
    "packet_id",
    "case_id",
    "codebook_ref",
    "source_anchor",
    "fragment_text",
    "span",
    "alternative_classes",
    "decision_space",
    "output_type",
    "authority",
    "suggestion_status",
    "model_invoked",
    "non_claims",
)
ANCHOR_CLOSED_KEYS = ("doc_path", "source_sha256", "block_index", "byte_len")
SPAN_CLOSED_KEYS = ("start", "end")

# Token set kept deliberately narrow and identical in spirit to the T01/T03
# gates: ``span``/``seed`` alone are legitimate field-name tokens
# (``span_closed_keys``, ``draw_seed``), so they are matched only by exact name.
FORBIDDEN_KEY_TOKENS = frozenset(
    {
        "label",
        "labels",
        "expected",
        "answer",
        "answers",
        "prediction",
        "predictions",
        "predicted",
        "gold",
        "golden",
        "capture",
        "captures",
    }
)
FORBIDDEN_EXACT_KEYS = frozenset(
    {
        "seed_span",
        "rule_seed_span",
        "rule_seed",
        "ds_span",
        "seed_slots",
    }
)
# Substrings that would carry a predicted answer wherever they appear: the
# case manifest, the packets, the closed schemas and the machine-readable
# contract blocks.
ANSWER_SUBSTRINGS = (
    "label",
    "expected",
    "answer",
    "prediction",
    "predicted",
    "gold",
    "capture",
    "rule_seed",
    "seed_span",
    "ds_span",
    "lawref_seed",
    "crates/",
    "AnnotationSuggestion:",
)
# Coder-provenance substrings.  The frozen schemas legitimately *declare* these
# as S02 coder-submission field names (and the codebook names the S02
# adjudication boundary), so they only constitute a leak where a model-facing
# packet carries them.
PROVENANCE_SUBSTRINGS = ("coder_id", "coder_pass", "submission_id", "adjudicat")
FORBIDDEN_SUBSTRINGS = ANSWER_SUBSTRINGS + PROVENANCE_SUBSTRINGS
EXEMPT_KEY_LISTS = frozenset({"forbidden_keys", "forbidden_seed_keys"})
# Pinned by value, so their own deny-list wording is not itself a leak.
EXEMPT_KEYS = EXEMPT_KEY_LISTS | frozenset({"non_claims", "forbidden_substrings"})

ISOLATION_TOKENS = (
    "m207-s01",
    "m207_s01",
    "prd/annotation",
    "m207-s01-prompt-packets",
    "m207-s01-pilot-cases",
    "m207-s01-codebook",
    "m207-s01-metaprompt",
)
ISOLATION_SKIP_PARTS = frozenset({"target", ".git", "node_modules", "__pycache__", ".venv"})
ISOLATION_MAX_BYTES = 4 * 1024 * 1024

D388_DEFERRED = frozenset(
    ["G03", "G04", "G05", "G06", "G07", "G08", "G09", "G10", "G11", "G12", "G13", "G15", "G16"]
)
D388_ADMISSION_SELECTED = frozenset({"G01", "G02", "G14"})
GATE_TOKEN_RE = re.compile(r"\bG\d{2}\b")
PROMOTION_RE = re.compile(
    r"R0(?:35|70|74)[^.\n]{0,60}\b(?:closed|validated|promoted|complete|accepted)\b",
    re.IGNORECASE,
)
FENCE_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
GATE_DIAGNOSTIC_RE = re.compile(r"FAIL ([A-Z][A-Z0-9_]+):")
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
TOKEN_SEPARATOR_RE = re.compile(r"[^A-Za-z0-9]+")
HUMAN_INPUT_TOKENS = ("coder", "submission_id", "adjudicat")

SUBCLIS: tuple[tuple[str, str, str], ...] = (
    ("schemas", "scripts/m207_s01_schemas.py", "M207_S01_SCHEMAS_OK"),
    ("select_cases", "scripts/m207_s01_select_cases.py", "M207_S01_SELECT_CASES_OK"),
    ("prompt_packet", "scripts/m207_s01_prompt_packet.py", "M207_S01_PROMPT_PACKET_OK"),
)

ARTIFACT_SPECS: tuple[tuple[str, str, str, str, str], ...] = (
    ("codebook", "codebook", CODEBOOK_REL, ".md", "prd/annotation/"),
    ("schemas", "schemas", SCHEMAS_REL, ".json", "prd/annotation/"),
    ("metaprompt", "metaprompt", METAPROMPT_REL, ".md", "prd/annotation/"),
    ("cases", "cases", CASES_REL, ".json", "prd/migration/rust-evidence/"),
    ("packets", "packets", PACKETS_REL, ".jsonl", "prd/migration/rust-evidence/"),
    ("seed_manifest", "seed manifest", SEED_REL, ".json", "prd/migration/rust-evidence/"),
    (
        "m199_protocol",
        "M199 protocol",
        M199_PROTOCOL_REL,
        ".md",
        "prd/migration/rust-evidence/",
    ),
    (
        "metadata_manifest",
        "metadata manifest",
        METADATA_REL,
        ".json",
        "prd/migration/rust-evidence/",
    ),
    ("fixture_dir", "fixture dir", FIXTURE_DIR_REL, "", "crates/ln-decode/tests/fixtures/"),
    ("requirements", "requirements projection", REQUIREMENTS_REL, ".md", "prd/"),
    ("d388_admission", "D388 admission", D388_ADMISSION_REL, ".md", "prd/architecture/"),
    ("review_program", "review program", REVIEW_PROGRAM_REL, ".md", "prd/architecture/"),
)

Failures = list[tuple[str, str]]


class VerificationError(Exception):
    """A fail-closed condition carrying a named diagnostic."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_artifact(
    root: Path, raw: str, label: str, *, suffix: str, prefix: str, directory: bool = False
) -> Path:
    """Resolve a repository-relative artifact path, fail-closed on escapes."""
    if (
        not raw
        or "\x00" in raw
        or raw.startswith("/")
        or "\\" in raw
        or (len(raw) > 1 and raw[1] == ":")
    ):
        raise VerificationError("UNSAFE_PATH", f"{label}={raw!r} must be a POSIX relative path")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise VerificationError("UNSAFE_PATH", f"{label}={raw!r} may not escape the repository")
    if not directory and suffix and relative.suffix != suffix:
        raise VerificationError("UNSAFE_PATH", f"{label}={raw!r} must have suffix {suffix}")
    if prefix and not relative.as_posix().startswith(prefix):
        raise VerificationError("UNSAFE_PATH", f"{label}={raw!r} must live under {prefix}")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    if not candidate.is_relative_to(root_resolved):
        raise VerificationError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_resolved}")
    return candidate


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise VerificationError("DUPLICATE_JSON_KEY", f"duplicate object key {key!r}")
        seen[key] = value
    return seen


def read_text(path: Path, label: str) -> str:
    if not path.is_file():
        raise VerificationError("MISSING_ARTIFACT", f"{label} not found at {path}")
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError("SCHEMA_PARSE_ERROR", f"{label} is not UTF-8: {exc}") from exc


def load_json(path: Path, label: str) -> Any:
    text = read_text(path, label)
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except VerificationError:
        raise
    except json.JSONDecodeError as exc:
        raise VerificationError("SCHEMA_PARSE_ERROR", f"{label} is not closed JSON: {exc}") from exc


def load_jsonl(path: Path, label: str) -> list[Any]:
    text = read_text(path, label)
    rows: list[Any] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line, object_pairs_hook=_reject_duplicate_keys))
        except VerificationError:
            raise
        except json.JSONDecodeError as exc:
            raise VerificationError(
                "SCHEMA_PARSE_ERROR", f"{label} line {number} is not closed JSON: {exc}"
            ) from exc
    return rows


def fenced_contracts(path: Path, label: str) -> list[Any]:
    """Parse every fenced ``json`` block of a markdown artifact."""
    blocks: list[Any] = []
    for index, block in enumerate(FENCE_RE.findall(read_text(path, label))):
        try:
            blocks.append(json.loads(block, object_pairs_hook=_reject_duplicate_keys))
        except VerificationError:
            raise
        except json.JSONDecodeError as exc:
            raise VerificationError(
                "SCHEMA_PARSE_ERROR", f"{label} fenced block {index} is not closed JSON: {exc}"
            ) from exc
    return blocks


def key_tokens(key: str) -> list[str]:
    return [token for token in TOKEN_SEPARATOR_RE.split(CAMEL_BOUNDARY_RE.sub("_", key)) if token]


def forbidden_key_hit(name: str) -> str | None:
    if set(key_tokens(name)) & FORBIDDEN_KEY_TOKENS:
        return "predicted-answer"
    if name.strip().lower() in FORBIDDEN_EXACT_KEYS:
        return "rule-seed-span"
    return None


def scan_payload(
    node: Any,
    pointer: str,
    failures: Failures,
    *,
    deny_list: bool = False,
    key_list: bool = False,
    needles: tuple[str, ...] = ANSWER_SUBSTRINGS,
) -> None:
    """Reject predicted-answer keys and substrings at any nesting depth.

    ``deny_list`` marks a value-pinned declaration (``non_claims``, the
    ``forbidden_*`` lists): its own wording enumerates forbidden words, so it is
    exempt.  ``key_list`` marks a ``*_keys`` list whose string elements are
    field names, so they are matched as names.  ``needles`` selects the
    substring family: answer carriers everywhere, coder provenance only in the
    model-facing packets.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            name = str(key)
            if not deny_list and name not in EXEMPT_KEY_LISTS:
                hit = forbidden_key_hit(name)
                if hit:
                    _fail(
                        failures,
                        "LEAK_FORBIDDEN_KEY",
                        f"{pointer}/{key} is a forbidden {hit} field",
                    )
            scan_payload(
                value,
                f"{pointer}/{key}",
                failures,
                deny_list=deny_list or name in EXEMPT_KEYS,
                key_list=name.endswith("_keys") and name not in EXEMPT_KEY_LISTS,
                needles=needles,
            )
    elif isinstance(node, list):
        for index, value in enumerate(node):
            if key_list and not deny_list and isinstance(value, str):
                hit = forbidden_key_hit(value)
                if hit:
                    _fail(
                        failures,
                        "LEAK_FORBIDDEN_KEY",
                        f"{pointer}[{index}] declares {value!r}, a forbidden {hit} field",
                    )
            scan_payload(
                value, f"{pointer}[{index}]", failures, deny_list=deny_list, needles=needles
            )
    elif isinstance(node, str) and not deny_list:
        for needle in needles:
            if needle in node:
                _fail(
                    failures,
                    "LEAK_FORBIDDEN_SUBSTRING",
                    f"{pointer} contains forbidden substring {needle!r}",
                )
                return


def check_frozen_pins(artifacts: dict[str, Path | None], failures: Failures) -> int:
    pinned = 0
    for name, (rel, pin) in PINS.items():
        path = artifacts.get(name)
        if path is None:
            continue
        if not path.is_file():
            _fail(failures, "MISSING_ARTIFACT", f"{rel} not found at {path}")
            continue
        digest = sha256_file(path)
        if digest != pin:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"{rel} sha256 {digest} != pinned {pin}",
            )
        else:
            pinned += 1
    return pinned


def seed_indexes(seed: Any, failures: Failures) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(seed, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "M199 seed manifest is not a JSON object")
        return {}, {}
    if seed.get("schema") != SEED_SCHEMA:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"M199 seed schema {seed.get('schema')!r} != {SEED_SCHEMA!r}",
        )
    documents = seed.get("documents")
    fragments = seed.get("fragments")
    docs = (
        [entry for entry in documents if isinstance(entry, dict)]
        if isinstance(documents, list)
        else []
    )
    frags = (
        [entry for entry in fragments if isinstance(entry, dict)]
        if isinstance(fragments, list)
        else []
    )
    if len(docs) != SEED_DOCUMENT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"M199 seed declares {len(docs)} documents, expected {SEED_DOCUMENT_COUNT}",
        )
    if len(frags) != SEED_FRAGMENT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"M199 seed declares {len(frags)} fragments, expected {SEED_FRAGMENT_COUNT}",
        )
    return {doc["doc_id"]: doc for doc in docs}, {frag["id"]: frag for frag in frags}


def check_counters(
    artifacts: dict[str, Path | None],
    frag_by_id: dict[str, Any],
    cases: Any,
    failures: Failures,
) -> tuple[int, int, str]:
    fixture_dir = artifacts.get("fixture_dir")
    fixture_txt = 0
    rollup = ""
    if fixture_dir is None:
        return 0, 0, rollup
    if not fixture_dir.is_dir():
        _fail(failures, "MISSING_ARTIFACT", f"fixture dir not found at {fixture_dir}")
        return 0, 0, rollup
    entries = sorted(fixture_dir.iterdir())
    stray_dirs = [entry.name for entry in entries if entry.is_dir()]
    if stray_dirs:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"fixture dir gained directorie(s): {stray_dirs[:3]}",
        )
    txt = [entry for entry in entries if entry.is_file() and entry.suffix == ".txt"]
    extra = [
        entry.name
        for entry in entries
        if entry.is_file() and entry.suffix != ".txt" and entry.name not in FIXTURE_ALLOWED_ENTRIES
    ]
    if extra:
        _fail(failures, "SEED_ENLARGED", f"new non-fragment fixture file(s): {extra[:3]}")
    fixture_txt = len(txt)
    if fixture_txt != FIXTURE_TXT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"fixture dir holds {fixture_txt} .txt file(s), expected {FIXTURE_TXT_COUNT}",
        )
    declared = {fragment.get("file") for fragment in frag_by_id.values()}
    present = {entry.name for entry in txt}
    if declared - present:
        _fail(
            failures,
            "MISSING_ARTIFACT",
            f"{len(declared - present)} seed fragment file(s) missing, e.g. {sorted(declared - present)[0]}",
        )
    if present - declared:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"{len(present - declared)} fixture .txt file(s) are not in the seed, e.g. "
            f"{sorted(present - declared)[0]}",
        )
    digest = hashlib.sha256()
    for entry in txt:
        digest.update(entry.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(entry).encode("utf-8"))
        digest.update(b"\n")
    rollup = digest.hexdigest()
    if rollup != FIXTURE_ROLLUP_SHA256:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"fixture rollup {rollup} != pinned {FIXTURE_ROLLUP_SHA256}",
        )
    case_count = 0
    if isinstance(cases, dict) and isinstance(cases.get("cases"), list):
        case_count = len(cases["cases"])
    return fixture_txt, case_count, rollup


def check_cases(
    cases: Any,
    doc_by_id: dict[str, Any],
    frag_by_id: dict[str, Any],
    failures: Failures,
) -> tuple[int, int]:
    if not isinstance(cases, dict) or not isinstance(cases.get("cases"), list):
        _fail(failures, "SCHEMA_PARSE_ERROR", "case manifest has no 'cases' list")
        return 0, 0
    rows = cases["cases"]
    count = len(rows)
    low, high = CASE_COUNT_RANGE
    if not low <= count <= high:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"case manifest holds {count} case(s), expected {low}..{high}",
        )
    if cases.get("case_count") != count:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"case_count {cases.get('case_count')!r} != len(cases) {count}",
        )
    seen_fragments: set[str] = set()
    families: dict[str, int] = {}
    validated = 0
    for index, case in enumerate(rows):
        pointer = f"cases[{index}]"
        if not isinstance(case, dict):
            _fail(failures, "SCHEMA_PARSE_ERROR", f"{pointer} is not a JSON object")
            continue
        if set(case) != set(CASE_CLOSED_KEYS):
            _fail(
                failures,
                "CASE_SCHEMA_DRIFT",
                f"{pointer} keys {sorted(set(case) ^ set(CASE_CLOSED_KEYS))} differ from the closed set",
            )
            continue
        if case["case_id"] != f"{CASE_PREFIX}{index + 1:03d}":
            _fail(
                failures, "CASE_ORDER_DRIFT", f"{pointer} case_id {case['case_id']!r} out of order"
            )
        fragment = frag_by_id.get(case["fragment_id"])
        if fragment is None:
            _fail(
                failures,
                "UNKNOWN_FRAGMENT",
                f"{pointer} fragment {case['fragment_id']!r} is not in the seed",
            )
            continue
        if case["fragment_id"] in seen_fragments:
            _fail(failures, "DUPLICATE_CASE", f"{pointer} reuses fragment {case['fragment_id']!r}")
        seen_fragments.add(case["fragment_id"])
        document = doc_by_id.get(fragment.get("doc_id"))
        if document is None:
            _fail(failures, "UNKNOWN_FRAGMENT", f"{pointer} fragment has no seed document")
            continue
        for field, expected in (
            ("doc_id", document.get("doc_id")),
            ("source_path", document.get("source_path")),
            ("source_sha256", document.get("source_sha256")),
            ("byte_len", fragment.get("byte_len")),
            ("source_block_index", fragment.get("source_block_index")),
        ):
            if case[field] != expected:
                _fail(
                    failures,
                    "FROZEN_SOURCE_DRIFT",
                    f"{pointer}.{field} {case[field]!r} != seed {expected!r}",
                )
        if case["start"] != 0 or case["end"] != case["byte_len"]:
            _fail(
                failures,
                "SPAN_OUT_OF_BOUNDS",
                f"{pointer} span ({case['start']}, {case['end']}) is not the full fragment",
            )
        if case["abstention_available"] is not True:
            _fail(failures, "ABSTENTION_COLLAPSE", f"{pointer} abstention_available is not true")
        if case["span_offered_for_coding"] is not True:
            _fail(failures, "OFFER_FLAG_DRIFT", f"{pointer} span_offered_for_coding is not true")
        expected_axes = [
            {"axis": axis, "values": list(values)} for axis, values in ALTERNATIVE_AXES
        ]
        if case["alternative_classes"] != expected_axes:
            _fail(
                failures,
                "ALTERNATIVES_DRIFT",
                f"{pointer}.alternative_classes drifted from the closed codebook axes",
            )
        source = case["metadata_source"]
        if source not in METADATA_SOURCES:
            _fail(
                failures,
                "METADATA_PATH_DERIVED",
                f"{pointer}.metadata_source {source!r} is not one of {list(METADATA_SOURCES)}",
            )
        elif source == UNKNOWN:
            for field in ("year", "document_type"):
                if case[field] != UNKNOWN:
                    _fail(
                        failures,
                        "METADATA_PATH_DERIVED",
                        f"{pointer}.{field} {case[field]!r} without validated provenance",
                    )
        else:
            validated += 1
            for field in ("year", "document_type"):
                if case[field] == UNKNOWN:
                    _fail(
                        failures,
                        "METADATA_SOURCE_UNVALIDATED",
                        f"{pointer}.{field} unknown despite validated-manifest provenance",
                    )
        if not isinstance(case["draw_stratum"], str) or not case["draw_stratum"]:
            _fail(failures, "STRATUM_DRIFT", f"{pointer}.draw_stratum is empty")
        family = case["work_family"]
        if not isinstance(family, str) or not family:
            _fail(failures, "WORK_FAMILY_DRIFT", f"{pointer}.work_family is empty")
        else:
            families[family] = families.get(family, 0) + 1
    for family, weight in sorted(families.items()):
        if weight > WORK_FAMILY_CAP:
            _fail(
                failures,
                "WORK_FAMILY_DOMINANCE",
                f"work family {family!r} contributes {weight} cases, cap is {WORK_FAMILY_CAP}",
            )
    return count, validated


def check_packets(
    packets: list[Any] | None,
    cases: Any,
    fixture_dir: Path | None,
    frag_by_id: dict[str, Any],
    failures: Failures,
) -> int:
    if packets is None:
        return 0
    case_rows = (
        cases["cases"] if isinstance(cases, dict) and isinstance(cases.get("cases"), list) else []
    )
    if len(packets) != len(case_rows):
        _fail(
            failures,
            "PACKET_COUNT_MISMATCH",
            f"{len(packets)} packet(s) for {len(case_rows)} case(s)",
        )
    for index, packet in enumerate(packets):
        pointer = f"packets[{index}]"
        if not isinstance(packet, dict):
            _fail(failures, "SCHEMA_PARSE_ERROR", f"{pointer} is not a JSON object")
            continue
        if set(packet) != set(PACKET_CLOSED_KEYS):
            _fail(
                failures,
                "PACKET_KEY_DRIFT",
                f"{pointer} keys {sorted(set(packet) ^ set(PACKET_CLOSED_KEYS))} differ from the closed set",
            )
            continue
        if packet["packet_id"] != f"{PACKET_PREFIX}{index + 1:03d}":
            _fail(failures, "PACKET_ORDER_DRIFT", f"{pointer} packet_id out of order")
        if packet["codebook_ref"] != CODEBOOK_REL:
            _fail(
                failures, "PACKET_KEY_DRIFT", f"{pointer}.codebook_ref drifted from {CODEBOOK_REL}"
            )
        for field, expected in OUTPUT_CONTRACT.items():
            if packet[field] != expected:
                _fail(
                    failures,
                    "AUTHORITY_CLAIM",
                    f"{pointer}.{field} {packet[field]!r} != {expected!r}",
                )
        if packet["non_claims"] != list(NON_CLAIMS):
            _fail(
                failures, "MISSING_NON_CLAIM", f"{pointer}.non_claims drifted from the codebook set"
            )
        anchor = packet["source_anchor"]
        if not isinstance(anchor, dict) or set(anchor) != set(ANCHOR_CLOSED_KEYS):
            _fail(
                failures, "ANCHOR_DRIFT", f"{pointer}.source_anchor is not the closed anchor shape"
            )
        span = packet["span"]
        if not isinstance(span, dict) or set(span) != set(SPAN_CLOSED_KEYS):
            _fail(failures, "SPAN_OUT_OF_BOUNDS", f"{pointer}.span is not the closed span shape")
        decision = packet["decision_space"]
        expected_decision = {
            "decision_values": list(DECISION_VALUES),
            "slot_space": list(M199_SLOT_SPACE),
            "abstention_values": list(ABSTENTION_VALUES),
        }
        if decision != expected_decision:
            _fail(
                failures,
                "NINTH_SLOT",
                f"{pointer}.decision_space drifted from the M199 section-5 slot space",
            )
        if index >= len(case_rows) or not isinstance(case_rows[index], dict):
            continue
        case = case_rows[index]
        if packet["case_id"] != case.get("case_id"):
            _fail(failures, "PACKET_ORDER_DRIFT", f"{pointer}.case_id does not match case order")
        if packet["alternative_classes"] != case.get("alternative_classes"):
            _fail(failures, "ALTERNATIVES_DRIFT", f"{pointer}.alternative_classes != case axes")
        if isinstance(anchor, dict) and set(anchor) == set(ANCHOR_CLOSED_KEYS):
            for field, expected in (
                ("doc_path", case.get("source_path")),
                ("source_sha256", case.get("source_sha256")),
                ("block_index", case.get("source_block_index")),
                ("byte_len", case.get("byte_len")),
            ):
                if anchor[field] != expected:
                    _fail(
                        failures,
                        "ANCHOR_DRIFT",
                        f"{pointer}.source_anchor.{field} {anchor[field]!r} != case {expected!r}",
                    )
        if isinstance(span, dict) and set(span) == set(SPAN_CLOSED_KEYS):
            if span["start"] != 0 or span["end"] != case.get("byte_len"):
                _fail(
                    failures,
                    "SPAN_OUT_OF_BOUNDS",
                    f"{pointer}.span is not the full frozen fragment",
                )
        fragment = frag_by_id.get(case.get("fragment_id"))
        if fragment is None or fixture_dir is None:
            continue
        fixture = fixture_dir / fragment["file"]
        if not fixture.is_file():
            _fail(failures, "MISSING_ARTIFACT", f"{pointer} fragment file missing at {fixture}")
            continue
        raw = fixture.read_bytes()
        text = packet["fragment_text"]
        if not isinstance(text, str) or text.encode("utf-8") != raw:
            _fail(
                failures,
                "FRAGMENT_TEXT_DRIFT",
                f"{pointer}.fragment_text is not the frozen decoded block of {fragment['file']}",
            )
    return len(packets)


def check_leakage(
    artifacts: dict[str, Path | None],
    cases: Any,
    packets: list[Any] | None,
    failures: Failures,
) -> int:
    before = sum(1 for diagnostic, _ in failures if diagnostic.startswith("LEAK_"))
    if cases is not None:
        scan_payload(cases, "cases", failures)
    if packets is not None:
        scan_payload(packets, "packets", failures, needles=FORBIDDEN_SUBSTRINGS)
    schemas = artifacts.get("schemas")
    if schemas is not None and schemas.is_file():
        try:
            scan_payload(load_json(schemas, "closed schemas"), "schemas", failures)
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    for name in ("codebook", "metaprompt"):
        path = artifacts.get(name)
        if path is None or not path.is_file():
            continue
        try:
            for index, block in enumerate(fenced_contracts(path, name)):
                scan_payload(block, f"{name}[fence {index}]", failures)
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    after = sum(1 for diagnostic, _ in failures if diagnostic.startswith("LEAK_"))
    return after - before


def check_prompt_isolation(root: Path, failures: Failures) -> int:
    crates = root / "crates"
    if not crates.is_dir():
        return 0
    scanned = 0
    for path in sorted(crates.rglob("*")):
        if not path.is_file():
            continue
        if ISOLATION_SKIP_PARTS.intersection(path.parts):
            continue
        if path.suffix != ".rs" and path.name != "Cargo.toml":
            continue
        try:
            if path.stat().st_size > ISOLATION_MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _fail(failures, "MISSING_ARTIFACT", f"cannot read {path}: {exc}")
            continue
        scanned += 1
        for token in ISOLATION_TOKENS:
            if token in text:
                _fail(
                    failures,
                    "PROMPT_ISOLATION_VIOLATION",
                    f"{path.relative_to(root)} references pilot artifact token {token!r}",
                )
                break
    return scanned


def check_lifecycle(
    artifacts: dict[str, Path | None],
    cases: Any,
    failures: Failures,
) -> int:
    blocks: list[tuple[str, Any]] = []
    for name in ("codebook", "metaprompt"):
        path = artifacts.get(name)
        if path is None or not path.is_file():
            continue
        try:
            for index, block in enumerate(fenced_contracts(path, name)):
                blocks.append((f"{name}[fence {index}]", block))
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    schemas = artifacts.get("schemas")
    if schemas is not None and schemas.is_file():
        try:
            blocks.append(("schemas", load_json(schemas, "closed schemas")))
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    if isinstance(cases, dict):
        blocks.append(("cases", cases))
    observed = 0
    for label, block in blocks:
        if not isinstance(block, dict) or "lifecycle" not in block:
            _fail(
                failures,
                "LIFECYCLE_MARKER_DRIFT",
                f"{label} carries no lifecycle marker block",
            )
            continue
        lifecycle = block["lifecycle"]
        if not isinstance(lifecycle, dict) or set(lifecycle) != set(LIFECYCLE):
            _fail(
                failures,
                "LIFECYCLE_MARKER_DRIFT",
                f"{label}.lifecycle keys {sorted(lifecycle) if isinstance(lifecycle, dict) else lifecycle!r} "
                f"differ from {sorted(LIFECYCLE)}",
            )
            continue
        observed += 1
        for marker, expected in LIFECYCLE.items():
            if lifecycle[marker] != expected:
                diagnostic = (
                    "GATE_SELECTION_VIOLATION"
                    if marker == "selected_d388_gates"
                    else "LIFECYCLE_MARKER_DRIFT"
                )
                _fail(
                    failures,
                    diagnostic,
                    f"{label}.lifecycle.{marker} {lifecycle[marker]!r} != {expected!r}",
                )
    return observed


def check_d388(artifacts: dict[str, Path | None], failures: Failures) -> int:
    admission = artifacts.get("d388_admission")
    if admission is None or not admission.is_file():
        return 0
    try:
        text = read_text(admission, "D388 admission")
    except VerificationError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return 0
    deferred: set[str] = set()
    selected: set[str] = set()
    for line in text.splitlines():
        if "deferred_d388_gates" in line:
            deferred |= set(GATE_TOKEN_RE.findall(line))
        elif "selected_d388_gates" in line:
            selected |= set(GATE_TOKEN_RE.findall(line))
    if deferred != set(D388_DEFERRED):
        _fail(
            failures,
            "GATE_SELECTION_VIOLATION",
            f"deferred D388 set {sorted(deferred)} != {sorted(D388_DEFERRED)}",
        )
    if selected != set(D388_ADMISSION_SELECTED):
        _fail(
            failures,
            "GATE_SELECTION_VIOLATION",
            f"admission selects {sorted(selected)}, expected {sorted(D388_ADMISSION_SELECTED)}",
        )
    if deferred & selected:
        _fail(
            failures,
            "GATE_SELECTION_VIOLATION",
            f"gate(s) both deferred and selected: {sorted(deferred & selected)}",
        )
    return len(deferred)


def check_requirements(artifacts: dict[str, Path | None], failures: Failures) -> int:
    projection = artifacts.get("requirements")
    if projection is None or not projection.is_file():
        return 0
    try:
        text = read_text(projection, "requirements projection")
    except VerificationError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return 0
    observed = 0
    for token in ("R035", "R070", "R074"):
        row = next(
            (line for line in text.splitlines() if line.startswith("|") and token in line),
            None,
        )
        if row is None or "active" not in row:
            _fail(
                failures,
                "REQUIREMENT_PROMOTION",
                f"{token} is no longer a tracked active guardrail in the requirements projection",
            )
        else:
            observed += 1
    return observed


def check_review_disposition(artifacts: dict[str, Path | None], failures: Failures) -> int:
    program = artifacts.get("review_program")
    if program is None or not program.is_file():
        return 0
    try:
        text = read_text(program, "review program")
    except VerificationError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return 0
    row = next((line for line in text.splitlines() if "M207-b2i96m" in line), None)
    if row is None or "F01-F03" not in row or "F14-F15" not in row:
        _fail(
            failures,
            "REVIEW_DISPOSITION_PROMOTION",
            "the review program no longer maps M207-b2i96m to F01-F03/F14-F15",
        )
        return 0
    return 1


def check_no_human_inputs(artifacts: dict[str, Path | None], failures: Failures) -> int:
    """No human coding exists in this slice, and none may be required to pass."""
    hits = 0
    for name, path in artifacts.items():
        if path is None:
            continue
        lowered = str(path).lower()
        for token in HUMAN_INPUT_TOKENS:
            if token in lowered:
                hits += 1
                _fail(
                    failures,
                    "MISSING_ARTIFACT",
                    f"verifier depends on a human-coding artifact ({name}={path})",
                )
    return hits


def check_promotions(artifacts: dict[str, Path | None], failures: Failures) -> int:
    scanned = 0
    for name in ("codebook", "metaprompt", "schemas"):
        path = artifacts.get(name)
        if path is None or not path.is_file():
            continue
        try:
            text = read_text(path, name)
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        scanned += 1
        for match in PROMOTION_RE.findall(text):
            _fail(
                failures,
                "REQUIREMENT_PROMOTION",
                f"{name} claims a guardrail promotion: {match!r}",
            )
    return scanned


def run_subclis(root: Path, failures: Failures) -> tuple[int, list[dict[str, Any]]]:
    passed = 0
    rows: list[dict[str, Any]] = []
    for name, relative, marker in SUBCLIS:
        command = [sys.executable, str(ROOT / relative), "check", "--root", str(root)]
        try:
            completed = subprocess.run(
                command, cwd=str(ROOT), text=True, capture_output=True, timeout=180, check=False
            )
        except subprocess.TimeoutExpired:
            _fail(failures, "SUBCLI_TIMEOUT", f"{relative} timed out after 180s")
            rows.append({"name": name, "status": None, "marker": marker})
            continue
        except OSError as exc:
            _fail(failures, "SUBCLI_FAILURE", f"{relative} could not be spawned: {exc}")
            rows.append({"name": name, "status": None, "marker": marker})
            continue
        rows.append({"name": name, "status": completed.returncode, "marker": marker})
        if completed.returncode == 0:
            if marker not in completed.stdout:
                _fail(
                    failures,
                    "SUBCLI_FAILURE",
                    f"{relative} exited 0 without the {marker} marker",
                )
            else:
                passed += 1
            continue
        diagnostics = GATE_DIAGNOSTIC_RE.findall(completed.stderr)
        if diagnostics:
            seen: set[str] = set()
            for diagnostic in diagnostics:
                if diagnostic in seen:
                    continue
                seen.add(diagnostic)
                _fail(failures, diagnostic, f"{relative} reported {diagnostic}")
        else:
            _fail(
                failures,
                "SUBCLI_FAILURE",
                f"{relative} exited {completed.returncode} without a named diagnostic",
            )
    return passed, rows


def run(root: Path, args: argparse.Namespace) -> tuple[Failures, str, dict[str, Any]]:
    failures: Failures = []
    artifacts: dict[str, Path | None] = {}
    for name, label, default, suffix, prefix in ARTIFACT_SPECS:
        raw = getattr(args, name.replace("-", "_"), default)
        try:
            artifacts[name] = resolve_artifact(
                root,
                raw,
                label,
                suffix=suffix,
                prefix=prefix,
                directory=(name == "fixture_dir"),
            )
        except VerificationError as exc:
            artifacts[name] = None
            _fail(failures, exc.diagnostic, exc.detail)

    pinned = check_frozen_pins(artifacts, failures)

    seed: Any = None
    seed_path = artifacts.get("seed_manifest")
    if seed_path is not None and seed_path.is_file():
        try:
            seed = load_json(seed_path, "M199 seed manifest")
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    cases: Any = None
    cases_path = artifacts.get("cases")
    if cases_path is not None and cases_path.is_file():
        try:
            cases = load_json(cases_path, "case manifest")
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    packets: list[Any] | None = None
    packets_path = artifacts.get("packets")
    if packets_path is not None and packets_path.is_file():
        try:
            packets = load_jsonl(packets_path, "prompt packets")
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    doc_by_id: dict[str, Any] = {}
    frag_by_id: dict[str, Any] = {}
    if isinstance(seed, dict):
        doc_by_id, frag_by_id = seed_indexes(seed, failures)

    fixture_txt, case_count, rollup = check_counters(artifacts, frag_by_id, cases, failures)
    validated = 0
    if isinstance(cases, dict):
        _, validated = check_cases(cases, doc_by_id, frag_by_id, failures)
    if packets is not None:
        check_packets(packets, cases, artifacts.get("fixture_dir"), frag_by_id, failures)

    leaks = check_leakage(artifacts, cases, packets, failures)
    isolated_files = check_prompt_isolation(root, failures)
    lifecycle_blocks = check_lifecycle(artifacts, cases, failures)
    deferred_gates = check_d388(artifacts, failures)
    active_requirements = check_requirements(artifacts, failures)
    review_rows = check_review_disposition(artifacts, failures)
    human_tokens = check_no_human_inputs(artifacts, failures)
    promotion_scan = check_promotions(artifacts, failures)

    subcli_passed, subcli_rows = run_subclis(root, failures)

    summary = (
        f"{MARKER} cases={case_count} case_range={CASE_COUNT_RANGE[0]}-{CASE_COUNT_RANGE[1]} "
        f"validated_metadata={validated} fixture_txt={fixture_txt} "
        f"fixture_rollup={rollup[:16]} pinned={pinned}/{len(PINS)} leaks={leaks} "
        f"isolation_files={isolated_files} lifecycle_blocks={lifecycle_blocks} "
        f"gates_deferred={deferred_gates} active_guardrails={active_requirements} "
        f"review_rows={review_rows} human_input_tokens={human_tokens} "
        f"promotion_scan={promotion_scan} subclis={subcli_passed}/{len(SUBCLIS)}"
    )
    details = {
        "cases": case_count,
        "fixture_txt": fixture_txt,
        "fixture_rollup": rollup,
        "pinned": pinned,
        "leaks": leaks,
        "isolation_files": isolated_files,
        "lifecycle_blocks": lifecycle_blocks,
        "deferred_gates": deferred_gates,
        "validated_metadata": validated,
        "subclis": subcli_rows,
    }
    return failures, summary, details


def report(failures: Failures, summary: str) -> int:
    if failures:
        seen: set[tuple[str, str]] = set()
        for diagnostic, detail in failures:
            entry = (diagnostic, detail)
            if entry in seen:
                continue
            seen.add(entry)
            print(f"FAIL {diagnostic}: {detail}", file=sys.stderr)
        print(f"FAIL {GATE}: {len(seen)} finding(s)", file=sys.stderr)
        return 1
    print(summary)
    return 0


def battery(results: Path, out: Path, failures: Failures, *, write: bool) -> int:
    """Assemble the tracked slice battery from the verify-script result table.

    Read-only by default: the assembled payload must equal the tracked bytes or
    the run fails closed with ``BATTERY_STALE``.  ``write=True`` regenerates the
    tracked artifact once and is a no-op when the bytes already match.
    """
    if not results.is_file():
        _fail(failures, "EMPTY_SUITE", f"result table {results} does not exist")
        return report(failures, "")
    text = results.read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 4:
            _fail(failures, "BATTERY_ROW_MALFORMED", f"result row {number} does not have 4 columns")
            continue
        identifier, status, duration, command = parts
        try:
            status_code = int(status)
            duration_ms = int(duration)
        except ValueError:
            _fail(failures, "BATTERY_ROW_MALFORMED", f"result row {number} has non-numeric columns")
            continue
        if status_code != 0:
            _fail(
                failures,
                "SUBCLI_FAILURE",
                f"check {identifier} still fails with status {status_code}",
            )
        rows.append(
            {
                "id": identifier,
                "command": command,
                "status": status_code,
                "verdict": "pass" if status_code == 0 else "fail",
                "durationMs": duration_ms,
            }
        )
    if not rows:
        _fail(failures, "EMPTY_SUITE", "the result table holds no check row")
    if failures:
        return report(failures, "")
    payload = {
        "schema": BATTERY_SCHEMA,
        "milestone": "M207-b2i96m",
        "slice": "S01",
        "task": "T04",
        "human_pilot_performed": False,
        "model_invoked": False,
        "runtime_stop_active": True,
        "selected_d388_gates": "none",
        "deferred_d388_gates": sorted(D388_DEFERRED),
        "human_adoption": "pending",
        "requirement_status_effect": "unchanged",
        "review_disposition_effect": "unchanged",
        "non_claims": list(NON_CLAIMS),
        "pins": {rel: pin for _name, (rel, pin) in sorted(PINS.items())},
        "fixture_rollup_sha256": FIXTURE_ROLLUP_SHA256,
        "fixture_txt": FIXTURE_TXT_COUNT,
        "check_count": len(rows),
        "checks": [
            {key: value for key, value in row.items() if key != "durationMs"} for row in rows
        ],
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    rendered_bytes = rendered.encode("utf-8")
    timings = " ".join(f"{row['id']}={row['durationMs']}ms" for row in rows)
    if write:
        out.parent.mkdir(parents=True, exist_ok=True)
        current = out.read_bytes() if out.is_file() else None
        if current == rendered_bytes:
            outcome = "unchanged"
        else:
            out.write_bytes(rendered_bytes)
            outcome = "written"
    elif not out.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"battery missing at {out}")
        return report(failures, "")
    elif out.read_bytes() != rendered_bytes:
        _fail(
            failures,
            "BATTERY_STALE",
            "assembled battery differs from the tracked battery; regenerate once with "
            "M207_S01_WRITE_BATTERY=1 before host verification",
        )
        return report(failures, "")
    else:
        outcome = "current"
    print(f"{BATTERY_MARKER} checks={len(rows)} path={out.name} {outcome}")
    print(f"{BATTERY_TIMINGS} {timings}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "battery"],
        help="'check' verifies the slice boundary; 'battery' writes the slice battery",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    for name, _label, default, _suffix, _prefix in ARTIFACT_SPECS:
        parser.add_argument(f"--{name.replace('_', '-')}", default=default)
    parser.add_argument("--results", default="", help="battery mode: tab-separated result table")
    parser.add_argument("--out", default=BATTERY_REL, help="battery mode: battery output path")
    parser.add_argument(
        "--write",
        action="store_true",
        help="battery mode: regenerate the tracked battery (default is read-only compare)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        return report([("MISSING_ARTIFACT", f"root {root} is not a directory")], "")

    if args.mode == "battery":
        failures: Failures = []
        if not args.results:
            return report([("EMPTY_SUITE", "battery mode needs --results")], "")
        if "\\" in args.results:
            return report(
                [("UNSAFE_PATH", f"results={args.results!r} may not use backslashes")], ""
            )
        try:
            out = resolve_artifact(
                root,
                args.out,
                "battery",
                suffix=".json",
                prefix="prd/migration/rust-evidence/",
            )
        except VerificationError as exc:
            return report([(exc.diagnostic, exc.detail)], "")
        return battery(Path(args.results), out, failures, write=args.write)

    failures, summary, _details = run(root, args)
    return report(failures, summary)


if __name__ == "__main__":
    raise SystemExit(main())
