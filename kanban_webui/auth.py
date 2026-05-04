"""Optional bearer-token auth.

Localhost-only operation is the default. If HERMES_KANBAN_WEBUI_TOKEN is set,
all /api routes require either Authorization: Bearer *** or X-Kanban-Token.
Tokens are intentionally not accepted in query strings.
"""
from __future__ import annotations

from fastapi import HTTPException, Request, status

from .config import get_settings


async def require_auth(request: Request) -> None:
    token = get_settings().token
    if not token:
        return
    supplied = request.headers.get("x-kanban-token")
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        supplied = auth.split(" ", 1)[1].strip()
    if supplied != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="auth token required")
