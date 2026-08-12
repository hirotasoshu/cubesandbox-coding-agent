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

## Credentials

Do not add `~/.codex/auth.json`, OpenCode auth state, API keys, SSH keys, or Git
credentials to this image. Keep authentication state per user and outside the
immutable template.
