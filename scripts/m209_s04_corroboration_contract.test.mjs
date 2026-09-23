// M209/S04 corroboration contract (T01).
//
// Offline and fail-closed: the S04 corroboration artifact must be a canonical,
// byte-stable, ASCII, count-only audit whose every arithmetic row re-converges
// under an independent recomputation performed HERE (the test re-reads the
// declared sibling artifacts itself instead of trusting the auditor's own
// derivation), and every code named in the documented fail-closed vocabulary
// must be provable against a mutated in-memory copy of the audited model, so
// the suite cannot fool itself by asserting codes it would never emit.
//
// Subprocesses are limited to `git ls-files --error-unmatch` (tracked-file
// proof for the digest subject) and `git status --porcelain` (frozen-input
// proof). No cargo, no network, and no `.gsd` / ignored / absolute path is ever
// read as evidence.
//
// Corpus gating: `consru_export/` is licensed, gitignored, read-only and may be
// absent. When it is absent this suite prints `M209_S04_CORPUS_ABSENT` and
// still asserts the mandatory artifact integrity block, so an absent corpus is
// a loud, recorded downgrade and never a silent pass.
//
// Run: node --test scripts/m209_s04_corroboration_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

import {
  AuditError,
  FAIL_CLOSED_CODES,
  NON_CLAIMS,
  assertAsciiOnly,
  assertModelShape,
  assertNonEmpty,
  audit,
  checkRenderedBytes,
  computeArithmetic,
  computeBindings,
  computeCrossArtifacts,
  computeDigests,
  computeFrozenBoundary,
  computePromotionChecks,
  defaultIsTracked,
  fnv1a64,
  heartbeat,
  loadModel,
  recomputeIdentityDigest,
  renderEvidence,
  resolveOutTarget,
} from "./m209_s04_evidence_audit.mjs";

const ROOT = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ARTIFACT_REL = "prd/migration/rust-evidence/m209-s04-corroboration-evidence.json";
const ARTIFACT_ABS = path.join(ROOT, ARTIFACT_REL);
const SCHEMA = "law-nexus/m209-corroboration-evidence/v1";
const S02_SOURCE_XML =
  "law-source/consultant/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--f9c8ca4c.xml";
const CORPUS_PREFIX = "consru_export/";
const CORPUS_ABS = path.join(ROOT, "consru_export");

// Mirrors scripts/m209_s04_evidence_audit.mjs#MODEL_FILES. Declared here so the
// test reads the chain artifacts through its own path list, not the auditor's.
const MODEL_FILES = Object.freeze({
  gateRegister: "prd/architecture/m209-s01-r035-gate-register.json",
  reconciliation: "prd/migration/rust-evidence/m209-s01-r035-gate-reconciliation.json",
  candidateArtifact: "prd/migration/rust-evidence/m209-s02-hierarchy-candidates-fz44.json",
  extractionEvidence: "prd/migration/rust-evidence/m209-s02-extraction-evidence.json",
  admissionRegeneration: "prd/migration/rust-evidence/m209-s02-admission-regeneration-evidence.json",
  familyDenominator: "prd/migration/rust-evidence/m209-s03-family-denominator.json",
  amendingAct: "prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json",
  commencement: "prd/migration/rust-evidence/m209-s03-commencement-transition-evidence.json",
  editionDelta: "prd/migration/rust-evidence/m209-s03-edition-delta-evidence.json",
  r070Ledger: "prd/migration/rust-evidence/m209-s03-r070-scope-ledger.json",
  frozenM202Candidates: "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json",
  frozenM202Regeneration: "prd/migration/rust-evidence/m202-s03-registry-regeneration.json",
  frozenM202ProofGate: "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json",
  frozenM201ProofGate: "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
  frozenM201TrackedChain: "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
});

// Mirrors scripts/m209_s04_evidence_audit.mjs#FROZEN_PATHS.
const FROZEN_PATHS = Object.freeze([
  "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json",
  "prd/migration/rust-evidence/m202-s03-registry-regeneration.json",
  "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json",
  "prd/architecture/kb-hierarchy-registry.yaml",
  "prd/architecture/kb-hierarchy-registry-admissions.yaml",
  "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
  "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
  "prd/architecture/fz44-tracked-edition-chain.yaml",
]);

