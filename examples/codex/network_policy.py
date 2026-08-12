#!/usr/bin/env python3
import os
import shlex

from cubesandbox import Action, Inject, Match, Rule, Sandbox

from examples.oauth import codex_auth_json, load_openai_oauth, placeholder_access_token


template = os.environ["CUBE_TEMPLATE_ID"]
model = shlex.quote(os.environ["CODEX_MODEL"])
openai = load_openai_oauth()
host = "chatgpt.com"
rules = [
    Rule(
        name="codex_chatgpt_oauth",
        match=Match(
            scheme="https",
            sni=host,
            host=host,
            method=["GET", "POST"],
            path="/backend-api/codex/*",
        ),
        action=Action(
            allow=True,
            audit="metadata",
            inject=[
                Inject(
                    header="Authorization",
                    format="Bearer ${SECRET}",
                    secret=openai["access"],
                ),
                Inject(header="ChatGPT-Account-Id", secret=openai["accountId"]),
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
    setup = sandbox.commands.run(
        "install -d -m 700 /root/.codex && install -m 600 /dev/null /root/.codex/auth.json",
        user="root",
    )
    if setup.exit_code != 0:
        raise RuntimeError(setup.stderr)
    sandbox.files.write(
        "/root/.codex/auth.json",
        codex_auth_json(openai, placeholder_access_token(openai)),
        user="root",
    )

    result = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --model {model} "
        "'Reply with one short sentence confirming connectivity'",
        cwd="/workspace",
        user="root",
        timeout=600,
    )
    print(result.stdout, end="")
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
