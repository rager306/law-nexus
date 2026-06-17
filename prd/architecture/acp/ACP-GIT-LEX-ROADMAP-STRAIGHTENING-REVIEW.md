# ACP / git-lex roadmap straightening review

## Status

Authoritative review and direction change. Produced after M063-qp7ial closeout.
Formalized by decision D084. Supersedes the bounded-pilot / shadow-forever direction
encoded in D080-D083 as the *active* roadmap; preserves the legitimate correctness
boundaries (authority model, R035/R037/R038 source/runtime gates).

This is a review artifact, not a proof. It does not validate R035/R037/R038 and does
not by itself approve main `.lex` adoption — it commits to an *adoption-oriented*
sequence whose first step is closing the M058 root cause.

## TL;DR

The project is stuck because it optimized the wrong objective. The stated goal is
"git-lex as the architectural foundation for ACP" (authoritative, installed,
reusable for law-nexus and other projects). The operating regime encoded across
M035-M063 and decisions D067-D083 is the opposite: "git-lex must never be source
truth, must never touch the main repo, must stay a disposable-workspace shadow
diagnostic." A thing cannot be a *foundation* while being forbidden from being
authoritative, from being installed, and from existing outside `/tmp`.

Compounding this, the single concrete technical blocker (M058: generated SHACL
shapes are underconstrained) was never fixed. Verified post-M063:
`git-lex-kit-acp/ontology/acp/acp.ttl` has 0 `sh:datatype`, 0 `sh:in`,
0 `sh:minCount`, and 0 OWL restrictions. Five milestones after M058 identified the
fix, it is still open — each milestone "preserved" it as a known limitation instead
of resolving it.

## A. Why the "giant" does not move

### A1. The root cause is known, concrete, and unrepaired

M058 pinpointed the cause: generated SHACL shapes lack `sh:datatype`/`sh:in`/
`sh:minCount`, so `git-lex validate` accepts almost anything. The fix is bounded
(M058/S03 listed it): strengthen the ontology, regenerate shapes, build true
negative fixtures, prove `git-lex validate` exits non-zero on bad records. Current
`acp.ttl` confirms it was never done.

### A2. The decision -> pilot -> decision loop around the same hole

- **M057** found a validation issue, overstated it.
- **M058** narrowed the root cause precisely. Did not fix it.
- **M062/S03** adapter-fitness decision = limited-pilot; explicitly rejected "go"
  because "M058 root cause is not resolved" — but planned no milestone to resolve it.
- **M063** ran the pilot. Outcome: pass with bounded evidence, hard validation gate
  *still blocked per M058* — i.e. it documented the bug instead of fixing it.
- **continue.md** proposes **M064** as another *decision* milestone about the same
  blocked L2.

Each cycle adds a governance layer (evidence matrices, state+rollback contracts,
halt analyses, wording contracts) around a hole nobody closes.

### A3. Proof-before-foundation inversion

The regime demands git-lex *prove* it is a trustworthy source-truth store before it
is *allowed* to be one. Trustworthiness cannot be proven without first committing to
use it. The loop is self-reinforcing: cannot adopt until proven, cannot prove until
adopted. This is why no amount of proof unblocks anything.

## B. Deviations and architectural errors (with evidence)