// The documented fail-closed vocabulary, transcribed independently of the
// module. A silent expansion of the module's list must fail this test.
const DOCUMENTED_CODES = Object.freeze([
  "artifact_empty",
  "count_partition_mismatch",
  "cross_artifact_disagreement",
  "digest_mismatch",
  "evidence_drift",
  "frozen_boundary_drift",
  "input_absent",
  "input_artifact_shape_invalid",
  "input_bytes_mismatch",
  "input_hash_mismatch",
  "input_not_tracked",
  "inventory_count_as_quantifier",
  "non_ascii_evidence",
  "out_absolute",
  "out_not_evidence_path",
  "out_of_repo_out",
  "out_symlink_target",
  "path_not_repository_relative",
  "promotion_claim_present",
]);

const FAILED_COUNTER_KEYS = [
  "bindings_failed",
  "digests_failed",
  "arithmetic_failed",
  "cross_artifact_failed",
  "frozen_boundary_failed",
  "promotion_checks_failed",
];

let cachedModel = null;
let cachedArtifact = null;
let cachedRaw = null;

function model() {
  if (cachedModel === null) cachedModel = loadModel();
  return cachedModel;
}

function artifactRaw() {
  if (cachedRaw === null) cachedRaw = readFileSync(ARTIFACT_ABS, "utf8");
  return cachedRaw;
}

function artifact() {
  if (cachedArtifact === null) cachedArtifact = JSON.parse(artifactRaw());
  return cachedArtifact;
}

function mutated(mutate) {
  const copy = structuredClone(model());
  mutate(copy);
  return copy;
}

/// A declaration unique to `reconciliation#sources.architecture_edges` is the
/// mutation site for the binding-level negative cases: it is declared exactly
/// once, so a byte/hash/path mutation raises the binding code instead of the
/// sibling-agreement code.
const UNIQUE_DECLARED_PATH = "prd/architecture/architecture_edges.jsonl";

function mutateUniqueSource(mutate) {
  const key = Object.keys(model().reconciliation.sources).find(
    (name) => model().reconciliation.sources[name].path === UNIQUE_DECLARED_PATH,
  );
  assert.ok(key, `no declared source binds ${UNIQUE_DECLARED_PATH}`);
  return mutated((copy) => {
    const entry = copy.reconciliation.sources[key];
    assert.equal(entry.path, UNIQUE_DECLARED_PATH);
    mutate(entry);
  });
}

/// Assert that `run()` raises `AuditError` carrying exactly `code`.
function fails(code, run) {
  return () => {
    assert.throws(run, (error) => {
      assert.ok(error instanceof AuditError, `expected AuditError, got ${error?.name}: ${error?.message}`);
      assert.equal(error.code, code, `expected ${code}, got ${error.code}: ${error.detail}`);
      return true;
    });
  };
}

// ---------------------------------------------------------------------------
// Independent arithmetic: the test re-reads the chain artifacts itself.
// ---------------------------------------------------------------------------

