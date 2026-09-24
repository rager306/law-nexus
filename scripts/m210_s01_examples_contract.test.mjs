// M210-3afp79 S01 T03 source-bound examples contract.
//
// Offline and fail-closed. The artifact under test is the S01 T03 package for the
// S02 decision: dispute cards bound to tracked source anchors, two negative
// examples, and a bounded corpus probe set. Nothing here is accepted semantics;
// the claim under test is only that every card has a real, tracked, hash-pinned
// anchor, that the corpus probe records a path/span/bytes/sha256 and never any
// legal text, and that the generator re-renders byte-identically.
//
// The corpus (consru_export/, licensed, untracked) is read only when it resolves
// locally. When it does not, this contract prints M210_S01_CORPUS_ABSENT and
// checks the tracked subset only: the corpus probes are not recomputed and the
// artifact keeps its committed pins.
//
// All subprocesses are limited to `node scripts/m210_s01_build_examples.mjs`
// (the generator under test) and `git ls-files --error-unmatch` (tracked-file
// proof). No network, no `.gsd` / ignored / absolute path is read as evidence,
// and this contract never writes a file.
//
// Run: node --test scripts/m210_s01_examples_contract.test.mjs

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";

import {
  ARTIFACT_RELATIVE_PATH,
  CORPUS_DIR_ENV,
  EMITTABLE_CODES,
  FAMILY_ORDER,
  KIND,
  LIFECYCLE,
  MILESTONE,
  PROBE_COUNT,
  PROBE_SPAN_CAP,
  REPO_ROOT,
  REQUIRED_NEGATIVE_EXAMPLES,
  SCHEMA,
  SHA_PATTERN,
  SLICE,
  TASK,
  liveEnv,
  probeCorpus,
  validateArtifact,
} from "./m210_s01_build_examples.mjs";

const root = REPO_ROOT;
const GENERATOR = "scripts/m210_s01_build_examples.mjs";
const ABSENT_CORPUS_DIR = "no-such-dir/m210-s01-corpus";

// The complete fail-closed code set. The `## Fail-closed codes` block below is
// asserted to document exactly this set (no more, no less), and the same set is
// asserted equal to the artifact's declared `fail_closed_codes`.
// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// family_uncovered: a declared family has no dispute card, or no corpus probe while the corpus is present.
// tracked_anchor_missing: a tracked anchor path is absent, not repository-relative, or the anchor block is missing.
// anchor_untracked: a tracked anchor exists on disk but git does not track it.
// anchor_hash_mismatch: a tracked anchor sha256 pin is malformed or differs from the live file.
// anchor_drift: a corpus probe pin (path, span, bytes, sha256) is malformed or differs from the live file.
// raw_text_leak: the artifact text carries an XML tag or a provider text marker.
// non_ascii_artifact: the artifact text carries a non-ASCII byte.
// self_declared_resolved: a card is adopted, does not require human source review, or claims verdict resolved.
// negative_example_missing: fewer than two negative examples, or a required example is absent or incomplete.
// corpus_probe_writes_text: a corpus probe record carries a key outside the closed count-only key set.
// check_not_byte_identical: --check rendered bytes differ from the committed artifact.
// DOCUMENTED_CODES_END

const PROBE_KEYS = ["probe_id", "family", "path", "span", "bytes", "sha256"];
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "not an adoption of normative semantics",
  "non-authoritative",
  "no runtime surface exists",
  "no legal text is copied",
  "verdict resolved is refused",
];

// ---------------------------------------------------------------------------
// repository helpers
// ---------------------------------------------------------------------------

