from __future__ import annotations

import base64
import ast
import json
import os
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
from examples.provider import load_api_key_provider, setup_codex, setup_opencode


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
                "codex/api_key_policy.py",
                "codex/network_policy.py",
                "opencode/api_key_policy.py",
                "opencode/network_policy.py",
            },
        )
        self.assertEqual(
            e2b_importers,
            {
                "docker/headless.py",
                "codex/headless.py",
                "codex/image_input.py",
                "codex/pause_resume.py",
                "codex/repository.py",
                "codex/stream_events.py",
                "opencode/headless.py",
                "opencode/http_api.py",
                "opencode/pause_resume.py",
                "opencode/repository.py",
            },
        )

        for relative_path in e2b_importers:
            source = (examples / relative_path).read_text()
            self.assertIn("upload_test_workspace(sandbox)", source)
            self.assertIn("download_test_workspace(", source)
            self.assertNotIn("volume_mounts", source)

    def test_e2b_examples_expose_optional_dev_sidecar_flag(self) -> None:
        examples = Path(__file__).parents[1] / "examples"
        for path in examples.glob("*/*.py"):
            if path.parent.name == "test_workspace" or path.name in {
                "api_key_policy.py",
                "network_policy.py",
                "__init__.py",
            }:
                continue
            source = path.read_text()
            self.assertIn('"--dev-sidecar"', source, path.as_posix())
            self.assertIn("setup_dev_sidecar()", source, path.as_posix())

        for path in examples.glob("*/*_policy.py"):
            self.assertNotIn("--dev-sidecar", path.read_text(), path.as_posix())

    def test_repository_examples_clone_as_command_user(self) -> None:
        examples = Path(__file__).parents[1] / "examples"
        for path in examples.glob("*/*.py"):
            source = path.read_text()
            if "sandbox.git.clone" in source:
                self.assertIn('user="root"', source, path.as_posix())

    def test_api_key_policy_examples_keep_real_keys_out_of_vm_env(self) -> None:
        examples = Path(__file__).parents[1] / "examples"
        expected = {
            "codex/api_key_policy.py": (
                "OPENAI_API_KEY",
                "sk-placeholder-not-a-real-key",
                'header="Authorization"',
            ),
            "opencode/api_key_policy.py": (
                "OPENAI_API_KEY",
                "sk-placeholder-not-a-real-key",
                'header="Authorization"',
            ),
        }

        for relative_path, (key_name, placeholder, injection) in expected.items():
            source = (examples / relative_path).read_text()
            self.assertIn("provider = load_api_key_provider()", source)
            self.assertIn(f'"{key_name}": "{placeholder}"', source)
            self.assertNotIn(f'"{key_name}": provider.api_key', source)
            self.assertIn("host = provider.host", source)
            self.assertIn('method=["GET", "POST"]', source)
            self.assertIn(injection, source)

        for relative_path in (
            "codex/api_key_policy.py",
            "opencode/api_key_policy.py",
        ):
            source = (examples / relative_path).read_text()
            self.assertIn('format="Bearer ${SECRET}"', source)

    def test_generic_provider_does_not_add_network_policy_to_headless(self) -> None:
        source = (
            Path(__file__).parents[1] / "examples" / "codex" / "headless.py"
        ).read_text()
        provider = (Path(__file__).parents[1] / "examples" / "provider.py").read_text()

        for name in ("OPENAI_BASE_URL", "OPENAI_API_KEY"):
            self.assertIn(name, provider)
        self.assertNotIn("LITELLM_", provider)
        self.assertNotIn("allow_out", source)
        self.assertNotIn("deny_out", source)
        self.assertNotIn("network=", source)

    def test_loads_generic_api_key_provider(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OPENAI_BASE_URL": "https://proxy.example.com",
                "OPENAI_API_KEY": "secret",
            },
            clear=True,
        ):
            provider = load_api_key_provider()

        self.assertIsNotNone(provider)
        self.assertEqual(provider.openai_base_url, "https://proxy.example.com/v1")
        self.assertEqual(provider.host, "proxy.example.com")
        self.assertTrue(provider.custom)

    def test_loads_native_openai_provider_from_api_key_only(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}, clear=True):
            provider = load_api_key_provider()

        self.assertIsNotNone(provider)
        self.assertEqual(provider.openai_base_url, "https://api.openai.com/v1")
        self.assertFalse(provider.custom)

    def test_codex_api_key_only_uses_native_openai_provider(self) -> None:
        sandbox = Mock()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}, clear=True):
            runtime = setup_codex(sandbox)

        self.assertEqual(runtime.args, "")
        self.assertEqual(runtime.envs, {"OPENAI_API_KEY": "secret"})
        sandbox.commands.run.assert_not_called()

    def test_opencode_api_key_only_uses_native_openai_provider(self) -> None:
        sandbox = Mock()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}, clear=True):
            runtime = setup_opencode(sandbox, "openai_compatible/gpt-5")

        self.assertEqual(runtime.model, "openai/gpt-5")
        self.assertEqual(runtime.envs, {"OPENAI_API_KEY": "secret"})
        sandbox.files.write.assert_not_called()

    def test_normalizes_provider_base_url_with_v1_suffix(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OPENAI_BASE_URL": "https://proxy.example.com/v1/",
                "OPENAI_API_KEY": "secret",
            },
            clear=True,
        ):
            provider = load_api_key_provider()

        self.assertEqual(provider.openai_base_url, "https://proxy.example.com/v1")

    def test_rejects_non_http_provider_url(self) -> None:
        with patch.dict(
            os.environ,
            {"OPENAI_BASE_URL": "proxy.example.com", "OPENAI_API_KEY": "secret"},
            clear=True,
        ):
            provider = load_api_key_provider()
            with self.assertRaisesRegex(SystemExit, "absolute HTTP"):
                _ = provider.host

    def test_opencode_uses_responses_capable_openai_sdk(self) -> None:
        sandbox = Mock()
        sandbox.commands.run.return_value = Mock(exit_code=0)
        with patch.dict(
            os.environ,
            {
                "OPENAI_BASE_URL": "https://proxy.example.com",
                "OPENAI_API_KEY": "secret",
            },
            clear=True,
        ):
            runtime = setup_opencode(sandbox, "gateway/model-1")

        config = json.loads(sandbox.files.write.call_args.args[1])
        self.assertEqual(
            config["provider"]["openai_compatible"]["npm"], "@ai-sdk/openai"
        )
        self.assertEqual(runtime.model, "openai_compatible/model-1")

    def test_rejects_partial_generic_api_key_provider(self) -> None:
        with (
            patch.dict(
                os.environ,
                {"OPENAI_BASE_URL": "https://proxy.example.com"},
                clear=True,
            ),
            self.assertRaisesRegex(SystemExit, "OPENAI_API_KEY"),
        ):
            load_api_key_provider()


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
