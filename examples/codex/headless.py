#!/usr/bin/env python3
import argparse
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


template = os.environ["CUBE_TEMPLATE_ID"]
model = shlex.quote(os.environ["CODEX_MODEL"])
openai = load_openai_oauth()

with Sandbox.create(template, timeout=600) as sandbox:
    setup = sandbox.commands.run(
        "install -d -m 700 /root/.codex && install -m 600 /dev/null /root/.codex/auth.json",
        user="root",
    )
    if setup.exit_code != 0:
        raise RuntimeError(setup.stderr)
    sandbox.files.write("/root/.codex/auth.json", codex_auth_json(openai), user="root")

    result = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --model {model} "
        "'Create a hello world HTTP server in Go'",
        cwd="/workspace",
        user="root",
        timeout=600,
    )
    print(result.stdout, end="")
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