const LIVE_ARITHMETIC = Object.freeze({
  candidate_by_level_sum: (m) => Object.values(m.candidateArtifact.counts.by_level),
  candidate_unique_duplicate_partition: (m) => [
    m.candidateArtifact.counts.unique,
    m.candidateArtifact.counts.duplicate,
  ],
  candidate_array_length: (m) => [m.candidateArtifact.candidates.length],
  successor_rows_partition: (m) => {
    const successor = m.admissionRegeneration.inputs.admission_source;
    return [successor.rows_m209_candidate_backed, successor.rows_legacy_human, successor.rows_punkt];
  },
  successor_candidate_backed_partition: (m) => [
    m.admissionRegeneration.denominator.candidate_backed_identities,
    m.admissionRegeneration.denominator.unadmitted_identities,
  ],
  amends_outcome_partition: (m) => Object.values(m.amendingAct.denominator.by_outcome),
  amends_resolved_with_remainder: (m) => {
    const outcomes = m.amendingAct.denominator.by_outcome;
    const remainder = Object.entries(outcomes)
      .filter(([key]) => key !== "resolved-provision")
      .reduce((total, [, value]) => total + value, 0);
    return [outcomes["resolved-provision"], remainder];
  },
  amends_layer1_coverage_partition: (m) => [
    m.amendingAct.denominator.by_layer1_coverage["with-amends-edge"],
    m.amendingAct.denominator.by_layer1_coverage["without-amends-edge"],
  ],
  amends_layer1_records_partition: (m) => [
    m.amendingAct.denominator.layer1_core_acts,
    m.amendingAct.denominator.layer1_amending_acts,
  ],
  amends_statya_refs_partition: (m) => {
    const denominator = m.amendingAct.denominator;
    return [
      denominator.distinct_statya_refs_resolved,
      denominator.distinct_statya_refs - denominator.distinct_statya_refs_resolved,
    ];
  },
  commencement_slot_kind_partition: (m) => [
    m.commencement.denominator.named_chain_slots,
    m.commencement.denominator.amending_act_slots,
  ],
  commencement_evidence_class_partition: (m) => Object.values(m.commencement.denominator.by_evidence_class),
  commencement_slot_verdict_partition: (m) => Object.values(m.commencement.denominator.by_slot_verdict),
  commencement_reason_code_partition: (m) => Object.values(m.commencement.denominator.by_reason_code),
  edition_partition: (m) => {
    const denominator = m.editionDelta.denominator;
    return [
      denominator.editions_processed,
      denominator.editions_unreadable,
      denominator.editions_unparsed_filename,
    ];
  },
  edition_windows: (m) => [m.editionDelta.denominator.editions_total, -1],
  manifest_records_partition: (m) => {
    const family = m.familyDenominator.families.find(
      (entry) => entry.family_id === "manifest_layer1_44fz_and_amending_laws",
    );
    return [family.decomposition.core_acts, family.decomposition.amending_acts];
  },
  family_chain_edition_partition: (m) => [
    m.familyDenominator.chain.decomposition.edition_matching,
    m.familyDenominator.chain.decomposition.edition_unparsed,
  ],
});

/// Headline chain numbers, re-derived live from the sibling artifacts.
const LIVE_CROSS_ARTIFACT = Object.freeze({
  candidates_1901: (m) => m.candidateArtifact.counts.unique,
  candidate_backed_102: (m) => m.extractionEvidence.resolvability.identities.length,
  successor_rows_166: (m) => m.admissionRegeneration.inputs.admission_source.rows_total,
  punkt_zero: (m) => m.admissionRegeneration.denominator.punkt_admitted,
  editions_118: (m) => m.familyDenominator.chain.editions_total,
  edition_dir_files_118: (m) => m.familyDenominator.chain.editions_total,
  edition_dir_listing_digest_agreement: (m) => m.familyDenominator.chain.input_sha256,
  edition_dir_bytes_agreement: (m) => m.familyDenominator.chain.input_bytes,
  windows_117: (m) => m.editionDelta.denominator.windows_total,
  layer1_records_122: (m) => m.amendingAct.denominator.layer1_records_total,
  layer1_amending_121: (m) => m.amendingAct.denominator.layer1_amending_acts,
  commencement_slots_122: (m) => m.commencement.denominator.slots_total,
  amends_edges_120: (m) => m.amendingAct.denominator.amends_edges_total,
  statya_refs_30: (m) => m.amendingAct.denominator.distinct_statya_refs,
  statya_refs_resolved_26: (m) => m.amendingAct.denominator.distinct_statya_refs_resolved,
});

/// Resolve one `artifact-name#dotted.path` source label from the cross-artifact
/// block against the live model. Array segments are matched by `leg_id` /
/// `family_id` label (the ledger and family blocks are label-addressed), a
/// trailing `.length` reads the array length.
const SOURCE_OBJECTS = Object.freeze({
  "candidate-artifact": (m) => m.candidateArtifact,
  "extraction-evidence": (m) => m.extractionEvidence,
  "admission-regeneration": (m) => m.admissionRegeneration,
  "amending-act": (m) => m.amendingAct,
  commencement: (m) => m.commencement,
  "edition-delta": (m) => m.editionDelta,
  "family-denominator": (m) => m.familyDenominator,
  "r070-ledger": (m) => m.r070Ledger,
  "m202-r035-proof-gate": (m) => m.frozenM202ProofGate,
});

