#!/usr/bin/env python3
import argparse
import os
import shlex
import sys

from examples.provider import setup_opencode
from examples.workspace import download_test_workspace, upload_test_workspace


parser = argparse.ArgumentParser()
parser.add_argument("--dev-sidecar", action="store_true")
args = parser.parse_args()
if args.dev_sidecar:
    from examples.dev_sidecar import setup_dev_sidecar

    setup_dev_sidecar()

from e2b import Sandbox


template = os.environ["CUBE_TEMPLATE_ID"]
model = os.environ["OPENCODE_MODEL"]

sandbox = Sandbox.create(template, timeout=600)
resumed = None
try:
    upload_test_workspace(sandbox)
    runtime = setup_opencode(sandbox, model)
    model = shlex.quote(runtime.model or model)

    first = sandbox.commands.run(
        f"opencode run --auto --model {model} "
        "'Create plan.md with a 3-step plan for a TODO CLI app'",
        cwd="/workspace",
        user="root",
        timeout=600,
        envs=runtime.envs,
    )
    if first.exit_code != 0:
        raise RuntimeError(first.stderr)

    sandbox_id = sandbox.sandbox_id
    sandbox.pause()
    resumed = Sandbox.connect(sandbox_id)

    second = resumed.commands.run(
        f"opencode run --continue --auto --model {model} "
        "'Now implement step 1 of the plan'",
        cwd="/workspace",
        user="root",
        timeout=600,
        envs=runtime.envs,
    )
    print(second.stdout, end="")
    print(f"Workspace: {download_test_workspace(resumed, 'opencode-pause-resume')}")
    if second.exit_code != 0:
        raise RuntimeError(second.stderr)

    print(resumed.files.read("/workspace/plan.md", user="root"))
finally:
    try:
        (resumed or sandbox).kill()
    except Exception:
        if resumed is not None:
            sandbox.kill()