function readRepo(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

function sha256Of(relativePath) {
  return `sha256:${createHash("sha256").update(readFileSync(path.join(root, relativePath))).digest("hex")}`;
}

const liveText = readRepo(ARTIFACT_RELATIVE_PATH);
const liveArtifact = JSON.parse(liveText);
const corpusLive = probeCorpus(undefined, root);

function cloneArtifact() {
  return JSON.parse(liveText);
}

function codesFor(result) {
  return [...new Set(result.errors.map((error) => error.name))];
}

function expectCode(result, name) {
  assert.ok(
    codesFor(result).includes(name),
    `expected ${name}, got ${JSON.stringify(result.errors)}`,
  );
  assert.equal(result.ok, false, `${name} must fail closed`);
  return result;
}

// A validation environment bound to the live tree. The probe surface is taken
// from the artifact's own committed pins so the code-coverage mutations are
// independent of whether the licensed corpus is mounted.
function coverageEnv(text) {
  return liveEnv({
    rootDir: root,
    artifactText: text,
    corpusPresent: true,
    liveProbes: liveArtifact.corpus_probes ?? [],
  });
}

function assertTrackedAnchor(scope, anchor) {
  assert.ok(anchor && typeof anchor === "object", `${scope} anchor must exist`);
  assert.equal(anchor.anchor_kind, "tracked", `${scope} anchor must be tracked`);
  assert.ok(
    typeof anchor.path === "string" &&
      !path.isAbsolute(anchor.path) &&
      !anchor.path.split("/").includes(".."),
    `${scope} anchor path must be repository-relative`,
  );
  assert.ok(existsSync(path.join(root, anchor.path)), `${scope} anchor must exist: ${anchor.path}`);
  const tracked = spawnSync("git", ["ls-files", "--error-unmatch", "--", anchor.path], {
    cwd: root,
    encoding: "utf8",
  });
  assert.equal(tracked.status, 0, `${scope} anchor must be git-tracked: ${anchor.path}`);
  assert.match(anchor.sha256, SHA_PATTERN, `${scope} sha256 pin must be well-formed`);
  assert.equal(anchor.sha256, sha256Of(anchor.path), `${scope} sha256 pin must match the live file`);
}

// ---------------------------------------------------------------------------
// artifact integrity
// ---------------------------------------------------------------------------

test("the artifact exists, is canonical compact ASCII and carries no raw text", () => {
  assert.ok(existsSync(path.join(root, ARTIFACT_RELATIVE_PATH)), `${ARTIFACT_RELATIVE_PATH} must exist`);
  assert.ok(liveText.length > 0, "the artifact must be non-empty");
  assert.ok(liveText.isWellFormed(), "the artifact must be well-formed UTF-8");
  assert.match(liveText, /^[\x00-\x7f]*$/, "the artifact must be pure ASCII");
  assert.ok(!liveText.includes("\n"), "canonical bytes are a single line");
  assert.ok(!liveText.endsWith("\n"), "canonical bytes carry no trailing newline");
  assert.equal(
    JSON.stringify(JSON.parse(liveText)),
    liveText,
    "the artifact must round-trip to identical canonical compact bytes (D424)",
  );
  for (const marker of RAW_TEXT_MARKERS) {
    assert.ok(!liveText.includes(marker), `the artifact must not carry ${marker}`);
  }
  assert.ok(
    !/[\u0400-\u04ff]/.test(liveText),
    "the artifact must carry no Cyrillic (raw legal text)",
  );
});

test("the envelope is the declared non-adopting S01 T03 record", () => {
  assert.equal(liveArtifact.schema, SCHEMA);
  assert.equal(liveArtifact.schema_version, 1);
  assert.equal(liveArtifact.kind, KIND);
  assert.equal(liveArtifact.milestone, MILESTONE);
  assert.equal(liveArtifact.slice, SLICE);
  assert.equal(liveArtifact.task, TASK);
  assert.equal(liveArtifact.lifecycle, LIFECYCLE);
  assert.equal(liveArtifact.authoritative, false);
  assert.equal(liveArtifact.ascii_only, true);
  assert.equal(liveArtifact.semantics_adopted, false);
  assert.deepEqual(liveArtifact.family_order, FAMILY_ORDER);
  assert.deepEqual([...liveArtifact.fail_closed_codes].sort(), [...EMITTABLE_CODES].sort());
  assert.ok(Array.isArray(liveArtifact.non_claims) && liveArtifact.non_claims.length >= 5);
  const joined = liveArtifact.non_claims.join(" ").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.ok(joined.includes(fragment), `non-claim fragment missing: ${fragment}`);
  }
});

