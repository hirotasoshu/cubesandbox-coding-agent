from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENCODE_AUTH_PATH = Path.home() / ".local/share/opencode/auth.json"
MINIMUM_TOKEN_LIFETIME = 30 * 60


def load_openai_oauth(path: Path = OPENCODE_AUTH_PATH) -> dict[str, Any]:
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

    claims = jwt_payload(openai["access"])
    expiry = claims.get("exp")
    if not isinstance(expiry, (int, float)) or expiry <= time.time() + MINIMUM_TOKEN_LIFETIME:
        raise SystemExit(
            "OpenCode access token expires within 30 minutes; refresh the host login first"
        )

    token_account_id = claims.get("https://api.openai.com/auth", {}).get(
        "chatgpt_account_id"
    )
    if token_account_id and token_account_id != openai["accountId"]:
        raise SystemExit("OpenCode accountId does not match the access token")
    return openai


def jwt_payload(token: str) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        value = json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit("OpenCode access token is not a valid JWT") from error
    if not isinstance(value, dict):
        raise SystemExit("OpenCode access token has an invalid JWT payload")
    return value


def codex_auth_json(openai: dict[str, Any], access_token: str | None = None) -> str:
    token = access_token or openai["access"]
    return json.dumps(
        {
            "auth_mode": "chatgptAuthTokens",
            "OPENAI_API_KEY": None,
            "tokens": {
                "id_token": token,
                "access_token": token,
                "refresh_token": "",
                "account_id": openai["accountId"],
            },
            "last_refresh": datetime.now(timezone.utc).isoformat(),
        }
    )


def opencode_auth_json(openai: dict[str, Any], access_token: str | None = None) -> str:
    token = access_token or openai["access"]
    claims = jwt_payload(token)
    return json.dumps(
        {
            "openai": {
                "type": "oauth",
                "access": token,
                "refresh": "",
                "expires": claims["exp"] * 1000,
                "accountId": openai["accountId"],
            }
        }
    )


def placeholder_access_token(openai: dict[str, Any]) -> str:
    claims = {
        "exp": int(time.time()) + 24 * 60 * 60,
        "https://api.openai.com/auth": {
            "chatgpt_account_id": openai["accountId"],
        },
    }
    encoded = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"placeholder.{encoded}.placeholder"
