# Coding agent examples

This directory contains runnable Codex and OpenCode examples for the public
CubeSandbox coding-agent template. It covers:

- creating sandboxes through CubeAPI's E2B-compatible API;
- using an OpenAI-compatible Responses API or OpenAI OAuth fallback;
- uploading a local test workspace and downloading the agent's result;
- pause/resume, streamed events, image input, and the OpenCode HTTP API;
- optional CubeEgress policies that keep real credentials outside the VM;
- an optional local-development sidecar.

No credentials belong in this repository. `.env` is git-ignored, and the
committed [`.env.example`](../.env.example) contains placeholders only.

## Prerequisites

- Python 3.11 or newer;
- access to a running CubeSandbox deployment;
- a registered template built from this repository's image;
- an OpenAI-compatible endpoint supporting the Responses API, or a valid local
  OpenAI OAuth login;
- wildcard sandbox DNS and TLS for direct production runs.

Run every command below from the repository root.

## Install dependencies

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Create local configuration

Copy the example configuration, replace every placeholder locally, and keep the
result uncommitted:

```bash
cp .env.example .env
chmod 600 .env
```

The scripts intentionally do not parse `.env` themselves. Export it into the
current shell before running an example:

```bash
set -a
. ./.env
set +a
```

Alternatively, if `uv` is installed, load the file for one command:

```bash
uv run --env-file .env --no-sync python -m examples.codex.headless
```

## Environment reference

### E2B-compatible CubeAPI

| Variable | Required | Purpose |
|---|---:|---|
| `E2B_API_URL` | Yes | Public CubeAPI base URL |
| `E2B_API_KEY` | Yes | CubeAPI static API key |
| `E2B_VALIDATE_API_KEY` | Cube deployments | Set to `false` when the Cube key does not use E2B's key format; CubeAPI still authenticates it server-side |
| `CUBE_TEMPLATE_ID` | Yes | Registered coding-agent template ID |

### Model provider

| Variable | Required | Purpose |
|---|---:|---|
| `OPENAI_BASE_URL` | Custom gateway mode | OpenAI-compatible endpoint; a trailing `/v1` is optional |
| `OPENAI_API_KEY` | API-key mode | OpenAI or custom provider API key |
| `CODEX_MODEL` | Codex | Provider model ID passed to Codex |
| `OPENCODE_MODEL` | OpenCode | Model in `provider/model` form; use `openai/...` for native OpenAI and `openai_compatible/...` for a custom gateway |

With only `OPENAI_API_KEY`, the examples use the agents' native OpenAI provider
and do not generate an `openai_compatible` provider. When `OPENAI_BASE_URL` is
set, `OPENAI_API_KEY` is also required and the examples configure the custom
Responses API provider. `OPENAI_BASE_URL` without a key is an error.

The OpenCode API-key configuration uses `@ai-sdk/openai`, not
`@ai-sdk/openai-compatible`, because these examples require `/v1/responses`
rather than `/v1/chat/completions`.

### Native policy examples

| Variable | Required | Purpose |
|---|---:|---|
| `CUBE_API_URL` | Policy examples | CubeAPI URL used by the native `cubesandbox` SDK |
| `CUBE_API_KEY` | Policy examples | CubeAPI static API key |
| `CUBE_PUBLIC_SCHEME` | OpenCode HTTP API | Must be `https` for direct public access; defaults to `https` |

### Per-example input and output

| Variable | Required | Purpose |
|---|---:|---|
| `REPOSITORY_URL` | Repository, stream, image examples | Public Git clone URL |
| `MOCKUP_PATH` | Image example | Local PNG, JPEG, or WebP file |
| `WORKSPACE_OUTPUT_DIR` | No | Local result directory; defaults to `workspace-output` |

The repository examples use a public clone URL. Do not embed a token in
`REPOSITORY_URL`. Private repository support requires explicitly passing a
credential to `sandbox.git.clone`.

## Authentication modes

### OpenAI-compatible API key

Native OpenAI API-key mode does not need a base URL:

```bash
unset OPENAI_BASE_URL
export OPENAI_API_KEY=<openai-key>
export CODEX_MODEL=<openai-model-id>
export OPENCODE_MODEL=openai/<openai-model-id>
```

For a custom model gateway, set both provider variables:

```bash
export OPENAI_BASE_URL=https://llm.example.com/v1
export OPENAI_API_KEY=<provider-key>
export CODEX_MODEL=<model-id>
export OPENCODE_MODEL=openai_compatible/<model-id>
```

