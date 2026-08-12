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


template = os.environ["CUBE_TEMPLATE_ID"]
model = shlex.quote(os.environ["CODEX_MODEL"])
repository_url = os.environ["REPOSITORY_URL"]
openai = load_openai_oauth()
schema = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "number"},
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                    "description": {"type": "string"},
                },
                "required": ["file", "severity", "description"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["issues"],
    "additionalProperties": False,
}

with Sandbox.create(template, timeout=600) as sandbox:
    setup = sandbox.commands.run(
        "install -d -m 700 /root/.codex && install -m 600 /dev/null /root/.codex/auth.json",
        user="root",
    )
    if setup.exit_code != 0:
        raise RuntimeError(setup.stderr)
    sandbox.files.write("/root/.codex/auth.json", codex_auth_json(openai), user="root")
    sandbox.files.write("/workspace/schema.json", json.dumps(schema), user="root")
    sandbox.git.clone(repository_url, path="/workspace/repo", depth=1)

    result = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --model {model} "
        "--output-schema /workspace/schema.json "
        "'Review this codebase for security issues'",
        cwd="/workspace/repo",
        user="root",
        timeout=600,
    )
    if result.exit_code != 0:
        raise RuntimeError(result.stderr)
    print(json.dumps(json.loads(result.stdout)["issues"], indent=2))
