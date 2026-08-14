---
id: ADR-0027
title: Multi-layer manifest classifier for document-specific link classification
status: Accepted
lifecycle: "[bounded]"
date: 2026-08-14
supersedes: none
related: [ADR-0025, ADR-0026, ADR-0019, ADR-0013]
---

# ADR-0027: Multi-layer manifest classifier for document-specific link classification

## Status

**Accepted [bounded]** only for the current **contains + AND/OR scoring**
subset (YAML templates, best-score-wins). Document-profile functions exist
(`load_profiles` / `detect_profile` / `apply_boost`) but are **not composed**
into `classify_all_scored`. Morph, proximity, prefix, regex, position,
profile-restricted templates, and top-2 closest-template backlog remain
`[proposed]`. `consru_export` classification counts are local `[smoke]`,
skip-capable, not promotion proof (R082). No `[validated]` promotion.

## Context

The initial link classifier (`classifier.rs` in `ln-consultant-parser`)
uses single-signal `contains(needle)` matching with first-match-wins. A
local `[smoke]` `consru_export` 44-ФЗ run (skip-capable, not promotion
proof) classified 3641 links (1025 amends, 1416 cites, 47 implements,
1153 unknown).

However, Russian legal documents have **diverse structures** across types:

| Document type | Amendment pattern | Citation pattern | Special |
|---|---|---|---|
| ФЗ | `(в ред. ФЗ от DD.MM.YYYY N XXX-ФЗ)` | `согласно статье N` | inline in article |
| ПП РФ | `внести изменения в...` | `на основании ФЗ` | title ≠ body |
| Приказ | — | `во исполнение ФЗ` | departmental style |
| Кодекс | `абзац утратил силу` | `настоящим Кодексом` | self-references |
| Суд. практика | — | `руководствуясь статьей...` | link = justification |
| Обзор | — | mass references | 4500 in one file |

A single `contains("в ред.")` classifier misses court decisions
(`руководствуясь`), government resolutions (`внести изменения`), and
morphological variants (`в ред.` vs `в редакции` vs `редакции`).

## Decision

Target design: a **four-layer manifest-driven classifier** where all logic
lives in YAML and the Rust engine interprets it. Only the contains+AND/OR
scoring subset is `[bounded]`; remaining layers/signals stay `[proposed]`.

### Layer 1: Document profiles `[proposed]` composition

Functions exist (`load_profiles` / `detect_profile` / `apply_boost`) but
are not composed into `classify_all_scored`. Target: each document type
gets a profile that:
- Identifies the type from path/title needles (YAML)
- Applies a `confidence_boost` multiplier
- Selects which templates are active (some templates are profile-restricted)

```yaml
document_profiles:
  federal_law:
    path_needles: [federalnyi-zakon, law_]
    confidence_boost: 1.0
  government_act:            # постановления И распоряжения Правительства
    path_needles: [postanovlenie-pravitelstva, rasporyazhenie-pravitelstva, resolution_, directive_]
    confidence_boost: 0.9
  departmental_act:
    path_needles: [prikaz-, order_, instruktsiya]
    confidence_boost: 0.85
  court_decision:
    path_needles: [postanovlenie-arbitrazhnogo, opredelenie]
    confidence_boost: 0.8
  default:
    confidence_boost: 0.7
```

Постановления и распоряжения Правительства — **оба нормативные акты**
(иерархия: ФКЗ > ФЗ > указы Президента > постановления и распоряжения
Правительства > ведомственные акты). Оба отнесены к `government_act`
с одинаковым boost 0.9; различие постановление/распоряжение сохраняется
как subtype в полном документном типе, но не влияет на classification boost.

### Layer 2: Signal matchers

Shipped `[bounded]` signal is `contains` only. Proximity, prefix, morph,
regex and position remain `[proposed]`. Target: each template is composed
of **signals** — atomic checks described in YAML:

| Signal type | YAML fields | Rust check |
|---|---|---|
| `proximity` | `needle, max_distance` | context.contains + distance |
| `contains` | `needle` | text.contains |
| `prefix` | `needle` | text.starts_with |
| `morph` | `needle, variants` | variants.any(contains) |
| `regex` | `pattern` | compiled match |
| `position` | `at: start/end` | link position in paragraph |

A template specifies `match_mode: all` (AND) or `match_mode: any` (OR).

