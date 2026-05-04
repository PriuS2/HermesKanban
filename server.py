"""Run KanbanWebUI with uvicorn.

Usage:
  python3 server.py --host 127.0.0.1 --port 8790
"""
from __future__ import annotations

import argparse

import uvicorn

from kanban_webui.config import get_settings


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Hermes KanbanWebUI")
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("kanban_webui.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
