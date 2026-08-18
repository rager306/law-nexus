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

**Accepted [bounded]** for the current **contains + bounded morph variants +
AND/OR scoring** subset (YAML templates, best-score-wins). Path-aware
classification composes `load_profiles` / `detect_profile` / `apply_boost` in
CLI and multi-edition flows; the compatibility wrapper uses the deterministic
default profile. YAML manifest sections (`link_classifiers`,
`classifier_templates`, `document_profiles`) are scanned with a bounded
sibling-key stop at section indentation, so sibling sections cannot leak into
each other. Proximity, prefix, regex, position, profile-restricted
templates, and top-2 closest-template backlog remain `[proposed]`.
`consru_export` classification counts are local `[smoke]`, skip-capable, not
promotion proof (R082). No `[validated]` promotion.

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
lives in YAML and the Rust engine interprets it. The contains+bounded-morph AND/OR
scoring and profile-confidence composition are `[bounded]`; remaining
signals/layers stay `[proposed]`.

### Layer 1: Document profiles `[bounded]` confidence composition

`classify_all_scored_for_path` detects a profile and applies its confidence
boost to the winning known classification. CLI inspect and multi-edition
processing pass the actual source path; `classify_all_scored` remains a
compatibility wrapper using the deterministic default profile. Profiles do not
change the legal kind. Each document type gets a profile that:
- Identifies the type from path/title needles (YAML)
- Applies a `confidence_boost` multiplier
- Does not yet select which templates are active; profile-restricted
  template routing remains `[proposed]`

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

Shipped `[bounded]` signals are `contains` and a bounded `morph_needles`
variant list. Morph variants use exact configured substring containment and
are not general linguistic morphology. Proximity, prefix, regex and position
remain `[proposed]`. Target: each template is composed
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

### Layer 3: Scoring engine `[bounded]` contains+morph AND/OR subset

The shipped engine **scores** every template on `contains` needles plus one
optional bounded morph signal (matched when any configured variant occurs).
AND (`match_all`) requires every signal; OR scales confidence by
matched/total. Highest score wins; ties are broken by YAML order. The winning
known classification is multiplied by `profile.confidence_boost`; `unknown`
remains at the explicit 0.1 baseline.

Shipped formula:

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
Shipped templates use `contains` needles, optional `morph_needles`, and
AND/OR scoring `[bounded]`.

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
   plus bounded `morph_needles` variants with AND/OR scoring. Proximity,
   prefix, regex, position, and profile restrictions remain `[proposed]`.
   Deterministic and YAML-driven
   for the shipped subset. The agent may employ NLP offline to PROPOSE
   templates; the parser applies shipped templates online to CLASSIFY.

## Consequences

- `classifier.rs` gains a `[bounded]` contains+bounded-morph AND/OR scoring
  engine (best-score-wins on the scored path; first-match-wins remains as
  fallback).
- YAML `classifier_templates` drive the shipped subset; a full four-layer
  `classifier_manifest` remains `[proposed]`.
- YAML manifest sections are isolated by indentation: every scanner stops at
  the next sibling mapping key at the heading's indent or at a shallower key;
  list items are not sibling keys. Sibling sections cannot leak into each
  other.
- Path-aware scoring composes document-profile confidence boost; profiles
  remain heuristic and cannot change classification kind or legal authority.
- Unknown-link observation store exists; top-2 closest-template backlog
  remains `[proposed]`. `consru_export` unknown counts are local `[smoke]`.
- Profile-restricted templates (e.g. court-only `руководствуясь`) remain
  `[proposed]` and do not yet prevent false positives by profile.
- New document types can receive confidence boosts through YAML profiles;
  profile-restricted template routing remains `[proposed]`.

## Review 8 amendments (2026-08-18, M171-nr6y51)

### R8-07: structural probe as detection factor B

Review 8 (`doc/review/review-17-08-2026.md` R8-07) requires **two-factor
group detection**: factor A is catalog metadata (path/kind/type needles with
rank) and factor B is a structural probe (presence of `statya`, numbering
distribution). ~10 % of laws carry no `statya` markers (small / ratification /
"punkt-only" acts), so metadata alone cannot detect the group.

Factor A is `[bounded]` YAML data today (`kb-ontology.yaml`
`document_groups` needles). Factor B — the structural probe — is `[proposed]`:
when it lands it composes into `detect_profile` as a deterministic second
signal, mirroring how Layer 1 profile confidence composition stays
YAML-driven. A conflict between factors fails closed to `Unknown` — the
classifier never guesses the group. The probe is a detection signal, not a
classification-kind change: it does not alter amends/cites/implements
scoring, the legal kind, or profile authority (Layer 1 boundary unchanged).

## Non-claims

- `[bounded]` covers only the shipped contains+bounded-morph AND/OR scoring
  and profile-confidence composition. Proximity, prefix, regex, position,
  profile restrictions, and top-2 backlog remain `[proposed]`.
- Path needles and confidence boosts are heuristic, not legal
  type-classification authority; they never change classification kind.
- Morphological matching is a configured variant list (`в ред.`, `в редакции`,
  `редакции`), not a full Russian NLP morphology engine.
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
