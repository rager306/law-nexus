# M052 S01 SHACL Negative Validation Proof

## Status

In progress for `M052-idogd6 / S01`.

This artifact resolves the M051 gap where `git-lex validate` passed positive fixtures but negative rejection was not proven. The goal is to separate source-backed validator semantics, shape-derived invalid fixture design, isolated runtime evidence, and ACP proof-gate classification.

## T01: GitNexus and source trace of validation semantics

### Scope

T01 traces source behavior only. It does not run new `git-lex` runtime validation commands and does not create or mutate `/root/law-nexus/.lex`.

Safety check before T01 source work:

```text
main_lex_absent=0  # shell test exit code for `test ! -e .lex`; 0 means absent
```

GitNexus index note:

- Initial GitNexus query for `git-lex-reference` warned that FTS indexes were degraded.
- The index was refreshed from `/root/vendor-source/git-lex` with:

```text
gitnexus analyze --force --name git-lex-reference
```

- Re-query after refresh returned validation/source flows without the degraded-index warning.

### Source anchors

| Surface | Source anchor | Finding |
|---|---|---|
| Validate command dispatch | `/root/vendor-source/git-lex/src/main.rs:2450-2470` | `Commands::Validate` calls `cmd_validate()` and exits with `exit(1)` only when it returns `false`. |
| Validate entry and repo/kit handling | `/root/vendor-source/git-lex/src/main.rs:1215-1234` | Not being in a git repo is fatal (`exit(1)`). Missing kit is not fatal: prints `No kit configured — nothing to validate.` and returns `true`. |
| Shape source loading | `/root/vendor-source/git-lex/src/main.rs:1235-1275` | Shapes are collected from `.lex/ontology/{short}/{short}-shapes.ttl` and `_ontology/*/*-shapes.ttl`. No shapes means skip validation and return `true`. |
| Shape parse/load/schema/compile failures | `/root/vendor-source/git-lex/src/main.rs:1291-1320` | Failed SHACL shapes parse, RDF load, schema parse, or compile prints diagnostics and returns `true`. These are fail-open setup errors. |
| File discovery | `/root/vendor-source/git-lex/src/main.rs:1277-1289` | Validator recursively walks non-dot directories and checks `.md` files. Dot directories such as `.lex` and `.git` are skipped. |
| Frontmatter conversion | `/root/vendor-source/git-lex/src/extraction.rs:159-274` | `frontmatter_to_turtle()` returns `None` for missing frontmatter, malformed YAML, no matching `kit.class.property` key, missing inferred doc type, or empty kit properties. `cmd_validate()` silently skips these files. |
| Data Turtle parse/load failures | `/root/vendor-source/git-lex/src/main.rs:1333-1348` | Per-file generated Turtle parse or RDF load errors are logged and skipped with `continue`; they do not increment `total_violations`. |
| SHACL processor errors | `/root/vendor-source/git-lex/src/main.rs:1352-1369` | `ShaclProcessor::validate()` errors are logged but do not set `total_violations`. If no other violation exists, final result can still be pass. |
| Violation handling | `/root/vendor-source/git-lex/src/main.rs:1354-1364` | Only a validation report with `!report.conforms()` increments `total_violations`, records failed file, and makes `cmd_validate()` return `false`. |
| Final outcome | `/root/vendor-source/git-lex/src/main.rs:1373-1399` | `total_violations == 0` returns `true`; otherwise returns `false`. Therefore non-zero CLI exit requires actual SHACL violations, not setup/data parse errors. |
| Shape generation | `/root/vendor-source/git-lex/src/shacl.rs:108-315` | Shapes are generated from OWL classes, properties, enum datatypes, and `owl:Restriction` cardinalities. Generated constraints include `sh:targetClass`, `sh:path`, `sh:nodeKind sh:IRI`, `sh:in`, `sh:datatype`, and `sh:minCount 1`. |
| Runtime shape parser | `/root/vendor-source/git-lex/src/ontology.rs:78-240` | Runtime shape parser records property constraints for prefix, namespace, target class, path, `nodeKind`, datatype, required/minCount, and comments. These shape files are the runtime source for class/property metadata. |

### GitNexus trace summary

GitNexus source/context queries confirmed the validation flow:

```text
cmd_validate -> frontmatter_to_turtle
cmd_validate -> resolve_kit_spec
cmd_validate -> get_kit
hook_pre_commit -> cmd_validate
main -> cmd_validate for Commands::Validate
```

