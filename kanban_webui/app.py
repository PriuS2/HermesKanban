"""FastAPI entrypoint for Hermes KanbanWebUI."""
from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth import require_auth
from .config import STATIC_DIR, get_settings
from .kanban_api import router as kanban_router
from .service_status import service_status


MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def _split_host(value: str) -> str:
    host = (value or "").strip()
    if host.startswith("[") and "]" in host:
        return host[1:host.index("]")].lower()
    if host.count(":") > 1:
        return host.lower()
    return host.rsplit(":", 1)[0].strip().rstrip(".").lower()


def _allowed_hostnames(settings) -> set[str]:
    raw = os.environ.get("HERMES_KANBAN_WEBUI_ALLOWED_HOSTS", "hermes.tailafe8b6.ts.net")
    names = {"localhost", "testserver", "127.0.0.1", "::1"}
    if settings.host not in {"0.0.0.0", "::", "[::]"}:
        names.add(settings.host)
    for item in raw.split(","):
        value = _split_host(item)
        if value:
            names.add(value)
    return names


def _host_allowed(request: Request, settings) -> bool:
    host = _split_host(request.headers.get("host") or request.url.netloc)
    if not host:
        return False
    if host in _allowed_hostnames(settings):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip in TAILSCALE_CGNAT


def _same_origin(request: Request, value: str) -> bool:
    parsed = urlparse(value)
    target_host = request.headers.get("host") or request.url.netloc
    return bool(parsed.scheme in {"http", "https"} and parsed.netloc == target_host)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_title, version="0.1.0")

    @app.middleware("http")
    async def validate_host_and_reject_cross_origin_mutations(request: Request, call_next):
        """Block DNS-rebinding hosts and browser drive-by writes.

        The app is loopback-first and may be exposed through a Tailscale-only
        proxy. Rejecting unknown Host headers prevents an attacker-controlled
        DNS name from becoming "same-origin" with itself while resolving to the
        local/tailnet service.
        """
        if not _host_allowed(request, settings):
            return JSONResponse({"detail": "host not allowed"}, status_code=400)
        if request.method.upper() in MUTATING_METHODS:
            sec_fetch_site = request.headers.get("sec-fetch-site", "").lower()
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            blocked = sec_fetch_site == "cross-site"
            if origin:
                blocked = blocked or not _same_origin(request, origin)
            elif referer:
                blocked = blocked or not _same_origin(request, referer)
            if blocked:
                return JSONResponse({"detail": "cross-origin mutation blocked"}, status_code=403)
        return await call_next(request)

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "service": "kanban-webui", "port": get_settings().port}

    @app.get("/service/status", dependencies=[Depends(require_auth)])
    def root_service_status() -> dict:
        return service_status()

    app.include_router(kanban_router, dependencies=[Depends(require_auth)])

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/{path:path}")
    def spa_fallback(path: str) -> FileResponse:
        # API 404s are handled by the router before this fallback. Everything
        # else gets the SPA shell for bookmarkable board URLs.
        file_path = STATIC_DIR / path
        if path and file_path.is_file() and file_path.resolve().is_relative_to(STATIC_DIR.resolve()):
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))

    return app


app = create_app()
