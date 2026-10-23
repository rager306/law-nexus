# Источники, версии и границы проверки

Проверено 2026-10-23. Для адаптации использованы GitHub metadata, фактический
release asset, pinned source Allspark, ранее проверенные контракты Path/PDD,
публичный Law-Nexus и дополнительный **DeepWiki MCP**. Точные commands/keys
сверены с кодом, а не только с README. Результаты реально выполненных probes
находятся в `validation/TESTED.md` исходного архива starter.

Распределение ответственности между компонентами, выбор conservative profile
и порядок bootstrap PR→native binding — наши проектные рекомендации, выведенные
из этих контрактов. Это не официальная универсальная интеграция трёх продуктов.

## Фиксированные baseline

| Компонент | Версия/ревизия |
|---|---|
| Allspark release | `allspark-v0.10.1-beta.38-fork.009` |
| Allspark source для release и supplement | `91ef629272eea1f556025ef0dbfe2b07bf8053fc` |
| Allspark main при проверке | `f4fc256bc88b95185cce823e6bd4f7196dc551c0`; не устанавливается |
| GSD Path | npm `@opengsd/gsd-path` 1.6.2; runtime digest в `.ai/versions.json` |
| PDD Kit | 0.37.1; `a833ce7efa3d37adfae77128b4b153ddaa3ff0ea` |
| Law-Nexus | `f15612b2034ce71c9109326173c5e8a3b8a86b76` при исходном исследовании |
| Node.js | 22.23.4 |
| uv | 0.13.5 |

Перед исполнением сравнить фактический Law HEAD. Исследованный публичный
checkout не содержит ignored `.gsd`, local AGENTS/MCP и dirty worktrees.
Online документация не доказывает состояние пользовательской машины.

## Allspark: release, identity и установка

