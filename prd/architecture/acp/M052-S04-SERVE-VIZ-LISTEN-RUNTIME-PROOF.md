# M052 S04 Serve Viz Listen Runtime Proof

## Status

In progress for `M052-idogd6 / S04`.

S04 resolves whether `git-lex-serve`, `viz`, `display`, and `listen` are real browser/API surfaces that can be exercised locally, and records their ACP adoption boundary.

## Guardrails

- Do not create or mutate `/root/law-nexus/.lex`.
- Runtime proof must use isolated `/tmp` git repositories.
- Browser-facing claims require actual browser actions with assertions.
- Servers must bind only locally and be cleaned up after proof.
- Do not treat server reachability as production readiness or ACP adoption.

## T01: Source trace of serve/viz/listen behavior

### Entry points and command routing

| Surface | Source anchor | Finding |
|---|---|---|
| `git lex serve ...` | `/root/vendor-source/git-lex/src/main.rs:2486-2500` | CLI delegates to `Command::new("git-lex-serve").args(&args).status()`. It is pass-through; real server semantics are in the server binary. |
| `git-lex-serve` binary | `/root/vendor-source/git-lex/src/bin/git-lex-serve.rs:15-44` | Clap binary exposes two subcommands: `viz --port <u16>` default `7878`, and `listen --port <u16>` default `7879`. |
| Store location | `/root/vendor-source/git-lex/src/lib.rs:22-40` | Persistent store is `{repo_root}/.git/lex/oxigraph`; `open_store_read_only()` opens it read-only if present. |
| `display` client | `/root/vendor-source/git-lex/src/main.rs:1489-1512` | `git lex display` POSTs `{ "query": ... }` to `http://127.0.0.1:{port}/api/run-and-push`; it does not open the store itself because the server owns the read-only view. |

### `viz` server behavior

Source: `/root/vendor-source/git-lex/src/bin/git-lex-serve.rs`.

Preconditions in `cmd_viz(port)`:

1. `open_store_read_only()` must succeed; otherwise it exits with:

```text
No knowledge graph store found.
Run 'git lex sync' first to build the store.
```

2. `.lex/www` must exist under the git root; otherwise it exits with:

```text
No www directory found at ...
Run 'git lex init' to install the base kit.
```

Runtime behavior in `run_viz_server(port, www_dir)`:

- Opens the Oxigraph store read-only.
- Builds Axum routes.
- Binds to `127.0.0.1:{port}`.
- If requested port is unavailable, tries up to `port..port+20`.
- Logs the selected URL:

```text
git-lex-serve viz listening on http://127.0.0.1:{chosen_port}
Serving assets from {repo}/.lex/www
Press Ctrl+C to stop, or: kill {pid}
```

- Calls `open::that_detached(&url)` to open a browser, but server functionality does not depend on that call succeeding.

Routes:

| Route | Method | Behavior |
|---|---|---|
| `/` | GET | Serves `.lex/www/index.html`; if missing, returns `<h1>index.html not found in .lex/www/</h1>`. |
| `/css/main.css` | GET | Serves `.lex/www/css/main.css` with `text/css` and `no-store`. |
| `/js/main.js` | GET | Serves `.lex/www/js/main.js` with `application/javascript` and `no-store`. |
| `/api/query` | POST JSON | Reads `query` field or defaults to `SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10`; returns SELECT/ASK/CONSTRUCT JSON from `run_sparql_to_json`. |
| `/api/push` | POST JSON | Stores arbitrary scene JSON and broadcasts it over WebSocket. |
| `/api/run-and-push` | POST JSON | Requires `query`; runs query, stores scene, broadcasts, returns `{ "ok": true }`. |
| `/api/file?uri=...` | GET | Resolves `fm:path` for an IRI, canonicalizes within repo root, and returns frontmatter/content or an error. |
| `/api/scene` | GET | Returns latest pushed scene or `null`. |
| `/ws` | WebSocket | Sends current scene or `{ "type":"hello" }`, then streams broadcasts. |

