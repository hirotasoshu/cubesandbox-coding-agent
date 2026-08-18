# CubeSandbox Coding Agent

Public CubeSandbox template image with:

- CubeSandbox `envd`
- OpenAI Codex CLI
- Anthropic Claude Code CLI
- OpenCode CLI
- DeepSeek Harness (`dsh`)
- Docker Engine configured with the `vfs` storage driver
- Node.js 24
- Python 3
- Git, Git LFS, GitHub-friendly SSH tooling
- common build and repository inspection utilities

The image contains no credentials. Mount or inject per-user agent
authentication state when a sandbox is created.

## Image

```text
ghcr.io/hirotasoshu/cubesandbox-coding-agent:latest
```

## CubeSandbox template

Create all four resource profiles with:

```bash
scripts/create-template-profiles.sh
```

| Alias | CPU | RAM | Writable layer | Intended use |
|---|---:|---:|---:|---|
| `coding-agent-small` | 1 vCPU | 2 GiB | 20 GiB | Lightweight edits and inspection |
| `coding-agent-medium` | 2 vCPU | 4 GiB | 30 GiB | General coding agents |
| `coding-agent-large` | 4 vCPU | 8 GiB | 50 GiB | Docker builds and larger repositories |
| `coding-agent-xlarge` | 6 vCPU | 12 GiB | 80 GiB | Heavy single-sandbox workloads |

Ports `4096` and `4500` are reserved for OpenCode server and Codex app-server.
They are not started by default. `envd` remains available on port `49983`.

Docker starts automatically inside the CubeSandbox MicroVM. Its daemon uses
the `vfs` storage driver because nested `overlay2` is not supported by the
template root filesystem. `vfs` is reliable but consumes more disk, so use the
`large` or `xlarge` profile for substantial image builds.

## Local verification

```bash
docker build -t cubesandbox-coding-agent .
docker run --rm --privileged cubesandbox-coding-agent \
  sh -c 'coding-agent-smoke && docker run --rm alpine:3.20 echo ok'
```

With a registered template and Cube API environment variables configured:

```bash
python scripts/verify-template.py
```

## Credentials

Do not add `~/.codex/auth.json`, Claude Code/OpenCode auth state, API keys, SSH
keys, or Git credentials to this image. Keep authentication state per user and
outside the immutable template. Run Claude Code as the non-root `agent` user;
`/workspace` is writable by that user.

DeepSeek Harness is installed as the pinned `dsh` CLI. Start its Web UI from a
sandbox workspace with `dsh web`. The current developer preview intentionally
binds only to `127.0.0.1` because the UI can execute commands; port `3080` is
therefore not publicly exposed by the templates. Model credentials must be
configured at runtime and are not baked into the image.

## Examples

See [`examples/README.md`](examples/README.md) for the complete agent example
catalog, setup, runnable commands, and security boundaries.
