#!/usr/bin/env python3
"""Safe-metaprompt packet builder and leakage gate for the M207 S01 pilot (T03).

This is the offline, fail-closed prompt-boundary gate required by RC28-F15
("Prompt output is AnnotationSuggestion only and cannot drive FSM, create a legal
fact, or supply human acceptance") and by ``assessment/28`` §6/§8.9 (a prompt may
see source text, anchor and local alternatives; its facilities must be provably
isolated from the product).

It emits ``prd/migration/rust-evidence/m207-s01-prompt-packets.jsonl`` -- exactly
one packet per pilot case drawn by T02 -- and ``check`` re-derives that artifact
byte-for-byte while re-reading the on-disk packets through the same inspection
path, so an injected key is caught without editing the emitter.

Design invariants (each enforced, not merely documented):

* **Closed wire shape.**  Every packet carries exactly the closed key set frozen
  in ``prd/annotation/m207-s01-schemas.json`` (``schemas.prompt_packet``) and in
  the metaprompt contract -- no extra key, at any nesting depth.  The wire floor
  is hand-rolled here, so a schema edited to *allow* a predicted-answer field
  still fails (``PACKET_KEY_DRIFT``).
* **No predicted answers.**  Keys and *key lists* are scanned recursively for
  ``label``/``expected``/``answer``/``prediction``/``gold``/``capture`` (and their
  compounds) and for the rule-seed-span fields; the serialized payload is scanned
  for forbidden substrings.  ``non_claims`` is pinned by value and therefore
  excluded from the substring scan (it is the codebook's own deny-list wording).
* **Source-bound packets.**  ``fragment_text`` is byte-for-byte the frozen decoded
  fixture block, ``source_anchor`` is the frozen seed binding, and the offered
  span is the whole block.  Any desync is ``PROMPT_ISOLATION_VIOLATION``.
* **No authority.**  ``output_type`` is ``AnnotationSuggestion``, ``authority`` is
  ``none``, ``suggestion_status`` is ``none-provided`` and ``model_invoked`` is
  ``false`` in every packet; anything else is ``AUTHORITY_CLAIM``.  No model is
  invoked in this slice and no suggestion is fabricated.
* **No product/output reference.**  Authored path values must live under an
  allowed prefix; ``crates/**`` references are rejected, which is the structural
  half of the prompt-isolation requirement.
* **No ninth slot.**  The packet ``decision_space.slot_space`` must be exactly the
  eight M199 §5 slots.

``check`` accepts a repository root (``--root``) and repository-relative artifact
paths, so an adversarial caller can run the real CLI against a temporary copy; a
leading ``/``, a backslash, or any ``..`` segment is ``UNSAFE_PATH``.

Success prints exactly one deterministic status line carrying the marker
``M207_S01_PROMPT_PACKET_OK``.  Every failure is a non-zero exit with named
diagnostics on stderr (``LEAK_FORBIDDEN_KEY``, ``LEAK_FORBIDDEN_SUBSTRING``,
``AUTHORITY_CLAIM``, ``PROMPT_ISOLATION_VIOLATION``, ``NINTH_SLOT``,
``PACKET_DRIFT``, ``FROZEN_SOURCE_DRIFT``, ``UNSAFE_PATH``, ...).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MARKER = "M207_S01_PROMPT_PACKET_OK"
GATE = "M207_S01_PROMPT_PACKET_GATE"

PACKET_SCHEMA = "m207-s01-prompt-packet/v1"
CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
METAPROMPT_REL = "prd/annotation/m207-s01-metaprompt.md"
SCHEMAS_REL = "prd/annotation/m207-s01-schemas.json"
CASES_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
PACKETS_REL = "prd/migration/rust-evidence/m207-s01-prompt-packets.jsonl"
SEED_REL = "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json"
SEED_SHA256 = "134751f49db1858329248be1857ada669097f1860609090028c7b5af8975574f"
SEED_SCHEMA = "npa-lawref-sample/v1"
FIXTURE_DIR_REL = "crates/ln-decode/tests/fixtures/npa-lawref"
FIXTURE_TXT_COUNT = 180
ANNOTATION_PREFIX = "prd/annotation/"
CONTRACT_HEADING = "Machine-readable metaprompt contract"
CODEBOOK_CONTRACT_HEADING = "Machine-readable codebook contract"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

CASE_COUNT_RANGE = (20, 40)
UNKNOWN = "unknown"
METADATA_SOURCES = ("validated-manifest", UNKNOWN)

# Hand-rolled floors: the wire shape, the slot space and the output contract are
# restated here so that a schema and a metaprompt mutated together cannot dilute
# them.  The authoritative sources remain the M199 protocol §5 (pinned by the T01
# gate) and the frozen codebook contract.
WIRE_REQUIRED_KEYS = (
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
ANCHOR_KEYS = ("doc_path", "source_sha256", "block_index", "byte_len")
SPAN_KEYS = ("start", "end")
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
OUTPUT_CONTRACT = {
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": False,
}
PATH_VALUED_KEYS = frozenset({"codebook_ref", "doc_path"})
FIXED_STRING_VALUES = {
    "codebook_ref": CODEBOOK_REL,
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": False,
}
# The frozen M199 seed draws 39 documents from the full consru export and one
# tracked Consultant member of the 44-FZ cluster (M199 §13), so both live frames
# are legitimate anchor prefixes; anything else (crates/**, absolute, ..) is not.
ALLOWED_PATH_PREFIXES = (
    "prd/annotation/",
    "prd/migration/rust-evidence/",
    "consru_export/consru_export/exports/",
    "law-source/consultant/",
)
FORBIDDEN_KEYS_CANONICAL = ("label", "expected", "answer", "prediction", "gold", "capture")
FORBIDDEN_SEED_KEYS_CANONICAL = (
    "seed_span",
    "rule_seed_span",
    "rule_seed",
    "ds_span",
    "seed_slots",
)
FORBIDDEN_SUBSTRINGS = (
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
    "coder_id",
    "coder_pass",
    "submission_id",
    "adjudicat",
    "AnnotationSuggestion:",
)
REQUIRED_SECTIONS = (
    "1. Scope: no model is invoked in this slice",
    "2. Packet contents",
    "3. Source anchor",
    "4. Alternatives and the closed decision space",
    "5. Forbidden packet content",
    "6. Output contract: AnnotationSuggestion only",
    "7. Prompt isolation from the product",
    "8. Lifecycle markers and non-claims",
    "Machine-readable metaprompt contract",
)
REQUIRED_MARKERS = {
    "human_adoption": "pending",
    "runtime_stop_active": True,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged",
}
METAPROMPT_CONTRACT_KEYS = (
    "metaprompt_id",
    "schema_id",
    "codebook",
    "packet_closed_keys",
    "anchor_closed_keys",
    "span_closed_keys",
    "decision_space",
    "output_contract",
    "forbidden_keys",
    "forbidden_seed_keys",
    "forbidden_substrings",
    "allowed_path_prefixes",
    "fixed_string_values",
    "case_count_range",
    "required_sections",
    "non_claims",
    "lifecycle",
)
NON_CLAIM_SUBSTRINGS = (
    "official-publication",
    "R070",
    "LawRef",
    "N2-gate",
    "legal interpretation",
    "gold",
)

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
FORBIDDEN_EXACT_KEYS = frozenset(FORBIDDEN_SEED_KEYS_CANONICAL)
EXEMPT_KEY_LISTS = frozenset({"forbidden_keys", "forbidden_seed_keys"})
# Pinned by value, so its own deny-list wording is not a leak.
SUBSTRING_SCAN_EXEMPT_KEYS = frozenset({"non_claims", "forbidden_keys", "forbidden_seed_keys"})

CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
TOKEN_SEPARATOR_RE = re.compile(r"[^A-Za-z0-9]+")
FENCE_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
HEADING_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)

Failures = list[tuple[str, str]]


class GateError(Exception):
    """Fatal, named gate failure that stops the run immediately."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_artifact(
    root: Path,
    raw: str,
    label: str,
    *,
    suffix: str | None = None,
    prefix: str | None = None,
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
        raise GateError(
            "SCHEMA_PARSE_ERROR",
            f"{label} is not closed JSON (YAML, comments, merged or truncated documents "
            f"are rejected): {exc}",
        ) from exc


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


