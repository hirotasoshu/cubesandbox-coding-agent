#!/usr/bin/env python3
from __future__ import annotations

import os
import time

from e2b import Sandbox


template_id = os.environ["CUBE_TEMPLATE_ID"]

with Sandbox.create(template=template_id, timeout=300) as sandbox:
    print(f"sandbox_id={sandbox.sandbox_id}")

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

    try:
        time.sleep(4)
        listeners = sandbox.commands.run(
            "ss -lnt | grep -E ':(4096|4500) ' && "
            "curl -fsS -u opencode:smoke "
            "http://127.0.0.1:4096/global/health",
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

    print("AGENT_SERVERS_OK")
