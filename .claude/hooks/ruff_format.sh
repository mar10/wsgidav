#!/usr/bin/env bash
# PostToolUse hook: format and sort imports in Python files edited by Claude Code.
# Only import sorting is auto-fixed (not F401), so an import added before its
# first use survives.
# Non-blocking: always exits 0.
file=$(jq -r '.tool_input.file_path // empty')
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
case "$file" in
  "$PWD"/wsgidav/*.py | "$PWD"/tests/*.py | wsgidav/*.py | tests/*.py)
    uv run --quiet ruff format --quiet "$file" >&2
    uv run --quiet ruff check --fix --select I --quiet "$file" >&2
    ;;
esac
exit 0