Relevant GitNexus processes after index refresh:

```text
proc_7_cmd_validate: Cmd_validate -> ParsedShape
proc_8_cmd_validate: Cmd_validate -> ShapeProp
proc_20_frontmatter_to_turtl: Frontmatter_to_turtle -> ParsedShape
proc_21_frontmatter_to_turtl: Frontmatter_to_turtle -> ShapeProp
proc_50_hook_pre_commit: Hook_pre_commit -> Resolve_kit_spec
```

### Why the M051 malformed fixture did not prove negative validation

The M051 negative attempt used malformed YAML frontmatter. Source trace explains why that was a weak fixture:

```rust
let yaml: HashMap<String, serde_yaml::Value> = serde_yaml::from_str(yaml_str).ok()?;
```

Because `frontmatter_to_turtle()` returns `Option<String>`, malformed YAML returns `None`. `cmd_validate()` then does:

```rust
let ttl = match frontmatter_to_turtle(filepath, &root, &kit) {
    Some(t) => t,
    None => continue,
};
```

So the file is skipped before SHACL validation. A skipped file cannot create `report.conforms() == false`, cannot increment `total_violations`, and cannot make the CLI exit non-zero.

### Fail-open and fail-closed map

| Condition | Source behavior | Exit implication | ACP implication |
|---|---|---|---|
| Not a git repo | `exit(1)` | fail-closed | Operational precondition only. |
| No kit configured | returns `true` | pass | Not proof that content is valid. |
| No SHACL shapes found | returns `true` | pass | Fail-open for proof gates. |
| Shape Turtle parse/load/schema/compile error | returns `true` | pass | Fail-open for proof gates. |
| Markdown has no frontmatter | skipped | pass if no other violations | Not validated. |
| Malformed YAML frontmatter | skipped via `None` | pass if no other violations | Not a valid negative fixture. |
| No `kit.class.property` key | skipped via `None` | pass if no other violations | Not validated. |
| Generated Turtle parse/load error | logged then `continue` | pass if no other violations | Fail-open for malformed generated data. |
| SHACL processor runtime error | logged but no violation count | pass if no other violations | Fail-open for processor errors. |
| SHACL report `!conforms()` | increments `total_violations` | `cmd_validate() == false`; CLI exits 1 | This is the only source-backed path for negative validation proof. |

### Fixture design hypothesis for T02

T02 should not use malformed YAML. It should create valid YAML frontmatter that passes `frontmatter_to_turtle()` and produces a data node targeted by a generated NodeShape, while violating constraints that the generated shapes actually contain.

Existing generated S10 shape inventory (`.gsd/exec/af2b2ad4-a10c-4e24-bbf8-9e3aba3ffc1b.stdout`) shows candidate constraints:

| Kit | Candidate class/property | Constraint | Fixture hypothesis |
|---|---|---|---|
| squad | `squad:Bug`, `squad:bugId` | `sh:minCount 1` | Create valid frontmatter with `squad.bug.bugStatus` but omit `squad.bug.bugId`; inferred type is `Bug`, so missing required `bugId` should violate `minCount`. |
| squad | `squad:Bug`, `squad:bugStatus` | `sh:in ( confirmed duplicate fixed open wontfix )`, plus `sh:minCount 1` | Use `squad.bug.bugStatus: not-a-status`; expected enum violation. |
| squad | `squad:Bug`, `squad:bugSeverity` | `sh:in ( cosmetic critical major minor )` | Use `squad.bug.bugSeverity: impossible`; expected enum violation. |
| soul | `soul:Dream`, `soul:dreamId` | `sh:minCount 1` | Create a `soul.dream.fromSoulDay` value but omit `soul.dream.dreamId`; expected required-field violation. |
| soul | `soul:Dream`, `soul:fromSoulDay` | `sh:datatype xsd:integer`, `sh:minCount 1` | Use `soul.dream.fromSoulDay: not-an-integer`; expected datatype violation if RDF parser accepts lexical typed literal and SHACL checks datatype value. |
| autoknow | `autoknow:Source`, `autoknow:sourceId` and `sourceType` | `sh:minCount 1`; `sourceType` enum | Use valid `autoknow.source.sourceType: spaceship` and omit `sourceId`; expected enum and required-field violation. |
| autoknow | `autoknow:Entity`, `autoknow:mentionCount` | `sh:datatype xsd:integer` | Use `autoknow.entity.mentionCount: not-an-int`; expected datatype violation. |