def load_jsonl(path: Path, label: str) -> list[Any]:
    """Parse a JSON Lines artifact; blank lines and duplicate keys fail closed."""
    if not path.is_file():
        raise GateError("MISSING_ARTIFACT", f"{label} not found at {path}")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} carries a UTF-8 BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not UTF-8: {exc}") from exc
    if text and not text.endswith("\n"):
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} does not end with a newline")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    documents: list[Any] = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            raise GateError("SCHEMA_PARSE_ERROR", f"{label}:{number} is blank; packets are objects")
        documents.append(load_json_text(line, f"{label}:{number}"))
    if not documents:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} carries no packets")
    return documents


def extract_fenced_contract(text: str, heading: str, label: str) -> dict[str, Any]:
    index = text.find(f"## {heading}")
    if index < 0:
        raise GateError("MISSING_SECTION", f"{label} section '## {heading}' is absent")
    block = FENCE_RE.search(text[index:])
    if block is None:
        raise GateError("MISSING_SECTION", f"{label} section '## {heading}' has no fenced json")
    contract = load_json_text(block.group(1), f"{label} contract")
    if not isinstance(contract, dict):
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} contract must be a JSON object")
    return contract


def file_headings(text: str) -> list[str]:
    """Section headings with markdown code spans normalized away."""
    return [match.group(1).strip().replace("`", "") for match in HEADING_RE.finditer(text)]


def key_tokens(key: str) -> list[str]:
    spaced = CAMEL_BOUNDARY_RE.sub("_", key)
    return [token for token in TOKEN_SEPARATOR_RE.split(spaced.lower()) if token]


def forbidden_key_hit(name: str) -> str | None:
    if set(key_tokens(name)) & FORBIDDEN_KEY_TOKENS:
        return "predicted-answer"
    if name.strip().lower() in FORBIDDEN_EXACT_KEYS:
        return "rule-seed-span"
    return None


def scan_forbidden_keys(node: Any, pointer: str, failures: Failures, *, in_key_list: bool) -> None:
    """Reject predicted-answer and rule-seed field names at any nesting depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            hit = forbidden_key_hit(key)
            if hit is not None:
                _fail(
                    failures,
                    "LEAK_FORBIDDEN_KEY",
                    f"{pointer}/{key} is a forbidden {hit} field",
                )
            nested = key.endswith("_keys") and key not in EXEMPT_KEY_LISTS
            scan_forbidden_keys(value, f"{pointer}/{key}", failures, in_key_list=nested)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            if in_key_list and isinstance(value, str):
                element = forbidden_key_hit(value)
                if element is not None:
                    _fail(
                        failures,
                        "LEAK_FORBIDDEN_KEY",
                        f"{pointer}[{index}] declares {value!r}, a forbidden {element} field",
                    )
            scan_forbidden_keys(value, f"{pointer}[{index}]", failures, in_key_list=in_key_list)


def substring_scan_view(packet: Any) -> Any:
    """Drop value-pinned deny-lists before the substring scan."""
    if not isinstance(packet, dict):
        return packet
    return {key: value for key, value in packet.items() if key not in SUBSTRING_SCAN_EXEMPT_KEYS}


def scan_forbidden_substrings(
    payload: Any, label: str, subs: tuple[str, ...], failures: Failures
) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    for needle in subs:
        if needle.lower() in text:
            _fail(
                failures,
                "LEAK_FORBIDDEN_SUBSTRING",
                f"{label} carries the forbidden substring {needle!r}",
            )


def scan_authored_paths(node: Any, pointer: str, failures: Failures) -> None:
    """Reject authored path values that leave the allowed prefix set.

    Only the keys whose value *is* a repository path are inspected, so the frozen
    fragment text is judged by its byte binding rather than by punctuation that
    Russian source text may legitimately contain.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{pointer}/{key}"
            if key in PATH_VALUED_KEYS:
                if not isinstance(value, str):
                    _fail(failures, "PATH_SCOPE_VIOLATION", f"{child} is not a string path")
                else:
                    check_authored_path(value, child, failures)
            scan_authored_paths(value, child, failures)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            scan_authored_paths(value, f"{pointer}[{index}]", failures)


