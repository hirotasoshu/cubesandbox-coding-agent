#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import create_sandbox, required_argument, run, stage_auth


MODEL = required_argument("OPENCODE_MODEL")


with create_sandbox() as sandbox:
    stage_auth(sandbox, "opencode")
    run(
        sandbox,
        f"opencode run --auto --dir /workspace --model {MODEL} "
        "'Create hello.txt containing exactly: Hello from OpenCode in CubeSandbox'",
    )
    run(sandbox, "test \"$(cat /workspace/hello.txt)\" = 'Hello from OpenCode in CubeSandbox'")
    print("OPENCODE_ONE_SHOT_OK")