Important fixture rules from source:

1. At least one key must match `short.class.property`, for example `squad.bug.bugStatus`.
2. The class segment is capitalized to infer RDF type, for example `bug` -> `Bug`.
3. If all kit-prefixed values are empty, the file is skipped.
4. ObjectProperty node-kind violations may be hard to trigger via normal frontmatter because `frontmatter_to_turtle()` converts object-property strings into IRIs. Required/enum/datatype violations are stronger first candidates.
5. A successful negative proof must show `Validated ... violation(s)` and CLI exit code `1`, not merely stderr text.

### T01 conclusion

The validator is not globally fail-closed. It is fail-closed only for actual SHACL conformance reports containing violations. Several setup and data-generation failures are fail-open or skipped:

- missing kit;
- missing shapes;
- bad shapes parse/load/compile;
- malformed YAML frontmatter;
- no kit-prefixed frontmatter keys;
- generated Turtle parse/load errors;
- SHACL processor errors.

Therefore M052/S01 should focus on shape-derived, valid-frontmatter invalid fixtures that reach `ShaclProcessor::validate()` and produce `report.conforms() == false`. Until T03 proves that path at runtime, git-lex negative SHACL validation remains **source-plausible but runtime-unproven** for ACP proof gates.

## T02: Shape-derived invalid fixture design

### Scope

T02 designs invalid fixtures only. It does not run `git-lex validate` and does not create or mutate `/root/law-nexus/.lex`.

The fixture design is based on generated SHACL shapes already present in prior isolated M051/S10 runtime workspaces. Constraint extraction was summarized in:

```text
.gsd/exec/382ed002-d210-473e-8bc6-2e800389653f.stdout
```

The extracted candidate constraints came from:

```text
/tmp/law-nexus-git-lex-s10-t09-corrected-20260531T142648Z/squad/.lex/ontology/squad/squad-shapes.ttl
/tmp/law-nexus-git-lex-s10-t09-corrected-20260531T142648Z/soul/.lex/ontology/soul/soul-shapes.ttl
/tmp/law-nexus-git-lex-s10-t09-corrected-20260531T142648Z/autoknow/_ontology/autoknow/autoknow-shapes.ttl
```

### Constraint inventory used for fixtures

| Kit | Class | Constraint candidates |
|---|---|---|
| squad | `squad:Bug` | `bugId` required; `bugStatus` required and enum `confirmed`, `duplicate`, `fixed`, `open`, `wontfix`; `bugSeverity` enum `cosmetic`, `critical`, `major`, `minor`. |
| soul | `soul:Dream` | `dreamId` required; `fromSoulDay` required and `xsd:integer`; `dreamComposedAt` `xsd:dateTime`; `dreamConsumed` `xsd:boolean`. |
| autoknow | `autoknow:Entity` | `entityId` required; `entityType` required; `mentionCount` `xsd:integer`. |
| autoknow | `autoknow:Source` | Prior S10 inventory also showed `sourceId` required; `sourceType` enum `chat`, `conversation`, `document`, `email`, `note`, `webpage`; `dateCaptured`/`dateUpdated` `xsd:dateTime`; `messageCount` `xsd:integer`. |

### Fixture design principles

A valid negative fixture must:

1. Be valid YAML frontmatter so `serde_yaml::from_str(...).ok()?` does not skip it.
2. Contain at least one `short.class.property` key so `frontmatter_to_turtle()` infers a document type.
3. Use a class segment that maps to a generated `sh:targetClass`, for example `squad.bug.*` -> `squad:Bug`.
4. Avoid relying on malformed YAML, absent frontmatter, unknown prefix, or empty values because those are skipped before SHACL validation.
5. Prefer `sh:minCount`, `sh:in`, and `sh:datatype` because normal frontmatter conversion makes `sh:nodeKind sh:IRI` harder to violate: object-property values are emitted as IRIs.
6. Expect success only if T03 observes `Validated ... violation(s)` and CLI exit code `1`.

### Proposed T03 fixtures

#### Fixture A: squad required and enum violation

Target workspace:

```text
/tmp/m052-s01-shacl-negative-*/squad
```

File:

```text
Squad/Bug/InvalidBug.md
```

