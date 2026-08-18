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
repository_url = os.environ["REPOSITORY_URL"]

with Sandbox.create(template, timeout=600) as sandbox:
    upload_test_workspace(sandbox)
    runtime = setup_codex(sandbox)
    sandbox.git.clone(repository_url, path="/workspace/repo", depth=1, user="root")

    result = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --model {model} {runtime.args} "
        "'Add error handling to all API endpoints'",
        cwd="/workspace/repo",
        user="root",
        timeout=600,
        envs=runtime.envs,
        on_stdout=lambda data: print(data, end=""),
    )
    print(f"Workspace: {download_test_workspace(sandbox, 'codex-repository')}")
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
    print(sandbox.commands.run("git diff", cwd="/workspace/repo", user="root").stdout)
