# ACP/git-lex decommission roadmap

**Status:** `[proposed]`, решение принято (D104), исполнение не начато.  
**Requirement:** R066.  
**Boundary:** внешний репозиторий `/root/git-lex-kit-acp/` не изменяется.

## Цель

Полностью вывести ACP/git-lex из активной архитектуры, runtime, hooks, CI,
skills, requirements, roadmap и source-of-truth law-nexus. Исторические
project-local артефакты не удаляются: они перемещаются в явно историческую
область `python_archive/acp_git_lex/` или другой согласованный archive root.

Общие полезные механики — архитектурные зависимости, ADR conformance,
requirement/state consistency, доказуемость, fail-closed проверки — сохраняются,
но переписываются без ACP/git-lex vocabulary и runtime dependence.

## Инвентарь на входе

Снимок 2026-07-20, tracked paths по ACP/git-lex паттернам: **555**.

| Группа | Файлы | Действие |
|---|---:|---|
| `.lex/` | 281 | архивировать целиком после отключения hook; убрать из активного checkout |
| `prd/architecture/acp/` | 194 | архивировать как историческую исследовательскую ветку |
| ACP/git-lex tests | 21 (name-based minimum) | архивировать с кодом; затем удалить из active pytest collection |
| ACP/git-lex scripts | 15 (name-based minimum) | архивировать; убрать active entrypoints/imports |
| `git-lex-kit-law-nexus/` | 14 | архивировать project-local kit/profile |
| `git-lex-kit-acp/` | 13 | архивировать только project-local copy; внешний repo не трогать |
| `.agents/skills/git-lex/` | 5 | архивировать, удалить active skill routing |
| `.agents/skills/acp/` | 3 | архивировать, удалить active skill routing |
| `.github/workflows/compliance-gate.yml` | 1 | не удалять вслепую: переименовать/rewrite как Rust+harness quality gate |
| другие PRD/source references | минимум 8 direct paths и около 300 textual-ref files | классифицировать historical/current; current переписать |

Name-based inventory — нижняя граница. Перед каждой archive wave нужен точный
manifest (`source_path`, `archive_path`, `sha256`, class, reason).

## Критическая операционная находка

`.git/hooks/pre-commit` сейчас полностью управляется git-lex и выполняет:

```sh
git-lex hook pre-commit
```

Последний ADR commit автоматически изменил `.lex/extract`, доказав, что git-lex
остаётся активным mutating dependency. `.pre-commit-config.yaml` сам `.lex` не
мутирует; он запускает ruff, import-linter и ADR verifier.

Первая волна обязана отключить именно git-managed `.git/hooks/pre-commit`, а не
удалить полезные structural checks.

## Архивная политика

Предлагаемый root:

```text
python_archive/acp_git_lex/
├── MANIFEST.json
├── README.md
├── lex-state/                 # бывшая .lex/
├── architecture/              # бывшая prd/architecture/acp/
├── scripts/
├── tests/
├── skills/
├── kits/
└── docs/
```

Правила:

1. только `git mv`, без удаления истории;
2. manifest фиксирует старый/новый path, sha256, тип, milestone и причину;
3. архив не импортируется, не исполняется и не сканируется active harness, кроме
   integrity check;
4. archive tests не входят в pytest collection;
5. generated `.spo`/projection state хранится как исторический снимок, но не
   обновляется hooks;
6. внешний `/root/git-lex-kit-acp/` и vendor checkouts не мутируются;
7. Git history остаётся основным rollback.

## Волны

### Wave D0 — Freeze and manifest

**Риск:** low. **Зависимости:** нет.

- снять точный список tracked paths и textual references;
- классифицировать `active-runtime`, `active-general-check`, `historical`,
  `product-reference`, `archive-only`;
- зафиксировать hashes и archive map;
- доказать, что product parser/retrieval/FalkorDB paths не попали в archive list.

**Проверка:** manifest completeness; duplicate target detection; product denylist;
`git diff --check`; GitNexus impact report.

### Wave D1 — Disconnect mutating runtime and hooks

**Риск:** high. **Зависимости:** D0.

- сохранить текущий `.git/hooks/pre-commit` как untracked local evidence outside
  active hook path;
- установить обычный `uv run pre-commit install` или target harness hook;
- проверить, что commit больше не запускает `git-lex hook pre-commit` и не
  изменяет `.lex/extract`;
- убрать git-lex commands from active local instructions/config;
- не архивировать bulk files в этой волне.

**Проверка:** hook content scan; dry/non-mutating pre-commit run; before/after
hash of `.lex`; temporary docs-only commit in isolated worktree if disk permits.

**Rollback:** restore hook file from manifest or `pre-commit install` again.

### Wave D2 — Preserve general quality gates without ACP vocabulary

**Риск:** medium. **Зависимости:** D1.

