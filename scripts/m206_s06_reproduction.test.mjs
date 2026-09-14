import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const root = fileURLToPath(new URL("..", import.meta.url));
const expected = process.env.M206_EXPECT;
assert.ok(expected === "red" || expected === "green", "M206_EXPECT must be explicitly red or green");

const suites = [
  {
    package: "ln-decode",
    test: "m206_grammar_context_regressions",
    cases: [
      ["rc28_f06_sibling_heading_closes_previous_container", "RC28-F06", true],
      ["rc28_f07_three_unrelated_blocks_have_no_parent_edges", "RC28-F07", true],
      ["rc28_f08_this_ref_survives_nonempty_worklist_and_empty_or_cited_negatives", "RC28-F08", true],
      ["rc28_f09_independent_sentences_and_incomplete_tail_keep_local_origins", "RC28-F09", true],
      ["rc28_f10_original_spans_accept_en_and_em_dash_range_variants", "RC28-F10", true],
    ],
  },
  {
    package: "ln-temporal",
    test: "m206_scope_regressions",
    cases: [
      ["rc28_f11_temporal_do_does_not_match_dolzhen", "RC28-F11", true],
      ["rc28_f11_actor_is_source_backed_and_not_the_whole_block", "RC28-F11", true],
      ["rc28_f11_independent_sentences_keep_independent_cues", "RC28-F11", false],
      ["rc28_f12_self_antecedent_alias_and_edition_are_not_one_construction", "RC28-F12", true],
      ["rc28_f12_utf8_origins_are_char_boundary_safe", "RC28-F12", false],
    ],
  },
];

function cargo(args) {
  return spawnSync("cargo", args, {
    cwd: root,
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function diagnostic(result) {
  return `${result.stdout ?? ""}\n${result.stderr ?? ""}\nspawn_error=${result.error?.message ?? "none"}\nstatus=${result.status}`;
}

for (const suite of suites) {
  test(`M206 compile ${suite.package}/${suite.test}`, () => {
    const result = cargo([
      "test",
      "-p",
      suite.package,
      "--offline",
      "--test",
      suite.test,
      "--no-run",
    ]);
    assert.equal(result.status, 0, diagnostic(result));
  });
}

for (const suite of suites) {
  for (const [caseName, identifier, reproduces] of suite.cases) {
    test(`M206 ${identifier} ${caseName}`, () => {
      const result = cargo([
        "test",
        "-p",
        suite.package,
        "--offline",
        "--test",
        suite.test,
        caseName,
        "--",
        "--exact",
        "--nocapture",
      ]);
      const output = diagnostic(result);
      const executed = output.match(/running (\d+) test/);
      assert.ok(executed, `${identifier} did not report a Rust test count\n${output}`);
      assert.equal(executed[1], "1", `${identifier} did not execute exactly one test; --exact no-test exits are not evidence\n${output}`);
      if (expected === "red" && reproduces) {
        assert.notEqual(result.status, 0, `${identifier} unexpectedly passed; red oracle is no longer reproducing the finding\n${output}`);
        assert.match(output, new RegExp(identifier.replace("-", "\\-")), `${identifier} failed without its case identifier\n${output}`);
        assert.doesNotMatch(output, /could not compile|unrecognized option|no tests? to run|panicked at.*unwrap/i, `${identifier} was not an assertion failure\n${output}`);
      } else {
        assert.equal(result.status, 0, `${identifier} is an already-passing baseline or green closeout contract\n${output}`);
      }
    });
  }
}