Query result behavior in `run_sparql_to_json`:

- SELECT returns `{ "type": "select", "vars": [...], "results": [...] }`.
- ASK returns `{ "type": "ask", "boolean": true|false }`.
- CONSTRUCT returns `{ "type": "construct", "triples": [...] }`.
- Parse/query errors return `{ "error": "parse error: ..." }` or `{ "error": "query error: ..." }` with HTTP 200 JSON, not a failing HTTP status.

### `listen` server behavior

Source: `/root/vendor-source/git-lex/src/bin/git-lex-serve.rs:437-501`.

Preconditions in `cmd_listen(port)`:

1. Must be in a git repo.
2. `.lex/repo.yml` must exist; otherwise exits:

```text
No git-lex repository found. Run 'git lex init' first.
```

3. `.lex/repo.yml` must contain one of:

```text
kit: squad
kit: soul
kit: lab
```

Otherwise exits:

```text
'listen' is only supported for squad, soul, or lab kits.
```

4. `open_store_read_only()` must succeed; otherwise exits:

```text
No knowledge graph store found. Run 'git lex sync' first to build the store.
```

Runtime behavior in `run_listen_server(port)`:

- Binds to `127.0.0.1:{port}`.
- Logs:

```text
git-lex-serve listen started on 127.0.0.1:{port}
```

- Exposes:

| Route | Method | Behavior |
|---|---|---|
| `/events` | GET | Server-Sent Events stream of broadcast messages. |
| `/notify` | POST JSON | Broadcasts payload JSON string and returns `{ "ok": true }`. |

Unlike `viz`, `listen` does not scan fallback ports; it unwraps bind and can panic/fail if the port is occupied.

### Browser / local exposure boundary

Both `viz` and `listen` bind to `127.0.0.1`, not `0.0.0.0`, in the observed source. This is appropriate for isolated local proof. It does not prove production exposure hardening, auth, CSRF protection, ACLs, TLS, or safe multi-user deployment.

### Safe invocation hypotheses for T02-T04

T02 workspace setup should:

```text
cd /tmp/m052-s04-...
git init
git-lex init --kit squad
git add ... && git commit ...
git-lex sync
```

Use `squad` because:

- `viz` only needs a synced store and `.lex/www`;
- `listen` explicitly supports `squad`;
- prior M052/S01/S03 fixtures already used squad successfully.

T03 safe `viz` command:

```text
PATH=/root/vendor-source/git-lex/target/debug:$PATH \
/root/vendor-source/git-lex/target/debug/git-lex-serve viz --port <free_local_port>
```

Expected proof points:

- readiness log includes `git-lex-serve viz listening on http://127.0.0.1:<port>`;
- browser `GET /` shows git-lex UI text or installed HTML markers;
- `/api/query` POST returns JSON with `type: select` for a known query;
- `/api/run-and-push` POST returns `{ "ok": true }`;
- `/api/scene` returns stored scene after push;
- server is killed cleanly;
- `/root/law-nexus/.lex` remains absent.

T04 safe `listen` command:

```text
PATH=/root/vendor-source/git-lex/target/debug:$PATH \
/root/vendor-source/git-lex/target/debug/git-lex-serve listen --port <free_local_port>
```

Expected proof points:

- readiness log includes `git-lex-serve listen started on 127.0.0.1:<port>`;
- POST `/notify` returns `{ "ok": true }`;
- SSE `/events` receives a posted payload if tested with a streaming client;
- classify as local notification server smoke only, not ACP adoption.

### T01 classification

```text
viz source behavior: source-backed local Axum HTTP/WebSocket server
viz runtime proof status: pending T03 browser/API assertions
listen source behavior: source-backed local Axum SSE/notify server for squad/soul/lab kits
listen runtime proof status: pending T04 endpoint probe
production/browser adoption status: still blocked until runtime, security, provenance, and rollback proof
```

