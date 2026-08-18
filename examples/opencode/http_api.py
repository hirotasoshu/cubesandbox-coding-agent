#!/usr/bin/env python3
import argparse
import os
import secrets
import time
from urllib.parse import urlsplit

import requests
from examples.provider import setup_opencode
from examples.workspace import download_test_workspace, upload_test_workspace


parser = argparse.ArgumentParser()
parser.add_argument("--dev-sidecar", action="store_true")
args = parser.parse_args()
if args.dev_sidecar:
    from examples.dev_sidecar import setup_dev_sidecar

    setup_dev_sidecar()

from e2b import Sandbox


template = os.environ["CUBE_TEMPLATE_ID"]
model = os.environ["OPENCODE_MODEL"]
server_password = secrets.token_urlsafe(32)

with Sandbox.create(template, timeout=600) as sandbox:
    upload_test_workspace(sandbox)
    runtime = setup_opencode(sandbox, model)
    provider_id, model_id = (runtime.model or model).split("/", 1)
    server = sandbox.commands.run(
        "opencode serve --hostname 0.0.0.0 --port 4096",
        cwd="/workspace",
        user="root",
        envs={**(runtime.envs or {}), "OPENCODE_SERVER_PASSWORD": server_password},
        background=True,
    )

    external_sidecar = os.environ.get("CUBE_DEV_PROXY_URL", "")
    scheme = (
        urlsplit(external_sidecar).scheme or "http"
        if args.dev_sidecar
        else os.environ.get("CUBE_PUBLIC_SCHEME", "https")
    )
    if not args.dev_sidecar and scheme != "https":
        raise SystemExit("OpenCode HTTP API requires CUBE_PUBLIC_SCHEME=https")
    base_url = f"{scheme}://{sandbox.get_host(4096)}"
    auth = ("opencode", server_password)
    for _ in range(60):
        try:
            health = requests.get(f"{base_url}/global/health", auth=auth, timeout=2)
            health.raise_for_status()
            break
        except requests.RequestException:
            time.sleep(0.5)
    else:
        server.kill()
        raise RuntimeError("OpenCode server did not become ready")

    session = requests.post(f"{base_url}/session", auth=auth, timeout=10)
    session.raise_for_status()
    response = requests.post(
        f"{base_url}/session/{session.json()['id']}/message",
        json={
            "model": {"providerID": provider_id, "modelID": model_id},
            "parts": [
                {"type": "text", "text": "Create a hello world HTTP server in Go"}
            ],
        },
        auth=auth,
        timeout=600,
    )
    response.raise_for_status()
    print(response.json())
    print(f"Workspace: {download_test_workspace(sandbox, 'opencode-http-api')}")
