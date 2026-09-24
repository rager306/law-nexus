#!/usr/bin/env node
// M210-3afp79 S02 T01 -- S01 input rebind and corpus anchor re-derivation.
//
// WHY THIS FILE EXISTS
// prd/architecture/m210-s01-packet-index.json declares a source_revision_policy:
// before the S01 packet is shown to the owner, every tracked input must be
// re-bound and every corpus anchor re-derived. S01 left that open: in the
// corpus-absent mode the committed probe pins were carried over unchecked and
// were not marked unverified (S01 Known Limitations (b)). A question put to the
// owner on an unchecked revision is not source-bound, and an unchecked anchor
// that looks checked is worse than an absent one. This generator closes both.
//
// WHAT IS RE-DERIVED, FROM WHERE
//   * every artifacts[] and source_bindings[] record of
//     prd/architecture/m210-s01-packet-index.json, re-hashed live from its
//     repository-relative path (18 records in total: 12 artifacts + 6 bindings)
//   * every corpus_probes[] record of
//     prd/architecture/m210-s01-source-bound-examples.json, re-derived live
//     (sha256, byte count, span) when the licensed corpus resolves
//   * the engine aggregate source revision, captured live from
//     scripts/m204_s08_source_revision.mjs (never hardcoded)
//
// WHAT IS NEVER WRITTEN
//   * No legal text: a corpus anchor records only path, span, bytes, sha256.
//   * No timestamp and no hardcoded aggregate hash: the report is canonical
//     compact ASCII JSON with a fixed key order, so a whole-file byte compare is
//     the determinism proof.
//
// CORPUS-GATED BEHAVIOUR (the fix for S01 Known Limitations (b))
//   When the licensed corpus resolves, every anchor is re-derived live and
//   marked verified:true with an empty unverified_reason. When it does not
//   resolve, M210_S02_CORPUS_ABSENT is printed and EVERY anchor is explicitly
//   marked verified:false with unverified_reason:corpus_absent. A committed pin
//   is never carried over as if it were verified: an anchor whose verified flag
//   is absent or contradicts its reason fails closed with
//   corpus_anchor_unverified_unmarked.
//
// SOURCE REVISION IS A SNAPSHOT, NOT A LIVE INVARIANT
//   The engine aggregate hash covers tracked content plus untracked non-ignored
//   files (`git ls-files --cached --others --exclude-standard`), so writing this
//   report shifts the aggregate. The stored value is therefore the revision
//   captured at rebind time, before this report existed; it is not a live
//   invariant. Staleness of the rebind is guarded exactly and separately by the
//   per-input live sha256 comparison, which is the real fail-closed gate.
//   `--check` re-renders everything live and reuses the committed
//   source_revision for the byte compare, while still capturing the live
//   revision to prove the capture path works.
//
// NAMED FAIL-CLOSED CODES (every one is exercised by the contract test)
//   input_missing                     a declared input is absent, or a live corpus anchor is absent
//   input_hash_mismatch               a live sha256 differs from its pin, or a corpus anchor drifted
//   input_untracked                   a declared input exists but git does not track it
//   input_path_not_repo_relative      a path is absolute, traverses `..`, escapes the repository root, or is an ignored overlay path
//   corpus_anchor_unverified_unmarked a corpus anchor carries no explicit verified boolean, or its flag contradicts its reason
//   check_not_byte_identical          --check rendered bytes differ from the committed report
//   source_revision_not_captured      source_revision is absent, malformed, or a stored aggregate hash
//   raw_text_leak                     the report text carries an XML tag or a provider text marker
//   non_ascii_artifact                the report text carries a non-ASCII byte
//   packet_index_unreadable           the packet index or its source_revision_policy cannot be read
//
// USAGE
//   node scripts/m210_s02_rebind.mjs --write   # default
//   node scripts/m210_s02_rebind.mjs --check
//   node scripts/m210_s02_rebind.mjs --print