## T02: Isolated serve workspace preparation

### Runtime workspace

Prepared workspace:

```text
/tmp/m052-s04-serve-co1uhmmh
```

Evidence anchors:

```text
.gsd/exec/3adc3be0-2473-47e9-b69d-8264104ae544.stdout
.gsd/exec/5f4ed792-8431-4b69-af32-16eaf2141247.stdout
```

### Setup result

The workspace was prepared with:

```text
git init
git-lex init --kit squad
git add README.md notes/context.txt
git commit -m "m052 s04 serve fixture"
git-lex sync
```

The first T02 attempt used an incomplete `squad:Decision` frontmatter fixture and was correctly rejected by git-lex pre-commit validation with `MinCount(1) not satisfied`. That workspace was discarded. The final workspace uses a README/plain-text fixture because S04 tests server behavior, not SHACL domain validation.

Final sync result:

```text
Sync /sync/37bbc4b5/: +17 assertions, -0 retracted (102 quads)
History: 4 commit(s), 17 events, 21 annotations
Total sync graphs: 1
Store: /tmp/m052-s04-serve-co1uhmmh/.git/lex/oxigraph
```

### Prepared-state checks

Corrected verification passed:

```text
workspace_exists: pass
repo: pass
repo_yml: pass
www_index: pass
www_js: pass
store: pass
squad_kit: pass
main_lex_absent: pass
```

`repo.yml` records the kit as:

```text
kit: repolex-ai/git-lex-kit-squad
```

This satisfies the S04 source requirement because `listen` checks for `kit: squad` or compatible kit text in source; T04 must verify whether the fully-qualified kit string is accepted at runtime or rejected by that exact source check.

### T02 classification

```text
serve workspace status: ready for T03/T04
viz prerequisites: `.git/lex/oxigraph` and `.lex/www` present
listen prerequisite ambiguity: source check may reject fully-qualified `repolex-ai/git-lex-kit-squad`; T04 must prove actual behavior
main repository safety: `/root/law-nexus/.lex` absent
```

## T03: Viz server browser and API proof

### Server invocation

Command:

```bash
cd /tmp/m052-s04-serve-co1uhmmh && \
PATH=/root/vendor-source/git-lex/target/debug:$PATH \
/root/vendor-source/git-lex/target/debug/git-lex-serve viz --port 8891
```

Server process:

```text
bg_shell process: 67150aec
status: ready
detected URL: http://127.0.0.1:8891
```

Server logs:

```text
git-lex-serve viz listening on http://127.0.0.1:8891
Serving assets from /tmp/m052-s04-serve-co1uhmmh/.lex/www
Press Ctrl+C to stop, or: kill 1962277
```

The server was killed after browser/API proof, and `bg_shell list` returned:

```text
No background processes.
```

### Browser UI assertions

Browser target:

```text
http://127.0.0.1:8891/
```

`browser_batch` passed navigation plus visible text assertions:

```text
git-lex viz
Recent Activity
Repo Graph
Interactive
```

Final page state also showed:

```text
connected
m052-s04-serve-co1uhmmh
kit: repolex-ai/git-lex-kit-squad
4 commits
17 documents
975 triples
```

### API proof

Browser-side fetch proof executed:

```javascript
POST /api/query        { query: 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 3' }
POST /api/run-and-push { query: 'ASK { ?s ?p ?o }' }
GET  /api/scene
```

Result:

```json
{
  "queryStatus": 200,
  "queryType": "select",
  "queryRows": 3,
  "pushStatus": 200,
  "pushOk": true,
  "sceneType": "ask",
  "sceneBoolean": true,
  "title": "git-lex viz",
  "bodyHasBrand": true
}
```

This proves the server can:

- serve the browser UI;
- query the read-only Oxigraph store;
- accept `run-and-push` scene updates;
- return pushed scene state.

