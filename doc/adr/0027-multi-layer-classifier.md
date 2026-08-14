---
id: ADR-0027
title: Multi-layer manifest classifier for document-specific link classification
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-14
supersedes: none
related: [ADR-0025, ADR-0026, ADR-0019, ADR-0013]
---

# ADR-0027: Multi-layer manifest classifier for document-specific link classification

## Status

**Accepted [bounded]** — scoring engine shipped with AND/OR multi-signal
logic. Verified on real 44-ФЗ corpus: 3641 classified links, 1025 amends,
1223 cites, 209 implements, 502 unknown patterns in learning backlog.
Document profiles and morph signals are `[proposed]` (not yet implemented).
Moves to `[validated]` when cross-edition validation confirms edge accuracy.

## Context

The initial link classifier (`classifier.rs` in `ln-consultant-parser`)
uses single-signal `contains(needle)` matching with first-match-wins. On
the real 44-ФЗ corpus this classifies 3641 links (1025 amends, 1416 cites,
47 implements, 1153 unknown).

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

Implement a **four-layer manifest-driven classifier** where all logic lives
in YAML and the Rust engine interprets it.

### Layer 1: Document profiles

Each document type gets a profile that:
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

Each template is composed of **signals** — atomic checks described in YAML:

| Signal type | YAML fields | Rust check |
|---|---|---|
| `proximity` | `needle, max_distance` | context.contains + distance |
| `contains` | `needle` | text.contains |
| `prefix` | `needle` | text.starts_with |
| `morph` | `needle, variants` | variants.any(contains) |
| `regex` | `pattern` | compiled match |
| `position` | `at: start/end` | link position in paragraph |

A template specifies `match_mode: all` (AND) or `match_mode: any` (OR).

### Layer 3: Scoring engine

Instead of first-match-wins, the engine **scores** every template:

```
template_score = base_confidence
  × Π(signal_match: 1.0 if match, 0.0 if not)
  × profile.confidence_boost
```

- If `match_mode: all`: all signals must match (product = 0 if any fails)
- If `match_mode: any`: at least one signal must match (product > 0)
- Highest score wins; ties broken by YAML order
- Below `unknown_threshold` (default 0.3) → `unknown` classification

### Layer 4: Learning backlog

Links classified as `unknown` (score < threshold) are recorded:
- Link text, context, occurrence count
- Top-2 closest templates and their scores
- Status: `candidate` for agent review

The agent (human or LLM) reads the backlog, proposes new templates, and
updates the YAML manifest. The system improves with each cycle.

### Template structure

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
3. **Manifest signals** `[proposed]`: deterministic, composable, YAML-driven, fast,
   auditable. The agent employs NLP offline to PROPOSE templates; the parser
   applies templates online to CLASSIFY.

## Consequences

- `classifier.rs` gains a scoring engine (no first-match-wins).
- YAML `classifier_manifest` section replaces flat `link_classifiers`.
- Document profiles enable type-specific templates.
- Unknown links (1153 in 44-ФЗ) become learning backlog, not lost data.
- Templates are composable: multi-signal AND/OR logic per template.
- Profile-restricted templates (e.g. court-only `руководствуясь`) prevent
  false positives in other document types.
- The classifier is **omnivorous**: new document types = new profiles +
  new templates in YAML, without Rust changes.

## Non-claims

- `[proposed]` design: scoring engine not yet implemented.
- Document profiles are heuristic (path/title needles), not legal type
  classification authority.
- Morphological matching is variant-list-based, not full Russian NLP
  morphology engine.
- Learning backlog observations are candidates for human/agent review,
  not auto-promoted YAML patches without a gate.
- `regex` signal type requires careful YAML input validation to avoid
  ReDoS or invalid patterns.

## References

- ADR-0025 (Consultant parser crate)
- ADR-0026 (RuVector agent memory)
- ADR-0019 (cross-act edge kinds)
- ADR-0013 (provider isolation)