import { execFileSync, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, realpathSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const REPORT_RELATIVE_PATH = "prd/architecture/m210-s02-rebind-report.json";
export const PACKET_INDEX_PATH = "prd/architecture/m210-s01-packet-index.json";
export const EXAMPLES_PATH = "prd/architecture/m210-s01-source-bound-examples.json";
export const SOURCE_REVISION_SCRIPT = "scripts/m204_s08_source_revision.mjs";

export const SCHEMA = "law-nexus/m210-s02-rebind-report/v1";
export const KIND = "m210-s02-rebind-report";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S02";
export const TASK = "T01";
export const LIFECYCLE = ["proposed"];
export const REQUIREMENT_REFS = ["RC28-F18", "R074"];

// The licensed corpus root named by the plan. The probes live one level deeper
// (exports/npa) and are resolved from their recorded repository-relative path.
export const CORPUS_ROOT_RELATIVE = "consru_export/consru_export/exports";
export const CORPUS_DIR_ENV = "M210_S02_CORPUS_DIR";
export const CORPUS_ABSENT_MARKER = "M210_S02_CORPUS_ABSENT";
export const CORPUS_PRESENT_MARKER = "M210_S02_CORPUS_PRESENT";
export const WRITTEN_MARKER = "M210_S02_REBIND_WRITTEN";
export const CHECK_OK_MARKER = "M210_S02_REBIND_CHECK_OK";
export const PRINT_MARKER = "M210_S02_REBIND_PRINTED";
export const CONTRACT_MARKER = "M210_S02_REBIND_OK";

export const PROBE_COUNT = 8;
export const PROBE_SPAN_CAP = 4096;

export const EMITTABLE_CODES = [
  "input_missing",
  "input_hash_mismatch",
  "input_untracked",
  "input_path_not_repo_relative",
  "corpus_anchor_unverified_unmarked",
  "check_not_byte_identical",
  "source_revision_not_captured",
  "raw_text_leak",
  "non_ascii_artifact",
  "packet_index_unreadable",
];

export const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;
export const SOURCE_REVISION_PATTERN = /^sha256:[0-9a-f]{64}$/;
export const SOURCE_REVISION_POLICY_ECHO_KEYS = [
  "must_rebind_every_tracked_input",
  "must_rederive_corpus_anchors",
  "aggregate_engine_hash",
  "hardcode_forbidden",
  "statement",
];
export const INPUT_VERDICTS = [
  "match",
  "missing",
  "hash_mismatch",
  "untracked",
  "path_not_repo_relative",
];
export const ANCHOR_UNVERIFIED_REASONS = [
  "",
  "corpus_absent",
  "path_not_repo_relative",
  "anchor_missing",
  "anchor_drift",
];
export const DRIFT_KINDS = ["input", "corpus_anchor"];

const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

const NON_CLAIMS = [
  "This report is not an adoption of normative semantics: it re-binds inputs and re-derives corpus anchors only.",
  "It is non-authoritative: it cannot satisfy a requirement, promote a lifecycle or establish legal correctness.",
  "A verified corpus anchor records only path, span, bytes and sha256; no legal text is copied and an anchor is not a reading.",
  "source_revision is the engine aggregate hash captured at rebind time, before this report was written; it is not a legal or semantic revision.",
  "A rebind proves only that the declared inputs still hash to their pins and that the corpus anchors still resolve; it does not validate any claim made from them.",
  "Section 3 of prd/temporal-legal-model.md is unchanged: the deferred terms stay deferred-undefined.",
];

export class RebindError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "RebindError";
    this.code = code;
    this.detail = detail;
  }
}

function fail(code, detail) {
  throw new RebindError(code, detail);
}

// ---------------------------------------------------------------------------
// repository helpers
// ---------------------------------------------------------------------------

export function isRepoRelative(value) {
  if (typeof value !== "string" || value.length === 0) return false;
  if (path.isAbsolute(value)) return false;
  if (value.startsWith("/")) return false;
  return value.split("/").every((part) => part !== "" && part !== ".." && part !== ".");
}

export function isIgnoredPath(value) {
  return (
    typeof value === "string" && IGNORED_SOURCE_PREFIXES.some((prefix) => value.startsWith(prefix))
  );
}

export function admissiblePath(value) {
  return isRepoRelative(value) && !isIgnoredPath(value);
}

