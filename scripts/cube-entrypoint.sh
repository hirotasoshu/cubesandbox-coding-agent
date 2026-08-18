#!/bin/sh
set -eu

DOCKER_LOG_FILE="${DOCKER_LOG_FILE:-/var/log/dockerd.log}"

if [ "${DOCKER_ENABLED:-true}" != "false" ]; then
    mkdir -p "$(dirname "${DOCKER_LOG_FILE}")"
    dockerd >>"${DOCKER_LOG_FILE}" 2>&1 &
    DOCKER_PID=$!
    echo "cube-entrypoint: started dockerd (pid=${DOCKER_PID})" >&2

    attempts=0
    until docker info >/dev/null 2>&1; do
        if ! kill -0 "${DOCKER_PID}" 2>/dev/null; then
            echo "cube-entrypoint: dockerd exited during startup" >&2
            tail -50 "${DOCKER_LOG_FILE}" >&2 || true
            exit 1
        fi
        attempts=$((attempts + 1))
        if [ "${attempts}" -ge 30 ]; then
            echo "cube-entrypoint: dockerd did not become ready within 30 seconds" >&2
            tail -50 "${DOCKER_LOG_FILE}" >&2 || true
            exit 1
        fi
        sleep 1
    done
fi

exec /usr/local/bin/cube-entrypoint-base.sh "$@"