- rewrite `.pre-commit-config.yaml` comments and hook names to Rust/repository
  architecture terms;
- transform `.github/workflows/compliance-gate.yml` into repository-quality CI:
  current Python checks while Python is the reference, then Cargo+harness checks;
- preserve `verify-adr-conformance.py` behavior but remove D098/ACP dependencies;
- preserve architecture graph/check only if it uses PRD/GSD/ADR/source evidence
  without ACP projection; otherwise replace with a simpler harness contract;
- add tests that prove these checks work without `.lex` and ACP artifacts.

**Проверка:** targeted verifier tests; pre-commit; CI syntax; no `.lex` mutation;
architecture/harness negative fixtures.

### Wave D3 — Deactivate and archive skills, kits, runtime adapters

**Риск:** medium. **Зависимости:** D2.

Archive:

- `.agents/skills/acp/`, `.agents/skills/git-lex/`;
- `git-lex-kit-acp/`, `git-lex-kit-law-nexus/` project-local copies;
- `scripts/acp_git_lex_backend.py`, `scripts/git_lex_diagnostic_adapter.py`;
- ACP canonical/projection/export/build scripts and direct ACP/git-lex verifiers;
- matching unit/integration/runtime tests.

Before move, use GitNexus impact on every public function/class touched.

**Проверка:** active imports zero; active executable references zero; pytest
collection excludes archive; product targeted tests remain green.

### Wave D4 — Archive `.lex` and ACP architecture history

**Риск:** medium, large diff. **Зависимости:** D3.

- move `.lex/` to `python_archive/acp_git_lex/lex-state/`;
- move `prd/architecture/acp/` to archive;
- preserve all files and SHA-256 in manifest;
- move remaining ACP-specific root/research docs, projections and examples;
- ensure no generator recreates `.lex`.

Split into sub-waves if commit size/reviewability requires it:

- D4a `.lex` generated/extract state;
- D4b runtime/fixture evidence;
- D4c architecture/research prose.

**Проверка:** manifest hash verification; `test ! -e .lex`; active generator
search zero; general architecture checks and product tests green.

### Wave D5 — Requirements, decisions and living documents

**Риск:** high semantic risk. **Зависимости:** D4.

- set ACP/git-lex requirements R041–R059/R049–R054 to superseded/out-of-scope as
  applicable, preserving their historical text and evidence;
- record D104 as successor for active ACP/git-lex decisions;
- rewrite `prd/ARCHITECTURE.md`, PRD, README and roadmap to remove active
  ACP/git-lex roles;
- retain generic evidence/citation/fail-closed rules where product-relevant;
- remove active routing to external ACP/git-lex skills;
- update architecture registry or replace it with the repository harness source.

**Проверка:** requirement/state consistency; no active requirement owns ACP or
`.lex`; living docs cite ADR-0004/0005/0007 and R063–R066.

### Wave D6 — Final residue and product-preservation gate

**Риск:** low after prior waves. **Зависимости:** D5.

Final active-tree criteria (archive excluded):

- zero runtime/config/hook references to `git-lex`, `git lex`, `.lex`, ACP kits;
- zero active ACP/git-lex skills, scripts, tests or workflow steps;
- zero active ACP/git-lex requirements;
- external `/root/git-lex-kit-acp/` unchanged;
- Rust transition docs and Python product reference intact;
- parser/retrieval/FalkorDB targeted suite and architecture contracts pass;
- archive manifest verifies every moved file.

Historical prose may mention ACP/git-lex only under archive or explicit
supersession records.

## Product-preservation denylist

Never archive merely because a file contains generic words such as "evidence",
"lifecycle", "projection", "ontology", or "architecture". Preserve active
product contracts for:

- Russian legal source evidence and provenance;
- parser hierarchy, references, temporal/deontic markers;
- EvidenceSpan/Citation fail-closed semantics;
- FalkorDB integration and generated-Cypher safety;
- local embedding and retrieval quality;
- ADR/requirements/state consistency;
- Rust architecture and repository harness.

## Observability

Each wave emits a compact report:

```json
{
  "wave": "D1",
  "status": "pass|fail|blocked",
  "active_path_count_before": 555,
  "active_path_count_after": 0,
  "moved": [],
  "rewritten": [],
  "preserved": [],
  "residue": [],
  "verification": [],
  "rollback": "git commit or manifest reference"
}
```

`active_path_count_after` reaches zero only at D6. It must not be falsified by
excluding inconvenient active references; only explicit archive paths are
excluded.

## Definition of done

ACP/git-lex decommission is complete only when it cannot mutate, execute, gate,
route, validate, or define active law-nexus state; all historical project-local
artifacts remain recoverable; general architecture/evidence checks survive
without ACP/git-lex; and product/Rust migration surfaces remain green.
