#!/usr/bin/env bash
# Is this install of the toolkit healthy, and is this project readable?
#
#   tools/doctor.sh [project_dir] [format=json]
#
# Checks the repository (marketplace, skills, hooks), the required and optional tools, the
# installed Claude Code plugins against the repository's version, the two knowledge bundles and
# their freshness, and — for a project — the registry, the Open Questions store, the audit log,
# the learned rules and the claims. Exit 0 with no failure (warnings allowed), 1 otherwise.
# The work is tools/lib/doctor.py; this wrapper is what /architect:doctor is allowed to run.
set -euo pipefail
exec python3 "$(cd "$(dirname "$0")" && pwd)/lib/doctor.py" "$@"
