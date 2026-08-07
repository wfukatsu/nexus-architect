#!/usr/bin/env bash
# Backlog delivery dashboard — the Epic -> Sub-Epic -> Issue tree with each item's
# delivery status (todo/doing/review/done/blocked) and its Implemented / Reviewed /
# Merged stages, plus an action menu that generates the slash command to run next.
#
# This is the backlog view of tools/nexus-status.sh, kept under its original name so
# existing docs, skills and habits keep working. Every option is the same; the unified
# tool adds three more views reachable with the Tab key, or directly with
# `nexus-status.sh --view=<name>`: `product` and `architect` (the two pipelines' phase
# progress, one tab each) and `codegen` (the code-generation phases of both).
#
#   tools/backlog-status.sh [PROJECT_DIR] [options]   ==  nexus-status.sh --view=backlog
#
# Run `tools/nexus-status.sh --help` for the full option list.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/nexus-status.sh" --view=backlog "$@"