### Browser diagnostics and UI/API contract gap

A stricter browser diagnostic assertion failed on `no_console_errors` and `no_failed_requests` because the frontend requested a route the server does not implement:

```text
GET http://127.0.0.1:8891/api/store-info → 404 / net::ERR_ABORTED
console: Failed to load resource: the server responded with a status of 404 (Not Found)
```

Source inspection of `.lex/www/js/main.js` shows this is a planned graceful-degradation endpoint:

```text
Contract (GET /api/store-info): { snapshot_at: "<ISO-8601>" }.
If the endpoint 404s the pill hides itself — no-op until W4R3Z ships the endpoint.
```

Classification:

```text
viz UI reachability: runtime-backed
viz core API query/run-and-push/scene: runtime-backed
browser diagnostics: has known failed `/api/store-info` request
UI/API completeness: partial; missing store-info endpoint
production readiness: not proven
```

### Browser evidence summary

Browser validation produced local `.artifacts/browser/` timeline/debug bundles during GSD closeout, but those bundles are local runtime evidence and are intentionally not durable proof anchors. The durable claim retained here is the bounded assertion result: browser UI assertions passed for the local `git-lex viz` page, API fetch proof passed for `/api/query`, `/api/run-and-push`, and `/api/scene`, and diagnostics exposed the known missing `/api/store-info` endpoint.

### T03 verification

- `bg_shell` readiness detected port `8891` and URL `http://127.0.0.1:8891`.
- Browser UI assertions passed.
- Browser API fetch proof passed for `/api/query`, `/api/run-and-push`, and `/api/scene`.
- Browser diagnostics surfaced one known missing endpoint: `/api/store-info`.
- Server was killed and no background processes remain.
- `/root/law-nexus/.lex` remained absent.

## T04: Listen server boundary probe

### Default initialized workspace behavior

Command:

```bash
cd /tmp/m052-s04-serve-co1uhmmh && \
PATH=/root/vendor-source/git-lex/target/debug:$PATH \
/root/vendor-source/git-lex/target/debug/git-lex-serve listen --port 8892
```

Result:

```text
bg_shell process: 83c02696
exit code: 1
stderr: 'listen' is only supported for squad, soul, or lab kits.
```

Cause:

- `git-lex init --kit squad` wrote `kit: repolex-ai/git-lex-kit-squad` to `.lex/repo.yml`.
- Source `cmd_listen` checks for literal substrings `kit: squad`, `kit: soul`, or `kit: lab`.
- Therefore the standard initialized squad workspace is rejected by `listen` even though it is a squad kit workspace.

Classification:

```text
listen after standard `git-lex init --kit squad`: blocked by kit-string mismatch
```

### Short-kit isolated probe

To separate the config bug from the server implementation, T04 copied the workspace to:

```text
/tmp/m052-s04-serve-listen-shortkit
```

and changed only the isolated copy's `.lex/repo.yml` from:

```text
kit: repolex-ai/git-lex-kit-squad
```

to:

```text
kit: squad
```

Command:

```bash
cd /tmp/m052-s04-serve-listen-shortkit && \
PATH=/root/vendor-source/git-lex/target/debug:$PATH \
/root/vendor-source/git-lex/target/debug/git-lex-serve listen --port 8893
```

Result:

```text
bg_shell process: 4bcbf89f
status: ready
git-lex-serve listen started on 127.0.0.1:8893
```

Endpoint probe evidence:

```text
.gsd/exec/93bc741b-6ccd-4b49-9dd0-273a298c8bb3.stdout
```

Probe result:

```text
notify_status= 200
notify_body= {"ok":true}
sse_received= ['data: {"kind":"notify","msg":"m052-s04-listen-proof"}']
sse_errors= []
main_lex_absent= True
```

This proves:

- `/notify` accepts JSON and returns `{ "ok": true }`.
- `/events` emits the posted payload as SSE.
- The implementation works locally when the source's exact kit-string precondition is satisfied.

