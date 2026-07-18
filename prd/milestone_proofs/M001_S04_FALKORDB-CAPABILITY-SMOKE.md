# S04 FalkorDB Capability Smoke

## Purpose

This artifact records bounded runtime smoke results for FalkorDB/FalkorDBLite capability claims while preserving the M001 architecture-only boundary. Runtime successes confirm only the synthetic probe behavior listed here; they do not implement LegalGraph ETL/import/product pipeline behavior and do not use legal document contents.

## Capability Findings

| Capability ID | Status | Evidence Class | Owner | Resolution Path | Verification Criteria | Raw Log |
|---|---|---|---|---|---|---|
| `docker-daemon` | confirmed-runtime | confirmed | S04 | Run a bounded Docker availability probe and record daemon/version metadata. | Terminal runtime status with command, exit code, duration, and raw-log reference. | `.gsd/milestones/M001/slices/S04/logs/docker-daemon.log` |
| `docker-falkordb-image` | confirmed-runtime | confirmed | S04 | Inspect/pull the bounded FalkorDB image or record explicit environment blockage. | Terminal image availability status with image/package/version metadata or blocked root cause. | `.gsd/milestones/M001/slices/S04/logs/docker-image-inspect.log` |
| `falkordb-basic-graph` | confirmed-runtime | confirmed | S04 | Start FalkorDB in the bounded smoke environment and execute a synthetic graph create/query/delete probe. | Terminal runtime status with synthetic graph result evidence and cleanup status. | `.gsd/milestones/M001/slices/S04/logs/runtime-probes.log` |
| `falkordb-udf-load-execute` | confirmed-runtime | confirmed | S04 | Run a synthetic JavaScript UDF load/list/execute/flush probe against FalkorDB. | Terminal runtime status proving UDF behavior or naming exact load/execution failure. | `.gsd/milestones/M001/slices/S04/logs/runtime-probes.log` |
| `falkordb-procedure-list` | confirmed-runtime | confirmed | S04 | Query procedure discovery/listing in the target FalkorDB runtime. | Terminal runtime status with procedure evidence or exact unsupported/blocked diagnostic. | `.gsd/milestones/M001/slices/S04/logs/runtime-probes.log` |
| `falkordb-fulltext-node` | confirmed-runtime | confirmed | S04 | Create a synthetic node full-text index and query it through FalkorDB procedures. | Terminal runtime status with expected synthetic rows or exact procedure/index failure. | `.gsd/milestones/M001/slices/S04/logs/runtime-probes.log` |
| `falkordb-vector-node` | confirmed-runtime | confirmed | S04 | Create a synthetic node vector index and query nearest synthetic rows. | Terminal runtime status with expected synthetic vector results or exact procedure/index failure. | `.gsd/milestones/M001/slices/S04/logs/runtime-probes.log` |
| `falkordb-vector-distance` | confirmed-runtime | confirmed | S04 | Evaluate bounded vector distance expressions against synthetic vectors. | Terminal runtime status with expected distance values or exact unsupported/error diagnostic. | `.gsd/milestones/M001/slices/S04/logs/runtime-probes.log` |
| `falkordblite-import` | confirmed-runtime | confirmed | S04 | Install/import FalkorDBLite in an isolated runtime boundary and record package/binary metadata. | Terminal runtime status with import/bootstrap evidence or exact package/binary blocked cause. | `.gsd/milestones/M001/slices/S04/logs/falkordblite-probes.log` |
| `falkordblite-basic-graph` | confirmed-runtime | confirmed | S04 | Run a synthetic embedded FalkorDBLite graph create/query/delete probe if bootstrap succeeds. | Terminal runtime status with embedded graph evidence or exact unavailable-module diagnostic. | `.gsd/milestones/M001/slices/S04/logs/falkordblite-probes.log` |
| `falkordblite-udf` | confirmed-runtime | confirmed | S04 | Probe UDF load/list/execute/flush behavior in FalkorDBLite only after embedded module availability is proven. | Terminal runtime status proving embedded UDF behavior or explicit blocked/failure diagnostic. | `.gsd/milestones/M001/slices/S04/logs/falkordblite-probes.log` |
| `falkordblite-vector-fulltext` | confirmed-runtime | confirmed | S04 | Probe FalkorDBLite vector and full-text procedures only after embedded module availability is proven. | Terminal runtime status proving embedded procedure behavior or explicit blocked/failure diagnostic. | `.gsd/milestones/M001/slices/S04/logs/falkordblite-probes.log` |
| `embedding-env` | blocked-environment | smoke-needed | S04 | Record Python package availability, model cache state, CPU/RAM/no-swap assumptions, and download boundaries. | Terminal environment status with package/cache metadata and no product embedding overclaim. | `.gsd/milestones/M001/slices/S04/logs/embedding-probes.log` |
| `embedding-cpu-tiny` | blocked-environment | smoke-needed | S04 | Run only a bounded tiny/cached CPU embedding smoke if dependencies and model cache permit it. | Terminal runtime status with duration/resource evidence or explicit package/cache blocked cause. | `.gsd/milestones/M001/slices/S04/logs/embedding-probes.log` |

