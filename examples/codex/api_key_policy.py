#!/usr/bin/env python3
import os
import shlex
from urllib.parse import urlsplit

from cubesandbox import Action, Inject, Match, Rule, Sandbox
from examples.provider import load_api_key_provider, setup_codex


template = os.environ["CUBE_TEMPLATE_ID"]
model = shlex.quote(os.environ["CODEX_MODEL"])
provider = load_api_key_provider()
if provider is None:
    raise SystemExit("OPENAI_API_KEY is required")
host = provider.host
path = f"{urlsplit(provider.openai_base_url).path.rstrip('/')}/*"
rules = [
    Rule(
        name="codex_openai_api_key",
        match=Match(
            scheme="https",
            sni=host,
            host=host,
            method=["GET", "POST"],
            path=path,
        ),
        action=Action(
            allow=True,
            audit="metadata",
            inject=[
                Inject(
                    header="Authorization",
                    format="Bearer ${SECRET}",
                    secret=provider.api_key,
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
    runtime = setup_codex(sandbox)
    result = sandbox.commands.run(
        "codex exec --dangerously-bypass-approvals-and-sandbox "
        f"--skip-git-repo-check --model {model} {runtime.args} "
        "'Reply with one short sentence confirming connectivity'",
        cwd="/workspace",
        user="root",
        timeout=600,
        envs={
            **(runtime.envs or {}),
            "OPENAI_API_KEY": "sk-placeholder-not-a-real-key",
        },
    )
    print(result.stdout, end="")
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