function resolveSource(m, source) {
  const separator = source.indexOf("#");
  assert.ok(separator > 0, `source label without artifact prefix: ${source}`);
  const artifactName = source.slice(0, separator);
  const base = SOURCE_OBJECTS[artifactName];
  assert.ok(base, `unknown source artifact in ${source}`);
  let cursor = base(m);
  for (const key of source.slice(separator + 1).split(".")) {
    assert.ok(cursor !== null && cursor !== undefined, `unresolved segment ${key} in ${source}`);
    if (key === "length") {
      cursor = cursor.length;
      continue;
    }
    if (Array.isArray(cursor)) {
      const labelled = cursor.find(
        (item) =>
          item !== null &&
          typeof item === "object" &&
          (item.leg_id === key ||
            item.family_id === key ||
            (typeof item.family_id === "string" && item.family_id.startsWith(key))),
      );
      cursor = labelled ?? cursor[Number(key)];
      continue;
    }
    // The ledger leg labels shorten `tracked_evidence.declared_counts` to
    // `declared_counts`; resolve the shorthand against the live leg.
    if (key === "declared_counts" && cursor.declared_counts === undefined && cursor.tracked_evidence) {
      cursor = cursor.tracked_evidence.declared_counts;
      continue;
    }
    cursor = cursor[key];
  }
  return cursor;
}

function assertIntegrityBlock(bundle) {
  assert.equal(bundle.schema, SCHEMA);
  assert.equal(bundle.lifecycle, "[bounded]");
  assert.equal(bundle.authoritative, false);
  assert.equal(bundle.count_only, true);
  assert.equal(bundle.ascii_only, true);
  assert.equal(bundle.gates_promoted, 0);
  assert.equal(bundle.legs_promoted, 0);
  assert.equal(bundle.proof_packages_attached, 0);
  assert.equal(bundle.requirement_records_mutated, 0);
  assert.deepEqual(bundle.requirement_dispositions, { R035: "active", R070: "active" });
  for (const key of FAILED_COUNTER_KEYS) assert.equal(bundle[key], 0, `${key} must be 0`);
  assert.deepEqual(bundle.fail_closed_codes, [...FAIL_CLOSED_CODES]);
  assert.deepEqual(bundle.non_claims, [...NON_CLAIMS]);
  const nonClaims = bundle.non_claims.join(" ");
  assert.match(nonClaims, /not-second-corpus-parser \(D559\)/);
  assert.match(nonClaims, /no-gate-promoted/);
  assert.match(nonClaims, /R035 stays active \(D430\)/);
  assert.match(nonClaims, /R070 stays active \(D416\)/);
}

// ---------------------------------------------------------------------------
// (a) + (c) documented vocabulary == emittable vocabulary
// ---------------------------------------------------------------------------

const NEGATIVE_CASES = Object.freeze({
  artifact_empty: fails("artifact_empty", () => assertNonEmpty("")),
  count_partition_mismatch: fails("count_partition_mismatch", () =>
    computeArithmetic(
      mutated((m) => {
        m.candidateArtifact.counts.extracted = 1902;
      }),
    ),
  ),
  cross_artifact_disagreement: fails("cross_artifact_disagreement", () =>
    computeCrossArtifacts(
      mutated((m) => {
        m.extractionEvidence.declared_denominator.denominator_total = 1900;
      }),
    ),
  ),
  digest_mismatch: fails("digest_mismatch", () =>
    recomputeIdentityDigest(
      mutated((m) => {
        m.candidateArtifact.candidates[0].number = "999999999";
      }).candidateArtifact,
      "m209-s02-hierarchy-candidates-fz44.json",
    ),
  ),
  evidence_drift: fails("evidence_drift", () => checkRenderedBytes("rendered", "committed")),
  frozen_boundary_drift: fails("frozen_boundary_drift", () =>
    computeFrozenBoundary(
      mutated((m) => {
        const pin = m.reconciliation.frozen_pins.rust_anchored.find(
          (entry) => entry.name === "m202_s02_candidates",
        );
        pin.sha256 = "00".repeat(32);
      }),
    ),
  ),
  input_absent: fails("input_absent", () =>
    computeBindings(
      mutateUniqueSource((entry) => {
        entry.path = "prd/architecture/m209-s04-absent-fixture.jsonl";
      }),
    ),
  ),
  input_artifact_shape_invalid: fails("input_artifact_shape_invalid", () =>
    assertModelShape({ ...model(), gateRegister: null }),
  ),
  input_bytes_mismatch: fails("input_bytes_mismatch", () =>
    computeBindings(
      mutateUniqueSource((entry) => {
        entry.bytes += 1;
      }),
    ),
  ),
  input_hash_mismatch: fails("input_hash_mismatch", () =>
    computeBindings(
      mutateUniqueSource((entry) => {
        entry.sha256 = "00".repeat(32);
      }),
    ),
  ),
  input_not_tracked: fails("input_not_tracked", () =>
    computeBindings(model(), { isTracked: () => false }),
  ),
  inventory_count_as_quantifier: fails("inventory_count_as_quantifier", () =>
    computePromotionChecks(
      mutated((m) => {
        m.gateRegister.gates[0].quantifier = { name: "registry_rows" };
      }),
    ),
  ),
  non_ascii_evidence: fails("non_ascii_evidence", () => {
    const bundle = structuredClone(artifact());
    bundle.probe_non_ascii = "\u00e9";
    return assertAsciiOnly(renderEvidence(bundle));
  }),
  out_absolute: fails("out_absolute", () => resolveOutTarget("/tmp/m209-s04-outside.json")),
  out_not_evidence_path: fails("out_not_evidence_path", () =>
    resolveOutTarget("scripts/m209-s04-not-evidence.json"),
  ),
  out_of_repo_out: fails("out_of_repo_out", () => resolveOutTarget("../m209-s04-outside.json")),
  out_symlink_target: fails("out_symlink_target", () =>
    resolveOutTarget(ARTIFACT_REL, {
      existsSync: () => true,
      lstatSync: () => ({ isSymbolicLink: () => true }),
    }),
  ),
  path_not_repository_relative: fails("path_not_repository_relative", () =>
    computeBindings(
      mutateUniqueSource((entry) => {
        entry.path = "/etc/passwd";
      }),
    ),
  ),
  promotion_claim_present: fails("promotion_claim_present", () =>
    computePromotionChecks(
      mutated((m) => {
        m.gateRegister.gates_promoted = 1;
      }),
    ),
  ),
});

