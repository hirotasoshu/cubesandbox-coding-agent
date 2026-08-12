#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cubesandbox import Sandbox

from _common import create_sandbox, kill_sandbox, required_argument, run, stage_auth


MODEL = required_argument("CODEX_MODEL")
sandbox = create_sandbox()
resumed = None
try:
    stage_auth(sandbox, "codex")
    run(
        sandbox,
        "printf '%s\\n' 'Create plan.md with one line: first turn complete' | "
        "codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "
        f"--model {MODEL} --color never -",
    )
    sandbox_id = sandbox.sandbox_id
    sandbox.pause(timeout=60)
    print("sandbox_paused=true")

    resumed = Sandbox.connect(sandbox_id)
    run(
        resumed,
        "printf '%s\\n' 'Append a second line to plan.md: resumed turn complete' | "
        "codex exec resume --last --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --model {MODEL} -",
    )
    run(
        resumed,
        "test \"$(sed -n '1p' /workspace/plan.md)\" = 'first turn complete' && "
        "test \"$(sed -n '2p' /workspace/plan.md)\" = 'resumed turn complete'",
    )
    print("CODEX_PAUSE_RESUME_OK")
finally:
    kill_sandbox(resumed or sandbox)
