# Coding agent examples

These examples adapt the official E2B Codex and OpenCode guides to the public
CubeSandbox template in this repository. Ordinary sandbox operations use the
E2B-compatible Python API explicitly:

```python
from e2b import Sandbox
```

Only `network_policy.py` and `api_key_policy.py` use the native `cubesandbox`
package because typed CubeEgress rules and credential injection are
Cube-specific.

## Setup

Create a virtual environment and install both SDKs:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Configure your CubeSandbox deployment locally. Keep real values out of this
repository:

```bash
export E2B_API_URL=http://<cube-api-host>:3000
export E2B_API_KEY=<deployment-api-key>
export CUBE_TEMPLATE_ID=<template-id>

# Required by the native network-policy examples.
export CUBE_API_URL="$E2B_API_URL"
export CUBE_API_KEY="$E2B_API_KEY"
export CUBE_PROXY_NODE_IP=<cube-proxy-node-ip>

# Model names stay in local configuration.
export CODEX_MODEL=<codex-model>
export OPENCODE_MODEL=<provider/model>
export CLAUDE_MODEL=<claude-model>

# Required only by the corresponding API-key policy examples.
export OPENAI_API_KEY=<openai-api-key>
export ANTHROPIC_API_KEY=<anthropic-api-key>
```

For an unauthenticated local deployment, use an E2B-shaped development value
and set `E2B_VALIDATE_API_KEY=false`. Never disable validation against a remote
or shared deployment.

`examples/opencode/http_api.py` requires a TLS-enabled CubeProxy public endpoint
and uses a random per-run Basic Auth password. Set `CUBE_PUBLIC_SCHEME=https`
explicitly if needed; plaintext public endpoints are rejected.

## Optional development sidecar

By default, no sidecar is started. The E2B SDK connects through the sandbox
domain returned by CubeAPI, which is the intended setup once wildcard DNS and
TLS are configured.