def check_authored_path(value: str, pointer: str, failures: Failures) -> None:
    """One authored path must be a repository-relative reference inside the frame."""
    candidate = value.strip()
    if (
        not candidate
        or "\\" in candidate
        or candidate.startswith("/")
        or ".." in candidate.split("/")
        or (len(candidate) > 1 and candidate[1] == ":")
    ):
        _fail(
            failures,
            "PATH_SCOPE_VIOLATION",
            f"{pointer} carries {candidate!r}, which is not a POSIX relative path",
        )
    elif not candidate.startswith(ALLOWED_PATH_PREFIXES):
        _fail(
            failures,
            "PROMPT_ISOLATION_VIOLATION",
            f"{pointer} references {candidate!r} outside {list(ALLOWED_PATH_PREFIXES)}",
        )


def _exact_keys(node: Any, expected: tuple[str, ...], pointer: str, failures: Failures) -> None:
    if not isinstance(node, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", f"{pointer} is not an object")
        return
    actual = set(node)
    if actual != set(expected):
        _fail(
            failures,
            "PACKET_KEY_DRIFT",
            f"{pointer} closed keys drifted (missing={sorted(set(expected) - actual)}, "
            f"extra={sorted(actual - set(expected))})",
        )


def check_non_claims(label: str, claims: Any, failures: Failures) -> None:
    if not isinstance(claims, list) or not claims or not all(isinstance(c, str) for c in claims):
        _fail(failures, "MISSING_NON_CLAIM", f"{label} must be a non-empty list of strings")
        return
    blob = "\n".join(claims)
    for required in NON_CLAIM_SUBSTRINGS:
        if required not in blob:
            _fail(
                failures,
                "MISSING_NON_CLAIM",
                f"{label} is missing the required non-claim substring {required!r}",
            )


def check_metaprompt_contract(
    contract: dict[str, Any],
    headings: list[str],
    schema: Any,
    codebook_contract: dict[str, Any],
    schema_non_claims: Any,
    failures: Failures,
) -> dict[str, Any]:
    """Cross-bind the metaprompt contract, the closed schemas and the codebook."""
    scan_forbidden_keys(contract, "metaprompt$", failures, in_key_list=False)
    if set(contract) != set(METAPROMPT_CONTRACT_KEYS):
        _fail(
            failures,
            "PROMPT_CONTRACT_DRIFT",
            "metaprompt contract keys drifted: extra="
            f"{sorted(set(contract) - set(METAPROMPT_CONTRACT_KEYS))} missing="
            f"{sorted(set(METAPROMPT_CONTRACT_KEYS) - set(contract))}",
        )
    if contract.get("metaprompt_id") != "m207-s01-metaprompt/v1":
        _fail(failures, "PROMPT_CONTRACT_DRIFT", "metaprompt_id must be m207-s01-metaprompt/v1")
    if contract.get("schema_id") != PACKET_SCHEMA:
        _fail(
            failures,
            "PROMPT_CONTRACT_DRIFT",
            f"metaprompt schema_id {contract.get('schema_id')!r} != {PACKET_SCHEMA!r}",
        )
    if contract.get("codebook") != CODEBOOK_REL:
        _fail(failures, "PROMPT_CONTRACT_DRIFT", f"metaprompt codebook must be {CODEBOOK_REL!r}")

    declared_wire = contract.get("packet_closed_keys")
    if not isinstance(declared_wire, list) or tuple(declared_wire) != WIRE_REQUIRED_KEYS:
        _fail(
            failures,
            "PACKET_KEY_DRIFT",
            f"metaprompt packet_closed_keys={declared_wire!r} != the closed wire shape "
            f"{list(WIRE_REQUIRED_KEYS)}",
        )
    if contract.get("anchor_closed_keys") != list(ANCHOR_KEYS):
        _fail(failures, "PACKET_KEY_DRIFT", "metaprompt anchor_closed_keys drifted")
    if contract.get("span_closed_keys") != list(SPAN_KEYS):
        _fail(failures, "PACKET_KEY_DRIFT", "metaprompt span_closed_keys drifted")

    decision_space = contract.get("decision_space")
    if not isinstance(decision_space, dict):
        _fail(failures, "PROMPT_CONTRACT_DRIFT", "metaprompt decision_space must be an object")
    else:
        slots = decision_space.get("slot_space")
        if not isinstance(slots, list) or tuple(slots) != M199_SLOT_SPACE:
            _fail(
                failures,
                "NINTH_SLOT",
                f"metaprompt decision_space.slot_space={slots!r} is not the closed M199 §5 space",
            )
        if decision_space.get("decision_values") != list(DECISION_VALUES):
            _fail(failures, "PROMPT_CONTRACT_DRIFT", "decision_space.decision_values drifted")
        if decision_space.get("abstention_values") != list(ABSTENTION_VALUES):
            _fail(failures, "ABSTENTION_COLLAPSE", "decision_space.abstention_values drifted")

    if contract.get("output_contract") != OUTPUT_CONTRACT:
        _fail(
            failures,
            "AUTHORITY_CLAIM",
            "metaprompt output_contract must keep AnnotationSuggestion / none / none-provided",
        )
    if contract.get("forbidden_keys") != list(FORBIDDEN_KEYS_CANONICAL):
        _fail(failures, "LEAK_FORBIDDEN_KEY", "metaprompt forbidden_keys must be the canonical six")
    if contract.get("forbidden_seed_keys") != list(FORBIDDEN_SEED_KEYS_CANONICAL):
        _fail(failures, "LEAK_FORBIDDEN_KEY", "metaprompt forbidden_seed_keys drifted")
    if contract.get("forbidden_substrings") != list(FORBIDDEN_SUBSTRINGS):
        _fail(failures, "LEAK_FORBIDDEN_KEY", "metaprompt forbidden_substrings drifted")
    if contract.get("allowed_path_prefixes") != list(ALLOWED_PATH_PREFIXES):
        _fail(failures, "PATH_SCOPE_VIOLATION", "metaprompt allowed_path_prefixes drifted")
    if contract.get("fixed_string_values") != FIXED_STRING_VALUES:
        _fail(failures, "AUTHORITY_CLAIM", "metaprompt fixed_string_values drifted")
    if contract.get("case_count_range") != list(CASE_COUNT_RANGE):
        _fail(failures, "CASE_COUNT_OUT_OF_RANGE", "metaprompt case_count_range drifted")
    if contract.get("required_sections") != list(REQUIRED_SECTIONS):
        _fail(
            failures,
            "MISSING_SECTION",
            "metaprompt required_sections must equal the frozen section list",
        )
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            _fail(failures, "MISSING_SECTION", f"metaprompt heading '## {section}' is absent")
    check_non_claims("metaprompt.non_claims", contract.get("non_claims"), failures)
    if contract.get("lifecycle") != REQUIRED_MARKERS:
        _fail(
            failures,
            "MISSING_LIFECYCLE_MARKER",
            f"metaprompt lifecycle={contract.get('lifecycle')!r} != {REQUIRED_MARKERS!r}",
        )

    codebook_schema = schema.get("schema") if isinstance(schema, dict) else None
    if codebook_contract.get("schema_id") != codebook_schema:
        _fail(
            failures,
            "PROMPT_CONTRACT_DRIFT",
            f"codebook contract schema_id {codebook_contract.get('schema_id')!r} != "
            f"schemas document {codebook_schema!r}",
        )
    codebook_slots = codebook_contract.get("slot_space")
    if isinstance(codebook_slots, dict):
        declared = codebook_slots.get("closed_keys")
        if not isinstance(declared, list) or tuple(declared) != M199_SLOT_SPACE:
            _fail(
                failures,
                "NINTH_SLOT",
                f"codebook slot space {declared!r} is not the frozen eight-slot space",
            )
    check_schema_side(schema, contract, failures)
    check_codebook_side(contract, codebook_contract, schema_non_claims, failures)
    return decision_space if isinstance(decision_space, dict) else {}


def prompt_packet_schema(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return None
    subschemas = schema.get("schemas")
    if not isinstance(subschemas, dict):
        return None
    return subschemas.get("prompt_packet")


def check_schema_side(schema: Any, contract: dict[str, Any], failures: Failures) -> None:
    """The closed schemas must declare exactly what the metaprompt declares."""
    sub = prompt_packet_schema(schema)
    if not isinstance(sub, dict):
        _fail(failures, "MISSING_ARTIFACT", "schemas.prompt_packet subsection is absent")
        return
    if sub.get("schema_id") != PACKET_SCHEMA:
        _fail(
            failures,
            "PROMPT_CONTRACT_DRIFT",
            f"schemas.prompt_packet.schema_id={sub.get('schema_id')!r} != {PACKET_SCHEMA!r}",
        )
    if sub.get("closed_keys") != contract.get("packet_closed_keys"):
        _fail(
            failures,
            "PACKET_KEY_DRIFT",
            "schemas.prompt_packet.closed_keys differ from the metaprompt closed wire shape",
        )
    for key, expected in (
        ("anchor_closed_keys", list(ANCHOR_KEYS)),
        ("span_closed_keys", list(SPAN_KEYS)),
    ):
        if sub.get(key) != expected:
            _fail(failures, "PACKET_KEY_DRIFT", f"schemas.prompt_packet.{key} drifted")
    required = sub.get("required_keys")
    if required != contract.get("packet_closed_keys"):
        _fail(
            failures,
            "PACKET_KEY_DRIFT",
            "schemas.prompt_packet.required_keys must equal the closed wire shape",
        )
    if sub.get("output_type") != OUTPUT_CONTRACT["output_type"]:
        _fail(failures, "AUTHORITY_CLAIM", "schemas.prompt_packet.output_type drifted")
    if sub.get("authority_values") != [OUTPUT_CONTRACT["authority"]]:
        _fail(failures, "AUTHORITY_CLAIM", "schemas.prompt_packet.authority_values drifted")
    if sub.get("suggestion_status_values") != [OUTPUT_CONTRACT["suggestion_status"]]:
        _fail(failures, "AUTHORITY_CLAIM", "schemas.prompt_packet.suggestion_status_values drifted")
    if sub.get("model_invoked") is not False:
        _fail(failures, "AUTHORITY_CLAIM", "schemas.prompt_packet.model_invoked must be false")


def check_codebook_side(
    contract: dict[str, Any],
    codebook_contract: dict[str, Any],
    schema_non_claims: Any,
    failures: Failures,
) -> None:
    """The frozen codebook contract is the slot/decision source of this boundary."""
    if codebook_contract.get("output_contract") != OUTPUT_CONTRACT:
        _fail(failures, "AUTHORITY_CLAIM", "codebook output_contract drifted")
    if codebook_contract.get("forbidden_keys") != contract.get("forbidden_keys"):
        _fail(failures, "LEAK_FORBIDDEN_KEY", "codebook and metaprompt forbidden_keys differ")
    if codebook_contract.get("forbidden_seed_keys") != contract.get("forbidden_seed_keys"):
        _fail(failures, "LEAK_FORBIDDEN_KEY", "codebook and metaprompt forbidden_seed_keys differ")
    if codebook_contract.get("non_claims") != contract.get("non_claims"):
        _fail(failures, "MISSING_NON_CLAIM", "codebook and metaprompt non_claims differ")
    if codebook_contract.get("non_claims") != schema_non_claims:
        _fail(failures, "MISSING_NON_CLAIM", "schemas and codebook non_claims differ")
    if codebook_contract.get("lifecycle") != REQUIRED_MARKERS:
        _fail(failures, "MISSING_LIFECYCLE_MARKER", "codebook lifecycle markers drifted")
    if codebook_contract.get("case_count_range") != list(CASE_COUNT_RANGE):
        _fail(failures, "CASE_COUNT_OUT_OF_RANGE", "codebook case_count_range drifted")
    abstention = codebook_contract.get("abstention")
    if not isinstance(abstention, dict) or abstention.get("values") != list(ABSTENTION_VALUES):
        _fail(failures, "ABSTENTION_COLLAPSE", "codebook abstention values drifted")


def seed_indexes(seed: Any, failures: Failures) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(seed, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "M199 seed manifest is not an object")
        return {}, {}
    if seed.get("schema") != SEED_SCHEMA:
        _fail(failures, "FROZEN_SOURCE_DRIFT", f"M199 seed schema {seed.get('schema')!r} drifted")
    fragments = {
        fragment["id"]: fragment
        for fragment in seed.get("fragments", [])
        if isinstance(fragment, dict) and isinstance(fragment.get("id"), str)
    }
    documents = {
        document["doc_id"]: document
        for document in seed.get("documents", [])
        if isinstance(document, dict) and isinstance(document.get("doc_id"), str)
    }
    if not fragments or not documents:
        _fail(failures, "FROZEN_SOURCE_DRIFT", "M199 seed carries no documents/fragments")
    return fragments, documents


def fixture_bytes_for(
    fixture_dir: Path,
    fragments: dict[str, Any],
    failures: Failures,
) -> dict[str, bytes]:
    """Load the frozen fragment bytes and refuse an enlarged fixture tree."""
    payload: dict[str, bytes] = {}
    if not fixture_dir.is_dir():
        _fail(failures, "MISSING_ARTIFACT", f"fixture directory {fixture_dir} does not exist")
        return payload
    declared = {fragment.get("file") for fragment in fragments.values()}
    on_disk = {path.relative_to(fixture_dir).as_posix() for path in fixture_dir.rglob("*.txt")}
    if len({name for name in on_disk if isinstance(name, str)}) != FIXTURE_TXT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"fixture tree holds {len(on_disk)} .txt files, expected {FIXTURE_TXT_COUNT}",
        )
    for extra in sorted(on_disk - declared):
        _fail(failures, "SEED_ENLARGED", f"fixture file {extra} is not declared by the M199 seed")
    for fragment_id, fragment in sorted(fragments.items()):
        name = fragment.get("file")
        if not isinstance(name, str) or "/" in name or "\\" in name or ".." in name:
            _fail(
                failures,
                "UNSAFE_PATH",
                f"fragment {fragment_id} declares unsafe file name {name!r}",
            )
            continue
        path = fixture_dir / name
        if not path.is_file():
            _fail(failures, "MISSING_ARTIFACT", f"frozen fragment file {name} is absent")
            continue
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf"):
            _fail(failures, "FROZEN_SOURCE_DRIFT", f"fragment {name} carries a UTF-8 BOM")
            continue
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            _fail(failures, "FROZEN_SOURCE_DRIFT", f"fragment {name} is not UTF-8: {exc}")
            continue
        if fragment.get("byte_len") != len(data):
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"fragment {fragment_id} byte_len drifted: seed "
                f"{fragment.get('byte_len')} != file {len(data)}",
            )
        payload[fragment_id] = data
    return payload


