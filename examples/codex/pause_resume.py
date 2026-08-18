#!/usr/bin/env python3
import argparse
import json
import os
import shlex
import sys

from examples.provider import setup_codex
from examples.workspace import download_test_workspace, upload_test_workspace


parser = argparse.ArgumentParser()
parser.add_argument("--dev-sidecar", action="store_true")
args = parser.parse_args()
if args.dev_sidecar:
    from examples.dev_sidecar import setup_dev_sidecar

    setup_dev_sidecar()

from e2b import Sandbox


template = os.environ["CUBE_TEMPLATE_ID"]
model = shlex.quote(os.environ["CODEX_MODEL"])

sandbox = Sandbox.create(template, timeout=600)
resumed = None
try:
    upload_test_workspace(sandbox)
    runtime = setup_codex(sandbox)

    first = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --json --model {model} {runtime.args} "
        "'Create plan.md with a 3-step plan for a TODO CLI app'",
        cwd="/workspace",
        user="root",
        timeout=600,
        envs=runtime.envs,
    )
    if first.exit_code != 0:
        raise RuntimeError(first.stderr)
    events = [json.loads(line) for line in first.stdout.splitlines() if line]
    thread_id = next(event["thread_id"] for event in events if event["type"] == "thread.started")

    sandbox_id = sandbox.sandbox_id
    sandbox.pause()
    resumed = Sandbox.connect(sandbox_id)

    second = resumed.commands.run(
        f"codex exec resume {shlex.quote(thread_id)} "
        "--dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "
        f"--model {model} {runtime.args} 'Now implement step 1 of the plan'",
        cwd="/workspace",
        user="root",
        timeout=600,
        envs=runtime.envs,
    )
    print(second.stdout, end="")
    print(f"Workspace: {download_test_workspace(resumed, 'codex-pause-resume')}")
    if second.exit_code != 0:
        raise RuntimeError(second.stderr)

    print(resumed.files.read("/workspace/plan.md", user="root"))
finally:
    try:
        (resumed or sandbox).kill()
    except Exception as cleanup_error:
        print(f"Sandbox cleanup failed: {cleanup_error}", file=sys.stderr)
        raise
