# Evidence — stack

<!-- Written by one researcher role. Consumed by the decider. -->

Dimension: stack
Questions assigned: Corpus delivery path for the strict corpus job: self-hosted runner with attached data vs reproducible delivery of a pinned corpus snapshot. Needed before any strict corpus claim; not blocking M001.

## Finding: the corpus is measured, not assumed — 3.53 GiB uncompressed, 0.30 GiB compressed

- **Claim**: The full corpus at `consru_export/consru_export/exports/` is exactly 43,785 XML files and 3,789,431,364 bytes (3.53 GiB); a `tar | zstd -T0 -3` archive of the same tree is 318,488,887 bytes (0.30 GiB, 11.9× compression). Local disk free on the volume holding the repo was 15.3 GiB at scan time (the dispatch brief said ~27 GB; measured 15.3 GiB on 2026-10-26).
- **Source**: local measurement in this session (`os.walk` size sum over `/root/law-nexus/consru_export/consru_export/exports`; `shutil.disk_usage`; archive built at `/tmp/consru_exports.tar.zst`, not written into the repo)
- **Confidence**: high
- **Why it matters here**: every delivery channel below is judged against these two measured numbers, and INTENT's risk "the corpus is absent locally" becomes a sizing question with a concrete answer.

## Finding: GitHub documents that self-hosted runners "should almost never be used" on public repositories — and this repository is public

- **Claim**: GitHub's security-hardening docs state: "self-hosted runners should almost never be used for public repositories on GitHub, because any user can open pull requests against the repository and compromise the environment." The origin repo `rager306/law-nexus` is public (unauthenticated GitHub API returns 200 with `private: false`, `allow_forking: true`), so option (a) as naively configured is the documented dangerous configuration.
- **Source**: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions (opened 2026-10-26); https://api.github.com/repos/rager306/law-nexus (unauthenticated, 200)
- **Confidence**: high
- **Why it matters here**: the runner-with-attached-data path must either restrict execution to protected branches/ephemeral, secret-free runners, or it contradicts the fail-closed security posture INTENT records for CI (M207 batteries are report-only precisely because CI inputs are untrusted).

## Finding: the corpus is deliberately kept off GitHub's surface, and every hosted delivery surface would publish it on a public repo

- **Claim**: `.gitignore` lines 149–152 exclude `consru_export.zip`, `*.zip`, and `consru_export/`, while the repository is public; therefore a release asset, a public GHCR image, or LFS objects on that repo would make all 43,785 commercial-format legal XML documents downloadable by anyone. Private-surface alternatives (private GHCR package) require authentication in CI and, on the GitHub Free plan, fit within a 500 MB storage / 1 GB monthly transfer quota (compressed snapshot: 318 MB).
- **Source**: `/root/law-nexus/.gitignore` lines 149–152; https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases ("Anyone with read access to a repository can view..."); https://docs.github.com/billing/managing-billing-for-github-packages/about-billing-for-github-packages (Free plan quota table)
- **Confidence**: high
- **Why it matters here**: INTENT asks for "reproducible delivery of a pinned corpus snapshot" without settling who may download it; the decider needs this exposure fork — public publish vs private-surface vs runner-only — before any channel choice, and it is likely a `NEEDS-USER` ruling on exposure. (Mechanics are high-confidence; the licensing/exposure weight is an inference from repo structure, not a documented project rule.)

## Finding: a pinned snapshot fits every GitHub-hosted channel with measured headroom — release assets, cache, and container layers

- **Claim**: Release assets allow up to 1,000 assets per release, each file under 2 GiB, with no total release-size or bandwidth limit — the 0.30 GiB zstd snapshot fits with ~6× headroom and is the only hosted channel that is naturally pinned (tag + asset + recorded sha256). Actions cache allows 10 GB per repository by default (eviction LRU, entries untouched >7 days removed, limit raisable by admins with billing beyond 10 GB) and supports restoring a default-branch-created cache into PR-triggered workflows. The Container registry allows 10 GB per layer with a 10-minute upload timeout, and public packages are free.
- **Source**: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases; https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching; https://github.blog/changelog/2025-11-20-github-actions-cache-size-can-now-exceed-10-gb-per-repository; https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- **Confidence**: high
- **Why it matters here**: the reproducible-snapshot path is not blocked by any platform limit once the corpus is compressed; the constraint is exposure (previous finding), not capacity.

## Finding: a cache is an evictable accelerator, not a reproducible delivery channel

- **Claim**: Cache entries are evicted least-recently-used when the repository is over its limit and are deleted after 7 days without access; caches are also immutable per key but restorable via `restore-keys` prefixes, which can silently deliver a different snapshot version than the one a strict claim assumes. A corpus carried only in a cache can therefore vanish or silently change; a strict job must treat cache-restore as best-effort and verify a recorded checksum after restore.
- **Source**: https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching (Default limits; eviction; cache access/scoping sections)
- **Confidence**: high
- **Why it matters here**: INTENT's prohibition N1 pattern (a green run that did not prove what it claims) would extend naturally to a cache-only delivery that silently downgraded to skip or ran against a stale snapshot.

