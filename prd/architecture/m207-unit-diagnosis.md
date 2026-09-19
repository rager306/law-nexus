# M207 unit diagnosis — WordML cut vs complete reference

**Status:** `[bounded]` overlay. Not gold, not a human pilot, not a Pullenti port.
**Does not rewrite** the frozen 180-fragment seed, the S01 codebook, or M207
submissions. Runtime stop remains active.

Executable gate: `uv run python scripts/m207_unit_diagnosis.py check`
(marker `M207_UNIT_DIAGNOSIS_OK`). Record:
`prd/migration/rust-evidence/m207-unit-diagnosis.json`.

## What was wrong

M207 asked two humans to code **one XML paragraph** as **one reference**.
Harvest (`block_is_reference_shaped` over a single `w:p`) selected any block
that *looked* like a cite. Consultant then splits long «(в ред. … от DATE N,
от DATE N, …)» lists across consecutive paragraphs. The coder therefore saw
a head with no closing parenthesis, or a tail `от 09.08.2022 N 1397, …`
with no TYPE.

That is the same class of defect as early NPA work: **insufficient context,
incorrect cut, incomplete text** — not “we lacked two lawyers”.

On the frozen 180:

| Observation | Count |
|---|---|
| unique texts | 143 / 180 (28 duplicate groups) |
| complete edition notes | 36 |
| incomplete series members | 20 |
| orphan `от DATE N` tails | 11 |
| in-text cites (`настоящ` / статьи) | 32 |
| document titles | 17 |
| power-of-attorney / not a norm cite | 8 |
| edition-list series reconstructed from adjacent same-document blocks | **10 series / 27 members** |

The M207 40-case draw inherited the cut: 37 unique texts, 8 truncated, 6
sitting on a glue pair (cases 11, 15, 19, 32, 40 and neighbours).

## What Pullenti actually does (orientation only, D380)

Local snapshot `/root/vendor-source/pullenti` (Lingvo 4.34):

- `AnalysisKit` + `Sofa` keep **one token chain over the whole document**.
  A WordML paragraph break is `IsNewlineBefore`, not a new document.
- `DecreeToken.ItemType.Edition` parses `(в ред. …)` including a bracketed
  list (`DecreeToken.cs` around the `_isEdition` / `BracketHelper` path).
- Elliptical members `от DATE N` inherit TYPE/ORG from the list head.
  Four DECREE on `npa-frag-050`-class lists is the documented observation
  in ADR-0028, not a product oracle.
- Nested changes use an explicit `changeStack`, not a second span minted
  across blocks.

**Not adopted:** vendor code, dictionaries, thresholds, SemanticService,
agreement-with-Pullenti as gold or as a second coder (RC28-F14 / D380).

## Orientation in evaluation (not cancelled)

D380 is not only «how to cut». It also keeps Pullenti as a **diagnostic
third extractor** on a bounded identifying sample after owner confirmation:
license-gated, `/tmp` rater allowed, product runtime forbidden. Ident40
already used that orientation: Pullenti four DECREE on elliptical tails vs
sol concatenating FZ vs spark writing «Федеральных законов» onto members vs
Agnes empty-parse (D383). Those dumps are **disagreement maps**, not gold
and not a second human coder.

M207 S03 machinery **consciously did not schedule** a Pullenti-differential
inside execute-task (F14 optional / license-gated; hard stop on code,
dictionaries, thresholds). That is «do not run the vendor in CI», not
«forget the orientation». Evaluation still has three layers:

1. **Human** two-pass + adjudication — the only independent-measured
   reference (S02/S03). Absent → `not-measured`.
2. **Pullenti (and the ident40 extractors)** — optional diagnostic overlay
   on *complete* coding units once the unit diagnosis is applied. Compare
   slots/TYPE inheritance/series membership. Never a rater, never α, never
   `independent-measured`.
3. **law-nexus parser** — system quality is out of M207 S03 by construction
   (`model_invoked=false`, framing rater-vs-resolved-reference).

git-lex-kit-acp is ontology/health for git-lex (archive). The old
`parsing_prompt.yaml` extracts **act hierarchy** (глава/статья), not
LawRef slots. They stay orientation for *other* contours, not M207 gold.

## What law-nexus already specified and did not use in the pilot

`prd/architecture/npa-document-context.yaml` (D385) already forbids the
naive fix and names the right one:

- allowed: `adjacent_blocks`, `open_series_head`
- forbidden: concatenate the document into parser input; fabricate a
  **cross-block TextAnchor**

M207 S01 nevertheless offered `start=0, end=byte_len` on each isolated
fixture and forbade narrowing (distant supervision). That honesty is
correct **inside a complete unit**. It is the wrong unit when the fixture
is half a list.

## Adaptation (do this; do not run the old 40)

1. **Keep the frozen seed.** Do not enlarge 180, do not rewrite `.txt`.
2. **Coding unit** = one complete reference occurrence, **or** one complete
   edition-list series whose members are adjacent same-document blocks.
   Display may join for the coder; the span of each member stays
   fragment-local. No merged TextAnchor.
3. **Do not send humans** `incomplete-series-member` or `orphan-tail`
   fragments as standalone cases. Show the diagnosed series instead.
4. **Split genres** before measuring α: consultant-ed-note / in-text cite /
   document-title / not-a-norm-reference. Mixing them made disagreement
   about the *task*, not about the parser.
5. **Duplicates** (28 groups) code once.
6. **Context** for elliptical tails is `open_series_head` (D385), not
   “paste the previous file into the packet”.

Until a new draw uses this overlay, M207 stays `needs-attention` for the
honest reason: machinery ready, **unit of coding not adapted**, human gold
absent. This document does not close that gate.
