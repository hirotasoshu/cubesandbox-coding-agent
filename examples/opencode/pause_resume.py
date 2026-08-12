#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cubesandbox import Sandbox

from _common import create_sandbox, kill_sandbox, required_argument, run, stage_auth


MODEL = required_argument("OPENCODE_MODEL")
sandbox = create_sandbox()
resumed = None
try:
    stage_auth(sandbox, "opencode")
    run(
        sandbox,
        f"opencode run --auto --dir /workspace --model {MODEL} "
        "'Create plan.md with one line: first turn complete'",
    )
    sandbox_id = sandbox.sandbox_id
    sandbox.pause(timeout=60)
    print("sandbox_paused=true")

    resumed = Sandbox.connect(sandbox_id)
    run(
        resumed,
        "opencode run --continue --auto --dir /workspace "
        f"--model {MODEL} "
        "'Append a second line to plan.md: resumed turn complete'",
    )
    run(
        resumed,
        "test \"$(sed -n '1p' /workspace/plan.md)\" = 'first turn complete' && "
        "test \"$(sed -n '2p' /workspace/plan.md)\" = 'resumed turn complete'",
    )
    print("OPENCODE_PAUSE_RESUME_OK")
finally:
    kill_sandbox(resumed or sandbox)
