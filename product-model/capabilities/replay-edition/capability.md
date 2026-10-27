---
availability:
  - place: terminal
references:
  - kind: code
    role: implementation
    target: crates/ln-product-cli/src/main.rs#replay
    title: replay()
---

# Replay edition

Compare two editions of one act: read the hierarchy markers of the seed and
target files, diff the marker sets, turn the diff into attach and detach
drafts plus text-facet drafts, apply the drafts against the target, and verify
by drift, missing, and phantom counters. The report distinguishes an empty
diff from an error; two editions prove the replay mechanics and nothing more.

Missing arguments are a usage error before any file is read.