test("every source binding is repository-relative, exists, is tracked and hash-pinned", () => {
  assert.ok(liveArtifact.source_bindings.length >= 4);
  for (const binding of liveArtifact.source_bindings) {
    assertTrackedAnchor(`binding ${binding.path}`, {
      anchor_kind: "tracked",
      path: binding.path,
      sha256: binding.sha256,
    });
    assert.ok(typeof binding.section === "string" && binding.section.length > 0);
    assert.ok(typeof binding.role === "string" && binding.role.length > 0);
  }
});

test("the artifact-integrity block passes for the tracked artifact", () => {
  const result = validateArtifact(liveArtifact, liveEnv({
    rootDir: root,
    artifactText: liveText,
    corpusPresent: corpusLive.present,
    liveProbes: corpusLive.probes,
  }));
  assert.deepEqual(result.errors, [], `artifact errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, true);
});

// ---------------------------------------------------------------------------
// dispute cards
// ---------------------------------------------------------------------------

test("every one of the eight families carries a human-reviewed, unresolved card with a tracked anchor", () => {
  const cards = liveArtifact.dispute_cards;
  assert.ok(Array.isArray(cards), "dispute_cards must be an array");
  assert.deepEqual(
    cards.map((card) => card.family),
    FAMILY_ORDER,
    "every family must carry exactly one card, in the declared order",
  );
  for (const card of cards) {
    assert.equal(card.requires_human_source_review, true, `${card.card_id} must require human review`);
    assert.equal(card.adopted, false, `${card.card_id} must not be adopted`);
    assert.ok(
      card.verdict === "unresolved" || card.verdict === "conflicted",
      `${card.card_id} verdict must be unresolved or conflicted`,
    );
    assert.notEqual(card.verdict, "resolved", "no verdict resolved is allowed without a human");
    assert.ok(typeof card.reading_a === "string" && card.reading_a.length > 0);
    assert.ok(typeof card.reading_b === "string" && card.reading_b.length > 0);
    assert.notEqual(card.reading_a, card.reading_b, `${card.card_id} must name two distinct readings`);
    assert.ok(
      typeof card.evidence_class === "string" && card.evidence_class.length > 0,
      `${card.card_id} must carry an evidence class`,
    );
    assertTrackedAnchor(`card ${card.card_id}`, card.anchor);
  }
});

test("the family verdict labels are derived from the T01 register, not hand-claimed", () => {
  const register = JSON.parse(readRepo("prd/architecture/m210-s01-normative-family-register.json"));
  const byFamily = new Map(register.families.map((family) => [family.family_id, family]));
  for (const card of liveArtifact.dispute_cards) {
    const source = byFamily.get(card.family);
    assert.ok(source, `the T01 register must carry ${card.family}`);
    assert.equal(card.evidence_class, source.evidence_class, `${card.family} evidence class must mirror T01`);
    const expected =
      source.vocabulary_status === "proposed" && source.evidence_class === "source-bound-span"
        ? "conflicted"
        : "unresolved";
    assert.equal(card.verdict, expected, `${card.family} verdict must follow the T01 status rule`);
  }
});

// ---------------------------------------------------------------------------
// negative examples
// ---------------------------------------------------------------------------

test("both negative examples are present, tracked-anchored and non-claiming", () => {
  const negatives = liveArtifact.negative_examples;
  assert.ok(Array.isArray(negatives), "negative_examples must be an array");
  assert.ok(negatives.length >= 2, "at least two negative examples are required");
  for (const exampleId of REQUIRED_NEGATIVE_EXAMPLES) {
    const found = negatives.find((example) => example.example_id === exampleId);
    assert.ok(found, `required negative example ${exampleId} must be present`);
    assert.ok(typeof found.fail_closed_code === "string" && found.fail_closed_code.length > 0);
    assert.ok(typeof found.non_claim === "string" && found.non_claim.length > 0);
    assertTrackedAnchor(`negative example ${exampleId}`, found.anchor);
  }
});

// ---------------------------------------------------------------------------
// corpus probes
// ---------------------------------------------------------------------------

test("the bounded corpus probe set carries one count-only pin per family and no legal text", () => {
  const probes = liveArtifact.corpus_probes;
  assert.ok(Array.isArray(probes), "corpus_probes must be an array");

  if (!corpusLive.present) {
    console.log("M210_S01_CORPUS_ABSENT");
    console.log(`corpus_root=${path.relative(root, path.join(root, "consru_export/consru_export/exports/npa"))}`);
    const result = validateArtifact(liveArtifact, liveEnv({
      rootDir: root,
      artifactText: liveText,
      corpusPresent: false,
    }));
    assert.deepEqual(result.errors, [], "the artifact-integrity block must still hold");
    return;
  }

  assert.equal(probes.length, PROBE_COUNT, "one probe per family");
  assert.deepEqual(probes.map((probe) => probe.family), FAMILY_ORDER);

  for (const probe of probes) {
    assert.deepEqual(
      Object.keys(probe),
      PROBE_KEYS,
      `probe ${probe.probe_id} must carry exactly the closed count-only key set`,
    );
    assert.ok(
      typeof probe.path === "string" &&
        !path.isAbsolute(probe.path) &&
        !probe.path.split("/").includes(".."),
      `probe ${probe.probe_id} path must be repository-relative`,
    );
    assert.ok(existsSync(path.join(root, probe.path)), `probe ${probe.probe_id} must resolve: ${probe.path}`);
    const bytes = readFileSync(path.join(root, probe.path));
    assert.ok(bytes.length > 0, `probe ${probe.probe_id} source must be non-empty`);
    assert.equal(probe.bytes, bytes.length, `probe ${probe.probe_id} byte pin must match`);
    assert.equal(
      probe.sha256,
      `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
      `probe ${probe.probe_id} sha256 pin must match`,
    );
    assert.deepEqual(
      probe.span,
      { start: 0, end: Math.min(bytes.length, PROBE_SPAN_CAP) },
      `probe ${probe.probe_id} span must be the leading bounded window`,
    );
    assert.ok(probe.span.end <= PROBE_SPAN_CAP, "the span must respect the bounded window cap");

    // Anti-leak sample: deterministic windows of the licensed source must not
    // appear in the tracked artifact.
    for (const offset of [0, Math.floor(bytes.length / 4), Math.floor(bytes.length / 2), bytes.length - 128]) {
      const start = Math.max(0, Math.min(offset, bytes.length - 96));
      const window = bytes.subarray(start, start + 96).toString("utf8");
      if (window.length === 96 && /^[\x00-\x7f]*$/.test(window)) {
        assert.ok(!liveText.includes(window), `raw corpus text leaked from ${probe.path}`);
      }
    }
  }

  const result = validateArtifact(liveArtifact, liveEnv({
    rootDir: root,
    artifactText: liveText,
    corpusPresent: true,
    liveProbes: corpusLive.probes,
  }));
  assert.deepEqual(result.errors, [], `live errors: ${JSON.stringify(result.errors)}`);
  console.log("M210_S01_CORPUS_PRESENT");
  console.log(`corpus_probes=${probes.length}`);
});

