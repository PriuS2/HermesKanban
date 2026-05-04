"""Best-effort service/status helpers."""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from .config import get_settings
from .hermes_imports import kanban_db


def _cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _gateway_hint() -> dict:
    if not _cmd_exists("pgrep"):
        return {"available": False, "reason": "pgrep not available"}
    try:
        out = subprocess.run(
            ["pgrep", "-af", "hermes.*gateway|gateway.*hermes"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=1,
            check=False,
        ).stdout.strip()
    except Exception as exc:  # pragma: no cover - host specific
        return {"available": False, "reason": str(exc)}
    rows = [line for line in out.splitlines() if line.strip()]
    return {"available": bool(rows), "processes": rows[:5]}


def service_status() -> dict:
    settings = get_settings()
    board = kanban_db.get_current_board()
    db_path = kanban_db.kanban_db_path(board=board)
    return {
        "service": "kanban-webui",
        "ok": True,
        "now": int(time.time()),
        "pid": os.getpid(),
        "host": settings.host,
        "port": settings.port,
        "state_dir": str(settings.state_dir),
        "log_path": str(settings.log_path),
        "current_board": board,
        "db_path": str(db_path),
        "db_exists": Path(db_path).exists(),
        "hermes_home": str(kanban_db.kanban_home()),
        "gateway": _gateway_hint(),
    }