## Runtime Boundary

The Docker harness uses only synthetic graph data and bounded local environment metadata. Docker daemon, image, container, and client failures are environment blockers; source/docs evidence is not upgraded to runtime proof, and bounded non-Docker capabilities remain non-product-proven unless a dedicated runtime probe executes.

## Command Summary

| Phase | Command | Duration (s) | Exit Code | Timed Out | Log |
|---|---|---:|---:|---|---|
| falkordblite-venv-create | `/root/law-nexus/.venv/bin/python3 -m venv /tmp/s04-falkordb-smoke-aywmlkks/falkordblite-venv` | 1.76 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/falkordblite-venv-create.log` |
| falkordblite-install | `/tmp/s04-falkordb-smoke-aywmlkks/falkordblite-venv/bin/python -m pip install /root/vendor-source/falkordblite` | 44.569 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/falkordblite-install.log` |
| falkordblite-probes | `/tmp/s04-falkordb-smoke-aywmlkks/falkordblite-venv/bin/python /tmp/s04-falkordb-smoke-aywmlkks/falkordblite_probes.py` | 26.473 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/falkordblite-probes.log` |
| embedding-probes | `/root/law-nexus/.venv/bin/python3 /tmp/s04-falkordb-smoke-aywmlkks/embedding_probes.py` | 0.019 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/embedding-probes.log` |
| docker-daemon | `docker version --format {{json .}}` | 0.027 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/docker-daemon.log` |
| docker-image-inspect | `docker image inspect falkordb/falkordb:edge --format {{json .}}` | 0.05 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/docker-image-inspect.log` |
| client-venv-create | `/root/law-nexus/.venv/bin/python3 -m venv /tmp/s04-falkordb-smoke-aywmlkks/venv` | 1.854 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/client-venv-create.log` |
| client-install | `/tmp/s04-falkordb-smoke-aywmlkks/venv/bin/python -m pip install /root/vendor-source/falkordb-py` | 38.419 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/client-install.log` |
| container-start | `docker run -d --name s04-falkordb-smoke-26e0d2f6331d -p 127.0.0.1:56929:6379 falkordb/falkordb:edge` | 0.28 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/container-start.log` |
| runtime-probes | `/tmp/s04-falkordb-smoke-aywmlkks/venv/bin/python /tmp/s04-falkordb-smoke-aywmlkks/runtime_probes.py` | 0.222 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/runtime-probes.log` |
| cleanup-1 | `docker rm -f s04-falkordb-smoke-26e0d2f6331d` | 0.337 | 0 | False | `.gsd/milestones/M001/slices/S04/logs/cleanup-1.log` |

## Environment Metadata

| Field | Value |
|---|---|
| Docker daemon | confirmed-runtime |
| FalkorDB image | {"created": "2026-05-07T16:02:18.677785772Z", "id": "sha256:4246e809a5fd74d233196e08c879885adc47bde499a8e25fa5ff83fd39644d80", "image": "falkordb/falkordb:edge", "repo_digests": ["falkordb/falkordb@sha256:4246e809a5fd74d233196e08c879885adc47bde499a8e25fa5ff83fd39644d80"]} |
| FalkorDB package | "/root/vendor-source/falkordb-py" |
| FalkorDBLite package | {"falkordb_module": "/tmp/s04-falkordb-smoke-aywmlkks/falkordblite-venv/lib/python3.13/site-packages/redislite/bin/falkordb.so", "redis_executable": "/tmp/s04-falkordb-smoke-aywmlkks/falkordblite-venv/lib/python3.13/site-packages/redislite/bin/redis-server", "redis_server_version": "8.6.2", "redislite_version": "0.0.0"} |
| sentence-transformers / torch packages | {"sentence_transformers": false, "torch": false, "transformers": false} |
| Embedding model cache | {"checked": ["/root/.cache/huggingface/hub/models--deepvk--USER-bge-m3"], "model_id": "deepvk/USER-bge-m3", "present": false} |
| JSON artifact | `prd/milestone_proofs/M001_S04_FALKORDB-CAPABILITY-SMOKE.json` |

