#!/usr/bin/env python3
import argparse
import json
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


buffer = ""


def print_events(data: str) -> None:
    global buffer
    buffer += data
    lines = buffer.split("\n")
    buffer = lines.pop()
    for line in lines:
        if line:
            event = json.loads(line)
            print(f"[{event['type']}] {event}")


template = os.environ["CUBE_TEMPLATE_ID"]
model = shlex.quote(os.environ["CODEX_MODEL"])
repository_url = os.environ["REPOSITORY_URL"]

with Sandbox.create(template, timeout=600) as sandbox:
    upload_test_workspace(sandbox)
    runtime = setup_codex(sandbox)
    sandbox.git.clone(repository_url, path="/workspace/repo", depth=1, user="root")

    result = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --json --model {model} {runtime.args} "
        "'Refactor the utils module into separate files'",
        cwd="/workspace/repo",
        user="root",
        timeout=600,
        envs=runtime.envs,
        on_stdout=print_events,
    )
    print(f"Workspace: {download_test_workspace(sandbox, 'codex-stream-events')}")
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
    if buffer.strip():
        event = json.loads(buffer)
        print(f"[{event['type']}] {event}")
