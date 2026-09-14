import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const DOC = 'prd/architecture/m206-s03-adoption-state.md';
const S02_VERIFY = 'scripts/m206_s02_t02_verify.sh';
const EXPECTED_SCENARIOS = [
  'F08-self-positive',
  'F08-cited-act-negative',
  'F08-self-missing-conflict',
  'F12-antecedent-positive',
  'F12-antecedent-unproven',
  'F12-alias-declare-use',
  'F12-alias-shadow-conflict',
  'F12-alias-boundary',
  'F07-series-positive',
  'F07-three-unrelated',
  'F07-series-invalid',
  'F12-edition-relation',
];
const DEFERRED = new Set(['G03', 'G04', 'G05', 'G06', 'G07', 'G08', 'G09', 'G10', 'G11', 'G12', 'G13', 'G15', 'G16']);
const SELECTED = new Set(['G01', 'G02', 'G14']);
const FORBIDDEN_SELECTED = new Set(['G08', 'G09', 'G10', 'G11', 'G12', 'G13', 'G15']);
const REQUIRED_ANCHORS = [
  'prd/architecture/m205-s03-context-fsm.yaml',
  'prd/architecture/m206-s02-adoption-state.md',
  'doc/review/review-28-10-09-2026.md',
  'prd/temporal-legal-model.md',
  'prd/architecture/model-crystal.md',
  '.gsd/DECISIONS.md',
];
const REQUIRED_MARKERS = [
  ['scope', 'RC28-F07, RC28-F08, RC28-F12'],
  ['classification', 'design-only'],
  ['authoritative', 'false'],
  ['human_adoption', 'pending'],
  ['runtime_stop_active', 'true'],
  ['runtime_demo', 'not-proven'],
  ['requirement_status_effect', 'unchanged'],
  ['review_disposition_effect', 'unchanged'],
  ['selected_baseline', 'G01, G02, G14'],
  ['deferred_gates', 'G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16'],
  ['must_not_select', 'G08, G09, G10, G11, G12, G13, G15'],
];
const DIAGNOSTIC = (code, detail) => new Error(`${code}: ${detail}`);

function markerValues(text, key) {
  const re = new RegExp(`^\\*\\*${key}:\\s*([^*]+?)\\s*\\*\\*$`, 'gm');
  return [...text.matchAll(re)].map((match) => match[1].trim());
}

function requireSingletonMarker(text, key, expected) {
  const values = markerValues(text, key);
  assert.equal(values.length, 1, DIAGNOSTIC('MARKER_DUPLICATE_OR_MISSING', key));
  assert.equal(values[0], expected, DIAGNOSTIC('MARKER_VALUE_MISMATCH', `${key}=${values[0]}`));
}

function parseGateSet(text, key) {
  const values = markerValues(text, key);
  assert.equal(values.length, 1, DIAGNOSTIC('SAFETY_MARKER_DUPLICATE_OR_MISSING', key));
  const entries = values[0].split(',').map((entry) => entry.trim()).filter(Boolean);
  assert.equal(new Set(entries).size, entries.length, DIAGNOSTIC('SAFETY_MARKER_DUPLICATE', key));
  assert.ok(entries.every((entry) => /^G(?:0[1-9]|1[0-6])$/.test(entry)), DIAGNOSTIC('UNKNOWN_GATE', key));
  return new Set(entries);
}