The regular E2B examples pass the API key to the agent process inside the VM.
They use open egress and should run only with trusted prompts and repositories.

### OpenAI OAuth fallback

To use the existing OpenAI OAuth state, remove both API-key variables:

```bash
unset OPENAI_BASE_URL
unset OPENAI_API_KEY
```

The host must have a valid OpenAI entry in
`~/.local/share/opencode/auth.json`. The examples copy only the current access
token and account ID into the VM. They never copy the refresh token and reject
access tokens with less than 30 minutes remaining.

## Test workspace round trip

Every E2B-based example performs this sequence:

1. Archive [`examples/test_workspace`](test_workspace) locally.
2. Upload it through the E2B Files API.
3. Extract it into `/workspace` inside the sandbox.
4. Run the coding agent with `/workspace` as its working directory, or clone a
   requested repository into `/workspace/repo`.
5. Archive the resulting `/workspace` and download it locally.

Results are written as `workspace-output/<example-name>.tar.gz` by default.
The downloaded archive excludes `.git`, `node_modules`, `dist`, `__pycache__`,
and `.pyc` files.

```bash
export WORKSPACE_OUTPUT_DIR=/tmp/coding-agent-results
python -m examples.codex.headless
mkdir -p /tmp/coding-agent-result
tar -xzf /tmp/coding-agent-results/codex-headless.tar.gz \
  -C /tmp/coding-agent-result
```

This is an upload/download round trip. It does not require a persistent volume
plugin and is not a host bind mount.

## Direct production transport

Do not pass `--dev-sidecar` when wildcard sandbox DNS and TLS are configured.
The E2B SDK obtains the sandbox domain from CubeAPI and connects directly:

```bash
python -m examples.codex.headless
python -m examples.opencode.headless
```

The public transport must allow hosts in the form
`https://<port>-<sandbox-id>.<sandbox-domain>`.

## Optional development sidecar

Use the sidecar only when local development lacks working wildcard DNS/TLS.
Append `--dev-sidecar` to any E2B-based example:

```bash
export CUBE_REMOTE_PROXY_BASE=https://<cube-proxy-host>:443
export CUBE_REMOTE_PROXY_VERIFY_SSL=false

python -m examples.codex.headless --dev-sidecar
python -m examples.opencode.headless --dev-sidecar
```

| Variable | Default | Purpose |
|---|---|---|
| `CUBE_REMOTE_PROXY_BASE` | `https://127.0.0.1:11443` | CubeProxy endpoint receiving forwarded data-plane traffic |
| `CUBE_REMOTE_PROXY_VERIFY_SSL` | `false` | Verify upstream CubeProxy TLS |
| `CUBE_REMOTE_SANDBOX_DOMAIN` | `cube.app` | Host suffix sent to CubeProxy |
| `CUBE_DEV_PROXY_HOST` | `127.0.0.1` | Embedded sidecar listen address |
| `CUBE_DEV_PROXY_PORT` | `12580` | Preferred embedded sidecar port |
| `CUBE_DEV_PROXY_URL` | unset | Use an already-running sidecar |

The sidecar has no authentication. Keep it bound to loopback and enable TLS
verification whenever traffic crosses an untrusted network. Policy examples use
the native SDK and do not accept `--dev-sidecar`.

## Run Codex examples

### Headless

Runs one non-interactive task against the uploaded test workspace:

```bash
python -m examples.codex.headless
tar -tzf workspace-output/codex-headless.tar.gz
```

### Public repository

```bash
export REPOSITORY_URL=https://github.com/<owner>/<repository>.git
python -m examples.codex.repository
tar -tzf workspace-output/codex-repository.tar.gz
```

### Stream JSONL events

```bash
export REPOSITORY_URL=https://github.com/<owner>/<repository>.git
python -m examples.codex.stream_events
tar -tzf workspace-output/codex-stream-events.tar.gz
```

### Pause and resume

Creates a thread, pauses the Cube sandbox, reconnects, and resumes the same
thread:

```bash
python -m examples.codex.pause_resume
tar -tzf workspace-output/codex-pause-resume.tar.gz
```

### Image input

Provide an existing image or download a disposable test image:

```bash
curl -fL https://picsum.photos/seed/cubesandbox-agent/1200/800 \
  -o /tmp/codex-mockup.jpg
export MOCKUP_PATH=/tmp/codex-mockup.jpg
export REPOSITORY_URL=https://github.com/<owner>/<repository>.git
python -m examples.codex.image_input
tar -tzf workspace-output/codex-image-input.tar.gz
```

### OAuth egress policy

