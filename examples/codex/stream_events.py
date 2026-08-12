#!/usr/bin/env python3
import argparse
import json
import os
import shlex

from examples.oauth import codex_auth_json, load_openai_oauth


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
openai = load_openai_oauth()

with Sandbox.create(template, timeout=600) as sandbox:
    setup = sandbox.commands.run(
        "install -d -m 700 /root/.codex && install -m 600 /dev/null /root/.codex/auth.json",
        user="root",
    )
    if setup.exit_code != 0:
        raise RuntimeError(setup.stderr)
    sandbox.files.write("/root/.codex/auth.json", codex_auth_json(openai), user="root")
    sandbox.git.clone(repository_url, path="/workspace/repo", depth=1)

    result = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --json --model {model} "
        "'Refactor the utils module into separate files'",
        cwd="/workspace/repo",
        user="root",
        timeout=600,
        on_stdout=print_events,
    )
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
    if buffer.strip():
        event = json.loads(buffer)
        print(f"[{event['type']}] {event}")
