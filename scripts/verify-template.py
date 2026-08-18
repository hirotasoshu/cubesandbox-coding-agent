#!/usr/bin/env python3
from __future__ import annotations

import os
import time

from e2b import Sandbox


template_id = os.environ["CUBE_TEMPLATE_ID"]

with Sandbox.create(template=template_id, timeout=300) as sandbox:
    result = sandbox.commands.run(
        "coding-agent-smoke && "
        "test ! -e /root/.codex/auth.json && "
        "test ! -e /root/.local/share/opencode/auth.json && "
        "printf 'CREDENTIALS_EMPTY\\n'",
        user="root",
        timeout=120,
    )
    print(result.stdout, end="")
    if result.exit_code != 0:
        print(result.stderr, end="")
        raise SystemExit(result.exit_code)

    codex = sandbox.commands.run(
        "codex app-server --listen ws://127.0.0.1:4500",
        user="root",
        background=True,
        timeout=0,
    )
    opencode = sandbox.commands.run(
        "OPENCODE_SERVER_PASSWORD=smoke "
        "opencode serve --hostname 127.0.0.1 --port 4096",
        user="root",
        background=True,
        timeout=0,
    )
    dsh = sandbox.commands.run(
        "dsh web --host 127.0.0.1 --port 3080",
        cwd="/workspace",
        user="root",
        background=True,
        timeout=0,
    )

    try:
        time.sleep(4)
        listeners = sandbox.commands.run(
            "ss -lnt | grep -E ':(3080|4096|4500) ' && "
            "curl -fsS -u opencode:smoke "
            "http://127.0.0.1:4096/global/health && "
            "curl -fsS http://127.0.0.1:3080/ >/dev/null",
            user="root",
            timeout=30,
        )
        print(listeners.stdout, end="")
        if listeners.exit_code != 0:
            print(listeners.stderr, end="")
            raise SystemExit(listeners.exit_code)
    finally:
        codex.kill()
        opencode.kill()
        dsh.kill()

    print("AGENT_SERVERS_AND_DSH_OK")

    for _ in range(60):
        docker = sandbox.commands.run(
            "docker info --format '{{.Driver}}' 2>/dev/null || true",
            user="root",
            timeout=10,
        )
        if docker.stdout.strip():
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("Docker daemon did not become ready")

    if docker.stdout.strip() != "vfs":
        raise RuntimeError(f"Unexpected Docker storage driver: {docker.stdout!r}")
    container = sandbox.commands.run(
        "docker run --rm alpine:3.20 echo DOCKER_IN_CUBE_OK",
        user="root",
        timeout=180,
    )
    print(container.stdout, end="")
    if container.exit_code != 0:
        print(container.stderr, end="")
        raise SystemExit(container.exit_code)