## Finding: GitHub-hosted runners have 14 GB SSD total disk — tight but sufficient for the strict job's measured inputs

- **Claim**: The standard `ubuntu-latest` runner is specified as 4 vCPU / 16 GB RAM / 14 GB SSD; the strict corpus job needs the repo checkout, the 3.53 GiB uncompressed corpus (0.30 GiB compressed before extraction), and a Rust build of `ln-consultant-parser` plus dependencies within that disk. Larger hosted runners offer "more RAM, CPU, and disk space" as paid options.
- **Source**: https://docs.github.com/en/actions/reference/github-hosted-runners-reference (spec tables); larger-runners summary on the same page
- **Confidence**: high
- **Why it matters here**: rules out dismissing option (b) on disk grounds; also bounds what the strict job may build — a full `--workspace` battery on 14 GB would need cache hygiene that the current job (single `-p ln-consultant-parser`, two test targets) already respects.

## Finding: the current job cannot route to a self-hosted runner at all — `ubuntu-latest` is a GitHub-hosted label

- **Claim**: The `corpus-integration` job declares `runs-on: ubuntu-latest` (workflow line 220) under a comment claiming "A self-hosted runner with the corpus mounted sets LAW_NEXUS_CORPUS_AVAILABLE=1" (lines 216–218). GitHub's docs define `ubuntu-latest` as the GitHub-hosted label and direct self-hosted targeting to labels beginning with `self-hosted` plus custom labels; no documented precedence exists for a self-hosted runner that carries a custom label named `ubuntu-latest` (community discussion #49299 shows the practice without a documented rule). Consequently, setting `vars.LAW_NEXUS_CORPUS_AVAILABLE=1` today turns the job red on a hosted runner with no corpus (strict env hard-fails), and the job never touches a self-hosted runner.
- **Source**: `/root/law-nexus/.github/workflows/repository-quality.yml:210-249`; https://docs.github.com/actions/using-jobs/choosing-the-runner-for-a-job; https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/using-labels-with-self-hosted-runners; https://github.com/orgs/community/discussions/49299
- **Confidence**: high
- **Why it matters here**: this is exactly SC9's "corpus job config matches its comment" residual; whichever delivery path wins, the config must change (explicit self-hosted label/group, or a hosted-fetch path), and until then no strict corpus claim can run anywhere.

## Finding: the strict tests pin the exact on-runner layout any delivery must produce

- **Claim**: `ln_decode::npa_sweep::default_sweep_root()` resolves the corpus to `<repo-root>/<CONSULTANT_EXPORT_DIR or "consru_export">/consru_export/exports/`, and the strict job runs with `LAW_NEXUS_REQUIRE_CORPUS=1`, which makes a missing root a test panic rather than a visible skip. Delivery therefore must materialize that exact tree (or set `CONSULTANT_EXPORT_DIR` to a directory containing `consru_export/exports/`), and can be verified by the tests' own hard-fail behavior.
- **Source**: `/root/law-nexus/crates/ln-decode/src/npa_sweep.rs:885-894`; `/root/law-nexus/crates/ln-consultant-parser/tests/gold_ladder_contract.rs` (`require_corpus`); workflow line 240
- **Confidence**: high
- **Why it matters here**: defines the delivery contract for both options — a runner with attached data must point `CONSULTANT_EXPORT_DIR` at its mount; a snapshot job must extract to this path before `cargo test`.

## Finding: Git LFS is workable only as a single archive blob, and its free quotas are community-documented

- **Claim**: Git LFS per-file limits are 2 GB (GitHub Free/Pro), 4 GB (Team), 5 GB (Enterprise Cloud), so the 0.30 GiB compressed snapshot fits as one LFS object while tracking 43,785 individual XML files through LFS (one pointer file each) is impractical. GitHub Docs do not state the included free storage/bandwidth on the opened page; community discussion records Free/Pro at 10 GiB storage + 10 GiB bandwidth per month (Team/Enterprise 250 GiB each). LFS objects in the public repo are publicly fetchable.
- **Source**: https://docs.github.com/repositories/working-with-files/managing-large-files/about-git-large-file-storage (per-file table); https://github.com/orgs/community/discussions/61362 (quota, secondary); https://github.com/orgs/community/discussions/188694 (quota, secondary)
- **Confidence**: medium
- **Why it matters here**: LFS is a viable private-repo delivery channel (auth-scoped) but not a capacity problem; public-repo LFS inherits the exposure finding. (Per-file limit is high-confidence from primary docs; the quota figures are community-only.)

