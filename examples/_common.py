from __future__ import annotations

import base64
import json
import os
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cubesandbox import Sandbox


OPENCODE_AUTH_PATH = Path.home() / ".local/share/opencode/auth.json"
REMOTE_CODEX_AUTH = "/root/.codex/auth.json"
REMOTE_OPENCODE_AUTH = "/root/.local/share/opencode/auth.json"
WORKSPACE = "/workspace"
MINIMUM_TOKEN_LIFETIME = 30 * 60


def create_sandbox() -> Sandbox:
    from cubesandbox import Sandbox

    return Sandbox.create(template=os.environ["CUBE_TEMPLATE_ID"], timeout=300)


def required_argument(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Set {name} before running this example")
    return shlex.quote(value)


def load_opencode_auth(path: Path = OPENCODE_AUTH_PATH) -> dict[str, Any]:
    try:
        auth = json.loads(path.read_text())
    except FileNotFoundError as error:
        raise SystemExit(f"OpenCode OAuth file not found: {path}") from error

    openai = auth.get("openai")
    required = ("access", "accountId", "type")
    if not isinstance(openai, dict) or any(not openai.get(key) for key in required):
        raise SystemExit(f"OpenCode OAuth file has no complete OpenAI login: {path}")
    if openai["type"] != "oauth":
        raise SystemExit("The OpenAI entry in OpenCode auth must use OAuth")
    return {"openai": openai}


def _jwt_payload(token: str) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        value = json.loads(decoded)
    except (IndexError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("OpenCode access token is not a valid JWT") from error
    if not isinstance(value, dict):
        raise ValueError("OpenCode access token has an invalid JWT payload")
    return value


def codex_auth_from_opencode(auth: dict[str, Any]) -> dict[str, Any]:
    openai = auth["openai"]
    access_token = openai["access"]
    account_id = openai["accountId"]
    claims = _jwt_payload(access_token)
    _require_fresh_access_token(openai, claims)
    auth_claims = claims.get("https://api.openai.com/auth", {})
    token_account_id = auth_claims.get("chatgpt_account_id")
    if token_account_id and token_account_id != account_id:
        raise ValueError("OpenCode accountId does not match the access token")

    # External-token mode deliberately omits the refresh token. OpenCode remains
    # its sole owner, avoiding refresh-token rotation races between both CLIs.
    return {
        "auth_mode": "chatgptAuthTokens",
        "OPENAI_API_KEY": None,
        "tokens": {
            "id_token": access_token,
            "access_token": access_token,
            "refresh_token": "",
            "account_id": account_id,
        },
        "last_refresh": datetime.now(timezone.utc).isoformat(),
    }


def opencode_runtime_auth(auth: dict[str, Any]) -> dict[str, Any]:
    source = auth["openai"]
    claims = _jwt_payload(source["access"])
    _require_fresh_access_token(source, claims)
    expires = source.get("expires")
    if not isinstance(expires, (int, float)):
        expires = claims["exp"] * 1000
    openai = {
        "type": "oauth",
        "access": source["access"],
        "refresh": "",
        "expires": expires,
        "accountId": source["accountId"],
    }
    return {"openai": openai}


def _require_fresh_access_token(
    openai: dict[str, Any],
    claims: dict[str, Any],
    minimum_lifetime: int = MINIMUM_TOKEN_LIFETIME,
) -> None:
    jwt_expiry = claims.get("exp")
    file_expiry = openai.get("expires")
    expiries = [
        expiry
        for expiry in (
            jwt_expiry if isinstance(jwt_expiry, (int, float)) else None,
            file_expiry / 1000 if isinstance(file_expiry, (int, float)) else None,
        )
        if expiry is not None
    ]
    if not expiries or min(expiries) <= time.time() + minimum_lifetime:
        raise SystemExit(
            "OpenCode access token is expired or expires within 30 minutes; "
            "refresh the host login before starting a sandbox"
        )


def stage_auth(sandbox: Sandbox, agent: str) -> None:
    auth = load_opencode_auth()
    if agent == "codex":
        remote_path = REMOTE_CODEX_AUTH
        contents = json.dumps(codex_auth_from_opencode(auth))
    elif agent == "opencode":
        remote_path = REMOTE_OPENCODE_AUTH
        contents = json.dumps(opencode_runtime_auth(auth))
    else:
        raise ValueError(f"Unsupported agent: {agent}")

    parent = remote_path.rsplit("/", 1)[0]
    result = sandbox.commands.run(
        f"install -d -m 700 {parent} && install -m 600 /dev/null {remote_path}",
        user="root",
        timeout=30,
    )
    require_success(result)
    sandbox.files.write(remote_path, contents)


def run(sandbox: Sandbox, command: str, timeout: int = 600) -> None:
    result = sandbox.commands.run(
        command, user="root", cwd=WORKSPACE, timeout=timeout
    )
    if result.stdout:
        print(result.stdout, end="")
    require_success(result)


def require_success(result: Any) -> None:
    if result.exit_code == 0:
        return
    if result.stderr:
        print(result.stderr, end="")
    raise RuntimeError(f"Sandbox command failed with exit code {result.exit_code}")


def kill_sandbox(sandbox: Sandbox) -> None:
    handling_error = sys.exc_info()[0] is not None
    try:
        sandbox.kill()
    except Exception:
        if not handling_error:
            raise
        print("Warning: sandbox cleanup also failed", file=sys.stderr)
