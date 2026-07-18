"""Source profile loader port (declarative Layer 2 per proposal 26 §3).

A source profile declares: format, structure, style_map, zones for a
source family. The profile is data-only — extraction engine logic is
in adapters (e.g. consultant_hierarchy.py). Universality claim: adding
a new source family = adding a profile + a thin adapter, not a new engine.

This module is the loader port only. It does NOT drive extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

# Type alias matching the ConsultantHierarchyLevel literal from parser_records
LevelName = str

@dataclass(frozen=True)
class CharNormalizationRule:
    """One regex-based character normalization rule."""

    pattern: str
    replacement: str
    description: str = ""

@dataclass(frozen=True)
class FormatSpec:
    """Format declaration: namespace, root element, char normalization rules."""

    namespace: str
    root_element: str
    paragraph_element: str
    document_properties_element: str = ""
    title_element: str = ""
    content_member: str = ""
    char_normalization: tuple[CharNormalizationRule, ...] = ()
    iterparse: bool = True
    iterparse_clear: bool = True

@dataclass(frozen=True)
class StructureSpec:
    """Structure declaration: ordered level ladder + marker regex families."""

    ladder: tuple[LevelName, ...]
    marker_patterns: dict[str, str] = field(default_factory=dict)
    numbering_formats: dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class StyleMapSpec:
    """Style -> level hint mapping (e.g. Consultant style \"5\" = document)."""

    mapping: dict[str, LevelName]
    default: LevelName = "body_text"

@dataclass(frozen=True)
class ZoneSpec:
    """Zone declaration: preamble or appendix with marker trigger."""

    marker: str | None
    trigger: str

@dataclass(frozen=True)
class SourceProfile:
    """Declarative source profile loaded from YAML."""

    source_kind: str
    source_label: str
    format: FormatSpec
    structure: StructureSpec
    style_map: StyleMapSpec
    zones: dict[str, ZoneSpec] = field(default_factory=dict)
    non_claim: str = ""

def _parse_char_normalization(rules: list[dict[str, Any]]) -> tuple[CharNormalizationRule, ...]:
    return tuple(
        CharNormalizationRule(
            pattern=str(rule["pattern"]),
            replacement=str(rule["replacement"]),
            description=str(rule.get("description", "")),
        )
        for rule in rules
    )

def load_profile(path: Path | None = None, *, source_kind: str | None = None) -> SourceProfile:
    """Load a source profile from YAML.

    Defaults to prd/parser/profiles/consultant_wordml.yaml. If ``source_kind``
    is given (e.g. "garant-odt"), loads the matching profile under
    prd/parser/profiles/<source_kind>.yaml. Validates required keys
    (format, structure, style_map, zones) and that the structure.ladder
    is a non-empty list of valid level names.
    """

    if path is None:
        profiles_dir = Path(__file__).resolve().parents[3] / "prd" / "parser" / "profiles"
        if source_kind is None:
            source_kind = "consultant_wordml"
        # Translate source_kind (e.g. "garant-odt") to filename
        # (e.g. "garant_odt.yaml").
        filename = source_kind.replace("-", "_") + ".yaml"
        path = profiles_dir / filename
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    source_kind = str(data["source_kind"])
    source_label = str(data["source_label"])

    fmt = data["format"]
    char_norm = _parse_char_normalization(fmt.get("char_normalization", []))
    format_spec = FormatSpec(
        namespace=str(fmt["namespace"]),
        root_element=str(fmt["root_element"]),
        paragraph_element=str(fmt["paragraph_element"]),
        document_properties_element=str(fmt.get("document_properties_element", "")),
        title_element=str(fmt.get("title_element", "")),
        content_member=str(fmt.get("content_member", "")),
        char_normalization=char_norm,
        iterparse=bool(fmt.get("iterparse", True)),
        iterparse_clear=bool(fmt.get("iterparse_clear", True)),
    )

    struct = data["structure"]
    ladder_data = struct["ladder"]
    if not isinstance(ladder_data, list) or not ladder_data:
        raise ValueError("structure.ladder must be a non-empty list")
    ladder = tuple(level for level in ladder_data)
    structure_spec = StructureSpec(
        ladder=ladder,  # type: ignore[arg-type]
        marker_patterns=dict(struct.get("marker_patterns", {})),
        numbering_formats=dict(struct.get("numbering_formats", {})),
    )

    style_data = data["style_map"]
    # Support two style_map shapes:
    # - flat dict (Consultant): {"5": "document", "2": "section_heading", ...}
    # - nested (Garant ODT): {"default": "body_text", "observed": ["s1", "s3", ...]}
    if isinstance(style_data, dict) and "observed" in style_data:
        observed_list = style_data.get("observed", [])
        mapping = {name: "body_text" for name in observed_list}
        default_level = str(style_data.get("default", "body_text"))
    else:
        mapping = dict(style_data)
        default_level = str(style_data.get("default", "body_text"))
    style_map_spec = StyleMapSpec(
        mapping=mapping,
        default=default_level,
    )

    zones_data = data.get("zones", {})
    zones_spec = {
        name: ZoneSpec(marker=spec.get("marker"), trigger=str(spec.get("trigger", "")))
        for name, spec in zones_data.items()
    }

    return SourceProfile(
        source_kind=source_kind,
        source_label=source_label,
        format=format_spec,
        structure=structure_spec,
        style_map=style_map_spec,
        zones=zones_spec,
        non_claim=str(data.get("non_claim", "")),
    )
