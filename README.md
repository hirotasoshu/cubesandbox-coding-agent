# CubeSandbox Coding Agent

Public CubeSandbox template image with:

- CubeSandbox `envd`
- OpenAI Codex CLI
- OpenCode CLI
- Node.js 24
- Python 3
- Git, Git LFS, GitHub-friendly SSH tooling
- common build and repository inspection utilities

The image contains no credentials. Mount or inject per-user Codex/OpenCode
authentication state when a sandbox is created.

## Image

```text
ghcr.io/hirotasoshu/cubesandbox-coding-agent:latest
```

## CubeSandbox template

```bash
cubemastercli tpl create-from-image \
  --image ghcr.io/hirotasoshu/cubesandbox-coding-agent:latest \
  --writable-layer-size 10G \
  --expose-port 49983 \
  --expose-port 4096 \
  --expose-port 4500 \
  --probe 49983 \
  --probe-path /health
```

Ports `4096` and `4500` are reserved for OpenCode server and Codex app-server
experiments. They are not started by default. `envd` remains the inherited
entrypoint on port `49983`.

## Local verification

```bash
docker build -t cubesandbox-coding-agent .
docker run --rm cubesandbox-coding-agent coding-agent-smoke
```

With a registered template and Cube API environment variables configured:

```bash
python scripts/verify-template.py
```

## Credentials

Do not add `~/.codex/auth.json`, OpenCode auth state, API keys, SSH keys, or Git
credentials to this image. Keep authentication state per user and outside the
immutable template.

## Codex and OpenCode examples

The Python examples run both agents with ChatGPT OAuth inside the registered
template. Model names remain local configuration rather than repository data:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

export CUBE_API_URL=http://<cube-api-host>:3000
export CUBE_PROXY_NODE_IP=<cube-proxy-node-ip>
export CUBE_TEMPLATE_ID=<template-id>
export CODEX_MODEL=<codex-model>
export OPENCODE_MODEL=<provider/model>

python examples/codex/one_shot.py
python examples/codex/pause_resume.py
python examples/opencode/one_shot.py
python examples/opencode/pause_resume.py
```

The examples enable each agent's unattended execution mode because the agent
already runs inside an isolated CubeSandbox microVM. Do not reuse these command
flags directly on a host machine.

The host must already be logged into OpenCode with OpenAI OAuth. The examples
read the OpenAI entry from `~/.local/share/opencode/auth.json` and upload a
minimal runtime credential through Cube's Files API. Both agents receive the
current access token and account ID, but no refresh token. Refresh the host
OpenCode login before running an example if the access token is near expiry.

CubeSandbox SDK 0.6.0 uploads Files API payloads over the HTTP data plane. Run
these drivers only across a trusted private network, or protect the data-plane
connection with a TLS tunnel. Do not send OAuth credentials over an untrusted
network.

Inside the microVM, credential directories use mode `0700` and files use mode
`0600`. The driver never includes credentials in the image, repository,
command-line arguments, environment variables, or its own output. The agent can
read its runtime credential inside the VM, so only run trusted prompts and code;
agent output is streamed without redaction. A paused sandbox snapshot contains
the staged access token, so always destroy snapshots when they are no longer
needed.

Run the local conversion tests with:

```bash
python -m unittest discover -s tests
```