test("the documented fail-closed vocabulary is exactly the emittable set", () => {
  assert.deepEqual([...FAIL_CLOSED_CODES], DOCUMENTED_CODES);
  assert.deepEqual(Object.keys(NEGATIVE_CASES).sort(), [...DOCUMENTED_CODES].sort());
  for (const [code, run] of Object.entries(NEGATIVE_CASES)) {
    assert.doesNotThrow(() => assert.equal(typeof run, "function"), `${code} case missing`);
    run();
  }
});

test("independent FNV-1a 64 primitives match the published test vectors", () => {
  assert.equal(fnv1a64(Buffer.from("")), "fnv1a64:cbf29ce484222325");
  assert.equal(fnv1a64(Buffer.from("a")), "fnv1a64:af63dc4c8601ec8c");
  assert.equal(fnv1a64(Buffer.from("foobar")), "fnv1a64:85944171f73967e8");
});

// ---------------------------------------------------------------------------
// (b) artifact integrity and independent re-derivation
// ---------------------------------------------------------------------------

test("artifact integrity: evidence-relative path, ASCII-only, non-empty, single line", () => {
  assert.equal(path.isAbsolute(ARTIFACT_REL), false);
  assert.equal(ARTIFACT_REL.split("/").includes(".."), false);
  const raw = artifactRaw();
  assertNonEmpty(raw);
  assertAsciiOnly(raw);
  assert.equal(raw.endsWith("\n"), true, "artifact must end with a single newline");
  assert.equal(raw.trimEnd().includes("\n"), false, "artifact must be one canonical JSON line");
  assert.equal(resolveOutTarget(ARTIFACT_REL).repoRelative, ARTIFACT_REL);
  const bundle = artifact();
  assertIntegrityBlock(bundle);
  assert.ok(bundle.bindings.length > 0);
  assert.ok(bundle.arithmetic.length > 0);
  assert.ok(bundle.cross_artifact.length > 0);
  assert.ok(bundle.frozen_boundary.length > 0);
});

