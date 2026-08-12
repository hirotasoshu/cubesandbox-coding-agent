# Copyright (c) 2026 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

"""Optional development proxy for the official E2B SDK.

Adapted from TencentCloud/CubeSandbox examples/e2b-dev-sidecar/dev_sidecar.py.
This intentionally patches only the E2B surfaces used by this repository.
"""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Iterable
from urllib.parse import urlencode, urlsplit

from aiohttp import ClientSession, ClientTimeout, TCPConnector, WSMsgType, hdrs, web


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
WEBSOCKET_REQUEST_HEADERS = {
    hdrs.CONNECTION,
    hdrs.SEC_WEBSOCKET_ACCEPT,
    hdrs.SEC_WEBSOCKET_EXTENSIONS,
    hdrs.SEC_WEBSOCKET_KEY,
    hdrs.SEC_WEBSOCKET_PROTOCOL,
    hdrs.SEC_WEBSOCKET_VERSION,
    hdrs.UPGRADE,
}
CONFIG_KEY = web.AppKey("config", dict)
SESSION_KEY = web.AppKey("session", ClientSession)

_PATCHED = False
_SIDECAR_LOCK = threading.Lock()
_SIDECAR_READY = threading.Event()
_SIDECAR_URL = ""
_SIDECAR_ERROR: BaseException | None = None


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _bool_env(name: str, default: bool) -> bool:
    value = _env(name)
    return default if not value else value.lower() in {"1", "true", "yes", "on"}


def _normalize_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value:
        return ""
    return value if "://" in value else f"http://{value}"


def _router_path(sandbox_id: str, port: int, tail: str = "") -> str:
    path = f"/sandboxes/router/{sandbox_id}/{port}"
    return f"{path}/{tail.lstrip('/')}" if tail else path


def _router_url(
    base_url: str, sandbox_id: str, port: int, tail: str = "", query: str = ""
) -> str:
    url = f"{base_url.rstrip('/')}{_router_path(sandbox_id, port, tail)}"
    return f"{url}?{query}" if query else url


def _router_host(base_url: str, sandbox_id: str, port: int) -> str:
    parsed = urlsplit(_normalize_url(base_url))
    base = f"{parsed.netloc}{parsed.path}".rstrip("/")
    return f"{base}{_router_path(sandbox_id, port)}"


def _copy_headers(
    headers: Iterable[tuple[str, str]], *, host: str, keep_upgrade: bool = False
) -> dict[str, str]:
    copied = {}
    for key, value in headers:
        lowered = key.lower()
        if lowered == "host" or (not keep_upgrade and lowered in HOP_BY_HOP_HEADERS):
            continue
        copied[key] = value
    copied["Host"] = host
    return copied


def _websocket_protocols(request: web.Request) -> tuple[str, ...]:
    return tuple(
        protocol.strip()
        for value in request.headers.getall(hdrs.SEC_WEBSOCKET_PROTOCOL, [])
        for protocol in value.split(",")
        if protocol.strip()
    )


async def _pump_to_upstream(downstream: web.WebSocketResponse, upstream) -> None:
    async for message in downstream:
        if message.type == WSMsgType.TEXT:
            await upstream.send_str(message.data)
        elif message.type == WSMsgType.BINARY:
            await upstream.send_bytes(message.data)
        elif message.type == WSMsgType.CLOSE:
            return


async def _pump_to_downstream(upstream, downstream: web.WebSocketResponse) -> None:
    async for message in upstream:
        if message.type == WSMsgType.TEXT:
            await downstream.send_str(message.data)
        elif message.type == WSMsgType.BINARY:
            await downstream.send_bytes(message.data)
        elif message.type == WSMsgType.CLOSE:
            return


async def _proxy(request: web.Request) -> web.StreamResponse:
    config = request.app[CONFIG_KEY]
    sandbox_id = request.match_info["sandbox_id"]
    port = int(request.match_info["port"])
    tail = request.match_info.get("tail", "")
    upstream_url = f"{config['proxy_base']}/{tail}"
    if request.query_string:
        upstream_url = f"{upstream_url}?{request.query_string}"
    host = f"{port}-{sandbox_id}.{config['sandbox_domain']}"
    session = request.app[SESSION_KEY]

    if request.headers.get(hdrs.UPGRADE, "").lower() == "websocket":
        headers = _copy_headers(request.headers.items(), host=host, keep_upgrade=True)
        headers = {
            key: value
            for key, value in headers.items()
            if key in WEBSOCKET_REQUEST_HEADERS or key.lower() not in HOP_BY_HOP_HEADERS
        }
        parsed = urlsplit(upstream_url)
        websocket_url = parsed._replace(
            scheme="wss" if parsed.scheme == "https" else "ws"
        ).geturl()
        requested_protocols = _websocket_protocols(request)
        async with session.ws_connect(
            websocket_url, headers=headers, protocols=requested_protocols
        ) as upstream:
            protocols = (upstream.protocol,) if upstream.protocol else ()
            downstream = web.WebSocketResponse(protocols=protocols)
            await downstream.prepare(request)
            tasks = {
                asyncio.create_task(_pump_to_upstream(downstream, upstream)),
                asyncio.create_task(_pump_to_downstream(upstream, downstream)),
            }
            _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            return downstream

    headers = _copy_headers(request.headers.items(), host=host)
    body = await request.read()
    async with session.request(
        request.method,
        upstream_url,
        headers=headers,
        data=body or None,
        allow_redirects=False,
    ) as upstream:
        response = web.StreamResponse(status=upstream.status, reason=upstream.reason)
        for key, value in upstream.headers.items():
            if key.lower() not in HOP_BY_HOP_HEADERS | {"content-length"}:
                response.headers.add(key, value)
        await response.prepare(request)
        async for chunk in upstream.content.iter_chunked(64 * 1024):
            await response.write(chunk)
        await response.write_eof()
        return response