### Layer 3: Scoring engine `[bounded]` contains+AND/OR subset

The shipped engine **scores** every template on `contains` needles:
AND (`match_all`) requires all needles; OR scales confidence by
matched/total. Highest score wins; ties broken by YAML order.
`profile.confidence_boost` is `[proposed]` and is not applied on the
shipped path.

Target formula (boost not composed today):

```
template_score = base_confidence
  × Π(signal_match: 1.0 if match, 0.0 if not)
  × profile.confidence_boost   # [proposed]; not applied
```

- If `match_mode: all`: all signals must match (product = 0 if any fails)
- If `match_mode: any`: at least one signal must match (product > 0)
- Highest score wins; ties broken by YAML order
- Below `unknown_threshold` (default 0.3) → `unknown` classification

### Layer 4: Learning backlog

Unknown-link observation store exists `[bounded]` (text/context/count).
Top-2 closest templates and their scores remain `[proposed]`.
Target records:
- Link text, context, occurrence count
- Top-2 closest templates and their scores `[proposed]`
- Status: `candidate` for agent review

The agent (human or LLM) reads the backlog, proposes new templates, and
updates the YAML manifest. The system improves with each cycle.

### Template structure

Target YAML vocabulary `[proposed]` for proximity/profile restrictions.
Shipped templates use `contains` needles + AND/OR only `[bounded]`.

```yaml
templates:
  amends_fz_amendment_note:
    classification: amends
    base_confidence: 0.9
    match_mode: all
    signals:
      - {type: proximity, needle: "в ред.", max_distance: 80}
      - {type: proximity, needle: "ФЗ", max_distance: 60}

  cites_governed_by:
    classification: cites
    base_confidence: 0.8
    match_mode: any
    profiles: [court_decision]  # only active for court docs
    signals:
      - {type: proximity, needle: "руководствуясь", max_distance: 80}
```

### Why not regex/NLP

1. **Regex**: fragile against Russian morphology, hard to maintain in YAML,
   no composition (AND/OR).
2. **NLP/LLM**: heavyweight, non-deterministic, requires API calls, not
   YAML-configurable. Suitable for the **agent** layer (proposing new
   templates from unknown backlog), not the **parser** layer.
3. **Manifest signals**: the shipped `[bounded]` subset is `contains` needles
   with AND/OR scoring. Proximity, prefix, morph, regex, position, and
   profile restrictions remain `[proposed]`. Deterministic and YAML-driven
   for the shipped subset. The agent may employ NLP offline to PROPOSE
   templates; the parser applies shipped templates online to CLASSIFY.

## Consequences

- `classifier.rs` gains a `[bounded]` contains+AND/OR scoring engine
  (best-score-wins on the scored path; first-match-wins remains as fallback).
- YAML `classifier_templates` drive the shipped subset; a full four-layer
  `classifier_manifest` remains `[proposed]`.
- Document-profile functions exist but are not composed into scoring.
- Unknown-link observation store exists; top-2 closest-template backlog
  remains `[proposed]`. `consru_export` unknown counts are local `[smoke]`.
- Profile-restricted templates (e.g. court-only `руководствуясь`) remain
  `[proposed]` and do not yet prevent false positives by profile.
- New document types still require composition work before profiles affect
  classification; YAML-only omnivorous routing is `[proposed]`.

## Non-claims

- `[bounded]` covers only the shipped contains+AND/OR scoring subset.
  Morph, proximity, prefix, regex, position, profile restrictions, and
  top-2 backlog remain `[proposed]` — not implemented in the scoring path.
- Document-profile functions are not composed into classification; path
  needles are heuristic, not legal type-classification authority.
- Morphological matching, if added later, is variant-list-based, not a
  full Russian NLP morphology engine.
- Learning backlog observations are candidates for human/agent review,
  not auto-promoted YAML patches without a gate. Top-2 closest templates
  are not recorded today.
- `regex` signal type is `[proposed]` and, if added, requires YAML input
  validation to avoid ReDoS or invalid patterns.
- `consru_export` classification counts are local `[smoke]`, skip-capable,
  not durable bounded or `[validated]` proof (R082).
- No legal correctness, citation authority, or `[validated]` promotion.

## References

- ADR-0025 (Consultant parser crate)
- ADR-0026 (RuVector agent memory)
- ADR-0019 (cross-act edge kinds)
- ADR-0013 (provider isolation)