test("the live corpus re-derives the declared probe pins", () => {
  if (!corpusLive.present) {
    console.log("M210_S01_CORPUS_ABSENT");
    return;
  }
  const declared = new Map(liveArtifact.corpus_probes.map((probe) => [probe.family, probe]));
  for (const probe of corpusLive.probes) {
    const pinned = declared.get(probe.family);
    assert.ok(pinned, `family ${probe.family} must be pinned in the artifact`);
    assert.equal(probe.path, pinned.path, `probe ${probe.family} path drifted`);
    assert.equal(probe.bytes, pinned.bytes, `probe ${probe.family} byte count drifted`);
    assert.equal(probe.sha256, pinned.sha256, `probe ${probe.family} sha256 drifted`);
    assert.deepEqual(probe.span, pinned.span, `probe ${probe.family} span drifted`);
  }
});

// ---------------------------------------------------------------------------
// generator CLI: --check is byte-identical and writes nothing
// ---------------------------------------------------------------------------

test("the generator --check is byte-identical and never writes the artifact", () => {
  const run = spawnSync("node", [GENERATOR, "--check"], { cwd: root, encoding: "utf8" });
  assert.equal(run.status, 0, `--check must succeed: ${run.stderr}`);
  assert.match(run.stdout, /M210_S01_EXAMPLES_CHECK_OK/);
  assert.match(run.stderr, /M210_S01_CORPUS_(ABSENT|PRESENT)/);
  assert.equal(readRepo(ARTIFACT_RELATIVE_PATH), liveText, "the artifact must be byte-identical after --check");
});