Content:

```markdown
---
squad.bug.bugStatus: impossible-status
squad.bug.bugSeverity: impossible-severity
---
Invalid squad bug fixture.
```

Expected generated RDF behavior:

- `frontmatter_to_turtle()` sees `squad.bug.*` and emits `<urn:doc:...> a squad:Bug`.
- `bugId` is omitted, so `sh:minCount 1` for `squad:bugId` should be violated.
- `bugStatus` lexical value is outside `sh:in`, so enum constraint should be violated.
- `bugSeverity` lexical value is outside `sh:in`, so enum constraint should be violated.

Expected validation result if negative SHACL works:

```text
exit code: 1
stderr includes: violation(s)
stderr includes one or more messages for bugStatus / bugSeverity / missing bugId
```

#### Fixture B: squad required-only control

File:

```text
Squad/Bug/MissingBugId.md
```

Content:

```markdown
---
squad.bug.bugStatus: open
---
Missing required bugId only.
```

Purpose:

- Isolates `sh:minCount` without enum noise.
- Expected violation: missing `squad:bugId`.

This is useful if enum handling is unsupported or noisy.

#### Fixture C: soul required and datatype violation

Target workspace:

```text
/tmp/m052-s01-shacl-negative-*/soul
```

File:

```text
Soul/Dream/InvalidDream.md
```

Content:

```markdown
---
soul.dream.fromSoulDay: not-an-integer
soul.dream.dreamConsumed: not-a-boolean
---
Invalid soul dream fixture.
```

Expected generated RDF behavior:

- `frontmatter_to_turtle()` infers `soul:Dream`.
- `dreamId` is omitted, so required/minCount should fail.
- `fromSoulDay` is emitted as typed literal `"not-an-integer"^^xsd:integer`; Turtle parsing may accept the lexical form and SHACL datatype should fail.
- `dreamConsumed` is emitted as typed literal `"not-a-boolean"^^xsd:boolean`; datatype should fail if lexical checking is enforced.

Caveat:

- If the RDF parser rejects invalid typed literal lexical forms before SHACL, source says `cmd_validate()` logs a parse error and continues. That would be fail-open and should be recorded as a blocked result, not as a successful negative validation.

#### Fixture D: autoknow required and datatype violation

Target workspace:

```text
/tmp/m052-s01-shacl-negative-*/autoknow
```

File:

```text
AutoKnow/Entity/InvalidEntity.md
```

Content:

```markdown
---
autoknow.entity.entityType: concept
autoknow.entity.mentionCount: not-an-integer
---
Invalid autoknow entity fixture.
```

Expected generated RDF behavior:

- `frontmatter_to_turtle()` infers `autoknow:Entity`.
- `entityId` is omitted, so required/minCount should fail.
- `mentionCount` is emitted as `xsd:integer`; invalid lexical value should either become SHACL datatype violation or a parser-level fail-open skip.

#### Fixture E: autoknow enum violation for Source

File:

```text
AutoKnow/Source/InvalidSource.md
```

Content:

```markdown
---
autoknow.source.sourceType: spaceship
autoknow.source.sourceName: Invalid source
---
Invalid autoknow source fixture.
```

Expected generated RDF behavior:

- `frontmatter_to_turtle()` infers `autoknow:Source`.
- `sourceId` is omitted, so required/minCount should fail.
- `sourceType` is outside allowed enum values and should fail `sh:in`.

### T03 runtime matrix recommendation

T03 should run a matrix with at least:

| Kit | Positive control | Negative fixtures |
|---|---|---|
| squad | Valid `Bug` or prior positive fixture with `bugId` and allowed `bugStatus` | Fixture A and B |
| soul | Valid `Dream` with `dreamId` and integer `fromSoulDay` | Fixture C |
| autoknow | Valid `Entity` or `Source` with required IDs | Fixture D and E |

For every run, T03 must record:

- command;
- exit code;
- stdout/stderr;
- exact fixture file path;
- generated shape path;
- whether file was counted in `Validated N files`;
- whether result was an actual SHACL violation, parser skip, processor error, or unexpected pass;
- `test ! -e /root/law-nexus/.lex` before and after.

### T02 conclusion

The T02 fixture design now targets real generated SHACL constraints instead of malformed frontmatter. The highest-confidence first runtime test is `squad:Bug` because it combines required and enum constraints and avoids datatype lexical-form ambiguity. `soul` and `autoknow` datatype fixtures are useful second-order tests but must be interpreted carefully because typed-literal parse errors may be fail-open before SHACL conformance reporting.

