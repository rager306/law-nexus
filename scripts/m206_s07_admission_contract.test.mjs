import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const root = fileURLToPath(new URL("..", import.meta.url));
const admissionPath = "prd/architecture/m206-s07-runtime-admission.md";
const admission = readFileSync(`${root}/${admissionPath}`, "utf8");

function source(relativePath) {
  return readFileSync(`${root}/${relativePath}`, "utf8");
}

function requireLiteral(text, literal, context) {
  assert.ok(text.includes(literal), `${context} is missing required literal: ${literal}`);
}

test("M206 S07 admission is source-bound to S05 and D388", () => {
  requireLiteral(admission, "prd/architecture/m206-s05-runtime-admission.md", "S05 admission source");
  requireLiteral(admission, "S05 already records the owner's Accept", "S05 owner Accept citation");
  requireLiteral(admission, "RC28-F06..F12", "admitted finding scope");
  requireLiteral(admission, "**selected_d388_gates:** G01, G02, G14", "D388 selected gates");
  requireLiteral(admission, "**deferred_d388_gates:**", "D388 deferred gates");
  requireLiteral(admission, "runtime_stop:** lifted for M206/S07", "runtime stop boundary");
});

test("M206 S07 preserves historical no-start provenance", () => {
  for (const state of ["s01", "s02", "s03", "s04"]) {
    const path = `prd/architecture/m206-${state}-adoption-state.md`;
    const content = source(path);
    requireLiteral(content, "NOT_RUN", `${path} historical status`);
    requireLiteral(admission, `S01, S02, S03, and S04 remain **NOT_RUN**`, "S01-S04 overlay status");
  }
});

test("M206 S07 admission names the executable contract and fail-closed boundary", () => {
  requireLiteral(admission, "scripts/m206_s07_admission_contract.test.mjs", "executable admission check");
  requireLiteral(admission, "scripts/m206_s06_reproduction.test.mjs", "reproduction oracle");
  requireLiteral(admission, "M206_EXPECT=green node --test scripts/m206_s06_reproduction.test.mjs", "green reproduction command");
  requireLiteral(admission, "actually executed `--exact` case", "exact execution evidence");
  requireLiteral(admission, "exit status consistent with that result", "result/status agreement");
  requireLiteral(admission, "spawn errors, signals, compile failures, skipped cases, and missing output are\nnot evidence", "fail-closed execution evidence");
  requireLiteral(admission, "missing, conflicting, or unavailable evidence remains fail-closed", "failure boundary");
  for (const finding of ["RC28-F06", "RC28-F07", "RC28-F08", "RC28-F09", "RC28-F10", "RC28-F11", "RC28-F12"]) {
    requireLiteral(admission, finding, `${finding} scope`);
  }
});
