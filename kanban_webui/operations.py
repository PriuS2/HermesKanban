"""Read-only board-level operations summaries for KanbanWebUI."""
from __future__ import annotations

import time
from typing import Any

from .hermes_imports import kanban_db
from .serializers import event_dict, run_dict, task_dict

FAILURE_EVENT_KINDS = {
    "gave_up",
    "spawn_failed",
    "timed_out",
    "crashed",
    "protocol_violation",
    "reclaimed",
}
HEARTBEAT_OVERDUE_SECONDS = 300
BACKOFF_BASE_SECONDS = 10
BACKOFF_CAP_SECONDS = 300


def build_operations_summary(
    conn,
    *,
    board: str,
    now: int | None = None,
    recent_limit: int = 20,
) -> dict[str, Any]:
    """Build a read-only operations snapshot from existing Kanban DB rows."""
    current = int(now if now is not None else time.time())
    limit = max(1, min(int(recent_limit), 100))
    default_failure_limit = int(getattr(kanban_db, "DEFAULT_FAILURE_LIMIT", 2) or 2)
    tasks = kanban_db.list_tasks(conn, include_archived=False)

    running_items = [_running_item(conn, task, current) for task in tasks if task.status == "running" or kanban_db.active_run(conn, task.id)]
    retry_items = [
        _failure_item(conn, task, current, default_failure_limit, include_backoff=True)
        for task in tasks
        if task.status == "ready" and int(task.consecutive_failures or 0) > 0 and task.last_failure_error
    ]
    retry_items.sort(key=lambda item: (item["eligible_at"] or 0, -int(item["attempt"]), item["task"]["id"]))

    blocked_items = [
        _failure_item(conn, task, current, default_failure_limit, include_backoff=False)
        for task in tasks
        if task.status == "blocked"
        and int(task.consecutive_failures or 0) > 0
        and (task.last_failure_error or _latest_failure_event(conn, task.id))
    ]
    blocked_items.sort(key=lambda item: (-(item["last_failure_at"] or 0), item["task"]["id"]))

    recent_failures = _recent_failure_events(conn, limit)
    summary = {
        "running": len(running_items),
        "claimed": sum(1 for task in tasks if task.claim_lock),
        "heartbeat_overdue": sum(1 for item in running_items if item["heartbeat"]["overdue"]),
        "ready": sum(1 for task in tasks if task.status == "ready"),
        "ready_unassigned": sum(1 for task in tasks if task.status == "ready" and not task.assignee),
        "retry_candidates": len(retry_items),
        "blocked_after_retries": len(blocked_items),
        "recent_failures": len(recent_failures),
    }
    return {
        "board": board,
        "now": current,
        "summary": summary,
        "running": running_items,
        "retry_queue": retry_items,
        "blocked_after_retries": blocked_items,
        "recent_failures": recent_failures,
        "advisory_backoff": "estimated_backoff_seconds is advisory until dispatcher-level backoff is implemented.",
    }


def _task_preview(task: kanban_db.Task) -> dict[str, Any]:
    return task_dict(task, include_body=False)


def _running_item(conn, task: kanban_db.Task, now: int) -> dict[str, Any]:
    active = kanban_db.active_run(conn, task.id)
    latest_event = _latest_event(conn, task.id)
    heartbeat_at = task.last_heartbeat_at or (active.last_heartbeat_at if active else None)
    heartbeat_age = now - int(heartbeat_at) if heartbeat_at else None
    started_at = active.started_at if active else task.started_at
    max_runtime = task.max_runtime_seconds or (active.max_runtime_seconds if active else None)
    return {
        "task": _task_preview(task),
        "run": run_dict(active) if active else None,
        "heartbeat": {
            "last_heartbeat_at": heartbeat_at,
            "age_seconds": heartbeat_age,
            "overdue": bool(heartbeat_age is not None and heartbeat_age > HEARTBEAT_OVERDUE_SECONDS),
        },
        "claim": {
            "lock": task.claim_lock,
            "expires": task.claim_expires,
            "expires_in_seconds": (int(task.claim_expires) - now) if task.claim_expires else None,
        },
        "worker": {
            "pid": task.worker_pid or (active.worker_pid if active else None),
            "elapsed_seconds": (now - int(started_at)) if started_at else None,
            "max_runtime_seconds": max_runtime,
        },
        "workspace": {"kind": task.workspace_kind, "path": task.workspace_path},
        "last_event": event_dict(latest_event) if latest_event else None,
    }


def _failure_item(
    conn,
    task: kanban_db.Task,
    now: int,
    default_failure_limit: int,
    *,
    include_backoff: bool,
) -> dict[str, Any]:
    failure_event = _latest_failure_event(conn, task.id)
    last_failure_at = _last_failure_at(conn, task, failure_event)
    attempt = int(task.consecutive_failures or 0)
    max_retries = int(task.max_retries or default_failure_limit)
    item: dict[str, Any] = {
        "task": _task_preview(task),
        "attempt": attempt,
        "max_retries": max_retries,
        "last_error": task.last_failure_error,
        "last_failure_kind": failure_event.kind if failure_event else None,
        "last_failure_at": last_failure_at,
    }
    if include_backoff:
        estimated = min(BACKOFF_CAP_SECONDS, BACKOFF_BASE_SECONDS * (2 ** max(0, attempt - 1)))
        eligible_at = (last_failure_at + estimated) if last_failure_at else None
        eligible_in = max(0, eligible_at - now) if eligible_at else 0
        item.update(
            {
                "estimated_backoff_seconds": estimated,
                "eligible_at": eligible_at,
                "eligible_in_seconds": eligible_in,
                "state": "eligible" if eligible_in == 0 else "estimated_wait",
            }
        )
    return item


def _latest_event(conn, task_id: str):
    events = kanban_db.list_events(conn, task_id)
    return events[-1] if events else None


def _latest_failure_event(conn, task_id: str):
    events = [event for event in kanban_db.list_events(conn, task_id) if event.kind in FAILURE_EVENT_KINDS]
    return events[-1] if events else None


def _last_failure_at(conn, task: kanban_db.Task, failure_event) -> int | None:
    if failure_event is not None:
        return int(failure_event.created_at)
    runs = kanban_db.list_runs(conn, task.id, include_active=False)
    ended = [int(run.ended_at) for run in runs if run.ended_at]
    if ended:
        return max(ended)
    if task.started_at:
        return int(task.started_at)
    if task.created_at:
        return int(task.created_at)
    return None


def _recent_failure_events(conn, recent_limit: int) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in FAILURE_EVENT_KINDS)
    rows = conn.execute(
        f"""
        SELECT *
          FROM task_events
         WHERE kind IN ({placeholders})
         ORDER BY id DESC
         LIMIT ?
        """,
        (*sorted(FAILURE_EVENT_KINDS), recent_limit),
    ).fetchall()
    events = []
    for row in rows:
        events.append(
            {
                "id": row["id"],
                "task_id": row["task_id"],
                "kind": row["kind"],
                "payload": _parse_payload(row["payload"]),
                "created_at": row["created_at"],
                "run_id": row["run_id"] if "run_id" in row.keys() else None,
            }
        )
    events.sort(key=lambda event: event["id"], reverse=True)
    return events


def _parse_payload(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    try:
        import json

        return json.loads(value)
    except Exception:
        return None