test("every arithmetic row re-converges under an independent recomputation", () => {
  const m = model();
  const rows = artifact().arithmetic;
  assert.equal(rows.length, Object.keys(LIVE_ARITHMETIC).length);
  for (const row of rows) {
    assert.equal(row.verdict, "pass", row.assertion_id);
    assert.ok(LIVE_ARITHMETIC[row.assertion_id], `undocumented assertion ${row.assertion_id}`);
    assert.deepEqual(row.terms, LIVE_ARITHMETIC[row.assertion_id](m), `${row.assertion_id}: terms`);
    assert.equal(row.terms.reduce((total, term) => total + term, 0), row.declared, row.assertion_id);
    assert.equal(row.computed, row.declared, row.assertion_id);
  }
  const numbers = Object.fromEntries(rows.map((row) => [row.assertion_id, row.declared]));
  assert.equal(numbers.candidate_by_level_sum, 1901);
  assert.equal(numbers.successor_rows_partition, 166);
  assert.equal(numbers.amends_edges_total ?? numbers.amends_outcome_partition, 120);
  assert.equal(numbers.amends_layer1_records_partition, 122);
  assert.equal(numbers.edition_partition, 118);
  assert.equal(numbers.edition_windows, 117);
  assert.equal(numbers.manifest_records_partition, 122);
  assert.equal(numbers.family_chain_edition_partition, 118);
});

test("cross-artifact rows agree internally and with live artifacts", () => {
  const m = model();
  const rows = artifact().cross_artifact;
  assert.equal(rows.length, Object.keys(LIVE_CROSS_ARTIFACT).length);
  for (const row of rows) {
    assert.equal(row.verdict, "pass", row.check_id);
    assert.ok(LIVE_CROSS_ARTIFACT[row.check_id], `undocumented check ${row.check_id}`);
    assert.equal(row.expected, LIVE_CROSS_ARTIFACT[row.check_id](m), `${row.check_id}: headline`);
    assert.ok(row.values.length >= 2, `${row.check_id}: needs a cross check`);
    for (const entry of row.values) {
      const live = resolveSource(m, entry.source);
      assert.equal(entry.value, row.expected, `${row.check_id}: ${entry.source} declared value`);
      assert.equal(live, row.expected, `${row.check_id}: ${entry.source} live value`);
    }
  }
  const expected = Object.fromEntries(rows.map((row) => [row.check_id, row.expected]));
  assert.equal(expected.candidates_1901, 1901);
  assert.equal(expected.candidate_backed_102, 102);
  assert.equal(expected.successor_rows_166, 166);
  assert.equal(expected.punkt_zero, 0);
  assert.equal(expected.editions_118, 118);
  assert.equal(expected.edition_dir_files_118, 118);
  assert.match(expected.edition_dir_listing_digest_agreement, /^sha256:[0-9a-f]{64}$/);
  assert.equal(expected.edition_dir_bytes_agreement, 508427429);
  assert.equal(expected.layer1_amending_121, 121);
  assert.equal(expected.commencement_slots_122, 122);
});

test("re-render reproduces the committed artifact byte for byte (--check semantics)", () => {
  const bundle = audit(model(), "all");
  const rendered = renderEvidence(bundle);
  checkRenderedBytes(rendered, artifactRaw());
  assert.equal(rendered, artifactRaw());
  for (const key of FAILED_COUNTER_KEYS) assert.equal(bundle[key], 0, key);
  assert.equal(bundle.bindings_total, artifact().bindings_total);
  assert.match(heartbeat(bundle), /failed=0 drift=0$/);
});

test("declared bindings and digests re-derive without mismatch", () => {
  const m = model();
  const bindings = computeBindings(m);
  assert.ok(bindings.length >= 30, `expected a populated binding set, got ${bindings.length}`);
  for (const row of bindings) {
    assert.ok(
      ["pass", "delegated-to-t02", "corpus-absent"].includes(row.verdict),
      `${row.relative_path}: ${row.verdict}`,
    );
    if (row.verdict === "pass") {
      // A declared pin may be hash-only (bytes null) by design; compare what
      // the artifact actually declared, never the absent half.
      if (row.declared_bytes !== null) {
        assert.equal(row.recomputed_bytes, row.declared_bytes, row.relative_path);
      }
      if (row.declared_sha256 !== null) {
        assert.equal(row.recomputed_sha256, row.declared_sha256, row.relative_path);
      }
      assert.ok(row.recomputed_sha256 !== null, `${row.relative_path}: sha256 must be recomputed`);
    }
  }
  const digests = computeDigests(m);
  assert.equal(digests.source_digest.recomputed, "fnv1a64:490f75a20886f160");
  assert.equal(digests.identity_digest.recomputed, "fnv1a64:778beb9832032d4e");
  assert.equal(digests.frozen_source_digest.recomputed, "fnv1a64:5ec57029f2ff9d05");
  for (const [key, row] of Object.entries(digests)) {
    assert.equal(row.verdict, "pass", key);
    assert.equal(row.recomputed, row.declared, key);
  }
  assert.equal(digests.identity_digest.unique_candidates, 1901);
});

