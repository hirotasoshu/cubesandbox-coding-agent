#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import create_sandbox, required_argument, run, stage_auth


PROMPT = "Create hello.txt containing exactly: Hello from Codex in CubeSandbox"
MODEL = required_argument("CODEX_MODEL")


with create_sandbox() as sandbox:
    stage_auth(sandbox, "codex")
    run(
        sandbox,
        "printf '%s\\n' '" + PROMPT + "' | "
        "codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "
        f"--model {MODEL} --color never -",
    )
    run(sandbox, "test \"$(cat /workspace/hello.txt)\" = 'Hello from Codex in CubeSandbox'")
    print("CODEX_ONE_SHOT_OK")
