import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { resolve, relative, isAbsolute } from 'node:path';
import { spawnSync } from 'node:child_process';

const DOC = 'prd/architecture/m206-s04-adoption-state.md';
const S03_DOC = 'prd/architecture/m206-s03-adoption-state.md';
const S03_VERIFY = 'scripts/m206_s03_adoption_contract.test.mjs';
const S02_DOC = 'prd/architecture/m206-s02-adoption-state.md';
const S02_VERIFY = 'scripts/m206_s02_t02_verify.sh';

// Deliberately independent of the document: the record cannot define its own coverage.
const EXPECTED_SCENARIOS = [
  'F10-CUE-TOKEN', 'F10-CUE-POSITIVE', 'F10-ACTOR-ANCHORED',
  'F10-ACTOR-NEGATIVE', 'F11-ENDPOINTS', 'F11-MEMBERSHIP',
  'F11-MISSING-MEMBER', 'F11-RANGE-INVALID', 'F12-VERTICAL-POSITIVE',
  'F12-VERTICAL-NEGATIVE', 'F12-CONTEXT-SEPARATION', 'F12-NO-IR',
];
const SELECTED = new Set(['G01', 'G02', 'G14']);
const DEFERRED = new Set(['G03', 'G04', 'G05', 'G06', 'G07', 'G08', 'G09', 'G10', 'G11', 'G12', 'G13', 'G15', 'G16']);
const FORBIDDEN_SELECTED = new Set(['G08', 'G09', 'G10', 'G11', 'G12', 'G13', 'G15']);
const REQUIRED_ANCHORS = [
  'doc/review/review-28-10-09-2026.md',
  'prd/architecture/m206-s02-adoption-state.md',
  'prd/architecture/m206-s03-adoption-state.md',
  'prd/architecture/npa-document-context.yaml',
  'prd/architecture/current-document-requisites.yaml',
  'prd/architecture/npa-capture-arbitration.yaml',
  'prd/architecture/reference-binding-contract.yaml',
  'prd/architecture/m205-s03-context-fsm.yaml',
  'prd/temporal-legal-model.md',
  'prd/architecture/model-crystal.md',
];
const MARKERS = [
  ['scope', 'RC28-F10, RC28-F11, RC28-F12'],
  ['classification', 'design-only'], ['authoritative', 'false'],
  ['lifecycle', 'proposed'], ['human_adoption', 'pending'],
  ['runtime_stop_active', 'true'], ['runtime_demo', 'not-proven'],
  ['requirement_status_effect', 'unchanged'],
  ['review_disposition_effect', 'unchanged'],
  ['selected_baseline', 'G01, G02, G14'],
  ['deferred_gates', 'G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16'],
  ['must_not_select', 'G08, G09, G10, G11, G12, G13, G15'],
];
const diagnostic = (code, detail) => new Error(`${code}: ${detail}`);

function markerValues(text, key) {
  const re = new RegExp(`^\\*\\*${key}:\\s*([^*]+?)\\s*\\*\\*$`, 'gm');
  return [...text.matchAll(re)].map((match) => match[1].trim());
}

function singleton(text, key, expected) {
  const values = markerValues(text, key);
  assert.equal(values.length, 1, diagnostic('MARKER_DUPLICATE_OR_MISSING', key));
  assert.equal(values[0], expected, diagnostic('MARKER_VALUE_MISMATCH', `${key}=${values[0]}`));
}

function gateSet(text, key) {
  const values = markerValues(text, key);
  assert.equal(values.length, 1, diagnostic('SAFETY_MARKER_DUPLICATE_OR_MISSING', key));
  const entries = values[0].split(',').map((x) => x.trim()).filter(Boolean);
  assert.equal(new Set(entries).size, entries.length, diagnostic('SAFETY_MARKER_DUPLICATE', key));
  assert.ok(entries.every((x) => /^G(?:0[1-9]|1[0-6])$/.test(x)), diagnostic('UNKNOWN_GATE', key));
  return new Set(entries);
}

function safeAnchor(anchor) {
  assert.ok(anchor && !isAbsolute(anchor), diagnostic('SOURCE_ANCHOR_UNSAFE', anchor));
  assert.ok(!anchor.split('/').includes('..'), diagnostic('SOURCE_ANCHOR_TRAVERSAL', anchor));
  assert.ok(!anchor.startsWith('.gsd/'), diagnostic('SOURCE_ANCHOR_IGNORED', anchor));
  const root = resolve('.');
  const target = resolve(root, anchor);
  assert.equal(relative(root, target), anchor, diagnostic('SOURCE_ANCHOR_OUTSIDE_ROOT', anchor));
  assert.ok(existsSync(target), diagnostic('SOURCE_ANCHOR_MISSING', anchor));
}