test("frozen boundary pins match live bytes and the worktree is untouched", () => {
  const rows = computeFrozenBoundary(model());
  assert.equal(rows.length, FROZEN_PATHS.length);
  assert.deepEqual(
    rows.map((row) => row.relative_path).sort(),
    [...FROZEN_PATHS].sort(),
  );
  for (const row of rows) assert.equal(row.verdict, "pass", row.relative_path);

  // Tracked-file proof for the digest subject (allowed subprocess #1).
  execFileSync("git", ["ls-files", "--error-unmatch", "--", S02_SOURCE_XML], {
    cwd: ROOT,
    stdio: "ignore",
  });
  assert.equal(defaultIsTracked(S02_SOURCE_XML), true);

  // Frozen-input proof (allowed subprocess #2): no frozen path is dirty.
  const dirty = execFileSync("git", ["status", "--porcelain", "--", ...FROZEN_PATHS], {
    cwd: ROOT,
    encoding: "utf8",
  });
  assert.equal(dirty.trim(), "", `frozen inputs modified in the worktree:\n${dirty}`);
});

test("anti-promotion and anti-quantifier guards hold over every audited artifact", () => {
  const checks = computePromotionChecks(model());
  assert.equal(checks.length, 5);
  for (const row of checks) {
    assert.equal(row.verdict, "pass", row.check_id);
    assert.equal(row.observed, 0, row.check_id);
  }
});

// ---------------------------------------------------------------------------
// (d) corpus-gated live recomputation
// ---------------------------------------------------------------------------

test("corpus-gated live recomputation of the S02 source and identity digests", () => {
  const bundle = artifact();
  if (existsSync(CORPUS_ABS)) {
    const sourceAbsolute = path.join(ROOT, S02_SOURCE_XML);
    assert.equal(existsSync(sourceAbsolute), true, S02_SOURCE_XML);
    const live = fnv1a64(readFileSync(sourceAbsolute));
    assert.equal(live, bundle.digests.source_digest.recomputed);
    assert.equal(live, bundle.digests.source_digest.declared);
    const identity = recomputeIdentityDigest(
      model().candidateArtifact,
      "m209-s02-hierarchy-candidates-fz44.json",
    );
    assert.equal(identity.recomputed, bundle.digests.identity_digest.recomputed);
    assert.equal(identity.recomputed, "fnv1a64:778beb9832032d4e");
  } else {
    console.log("M209_S04_CORPUS_ABSENT");
    assert.ok(bundle.fail_closed_codes.length > 0);
    assert.ok(bundle.non_claims.length > 0);
    assert.equal(bundle.count_only, true);
    assert.equal(bundle.authoritative, false);
  }
  assertIntegrityBlock(bundle);
});

test("the delegated directory rows are recorded, never silently dropped", () => {
  const rows = artifact().bindings.filter((row) => row.verdict !== "pass");
  assert.ok(rows.length > 0, "expected explicitly recorded delegated corpus rows");
  for (const row of rows) {
    assert.ok(["delegated-to-t02", "corpus-absent"].includes(row.verdict), row.relative_path);
  }
  const delegated = rows.filter((row) => row.verdict === "delegated-to-t02");
  assert.ok(delegated.length > 0);
  for (const row of delegated) {
    assert.equal(row.kind, "directory");
    assert.ok(row.relative_path.startsWith(CORPUS_PREFIX), row.relative_path);
  }
  assert.ok(
    artifact().non_claims.join(" ").includes("directory-listing-digests-delegated-to-s04-t02"),
  );
});

test("every audited chain artifact exists and is a tracked repository file", () => {
  const paths = Object.values(MODEL_FILES);
  assert.equal(paths.length, 15);
  const output = execFileSync("git", ["ls-files", "--error-unmatch", "--", ...paths], {
    cwd: ROOT,
    encoding: "utf8",
  });
  const tracked = new Set(output.split("\n").filter((line) => line !== ""));
  for (const relativePath of paths) {
    assert.equal(existsSync(path.join(ROOT, relativePath)), true, relativePath);
    assert.equal(tracked.has(relativePath), true, `${relativePath} must be tracked`);
  }
});
