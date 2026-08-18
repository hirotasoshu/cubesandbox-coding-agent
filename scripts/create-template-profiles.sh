#!/usr/bin/env bash
set -euo pipefail

image="${1:-ghcr.io/hirotasoshu/cubesandbox-coding-agent:latest}"

create_profile() {
    local name="$1"
    local cpu="$2"
    local memory="$3"
    local disk="$4"

    cubemastercli tpl create-from-image \
        --image "${image}" \
        --alias "coding-agent-${name}" \
        --cpu "${cpu}" \
        --memory "${memory}" \
        --writable-layer-size "${disk}" \
        --expose-port 49983 \
        --expose-port 4096 \
        --expose-port 4500 \
        --probe 49983 \
        --probe-path /health
}

create_profile small 1000 2048 20Gi
create_profile medium 2000 4096 30Gi
create_profile large 3000 6144 50Gi
create_profile xlarge 4000 8192 80Gi
