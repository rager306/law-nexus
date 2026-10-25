#!/usr/bin/env bash
# Source from Bash. Leaves the interactive shell HOME unchanged.
# The helper validates a shared primary root and native worktree placement.
# Only general project tooling is exported. Existing upstream Prime variables
# are untouched; the Allspark launcher supplies fork overrides to its child.
ai_stack_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if ai_stack_exports="$(python3 -B "$ai_stack_script_dir/stack-env.py" --shell)"; then
    eval "$ai_stack_exports"
    unset ai_stack_script_dir ai_stack_exports
else
    unset ai_stack_script_dir ai_stack_exports
    return 1 2>/dev/null || exit 1
fi