def utf8_boundaries(data: bytes) -> set[int]:
    boundaries = {0}
    offset = 0
    for char in data.decode("utf-8"):
        offset += len(char.encode("utf-8"))
        boundaries.add(offset)
    return boundaries


def inspect_cases(
    artifact: Any,
    *,
    fragments: dict[str, Any],
    documents: dict[str, Any],
    fixture_bytes: dict[str, bytes],
    failures: Failures,
) -> list[dict[str, Any]]:
    """Structurally validate the T02 case manifest before any packet is built."""
    if not isinstance(artifact, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "case manifest is not an object")
        return []
    scan_forbidden_keys(artifact, "cases$", failures, in_key_list=False)
    if artifact.get("schema") != "m207-s01-pilot-cases/v1":
        _fail(failures, "CASE_MANIFEST_DRIFT", f"case manifest schema {artifact.get('schema')!r}")
    if artifact.get("codebook") != CODEBOOK_REL:
        _fail(failures, "CASE_MANIFEST_DRIFT", "case manifest codebook reference drifted")
    cases = artifact.get("cases")
    if not isinstance(cases, list):
        _fail(failures, "SCHEMA_PARSE_ERROR", "case manifest has no cases array")
        return []
    if not CASE_COUNT_RANGE[0] <= len(cases) <= CASE_COUNT_RANGE[1]:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"case manifest holds {len(cases)} cases, outside {list(CASE_COUNT_RANGE)}",
        )
    if artifact.get("case_count") != len(cases):
        _fail(
            failures,
            "CASE_MANIFEST_DRIFT",
            f"case_count {artifact.get('case_count')!r} != {len(cases)} cases",
        )
    check_non_claims("case_manifest.non_claims", artifact.get("non_claims"), failures)
    if artifact.get("lifecycle") != REQUIRED_MARKERS:
        _fail(failures, "MISSING_LIFECYCLE_MARKER", "case manifest lifecycle markers drifted")

    for number, case in enumerate(cases, start=1):
        pointer = f"cases[{number - 1}]"
        if not isinstance(case, dict):
            _fail(failures, "SCHEMA_PARSE_ERROR", f"{pointer} is not an object")
            continue
        case_id = case.get("case_id")
        if case_id != f"m207-s01-case-{number:03d}":
            _fail(
                failures,
                "CASE_MANIFEST_DRIFT",
                f"{pointer} case_id {case_id!r} is not the deterministic id",
            )
        fragment = fragments.get(case.get("fragment_id"))
        if fragment is None:
            _fail(
                failures,
                "MISSING_ARTIFACT",
                f"{pointer} references {case.get('fragment_id')!r}, absent from the frozen seed",
            )
            continue
        document = documents.get(fragment.get("doc_id"))
        if document is None or case.get("doc_id") != fragment.get("doc_id"):
            _fail(failures, "PROVENANCE_DRIFT", f"{pointer} is not bound to a frozen seed document")
            continue
        if case.get("source_path") != document.get("source_path"):
            _fail(failures, "PROVENANCE_DRIFT", f"{pointer} source_path drifted from the seed")
        if case.get("source_sha256") != document.get("source_sha256"):
            _fail(failures, "PROVENANCE_DRIFT", f"{pointer} source_sha256 drifted from the seed")
        if not isinstance(case.get("source_sha256"), str) or not SHA256_RE.match(
            case["source_sha256"]
        ):
            _fail(failures, "PROVENANCE_DRIFT", f"{pointer} source_sha256 is not 64 hex chars")
        if case.get("source_block_index") != fragment.get("source_block_index"):
            _fail(failures, "PROVENANCE_DRIFT", f"{pointer} source_block_index drifted")

        data = fixture_bytes.get(fragment.get("id"))
        if data is None:
            _fail(
                failures,
                "MISSING_ARTIFACT",
                f"{pointer} has no frozen fragment bytes for {fragment.get('id')!r}",
            )
            continue
        if case.get("byte_len") != len(data):
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"{pointer} byte_len {case.get('byte_len')!r} != frozen fragment {len(data)}",
            )
        start, end = case.get("start"), case.get("end")
        if not all(isinstance(value, int) for value in (start, end)):
            _fail(failures, "SPAN_OUT_OF_BOUNDS", f"{pointer} span fields are not integers")
        elif not 0 <= start < end <= len(data):
            _fail(
                failures,
                "SPAN_OUT_OF_BOUNDS",
                f"{pointer} span [{start}, {end}) is empty or past EOF (byte_len={len(data)})",
            )
        else:
            boundaries = utf8_boundaries(data)
            if start not in boundaries or end not in boundaries:
                _fail(
                    failures,
                    "SPAN_NOT_UTF8_BOUNDARY",
                    f"{pointer} span [{start}, {end}) splits a UTF-8 code point",
                )
            if (start, end) != (0, len(data)):
                _fail(
                    failures,
                    "SPAN_NOT_FULL_FRAGMENT",
                    f"{pointer} offered span [{start}, {end}) is not the whole frozen block; "
                    "a narrowed window would import a prediction",
                )
        if case.get("abstention_available") is not True:
            _fail(failures, "ABSTENTION_COLLAPSE", f"{pointer} abstention_available is not true")
        if case.get("span_offered_for_coding") is not True:
            _fail(failures, "OFFER_FLAG_DRIFT", f"{pointer} span_offered_for_coding is not true")
        source = case.get("metadata_source")
        if source not in METADATA_SOURCES:
            _fail(
                failures,
                "METADATA_PATH_DERIVED",
                f"{pointer} metadata_source {source!r} is outside {list(METADATA_SOURCES)}",
            )
        elif source == UNKNOWN and (
            case.get("year") != UNKNOWN or case.get("document_type") != UNKNOWN
        ):
            _fail(
                failures,
                "METADATA_PATH_DERIVED",
                f"{pointer} carries year/document_type without a validated manifest",
            )
    return [case for case in cases if isinstance(case, dict)]