async def _startup(app: web.Application) -> None:
    config = app[CONFIG_KEY]
    app[SESSION_KEY] = ClientSession(
        connector=TCPConnector(ssl=config["verify_ssl"]),
        timeout=ClientTimeout(total=None, connect=30, sock_read=None),
        auto_decompress=False,
        skip_auto_headers={hdrs.ACCEPT_ENCODING},
    )


async def _cleanup(app: web.Application) -> None:
    await app[SESSION_KEY].close()


def _build_app() -> web.Application:
    app = web.Application(client_max_size=64 * 1024 * 1024)
    app[CONFIG_KEY] = {
        "proxy_base": _env("CUBE_REMOTE_PROXY_BASE", "https://127.0.0.1:11443").rstrip("/"),
        "sandbox_domain": _env("CUBE_REMOTE_SANDBOX_DOMAIN", "cube.app"),
        "verify_ssl": _bool_env("CUBE_REMOTE_PROXY_VERIFY_SSL", False),
    }
    app.on_startup.append(_startup)
    app.on_cleanup.append(_cleanup)
    app.router.add_route("*", "/sandboxes/router/{sandbox_id}/{port}", _proxy)
    app.router.add_route("*", "/sandboxes/router/{sandbox_id}/{port}/{tail:.*}", _proxy)
    return app


async def _start(host: str, preferred_port: int) -> int:
    runner = web.AppRunner(_build_app())
    await runner.setup()
    for port in [*range(preferred_port, preferred_port + 32), 0]:
        site = web.TCPSite(runner, host=host, port=port)
        try:
            await site.start()
        except OSError:
            continue
        return int(runner.addresses[0][1])
    raise RuntimeError("Failed to bind embedded dev sidecar")


def _run(host: str, preferred_port: int) -> None:
    global _SIDECAR_ERROR, _SIDECAR_URL
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        port = loop.run_until_complete(_start(host, preferred_port))
        _SIDECAR_URL = f"http://{host}:{port}"
        _SIDECAR_READY.set()
        loop.run_forever()
    except Exception as error:
        _SIDECAR_ERROR = error
        _SIDECAR_READY.set()


def _sidecar_url() -> str:
    global _SIDECAR_ERROR, _SIDECAR_URL
    explicit_url = _normalize_url(_env("CUBE_DEV_PROXY_URL"))
    if explicit_url:
        return explicit_url
    if _SIDECAR_URL:
        return _SIDECAR_URL
    with _SIDECAR_LOCK:
        if not _SIDECAR_URL:
            thread = threading.Thread(
                target=_run,
                args=(
                    _env("CUBE_DEV_PROXY_HOST", "127.0.0.1"),
                    int(_env("CUBE_DEV_PROXY_PORT", "12580")),
                ),
                daemon=True,
            )
            thread.start()
            _SIDECAR_READY.wait(timeout=10)
    if _SIDECAR_ERROR:
        raise RuntimeError("Embedded dev sidecar failed to start") from _SIDECAR_ERROR
    if not _SIDECAR_URL:
        raise RuntimeError("Embedded dev sidecar did not become ready")
    return _SIDECAR_URL


def setup_dev_sidecar() -> None:
    """Start the optional sidecar and patch E2B data-plane URL construction."""
    from e2b import ConnectionConfig
    from e2b.sandbox.main import SandboxBase

    global _PATCHED
    if _PATCHED:
        return
    base_url = _sidecar_url()

    def get_sandbox_url(self, sandbox_id: str, _sandbox_domain: str) -> str:
        return _router_url(base_url, sandbox_id, self.envd_port)

    def get_host(self, port: int) -> str:
        return _router_host(base_url, self.sandbox_id, port)

    def file_url(
        self,
        path: str,
        user: str | None = None,
        signature: str | None = None,
        signature_expiration: int | None = None,
    ) -> str:
        query = {"path": path} if path else {}
        if user:
            query["username"] = user
        if signature:
            query["signature"] = signature
        if signature_expiration:
            query["signature_expiration"] = str(signature_expiration)
        return _router_url(
            base_url, self.sandbox_id, self.connection_config.envd_port, "files", urlencode(query)
        )

    ConnectionConfig.get_sandbox_url = get_sandbox_url
    SandboxBase.get_host = get_host
    SandboxBase._file_url = file_url
    _PATCHED = True
