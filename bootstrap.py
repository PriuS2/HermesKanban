"""Small bootstrap helper for local service directories."""
from __future__ import annotations

from kanban_webui.config import get_settings


def main() -> None:
    settings = get_settings()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    settings.log_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"state_dir={settings.state_dir}")
    print(f"log_path={settings.log_path}")
    print(f"url=http://{settings.host}:{settings.port}")


if __name__ == "__main__":
    main()
