#!/usr/bin/env python3
import os
import shlex
from urllib.parse import urlsplit

from cubesandbox import Action, Inject, Match, Rule, Sandbox
from examples.provider import load_api_key_provider, setup_opencode


template = os.environ["CUBE_TEMPLATE_ID"]
model = os.environ["OPENCODE_MODEL"]
provider = load_api_key_provider()
if provider is None:
    raise SystemExit("OPENAI_API_KEY is required")
host = provider.host
path = f"{urlsplit(provider.openai_base_url).path.rstrip('/')}/*"
rules = [
    Rule(
        name="opencode_openai_api_key",
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
    runtime = setup_opencode(sandbox, model)
    model = shlex.quote(runtime.model or model)
    result = sandbox.commands.run(
        f"opencode run --auto --model {model} "
        "'Reply with one short sentence confirming connectivity'",
        cwd="/workspace",
        user="root",
        timeout=600,
        envs={
            **(runtime.envs or {}),
            "OPENAI_API_KEY": "sk-placeholder-not-a-real-key",
            "NODE_EXTRA_CA_CERTS": "/etc/ssl/certs/ca-certificates.crt",
        },
    )
    print(result.stdout, end="")
    if result.exit_code != 0:
        raise SystemExit(result.exit_code)