test("the generator without a local corpus renders the tracked block and marks the corpus absent", () => {
  const run = spawnSync("node", [GENERATOR, "--print"], {
    cwd: root,
    encoding: "utf8",
    env: { ...process.env, [CORPUS_DIR_ENV]: ABSENT_CORPUS_DIR },
  });
  assert.equal(run.status, 0, `--print must succeed: ${run.stderr}`);
  assert.match(run.stderr, /M210_S01_CORPUS_ABSENT/);
  const artifact = JSON.parse(run.stdout);
  assert.deepEqual(artifact.corpus_probes, [], "a fresh corpus-free render carries no probes");
  assert.deepEqual(
    artifact.dispute_cards.map((card) => card.family),
    FAMILY_ORDER,
    "the tracked block must still cover all eight families",
  );
  const result = validateArtifact(artifact, liveEnv({
    rootDir: root,
    artifactText: JSON.stringify(artifact),
    corpusPresent: false,
  }));
  assert.deepEqual(result.errors, [], "the tracked-only render must validate");
  console.log("M210_S01_CORPUS_ABSENT");
});

// ---------------------------------------------------------------------------
// code coverage: one empirical mutation per documented fail-closed code
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "family_uncovered",
    mutate: (artifact) => {
      artifact.dispute_cards = artifact.dispute_cards.filter((card) => card.family !== "condition");
    },
  },
  {
    code: "tracked_anchor_missing",
    mutate: (artifact) => {
      artifact.dispute_cards[0].anchor.path = "prd/architecture/absent-anchor.json";
    },
    env: () => ({
      exists: (relativePath) => !relativePath.includes("absent-anchor") && existsSync(path.join(root, relativePath)),
    }),
  },
  {
    code: "anchor_untracked",
    mutate: () => {},
    env: (artifact) => ({
      isTracked: (relativePath) => relativePath !== artifact.dispute_cards[0].anchor.path,
    }),
  },
  {
    code: "anchor_hash_mismatch",
    mutate: (artifact) => {
      artifact.dispute_cards[0].anchor.sha256 = `sha256:${"0".repeat(64)}`;
    },
  },
  {
    code: "anchor_drift",
    mutate: (artifact) => {
      artifact.corpus_probes[0].bytes += 1;
    },
  },
  {
    code: "raw_text_leak",
    mutate: (artifact) => {
      artifact.dispute_cards[0].reading_a = "<w:p>duty";
    },
  },
  {
    code: "non_ascii_artifact",
    mutate: (artifact) => {
      artifact.dispute_cards[0].reading_a = "\u041f\u0420\u0410\u0412\u041e";
    },
  },
  {
    code: "self_declared_resolved",
    mutate: (artifact) => {
      artifact.dispute_cards[0].verdict = "resolved";
    },
  },
  {
    code: "negative_example_missing",
    mutate: (artifact) => {
      artifact.negative_examples = artifact.negative_examples.slice(0, 1);
    },
  },
  {
    code: "corpus_probe_writes_text",
    mutate: (artifact) => {
      artifact.corpus_probes[0].text = "raw legal text";
    },
  },
  {
    code: "check_not_byte_identical",
    mutate: () => {},
    env: (artifact) => ({ committedText: `${JSON.stringify(artifact)} ` }),
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const held = ARTIFACT_RELATIVE_PATH;
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const artifact = cloneArtifact();
    entry.mutate(artifact);
    const text = JSON.stringify(artifact);
    if (!Array.isArray(artifact.corpus_probes) || artifact.corpus_probes.length === 0) {
      assert.ok(
        entry.code !== "anchor_drift" && entry.code !== "corpus_probe_writes_text",
        `${entry.code} requires an artifact with committed corpus probes`,
      );
      continue;
    }
    const env = { ...coverageEnv(text), ...(entry.env ? entry.env(artifact) : {}) };
    expectCode(validateArtifact(artifact, env), entry.code);
    covered.add(entry.code);
  }
  assert.deepEqual(
    [...covered].sort(),
    [...EMITTABLE_CODES].sort(),
    `every documented code must fire; unexercised: ${EMITTABLE_CODES.filter((code) => !covered.has(code))}`,
  );
  assert.ok(held.endsWith(ARTIFACT_RELATIVE_PATH), "the artifact path is unchanged");
});