| # | Deviation | Evidence |
|---|-----------|----------|
| B1 | The real blocker is never fixed. M058-fix not executed across 5 milestones. | `acp.ttl`: 0 datatype/in/minCount now. M058/S03 listed the fix. |
| B2 | Disposable-workspace-only regime blocks adoption by construction. git-lex is not installed; rebuilt from source in `/tmp` for every proof. | `git lex` -> "not a git command". All runtime proofs are source-built in `/tmp`. |
| B3 | "Shadow diagnostic" ceiling set by M055 and preserved by every successor. L2 "blocked until human approval", but approval is never asked as approval — only as approval of *another decision milestone*. | D080; M062/S03 rejected "go"; M063; continue.md. |
| B4 | Governance weight >> product. ~25 ACP/git-lex milestones vs tiny deliverables (ACP-kit 9 files, law-nexus-kit 15 files, ~8 verify scripts). | `git-lex-kit-acp/`, `git-lex-kit-law-nexus/`, `scripts/verify-*.py`. |
| B5 | "Universal reusable core" is unproven. Every proof is law-nexus-specific. No proof on a second, different project — yet reuse for other projects is the stated goal. | M061/S01-S05, M063 all use paired ACP + law-nexus fixtures. |
| B6 | Existing git-lex patterns are not reused. `/root/vendor-source` ships working reference kits (`git-lex-kit-autoknow` adaptive Source/Entity + subagent extraction, `soul`, `squad`) that demonstrate real adaptive extraction; they are inspected as prior art but their mechanics are not adopted. | git-lex skill quick_start enumerates vendor kits. |

## C. Straightened roadmap

Principle: replace bounded pilots and decision loops with real adoption milestones,
ordered foundation-first. Reverse the current order: close the hole and lay the
foundation, then prove the rest.

- **Stage 0 — Direction decision [DONE, D084].** git-lex role = foundation/source-truth
  for ACP. Records are authoritative when category + lifecycle state + evidence anchor +
  proof gate (or accepted decision) are explicit (the model already exists, D072).

- **Stage 1 — Close the M058 root cause [milestone M064].** Strengthen `acp.ttl`
  (`sh:datatype`/`sh:in`/`sh:minCount` or OWL restrictions), regenerate shapes, build
  true negative fixtures that survive `frontmatter_to_turtle` normalization, prove
  `git-lex validate` exits non-zero with actionable diagnostics. This is the gate every
  prior decision pointed at and nobody executed.

- **Stage 2 — Install git-lex for real.** Pin a version; make `git lex` a real command
  in the environment; stop the source-build-in-`/tmp` ritual. Close supply-chain /
  binary trust (M051/S09): fix the provenance source and binary verification.

- **Stage 3 — Adopt `.lex` in one real repository.** A deliberate decision that lifts
  the "never in main repo" rule (that rule belonged to the exploration phase). law-nexus
  or a dedicated acp repo: `git-lex init --kit rager306/git-lex-kit-acp`, place ACP
  records, use validate/sync/query in real work.

- **Stage 4 — Prove reusability with a second project.** Install and use ACP-kit in a
  second, non-law-nexus project. This is the only thing that turns "universal core" from
  a claim into a fact (B5).

- **Stage 5 — Formalize the authority model.** Fix when a record becomes authoritative
  (D072 model). Replace blanket "source-truth migration blocked" with managed,
  gate-controlled migration.

## Boundaries to keep vs drop

Keep (real correctness, not paralysis):

- The authority model: a record is authoritative only with source category + lifecycle
  state + evidence anchor + proof gate or accepted decision (D072).
- R035/R037/R038 require real source/runtime/real-document evidence; projection shape is
  never authority for them.
- Proof-gate discipline and anti-imitation rule (D072).

Drop (paralysis that blocks the goal):

- "Never install git-lex"; "never touch main repo"; "shadow diagnostic forever";
  "disposable-workspace-only proofs"; the proof-before-foundation inversion; the
  decision -> pilot -> decision loop.

## Relation to prior decisions D080-D083

Not a contradiction — the logical consequence the prior decisions themselves named.
D080-D083 all named "ontology/generator strengthening plus true negative runtime
proof" as the gate to advance beyond shadow/diagnostic-smoke. M064 (Stage 1) executes
exactly that gate. D084 reframes the roadmap from *preserving* the bounded-pilot state
to *executing* the advance gate the old decisions required.

## Next milestone

**M064 — Strengthen ACP-kit ontology shapes to close the M058 validation gate.**
Planned immediately after this review. Success = `git-lex validate` rejects bad records
with actionable diagnostics and accepts well-formed ones; M058 root cause closed.
M064 does not itself validate R035/R037/R038 and does not itself approve production
adoption — those remain on their own later stages.