## T03: Isolated negative validation runtime matrix

### Scope and safety

T03 ran only in disposable `/tmp` repositories with the source-built debug binary:

```text
binary: /root/vendor-source/git-lex/target/debug/git-lex
workspace_root: /tmp/m052-s01-shacl-negative-6pi1ifhf
main_lex_before: False
main_lex_after: False
```

Full runtime output is persisted at:

```text
.gsd/exec/8be9e02b-3e9b-47f9-9807-44cc1f84cf2e.stdout
```

No `/root/law-nexus/.lex` state was created.

### Runtime matrix summary

| Kit | Phase | Fixture | Exit | Result |
|---|---|---|---:|---|
| squad | init | n/a | 0 | Init succeeded; hooks ran extraction/validation and existing content passed. |
| squad | positive | `Squad/Bug/ValidBug.md` | 0 | `Validated 2 files ... all pass`. |
| squad | negative required and enum | `Squad/Bug/InvalidBug.md` | 1 | 3 violations in 1 file: invalid `bugStatus`, missing `bugId`, invalid `bugSeverity`. |
| squad | negative required-only | `Squad/Bug/MissingBugId.md` | 1 | 1 direct violation for missing `bugId`; cumulative run also reports prior invalid fixture. |
| soul | init | n/a | 0 | Init succeeded with `agent_name` supplied non-interactively; existing content passed. |
| soul | positive | `Soul/Dream/ValidDream.md` | 0 | `Validated 3 files ... all pass`. |
| soul | negative required/datatype | `Soul/Dream/InvalidDream.md` | 1 | 3 violations: `fromSoulDay` datatype, missing `dreamId`, `dreamConsumed` datatype. |
| autoknow | init | n/a | 0 | Init succeeded; generated `_ontology/autoknow/autoknow-shapes.ttl`; initial validation counted 0 files. |
| autoknow | positive | `AutoKnow/Entity/ValidEntity.md` | 0 | `Validated 1 files ... all pass`. |
| autoknow | negative entity | `AutoKnow/Entity/InvalidEntity.md` | 1 | 2 violations: missing `entityId`, invalid `mentionCount` datatype. |
| autoknow | negative source | `AutoKnow/Source/InvalidSource.md` | 1 | 2 violations for source fixture: missing `sourceId`, invalid `sourceType` enum; cumulative run also reports prior invalid entity. |

### Key observed outputs

#### Squad invalid bug

```text
Squad/Bug/InvalidBug.md — 3 violation(s):
  → In constraint not satisfied. Expected one of: confirmed, duplicate, fixed, open, wontfix
  → MinCount(1) not satisfied
  → In constraint not satisfied. Expected one of: cosmetic, critical, major, minor
Validated 3 files in 55.5ms — 3 violation(s) in 1 file(s)
exit code: 1
```

#### Squad missing required only

```text
Squad/Bug/MissingBugId.md — 1 violation(s):
  → MinCount(1) not satisfied
Validated 4 files in 54.9ms — 4 violation(s) in 2 file(s)
exit code: 1
```

#### Soul invalid dream

```text
Soul/Dream/InvalidDream.md — 3 violation(s):
  → Expected datatype: xsd:integer
  → MinCount(1) not satisfied
  → Expected datatype: xsd:boolean
Validated 4 files in 71.3ms — 3 violation(s) in 1 file(s)
exit code: 1
```

#### Autoknow invalid entity

```text
AutoKnow/Entity/InvalidEntity.md — 2 violation(s):
  → MinCount(1) not satisfied
  → Expected datatype: xsd:integer
Validated 2 files in 32.9ms — 2 violation(s) in 1 file(s)
exit code: 1
```

#### Autoknow invalid source

```text
AutoKnow/Source/InvalidSource.md — 2 violation(s):
  → MinCount(1) not satisfied
  → In constraint not satisfied. Expected one of: chat, conversation, document, email, note, webpage
Validated 3 files in 35.6ms — 4 violation(s) in 2 file(s)
exit code: 1
```

### What this upgrades

M051's negative validation gap is now narrowed substantially:

