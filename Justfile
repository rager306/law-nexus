# Unified Rust Standard Justfile for law-nexus (Tier 0..3)
set shell := ["bash", "-euo", "pipefail", "-c"]

export CARGO_BUILD_JOBS := env("CARGO_BUILD_JOBS", "4")
export NEXTEST_TEST_THREADS := env("NEXTEST_TEST_THREADS", "4")
# Normalize diagnostic width across interactive PTYs and agents to avoid kache misses
export COLUMNS := "120"

# Opt-in CLIF loop: portable defaults (inside target/ so git status stays clean)
cargo_bin := env("CARGO", "cargo")
clif_toolchain := env("LN_CLIF_TOOLCHAIN", "nightly-2026-08-21")
clif_target := env("LN_CLIF_TARGET_DIR", "target/clif")

CORE_PURE_CRATES := "-p ln-status -p ln-temporal -p ln-identity -p ln-relation -p ln-applicability -p ln-citation -p ln-diagnostic -p ln-gate"

default:
    @just --list

# Opt-in WF-1 turbo test loop: Cranelift + parallel frontend + embed-metadata=no (-32% edit-rebuild, -24% RAM)
# Runs real rustc frontend/borrowck; isolated target/clif + KACHE_DISABLED=1 so 1.99.1 kache stays clean.
test-clif crate="ln-temporal" filter="":
    KACHE_DISABLED=1 RUSTC_WRAPPER="" CARGO_BUILD_RUSTC_WRAPPER="" \
        CARGO_TARGET_DIR="{{clif_target}}" \
        RUSTFLAGS="-Zcodegen-backend=cranelift -Zthreads=4 -Zembed-metadata=no -C link-arg=-fuse-ld=mold" \
        {{cargo_bin}} +{{clif_toolchain}} nextest run -p {{crate}} --lib {{filter}}

# Tier 0 (<10s): fast pre-commit gate
gate-fast crate="":
    cargo fmt --all -- --check
    @if command -v gitleaks >/dev/null 2>&1; then gitleaks protect --staged --no-banner; fi
    @if [ -n "{{crate}}" ]; then \
        cargo clippy -p "{{crate}}" --offline --all-targets --no-deps -- -D warnings; \
    else \
        cargo clippy --workspace --offline --no-deps -- -D warnings; \
    fi
    uv run --frozen python scripts/verify-crate-dependency-allowlist.py
    uv run --frozen python scripts/verify-adr-conformance.py

# Tier 1 (1-5m): pre-push / PR gate
gate:
    cargo fmt --all -- --check
    cargo clippy --workspace --offline --all-targets -- -D warnings
    env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN -u OPENAI_API_KEY -u GOOGLE_APPLICATION_CREDENTIALS \
        cargo nextest run --workspace --offline --profile ci
    cargo deny --offline check -D unsound advisories licenses bans sources
    cargo shear
    # TODO(ci-hardening): remove `|| true` after pinning Actions in repository-quality.yml
    # in lockstep with tests/test_repository_quality_gate.py:138.
    @if [ -d .github/workflows ]; then \
        if command -v actionlint >/dev/null 2>&1; then actionlint; fi; \
        if command -v zizmor >/dev/null 2>&1; then zizmor .github/workflows || true; fi; \
    fi
    uv run --frozen python scripts/verify-crate-dependency-allowlist.py
    uv run --frozen python scripts/verify-adr-conformance.py

# Tier 2: architectural ratchet lint via deslop-please (serialized + cgroup-capped)
arch-lint:
    @command -v deslop-please >/dev/null || { echo "missing deslop-please@0.1.4"; exit 2; }
    @rust-analyzer --version >/dev/null || { echo "missing rust-analyzer component"; exit 2; }
    @if [ -f .deslop-please.allow ]; then \
        rust-heavy-run -- deslop-please --allow .deslop-please.allow; \
    else \
        rust-heavy-run -- deslop-please; \
    fi

arch-lint-ratchet base="HEAD":
    @if [ -f .deslop-please.allow ] && git diff "{{base}}" -- .deslop-please.allow | /usr/bin/grep -Eq '^\+[^+#]'; then \
        echo "ERROR: new entries added to .deslop-please.allow require explicit human review"; \
        exit 1; \
    fi

# Tier 2: composite deep-verification checkpoint (arch-lint + core coverage)
verify: arch-lint cov

# Tier 2: Miri on pure-Rust crates (no SQLite FFI)
miri crate="ln-temporal" filter="":
    rust-heavy-run --no-kache -- cargo +nightly-2026-08-21 miri test -p {{crate}} --lib {{ if filter != "" { "-- " + filter } else { "" } }}

# Tier 2: LLVM coverage summary on pure-Rust core crates (includes tests/ where law-nexus suites live)
cov:
    rust-heavy-run --no-kache -- cargo llvm-cov nextest {{CORE_PURE_CRATES}} --summary-only

# Tier 2: mutation testing on a target crate (uses /srv/rust-build/mutants-tmp, never 16G tmpfs)
mutants crate="ln-temporal" shard="":
    rust-heavy-run --no-kache --mutants-tmp -- cargo mutants -p {{crate}} {{ if shard != "" { "--shard " + shard } else { "" } }} --test-tool=nextest --jobs 4 --timeout 60 --output target

# Tier 2: top monomorphization hogs (compile-time diagnostics)
llvm-lines crate="ln-temporal":
    KACHE_DISABLED=1 RUSTC_WRAPPER="" cargo llvm-lines -p {{crate}} --lib | head -n 25

# Tier 3: auditable release builds + binary audit + CycloneDX 1.5 SBOM (artifacts in target/sbom/)
# Keep the 11 explicit --ignore IDs below in sync with deny.toml until the major-upgrade PR lands.
AUDIT_BASELINE_IGNORES := "--ignore RUSTSEC-2026-0367 --ignore RUSTSEC-2026-0368 --ignore RUSTSEC-2026-0369 --ignore RUSTSEC-2026-0429 --ignore RUSTSEC-2026-0545 --ignore RUSTSEC-2026-0546 --ignore RUSTSEC-2026-0547 --ignore RUSTSEC-2026-0548 --ignore RUSTSEC-2026-0194 --ignore RUSTSEC-2026-0195 --ignore RUSTSEC-2026-0459"

release:
    cargo deny --offline check -D unsound advisories licenses bans sources
    cargo auditable build --release -p ln-status --bin ln-status
    cargo auditable build --release -p ln-product-cli --bin law-nexus-inspect
    cargo audit --no-fetch bin target/release/ln-status
    cargo audit --no-fetch {{AUDIT_BASELINE_IGNORES}} bin target/release/law-nexus-inspect
    mkdir -p target/sbom
    cargo cyclonedx --manifest-path Cargo.toml --format json --spec-version 1.5 --describe binaries
    mv -f crates/ln-status/*.cdx.json crates/ln-product-cli/*.cdx.json target/sbom/
    rm -f crates/*/*.cdx.json
