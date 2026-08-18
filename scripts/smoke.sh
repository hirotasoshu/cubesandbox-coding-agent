#!/usr/bin/env bash
set -euo pipefail

codex --version
opencode --version
dsh --help >/dev/null
docker --version
dockerd --version
node --version
python3 --version
git --version
rg --version | sed -n '1p'

test -x /usr/bin/envd
test -x /usr/local/bin/cube-entrypoint-base.sh
test "$(jq -r '."storage-driver"' /etc/docker/daemon.json)" = vfs
test "${CODEX_HOME:-/root/.codex}" = /root/.codex
id agent >/dev/null
runuser -u agent -- test -w /workspace
runuser -u agent -- env HOME=/home/agent claude --version