- Valid YAML with kit-prefixed keys reaches SHACL validation.
- Generated `sh:minCount`, `sh:in`, and `sh:datatype` constraints can produce `!report.conforms()`.
- `cmd_validate()` returns `false` for those reports.
- CLI `git-lex validate` exits `1` for shape-derived invalid fixtures.
- Positive controls still exit `0`.
- This was proven for three non-base kits: `squad`, `soul`, and `autoknow`.

### What remains bounded

This does not remove all validator caveats found in T01:

| Surface | Status after T03 | Reason |
|---|---|---|
| Shape-derived invalid fixtures | runtime-backed fail-closed | Proven with exit code 1 for `squad`, `soul`, `autoknow`. |
| Positive validation | runtime-backed | Positive controls passed. |
| Missing kit / missing shapes | still fail-open | Source trace returns `true`. |
| Bad shape parse/load/schema/compile | still fail-open | Source trace returns `true`. |
| Malformed YAML frontmatter | still skipped/fail-open | Source trace returns `None` and `continue`. |
| Unknown or empty kit-prefixed properties | still skipped/fail-open | `frontmatter_to_turtle()` returns `None` if no usable kit props. |
| Generated Turtle parse/load errors | still fail-open | Source trace logs and continues. |
| SHACL processor errors | still fail-open | Source trace logs errors without incrementing violations. |

### T03 conclusion

Negative SHACL validation is now **runtime-backed for shape-derived valid-frontmatter violations**. It is not globally fail-closed: setup, malformed input, missing shapes, parser/load, and processor-error paths remain fail-open or skipped. ACP can use git-lex validation as an adapter-later diagnostic for generated shape constraints, but must not treat it as a complete proof gate without wrapper checks for skipped files, missing shapes, setup errors, and expected file counts.

## T04: SHACL proof-gate classification

### Final classification

| Capability | M051 status | M052/S01 status | Classification |
|---|---|---|---|
| Positive `git-lex validate` | runtime-backed narrow positive fixture | confirmed across squad/soul/autoknow positive controls | runtime-backed smoke |
| Negative validation for malformed YAML | failed to fail | source-explained as skipped before SHACL | rejected as negative proof strategy |
| Negative validation for generated shape constraints | unproven | proven with exit 1 for `sh:minCount`, `sh:in`, and `sh:datatype` violations | upgraded to runtime-backed diagnostic |
| Global validation fail-closed behavior | unproven | source shows multiple fail-open/skipped paths | still blocked as complete proof gate |
| ACP proof-gate use | blocked | possible only behind wrapper checks | adapter-later, wrapper-required |

### Knowledge delta KD-M052-S01

| Field | Value |
|---|---|
| Prior assumption/open question | M051 could not prove negative validation; malformed frontmatter did not fail. |
| Evidence anchor | `prd/architecture/acp/M052-S01-SHACL-NEGATIVE-VALIDATION.md`; `.gsd/exec/8be9e02b-3e9b-47f9-9807-44cc1f84cf2e.stdout`. |
| Proof class | GitNexus/source trace plus isolated runtime proof. |
| Updated conclusion | `git-lex validate` can fail closed for valid-frontmatter documents that reach SHACL and violate generated shape constraints. |
| Remaining boundary | It is not globally fail-closed; missing shapes, malformed YAML, skipped files, parser/load/setup errors, and processor errors can still pass or be skipped. |
| Downstream implication | ACP may treat git-lex validation as adapter-later diagnostic evidence only if wrapper checks enforce expected shapes, counted files, and fail-closed handling for diagnostics. |

### Runtime adoption gate update

Updated durable guidance:

```text
.agents/skills/git-lex/references/runtime-adoption-gates.md
```

The update records that M052/S01 upgraded negative validation for shape-derived fixtures, while preserving wrapper requirements for skipped/fail-open paths.

### ACP implication

For ACP, the safe wording is:

> git-lex validation has runtime-backed negative behavior for generated SHACL constraints when files are valid frontmatter and are actually counted by the validator. It is not sufficient as a standalone ACP proof gate without adapter wrapper checks for missing shapes, skipped files, setup diagnostics, and expected file counts.

Unsafe wording remains:

> git-lex validation is fail-closed for all invalid documents.

### S01 conclusion

S01 resolves the original M051 negative-validation gap narrowly but materially. The status moves from **negative validation unproven** to **negative validation runtime-backed for shape-derived valid-frontmatter fixtures, wrapper-required for ACP proof gates**.
