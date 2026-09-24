#!/usr/bin/env node
// M210-3afp79 S01 T03 -- source-bound dispute cards and negative examples.
//
// WHY THIS FILE EXISTS
// S01 T03 must hand the S02 decision a package that can actually be shown to an
// owner: dispute cards that are anchored in a *source* (a tracked file with a
// section and a sha256 pin, or a corpus-gated span pin), plus two negative
// examples that name the conflation each one refuses. Prose is not showable;
// pins are. So this generator derives the artifact from live files instead of
// trusting hand-typed claims.
//
// WHAT IS DERIVED, FROM WHERE
//   * the eight-family order, each family's owning source, vocabulary status and
//     evidence class   <- prd/architecture/m210-s01-normative-family-register.json
//   * the N to M provenance alternative context (referenced, never re-decided)
//                      <- prd/architecture/m210-s01-ir-alternatives.json
//   * the pinned ComponentConcept registry (referenced boundary)
//                      <- prd/architecture/kb-hierarchy-registry.yaml
//   * the structural N to M amends-edge anchors (referenced boundary)
//                      <- prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json
//   * per-family dispute-card anchors (section + live sha256) from the owning
//     sources named by the T01 register
//   * a bounded corpus probe set: at most PROBE_COUNT regular files taken
//     deterministically from the licensed, untracked corpus export directory
//     (consru_export/consru_export/exports/npa), one per family, pinned by
//     repository-relative path, span [start,end), byte count and sha256.
//
// WHAT IS NEVER WRITTEN
//   * No legal text. The corpus probe records only path, span, bytes, sha256.
//     The probe record has a closed key set; any extra key is refused with
//     `corpus_probe_writes_text`. The corpus is read locally and never copied.
//   * No timestamp and no aggregate engine hash: the artifact is canonical
//     compact ASCII JSON with a fixed key order, so a whole-file byte compare in
//     --check mode is the determinism proof (D424).
//
// CORPUS-GATED BEHAVIOUR
//   When the corpus directory resolves, probes are re-derived live and the full
//   artifact is rendered. When it does not resolve, M210_S01_CORPUS_ABSENT is
//   printed to stderr and the committed probe pins are carried over unverified
//   (only the tracked block is re-derived); a fresh render without a corpus
//   carries no probes at all. The contract test re-checks the corpus pins only
//   when the corpus is present.
//
// NAMED FAIL-CLOSED CODES (every one is exercised by the contract test)
//   family_uncovered          a declared family has no dispute card (or no probe while the corpus is present)
//   tracked_anchor_missing    a tracked anchor path is absent, not repository-relative, or the anchor block is missing
//   anchor_untracked          a tracked anchor exists but git does not track it
//   anchor_hash_mismatch      a tracked anchor sha256 pin is malformed or differs from the live file
//   anchor_drift              a corpus probe pin (path, span, bytes, sha256) is malformed or differs from the live file
//   raw_text_leak             the artifact text carries an XML tag or a provider text marker
//   non_ascii_artifact        the artifact text carries a non-ASCII byte
//   self_declared_resolved    a card is adopted, does not require human source review, or claims verdict resolved
//   negative_example_missing  fewer than two negative examples, or a required example is absent or incomplete
//   corpus_probe_writes_text  a corpus probe record carries a key outside the closed count-only key set
//   check_not_byte_identical  --check rendered bytes differ from the committed artifact
//
// USAGE
//   node scripts/m210_s01_build_examples.mjs --write      # default
//   node scripts/m210_s01_build_examples.mjs --check
//   node scripts/m210_s01_build_examples.mjs --print      # JSON to stdout, markers to stderr
//
// Offline, dependency-free (node stdlib only), deterministic: no clock, no
// randomness, no network, byte-stable output for byte-stable inputs.

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const ARTIFACT_RELATIVE_PATH = "prd/architecture/m210-s01-source-bound-examples.json";

export const SCHEMA = "law-nexus/m210-source-bound-examples/v1";
export const KIND = "m210-s01-source-bound-examples";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S01";
export const TASK = "T03";
export const LIFECYCLE = "[proposed]";
export const ORIGINATING_REVIEW = "doc/review/review-28-10-09-2026.md RC28-F18 and RC28-F19";
export const REQUIREMENT_REFS = ["RC28-F18", "R074"];

