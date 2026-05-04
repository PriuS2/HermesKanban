"""JSON serializers for Hermes Kanban dataclasses and SQLite rows."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .hermes_imports import kanban_db


def task_dict(task: kanban_db.Task, *, include_body: bool = True) -> dict[str, Any]:
    data = asdict(task)
    if not include_body and data.get("body"):
        body = str(data["body"])
        data["body_preview"] = body[:240] + ("…" if len(body) > 240 else "")
        data["body"] = None
    try:
        data["age"] = kanban_db.task_age(task)
    except Exception:
        data["age"] = {}
    return data


def comment_dict(comment: kanban_db.Comment) -> dict[str, Any]:
    return asdict(comment)


def event_dict(event: kanban_db.Event) -> dict[str, Any]:
    return asdict(event)


def run_dict(run: kanban_db.Run) -> dict[str, Any]:
    return asdict(run)


def links_for(conn, task_id: str) -> dict[str, list[str]]:
    return {
        "parents": [
            row["parent_id"]
            for row in conn.execute(
                "SELECT parent_id FROM task_links WHERE child_id = ? ORDER BY parent_id",
                (task_id,),
            ).fetchall()
        ],
        "children": [
            row["child_id"]
            for row in conn.execute(
                "SELECT child_id FROM task_links WHERE parent_id = ? ORDER BY child_id",
                (task_id,),
            ).fetchall()
        ],
    }


def row_dict(row) -> dict[str, Any]:
    return dict(row) if row is not None else {}
