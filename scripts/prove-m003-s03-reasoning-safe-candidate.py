#!/usr/bin/env python3
"""M003/S03 reasoning-safe generated-Cypher candidate proof skeleton.

This module is intentionally local and deterministic. It classifies provider-
shaped payload fixtures into a safe generated-Cypher candidate handoff without
calling MiniMax, FalkorDB, the M002 validator, or any graph execution surface.
Only whitespace trimming is allowed before candidate acceptance: surrounding
prose, markdown fences, comments, multi-statements, and reasoning tags fail
closed before any later validation/execution stage can see a candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m003-s03-reasoning-safe-candidate/v1"
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
DEFAULT_ENDPOINT = "https://api.minimax.io/v1"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S03"
JSON_ARTIFACT = "S03-REASONING-SAFE-CANDIDATE.json"
MARKDOWN_ARTIFACT = "S03-REASONING-SAFE-CANDIDATE.md"

Status = Literal["blocked-credential", "blocked-environment", "failed-runtime", "confirmed-runtime"]

STATUS_CATEGORIES = (
    "blocked-credential",
    "blocked-environment",
    "failed-runtime",
    "confirmed-runtime",
)
ROOT_CAUSE_CATEGORIES = (
    "none",
    "minimax-credential-missing",
    "environment-import-failed",
    "resolver-failed",
    "provider-http-error",
    "provider-timeout",
    "provider-schema-mismatch",
    "empty-content",
    "non-cypher-output",
    "reasoning-contamination",
    "markdown-contamination",
    "prose-contamination",
    "candidate-comment-contamination",
    "candidate-multi-statement",
    "redaction-violation",
)
PHASE_CATEGORIES = (
    "credential-check",
    "environment",
    "resolver",
    "provider-response",
    "candidate-classification",
    "artifact-redaction",
)

FORBIDDEN_ARTIFACT_TERMS = (
    "Authorization",
    "Bearer",
    "api_key",
    "api-key",
    "sk-",
    "BEGIN PRIVATE KEY",
    "RAW_LEGAL_TEXT_SENTINEL",
    "raw_provider_body_value",
    "raw_response",
    "request_prompt",
    "reasoning_text_value",
    "raw_legal_text_value",
    "falkordb_rows_value",
)
SECRET_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"RAW_LEGAL_TEXT_SENTINEL[^\n\r\t,;}]*"),
)

BOUNDARY_STATEMENT = (
    "This artifact proves only local S03 extraction/classification behavior for provider-shaped "
    "payloads. It does not prove provider generation quality, Legal KnowQL product behavior, "
    "legal-answer correctness, M002 validation, FalkorDB execution, ODT parsing, retrieval quality, "
    "or production graph schema fitness. Raw provider bodies are not persisted."
)
PROSE_SUFFIX_MARKERS = (
    "this ",
    "these ",
    "the query ",
    "it ",
    "here ",
    "explanation",
    "because ",
    "note:",
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compose_endpoint_metadata(endpoint: str) -> dict[str, Any]:
    stripped = endpoint.strip()
    parts = urlsplit(stripped)
    path = parts.path.rstrip("/")
    effective_path = path if path.endswith("/chat/completions") else f"{path}/chat/completions"
    if not effective_path.startswith("/"):
        effective_path = f"/{effective_path}"
    return {
        "endpoint_input": endpoint,
        "effective_chat_completions_url": urlunsplit((parts.scheme, parts.netloc, effective_path, "", "")),
        "preserves_v1": "v1" in effective_path.split("/chat/completions", maxsplit=1)[0].split("/"),
        "model": DEFAULT_MODEL,
    }


def _message_from_provider_shape(decoded: object) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    choices = decoded.get("choices") if isinstance(decoded, dict) else None
    shape = {
        "has_choices": isinstance(choices, list),
        "choice_count": len(choices) if isinstance(choices, list) else 0,
        "has_message": False,
    }
    if not isinstance(choices, list) or not choices:
        return None, shape
    first = choices[0]
    if not isinstance(first, dict):
        return None, shape
    message = first.get("message")
    if not isinstance(message, dict):
        return None, shape
    shape["has_message"] = True
    return cast("dict[str, Any]", message), shape


def _reasoning_summary(message: dict[str, Any] | None) -> dict[str, Any]:
    if message is None:
        return {
            "present": False,
            "separated": False,
            "detail_count": 0,
            "detail_types": [],
            "raw_text_persisted": False,
        }
    details = message.get("reasoning_details")
    content = message.get("reasoning_content")
    present = details is not None or content is not None
    detail_types: list[str] = []
    detail_count = 0
    if isinstance(details, list):
        detail_count = len(details)
        for item in details:
            if isinstance(item, dict) and isinstance(item.get("type"), str):
                detail_types.append(item["type"])
            else:
                detail_types.append(type(item).__name__)
    elif details is not None:
        detail_count = 1
        detail_types.append(type(details).__name__)
    elif content is not None:
        detail_count = 1
        detail_types.append("reasoning_content")
    return {
        "present": present,
        "separated": present,
        "detail_count": detail_count,
        "detail_types": detail_types,
        "raw_text_persisted": False,
    }


def _safe_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _has_comment(text: str) -> bool:
    return "//" in text or "/*" in text or "*/" in text or any(line.lstrip().startswith("--") for line in text.splitlines())


def _has_multi_statement(text: str) -> bool:
    stripped = text.strip()
    if ";" not in stripped:
        return False
    without_final = stripped[:-1] if stripped.endswith(";") else stripped
    return ";" in without_final or not stripped.endswith(";")


def _has_prose_suffix(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    for line in lines[1:]:
        lowered = line.lower()
        if lowered.startswith(PROSE_SUFFIX_MARKERS):
            return True
        if not lowered.startswith(("match ", "call ", "where ", "return ", "with ", "yield ", "limit ", "order ", "and ", "or ", ",", "(")):
            return True
    return False


def classify_candidate_text(content: object) -> dict[str, Any]:
    """Classify candidate text using only whitespace trim before acceptance."""
    if not isinstance(content, str):
        return {
            "accepted": False,
            "root_cause": "provider-schema-mismatch",
            "status": "failed-runtime",
            "starts_with": None,
            "categories": ["malformed-provider-shape"],
            "text_length": 0,
            "trimmed_length": 0,
            "sha256_12": None,
            "has_think_tag": False,
            "has_markdown_fence": False,
            "has_prose_prefix": False,
            "has_prose_suffix": False,
            "has_comment": False,
            "has_multi_statement": False,
            "raw_provider_body_persisted": False,
        }

    stripped = content.strip()
    lowered = stripped.lower()
    starts_with = "MATCH" if stripped.upper().startswith("MATCH") else "CALL" if stripped.upper().startswith("CALL") else "OTHER"
    has_think_tag = "<think" in lowered or "</think" in lowered
    has_markdown_fence = "```" in stripped
    has_prose_prefix = (
        bool(stripped)
        and starts_with == "OTHER"
        and not has_markdown_fence
        and not has_think_tag
        and ("match" in lowered or "call" in lowered or ":" in stripped or len(stripped.split()) > 1)
    )
    has_prose_suffix = starts_with in {"MATCH", "CALL"} and _has_prose_suffix(stripped)
    has_comment = _has_comment(stripped)
    has_multi_statement = _has_multi_statement(stripped)

    categories: list[str] = []
    root_cause = "none"
    if not stripped:
        root_cause = "empty-content"
        categories.append("malformed-content")
    elif has_think_tag:
        root_cause = "reasoning-contamination"
        categories.append("reasoning-tag-contamination")
    elif has_markdown_fence:
        root_cause = "markdown-contamination"
        categories.append("markdown-fence-contamination")
    elif starts_with == "OTHER":
        root_cause = "non-cypher-output"
        categories.append("prose-prefix" if has_prose_prefix else "non-cypher")
    elif has_prose_suffix:
        root_cause = "prose-contamination"
        categories.append("prose-suffix")
    elif has_comment:
        root_cause = "candidate-comment-contamination"
        categories.append("comment-contamination")
    elif has_multi_statement:
        root_cause = "candidate-multi-statement"
        categories.append("multi-statement")

    accepted = root_cause == "none"
    diagnostics: dict[str, Any] = {
        "accepted": accepted,
        "root_cause": root_cause,
        "status": "confirmed-runtime" if accepted else "failed-runtime",
        "starts_with": starts_with if starts_with in {"MATCH", "CALL"} else "OTHER",
        "categories": categories,
        "text_length": len(content),
        "trimmed_length": len(stripped),
        "sha256_12": _safe_hash(stripped) if stripped else None,
        "has_think_tag": has_think_tag,
        "has_markdown_fence": has_markdown_fence,
        "has_prose_prefix": has_prose_prefix,
        "has_prose_suffix": has_prose_suffix,
        "has_comment": has_comment,
        "has_multi_statement": has_multi_statement,
        "raw_provider_body_persisted": False,
    }
    if accepted:
        diagnostics["normalized_text"] = stripped
    return diagnostics


def classify_provider_response(decoded: object) -> dict[str, Any]:
    """Classify an OpenAI-compatible provider-shaped object without persisting raw bodies."""
    message, shape = _message_from_provider_shape(decoded)
    reasoning = _reasoning_summary(message)
    if message is None:
        candidate = classify_candidate_text(None)
        candidate["categories"] = ["malformed-provider-shape"]
        return {
            "accepted": False,
            "status": "failed-runtime",
            "root_cause": "provider-schema-mismatch",
            "phase": "provider-response",
            "provider_shape": shape,
            "candidate": candidate,
            "reasoning": reasoning,
        }

    content = message.get("content")
    candidate = classify_candidate_text(content)
    if not isinstance(content, str):
        candidate["categories"] = ["malformed-provider-shape"]
    return {
        "accepted": bool(candidate["accepted"]),
        "status": candidate["status"],
        "root_cause": candidate["root_cause"],
        "phase": "candidate-classification" if candidate["accepted"] else "provider-response",
        "provider_shape": {**shape, "has_content": isinstance(content, str), "content_kind": "string" if isinstance(content, str) else type(content).__name__},
        "candidate": candidate,
        "reasoning": reasoning,
    }


def boundary_payload() -> dict[str, list[str]]:
    return {
        "proves": [
            "local classification separates reasoning metadata from candidate text",
            "accepted candidate text starts with MATCH or CALL after whitespace trim only",
            "contamination categories are emitted before downstream validation or execution",
        ],
        "does_not_prove": [
            "provider generation quality",
            "Legal KnowQL product behavior",
            "legal-answer correctness",
            "M002 validation acceptance",
            "FalkorDB execution",
            "ODT parsing",
            "retrieval quality",
            "production graph schema fitness",
        ],
        "safety": [
            "raw provider bodies are not persisted",
            "credential-bearing values and authorization material are not persisted",
            "request text, raw reasoning text, raw legal text, and raw FalkorDB rows are not persisted",
            "rejected candidate text is represented only by categories, lengths, booleans, and hashes",
        ],
    }


def base_artifact(*, status: Status, root_cause: str, phase: str, provider_attempts: int) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": status,
        "root_cause": root_cause,
        "phase": phase,
        "status_categories": list(STATUS_CATEGORIES),
        "root_cause_categories": list(ROOT_CAUSE_CATEGORIES),
        "phase_categories": list(PHASE_CATEGORIES),
        "provider_attempts": provider_attempts,
        "endpoint": compose_endpoint_metadata(DEFAULT_ENDPOINT),
        "resolver": {
            "route": "generated PyO3/genai MiniMax OpenAI adapter",
            "normalized_endpoint_expected": "https://api.minimax.io/v1/",
            "metadata_persisted": "categorical-only",
        },
        "safety": {
            "raw_provider_body_persisted": False,
            "credential_persisted": False,
            "auth_header_persisted": False,
            "request_text_persisted": False,
            "raw_reasoning_text_persisted": False,
            "raw_legal_text_persisted": False,
            "raw_falkordb_rows_persisted": False,
        },
        "boundaries": boundary_payload(),
        "non_claims": boundary_payload()["does_not_prove"],
    }


def build_blocked_credential_artifact() -> dict[str, Any]:
    artifact = base_artifact(
        status="blocked-credential",
        root_cause="minimax-credential-missing",
        phase="credential-check",
        provider_attempts=0,
    )
    artifact.update(
        {
            "candidate": classify_candidate_text("") | {"categories": ["not-run"]},
            "reasoning": _reasoning_summary(None),
            "commands": [],
            "credential": {"present": False, "name_persisted": False},
        }
    )
    assert_safe_artifact(artifact)
    return artifact


def build_failed_runtime_artifact(
    *, root_cause: str, phase: str, classification: dict[str, Any], provider_attempts: int, commands: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    artifact = base_artifact(
        status="failed-runtime",
        root_cause=root_cause,
        phase=phase,
        provider_attempts=provider_attempts,
    )
    artifact.update(
        {
            "candidate": classification.get("candidate", classify_candidate_text(None)),
            "reasoning": classification.get("reasoning", _reasoning_summary(None)),
            "provider_shape": classification.get("provider_shape", {}),
            "commands": commands or [],
        }
    )
    artifact["candidate"].pop("normalized_text", None)
    assert_safe_artifact(artifact)
    return artifact


def build_confirmed_runtime_artifact(
    *, classification: dict[str, Any], provider_attempts: int, commands: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    if not classification.get("accepted"):
        raise ValueError("confirmed runtime requires an accepted classification")
    artifact = base_artifact(
        status="confirmed-runtime",
        root_cause="none",
        phase="candidate-classification",
        provider_attempts=provider_attempts,
    )
    artifact.update(
        {
            "candidate": classification["candidate"],
            "reasoning": classification["reasoning"],
            "provider_shape": classification.get("provider_shape", {}),
            "commands": commands or [],
        }
    )
    assert_safe_artifact(artifact)
    return artifact


def assert_safe_artifact(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError("refusing to write secret-like artifact content")
    for term in FORBIDDEN_ARTIFACT_TERMS:
        if term in text:
            raise ValueError(f"refusing to write forbidden artifact term: {term}")
    if "normalized_text" in payload.get("candidate", {}) and payload.get("status") != "confirmed-runtime":
        raise ValueError("rejected candidates must not persist normalized_text")


def render_markdown(payload: dict[str, Any]) -> str:
    candidate = payload.get("candidate", {}) if isinstance(payload.get("candidate"), dict) else {}
    reasoning = payload.get("reasoning", {}) if isinstance(payload.get("reasoning"), dict) else {}
    lines = [
        "# M003/S03 Reasoning-Safe Candidate",
        "",
        f"- Schema: `{payload.get('schema_version')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Root cause: `{payload.get('root_cause')}`",
        f"- Phase: `{payload.get('phase')}`",
        f"- Provider attempts: `{payload.get('provider_attempts')}`",
        f"- Candidate accepted: `{candidate.get('accepted')}`",
        f"- Candidate starts with: `{candidate.get('starts_with')}`",
        f"- Think-tag contamination: `{candidate.get('has_think_tag')}`",
        f"- Markdown fence contamination: `{candidate.get('has_markdown_fence')}`",
        f"- Prose prefix: `{candidate.get('has_prose_prefix')}`",
        f"- Prose suffix: `{candidate.get('has_prose_suffix')}`",
        f"- Raw body persisted: `{candidate.get('raw_provider_body_persisted')}`",
        f"- Reasoning present: `{reasoning.get('present')}`",
        f"- Reasoning separated: `{reasoning.get('separated')}`",
        f"- Reasoning raw text persisted: `{reasoning.get('raw_text_persisted')}`",
        "",
        BOUNDARY_STATEMENT,
        "",
        "## Boundaries",
        "",
        "### Proves",
        *[f"- {item}" for item in payload.get("boundaries", {}).get("proves", [])],
        "",
        "### Does not prove",
        *[f"- {item}" for item in payload.get("boundaries", {}).get("does_not_prove", [])],
        "",
        "### Safety",
        *[f"- {item}" for item in payload.get("boundaries", {}).get("safety", [])],
        "",
    ]
    markdown = "\n".join(lines)
    assert_safe_artifact({"markdown_summary": markdown})
    return markdown


def write_artifacts(output_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    assert_safe_artifact(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / JSON_ARTIFACT
    markdown_path = output_dir / MARKDOWN_ARTIFACT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--fixture", choices=("clean", "blocked-credential"), default="clean")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.fixture == "blocked-credential":
        artifact = build_blocked_credential_artifact()
    else:
        classification = classify_provider_response(
            {"choices": [{"message": {"content": "MATCH (article:Article) RETURN article.id LIMIT 5"}}]}
        )
        artifact = build_confirmed_runtime_artifact(classification=classification, provider_attempts=0, commands=[])
    write_artifacts(args.artifact_dir, artifact)
    print(json.dumps({"status": artifact["status"], "root_cause": artifact["root_cause"]}, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
