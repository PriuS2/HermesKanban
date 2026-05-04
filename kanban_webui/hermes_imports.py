"""Hermes import helpers.

The service runs from this standalone repo but deliberately reuses the installed
Hermes Kanban DB module as the single source of truth.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_hermes_importable() -> None:
    """Put the local Hermes checkout on sys.path when it is not installed.

    tjseh0091's Hermes source normally lives at ~/.hermes/hermes-agent and is
    already injected in Hermes sessions. The start script may run outside that
    environment, so make path resolution explicit and predictable.
    """
    candidates = []
    env_root = os.environ.get("HERMES_AGENT_ROOT")
    if env_root:
        candidates.append(Path(env_root).expanduser())

    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        hh = Path(hermes_home).expanduser()
        candidates.extend([
            hh / "hermes-agent",
            hh.parent / "hermes-agent",
            hh.parent.parent / ".hermes" / "hermes-agent",
        ])

    user = os.environ.get("USER")
    if user:
        candidates.append(Path("/home") / user / ".hermes" / "hermes-agent")

    candidates.extend(
        [
            Path.home() / ".hermes" / "hermes-agent",
            Path.home() / ".local" / "share" / "hermes-agent",
        ]
    )
    for candidate in candidates:
        if (candidate / "hermes_cli" / "kanban_db.py").is_file():
            s = str(candidate)
            if s not in sys.path:
                sys.path.insert(0, s)
            return


ensure_hermes_importable()

try:  # noqa: E402 - path setup above is intentional
    from hermes_cli import kanban_db  # type: ignore
except Exception as exc:  # pragma: no cover - depends on host install
    raise RuntimeError(
        "Could not import hermes_cli.kanban_db. Set HERMES_AGENT_ROOT to the "
        "Hermes Agent checkout that contains hermes_cli/kanban_db.py."
    ) from exc