For local development without that domain setup, pass `--dev-sidecar`. This
starts the embedded proxy adapted from CubeSandbox's official
[`e2b-dev-sidecar`](https://github.com/TencentCloud/CubeSandbox/tree/master/examples/e2b-dev-sidecar)
example and patches E2B data-plane URL construction for the current process.

```bash
export CUBE_REMOTE_PROXY_BASE=https://<cube-proxy-host>:443

# Optional for self-signed development certificates; false is the default.
export CUBE_REMOTE_PROXY_VERIFY_SSL=false

python -m examples.codex.headless --dev-sidecar
python -m examples.opencode.headless --dev-sidecar
```

Optional sidecar settings:

| Variable | Purpose |
|---|---|
| `CUBE_REMOTE_PROXY_BASE` | CubeProxy endpoint receiving forwarded data-plane traffic |
| `CUBE_REMOTE_PROXY_VERIFY_SSL` | Verify CubeProxy TLS; defaults to `false` for local mkcert setups |
| `CUBE_REMOTE_SANDBOX_DOMAIN` | Host suffix sent to CubeProxy; defaults to `cube.app` |
| `CUBE_DEV_PROXY_HOST` | Embedded sidecar listen address; defaults to `127.0.0.1` |
| `CUBE_DEV_PROXY_PORT` | Preferred embedded sidecar port; defaults to `12580` |
| `CUBE_DEV_PROXY_URL` | Use an already-running sidecar instead of starting one |

The flag is available on every E2B-based example in the tables below. It is not
available on the policy examples, which use the native CubeSandbox SDK and
their own `CUBE_PROXY_NODE_IP` transport. The sidecar is development-only and
should be removed from the invocation when the sandbox domain is ready.

Keep the embedded `CUBE_DEV_PROXY_HOST` on its default loopback address. The
sidecar has no authentication and must not be exposed on `0.0.0.0`. An external
`CUBE_DEV_PROXY_URL` must point to a trusted, access-controlled proxy; use HTTPS
when traffic crosses anything other than the local machine.

The host must already have a valid OpenAI OAuth login at
`~/.local/share/opencode/auth.json`. Runtime files contain only the current
access token and account ID, never the refresh token. The scripts reject access
tokens with less than 30 minutes remaining.

Run examples from the repository root with `python -m`, so `examples.oauth`
resolves without modifying `sys.path`:

```bash
python -m examples.codex.headless
```

## Codex

| Example | E2B scenario | Extra input |
|---|---|---|
| `codex/headless.py` | Non-interactive one-shot run | None |
| `codex/repository.py` | Clone a repository, edit it, print `git diff` | `REPOSITORY_URL` |
| `codex/structured_output.py` | Validate the final response with a JSON Schema | `REPOSITORY_URL` |
| `codex/stream_events.py` | Stream and parse Codex JSONL events | `REPOSITORY_URL` |
| `codex/pause_resume.py` | Resume a Codex thread after Cube pause/connect | None |
| `codex/image_input.py` | Upload a mockup and pass it with `--image` | `REPOSITORY_URL`, `MOCKUP_PATH` |
| `codex/network_policy.py` | Native Cube default-deny and on-wire OAuth injection | Native Cube variables above |
| `codex/api_key_policy.py` | Native Cube default-deny and on-wire OpenAI API-key injection | `OPENAI_API_KEY` |

Run them with:

```bash
python -m examples.codex.headless

export REPOSITORY_URL=https://github.com/<owner>/<repository>.git
python -m examples.codex.repository
python -m examples.codex.structured_output
python -m examples.codex.stream_events

python -m examples.codex.pause_resume

export MOCKUP_PATH=./mockup.png
python -m examples.codex.image_input

python -m examples.codex.network_policy
python -m examples.codex.api_key_policy
```

Append `--dev-sidecar` only to E2B-based commands when using the optional
development proxy.

The repository examples intentionally use a public clone URL. For a private
repository, add `GITHUB_TOKEN` locally and pass it to `sandbox.git.clone` as
shown in the official E2B guide; never put a token in `REPOSITORY_URL`.

## OpenCode

| Example | E2B scenario | Extra input |
|---|---|---|
| `opencode/headless.py` | Non-interactive one-shot run | None |
| `opencode/repository.py` | Clone a repository, edit it, print `git diff` | `REPOSITORY_URL` |
| `opencode/http_api.py` | Start `opencode serve` and call its HTTP API | `CUBE_PUBLIC_SCHEME` when needed |
| `opencode/pause_resume.py` | Continue the OpenCode session after Cube pause/connect | None |
| `opencode/network_policy.py` | Native Cube default-deny and on-wire OAuth injection | Native Cube variables above |
| `opencode/api_key_policy.py` | Native Cube default-deny and on-wire OpenAI API-key injection | `OPENAI_API_KEY` |

Run them with:

```bash
python -m examples.opencode.headless

export REPOSITORY_URL=https://github.com/<owner>/<repository>.git
python -m examples.opencode.repository

python -m examples.opencode.http_api
python -m examples.opencode.pause_resume
python -m examples.opencode.network_policy
python -m examples.opencode.api_key_policy
```

Append `--dev-sidecar` only to E2B-based commands when using the optional
development proxy.

## Claude Code

Claude Code runs as the non-root `agent` user because it rejects unattended
permission bypass under root:

```bash
python -m examples.claude.api_key_policy
```

The example uses `--bare` to avoid loading repository-controlled hooks,
plugins, MCP servers, and settings during this connectivity check.

## Security boundaries

- Headless, repository, structured, streaming, resume, image, and HTTP examples
  upload a short-lived OAuth access token to the microVM through the E2B Files
  API. The agent can read that token and has open egress.
- Run direct-token examples only across a trusted private data-plane network or
  a TLS-protected connection, and only with trusted prompts and repositories.
- Agent output is streamed without secret redaction.
- Pause snapshots preserve the staged access token until the sandbox is killed.
- The two native OAuth policy examples put only a placeholder token in the
  microVM. CubeEgress injects the real bearer token and account header only on
  GET/POST requests to `https://chatgpt.com/backend-api/codex/*`; all other
  internet access is denied.
- Native network-policy creation sends the real token to CubeAPI as part of the
  injection rule. Protect the Cube control-plane connection with TLS or keep it
  entirely on a trusted private network; never log sandbox creation payloads.
- CubeSandbox's Node-based OpenCode path needs the CubeEgress CA in
  `NODE_EXTRA_CA_CERTS`; the example points it at the system CA bundle.
- The API-key policy examples likewise expose only placeholders inside the VM.
  CubeEgress injects the real OpenAI key as `Authorization: Bearer ...` only for
  `https://api.openai.com/v1/*`, or the real Anthropic key as `x-api-key` only
  for `https://api.anthropic.com/v1/*`. All other internet access is denied.
- The optional sidecar forwards data-plane traffic and disables upstream TLS
  verification by default for local mkcert deployments. Do not use that default
  across an untrusted network; set `CUBE_REMOTE_PROXY_VERIFY_SSL=true` with a
  trusted CubeProxy certificate.

## Sources

- [E2B Codex guide](https://e2b.dev/docs/agents/codex)
- [E2B OpenCode guide](https://e2b.dev/docs/agents/opencode)
- [CubeSandbox Pi integration](https://github.com/TencentCloud/CubeSandbox/tree/master/examples/pi-agent-integration)

Run the OAuth conversion tests with:

```bash
python -m unittest discover -s tests
```
