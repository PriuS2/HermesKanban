"""Runtime settings for KanbanWebUI."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def real_user_home() -> Path:
    """Return the OS user's home, not Hermes profile HOME.

    Hermes Agent sessions may set HOME to ~/.hermes/profiles/<profile>/home.
    KanbanWebUI service state should live in /home/<user>/.hermes instead.
    """
    override = os.environ.get("HERMES_REAL_HOME")
    if override:
        return Path(override).expanduser()
    user = os.environ.get("USER")
    if user and (Path("/home") / user).exists():
        return Path("/home") / user
    return Path.home()


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8790
    log_path: Path = Path.home() / ".hermes" / "logs" / "kanban-webui.log"
    state_dir: Path = Path.home() / ".hermes" / "kanban-webui"
    token: str | None = None
    app_title: str = "Hermes KanbanWebUI"


def get_settings() -> Settings:
    user_home = real_user_home()
    host = os.environ.get("HERMES_KANBAN_WEBUI_HOST", "127.0.0.1")
    port = int(os.environ.get("HERMES_KANBAN_WEBUI_PORT", "8790"))
    log_path = Path(os.environ.get("HERMES_KANBAN_WEBUI_LOG", str(user_home / ".hermes" / "logs" / "kanban-webui.log"))).expanduser()
    state_dir = Path(os.environ.get("HERMES_KANBAN_WEBUI_STATE", str(user_home / ".hermes" / "kanban-webui"))).expanduser()
    token = os.environ.get("HERMES_KANBAN_WEBUI_TOKEN") or None
    return Settings(host=host, port=port, log_path=log_path, state_dir=state_dir, token=token)


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