def build_packets(
    cases: list[dict[str, Any]],
    *,
    fixture_bytes: dict[str, bytes],
    alternative_classes: Any,
    codebook_non_claims: Any,
    slot_space: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Build one packet per pilot case; the builder mints no content of its own."""
    decision_space = {
        "decision_values": list(DECISION_VALUES),
        "slot_space": list(slot_space),
        "abstention_values": list(ABSTENTION_VALUES),
    }
    packets: list[dict[str, Any]] = []
    for number, case in enumerate(cases, start=1):
        data = fixture_bytes[case["fragment_id"]]
        packets.append(
            {
                "packet_id": f"m207-s01-packet-{number:03d}",
                "case_id": case["case_id"],
                "codebook_ref": CODEBOOK_REL,
                "source_anchor": {
                    "doc_path": case["source_path"],
                    "source_sha256": case["source_sha256"],
                    "block_index": case["source_block_index"],
                    "byte_len": case["byte_len"],
                },
                "fragment_text": data.decode("utf-8"),
                "span": {"start": case["start"], "end": case["end"]},
                "alternative_classes": alternative_classes,
                "decision_space": decision_space,
                "output_type": OUTPUT_CONTRACT["output_type"],
                "authority": OUTPUT_CONTRACT["authority"],
                "suggestion_status": OUTPUT_CONTRACT["suggestion_status"],
                "model_invoked": OUTPUT_CONTRACT["model_invoked"],
                "non_claims": list(codebook_non_claims),
            }
        )
    return packets


def inspect_packet(
    packet: Any,
    *,
    number: int,
    case: dict[str, Any] | None,
    fragments: dict[str, Any],
    fixture_bytes: dict[str, bytes],
    contract: dict[str, Any],
    failures: Failures,
) -> None:
    """Full closed-shape, leakage, authority and source-binding inspection."""
    pointer = f"packets[{number - 1}]"
    if not isinstance(packet, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", f"{pointer} is not an object")
        return
    _exact_keys(packet, WIRE_REQUIRED_KEYS, pointer, failures)
    scan_forbidden_keys(packet, pointer, failures, in_key_list=False)
    scan_forbidden_substrings(
        substring_scan_view(packet),
        pointer,
        tuple(contract.get("forbidden_substrings") or FORBIDDEN_SUBSTRINGS),
        failures,
    )
    scan_authored_paths(packet, pointer, failures)

    if packet.get("packet_id") != f"m207-s01-packet-{number:03d}":
        _fail(
            failures,
            "PACKET_ORDER_DRIFT",
            f"{pointer} packet_id {packet.get('packet_id')!r} is not the deterministic id",
        )
    if packet.get("codebook_ref") != CODEBOOK_REL:
        _fail(failures, "PACKET_DRIFT", f"{pointer} codebook_ref is not the frozen codebook")
    for key in ("codebook_ref", "output_type", "authority", "suggestion_status", "model_invoked"):
        expected = FIXED_STRING_VALUES.get(key)
        if expected is None:
            continue
        if packet.get(key) != expected:
            _fail(
                failures,
                "AUTHORITY_CLAIM" if key != "codebook_ref" else "PACKET_DRIFT",
                f"{pointer}.{key}={packet.get(key)!r} != {expected!r}",
            )
    if packet.get("authority") != "none" or packet.get("suggestion_status") != "none-provided":
        _fail(
            failures,
            "AUTHORITY_CLAIM",
            f"{pointer} must keep authority=none and suggestion_status=none-provided",
        )

    decision_space = packet.get("decision_space")
    if not isinstance(decision_space, dict):
        _fail(failures, "PACKET_DRIFT", f"{pointer} decision_space must be an object")
    else:
        _exact_keys(
            decision_space,
            ("decision_values", "slot_space", "abstention_values"),
            f"{pointer}.decision_space",
            failures,
        )
        slots = decision_space.get("slot_space")
        if not isinstance(slots, list) or tuple(slots) != M199_SLOT_SPACE:
            _fail(
                failures,
                "NINTH_SLOT",
                f"{pointer}.decision_space.slot_space={slots!r} is not the closed M199 §5 space",
            )
        if decision_space.get("decision_values") != list(DECISION_VALUES):
            _fail(failures, "PACKET_DRIFT", f"{pointer} decision_values drifted")
        if decision_space.get("abstention_values") != list(ABSTENTION_VALUES):
            _fail(failures, "ABSTENTION_COLLAPSE", f"{pointer} abstention_values drifted")

    check_non_claims(f"{pointer}.non_claims", packet.get("non_claims"), failures)

    if case is None:
        return
    if packet.get("case_id") != case.get("case_id"):
        _fail(
            failures,
            "PACKET_ORDER_DRIFT",
            f"{pointer} case_id {packet.get('case_id')!r} != {case.get('case_id')!r}",
        )
    fragment = fragments.get(case.get("fragment_id"))
    data = fixture_bytes.get(fragment.get("id")) if fragment else None
    if data is None:
        _fail(failures, "MISSING_ARTIFACT", f"{pointer} has no frozen fragment bytes")
        return
    anchor = packet.get("source_anchor")
    _exact_keys(anchor, ANCHOR_KEYS, f"{pointer}.source_anchor", failures)
    if isinstance(anchor, dict):
        expected_anchor = {
            "doc_path": case.get("source_path"),
            "source_sha256": case.get("source_sha256"),
            "block_index": case.get("source_block_index"),
            "byte_len": case.get("byte_len"),
        }
        for key, expected in expected_anchor.items():
            if anchor.get(key) != expected:
                _fail(
                    failures,
                    "ANCHOR_DRIFT",
                    f"{pointer}.source_anchor.{key}={anchor.get(key)!r} != {expected!r}",
                )
    span = packet.get("span")
    _exact_keys(span, SPAN_KEYS, f"{pointer}.span", failures)
    if isinstance(span, dict):
        start, end = span.get("start"), span.get("end")
        if not all(isinstance(value, int) for value in (start, end)):
            _fail(failures, "SPAN_OUT_OF_BOUNDS", f"{pointer}.span fields are not integers")
        elif not 0 <= start < end <= len(data):
            _fail(
                failures,
                "SPAN_OUT_OF_BOUNDS",
                f"{pointer}.span [{start}, {end}) is empty or past EOF (byte_len={len(data)})",
            )
        elif (start, end) != (0, len(data)):
            _fail(
                failures,
                "SPAN_NOT_FULL_FRAGMENT",
                f"{pointer}.span [{start}, {end}) is not the whole frozen block",
            )
    text = packet.get("fragment_text")
    if not isinstance(text, str):
        _fail(failures, "PROMPT_ISOLATION_VIOLATION", f"{pointer}.fragment_text is not a string")
    else:
        if text != data.decode("utf-8"):
            _fail(
                failures,
                "PROMPT_ISOLATION_VIOLATION",
                f"{pointer}.fragment_text is not the frozen decoded fragment "
                "(truncated, rewritten or desynchronized)",
            )
        elif len(text.encode("utf-8")) != case.get("byte_len"):
            _fail(
                failures,
                "PROMPT_ISOLATION_VIOLATION",
                f"{pointer}.fragment_text byte length != the frozen byte_len",
            )
    if packet.get("alternative_classes") != case.get("alternative_classes"):
        _fail(
            failures,
            "ALTERNATIVES_DRIFT",
            f"{pointer}.alternative_classes differ from the pilot case decision poles",
        )


def inspect_packets(
    packets: list[Any],
    *,
    cases: list[dict[str, Any]],
    fragments: dict[str, Any],
    fixture_bytes: dict[str, bytes],
    contract: dict[str, Any],
    failures: Failures,
) -> None:
    if len(packets) != len(cases):
        _fail(
            failures,
            "PACKET_COUNT_MISMATCH",
            f"{len(packets)} packet(s) for {len(cases)} pilot case(s)",
        )
    for number, packet in enumerate(packets, start=1):
        case = cases[number - 1] if number - 1 < len(cases) else None
        inspect_packet(
            packet,
            number=number,
            case=case,
            fragments=fragments,
            fixture_bytes=fixture_bytes,
            contract=contract,
            failures=failures,
        )


def render_packets(packets: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(packet, ensure_ascii=False) + "\n" for packet in packets).encode(
        "utf-8"
    )


def run(mode: str, args: argparse.Namespace) -> tuple[Failures, str]:
    root = Path(args.root)
    if not root.is_dir():
        return [("MISSING_ARTIFACT", f"root {root} is not a directory")], ""
    try:
        cases_path = resolve_artifact(root, args.cases, "cases", suffix=".json")
        packets_path = resolve_artifact(root, args.packets, "packets", suffix=".jsonl")
        schemas_path = resolve_artifact(
            root, args.schemas, "schemas", suffix=".json", prefix=ANNOTATION_PREFIX
        )
        metaprompt_path = resolve_artifact(
            root, args.metaprompt, "metaprompt", suffix=".md", prefix=ANNOTATION_PREFIX
        )
        codebook_path = resolve_artifact(
            root, args.codebook, "codebook", suffix=".md", prefix=ANNOTATION_PREFIX
        )
        seed_path = resolve_artifact(root, args.seed_manifest, "seed-manifest", suffix=".json")
        fixture_dir = resolve_artifact(root, args.fixture_dir, "fixture-dir")
    except GateError as exc:
        return [(exc.diagnostic, exc.detail)], ""

    failures: Failures = []
    schema: Any = None
    if not schemas_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"schemas missing at {args.schemas}")
    else:
        try:
            schema = load_json(schemas_path, "schemas document")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    codebook_contract: dict[str, Any] = {}
    if not codebook_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"codebook missing at {args.codebook}")
    else:
        try:
            codebook_contract = extract_fenced_contract(
                codebook_path.read_text(encoding="utf-8"),
                CODEBOOK_CONTRACT_HEADING,
                "codebook",
            )
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    contract: dict[str, Any] = {}
    if not metaprompt_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"metaprompt missing at {args.metaprompt}")
    else:
        text = metaprompt_path.read_text(encoding="utf-8")
        try:
            contract = extract_fenced_contract(text, CONTRACT_HEADING, "metaprompt")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
        else:
            check_metaprompt_contract(
                contract,
                file_headings(text),
                schema,
                codebook_contract,
                schema.get("non_claims") if isinstance(schema, dict) else None,
                failures,
            )

    seed: Any = None
    if not seed_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"M199 seed manifest missing at {args.seed_manifest}")
    else:
        digest = sha256_file(seed_path)
        if digest != SEED_SHA256:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"M199 seed sha256 {digest} != pinned {SEED_SHA256}",
            )
        try:
            seed = load_json(seed_path, "M199 seed manifest")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    fragments, documents = seed_indexes(seed, failures)
    fixture_bytes = fixture_bytes_for(fixture_dir, fragments, failures)

    cases: list[dict[str, Any]] = []
    if not cases_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"case manifest missing at {args.cases}")
    else:
        try:
            cases = inspect_cases(
                load_json(cases_path, "case manifest"),
                fragments=fragments,
                documents=documents,
                fixture_bytes=fixture_bytes,
                failures=failures,
            )
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    alternative_classes = codebook_contract.get("alternative_axes")
    codebook_non_claims = codebook_contract.get("non_claims")
    slot_space = M199_SLOT_SPACE
    if isinstance(codebook_contract.get("slot_space"), dict):
        declared = codebook_contract["slot_space"].get("closed_keys")
        if isinstance(declared, list):
            slot_space = tuple(declared)

    packets: list[dict[str, Any]] = []
    if cases and all(case.get("fragment_id") in fixture_bytes for case in cases):
        try:
            packets = build_packets(
                cases,
                fixture_bytes=fixture_bytes,
                alternative_classes=alternative_classes,
                codebook_non_claims=codebook_non_claims,
                slot_space=slot_space,
            )
            inspect_packets(
                packets,
                cases=cases,
                fragments=fragments,
                fixture_bytes=fixture_bytes,
                contract=contract,
                failures=failures,
            )
        except KeyError as exc:
            _fail(failures, "MISSING_ARTIFACT", f"case draw references unknown fragment {exc}")

    payload = render_packets(packets)
    if mode == "write":
        if not failures:
            packets_path.parent.mkdir(parents=True, exist_ok=True)
            packets_path.write_bytes(payload)
    else:
        on_disk: list[Any] = []
        try:
            on_disk = load_jsonl(packets_path, "prompt packets")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
        else:
            inspect_packets(
                on_disk,
                cases=cases,
                fragments=fragments,
                fixture_bytes=fixture_bytes,
                contract=contract,
                failures=failures,
            )
        if packets_path.is_file() and packets_path.read_bytes() != payload:
            _fail(
                failures,
                "PACKET_DRIFT",
                f"on-disk {args.packets} is not the deterministic regeneration "
                f"({len(packets_path.read_bytes())} vs {len(payload)} bytes)",
            )

    summary = (
        f"{MARKER} mode={mode} packets={len(packets)} cases={len(cases)} "
        f"authority={OUTPUT_CONTRACT['authority']} "
        f"suggestion_status={OUTPUT_CONTRACT['suggestion_status']} "
        f"model_invoked={OUTPUT_CONTRACT['model_invoked']} "
        f"slot_space={len(M199_SLOT_SPACE)} leakage_findings="
        f"{sum(1 for diagnostic, _ in failures if diagnostic.startswith('LEAK_'))}"
    )
    return failures, summary


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "write"],
        help="'check' re-derives the packets byte-for-byte; 'write' emits them",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    parser.add_argument("--cases", default=CASES_REL, help="pilot case manifest path")
    parser.add_argument("--packets", default=PACKETS_REL, help="prompt packet JSONL path")
    parser.add_argument("--schemas", default=SCHEMAS_REL, help="closed pilot schema path")
    parser.add_argument("--metaprompt", default=METAPROMPT_REL, help="metaprompt contract path")
    parser.add_argument("--codebook", default=CODEBOOK_REL, help="frozen codebook path")
    parser.add_argument("--seed-manifest", default=SEED_REL, help="frozen M199 seed manifest")
    parser.add_argument(
        "--fixture-dir", default=FIXTURE_DIR_REL, help="frozen fragment fixture directory"
    )
    args = parser.parse_args(argv)
    failures, summary = run(args.mode, args)
    return report(failures, summary)


if __name__ == "__main__":
    raise SystemExit(main())
