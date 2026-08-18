from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass
from urllib.parse import urlsplit

from examples.oauth import (
    codex_auth_json,
    load_openai_oauth,
    opencode_auth_json,
)


@dataclass(frozen=True)
class ApiKeyProvider:
    base_url: str
    api_key: str
    custom: bool

    @property
    def openai_base_url(self) -> str:
        base_url = self.base_url.rstrip("/")
        return base_url if base_url.endswith("/v1") else f"{base_url}/v1"

    @property
    def host(self) -> str:
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise SystemExit("OPENAI_BASE_URL must be an absolute HTTP(S) URL")
        return parsed.hostname


@dataclass(frozen=True)
class AgentRuntime:
    args: str = ""
    envs: dict[str, str] | None = None
    model: str | None = None


def load_api_key_provider() -> ApiKeyProvider | None:
    base_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY")
    if base_url and not api_key:
        raise SystemExit(
            "API-key provider configuration is incomplete; missing: OPENAI_API_KEY"
        )
    if not api_key:
        return None
    return ApiKeyProvider(
        base_url=base_url or "https://api.openai.com",
        api_key=api_key,
        custom=bool(base_url),
    )


def setup_codex(sandbox) -> AgentRuntime:
    provider = load_api_key_provider()
    if provider and provider.custom:
        args = " ".join(
            [
                '-c model_provider="openai_compatible"',
                '-c model_providers.openai_compatible.name="OpenAI-compatible"',
                "-c model_providers.openai_compatible.base_url="
                f"{shlex.quote(provider.openai_base_url)}",
                '-c model_providers.openai_compatible.env_key="OPENAI_API_KEY"',
                '-c model_providers.openai_compatible.wire_api="responses"',
            ]
        )
        return AgentRuntime(
            args=args,
            envs={
                "OPENAI_API_KEY": provider.api_key,
                "CODEX_CA_CERTIFICATE": "/etc/cube/ca/cube-root-ca.crt",
            },
        )

    if provider:
        return AgentRuntime(envs={"OPENAI_API_KEY": provider.api_key})

    openai = load_openai_oauth()
    setup = sandbox.commands.run(
        "install -d -m 700 /root/.codex && "
        "install -m 600 /dev/null /root/.codex/auth.json",
        user="root",
    )
    if setup.exit_code != 0:
        raise RuntimeError(setup.stderr)
    sandbox.files.write("/root/.codex/auth.json", codex_auth_json(openai), user="root")
    return AgentRuntime()


def setup_opencode(sandbox, model: str) -> AgentRuntime:
    provider = load_api_key_provider()
    if provider and provider.custom:
        _, model_id = model.split("/", 1)
        config = {
            "$schema": "https://opencode.ai/config.json",
            "provider": {
                "openai_compatible": {
                    "npm": "@ai-sdk/openai",
                    "name": "OpenAI-compatible",
                    "options": {
                        "apiKey": "{env:OPENAI_API_KEY}",
                        "baseURL": provider.openai_base_url,
                    },
                    "models": {model_id: {"name": model_id}},
                }
            },
        }
        setup = sandbox.commands.run(
            "install -d -m 700 /root/.config/opencode",
            user="root",
        )
        if setup.exit_code != 0:
            raise RuntimeError(setup.stderr)
        sandbox.files.write(
            "/root/.config/opencode/opencode.json", json.dumps(config), user="root"
        )
        return AgentRuntime(
            envs={
                "OPENAI_API_KEY": provider.api_key,
                "NODE_EXTRA_CA_CERTS": "/etc/ssl/certs/ca-certificates.crt",
            },
            model=f"openai_compatible/{model_id}",
        )

    if provider:
        provider_id, model_id = model.split("/", 1)
        native_model = (
            f"openai/{model_id}" if provider_id == "openai_compatible" else model
        )
        return AgentRuntime(
            envs={"OPENAI_API_KEY": provider.api_key},
            model=native_model,
        )

    openai = load_openai_oauth()
    setup = sandbox.commands.run(
        "install -d -m 700 /root/.local/share/opencode && "
        "install -m 600 /dev/null /root/.local/share/opencode/auth.json",
        user="root",
    )
    if setup.exit_code != 0:
        raise RuntimeError(setup.stderr)
    sandbox.files.write(
        "/root/.local/share/opencode/auth.json", opencode_auth_json(openai), user="root"
    )
    return AgentRuntime()