Uses the native CubeSandbox SDK, default-deny egress, and on-wire OAuth header
injection. The real OAuth access token is not placed in the VM:

```bash
python -m examples.codex.network_policy
```

### API-key egress policy

Uses default-deny egress and injects the real `OPENAI_API_KEY` only for requests
to `api.openai.com` in native mode, or to the host and API path derived from
`OPENAI_BASE_URL` in custom gateway mode:

```bash
python -m examples.codex.api_key_policy
```

## Run OpenCode examples

### Headless

```bash
python -m examples.opencode.headless
tar -tzf workspace-output/opencode-headless.tar.gz
```

### Public repository

```bash
export REPOSITORY_URL=https://github.com/<owner>/<repository>.git
python -m examples.opencode.repository
tar -tzf workspace-output/opencode-repository.tar.gz
```

### Pause and resume

```bash
python -m examples.opencode.pause_resume
tar -tzf workspace-output/opencode-pause-resume.tar.gz
```

### HTTP API

Starts `opencode serve` on sandbox port `4096`, protects it with a random
per-run Basic Auth password, creates a session, submits a message, and downloads
the workspace result:

```bash
export CUBE_PUBLIC_SCHEME=https
python -m examples.opencode.http_api
tar -tzf workspace-output/opencode-http-api.tar.gz
```

Direct public access rejects plaintext HTTP. With `--dev-sidecar`, the script
uses the sidecar URL scheme for local development.

### OAuth egress policy

```bash
python -m examples.opencode.network_policy
```

### API-key egress policy

```bash
python -m examples.opencode.api_key_policy
```

## Run all regular examples

Set `REPOSITORY_URL` and `MOCKUP_PATH` first, then run:

```bash
python -m examples.codex.headless
python -m examples.codex.repository
python -m examples.codex.stream_events
python -m examples.codex.pause_resume
python -m examples.codex.image_input

python -m examples.opencode.headless
python -m examples.opencode.repository
python -m examples.opencode.pause_resume
python -m examples.opencode.http_api
```

Run policy examples separately because they exercise a different security
boundary and use the native CubeSandbox SDK:

```bash
python -m examples.codex.network_policy
python -m examples.codex.api_key_policy
python -m examples.opencode.network_policy
python -m examples.opencode.api_key_policy
```

## Security boundaries

- Regular E2B examples put the selected API key or short-lived OAuth access
  token inside the VM and allow open egress.
- Agent output is streamed without secret redaction.
- Uploaded prompts, source code, and generated files may be sent to the model
  provider.
- Pause snapshots retain staged credentials until the sandbox is killed.
- Policy examples put placeholder credentials in the VM. CubeEgress injects the
  real credential only for the configured destination and denies other egress.
- Policy creation sends the real credential to CubeAPI as part of the injection
  rule. Use TLS and do not log sandbox creation payloads.
- Downloaded workspace archives may contain generated source code or other
  sensitive data. `workspace-output/` is git-ignored, but still protect or
  delete it as appropriate.
- The OpenCode HTTP API uses a random password but is still intended for
  short-lived example sessions, not permanent public hosting.

## Troubleshooting

### Missing environment variable

Confirm that `.env` was exported into the current shell:

```bash
set -a
. ./.env
set +a
```

### Incomplete provider configuration

If `OPENAI_BASE_URL` is set, also set `OPENAI_API_KEY`. With only the key, the
examples use native OpenAI. Unset both variables to select OAuth fallback.

### OpenCode request timeout or `/v1/chat/completions` failure

Ensure the generated provider uses `@ai-sdk/openai` and that the gateway
supports `/v1/responses`.

### Repository clone permission failure

The examples clone as `root` into `/workspace/repo`. Use the current scripts;
older revisions omitted the clone user and could not create that directory in
this template.

### OpenCode HTTP API is unreachable

Verify wildcard DNS/TLS for port `4096`, `CUBE_PUBLIC_SCHEME=https`, and the
CubeProxy public route. Use `--dev-sidecar` only for local development.

### No result archive

The archive is downloaded after a successful agent command. Check the command
exception and ensure the local `WORKSPACE_OUTPUT_DIR` is writable.

## Validation

```bash
python -m unittest discover -s tests
python -m compileall -q examples tests
git diff --check
```

## Sources

- [E2B Codex guide](https://e2b.dev/docs/agents/codex)
- [E2B OpenCode guide](https://e2b.dev/docs/agents/opencode)
- [CubeSandbox Pi integration](https://github.com/TencentCloud/CubeSandbox/tree/master/examples/pi-agent-integration)