test("the documented code block equals the declared code set", () => {
  const source = readRepo("scripts/m210_s01_examples_contract.test.mjs");
  const block = source.match(/\/\/ DOCUMENTED_CODES_BEGIN\n([\s\S]*?)\/\/ DOCUMENTED_CODES_END/);
  assert.ok(block, "the documented codes block must exist");
  const documented = block[1]
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_]+):/))
    .filter(Boolean)
    .map((match) => match[1]);
  assert.deepEqual(documented.sort(), [...EMITTABLE_CODES].sort());
  assert.deepEqual(
    [...liveArtifact.fail_closed_codes].sort(),
    [...EMITTABLE_CODES].sort(),
    "the artifact must declare exactly the emitted code set",
  );
});

// ---------------------------------------------------------------------------
// negative paths beyond the code-coverage table
// ---------------------------------------------------------------------------

test("negative: an unsupported envelope, card or probe shape fails closed", () => {
  const cases = [
    (artifact) => {
      artifact.dispute_cards[0].adopted = true;
    },
    (artifact) => {
      artifact.dispute_cards[0].requires_human_source_review = false;
    },
    (artifact) => {
      artifact.semantics_adopted = true;
    },
    (artifact) => {
      artifact.corpus_probes[0].span = { start: 10, end: 5 };
    },
    (artifact) => {
      artifact.corpus_probes[0].sha256 = "sha256:XYZ";
    },
    (artifact) => {
      artifact.negative_examples[1].non_claim = "";
    },
    (artifact) => {
      artifact.dispute_cards[0].anchor.path = "/tmp/escape.md";
    },
    (artifact) => {
      artifact.dispute_cards[0].anchor.path = "../../escape.md";
    },
    (artifact) => {
      delete artifact.negative_examples[0].anchor;
    },
  ];
  for (const mutate of cases) {
    const artifact = cloneArtifact();
    mutate(artifact);
    const result = validateArtifact(artifact, coverageEnv(JSON.stringify(artifact)));
    assert.equal(result.ok, false, `${mutate} must fail closed: ${JSON.stringify(result.errors)}`);
  }
});

// ---------------------------------------------------------------------------
// markers (emitted only after the source-bound examples contract holds)
// ---------------------------------------------------------------------------

test("M210 S01 source-bound examples markers", () => {
  const result = validateArtifact(liveArtifact, liveEnv({
    rootDir: root,
    artifactText: liveText,
    corpusPresent: corpusLive.present,
    liveProbes: corpusLive.probes,
  }));
  assert.deepEqual(result.errors, [], `errors: ${JSON.stringify(result.errors)}`);
  console.log("M210_S01_EXAMPLES_OK");
  console.log(`families=${liveArtifact.dispute_cards.length}`);
  console.log(`negative_examples=${liveArtifact.negative_examples.length}`);
  console.log(`corpus_probes=${(liveArtifact.corpus_probes ?? []).length}`);
  console.log(`fail_closed_codes=${EMITTABLE_CODES.length}`);
});
