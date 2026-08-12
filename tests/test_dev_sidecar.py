from __future__ import annotations

import unittest

from multidict import CIMultiDict

from examples.dev_sidecar import _router_host, _router_url, _websocket_protocols


class DevSidecarUrlTest(unittest.TestCase):
    def test_builds_envd_router_url(self) -> None:
        self.assertEqual(
            _router_url("http://127.0.0.1:12580", "sandbox-1", 49983),
            "http://127.0.0.1:12580/sandboxes/router/sandbox-1/49983",
        )

    def test_builds_public_host_fragment(self) -> None:
        self.assertEqual(
            _router_host("http://127.0.0.1:12580", "sandbox-1", 4096),
            "127.0.0.1:12580/sandboxes/router/sandbox-1/4096",
        )

    def test_splits_websocket_protocol_header(self) -> None:
        class Request:
            headers = CIMultiDict({"Sec-WebSocket-Protocol": "proto1, proto2"})

        self.assertEqual(_websocket_protocols(Request()), ("proto1", "proto2"))


if __name__ == "__main__":
    unittest.main()
