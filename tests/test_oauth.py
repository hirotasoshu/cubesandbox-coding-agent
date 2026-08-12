from __future__ import annotations

import base64
import ast
import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from cubesandbox._commands import CommandResult, Commands

from examples.oauth import (
    codex_auth_json,
    load_openai_oauth,
    opencode_auth_json,
    placeholder_access_token,
)


def jwt(payload: dict[str, object]) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{encoded}.signature"


class OAuthTest(unittest.TestCase):
    def setUp(self) -> None:
        self.token = jwt(
            {
                "exp": time.time() + 3600,
                "https://api.openai.com/auth": {"chatgpt_account_id": "account-1"},
            }
        )
        self.openai = {
            "type": "oauth",
            "access": self.token,
            "refresh": "must-not-be-copied",
            "expires": (time.time() + 3600) * 1000,
            "accountId": "account-1",
            "futureSensitiveField": "must-not-be-copied-either",
        }

    def test_loads_only_openai_entry(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "auth.json"
            path.write_text(
                json.dumps(
                    {
                        "openai": self.openai,
                        "other-provider": {"key": "other-secret"},
                    }
                )
            )
            loaded = load_openai_oauth(path)
        self.assertEqual(loaded, self.openai)

    def test_codex_auth_omits_refresh_token(self) -> None:
        auth = json.loads(codex_auth_json(self.openai))
        self.assertEqual(auth["auth_mode"], "chatgptAuthTokens")
        self.assertEqual(auth["tokens"]["refresh_token"], "")
        self.assertNotIn("must-not-be-copied", json.dumps(auth))

    def test_opencode_auth_allowlists_fields(self) -> None:
        auth = json.loads(opencode_auth_json(self.openai))
        self.assertEqual(
            set(auth["openai"]), {"type", "access", "refresh", "expires", "accountId"}
        )
        self.assertEqual(auth["openai"]["refresh"], "")
        self.assertNotIn("must-not-be-copied", json.dumps(auth))

    def test_placeholder_contains_no_real_access_token(self) -> None:
        placeholder = placeholder_access_token(self.openai)
        self.assertNotEqual(placeholder, self.token)
        self.assertNotIn(self.token, placeholder)

    def test_rejects_token_near_expiry(self) -> None:
        self.openai["access"] = jwt({"exp": time.time() + 60})
        with TemporaryDirectory() as directory:
            path = Path(directory) / "auth.json"
            path.write_text(json.dumps({"openai": self.openai}))
            with self.assertRaisesRegex(SystemExit, "expires within 30 minutes"):
                load_openai_oauth(path)


class ExampleImportsTest(unittest.TestCase):
    def test_only_network_policy_examples_import_cubesandbox(self) -> None:
        examples = Path(__file__).parents[1] / "examples"
        native_importers = set()
        e2b_importers = set()

        for path in examples.glob("*/*.py"):
            tree = ast.parse(path.read_text())
            modules = {
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            }
            if "cubesandbox" in modules:
                native_importers.add(path.relative_to(examples).as_posix())
            if "e2b" in modules:
                e2b_importers.add(path.relative_to(examples).as_posix())

        self.assertEqual(
            native_importers,
            {
                "claude/api_key_policy.py",
                "codex/api_key_policy.py",
                "codex/network_policy.py",
                "opencode/api_key_policy.py",
                "opencode/network_policy.py",
            },
        )
        self.assertEqual(
            e2b_importers,
            {
                "codex/headless.py",
                "codex/image_input.py",
                "codex/pause_resume.py",
                "codex/repository.py",
                "codex/stream_events.py",
                "codex/structured_output.py",
                "opencode/headless.py",
                "opencode/http_api.py",
                "opencode/pause_resume.py",
                "opencode/repository.py",
            },
        )

    def test_e2b_examples_expose_optional_dev_sidecar_flag(self) -> None:
        examples = Path(__file__).parents[1] / "examples"
        for path in examples.glob("*/*.py"):
            if path.name in {"api_key_policy.py", "network_policy.py", "__init__.py"}:
                continue
            source = path.read_text()
            self.assertIn('"--dev-sidecar"', source, path.as_posix())
            self.assertIn("setup_dev_sidecar()", source, path.as_posix())

        for path in examples.glob("*/*_policy.py"):
            self.assertNotIn("--dev-sidecar", path.read_text(), path.as_posix())

    def test_api_key_policy_examples_keep_real_keys_out_of_vm_env(self) -> None:
        examples = Path(__file__).parents[1] / "examples"
        expected = {
            "claude/api_key_policy.py": (
                "ANTHROPIC_API_KEY",
                "sk-ant-placeholder-not-a-real-key",
                "api.anthropic.com",
                'Inject(header="x-api-key", secret=api_key)',
            ),
            "codex/api_key_policy.py": (
                "OPENAI_API_KEY",
                "sk-placeholder-not-a-real-key",
                "api.openai.com",
                'header="Authorization"',
            ),
            "opencode/api_key_policy.py": (
                "OPENAI_API_KEY",
                "sk-placeholder-not-a-real-key",
                "api.openai.com",
                'header="Authorization"',
            ),
        }

        for relative_path, (key_name, placeholder, host, injection) in expected.items():
            source = (examples / relative_path).read_text()
            self.assertIn(f'api_key = os.environ["{key_name}"]', source)
            self.assertIn(f'"{key_name}": "{placeholder}"', source)
            self.assertNotIn(f'"{key_name}": api_key', source)
            self.assertIn(f'host = "{host}"', source)
            self.assertIn('path="/v1/*"', source)
            self.assertIn('method=["GET", "POST"]', source)
            self.assertIn(injection, source)

        for relative_path in (
            "codex/api_key_policy.py",
            "opencode/api_key_policy.py",
        ):
            source = (examples / relative_path).read_text()
            self.assertIn('format="Bearer ${SECRET}"', source)


class CubeSandboxCompatibilityTest(unittest.TestCase):
    def test_commands_use_connect_fallback_when_e2b_protocol_import_fails(self) -> None:
        commands = Commands(Mock())
        fallback_result = CommandResult(stdout="ok", stderr="", exit_code=0)

        with (
            patch.object(commands, "_run_with_e2b_connect", side_effect=ImportError),
            patch.object(
                commands,
                "_run_with_connect_fallback",
                return_value=fallback_result,
            ) as fallback,
        ):
            result = commands.run("true", user="agent")

        self.assertEqual(result, fallback_result)
        fallback.assert_called_once_with(
            "true", timeout=None, cwd=None, envs={}, user="agent"
        )


if __name__ == "__main__":
    unittest.main()