## Cleanup Status

cleanup ok: docker rm -f s04-falkordb-smoke-26e0d2f6331d; temporary workspace removed: /tmp/s04-falkordb-smoke-aywmlkks

## Failure Diagnostics

| Capability ID | Root Cause | Detail |
|---|---|---|
| `docker-daemon` | docker-daemon-ok | Docker CLI reached the daemon and returned version metadata. |
| `docker-falkordb-image` | docker-falkordb-image-ok | Image falkordb/falkordb:edge is available locally or was pulled successfully. |
| `falkordb-basic-graph` | falkordb-basic-graph-ok | synthetic graph query returned [[1]] |
| `falkordb-udf-load-execute` | falkordb-udf-load-execute-ok | udf list=[['library_name', 's04lib', 'functions', ['my_add']]]; execution rows=[[8]] |
| `falkordb-procedure-list` | falkordb-procedure-list-ok | procedure listing returned 5 rows |
| `falkordb-fulltext-node` | falkordb-fulltext-node-ok | fulltext index created=1.0; indices=[['Doc', ['body'], OrderedDict({'body': ['FULLTEXT']}), OrderedDict({'body': OrderedDict()}), 'english', [], 'NODE', 'OPERATIONAL', OrderedDict({'gcPolicy': 0, 'score': 1.0, 'lang': 'english', 'fields': [OrderedDict({'path': 'body', 'name': 'body', 'options': 0, 'textWeight': 1.0, 'tagCaseSensitive': False}), OrderedDict({'path': 'NONE_INDEXABLE_FIELDS', 'name': 'NONE_INDEXABLE_FIELDS', 'options': 0, 'textWeight': 0.0, 'tagCaseSensitive': True})], 'numDocuments': 1, 'maxDocId': 1, 'docTableSize': 74, 'sortablesSize': 0, 'docTrieSize': 29, 'numTerms': 6, 'numRecords': 6, 'invertedSize': 36, 'invertedCap': 0, 'skipIndexesSize': 0, 'scoreIndexesSize': 0, 'offsetVecsSize': 6, 'offsetVecRecords': 6, 'termsSize': 38, 'indexingFailures': 0, 'totalCollected': 0, 'numCycles': 0, 'totalMSRun': 0, 'lastRunTimeMs': 0})]] |
| `falkordb-vector-node` | falkordb-vector-node-ok | vector index created=1.0; indices=[['Embedding', ['vec'], OrderedDict({'vec': ['VECTOR']}), OrderedDict({'vec': OrderedDict({'dimension': 4, 'similarityFunction': 'euclidean', 'M': 16, 'efConstruction': 200, 'efRuntime': 10})}), 'english', [], 'NODE', 'OPERATIONAL', OrderedDict({'gcPolicy': 0, 'score': 1.0, 'lang': 'english', 'fields': [OrderedDict({'path': 'vector:vec', 'name': 'vector:vec', 'options': 0, 'textWeight': 0.0, 'tagCaseSensitive': False}), OrderedDict({'path': 'NONE_INDEXABLE_FIELDS', 'name': 'NONE_INDEXABLE_FIELDS', 'options': 0, 'textWeight': 0.0, 'tagCaseSensitive': True})], 'numDocuments': 0, 'maxDocId': 0, 'docTableSize': 0, 'sortablesSize': 0, 'docTrieSize': 0, 'numTerms': 0, 'numRecords': 0, 'invertedSize': 0, 'invertedCap': 0, 'skipIndexesSize': 0, 'scoreIndexesSize': 0, 'offsetVecsSize': 0, 'offsetVecRecords': 0, 'termsSize': 0, 'indexingFailures': 0, 'totalCollected': 0, 'numCycles': 0, 'totalMSRun': 0, 'lastRunTimeMs': 0})]] |
| `falkordb-vector-distance` | falkordb-vector-distance-ok | vecf32 synthetic vector returned [1.0, 2.0, 3.0, 4.0] |
| `falkordblite-import` | falkordblite-import-ok | import ok with embedded binaries: {'redislite_version': '0.0.0', 'redis_executable': '/tmp/s04-falkordb-smoke-aywmlkks/falkordblite-venv/lib/python3.13/site-packages/redislite/bin/redis-server', 'falkordb_module': '/tmp/s04-falkordb-smoke-aywmlkks/falkordblite-venv/lib/python3.13/site-packages/redislite/bin/falkordb.so', 'redis_server_version': '8.6.2'} |
| `falkordblite-basic-graph` | falkordblite-basic-graph-ok | synthetic embedded graph query returned [[2]] |
| `falkordblite-udf` | falkordblite-udf-ok | udf load='OK'; rows=[[11]] |
| `falkordblite-vector-fulltext` | falkordblite-vector-fulltext-ok | fulltext=1.0; vector=1.0; indices=[['Embedding', ['vec'], OrderedDict({'vec': ['VECTOR']}), OrderedDict({'vec': OrderedDict({'dimension': 4, 'similarityFunction': 'euclidean', 'M': 16, 'efConstruction': 200, 'efRuntime': 10})}), 'english', [], 'NODE', 'OPERATIONAL', OrderedDict({'gcPolicy': 0, 'score': 1.0, 'lang': 'english', 'fields': [OrderedDict({'path': 'vector:vec', 'name': 'vector:vec', 'options': 0, 'textWeight': 0.0, 'tagCaseSensitive': False}), OrderedDict({'path': 'NONE_INDEXABLE_FIELDS', 'name': 'NONE_INDEXABLE_FIELDS', 'options': 0, 'textWeight': 0.0, 'tagCaseSensitive': True})], 'numDocuments': 0, 'maxDocId': 0, 'docTableSize': 0, 'sortablesSize': 0, 'docTrieSize': 0, 'numTerms': 0, 'numRecords': 0, 'invertedSize': 0, 'invertedCap': 0, 'skipIndexesSize': 0, 'scoreIndexesSize': 0, 'offsetVecsSize': 0, 'offsetVecRecords': 0, 'termsSize': 0, 'indexingFailures': 0, 'totalCollected': 0, 'numCycles': 0, 'totalMSRun': 0, 'lastRunTimeMs': 0})], ['Doc', ['body'], OrderedDict({'body': ['FULLTEXT']}), OrderedDict({'body': OrderedDict()}), 'english', [], 'NODE', 'OPERATIONAL', OrderedDict({'gcPolicy': 0, 'score': 1.0, 'lang': 'english', 'fields': [OrderedDict({'path': 'body', 'name': 'body', 'options': 0, 'textWeight': 1.0, 'tagCaseSensitive': False}), OrderedDict({'path': 'NONE_INDEXABLE_FIELDS', 'name': 'NONE_INDEXABLE_FIELDS', 'options': 0, 'textWeight': 0.0, 'tagCaseSensitive': True})], 'numDocuments': 0, 'maxDocId': 0, 'docTableSize': 0, 'sortablesSize': 0, 'docTrieSize': 0, 'numTerms': 0, 'numRecords': 0, 'invertedSize': 0, 'invertedCap': 0, 'skipIndexesSize': 0, 'scoreIndexesSize': 0, 'offsetVecsSize': 0, 'offsetVecRecords': 0, 'termsSize': 0, 'indexingFailures': 0, 'totalCollected': 0, 'numCycles': 0, 'totalMSRun': 0, 'lastRunTimeMs': 0})]] |
| `embedding-env` | embedding-packages-missing | Missing Python packages for local embedding smoke: ['sentence_transformers', 'torch', 'transformers']; cache={'checked': ['/root/.cache/huggingface/hub/models--deepvk--USER-bge-m3'], 'model_id': 'deepvk/USER-bge-m3', 'present': False} |
| `embedding-cpu-tiny` | embedding-packages-missing | Optional tiny CPU encode skipped because sentence-transformers/torch are not importable. |

## Verification

```bash
uv run python scripts/verify-s04-falkordb-smoke.py --require-runtime-results
```
