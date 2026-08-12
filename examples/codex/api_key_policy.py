#!/usr/bin/env python3
import os
import shlex

from cubesandbox import Action, Inject, Match, Rule, Sandbox


template = os.environ["CUBE_TEMPLATE_ID"]
model = shlex.quote(os.environ["CODEX_MODEL"])
api_key = os.environ["OPENAI_API_KEY"]
host = "api.openai.com"
rules = [
    Rule(
        name="codex_openai_api_key",
        match=Match(
            scheme="https",
            sni=host,
            host=host,
            method=["GET", "POST"],
            path="/v1/*",
        ),
        action=Action(
            allow=True,
            audit="metadata",
            inject=[
                Inject(
                    header="Authorization",
                    format="Bearer ${SECRET}",
                    secret=api_key,
                )
            ],
        ),
    )
]

with Sandbox.create(
    template=template,
    allow_internet_access=False,
    network={"rules": rules},
    timeout=600,
) as sandbox:
    result = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --model {model} "
        "'Reply with one short sentence confirming connectivity'",
        cwd="/workspace",
        user="root",
        timeout=600,
        envs={"OPENAI_API_KEY": "sk-placeholder-not-a-real-key"},
    )
    print(result.stdout, end="")
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
