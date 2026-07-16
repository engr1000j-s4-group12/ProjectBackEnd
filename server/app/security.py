from __future__ import annotations

import base64
import binascii
import hmac
import os

from starlette.datastructures import Headers
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send


def _same(value: str, expected: str) -> bool:
    return bool(expected) and hmac.compare_digest(value.encode(), expected.encode())


class AccessControlMiddleware:
    """Optional Basic/Bearer protection without buffering streamed responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        headers = Headers(scope=scope)
        denied: Response | None = None
        if path.startswith("/admin") or path.startswith("/api/admin"):
            denied = self._check_admin(headers)
        elif path.startswith("/api/device/"):
            denied = self._check_bearer(headers, "DEVICE_API_TOKEN", "DEVICE_UNAUTHORIZED")
        elif path == "/mcp":
            denied = self._check_bearer(headers, "MCP_API_TOKEN", "MCP_UNAUTHORIZED")
        if denied is not None:
            await denied(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _check_admin(self, headers: Headers) -> Response | None:
        username = os.getenv("ADMIN_USERNAME", "")
        password = os.getenv("ADMIN_PASSWORD", "")
        if not username or not password:
            return None
        authorization = headers.get("authorization", "")
        try:
            scheme, encoded = authorization.split(" ", 1)
            decoded = base64.b64decode(encoded).decode("utf-8")
            supplied_user, supplied_password = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError, binascii.Error):
            scheme = supplied_user = supplied_password = ""
        if scheme.lower() == "basic" and _same(supplied_user, username) and _same(
            supplied_password, password
        ):
            return None
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Longbin Guide Admin"'},
        )

    def _check_bearer(
        self, headers: Headers, variable: str, error_code: str
    ) -> Response | None:
        expected = os.getenv(variable, "")
        if not expected:
            return None
        authorization = headers.get("authorization", "")
        supplied = ""
        if authorization.lower().startswith("bearer "):
            supplied = authorization[7:].strip()
        supplied = headers.get("x-device-token", supplied)
        if _same(supplied, expected):
            return None
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "error": {
                    "code": error_code,
                    "message": "Invalid or missing access token.",
                    "retryable": False,
                    "speak": "设备认证失败，请联系工作人员。",
                },
            },
        )