## Finding: artifacts are quantitatively disqualified as the corpus channel on a Free plan

- **Claim**: Workflow artifacts default to 90-day retention and are capped by plan storage quotas — 500 MB on GitHub Free, 1 GB Pro, 2 GB Team, 50 GB Enterprise Cloud — shared with all other artifacts; the compressed corpus (318 MB) would nearly exhaust a Free account's quota and expire after 90 days, so artifacts cannot serve as a reproducible pinned delivery channel.
- **Source**: https://docs.github.com/en/actions/reference/limits (plan quota table); https://docs.github.com/actions/managing-workflow-runs/removing-workflow-artifacts ("By default, GitHub stores build logs and artifacts for 90 days")
- **Confidence**: high
- **Why it matters here**: removes one option from the (b) family cheaply; artifacts remain useful only for intra-run debugging, matching the INTENT constraint that green CI must not be confused with corpus proof.

## Finding: hosted-minutes cost is neutral in both directions; a self-hosted per-minute charge was announced for private repos only and postponed

- **Claim**: GitHub's billing docs state Actions usage "is free for self-hosted runners and for public repositories that use standard GitHub-hosted runners." A December 2025 changelog reduced hosted-runner prices, and a planned $0.002/minute platform charge for self-hosted runners (private repositories, announced for 2026-03-01) was postponed per third-party tracking; the current billing page still describes self-hosted usage as free.
- **Source**: https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions; https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions; https://runs-on.com/blog/github-self-hosted-runner-fee-2026 (secondary)
- **Confidence**: medium
- **Why it matters here**: the owner's choice between runner-with-data and snapshot delivery is not pushed by Actions billing today, but pricing moved twice in late 2025/2026 — re-check before building cost claims into a decision. (The free-usage statement is primary docs; the postponement rests on a third-party tracker.)

## Assigned questions — answers

- Corpus delivery path for the strict corpus job: self-hosted runner with attached data vs reproducible delivery of a pinned corpus snapshot. Needed before any strict corpus claim; not blocking M001. → **Both paths are technically viable against measured limits; neither is blocked by capacity, and the real forks are security exposure and who may download the corpus.** Evidence: (a) Self-hosted runner with attached data: free to run (billing docs), unlimited local disk where the corpus already lives (3.53 GiB measured here, 15.3 GiB free), but GitHub's own hardening docs say self-hosted runners "should almost never be used" on public repositories like this one — so it is only safe if restricted (protected branches, ephemeral/secret-free runner) — and the current workflow cannot route to it anyway (`runs-on: ubuntu-latest` is a hosted label; the comment and config contradict each other). (b) Reproducible pinned snapshot on hosted runners: the zstd-compressed corpus is 0.30 GiB, fitting every channel with headroom — release asset (2 GiB/file, 1,000 assets, no total limit; naturally pinned by tag + sha256), Actions cache (10 GB/repo, but evictable and restore-keys-mutable — best-effort only), GHCR image (10 GB/layer, public packages free, private needs auth + 500 MB/1 GB Free quota); artifacts (500 MB Free quota, 90-day retention) are disqualified. Every hosted public surface (release asset, public image, LFS) would publish the corpus that `.gitignore` deliberately withholds from a public repo; a private surface or the runner-only path avoids that. The strict tests pin the required on-runner layout (`<root>/consru_export/consru_export/exports/` or `CONSULTANT_EXPORT_DIR`) and hard-fail on absence under `LAW_NEXUS_REQUIRE_CORPUS=1`, so either path is verifiable by the tests themselves. No single source settles the choice; the exposure ruling (public publish vs private surface vs runner-only) is owner-level. Not blocking M001 (per INTENT), which keeps the corpus job skipped.

## Dead ends

- `https://docs.github.com/en/actions/reference/workflows-and-actions/usage-limits-billing-and-administration` — 404 (docs restructured); plan quotas now live at `/en/actions/reference/limits`, which was opened instead.
- `https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-artifacts` (and the `.../actions/reference/workflow-artifacts` variant) — 404; the default 90-day retention statement was found in `/actions/managing-workflow-runs/removing-workflow-artifacts` instead.
- `consru_export.zip` — named in `.gitignore:149` but absent on disk, so its size could not be measured; the compressed-size figure comes from a fresh zstd tarball built in-session.
- GHCR total-image-size limit — no documented total cap found on the billing or container-registry pages (only the per-layer 10 GB limit and 10-minute upload timeout); treat "no total limit" as unverified rather than confirmed.
- `exa` web_fetch on docs.github.com — returned `CRAWL_NOT_FOUND` for the usage-limits URL; `tavily_extract`/`jina read_url` used for all opened pages.
- Documented precedence for a self-hosted runner carrying a custom `ubuntu-latest` label — none found; only community discussion #49299 (question + workaround), no normative rule, hence the config-mismatch finding stops at "cannot route today".
