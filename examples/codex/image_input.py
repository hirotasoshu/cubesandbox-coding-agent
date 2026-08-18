#!/usr/bin/env python3
import argparse
import os
import shlex
from pathlib import Path

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
mockup_path = Path(os.environ["MOCKUP_PATH"])
remote_mockup_path = f"/workspace/mockup{mockup_path.suffix or '.png'}"

with Sandbox.create(template, timeout=600) as sandbox:
    upload_test_workspace(sandbox)
    runtime = setup_codex(sandbox)
    sandbox.files.write(remote_mockup_path, mockup_path.read_bytes(), user="root")
    sandbox.git.clone(repository_url, path="/workspace/repo", depth=1, user="root")

    result = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --model {model} {runtime.args} "
        "'Implement this UI design as a React component' "
        f"--image {shlex.quote(remote_mockup_path)}",
        cwd="/workspace/repo",
        user="root",
        timeout=600,
        envs=runtime.envs,
        on_stdout=lambda data: print(data, end=""),
    )
    print(f"Workspace: {download_test_workspace(sandbox, 'codex-image-input')}")
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