export const T01_REGISTER_PATH = "prd/architecture/m210-s01-normative-family-register.json";
export const T02_ALTERNATIVES_PATH = "prd/architecture/m210-s01-ir-alternatives.json";
export const HIERARCHY_REGISTRY_PATH = "prd/architecture/kb-hierarchy-registry.yaml";
export const M209_AMENDS_EVIDENCE_PATH =
  "prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json";
export const REVIEW_28_PATH = "doc/review/review-28-10-09-2026.md";
export const TEMPORAL_MODEL_PATH = "prd/temporal-legal-model.md";
export const GAP_REGISTER_PATH = "prd/architecture/temporal-semantic-gap-register.md";
export const KB_ONTOLOGY_DRAFT_PATH = "prd/architecture/kb-ontology-l1-l3-draft.md";

// Bounded corpus probe source. Untracked, licensed, read-only, local.
export const CORPUS_ROOT_RELATIVE = "consru_export/consru_export/exports/npa";
export const CORPUS_DIR_ENV = "M210_S01_CORPUS_DIR";
export const PROBE_COUNT = 8;
export const PROBE_SPAN_CAP = 4096;

export const FAMILY_ORDER = [
  "obligation",
  "permission",
  "prohibition",
  "definition",
  "competence",
  "condition",
  "exception",
  "temporal_qualification",
];

export const REQUIRED_NEGATIVE_EXAMPLES = [
  "absence_of_obligation_is_not_prohibition",
  "lack_of_evidence_is_not_falsity",
];

export const EMITTABLE_CODES = [
  "family_uncovered",
  "tracked_anchor_missing",
  "anchor_untracked",
  "anchor_hash_mismatch",
  "anchor_drift",
  "raw_text_leak",
  "non_ascii_artifact",
  "self_declared_resolved",
  "negative_example_missing",
  "corpus_probe_writes_text",
  "check_not_byte_identical",
];

export const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;

const PROBE_KEYS = new Set(["probe_id", "family", "path", "span", "bytes", "sha256"]);

// XML tags and provider text markers: never legitimate in a count-only artifact.
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];

const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// Tracked source bindings. Section and role are design metadata; sha256 is live.
const SOURCE_BINDING_TABLE = [
  [
    T01_REGISTER_PATH,
    "families array (eight families, owning sources, vocabulary statuses)",
    "T01 closed family register: family order, owning sources and vocabulary statuses",
  ],
  [
    T02_ALTERNATIVES_PATH,
    "variants array and provenance_contract (N to M cardinality)",
    "T02 normative IR alternatives and the N to M provenance contract",
  ],
  [
    HIERARCHY_REGISTRY_PATH,
    "bindings array (pinned ComponentConcept registry)",
    "pinned hierarchy registry: ComponentConcept identities are not minted here",
  ],
  [
    M209_AMENDS_EVIDENCE_PATH,
    "edges array (structural amends edges)",
    "structural N to M amends-edge anchors: provision to rule cardinality evidence",
  ],
  [
    REVIEW_28_PATH,
    "RC28-F18 and RC28-F19",
    "originating requirement for the closed eight-family set and the two negative distinctions",
  ],
  [
    TEMPORAL_MODEL_PATH,
    "section 3 Glossary and ownership",
    "section 3 term rows for condition, exception and temporal qualification",
  ],
  [
    GAP_REGISTER_PATH,
    "section 2 Active gaps TSG-005, TSG-006, TSG-007",
    "gap rows for the deontic and competence families",
  ],
  [
    KB_ONTOLOGY_DRAFT_PATH,
    "section 6 Forbidden kinds in L1-L3 core (KBO-R017)",
    "boundary source: a NormRule product graph is not L1-L3 core truth",
  ],
];