function validate(text) {
  for (const [key, value] of REQUIRED_MARKERS) requireSingletonMarker(text, key, value);
  const selected = parseGateSet(text, 'selected_baseline');
  const deferred = parseGateSet(text, 'deferred_gates');
  const forbidden = parseGateSet(text, 'must_not_select');
  assert.deepEqual(selected, SELECTED, DIAGNOSTIC('SELECTED_GATE_SET_MISMATCH', [...selected].join(',')));
  assert.deepEqual(deferred, DEFERRED, DIAGNOSTIC('DEFERRED_GATE_SET_MISMATCH', [...deferred].join(',')));
  assert.deepEqual(forbidden, FORBIDDEN_SELECTED, DIAGNOSTIC('FORBIDDEN_GATE_SET_MISMATCH', [...forbidden].join(',')));
  assert.equal([...selected].filter((gate) => deferred.has(gate)).length, 0, DIAGNOSTIC('GATE_OVERLAP', 'selected/deferred'));
  assert.equal([...forbidden].filter((gate) => selected.has(gate)).length, 0, DIAGNOSTIC('FORBIDDEN_GATE_SELECTED', [...forbidden].join(',')));

  const scenarioRows = [...text.matchAll(/^\| `([^`]+)` \| .*? \| ([^|]+?) \|$/gm)].map((match) => ({ id: match[1], status: match[2].trim() }));
  const ids = scenarioRows.map(({ id }) => id);
  assert.equal(new Set(ids).size, ids.length, DIAGNOSTIC('SCENARIO_DUPLICATE', ids.join(',')));
  assert.equal(scenarioRows.length, EXPECTED_SCENARIOS.length, DIAGNOSTIC('SCENARIO_COUNT', scenarioRows.length));
  assert.deepEqual(new Set(ids), new Set(EXPECTED_SCENARIOS), DIAGNOSTIC('SCENARIO_SET_MISMATCH', ids.join(',')));
  assert.ok(scenarioRows.every(({ status }) => status === 'not executed'), DIAGNOSTIC('SCENARIO_EXECUTED', ids.join(',')));

  for (const anchor of REQUIRED_ANCHORS) assert.ok(text.includes(anchor), DIAGNOSTIC('SOURCE_ANCHOR_MISSING', anchor));
  assert.match(text, /owner Reject provenance[\s\S]*?04fd05a2-338f-45af-a1cc-13501717dc53[\s\S]*?not a Reject of RC28-F07, RC28-F08, or RC28-F12/, DIAGNOSTIC('REJECT_PROVENANCE_LOST', 'F06/F10 only'));
  assert.match(text, /Resume requires a separate source-bound owner admission[\s\S]*?sanctioned runtime replan/, DIAGNOSTIC('RESUME_GUARD_MISSING', 'admission/replan'));
  assert.match(text, /M204 and M205 prerequisites/, DIAGNOSTIC('PREREQUISITE_GUARD_MISSING', 'M204/M205'));
  assert.match(text, /prd\/architecture\/m206-s02-adoption-state\.md/, DIAGNOSTIC('UPSTREAM_SOURCE_ANCHOR_MISSING', 'M206/S02'));
  assert.match(text, /do not modify Rust, tests, dependencies, ADRs, M205 pins, requirements, or\s+findings/, DIAGNOSTIC('SAFETY_MARKER_MISSING', 'prohibited changes'));
  return { scenarios: ids.length, runtimeDemo: 'not-proven' };
}

function hash(text) { return createHash('sha256').update(text).digest('hex'); }
function expectRejected(label, mutate, code) {
  const original = readFileSync(DOC, 'utf8');
  assert.throws(() => validate(mutate(original)), (error) => {
    assert.match(error.message, new RegExp(`^${code}:`), `${label}: ${error.message}`);
    return true;
  }, label);
}

const original = readFileSync(DOC, 'utf8');

test('original and tolerant whitespace/prose copies pass without exact prose coupling', () => {
  const before = hash(original);
  const result = validate(original);
  const tolerant = original
    .replace(/\*\*scope: RC28-F07, RC28-F08, RC28-F12\*\*/, '**scope:   RC28-F07, RC28-F08, RC28-F12**')
    .replace('not runtime PASS, admission, or adoption evidence', 'not runtime PASS, admission, or adoption evidence; explanatory prose may vary');
  assert.deepEqual(validate(tolerant), result);
  assert.equal(hash(readFileSync(DOC, 'utf8')), before, 'input document was mutated');
  assert.equal(result.scenarios, 12);
  assert.equal(result.runtimeDemo, 'not-proven');
});

test('negative mutation: runtime stop cannot be disabled', () => {
  expectRejected('stop false', (text) => text.replace('**runtime_stop_active: true**', '**runtime_stop_active: false**'), 'MARKER_VALUE_MISMATCH');
});
test('negative mutation: adoption cannot be accepted', () => {
  expectRejected('adoption accepted', (text) => text.replace('**human_adoption: pending**', '**human_adoption: accepted**'), 'MARKER_VALUE_MISMATCH');
});
test('negative mutation: runtime demo cannot be proven', () => {
  expectRejected('demo proven', (text) => text.replace('**runtime_demo: not-proven**', '**runtime_demo: proven**'), 'MARKER_VALUE_MISMATCH');
});
test('negative mutation: missing scenario is rejected', () => {
  expectRejected('missing scenario', (text) => text.replace('`F08-self-positive`', '`F08-self-removed`'), 'SCENARIO_SET_MISMATCH');
});
test('negative mutation: duplicate scenario is rejected', () => {
  expectRejected('duplicate scenario', (text) => text.replace(/(^\| `F08-self-positive` \|[^\n]*$)/m, '$1\n| `F08-self-positive` | duplicate | not executed |'), 'SCENARIO_DUPLICATE');
});
test('negative mutation: executed scenario is rejected', () => {
  expectRejected('scenario executed', (text) => text.replace(/(\| `F08-self-positive` \|[^\n]*\| )not executed( \|)/, '$1executed$2'), 'SCENARIO_EXECUTED');
});
test('negative mutation: deferred gate loss is rejected', () => {
  expectRejected('missing deferred gate', (text) => text.replace('G15, G16', 'G15'), 'MARKER_VALUE_MISMATCH');
});
test('negative mutation: forbidden gate selection is rejected', () => {
  expectRejected('forbidden gate selected', (text) => text.replace('**selected_baseline: G01, G02, G14**', '**selected_baseline: G01, G02, G08, G14**'), 'MARKER_VALUE_MISMATCH');
});
test('negative mutation: provenance cannot be transferred to F07/F08/F12', () => {
  expectRejected('reject transferred', (text) => text.replace('not a Reject of RC28-F07, RC28-F08, or RC28-F12', 'is a Reject of RC28-F07, RC28-F08, or RC28-F12'), 'REJECT_PROVENANCE_LOST');
});
test('negative mutation: source anchor is mandatory', () => {
  expectRejected('source anchor missing', (text) => text.replace('doc/review/review-28-10-09-2026.md', 'doc/review/missing-review.md'), 'SOURCE_ANCHOR_MISSING');
});
test('negative mutation: safety marker is mandatory', () => {
  expectRejected('safety marker missing', (text) => text.replace(/do not modify Rust, tests, dependencies, ADRs, M205 pins, requirements, or\n  findings/, 'do not modify Rust, tests, dependencies, ADRs, M205 pins, requirements'), 'SAFETY_MARKER_MISSING');
});
test('negative mutation: duplicate safety marker is rejected', () => {
  expectRejected('duplicate safety marker', (text) => text.replace('**runtime_stop_active: true**', '**runtime_stop_active: true**\n**runtime_stop_active: true**'), 'MARKER_DUPLICATE_OR_MISSING');
});

test('S02 verifier remains passing and this test does not mutate inputs', () => {
  const before = hash(original);
  const result = spawnSync('bash', [S02_VERIFY], { encoding: 'utf8' });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stdout, /M206_S02_T02_VERIFY_OK/);
  assert.equal(hash(readFileSync(DOC, 'utf8')), before);
});
