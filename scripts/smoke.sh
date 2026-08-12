#!/usr/bin/env bash
set -euo pipefail

codex --version
opencode --version
node --version
python3 --version
git --version
rg --version | sed -n '1p'

test -x /usr/bin/envd
test "${CODEX_HOME:-}" = /root/.codex
