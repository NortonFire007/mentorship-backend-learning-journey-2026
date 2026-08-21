from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Scope, Receive, Send
from mcp.server.fastmcp import FastMCP
from src.core.config import settings


import secrets

def verify_auth(scope: Scope) -> bool:
    """
    Verify that the request scope contains a valid Authorization header
    with Bearer token matching settings.MCP_API_KEY.
    """
    headers = dict(scope.get("headers", []))
    auth_header = headers.get(b"authorization", b"").decode("utf-8")
    if not auth_header.startswith("Bearer "):
        return False
    token = auth_header[7:].strip()
    return secrets.compare_digest(token, settings.MCP_API_KEY)


class MCPAuthMiddleware:
    """
    ASGI middleware enforcing Bearer token authentication for FastMCP endpoints.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            if not verify_auth(scope):
                response = JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: Invalid or missing bearer token"}
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


mcp = FastMCP("AI Admin Panel", stateless_http=True)
mcp.settings.streamable_http_path = "/"


def get_asgi_app() -> ASGIApp:
    """
    Return the authenticated Starlette ASGI application for mounting into FastAPI.
    """
    return MCPAuthMiddleware(mcp.streamable_http_app())


# Attach get_asgi_app to the FastMCP instance so `mcp.get_asgi_app()` works seamlessly
mcp.get_asgi_app = get_asgi_app  # type: ignore[attr-defined]