- [Опубликованный release](https://github.com/rager306/allspark/releases/tag/allspark-v0.10.1-beta.38-fork.009),
  [SHA256SUMS](https://github.com/rager306/allspark/releases/download/allspark-v0.10.1-beta.38-fork.009/SHA256SUMS).
- [Source tree release commit](https://github.com/rager306/allspark/tree/91ef629272eea1f556025ef0dbfe2b07bf8053fc),
  [tag→main snapshot compare](https://github.com/rager306/allspark/compare/91ef629272eea1f556025ef0dbfe2b07bf8053fc...f4fc256bc88b95185cce823e6bd4f7196dc551c0).
- [Fork release packaging в tag](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/.github/workflows/release-fork.yml),
  [fork changelog](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/CHANGELOG-FORK.md).
- [Официальный launcher](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/scripts/allspark-launcher.sh): HOME, agent/session dirs и socket.
- [Fork identity](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/docs/fork-identity.md),
  [root instructions, fork section](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/AGENTS.md).
- [Fork feature guide](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/readme-fork.md) и
  [верхний README](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/README.md)
  содержат расхождения с данным release; они перечислены в ALLSPARK_NOTES.
- [CLI config](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-cli/src/config.rs),
  [CLI args](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-cli/src/args.rs),
  [bootstrap entry](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-cli/src/lib.rs).
- [Kernel source resolution](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/kernel/bootstrap/venv/runtime_source.rs),
  [runtime dependencies](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/prime-agent-runtime/pyproject.toml).
- [Compiled model fallback](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-models/src/chain.rs),
  [MCP catalog assembly](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/mcp/service_catalog.rs).

## Allspark: настройки, skills и инструменты

- [Settings types и Jev defaults](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/settings/types.rs),
  [storage](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/settings/storage.rs),
  [merge](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/settings/merge.rs).
- [Global-only harness/factory settings](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/settings/interactive_settings.rs),
  [RLM depth](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/session_engine/rlm_host.rs).
- [Skill auto-discovery](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/packages/resolve/auto.rs),
  [explicit resource resolution](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/resources/resolution.rs).
- [Native tool integration](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/session_engine/engine.rs),
  [active LSP server table](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-lsp/src/servers.rs).
- [MCP settings/runtime schema](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/mcp/mod.rs),
  [global-only CLI management](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-cli/src/mcp_command.rs),
  [generic MCP skill](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/skills/mcp/SKILL.md).
- [Print runtime](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-cli/src/print_runtime.rs),
  [version-check opt-out](https://github.com/rager306/allspark/blob/91ef629272eea1f556025ef0dbfe2b07bf8053fc/crates/pa-core/src/update/release.rs).

## GSD Path

- [Repository/release](https://github.com/open-gsd/gsd-path/tree/v1.6.2),
  [npm package metadata](https://registry.npmjs.org/@opengsd%2fgsd-path/1.6.2).
- [Python installer](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/install.py),
  [runtime verification/restore](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/status_runtime.py),
  [worktree placement](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/worktree_paths.py).
- [Router](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/path/SKILL.md),
  [host dispatch](https://github.com/open-gsd/gsd-path/blob/v1.6.2/skills/path/references/dispatch.md).
- [Build dispatcher](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/dispatch_driver.py),
  [workflow helper](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/workflow_run.py).
- [Binding/remote baseline](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/pipeline_git.py),
  [native state](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/pipeline_state.py),
  [Core-only migrator](https://github.com/open-gsd/gsd-path/blob/v1.6.2/scripts/migrate_core.py).

## PDD Kit и системные tools

- [Install](https://pdd-kit.dev/docs/cli-install), [map](https://pdd-kit.dev/docs/skill-pdd-map),
  [ideate](https://pdd-kit.dev/docs/skill-pdd-ideate), [verify](https://pdd-kit.dev/docs/skill-pdd-verify).
- [Model/schema](https://pdd-kit.dev/docs/product-model), [references](https://pdd-kit.dev/docs/references),
  [lint](https://pdd-kit.dev/docs/cli-lint), [viewer](https://pdd-kit.dev/docs/cli-view).
- [Pinned source](https://github.com/itai-gendler/pdd-kit/tree/a833ce7efa3d37adfae77128b4b153ddaa3ff0ea),
  [npm metadata](https://registry.npmjs.org/pdd-toolkit/0.37.1).
- [Node release](https://nodejs.org/en/blog/release/v22.23.4/),
  [archive SHA256](https://nodejs.org/dist/v22.23.4/SHASUMS256.txt).
- [uv release](https://github.com/astral-sh/uv/releases/tag/0.13.5),
  [uv storage env](https://github.com/astral-sh/uv/blob/0.13.5/docs/reference/storage.md).
- [Rust installation](https://rustup.rs/).

## DeepWiki MCP: как использовано

Для этой адаптации выполнены MCP `initialize`, discovery, чтение wiki structure
`rager306/allspark` и два `ask_wiki_question`. Форк обнаружен в индексе.
Ответы использованы для навигации и дополнительной проверки:

- [Allspark identity, installation и resource resolution](https://deepwiki.com/search/adapting-a-pinned-repolocal-in_d9cbe701-4cd2-42e8-877f-d1ca7b527b44).
- [Границы native integration с GSD Path](https://deepwiki.com/search/does-the-indexed-allspark-fork_6c6ea247-539f-4a8b-b67d-3ab7b96e0c6b).

DeepWiki не дал надёжного exact indexed commit SHA. Некоторые обобщения
catalog packaging и fork defaults расходятся с опубликованным asset и кодом.
Поэтому источником pin/installation claims являются GitHub и actual archive,
а не предположение, что wiki всегда описывает release tag.

Предыдущее исследование Path/PDD использовало также:

- [Path CLI orchestration](https://deepwiki.com/search/for-a-proposed-integration-wit_55020166-ab96-4120-94fb-f31b45731ecd).
- [Path integration limits](https://deepwiki.com/search/assess-sourcesupported-integra_46bdb130-cc25-4210-88be-c9ea56c72292).
- [Path sole coordinator и review](https://deepwiki.com/search/we-want-path-to-remain-the-sol_879db740-8cfb-4f73-a6e8-9211246e3adc).
- [Установка, exact restore и clean baseline](https://deepwiki.com/search/preparing-migration-installati_f6b47cb4-6254-464c-8d48-f4efdd33d709).

PDD и Law-Nexus не были доступны в индексе при том исследовании; их сведения
сверялись непосредственно с primary docs/source. Это не утверждение об их
будущем статусе индексации. Для подключения DeepWiki к Allspark используем
[официальный Streamable HTTP endpoint](https://docs.devin.ai/work-with-devin/deepwiki-mcp),
но actual tool names всегда получаем через discovery.

## Law-Nexus

Файловые источники, historical CI baseline, migration matrix и proof limits
собраны в разделе «Источники» [MIGRATION.md](MIGRATION.md#источники).
Старый CI run не представлен как сегодняшняя локальная проверка. Полный
legal/product audit и actual migration не являются выполненной частью
подготовки этого installer/tutorial.