### Cleanup

The short-kit listen server was killed, and the crashed default-kit process record was also cleared. Final process list:

```text
No background processes.
```

### T04 classification

```text
listen implementation: runtime-backed for local SSE `/events` and JSON `/notify` on an isolated short-kit repo
listen standard init compatibility: blocked by fully-qualified kit string mismatch
listen adoption status: partial; adapter-later until kit detection is fixed or invocation policy is documented
production readiness: not proven
main repository safety: `/root/law-nexus/.lex` absent
```

## T05: Serve, viz, and listen adoption boundary

### Final capability disposition

| Surface | Final S04 classification | Evidence | ACP boundary |
|---|---|---|---|
| `git lex serve ...` CLI path | source-backed pass-through | `src/main.rs` delegates to `git-lex-serve` | CLI wrapper only; server semantics live in binary. |
| `git-lex-serve viz` startup | runtime-backed local smoke | `bg_shell` ready on `127.0.0.1:8891` | Local-only; no production hardening proof. |
| `viz` browser UI | runtime-backed with diagnostics gap | Browser UI assertions passed for `git-lex viz`, navigation modes, connected repo text | Browser-quality claim is partial because `/api/store-info` 404s. |
| `viz` core APIs | runtime-backed | `/api/query`, `/api/run-and-push`, `/api/scene` proof passed | Query/push scene smoke only; no auth/ACL/TLS/CSRF proof. |
| `viz` WebSocket route | source-backed only | `/ws` route traced; no runtime WebSocket assertion in S04 | Not claimed as runtime-backed beyond source. |
| `display` client | source-backed only | `cmd_display` POSTs to `/api/run-and-push`; T03 proved endpoint, not CLI display command | Display command runtime remains for S05 CLI matrix unless separately tested. |
| `listen` standard init compatibility | blocked | Standard `init --kit squad` repo rejected by literal kit-string check | Needs upstream fix or adapter workaround. |
| `listen` SSE/notify implementation | runtime-backed under short-kit config | `/notify` returned `{ "ok": true }`; `/events` received payload | Partial local smoke only. |

### Browser evidence disposition

Browser evidence is sufficient for M052/S04 local UI proof at the assertion-summary level: the local `git-lex viz` page was reached, expected visible UI text was asserted, core API fetches passed, and the known `/api/store-info` diagnostics gap was observed. Local `.artifacts/browser/` bundles are intentionally excluded from durable proof anchors.

However, S04 does **not** satisfy production UI readiness because diagnostics show:

```text
GET /api/store-info -> 404
```

The correct wording is:

```text
git-lex-serve viz is runtime-backed as a local browser/API smoke surface, with a known missing `/api/store-info` route.
```

Unsafe wording:

```text
git-lex-serve viz is production-ready.
```

Unsafe wording:

```text
git-lex browser UI has clean diagnostics.
```

### Durable guidance update

Updated:

```text
.agents/skills/git-lex/references/runtime-adoption-gates.md
```

The guidance now records:

- `viz` local browser/API runtime proof;
- `/api/store-info` UI/API gap;
- `listen` standard init kit-string mismatch;
- `listen` short-kit SSE/notify proof;
- adapter-later/production-not-proven boundary.

### S04 conclusion

S04 upgrades `git-lex-serve viz` from unproven to local runtime-backed for browser UI and core APIs, but with a real diagnostics gap. It upgrades `listen` implementation behavior to partial runtime-backed under a short-kit configuration, while standard initialized squad repos remain blocked by a kit-string mismatch.

Final disposition:

```text
serve/viz: upgraded to local runtime smoke, partial browser diagnostics
listen: partial; implementation works under short-kit config, standard init compatibility blocked
ACP adoption: adapter-later
production readiness: still blocked
main repository safety: preserved; no `/root/law-nexus/.lex`
```
