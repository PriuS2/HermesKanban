"""Feature registry used by tests and the UI to keep CLI parity visible."""
from __future__ import annotations

CLI_PARITY = [
    {"cli": "init", "api": "POST /api/init", "ui": "first-load init button"},
    {"cli": "boards list", "api": "GET /api/boards", "ui": "board switcher"},
    {"cli": "boards create", "api": "POST /api/boards", "ui": "new board modal"},
    {"cli": "boards rename", "api": "PATCH /api/boards/{slug}", "ui": "board settings"},
    {"cli": "boards rm", "api": "DELETE /api/boards/{slug}", "ui": "board settings danger zone"},
    {"cli": "boards switch", "api": "POST /api/boards/{slug}/switch", "ui": "board switcher"},
    {"cli": "create", "api": "POST /api/tasks", "ui": "quick/advanced create"},
    {"cli": "list", "api": "GET /api/board", "ui": "columns/table/filter"},
    {"cli": "show", "api": "GET /api/tasks/{task_id}", "ui": "drawer detail"},
    {"cli": "assign", "api": "POST /api/tasks/{task_id}/assign", "ui": "drawer/card quick action"},
    {"cli": "link", "api": "POST /api/links", "ui": "dependency editor"},
    {"cli": "unlink", "api": "DELETE /api/links", "ui": "dependency editor"},
    {"cli": "claim", "api": "POST /api/tasks/{task_id}/claim", "ui": "advanced action"},
    {"cli": "heartbeat", "api": "POST /api/tasks/{task_id}/heartbeat", "ui": "Live Run Monitor"},
    {"cli": "comment", "api": "POST /api/tasks/{task_id}/comments", "ui": "drawer comments"},
    {"cli": "complete", "api": "POST /api/tasks/{task_id}/complete", "ui": "done drop/dialog"},
    {"cli": "block", "api": "POST /api/tasks/{task_id}/block", "ui": "blocked drop/dialog"},
    {"cli": "unblock", "api": "POST /api/tasks/{task_id}/unblock", "ui": "unblock action"},
    {"cli": "archive", "api": "POST /api/tasks/{task_id}/archive", "ui": "archive action"},
    {"cli": "tail/watch", "api": "GET /api/events", "ui": "live refresh"},
    {"cli": "runs", "api": "GET /api/tasks/{task_id}/runs", "ui": "drawer run history"},
    {"cli": "assignees", "api": "GET /api/assignees", "ui": "assignee picker"},
    {"cli": "dispatch", "api": "POST /api/dispatch", "ui": "service actions"},
    {"cli": "stats", "api": "GET /api/stats", "ui": "KPI row"},
    {"cli": "log", "api": "GET /api/tasks/{task_id}/log", "ui": "Live Run Monitor log tab"},
    {"cli": "context", "api": "GET /api/tasks/{task_id}/context", "ui": "drawer context tab"},
    {"cli": "notify-*", "api": "GET/POST/DELETE /api/notify", "ui": "advanced drawer"},
    {"cli": "gc", "api": "POST /api/gc", "ui": "maintenance panel"},
    {"cli": "daemon", "api": "GET /api/daemon", "ui": "deprecated note"},
]


def registry() -> dict:
    return {"cli_parity": CLI_PARITY, "count": len(CLI_PARITY)}