// Per-family owning-source anchor: path plus section, live sha256 is computed.
const CARD_ANCHOR_TABLE = {
  obligation: [REVIEW_28_PATH, "RC28-F18"],
  permission: [REVIEW_28_PATH, "RC28-F18"],
  prohibition: [REVIEW_28_PATH, "RC28-F18"],
  definition: [REVIEW_28_PATH, "RC28-F18"],
  competence: [GAP_REGISTER_PATH, "TSG-007"],
  condition: [TEMPORAL_MODEL_PATH, "section 3 Condition row"],
  exception: [TEMPORAL_MODEL_PATH, "section 3 Exception / Defeater row"],
  temporal_qualification: [TEMPORAL_MODEL_PATH, "section 3 Event time row"],
};

// Design-language description of what two competing readings differ on. These
// are statements about the design space, never about what a source says.
const CARD_READINGS = {
  obligation: [
    "A duty exists only where a source span establishes the deontic operator for the act.",
    "A duty may be inferred from the practical necessity of the act in its context.",
  ],
  permission: [
    "Permission is a positive entitlement that must be established by a source span.",
    "Permission follows from the mere absence of a prohibition on the act.",
  ],
  prohibition: [
    "A prohibition is a positive ban that must be established by a source span.",
    "A prohibition may be inferred from the absence of a permission for the act.",
  ],
  definition: [
    "A definitional norm is a distinct normative family with its own boundary.",
    "A definition is only a naming convention carried inside another family.",
  ],
  competence: [
    "Competence is a power held by a named body and must be established by a source span.",
    "Competence follows from the ordinary function of the body without a further span.",
  ],
  condition: [
    "A condition is a guard on the norm and must be established as part of the norm.",
    "A condition is a factual premise of the case and not part of the norm.",
  ],
  exception: [
    "An exception defeats a norm only where the defeat is established by a source span.",
    "An exception limits the scope of the norm from the start rather than defeating it.",
  ],
  temporal_qualification: [
    "The governing time is the qualification established for the norm itself.",
    "The governing time follows the time the fact occurred.",
  ],
};

const NEGATIVE_EXAMPLE_TABLE = [
  {
    example_id: "absence_of_obligation_is_not_prohibition",
    anchor: { path: REVIEW_28_PATH, section: "RC28-F18 and RC28-F19" },
    fail_closed_code: "absence_of_obligation_conflated_with_prohibition",
    non_claim:
      "Nothing in this package lets a missing duty be read as a ban, or a ban as a missing duty.",
  },
  {
    example_id: "lack_of_evidence_is_not_falsity",
    anchor: { path: GAP_REGISTER_PATH, section: "section 2 Active gaps" },
    fail_closed_code: "lack_of_evidence_conflated_with_falsity",
    non_claim:
      "An unproven claim stays Unknown; absence of a proven source span is never falsity.",
  },
];

const NON_CLAIMS = [
  "This package is not an adoption of normative semantics: no reading, card or verdict here is accepted.",
  "It is non-authoritative: it cannot satisfy a requirement, promote a lifecycle or establish legal correctness.",
  "No runtime surface exists or is promised: there is no normative IR, rule graph or applicability evaluator.",
  "A corpus probe records only path, span, bytes and sha256; no legal text is copied and a probe is not a reading.",
  "Every dispute card is unresolved or conflicted by construction: a verdict resolved is refused without a human source review.",
  "The two negative examples are boundaries, not findings: absence of obligation is not prohibition and lack of evidence is not falsity.",
  "Family labelling of a corpus probe is a coverage label, not a claim that the span states that family.",
];

const REVISION_POLICY =
  "Re-derive before use: re-hash every tracked anchor, re-read the family order from the T01 register, re-probe the bounded corpus set and re-render; no timestamp and no aggregate engine hash are stored here.";

class BuildError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "BuildError";
    this.code = code;
    this.detail = detail;
  }
}

function fail(code, detail) {
  throw new BuildError(code, detail);
}

// ---------------------------------------------------------------------------
// repository helpers
// ---------------------------------------------------------------------------

export function isRepoRelative(value) {
  if (typeof value !== "string" || value.length === 0) return false;
  if (path.isAbsolute(value)) return false;
  return value.split("/").every((part) => part !== "" && part !== ".." && part !== ".");
}