function validate(text) {
  for (const [key, expected] of MARKERS) singleton(text, key, expected);
  const selected = gateSet(text, 'selected_baseline');
  const deferred = gateSet(text, 'deferred_gates');
  const forbidden = gateSet(text, 'must_not_select');
  assert.deepEqual(selected, SELECTED, diagnostic('SELECTED_GATE_SET_MISMATCH', [...selected].join(',')));
  assert.deepEqual(deferred, DEFERRED, diagnostic('DEFERRED_GATE_SET_MISMATCH', [...deferred].join(',')));
  assert.deepEqual(forbidden, FORBIDDEN_SELECTED, diagnostic('FORBIDDEN_GATE_SET_MISMATCH', [...forbidden].join(',')));
  assert.equal([...selected].some((x) => deferred.has(x)), false, diagnostic('GATE_OVERLAP', 'selected/deferred'));
  assert.equal([...selected].some((x) => forbidden.has(x)), false, diagnostic('FORBIDDEN_GATE_SELECTED', [...forbidden].join(',')));

  const rows = [...text.matchAll(/^\| `([^`]+)` \| ([^\n]+?) \|$/gm)].map((m) => {
    const cells = m[0].slice(1, -1).split('|').map((cell) => cell.trim());
    return { id: m[1], cells, line: m[0] };
  });
  const ids = rows.map((row) => row.id);
  assert.equal(new Set(ids).size, ids.length, diagnostic('SCENARIO_DUPLICATE', ids.join(',')));
  assert.deepEqual(new Set(ids), new Set(EXPECTED_SCENARIOS), diagnostic('SCENARIO_SET_MISMATCH', ids.join(',')));
  assert.equal(rows.length, EXPECTED_SCENARIOS.length, diagnostic('SCENARIO_COUNT', rows.length));
  for (const row of rows) {
    assert.equal(row.cells.length, 7, diagnostic('SCENARIO_COLUMNS', row.id));
    assert.ok(row.cells.slice(1).every((cell) => cell.length > 0), diagnostic('SCENARIO_FIELD_MISSING', row.id));
    assert.equal(row.cells[6], 'not executed', diagnostic('SCENARIO_EXECUTED', row.id));
    const anchors = [...row.line.matchAll(/`([^`]+\.(?:md|yaml))`/g)].map((m) => m[1]);
    assert.ok(anchors.length > 0, diagnostic('SCENARIO_ANCHOR_MISSING', row.id));
    anchors.forEach(safeAnchor);
  }

  for (const anchor of REQUIRED_ANCHORS) assert.ok(text.includes(anchor), diagnostic('SOURCE_ANCHOR_MISSING', anchor));
  assert.match(text, /The owner Reject interaction[\s\S]*?04fd05a2-338f-45af-a1cc-13501717dc53[\s\S]*?F06\/F10\s+provenance[\s\S]*?not a Reject of F11 or F12/, diagnostic('REJECT_PROVENANCE_LOST', 'F06/F10 only'));
  assert.doesNotMatch(text, /\bis a Reject of F11 or F12\b/, diagnostic('REJECT_TRANSFERRED', 'F11/F12'));
  assert.match(text, /Resume requires a separate source-bound owner admission[\s\S]*?sanctioned runtime replan/, diagnostic('RESUME_GUARD_MISSING', 'admission/replan'));
  assert.match(text, /M204 and M205 prerequisites/, diagnostic('PREREQUISITE_GUARD_MISSING', 'M204/M205'));
  assert.match(text, /endpoints only[\s\S]*?full StructuralMembership/, diagnostic('ENDPOINT_MEMBERSHIP_COLLAPSED', 'endpoints/membership'));
  assert.match(text, /candidate is not NormRule[\s\S]*?status, applicability, force, or legal IR/i, diagnostic('IR_CEILING_MISSING', 'candidate/IR'));
  return { scenarios: ids.length, runtimeDemo: 'not-proven' };
}

function hash(path) { return createHash('sha256').update(readFileSync(path)).digest('hex'); }
function expectRejected(label, mutate, code) {
  const original = readFileSync(DOC, 'utf8');
  assert.throws(() => validate(mutate(original)), (error) => {
    assert.match(error.message, new RegExp(`^${code}:`), `${label}: ${error.message}`);
    return true;
  }, label);
}

const original = readFileSync(DOC, 'utf8');

test('actual record passes and harmless prose mutation remains accepted', () => {
  const before = hash(DOC);
  const result = validate(original);
  const tolerant = original.replace('future obligations only', 'future obligations only; explanatory prose may vary');
  assert.deepEqual(validate(tolerant), result);
  assert.equal(hash(DOC), before, 'input document was mutated');
  assert.equal(result.scenarios, 12);
});

test('negative mutations reject promotion and marker drift', () => {
  expectRejected('stop false', (x) => x.replace('**runtime_stop_active: true**', '**runtime_stop_active: false**'), 'MARKER_VALUE_MISMATCH');
  expectRejected('adoption accepted', (x) => x.replace('**human_adoption: pending**', '**human_adoption: accepted**'), 'MARKER_VALUE_MISMATCH');
  expectRejected('runtime proven', (x) => x.replace('**runtime_demo: not-proven**', '**runtime_demo: proven**'), 'MARKER_VALUE_MISMATCH');
  expectRejected('authoritative true', (x) => x.replace('**authoritative: false**', '**authoritative: true**'), 'MARKER_VALUE_MISMATCH');
  expectRejected('requirement effect changed', (x) => x.replace('**requirement_status_effect: unchanged**', '**requirement_status_effect: changed**'), 'MARKER_VALUE_MISMATCH');
  expectRejected('review effect changed', (x) => x.replace('**review_disposition_effect: unchanged**', '**review_disposition_effect: changed**'), 'MARKER_VALUE_MISMATCH');
});

