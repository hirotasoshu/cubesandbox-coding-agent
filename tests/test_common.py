from __future__ import annotations

import base64
import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from examples._common import (
    codex_auth_from_opencode,
    load_opencode_auth,
    opencode_runtime_auth,
)


def jwt(payload: dict[str, object]) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{encoded}.signature"


class CodexAuthConversionTest(unittest.TestCase):
    def test_converts_to_external_tokens_without_refresh_token(self) -> None:
        token = jwt(
            {
                "exp": time.time() + 3600,
                "https://api.openai.com/auth": {"chatgpt_account_id": "account-1"},
            }
        )
        source = {
            "openai": {
                "type": "oauth",
                "access": token,
                "refresh": "must-not-be-copied",
                "expires": (time.time() + 3600) * 1000,
                "accountId": "account-1",
                "futureSensitiveField": "must-not-be-copied-either",
            }
        }

        converted = codex_auth_from_opencode(source)

        self.assertEqual(converted["auth_mode"], "chatgptAuthTokens")
        self.assertEqual(converted["tokens"]["id_token"], token)
        self.assertEqual(converted["tokens"]["access_token"], token)
        self.assertEqual(converted["tokens"]["refresh_token"], "")
        self.assertNotIn("must-not-be-copied", json.dumps(converted))

    def test_rejects_account_mismatch(self) -> None:
        token = jwt(
            {
                "exp": time.time() + 3600,
                "https://api.openai.com/auth": {"chatgpt_account_id": "account-2"},
            }
        )
        source = {
            "openai": {
                "access": token,
                "accountId": "account-1",
                "expires": (time.time() + 3600) * 1000,
            }
        }

        with self.assertRaisesRegex(ValueError, "does not match"):
            codex_auth_from_opencode(source)


class OpenCodeAuthLoadingTest(unittest.TestCase):
    def test_discards_credentials_for_other_providers(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "auth.json"
            path.write_text(
                json.dumps(
                    {
                        "openai": {
                            "type": "oauth",
                            "access": "access-token",
                            "accountId": "account-1",
                        },
                        "other-provider": {"key": "must-not-be-copied"},
                    }
                )
            )

            loaded = load_opencode_auth(path)

        self.assertEqual(set(loaded), {"openai"})
        self.assertNotIn("must-not-be-copied", json.dumps(loaded))

    def test_runtime_auth_omits_refresh_token(self) -> None:
        token = jwt({"exp": time.time() + 3600})
        source = {
            "openai": {
                "type": "oauth",
                "access": token,
                "refresh": "must-not-be-copied",
                "expires": (time.time() + 3600) * 1000,
                "accountId": "account-1",
            }
        }

        runtime_auth = opencode_runtime_auth(source)

        self.assertEqual(runtime_auth["openai"]["refresh"], "")
        self.assertNotIn("must-not-be-copied", json.dumps(runtime_auth))
        self.assertNotIn("futureSensitiveField", runtime_auth["openai"])

    def test_rejects_access_token_near_expiry(self) -> None:
        token = jwt({"exp": time.time() + 60})
        source = {
            "openai": {
                "access": token,
                "expires": (time.time() + 60) * 1000,
                "accountId": "account-1",
            }
        }

        with self.assertRaisesRegex(SystemExit, "expires within 30 minutes"):
            codex_auth_from_opencode(source)


if __name__ == "__main__":
    unittest.main()