function assertReadable(relativePath) {
  if (!isRepoRelative(relativePath)) fail("tracked_anchor_missing", `${relativePath} is not repository-relative`);
  for (const prefix of IGNORED_SOURCE_PREFIXES) {
    if (relativePath.startsWith(prefix)) fail("tracked_anchor_missing", `${relativePath} is an ignored overlay path`);
  }
}

function hashFile(absolutePath) {
  return createHash("sha256").update(readFileSync(absolutePath)).digest("hex");
}

export function readTrackedText(rootDir, relativePath) {
  assertReadable(relativePath);
  return readFileSync(path.join(rootDir, relativePath), "utf8");
}

function gitTracks(rootDir, relativePath) {
  try {
    execFileSync("git", ["ls-files", "--error-unmatch", "--", relativePath], {
      cwd: rootDir,
      stdio: ["ignore", "ignore", "ignore"],
    });
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// derivation
// ---------------------------------------------------------------------------

export function probeCorpus(corpusDir, rootDir = REPO_ROOT) {
  const directory = corpusDir ?? path.join(rootDir, CORPUS_ROOT_RELATIVE);
  if (!existsSync(directory) || !statSync(directory).isDirectory()) {
    return { present: false, probes: [] };
  }
  const names = readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .sort();
  if (names.length < PROBE_COUNT) {
    fail(
      "anchor_drift",
      `corpus directory carries ${names.length} regular files, fewer than the bounded probe count ${PROBE_COUNT}`,
    );
  }
  const probes = [];
  for (let index = 0; index < PROBE_COUNT; index += 1) {
    const pick = Math.floor((index * (names.length - 1)) / (PROBE_COUNT - 1));
    const absolute = path.join(directory, names[pick]);
    const bytes = readFileSync(absolute);
    const relative = path.relative(rootDir, absolute).split(path.sep).join("/");
    const recorded = isRepoRelative(relative) ? relative : `${CORPUS_ROOT_RELATIVE}/${names[pick]}`;
    probes.push({
      probe_id: `m210-s01-probe-${FAMILY_ORDER[index]}`,
      family: FAMILY_ORDER[index],
      path: recorded,
      span: { start: 0, end: Math.min(bytes.length, PROBE_SPAN_CAP) },
      bytes: bytes.length,
      sha256: `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
    });
  }
  return { present: true, probes };
}

function deriveBindings(rootDir) {
  return SOURCE_BINDING_TABLE.map(([relativePath, section, role]) => {
    assertReadable(relativePath);
    const absolute = path.join(rootDir, relativePath);
    if (!existsSync(absolute)) fail("tracked_anchor_missing", `source binding ${relativePath} is absent`);
    return {
      path: relativePath,
      section,
      role,
      sha256: `sha256:${hashFile(absolute)}`,
    };
  });
}

function deriveCards(rootDir, register) {
  const byFamily = new Map((register.families ?? []).map((family) => [family.family_id, family]));
  return FAMILY_ORDER.map((family) => {
    const source = byFamily.get(family);
    if (!source) fail("family_uncovered", `the T01 register carries no family ${family}`);
    const [anchorPath, section] = CARD_ANCHOR_TABLE[family];
    const absolute = path.join(rootDir, anchorPath);
    if (!existsSync(absolute)) fail("tracked_anchor_missing", `card anchor ${anchorPath} is absent`);
    const [readingA, readingB] = CARD_READINGS[family];
    const proposed = source.vocabulary_status === "proposed";
    const spanBound = source.evidence_class === "source-bound-span";
    return {
      card_id: `m210-s01-dc-${family}`,
      family,
      anchor: {
        anchor_kind: "tracked",
        path: anchorPath,
        section,
        sha256: `sha256:${hashFile(absolute)}`,
      },
      evidence_class: source.evidence_class,
      reading_a: readingA,
      reading_b: readingB,
      corpus_probe_id: `m210-s01-probe-${family}`,
      requires_human_source_review: true,
      adopted: false,
      verdict: proposed && spanBound ? "conflicted" : "unresolved",
    };
  });
}

function deriveNegativeExamples(rootDir) {
  return NEGATIVE_EXAMPLE_TABLE.map((entry) => {
    const absolute = path.join(rootDir, entry.anchor.path);
    if (!existsSync(absolute)) fail("tracked_anchor_missing", `negative example anchor ${entry.anchor.path} is absent`);
    return {
      example_id: entry.example_id,
      anchor: {
        anchor_kind: "tracked",
        path: entry.anchor.path,
        section: entry.anchor.section,
        sha256: `sha256:${hashFile(absolute)}`,
      },
      fail_closed_code: entry.fail_closed_code,
      non_claim: entry.non_claim,
    };
  });
}

export function renderArtifact(options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const corpus = probeCorpus(options.corpusDir, rootDir);
  let probes = corpus.probes;
  let carriedOver = false;
  if (!corpus.present && typeof options.carryOverText === "string") {
    const previous = JSON.parse(options.carryOverText);
    if (Array.isArray(previous.corpus_probes)) {
      probes = previous.corpus_probes;
      carriedOver = true;
    }
  }
  const register = JSON.parse(readTrackedText(rootDir, T01_REGISTER_PATH));
  const artifact = {
    schema: SCHEMA,
    schema_version: 1,
    kind: KIND,
    milestone: MILESTONE,
    slice: SLICE,
    task: TASK,
    lifecycle: LIFECYCLE,
    authoritative: false,
    ascii_only: true,
    semantics_adopted: false,
    requirement_refs: REQUIREMENT_REFS,
    originating_review: ORIGINATING_REVIEW,
    family_order: FAMILY_ORDER,
    fail_closed_codes: EMITTABLE_CODES,
    source_bindings: deriveBindings(rootDir),
    dispute_cards: deriveCards(rootDir, register),
    corpus_probes: probes,
    negative_examples: deriveNegativeExamples(rootDir),
    non_claims: NON_CLAIMS,
    revision_policy: REVISION_POLICY,
  };
  return {
    artifact,
    text: JSON.stringify(artifact),
    corpusPresent: corpus.present,
    carriedOver,
    probes,
  };
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

export function validateArtifact(artifact, env = {}) {
  const errors = [];
  const code = (name, detail) => errors.push({ name, detail });
  const text = env.artifactText ?? JSON.stringify(artifact);
  const exists = env.exists ?? (() => true);
  const isTracked = env.isTracked ?? (() => true);
  const liveSha = env.sha256 ?? (() => null);
  const corpusPresent = env.corpusPresent ?? false;
  const liveProbes = Array.isArray(env.liveProbes) ? env.liveProbes : [];
  const liveProbeByFamily = new Map(liveProbes.map((probe) => [probe.family, probe]));

  // 1. text hygiene: ASCII-only, no XML tags and no provider text markers.
  const offending = [...text].findIndex((character) => character.charCodeAt(0) > 0x7f);
  if (offending >= 0) code("non_ascii_artifact", `non-ascii character at index ${offending}`);
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) code("raw_text_leak", `text marker ${marker}`);
  }

  // 2. no self-declared adoption or resolution.
  if (artifact?.semantics_adopted === true) {
    code("self_declared_resolved", "artifact-level semantics_adopted must be false");
  }
  if (artifact?.authoritative === true) {
    code("self_declared_resolved", "artifact-level authoritative must be false");
  }

  const checkTrackedAnchor = (scope, anchor) => {
    if (!anchor || typeof anchor !== "object") {
      code("tracked_anchor_missing", `${scope} anchor is missing`);
      return;
    }
    const anchorPath = anchor.path;
    if (!isRepoRelative(anchorPath)) {
      code("tracked_anchor_missing", `${scope} anchor path is not repository-relative`);
      return;
    }
    if (!exists(anchorPath)) {
      code("tracked_anchor_missing", `${scope} anchor is absent: ${anchorPath}`);
      return;
    }
    if (!isTracked(anchorPath)) {
      code("anchor_untracked", `${scope} anchor is not git-tracked: ${anchorPath}`);
    }
    if (typeof anchor.sha256 !== "string" || !SHA_PATTERN.test(anchor.sha256)) {
      code("anchor_hash_mismatch", `${scope} sha256 pin is malformed`);
      return;
    }
    const live = liveSha(anchorPath);
    if (typeof live === "string" && live !== anchor.sha256) {
      code("anchor_hash_mismatch", `${scope} sha256 pin differs from the live file`);
    }
  };

  // 3. dispute cards: full family coverage, human review required, tracked anchors.
  const cards = Array.isArray(artifact?.dispute_cards) ? artifact.dispute_cards : null;
  if (!cards) {
    code("family_uncovered", "dispute_cards is missing");
  } else {
    const seen = new Set();
    for (const card of cards) {
      const scope = `card ${typeof card?.card_id === "string" ? card.card_id : "<unnamed>"}`;
      const family = card?.family;
      if (!FAMILY_ORDER.includes(family)) {
        code("family_uncovered", `${scope} names an unknown family ${family}`);
        continue;
      }
      seen.add(family);
      if (card.adopted !== false) code("self_declared_resolved", `${scope} adopted must be false`);
      if (card.requires_human_source_review !== true) {
        code("self_declared_resolved", `${scope} requires_human_source_review must be true`);
      }
      if (card.verdict !== "unresolved" && card.verdict !== "conflicted") {
        code("self_declared_resolved", `${scope} verdict ${card.verdict} is not allowed`);
      }
      checkTrackedAnchor(scope, card.anchor);
    }
    for (const family of FAMILY_ORDER) {
      if (!seen.has(family)) code("family_uncovered", `family ${family} has no dispute card`);
    }
  }

  // 4. negative examples: at least two, both required ids present and complete.
  const negatives = Array.isArray(artifact?.negative_examples) ? artifact.negative_examples : [];
  if (negatives.length < 2) {
    code("negative_example_missing", `only ${negatives.length} negative examples`);
  }
  for (const exampleId of REQUIRED_NEGATIVE_EXAMPLES) {
    const found = negatives.find((example) => example?.example_id === exampleId);
    if (!found) {
      code("negative_example_missing", `required example ${exampleId} is absent`);
      continue;
    }
    if (typeof found.non_claim !== "string" || found.non_claim.trim() === "") {
      code("negative_example_missing", `${exampleId} non_claim is missing`);
    }
    if (typeof found.fail_closed_code !== "string" || found.fail_closed_code.trim() === "") {
      code("negative_example_missing", `${exampleId} fail_closed_code is missing`);
    }
    checkTrackedAnchor(exampleId, found.anchor);
  }

  // 5. corpus probes: closed count-only key set, family coverage, live re-derivation.
  if (corpusPresent) {
    const probes = Array.isArray(artifact?.corpus_probes) ? artifact.corpus_probes : null;
    if (!probes) {
      code("family_uncovered", "corpus_probes is missing while the corpus is present");
    } else {
      const seen = new Set();
      for (const probe of probes) {
        const scope = `probe ${typeof probe?.probe_id === "string" ? probe.probe_id : "<unnamed>"}`;
        const extra = Object.keys(probe ?? {}).filter((key) => !PROBE_KEYS.has(key));
        if (extra.length > 0) {
          code("corpus_probe_writes_text", `${scope} carries keys outside the count-only set: ${extra.join(",")}`);
        }
        const family = probe?.family;
        if (!FAMILY_ORDER.includes(family)) {
          code("family_uncovered", `${scope} names an unknown family ${family}`);
          continue;
        }
        seen.add(family);
        if (!isRepoRelative(probe.path)) {
          code("anchor_drift", `${scope} path is not repository-relative`);
        }
        if (!Number.isInteger(probe.bytes) || probe.bytes <= 0) {
          code("anchor_drift", `${scope} byte pin is malformed`);
        }
        if (typeof probe.sha256 !== "string" || !SHA_PATTERN.test(probe.sha256)) {
          code("anchor_drift", `${scope} sha256 pin is malformed`);
        }
        const span = probe.span;
        if (
          !span ||
          !Number.isInteger(span.start) ||
          !Number.isInteger(span.end) ||
          span.start < 0 ||
          span.end <= span.start
        ) {
          code("anchor_drift", `${scope} span is malformed`);
        }
        const live = liveProbeByFamily.get(family);
        if (live) {
          if (live.path !== probe.path) code("anchor_drift", `${scope} path drifted`);
          if (live.bytes !== probe.bytes) code("anchor_drift", `${scope} byte count drifted`);
          if (live.sha256 !== probe.sha256) code("anchor_drift", `${scope} sha256 drifted`);
          if (live.span?.start !== span?.start || live.span?.end !== span?.end) {
            code("anchor_drift", `${scope} span drifted`);
          }
        }
      }
      for (const family of FAMILY_ORDER) {
        if (!seen.has(family)) code("family_uncovered", `family ${family} has no corpus probe`);
      }
    }
  }

  // 6. --check: rendered bytes must equal the committed artifact bytes.
  if (typeof env.committedText === "string" && env.committedText !== text) {
    code("check_not_byte_identical", "rendered bytes differ from the committed artifact");
  }

  return { ok: errors.length === 0, errors };
}

export function liveEnv(options) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const shaCache = new Map();
  const trackedCache = new Map();
  return {
    artifactText: options.artifactText,
    corpusPresent: options.corpusPresent ?? false,
    liveProbes: options.liveProbes ?? [],
    committedText: options.committedText,
    exists: (relativePath) => existsSync(path.join(rootDir, relativePath)),
    isTracked: (relativePath) => {
      if (trackedCache.has(relativePath)) return trackedCache.get(relativePath);
      const tracked = gitTracks(rootDir, relativePath);
      trackedCache.set(relativePath, tracked);
      return tracked;
    },
    sha256: (relativePath) => {
      if (shaCache.has(relativePath)) return shaCache.get(relativePath);
      const digest = `sha256:${hashFile(path.join(rootDir, relativePath))}`;
      shaCache.set(relativePath, digest);
      return digest;
    },
  };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function main(argv) {
  const mode = argv.includes("--check") ? "check" : argv.includes("--print") ? "print" : "write";
  const artifactPath = path.join(REPO_ROOT, ARTIFACT_RELATIVE_PATH);
  const carryOverText = existsSync(artifactPath) ? readFileSync(artifactPath, "utf8") : null;
  // --print shows the honest corpus-free render (tracked block only); --write and
  // --check carry the committed probe pins over so byte identity is preserved
  // when the licensed corpus is not mounted locally.
  const rendered = renderArtifact({
    rootDir: REPO_ROOT,
    corpusDir: process.env[CORPUS_DIR_ENV],
    carryOverText: mode === "print" ? undefined : carryOverText ?? undefined,
  });
  if (!rendered.corpusPresent) {
    process.stderr.write("M210_S01_CORPUS_ABSENT\n");
  } else {
    process.stderr.write(`M210_S01_CORPUS_PRESENT probes=${rendered.probes.length}\n`);
  }
  const env = liveEnv({
    rootDir: REPO_ROOT,
    artifactText: rendered.text,
    corpusPresent: rendered.corpusPresent,
    liveProbes: rendered.probes,
    committedText: mode === "check" ? carryOverText ?? undefined : undefined,
  });
  const result = validateArtifact(rendered.artifact, env);
  if (!result.ok) {
    for (const error of result.errors) {
      process.stderr.write(`${error.name}: ${error.detail}\n`);
    }
    process.exitCode = 1;
    return;
  }
  if (mode === "print") {
    process.stdout.write(`${rendered.text}\n`);
    return;
  }
  if (mode === "check") {
    if (carryOverText === null) {
      process.stderr.write("check_not_byte_identical: the committed artifact is absent\n");
      process.exitCode = 1;
      return;
    }
    process.stdout.write("M210_S01_EXAMPLES_CHECK_OK\n");
    return;
  }
  writeFileSync(artifactPath, rendered.text);
  process.stdout.write("M210_S01_EXAMPLES_WRITTEN\n");
}

const invokedDirectly =
  typeof process.argv[1] === "string" && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedDirectly) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    if (error instanceof BuildError) {
      process.stderr.write(`${error.code}: ${error.detail}\n`);
      process.exitCode = 1;
    } else {
      throw error;
    }
  }
}