test('negative mutations reject marker, scenario, path, and gate corruption', () => {
  expectRejected('duplicate marker', (x) => x.replace('**runtime_stop_active: true**', '**runtime_stop_active: true**\n**runtime_stop_active: true**'), 'MARKER_DUPLICATE_OR_MISSING');
  expectRejected('missing scenario', (x) => x.replace('`F10-CUE-TOKEN`', '`F10-CUE-REMOVED`'), 'SCENARIO_SET_MISMATCH');
  expectRejected('duplicate scenario', (x) => x.replace(/(^\| `F10-CUE-TOKEN` \|[^\n]*$)/m, '$1\n| `F10-CUE-TOKEN` | duplicate | input | outcome | anchor.md | proof | not executed |'), 'SCENARIO_DUPLICATE');
  expectRejected('extra scenario', (x) => x.replace('\n## Resume conditions', '\n| `F99-EXTRA` | extra | input | outcome | doc/review/review-28-10-09-2026.md | proof | not executed |\n\n## Resume conditions'), 'SCENARIO_SET_MISMATCH');
  expectRejected('executed scenario', (x) => x.replace('| not executed |', '| executed |'), 'SCENARIO_EXECUTED');
  expectRejected('missing anchor', (x) => x.replaceAll('`doc/review/review-28-10-09-2026.md`', '`doc/review/missing.md`'), 'SOURCE_ANCHOR_MISSING');
  expectRejected('absolute anchor', (x) => x.replaceAll('`doc/review/review-28-10-09-2026.md`', '`/tmp/review.md`'), 'SOURCE_ANCHOR_UNSAFE');
  expectRejected('traversal anchor', (x) => x.replaceAll('`doc/review/review-28-10-09-2026.md`', '`../review.md`'), 'SOURCE_ANCHOR_TRAVERSAL');
  expectRejected('deferred gate removed', (x) => x.replace('G15, G16', 'G15'), 'MARKER_VALUE_MISMATCH');
  expectRejected('forbidden selected', (x) => x.replace('**selected_baseline: G01, G02, G14**', '**selected_baseline: G01, G02, G08, G14**'), 'MARKER_VALUE_MISMATCH');
  expectRejected('forbidden gate removed', (x) => x.replace('G08, G09, G10, G11, G12, G13, G15', 'G08, G09, G10, G11, G12, G13'), 'MARKER_VALUE_MISMATCH');
});

test('negative mutations preserve provenance and authority ceilings', () => {
  expectRejected('reject transferred', (x) => x.replace('not a Reject of F11 or F12', 'is a Reject of F11 or F12'), 'REJECT_PROVENANCE_LOST');
  expectRejected('no IR removed', (x) => x.replace(/candidate is not NormRule and does not create status, applicability, force, or legal IR/i, 'candidate may create status'), 'IR_CEILING_MISSING');
  expectRejected('endpoints collapsed', (x) => x.replace('endpoints only; do not represent endpoints as full StructuralMembership', 'endpoints are full StructuralMembership'), 'ENDPOINT_MEMBERSHIP_COLLAPSED');
});

test('inherited S02 and S03 verifiers pass and all consumed inputs remain byte-identical', () => {
  const paths = [S02_DOC, S02_VERIFY, S03_DOC, S03_VERIFY];
  const before = new Map(paths.map((path) => [path, hash(path)]));
  const inheritedEnv = { ...process.env };
  delete inheritedEnv.NODE_TEST_CONTEXT;
  const s03 = spawnSync(process.execPath, [S03_VERIFY], { encoding: 'utf8', env: inheritedEnv });
  assert.equal(s03.status, 0, `${s03.stdout}\n${s03.stderr}`);
  // S03 is itself a node:test suite. When nested under node --test, Node
  // switches its child reporter to the binary event stream; exit=0 is the
  // stable inherited success signal rather than a TAP-format assertion.
  console.log('M206_S03_CONTRACT_OK inherited_exit=0');
  const s02 = spawnSync('bash', [S02_VERIFY], { encoding: 'utf8', env: inheritedEnv });
  assert.equal(s02.status, 0, `${s02.stdout}\n${s02.stderr}`);
  assert.match(s02.stdout, /M206_S02_T02_VERIFY_OK/);
  for (const path of paths) assert.equal(hash(path), before.get(path), `upstream input mutated: ${path}`);
});

console.log(`M206_S04_CONTRACT_OK future_scenarios=${EXPECTED_SCENARIOS.length} runtime_demo=not-proven`);
