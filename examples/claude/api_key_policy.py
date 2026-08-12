#!/usr/bin/env python3
import os
import shlex

from cubesandbox import Action, Inject, Match, Rule, Sandbox


template = os.environ["CUBE_TEMPLATE_ID"]
model = shlex.quote(os.environ["CLAUDE_MODEL"])
api_key = os.environ["ANTHROPIC_API_KEY"]
host = "api.anthropic.com"
rules = [
    Rule(
        name="claude_anthropic_api_key",
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
            inject=[Inject(header="x-api-key", secret=api_key)],
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
        "claude --bare --dangerously-skip-permissions --print "
        f"--model {model} "
        "'Reply with one short sentence confirming connectivity'",
        cwd="/workspace",
        user="agent",
        timeout=600,
        envs={
            "ANTHROPIC_API_KEY": "sk-ant-placeholder-not-a-real-key",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "NODE_EXTRA_CA_CERTS": "/etc/ssl/certs/ca-certificates.crt",
        },
    )
    print(result.stdout, end="")
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