// Node's test runner marks each child test process with NODE_TEST_CONTEXT. A
// contract spawned from inside `node --test` inherits it and the nested runner
// then suppresses reporter output: the run exits 0 but prints no parseable
// counts, which would look green. Strip it for every spawn (S01 precedent).
export function cleanTestEnv(env = process.env) {
  const cleaned = { ...env };
  delete cleaned.NODE_TEST_CONTEXT;
  return cleaned;
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

export function corpusDirectory(rootDir = REPO_ROOT, override) {
  return override ? path.resolve(override) : path.join(rootDir, CORPUS_ROOT_RELATIVE);
}

export function corpusPresent(rootDir = REPO_ROOT, override) {
  const directory = corpusDirectory(rootDir, override);
  return existsSync(directory) && statSync(directory).isDirectory();
}

// A probe path is recorded repository-relative (for example
// consru_export/consru_export/exports/npa/x.xml). It is resolved under the
// corpus root when it sits below it, so an alternate corpus mount works without
// rewriting the recorded pins.
export function resolveProbePath(rootDir, directory, recordedPath) {
  const prefix = `${CORPUS_ROOT_RELATIVE}/`;
  if (isRepoRelative(recordedPath) && recordedPath.startsWith(prefix)) {
    return path.join(directory, recordedPath.slice(prefix.length));
  }
  return path.join(rootDir, recordedPath);
}

export function fileLookup(rootDir = REPO_ROOT) {
  const realRoot = realpathSync(rootDir);
  const bytesCache = new Map();
  const trackedCache = new Map();
  const insideCache = new Map();
  const bytes = (relativePath) => {
    if (bytesCache.has(relativePath)) return bytesCache.get(relativePath);
    let value = null;
    try {
      value = readFileSync(path.join(rootDir, relativePath));
    } catch {
      value = null;
    }
    bytesCache.set(relativePath, value);
    return value;
  };
  return {
    exists: (relativePath) => existsSync(path.join(rootDir, relativePath)),
    isTracked: (relativePath) => {
      if (trackedCache.has(relativePath)) return trackedCache.get(relativePath);
      const tracked = gitTracks(rootDir, relativePath);
      trackedCache.set(relativePath, tracked);
      return tracked;
    },
    bytes,
    sha256: (relativePath) => {
      const value = bytes(relativePath);
      if (!value) return null;
      return `sha256:${createHash("sha256").update(value).digest("hex")}`;
    },
    // Symlink escapes are fail-closed: a declared path whose real target leaves
    // the repository root is not admissible, whatever its spelling.
    insideRoot: (relativePath) => {
      if (insideCache.has(relativePath)) return insideCache.get(relativePath);
      let inside = false;
      try {
        const real = realpathSync(path.join(rootDir, relativePath));
        inside = real === realRoot || real.startsWith(`${realRoot}${path.sep}`);
      } catch {
        inside = false;
      }
      insideCache.set(relativePath, inside);
      return inside;
    },
  };
}

// ---------------------------------------------------------------------------
// source loading
// ---------------------------------------------------------------------------

export function loadPacketIndex(rootDir = REPO_ROOT) {
  const absolute = path.join(rootDir, PACKET_INDEX_PATH);
  if (!existsSync(absolute)) fail("packet_index_unreadable", `${PACKET_INDEX_PATH} is absent`);
  let parsed;
  try {
    parsed = JSON.parse(readFileSync(absolute, "utf8"));
  } catch (error) {
    fail("packet_index_unreadable", `${PACKET_INDEX_PATH} is not parseable: ${error?.message}`);
  }
  if (!parsed || typeof parsed !== "object") {
    fail("packet_index_unreadable", `${PACKET_INDEX_PATH} is not an object`);
  }
  if (!Array.isArray(parsed.artifacts) || !Array.isArray(parsed.source_bindings)) {
    fail("packet_index_unreadable", `${PACKET_INDEX_PATH} carries no artifacts[] / source_bindings[]`);
  }
  if (!parsed.source_revision_policy || typeof parsed.source_revision_policy !== "object") {
    fail("packet_index_unreadable", `${PACKET_INDEX_PATH} carries no source_revision_policy`);
  }
  return parsed;
}

export function loadExamples(rootDir = REPO_ROOT) {
  const absolute = path.join(rootDir, EXAMPLES_PATH);
  if (!existsSync(absolute)) fail("packet_index_unreadable", `${EXAMPLES_PATH} is absent`);
  let parsed;
  try {
    parsed = JSON.parse(readFileSync(absolute, "utf8"));
  } catch (error) {
    fail("packet_index_unreadable", `${EXAMPLES_PATH} is not parseable: ${error?.message}`);
  }
  if (!Array.isArray(parsed?.corpus_probes)) {
    fail("packet_index_unreadable", `${EXAMPLES_PATH} carries no corpus_probes[]`);
  }
  return parsed;
}

export function declaredInputRecords(packetIndex) {
  return [
    ...(packetIndex.artifacts ?? []).map((record) => ({ ...record, record_set: "artifacts" })),
    ...(packetIndex.source_bindings ?? []).map((record) => ({ ...record, record_set: "source_bindings" })),
  ];
}

// ---------------------------------------------------------------------------
// source revision capture (live subprocess, never a stored literal)
// ---------------------------------------------------------------------------

export function captureSourceRevision(rootDir = REPO_ROOT, options = {}) {
  const spawned = spawnSync(options.execPath ?? process.execPath, [SOURCE_REVISION_SCRIPT], {
    cwd: rootDir,
    encoding: "utf8",
    timeout: options.timeoutMs ?? 120000,
    maxBuffer: 8 * 1024 * 1024,
    env: cleanTestEnv(options.env ?? process.env),
  });
  const output = `${spawned.stdout || ""}${spawned.stderr || ""}`.trim();
  if (spawned.status !== 0) {
    fail("source_revision_not_captured", `${SOURCE_REVISION_SCRIPT} exited ${spawned.status}: ${output}`);
  }
  let parsed;
  try {
    parsed = JSON.parse(output.split("\n").filter(Boolean).pop());
  } catch (error) {
    fail("source_revision_not_captured", `${SOURCE_REVISION_SCRIPT} printed no JSON: ${output}`);
  }
  if (parsed?.ok !== true || typeof parsed.source_revision !== "string") {
    fail("source_revision_not_captured", `${SOURCE_REVISION_SCRIPT} returned ${JSON.stringify(parsed)}`);
  }
  if (!SOURCE_REVISION_PATTERN.test(parsed.source_revision)) {
    fail("source_revision_not_captured", `unexpected source revision shape: ${parsed.source_revision}`);
  }
  return parsed.source_revision;
}

// ---------------------------------------------------------------------------
// derivation
// ---------------------------------------------------------------------------

export function deriveReboundInputs(packetIndex, lookup) {
  const rows = [];
  const drift = [];
  for (const record of declaredInputRecords(packetIndex)) {
    const declaredPath = record.path;
    const expected = record.sha256;
    let verdict = "match";
    let live = "";
    if (!admissiblePath(declaredPath) || !lookup.insideRoot(declaredPath)) {
      verdict = "path_not_repo_relative";
    } else if (!lookup.exists(declaredPath)) {
      verdict = "missing";
    } else if (!lookup.isTracked(declaredPath)) {
      verdict = "untracked";
    } else {
      live = lookup.sha256(declaredPath) ?? "";
      if (typeof expected !== "string" || !SHA_PATTERN.test(expected) || live !== expected) {
        verdict = "hash_mismatch";
      }
    }
    if (verdict !== "match") {
      drift.push({
        kind: "input",
        path: typeof declaredPath === "string" ? declaredPath : String(declaredPath),
        detail: `${verdict}${live ? ` live=${live}` : ""}`,
      });
    }
    rows.push({
      path: declaredPath,
      role: record.role,
      expected_sha256: expected,
      live_sha256: live,
      verdict,
    });
  }
  return { rows, drift };
}

export function deriveCorpusAnchors(examples, options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const directory = options.corpusDir ?? corpusDirectory(rootDir);
  const present = options.corpusPresent ?? false;
  const lookup = options.lookup ?? fileLookup(rootDir);
  const probes = Array.isArray(examples?.corpus_probes) ? examples.corpus_probes : [];
  const rows = [];
  const drift = [];
  for (const probe of probes) {
    const recordedPath = probe.path;
    const base = {
      probe_id: probe.probe_id,
      family: probe.family,
      path: recordedPath,
      span: probe.span,
      bytes: probe.bytes,
      sha256: probe.sha256,
    };
    if (!present) {
      rows.push({ ...base, verified: false, unverified_reason: "corpus_absent" });
      continue;
    }
    if (!admissiblePath(recordedPath)) {
      rows.push({ ...base, verified: false, unverified_reason: "path_not_repo_relative" });
      drift.push({
        kind: "corpus_anchor",
        path: String(recordedPath),
        detail: "path_not_repo_relative",
      });
      continue;
    }
    const absolute = resolveProbePath(rootDir, directory, recordedPath);
    if (!existsSync(absolute)) {
      rows.push({ ...base, verified: false, unverified_reason: "anchor_missing" });
      drift.push({ kind: "corpus_anchor", path: recordedPath, detail: "anchor_missing" });
      continue;
    }
    const bytes = readFileSync(absolute);
    const liveSha = `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
    const liveSpan = { start: 0, end: Math.min(bytes.length, PROBE_SPAN_CAP) };
    const matches =
      liveSha === probe.sha256 &&
      bytes.length === probe.bytes &&
      liveSpan.start === probe.span?.start &&
      liveSpan.end === probe.span?.end;
    if (!matches) {
      drift.push({ kind: "corpus_anchor", path: recordedPath, detail: "anchor_drift" });
    }
    rows.push({
      probe_id: probe.probe_id,
      family: probe.family,
      path: recordedPath,
      span: matches ? probe.span : liveSpan,
      bytes: bytes.length,
      sha256: liveSha,
      verified: matches,
      unverified_reason: matches ? "" : "anchor_drift",
    });
  }
  return { rows, drift };
}

export function derivePolicyEcho(packetIndex) {
  const policy = packetIndex?.source_revision_policy;
  if (!policy || typeof policy !== "object") {
    fail("packet_index_unreadable", "the packet index carries no source_revision_policy");
  }
  const echo = {};
  for (const key of SOURCE_REVISION_POLICY_ECHO_KEYS) {
    if (policy[key] === undefined) {
      fail("packet_index_unreadable", `source_revision_policy.${key} is absent`);
    }
    echo[key] = policy[key];
  }
  return echo;
}

export function renderReport(options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const lookup = options.lookup ?? fileLookup(rootDir);
  const packetIndex = options.packetIndex ?? loadPacketIndex(rootDir);
  const examples = options.examples ?? loadExamples(rootDir);
  const directory = options.corpusDir ?? corpusDirectory(rootDir, options.corpusDirOverride);
  const present = options.corpusPresent ?? corpusPresent(rootDir, options.corpusDirOverride);
  const sourceRevision = options.sourceRevision ?? captureSourceRevision(rootDir);
  if (!SOURCE_REVISION_PATTERN.test(String(sourceRevision))) {
    fail("source_revision_not_captured", `source revision ${sourceRevision} is not sha256:<64hex>`);
  }
  const inputs = deriveReboundInputs(packetIndex, lookup);
  const anchors = deriveCorpusAnchors(examples, {
    rootDir,
    corpusDir: directory,
    corpusPresent: present,
    lookup,
  });
  const report = {
    schema: SCHEMA,
    schema_version: 1,
    kind: KIND,
    milestone: MILESTONE,
    slice: SLICE,
    task: TASK,
    lifecycle: LIFECYCLE,
    authoritative: false,
    ascii_only: true,
    requirement_refs: REQUIREMENT_REFS,
    rebound_inputs: inputs.rows,
    corpus_anchors: anchors.rows,
    source_revision: sourceRevision,
    drift: [...inputs.drift, ...anchors.drift],
    fail_closed_codes: EMITTABLE_CODES,
    non_claims: NON_CLAIMS,
    source_revision_policy_echo: derivePolicyEcho(packetIndex),
  };
  return {
    report,
    text: JSON.stringify(report),
    corpusPresent: present,
    liveInputs: inputs.rows,
    liveAnchors: anchors.rows,
    drift: report.drift,
    declaredInputCount: declaredInputRecords(packetIndex).length,
    declaredProbeCount: examples.corpus_probes.length,
  };
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

export function validateReport(report, env = {}) {
  const errors = [];
  const code = (name, detail) => errors.push({ name, detail });
  const text = typeof env.text === "string" ? env.text : JSON.stringify(report);
  const exists = env.exists ?? (() => true);
  const isTracked = env.isTracked ?? (() => true);
  const sha256 = env.sha256 ?? (() => null);
  const insideRoot = env.insideRoot ?? (() => true);
  const present = env.corpusPresent ?? false;
  const liveAnchors = Array.isArray(env.liveAnchors) ? env.liveAnchors : [];
  const liveByProbe = new Map(liveAnchors.map((anchor) => [anchor.probe_id, anchor]));

  // 1. text hygiene: ASCII-only, no XML tags and no provider text markers.
  const offending = [...text].findIndex((character) => character.charCodeAt(0) > 0x7f);
  if (offending >= 0) code("non_ascii_artifact", `non-ascii character at index ${offending}`);
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) code("raw_text_leak", `text marker ${marker}`);
  }

  // 2. the packet index must be readable: its policy echo is the fingerprint.
  if (env.packetIndexError) code("packet_index_unreadable", String(env.packetIndexError));
  const echo = report?.source_revision_policy_echo;
  if (!echo || typeof echo !== "object") {
    code("packet_index_unreadable", "source_revision_policy_echo is missing");
  } else {
    if (echo.must_rebind_every_tracked_input !== true) {
      code("packet_index_unreadable", "must_rebind_every_tracked_input must be true");
    }
    if (echo.must_rederive_corpus_anchors !== true) {
      code("packet_index_unreadable", "must_rederive_corpus_anchors must be true");
    }
    if (echo.hardcode_forbidden !== true) {
      code("packet_index_unreadable", "hardcode_forbidden must be true");
    }
    if (typeof echo.aggregate_engine_hash !== "string" || echo.aggregate_engine_hash === "") {
      code("packet_index_unreadable", "aggregate_engine_hash must name the validate-time supply");
    }
    if (typeof echo.statement !== "string" || echo.statement.trim() === "") {
      code("packet_index_unreadable", "statement is missing");
    }
  }

  // 3. the source revision was captured live, never stored as an aggregate hash.
  const revision = report?.source_revision;
  if (typeof revision !== "string" || !SOURCE_REVISION_PATTERN.test(revision)) {
    code("source_revision_not_captured", `source_revision=${JSON.stringify(revision)}`);
  } else if (typeof env.sourceRevision === "string" && env.sourceRevision !== revision) {
    code("source_revision_not_captured", "source_revision differs from the live capture");
  }
  if (
    echo &&
    typeof echo.aggregate_engine_hash === "string" &&
    SOURCE_REVISION_PATTERN.test(echo.aggregate_engine_hash)
  ) {
    code(
      "source_revision_not_captured",
      "the aggregate engine hash is stored instead of supplied at validate time",
    );
  }

  // 4. rebound inputs: every declared record present, tracked and hash-bound.
  const inputs = Array.isArray(report?.rebound_inputs) ? report.rebound_inputs : null;
  if (!inputs || inputs.length === 0) {
    code("input_missing", "rebound_inputs is missing or empty");
  } else {
    if (typeof env.declaredInputCount === "number" && inputs.length !== env.declaredInputCount) {
      code(
        "input_missing",
        `rebound_inputs carries ${inputs.length} rows, the packet index declares ${env.declaredInputCount}`,
      );
    }
    const byPath = new Map();
    for (const row of inputs) {
      const scope = `input ${typeof row?.path === "string" ? row.path : "<unnamed>"}`;
      if (typeof row?.path === "string") byPath.set(row.path, row);
      if (!admissiblePath(row?.path) || !insideRoot(row?.path)) {
        code("input_path_not_repo_relative", `${scope} is not an admissible repository-relative path`);
        continue;
      }
      if (!exists(row.path)) {
        code("input_missing", `${scope} is absent`);
        continue;
      }
      if (!isTracked(row.path)) code("input_untracked", `${scope} is not git-tracked`);
      if (typeof row.expected_sha256 !== "string" || !SHA_PATTERN.test(row.expected_sha256)) {
        code("input_hash_mismatch", `${scope} expected_sha256 is malformed`);
        continue;
      }
      const live = sha256(row.path);
      if (typeof live === "string" && live !== row.expected_sha256) {
        code("input_hash_mismatch", `${scope} live sha256 differs from the pin`);
      }
      if (!INPUT_VERDICTS.includes(row.verdict)) {
        code("input_hash_mismatch", `${scope} verdict ${JSON.stringify(row.verdict)} is unknown`);
        continue;
      }
      if (row.verdict !== "match") {
        code("input_hash_mismatch", `${scope} verdict ${row.verdict} is not a bound verdict`);
      } else if (row.live_sha256 !== row.expected_sha256) {
        code("input_hash_mismatch", `${scope} live_sha256 does not match the pin`);
      }
    }
    // drift consistency: a drifted input is recorded exactly once.
    const drift = Array.isArray(report?.drift) ? report.drift : null;
    if (!drift) {
      code("input_missing", "drift is missing");
    } else {
      for (const [declaredPath, row] of byPath) {
        const recorded = drift.some((entry) => entry?.kind === "input" && entry?.path === declaredPath);
        if (row.verdict !== "match" && !recorded) {
          code("input_hash_mismatch", `input ${declaredPath} drifted without a drift row`);
        }
        if (row.verdict === "match" && recorded) {
          code("input_hash_mismatch", `input ${declaredPath} carries a drift row but no drift`);
        }
      }
      for (const entry of drift) {
        if (!DRIFT_KINDS.includes(entry?.kind)) {
          code("input_hash_mismatch", `drift kind ${JSON.stringify(entry?.kind)} is unknown`);
          continue;
        }
        if (typeof entry.path !== "string" || entry.path === "") {
          code("input_hash_mismatch", "drift row path is missing");
        } else if (entry.kind === "input" && !byPath.has(entry.path)) {
          code("input_hash_mismatch", `drift row names an undeclared input ${entry.path}`);
        }
        if (typeof entry.detail !== "string" || entry.detail === "") {
          code("input_hash_mismatch", "drift row detail is missing");
        }
      }
    }
  }

  // 5. corpus anchors: never verified without an explicit, consistent mark.
  const anchors = Array.isArray(report?.corpus_anchors) ? report.corpus_anchors : null;
  if (!anchors) {
    code("corpus_anchor_unverified_unmarked", "corpus_anchors is missing");
  } else {
    if (typeof env.declaredProbeCount === "number" && anchors.length !== env.declaredProbeCount) {
      code(
        "input_missing",
        `corpus_anchors carries ${anchors.length} rows, the examples artifact declares ${env.declaredProbeCount}`,
      );
    }
    for (const anchor of anchors) {
      const scope = `anchor ${typeof anchor?.probe_id === "string" ? anchor.probe_id : "<unnamed>"}`;
      if (typeof anchor?.verified !== "boolean") {
        code("corpus_anchor_unverified_unmarked", `${scope} carries no explicit verified boolean`);
        continue;
      }
      if (anchor.verified === false) {
        if (!(typeof anchor.unverified_reason === "string" && anchor.unverified_reason !== "")) {
          code("corpus_anchor_unverified_unmarked", `${scope} is unverified without a reason`);
        }
      } else if (anchor.unverified_reason !== "") {
        code("corpus_anchor_unverified_unmarked", `${scope} is verified but carries an unverified_reason`);
      }
      if (anchor.verified === true && !present) {
        code("corpus_anchor_unverified_unmarked", `${scope} claims verified while the corpus is absent`);
      }
      if (!admissiblePath(anchor.path)) {
        code("input_path_not_repo_relative", `${scope} path is not an admissible repository-relative path`);
        continue;
      }
      if (!present) continue;
      const live = liveByProbe.get(anchor.probe_id);
      if (!live) {
        code("input_missing", `${scope} has no live re-derivation`);
        continue;
      }
      const liveMatches =
        live.sha256 === anchor.sha256 &&
        live.bytes === anchor.bytes &&
        live.path === anchor.path &&
        live.span?.start === anchor.span?.start &&
        live.span?.end === anchor.span?.end;
      if (!liveMatches) {
        code("input_hash_mismatch", `${scope} does not match its live re-derivation`);
      } else if (anchor.verified !== true) {
        code(
          "corpus_anchor_unverified_unmarked",
          `${scope} is not verified although its live anchor matches`,
        );
      }
    }
  }

  // 6. --check: rendered bytes must equal the committed report bytes.
  if (typeof env.committedText === "string" && env.committedText !== text) {
    code("check_not_byte_identical", "rendered bytes differ from the committed report");
  }

  return { ok: errors.length === 0, errors };
}

export function liveEnv(options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const lookup = options.lookup ?? fileLookup(rootDir);
  return {
    text: options.text,
    committedText: options.committedText,
    corpusPresent: options.corpusPresent ?? false,
    liveAnchors: options.liveAnchors ?? [],
    declaredInputCount: options.declaredInputCount,
    declaredProbeCount: options.declaredProbeCount,
    sourceRevision: options.sourceRevision,
    packetIndexError: options.packetIndexError,
    exists: lookup.exists,
    isTracked: lookup.isTracked,
    sha256: lookup.sha256,
    insideRoot: lookup.insideRoot,
  };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

export function runRebind(argv = [], options = {}) {
  const mode = argv.includes("--check") ? "check" : argv.includes("--print") ? "print" : "write";
  const rootDir = options.rootDir ?? REPO_ROOT;
  const reportPath = path.join(rootDir, REPORT_RELATIVE_PATH);
  const committedText = existsSync(reportPath) ? readFileSync(reportPath, "utf8") : null;
  const lookup = options.lookup ?? fileLookup(rootDir);
  const override = options.corpusDirOverride ?? process.env[CORPUS_DIR_ENV];
  const directory = options.corpusDir ?? corpusDirectory(rootDir, override);
  const present = options.corpusPresent ?? corpusPresent(rootDir, override);
  const stderr = [];
  const stdout = [];
  if (present) {
    stderr.push(`${CORPUS_PRESENT_MARKER} root=${CORPUS_ROOT_RELATIVE}`);
  } else {
    stderr.push(CORPUS_ABSENT_MARKER);
  }

  let liveRevision;
  try {
    liveRevision = options.sourceRevision ?? captureSourceRevision(rootDir, options);
  } catch (error) {
    const detail = error instanceof RebindError ? `${error.code}: ${error.detail}` : String(error);
    return { mode, exitCode: 1, stdout: "", stderr: [...stderr, detail], wrote: false };
  }

  // source_revision is a snapshot: the report's own bytes shift the engine
  // aggregate, so --check reuses the committed value for the byte compare and
  // still captures the live revision above to prove the capture path works.
  let renderRevision = liveRevision;
  if (mode === "check" && committedText !== null) {
    try {
      const committed = JSON.parse(committedText);
      if (typeof committed?.source_revision === "string") renderRevision = committed.source_revision;
    } catch {
      renderRevision = liveRevision;
    }
  }

  let rendered;
  try {
    rendered = renderReport({
      rootDir,
      lookup,
      corpusDir: directory,
      corpusPresent: present,
      corpusDirOverride: override,
      sourceRevision: renderRevision,
      packetIndex: options.packetIndex,
      examples: options.examples,
    });
  } catch (error) {
    const detail = error instanceof RebindError ? `${error.code}: ${error.detail}` : String(error);
    return { mode, exitCode: 1, stdout: "", stderr: [...stderr, detail], wrote: false };
  }

  const env = liveEnv({
    rootDir,
    lookup,
    text: rendered.text,
    committedText: mode === "check" ? committedText ?? "" : undefined,
    corpusPresent: present,
    liveAnchors: rendered.liveAnchors,
    declaredInputCount: rendered.declaredInputCount,
    declaredProbeCount: rendered.declaredProbeCount,
    sourceRevision: mode === "write" ? liveRevision : undefined,
  });
  const result = validateReport(rendered.report, env);
  if (!result.ok) {
    for (const error of result.errors) stderr.push(`${error.name}: ${error.detail}`);
    return {
      mode,
      exitCode: 1,
      stdout: "",
      stderr,
      wrote: false,
      report: rendered.report,
      text: rendered.text,
      errors: result.errors,
    };
  }

  if (mode === "print") {
    stdout.push(rendered.text);
    stderr.push(PRINT_MARKER);
    return { mode, exitCode: 0, stdout, stderr, wrote: false, report: rendered.report, text: rendered.text };
  }
  if (mode === "check") {
    if (committedText === null) {
      return {
        mode,
        exitCode: 1,
        stdout: "",
        stderr: [...stderr, "check_not_byte_identical: the committed report is absent"],
        wrote: false,
      };
    }
    stdout.push(CHECK_OK_MARKER);
    return { mode, exitCode: 0, stdout, stderr, wrote: false, report: rendered.report, text: rendered.text };
  }
  if (!options.dryRun) writeFileSync(reportPath, rendered.text);
  stdout.push(WRITTEN_MARKER);
  return {
    mode,
    exitCode: 0,
    stdout,
    stderr,
    wrote: !options.dryRun,
    report: rendered.report,
    text: rendered.text,
  };
}

export function main(argv = process.argv.slice(2)) {
  const result = runRebind(argv);
  for (const line of result.stderr) process.stderr.write(`${line}\n`);
  for (const line of result.stdout) process.stdout.write(`${line}\n`);
  process.exitCode = result.exitCode;
  return result;
}

const invokedDirectly =
  typeof process.argv[1] === "string" &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedDirectly) {
  main();
}
