#!/usr/bin/env python3
import argparse
import os
import shlex

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

with Sandbox.create(template, timeout=600) as sandbox:
    upload_test_workspace(sandbox)
    runtime = setup_codex(sandbox)

    result = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --model {model} {runtime.args} "
        "'Create fibonacci.exs with an idiomatic lazy Fibonacci number generator "
        "in Elixir and a short example that prints the first 10 numbers'",
        cwd="/workspace",
        user="root",
        timeout=600,
        envs=runtime.envs,
    )
    print(result.stdout, end="")
    print(f"Workspace: {download_test_workspace(sandbox, 'codex-headless')}")
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
