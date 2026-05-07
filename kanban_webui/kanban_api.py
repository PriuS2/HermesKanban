"""FastAPI routes that map KanbanWebUI controls to hermes_cli.kanban_db.

The important rule: Hermes' existing kanban_db module remains the single source
of truth. This router only serializes, validates, and provides UX-friendly API
surfaces around those functions.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Iterable, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .hermes_imports import kanban_db
from .serializers import comment_dict, event_dict, links_for, run_dict, task_dict
from .service_status import service_status
from .ui_registry import registry
from .config import get_settings
from . import app_update, workflow_drafts, workflow_planner, workflows

router = APIRouter(prefix="/api")

BOARD_COLUMNS = ["triage", "todo", "ready", "running", "blocked", "done"]
INITIAL_TASK_STATUSES = {"ready", "todo", "triage"}
UPDATE_TASK_STATUSES = {"done", "blocked", "ready", "archived", "todo", "triage", "running"}
WRITEABLE_TASK_FIELDS = {
    "title",
    "body",
    "priority",
    "tenant",
    "workspace_kind",
    "workspace_path",
    "max_runtime_seconds",
    "workflow_template_id",
    "current_step_key",
    "skills",
}


class CreateBoardBody(BaseModel):
    slug: str
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    switch: bool = False


class PatchBoardBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    archived: Optional[bool] = None


class CreateTaskBody(BaseModel):
    title: str
    body: Optional[str] = None
    assignee: Optional[str] = None
    created_by: Optional[str] = "kanban-webui"
    workspace_kind: str = "scratch"
    workspace_path: Optional[str] = None
    tenant: Optional[str] = None
    priority: int = 0
    parents: list[str] = Field(default_factory=list)
    triage: bool = False
    idempotency_key: Optional[str] = None
    max_runtime_seconds: Optional[int] = None
    skills: Optional[list[str]] = None
    status: Optional[str] = None
    workflow_template_id: Optional[str] = None
    current_step_key: Optional[str] = None


class WorkflowRequestBody(BaseModel):
    template_id: str
    title: str
    body: Optional[str] = None
    instance_id: Optional[str] = None
    assignee_overrides: dict[str, str] = Field(default_factory=dict)
    created_by: Optional[str] = "kanban-webui"
    workspace_kind: str = "scratch"
    workspace_path: Optional[str] = None
    tenant: Optional[str] = None
    priority_offset: int = 0


class WorkflowAttachmentBody(BaseModel):
    filename: str
    content: str
    content_type: Optional[str] = "text/plain"


class WorkflowDraftCreateBody(BaseModel):
    prompt: str
    planner_profile: Optional[str] = None
    max_steps: Optional[int] = None
    attachments: list[WorkflowAttachmentBody] = Field(default_factory=list)


class WorkflowDraftReviseBody(BaseModel):
    revision_prompt: str


class WorkflowDraftInstantiateBody(BaseModel):
    instance_id: Optional[str] = None
    created_by: Optional[str] = "kanban-webui"
    workspace_kind: str = "scratch"
    workspace_path: Optional[str] = None
    tenant: Optional[str] = None
    priority_offset: int = 0


class BulkCreateBody(BaseModel):
    lines: Optional[str] = None
    tasks: list[CreateTaskBody] = Field(default_factory=list)
    defaults: dict[str, Any] = Field(default_factory=dict)


class UpdateTaskBody(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    assignee: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    tenant: Optional[str] = None
    workspace_kind: Optional[str] = None
    workspace_path: Optional[str] = None
    max_runtime_seconds: Optional[int] = None
    skills: Optional[list[str]] = None
    workflow_template_id: Optional[str] = None
    current_step_key: Optional[str] = None
    result: Optional[str] = None
    summary: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    block_reason: Optional[str] = None


class AssignBody(BaseModel):
    assignee: Optional[str] = None
    profile: Optional[str] = None


class ClaimBody(BaseModel):
    ttl_seconds: Optional[int] = None
    claimer: Optional[str] = None


class HeartbeatBody(BaseModel):
    note: Optional[str] = None
    ttl_seconds: Optional[int] = None
    claimer: Optional[str] = None
    extend_claim: bool = False


class CommentBody(BaseModel):
    body: str
    author: Optional[str] = "kanban-webui"


class CompleteBody(BaseModel):
    ids: list[str] = Field(default_factory=list)
    result: Optional[str] = None
    summary: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class BlockBody(BaseModel):
    ids: list[str] = Field(default_factory=list)
    reason: Optional[str] = None


class BulkTaskBody(BaseModel):
    ids: list[str]
    status: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[int] = None
    result: Optional[str] = None
    summary: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    reason: Optional[str] = None


class LinkBody(BaseModel):
    parent_id: str
    child_id: str


class NotifyBody(BaseModel):
    task_id: str
    platform: str = "webui"
    chat_id: str = "kanban-webui"
    thread_id: Optional[str] = None
    user_id: Optional[str] = None


HOME_CHANNEL_ENVS = {
    "telegram": "TELEGRAM_HOME_CHANNEL",
    "discord": "DISCORD_HOME_CHANNEL",
    "slack": "SLACK_HOME_CHANNEL",
    "signal": "SIGNAL_HOME_CHANNEL",
    "mattermost": "MATTERMOST_HOME_CHANNEL",
    "sms": "SMS_HOME_CHANNEL",
    "dingtalk": "DINGTALK_HOME_CHANNEL",
    "feishu": "FEISHU_HOME_CHANNEL",
    "wecom": "WECOM_HOME_CHANNEL",
    "weixin": "WEIXIN_HOME_CHANNEL",
    "bluebubbles": "BLUEBUBBLES_HOME_CHANNEL",
    "qqbot": "QQBOT_HOME_CHANNEL",
    "yuanbao": "YUANBAO_HOME_CHANNEL",
}
LEGACY_HOME_CHANNEL_ENVS = {"qqbot": "QQ_HOME_CHANNEL"}


def _add_home_channel(result: list[dict[str, str]], seen: set[str], *, platform: str, chat_id: Any, name: Any = None, thread_id: Any = None) -> None:
    platform_name = str(platform or "").strip().lower()
    chat_text = str(chat_id or "").strip()
    if not platform_name or not chat_text or platform_name in seen:
        return
    result.append(
        {
            "platform": platform_name,
            "chat_id": chat_text,
            "thread_id": str(thread_id or ""),
            "name": str(name or "Home"),
        }
    )
    seen.add(platform_name)


def _yaml_scalar(value: str) -> str:
    text = value.split("#", 1)[0].strip()
    if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
        return text[1:-1]
    return text


def _config_paths() -> list[Path]:
    paths: list[Path] = []
    if os.getenv("HERMES_CONFIG"):
        paths.append(Path(os.environ["HERMES_CONFIG"]).expanduser())
    if os.getenv("HERMES_HOME"):
        paths.append(Path(os.environ["HERMES_HOME"]).expanduser() / "config.yaml")
    if os.getenv("USER"):
        paths.append(Path("/home") / os.environ["USER"] / ".hermes" / "config.yaml")
    paths.append(Path.home() / ".hermes" / "config.yaml")
    unique: list[Path] = []
    for path in paths:
        if path not in unique:
            unique.append(path)
    return unique


def _add_home_channels_from_config(result: list[dict[str, str]], seen: set[str]) -> None:
    """Small YAML fallback for WebUI venvs without PyYAML/gateway deps."""
    for path in _config_paths():
        if not path.is_file():
            continue
        current_platform: Optional[str] = None
        current_indent = 0
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for raw_line in lines:
            if not raw_line.strip() or raw_line.lstrip().startswith("#"):
                continue
            indent = len(raw_line) - len(raw_line.lstrip())
            line = raw_line.strip()
            if indent == 0 and line.endswith(":"):
                candidate = line[:-1].strip().lower()
                current_platform = candidate if candidate in HOME_CHANNEL_ENVS else None
                current_indent = indent
                continue
            if indent == 0:
                current_platform = None
                for platform, env_name in HOME_CHANNEL_ENVS.items():
                    if line.startswith(f"{env_name}:"):
                        _add_home_channel(result, seen, platform=platform, chat_id=_yaml_scalar(line.split(":", 1)[1]))
                continue
            if current_platform and indent > current_indent and line.startswith("home_channel:"):
                _add_home_channel(result, seen, platform=current_platform, chat_id=_yaml_scalar(line.split(":", 1)[1]))
        break


def _configured_home_channels() -> list[dict[str, str]]:
    """Return gateway home channels available for dashboard-style toggles.

    Prefer Hermes' GatewayConfig when importable, then documented env vars, then
    a tiny config.yaml fallback for this standalone WebUI's lean virtualenv.
    """
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    try:
        from gateway.config import load_gateway_config

        gw_cfg = load_gateway_config()
        for platform, pcfg in (getattr(gw_cfg, "platforms", {}) or {}).items():
            home = getattr(pcfg, "home_channel", None)
            if not home:
                continue
            platform_name = getattr(platform, "value", str(platform))
            _add_home_channel(
                result,
                seen,
                platform=platform_name,
                chat_id=getattr(home, "chat_id", ""),
                thread_id=getattr(home, "thread_id", None),
                name=getattr(home, "name", None),
            )
    except Exception:
        pass

    for platform, env_name in HOME_CHANNEL_ENVS.items():
        chat_id = os.getenv(env_name) or os.getenv(LEGACY_HOME_CHANNEL_ENVS.get(platform, ""))
        if not chat_id:
            continue
        base = env_name.removesuffix("_CHANNEL")
        _add_home_channel(
            result,
            seen,
            platform=platform,
            chat_id=chat_id,
            thread_id=os.getenv(f"{base}_CHANNEL_THREAD_ID") or os.getenv(f"{base}_THREAD_ID"),
            name=os.getenv(f"{base}_CHANNEL_NAME") or os.getenv(f"{base}_NAME") or "Home",
        )

    _add_home_channels_from_config(result, seen)

    result.sort(key=lambda item: item["platform"])
    return result


def _home_for_platform(platform: str) -> dict[str, str]:
    home = next((item for item in _configured_home_channels() if item["platform"] == platform), None)
    if not home:
        raise HTTPException(status_code=404, detail=f"No home channel configured for platform {platform!r}")
    return home


def _home_subscription_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get("platform") or ""),
        str(item.get("chat_id") or ""),
        str(item.get("thread_id") or ""),
    )


def _normalize_board(slug: Optional[str]) -> str:
    try:
        normed = kanban_db._normalize_board_slug(slug) if slug else kanban_db.get_current_board()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return normed or "default"


def _resolve_board(slug: Optional[str]) -> str:
    board = _normalize_board(slug)
    if not kanban_db.board_exists(board):
        raise HTTPException(status_code=404, detail=f"board {board!r} does not exist")
    return board


def _clamp_max_steps(value: Optional[int], default: int, maximum: int) -> int:
    if value is None:
        return max(1, min(int(default), int(maximum)))
    return max(1, min(int(value), int(maximum)))


def _raise_proposal_errors(validation: dict[str, Any]) -> None:
    errors = validation.get("errors") or []
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})


def _load_workflow_draft_for_board(settings: Settings, draft_id: str, board: str) -> dict[str, Any]:
    try:
        draft = workflow_drafts.load_draft(settings, draft_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"workflow draft {draft_id!r} not found") from exc
    except workflow_drafts.DraftError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if draft.get("board") != board:
        raise HTTPException(status_code=404, detail=f"workflow draft {draft_id!r} not found")
    return draft


def _raise_not_applyable(draft: dict[str, Any]) -> None:
    proposal = draft.get("proposal") or {}
    if proposal.get("applyable") is False:
        raise HTTPException(status_code=409, detail="workflow draft is not applyable; revise it before applying")


def _conn(board: Optional[str] = None):
    return kanban_db.connect(board=_resolve_board(board))


def _board_counts(slug: str) -> dict[str, int]:
    try:
        path = kanban_db.kanban_db_path(board=slug)
        if not path.exists():
            return {}
        conn = kanban_db.connect(board=slug)
        try:
            rows = conn.execute("SELECT status, COUNT(*) AS n FROM tasks GROUP BY status").fetchall()
            return {row["status"]: int(row["n"]) for row in rows}
        finally:
            conn.close()
    except Exception:
        return {}


def _board_payload(slug: str) -> dict[str, Any]:
    meta = kanban_db.read_board_metadata(slug)
    meta["counts"] = _board_counts(slug)
    meta["total"] = sum(meta["counts"].values())
    meta["is_current"] = slug == kanban_db.get_current_board()
    return meta


def _all_ids(path_id: str, ids: Iterable[str]) -> list[str]:
    out = [path_id]
    for task_id in ids:
        if task_id and task_id not in out:
            out.append(task_id)
    return out


def _normalize_assignee(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return kanban_db._canonical_assignee(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _insert_event(conn, task_id: str, kind: str, payload: Optional[dict[str, Any]] = None) -> None:
    conn.execute(
        "INSERT INTO task_events (task_id, kind, payload, created_at) VALUES (?, ?, ?, ?)",
        (task_id, kind, json.dumps(payload, ensure_ascii=False) if payload else None, int(time.time())),
    )


def _set_status_direct(conn, task_id: str, status: str) -> bool:
    if status == "running":
        raise HTTPException(status_code=400, detail="use claim/dispatch instead of direct running status")
    with kanban_db.write_txn(conn):
        prev = conn.execute("SELECT status, current_run_id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if prev is None:
            return False
        was_running = prev["status"] == "running"
        cur = conn.execute(
            """
            UPDATE tasks
               SET status = ?,
                   claim_lock = CASE WHEN ? = 'running' THEN claim_lock ELSE NULL END,
                   claim_expires = CASE WHEN ? = 'running' THEN claim_expires ELSE NULL END,
                   worker_pid = CASE WHEN ? = 'running' THEN worker_pid ELSE NULL END,
                   current_run_id = CASE WHEN ? = 'running' THEN current_run_id ELSE current_run_id END
             WHERE id = ?
            """,
            (status, status, status, status, status, task_id),
        )
        if cur.rowcount != 1:
            return False
        run_id = None
        if was_running and status != "running" and prev["current_run_id"]:
            run_id = kanban_db._end_run(
                conn,
                task_id,
                outcome="reclaimed",
                status="reclaimed",
                summary=f"status changed to {status} (kanban-webui/direct)",
            )
        _insert_event(conn, task_id, "status", {"status": status})
    if status in ("ready", "done"):
        kanban_db.recompute_ready(conn)
    return True


def _precheck_status_transition(task, status: Optional[str]) -> None:
    if status is None:
        return
    current = task.status
    allowed = True
    if status == "done":
        allowed = current in {"running", "ready", "blocked"}
    elif status == "blocked":
        allowed = current in {"running", "ready"}
    elif status == "ready":
        allowed = True
    elif status == "archived":
        allowed = current != "archived"
    elif status in {"todo", "triage"}:
        allowed = True
    elif status == "running":
        raise HTTPException(status_code=400, detail="use /claim or dispatcher to move a task to running")
    else:
        raise HTTPException(status_code=400, detail=f"unknown status {status!r}")
    if not allowed:
        raise HTTPException(status_code=409, detail=f"status transition from {current!r} to {status!r} was refused")


def _normalize_writeable_task_updates(payload: UpdateTaskBody) -> dict[str, Any]:
    """Validate and normalize PATCH fields before any DB mutation.

    This avoids validation-after-write partial mutations when a request combines
    valid fields, such as assignee, with an invalid status/title/workspace_kind.
    """
    status = payload.status
    if status is not None:
        if status not in UPDATE_TASK_STATUSES:
            raise HTTPException(status_code=400, detail=f"unknown status {status!r}")
        if status == "running":
            raise HTTPException(status_code=400, detail="use /claim or dispatcher to move a task to running")

    updates: dict[str, Any] = {}
    raw = payload.model_dump(exclude_unset=True)
    for key in WRITEABLE_TASK_FIELDS:
        if key not in raw:
            continue
        value = raw[key]
        if key == "title":
            if not str(value or "").strip():
                raise HTTPException(status_code=400, detail="title cannot be empty")
            value = str(value).strip()
        if key == "workspace_kind" and value not in kanban_db.VALID_WORKSPACE_KINDS:
            raise HTTPException(status_code=400, detail=f"workspace_kind must be one of {sorted(kanban_db.VALID_WORKSPACE_KINDS)}")
        if key == "skills" and value is not None:
            cleaned: list[str] = []
            seen: set[str] = set()
            for item in value:
                name = str(item).strip()
                if "," in name:
                    raise HTTPException(status_code=400, detail="skill names cannot contain commas")
                if name and name not in seen:
                    cleaned.append(name)
                    seen.add(name)
            value = json.dumps(cleaned, ensure_ascii=False)
        updates[key] = value
    return updates


def _apply_create_workflow_fields(
    conn,
    task_id: str,
    *,
    workflow_template_id: Optional[str],
    current_step_key: Optional[str],
) -> None:
    if workflow_template_id is None and current_step_key is None:
        return
    with kanban_db.write_txn(conn):
        conn.execute(
            "UPDATE tasks SET workflow_template_id = ?, current_step_key = ? WHERE id = ?",
            (workflow_template_id, current_step_key, task_id),
        )
        _insert_event(
            conn,
            task_id,
            "workflow_attached",
            {"template_id": workflow_template_id, "step_key": current_step_key},
        )


def _apply_task_update(conn, task_id: str, payload: UpdateTaskBody) -> dict[str, Any]:
    task = kanban_db.get_task(conn, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task {task_id} not found")

    updates = _normalize_writeable_task_updates(payload)
    assignee = _normalize_assignee(payload.assignee) if payload.assignee is not None else None
    _precheck_status_transition(task, payload.status)

    if payload.status is not None:
        status = payload.status
        if status == "done":
            ok = kanban_db.complete_task(
                conn,
                task_id,
                result=payload.result,
                summary=payload.summary,
                metadata=payload.metadata,
            )
        elif status == "blocked":
            ok = kanban_db.block_task(conn, task_id, reason=payload.block_reason)
        elif status == "ready":
            current = kanban_db.get_task(conn, task_id)
            ok = kanban_db.unblock_task(conn, task_id) if current and current.status == "blocked" else _set_status_direct(conn, task_id, "ready")
        elif status == "archived":
            ok = kanban_db.archive_task(conn, task_id)
        elif status in ("todo", "triage"):
            ok = _set_status_direct(conn, task_id, status)
        else:
            raise HTTPException(status_code=400, detail=f"unknown status {status!r}")
        if not ok:
            raise HTTPException(status_code=409, detail=f"status transition to {status!r} was refused")

    if payload.assignee is not None:
        try:
            ok = kanban_db.assign_task(conn, task_id, assignee)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if not ok:
            raise HTTPException(status_code=404, detail="task not found")

    if updates:
        with kanban_db.write_txn(conn):
            # Safe dynamic column list: every key comes from the static
            # WRITEABLE_TASK_FIELDS whitelist above; values stay parameterized.
            sets = ", ".join(f"{field} = ?" for field in updates)
            vals = list(updates.values()) + [task_id]
            sql = "UPDATE tasks SET " + sets + " WHERE id = ?"
            conn.execute(sql, vals)
            _insert_event(conn, task_id, "edited", {"fields": sorted(updates)})

    updated = kanban_db.get_task(conn, task_id)
    return task_dict(updated) if updated else {}


def _task_detail(conn, task_id: str, *, board: str) -> dict[str, Any]:
    task = kanban_db.get_task(conn, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task {task_id} not found")
    return {
        "task": task_dict(task),
        "links": links_for(conn, task_id),
        "comments": [comment_dict(c) for c in kanban_db.list_comments(conn, task_id)],
        "events": [event_dict(e) for e in kanban_db.list_events(conn, task_id)],
        "runs": [run_dict(r) for r in kanban_db.list_runs(conn, task_id)],
        "board": board,
    }


@router.get("/config")
def get_config() -> dict[str, Any]:
    return {
        "service": "kanban-webui",
        "default_language": "ko",
        "columns": BOARD_COLUMNS,
        "archived_column": "archived",
        "dangerous_statuses": ["blocked", "done", "archived"],
        "cli_parity": registry()["cli_parity"],
    }


@router.get("/service/status")
def get_service_status() -> dict[str, Any]:
    return service_status()


@router.get("/app/update-status")
def get_app_update_status() -> dict[str, Any]:
    return app_update.get_update_status()


@router.post("/app/update")
def update_app() -> dict[str, Any]:
    try:
        return app_update.apply_update()
    except app_update.UpdateBlocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except app_update.UpdateUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/init")
def init(board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _normalize_board(board)
    if selected != "default" and not kanban_db.board_exists(selected):
        kanban_db.create_board(selected)
    path = kanban_db.init_db(board=selected)
    return {"ok": True, "board": selected, "db_path": str(path)}


@router.get("/ui/registry")
def ui_registry() -> dict[str, Any]:
    return registry()


def _deprecated_template_workflows() -> None:
    raise HTTPException(
        status_code=410,
        detail="Template workflows are deprecated. Use /api/workflows/drafts instead.",
    )


@router.get("/workflows/templates")
def workflow_templates() -> dict[str, Any]:
    _deprecated_template_workflows()


@router.get("/workflows/templates/{template_id}")
def workflow_template(template_id: str) -> dict[str, Any]:
    _deprecated_template_workflows()


@router.post("/workflows/preview")
def workflow_preview(payload: WorkflowRequestBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    _deprecated_template_workflows()


@router.post("/workflows/instantiate")
def workflow_instantiate(payload: WorkflowRequestBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    _deprecated_template_workflows()


@router.post("/workflows/drafts")
def create_workflow_draft(payload: WorkflowDraftCreateBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt is required")
    settings = get_settings()
    max_steps = _clamp_max_steps(payload.max_steps, settings.workflow_default_max_steps, settings.workflow_max_steps)
    draft_id = workflow_drafts.new_draft_id()
    draft_path = workflow_drafts.draft_dir(settings, draft_id)
    conn = kanban_db.connect(board=selected)
    try:
        profiles = workflow_drafts.available_profiles(conn)
        planner_profile = workflow_drafts.select_planner_profile(
            payload.planner_profile,
            settings=settings,
            profiles=profiles,
        )
        attachments = workflow_drafts.normalize_attachment_inputs(
            draft_path,
            [item.model_dump() for item in payload.attachments],
            max_files=settings.workflow_attachment_max_files,
            max_bytes=settings.workflow_attachment_max_bytes,
        )
        proposal = workflow_planner.generate_workflow_proposal(
            prompt=prompt,
            planner_profile=planner_profile,
            max_steps=max_steps,
            attachments=attachments,
            profiles=profiles,
            settings=settings,
        )
        normalized, validation = workflow_drafts.normalize_proposal(
            proposal,
            available_profile_names=workflow_drafts.profile_names(profiles),
            max_steps=max_steps,
        )
        _raise_proposal_errors(validation)
        draft = workflow_drafts.create_draft_record(
            settings=settings,
            board=selected,
            prompt=prompt,
            planner_profile=planner_profile,
            max_steps=max_steps,
            attachments=attachments,
            proposal=normalized,
            validation=validation,
            profiles=profiles,
            draft_id=draft_id,
        )
        return {"ok": True, "board": selected, "draft": draft, "profiles": profiles}
    except workflow_planner.PlannerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except workflow_drafts.DraftError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        conn.close()


@router.get("/workflows/drafts/{draft_id}")
def get_workflow_draft(draft_id: str, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    settings = get_settings()
    draft = _load_workflow_draft_for_board(settings, draft_id, selected)
    return {"ok": True, "board": selected, "draft": draft, "profiles": draft.get("profiles") or []}


@router.post("/workflows/drafts/{draft_id}/revise")
def revise_workflow_draft(
    draft_id: str,
    payload: WorkflowDraftReviseBody,
    board: Optional[str] = Query(None),
) -> dict[str, Any]:
    selected = _resolve_board(board)
    revision_prompt = payload.revision_prompt.strip()
    if not revision_prompt:
        raise HTTPException(status_code=422, detail="revision_prompt is required")
    settings = get_settings()
    try:
        draft = _load_workflow_draft_for_board(settings, draft_id, selected)
        if draft.get("status") == "applied":
            raise HTTPException(status_code=409, detail="applied workflow drafts cannot be revised")
        profiles = draft.get("profiles") or []
        proposal = workflow_planner.generate_workflow_proposal(
            prompt=draft.get("prompt") or "",
            planner_profile=draft.get("planner_profile") or "default",
            max_steps=int(draft.get("max_steps") or settings.workflow_default_max_steps),
            attachments=draft.get("attachments") or [],
            profiles=profiles,
            settings=settings,
            previous_proposal=draft.get("proposal"),
            revision_prompt=revision_prompt,
        )
        normalized, validation = workflow_drafts.normalize_proposal(
            proposal,
            available_profile_names=workflow_drafts.profile_names(profiles),
            max_steps=int(draft.get("max_steps") or settings.workflow_max_steps),
        )
        _raise_proposal_errors(validation)
        draft = workflow_drafts.append_revision(
            settings,
            draft,
            revision_prompt=revision_prompt,
            proposal=normalized,
            validation=validation,
        )
        return {"ok": True, "board": selected, "draft": draft, "profiles": profiles}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"workflow draft {draft_id!r} not found") from exc
    except HTTPException:
        raise
    except workflow_planner.PlannerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except workflow_drafts.DraftError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workflows/drafts/{draft_id}/instantiate")
def instantiate_workflow_draft(
    draft_id: str,
    payload: WorkflowDraftInstantiateBody,
    board: Optional[str] = Query(None),
) -> dict[str, Any]:
    selected = _resolve_board(board)
    settings = get_settings()
    conn = kanban_db.connect(board=selected)
    try:
        draft = _load_workflow_draft_for_board(settings, draft_id, selected)
        if draft.get("status") == "applied":
            raise HTTPException(status_code=409, detail="workflow draft has already been applied")
        validation = draft.get("validation") or {}
        _raise_proposal_errors(validation)
        _raise_not_applyable(draft)
        result = workflows.instantiate_steps_workflow(
            conn,
            source_id=workflow_drafts.PROMPT_WORKFLOW_SOURCE_ID,
            source_name=workflow_drafts.PROMPT_WORKFLOW_SOURCE_NAME,
            steps=workflow_drafts.steps_for_instantiation(draft),
            instance_id=payload.instance_id,
            created_by=payload.created_by,
            workspace_kind=payload.workspace_kind,
            workspace_path=payload.workspace_path,
            tenant=payload.tenant,
            priority_offset=payload.priority_offset,
        )
        result["board"] = selected
        workflow_drafts.mark_applied(
            settings,
            draft,
            instance_id=result["instance_id"],
            result=result,
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"workflow draft {draft_id!r} not found") from exc
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except workflow_drafts.DraftError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        conn.close()


@router.get("/workflows/instances/{instance_id}")
def workflow_instance(instance_id: str, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        try:
            instance = workflows.workflow_instance(conn, instance_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if instance is None:
            raise HTTPException(status_code=404, detail=f"workflow instance {instance_id!r} not found")
        return {
            "board": selected,
            "instance_id": instance["instance_id"],
            "template_id": instance["template_id"],
            "tasks": [task_dict(task) for task in instance["tasks"]],
            "links": instance["links"],
            "progress": instance["progress"],
        }
    finally:
        conn.close()


@router.get("/boards")
def list_boards(include_archived: bool = Query(False)) -> dict[str, Any]:
    boards = [
        _board_payload(board["slug"])
        for board in kanban_db.list_boards(include_archived=include_archived)
    ]
    return {"boards": boards, "current": kanban_db.get_current_board()}


@router.post("/boards")
def create_board(payload: CreateBoardBody) -> dict[str, Any]:
    try:
        meta = kanban_db.create_board(
            payload.slug,
            name=payload.name,
            description=payload.description,
            icon=payload.icon,
            color=payload.color,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.switch:
        kanban_db.set_current_board(meta["slug"])
    return {"board": _board_payload(meta["slug"]), "current": kanban_db.get_current_board()}


@router.get("/boards/current")
def current_board() -> dict[str, Any]:
    slug = kanban_db.get_current_board()
    return {"current": slug, "board": _board_payload(slug)}


@router.get("/boards/{slug}")
def get_board_detail(slug: str) -> dict[str, Any]:
    board = _resolve_board(slug)
    return {"board": _board_payload(board)}


@router.patch("/boards/{slug}")
def patch_board(slug: str, payload: PatchBoardBody) -> dict[str, Any]:
    board = _resolve_board(slug)
    meta = kanban_db.write_board_metadata(
        board,
        name=payload.name,
        description=payload.description,
        icon=payload.icon,
        color=payload.color,
        archived=payload.archived,
    )
    return {"board": _board_payload(meta["slug"])}


@router.delete("/boards/{slug}")
def delete_board(slug: str, delete: bool = Query(False)) -> dict[str, Any]:
    try:
        result = kanban_db.remove_board(slug, archive=not delete)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"result": result, "current": kanban_db.get_current_board()}


@router.post("/boards/{slug}/switch")
def switch_board(slug: str) -> dict[str, Any]:
    board = _resolve_board(slug)
    kanban_db.set_current_board(board)
    return {"current": board, "board": _board_payload(board)}


@router.get("/board")
def board_view(
    board: Optional[str] = Query(None),
    tenant: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    mine: bool = Query(False),
    q: Optional[str] = Query(None),
    include_archived: bool = Query(False),
) -> dict[str, Any]:
    selected = _resolve_board(board)
    tenant = tenant.strip() or None if tenant is not None else None
    assignee = assignee.strip() or None if assignee is not None else None
    status = status.strip() or None if status is not None else None
    q = q.strip() or None if q is not None else None
    if mine and not assignee:
        import os

        assignee = os.environ.get("USER") or None
    conn = kanban_db.connect(board=selected)
    try:
        try:
            tasks = kanban_db.list_tasks(
                conn,
                assignee=assignee,
                status=status,
                tenant=tenant,
                include_archived=include_archived,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if q:
            needle = q.casefold()
            tasks = [
                task
                for task in tasks
                if needle in task.title.casefold()
                or needle in (task.body or "").casefold()
                or needle in task.id.casefold()
            ]

        links = [
            {"parent_id": row["parent_id"], "child_id": row["child_id"]}
            for row in conn.execute("SELECT parent_id, child_id FROM task_links ORDER BY parent_id, child_id").fetchall()
        ]
        link_counts: dict[str, dict[str, int]] = {}
        for link in links:
            link_counts.setdefault(link["parent_id"], {"parents": 0, "children": 0})["children"] += 1
            link_counts.setdefault(link["child_id"], {"parents": 0, "children": 0})["parents"] += 1
        comment_counts = {
            row["task_id"]: int(row["n"])
            for row in conn.execute("SELECT task_id, COUNT(*) AS n FROM task_comments GROUP BY task_id").fetchall()
        }
        progress: dict[str, dict[str, int]] = {}
        for row in conn.execute(
            "SELECT l.parent_id AS parent_id, t.status AS child_status FROM task_links l JOIN tasks t ON t.id = l.child_id"
        ).fetchall():
            item = progress.setdefault(row["parent_id"], {"done": 0, "total": 0})
            item["total"] += 1
            if row["child_status"] == "done":
                item["done"] += 1
        latest_event_id = conn.execute("SELECT COALESCE(MAX(id), 0) AS m FROM task_events").fetchone()["m"]
        columns = {column: [] for column in BOARD_COLUMNS}
        if include_archived:
            columns["archived"] = []
        rows = []
        for task in tasks:
            item = task_dict(task, include_body=False)
            item["link_counts"] = link_counts.get(task.id, {"parents": 0, "children": 0})
            item["comment_count"] = comment_counts.get(task.id, 0)
            item["progress"] = progress.get(task.id)
            rows.append(item)
            column = task.status if task.status in columns else "todo"
            columns.setdefault(column, []).append(item)
        tenants = [
            row["tenant"]
            for row in conn.execute("SELECT DISTINCT tenant FROM tasks WHERE tenant IS NOT NULL ORDER BY tenant").fetchall()
        ]
        return {
            "board": selected,
            "board_meta": _board_payload(selected),
            "columns": columns,
            "column_order": BOARD_COLUMNS + (["archived"] if include_archived else []),
            "tasks": rows,
            "links": links,
            "stats": kanban_db.board_stats(conn),
            "assignees": kanban_db.known_assignees(conn),
            "tenants": tenants,
            "latest_event_id": int(latest_event_id),
        }
    finally:
        conn.close()


@router.get("/board/table")
def board_table(board: Optional[str] = Query(None), include_archived: bool = Query(False)) -> dict[str, Any]:
    payload = board_view(board=board, include_archived=include_archived)
    return {"board": payload["board"], "rows": payload["tasks"], "stats": payload["stats"]}


@router.post("/tasks")
def create_task(payload: CreateTaskBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        if payload.status and payload.status not in INITIAL_TASK_STATUSES:
            raise HTTPException(status_code=400, detail="initial status can only be ready/todo/triage; use lifecycle endpoints for others")
        try:
            task_id = kanban_db.create_task(
                conn,
                title=payload.title,
                body=payload.body,
                assignee=payload.assignee,
                created_by=payload.created_by,
                workspace_kind=payload.workspace_kind,
                workspace_path=payload.workspace_path,
                tenant=payload.tenant,
                priority=payload.priority,
                parents=payload.parents,
                triage=payload.triage,
                idempotency_key=payload.idempotency_key,
                max_runtime_seconds=payload.max_runtime_seconds,
                skills=payload.skills,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if payload.status:
            _set_status_direct(conn, task_id, payload.status)
        _apply_create_workflow_fields(
            conn,
            task_id,
            workflow_template_id=payload.workflow_template_id,
            current_step_key=payload.current_step_key,
        )
        return _task_detail(conn, task_id, board=selected)
    finally:
        conn.close()


@router.post("/tasks/bulk-create")
def bulk_create(payload: BulkCreateBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    items: list[CreateTaskBody] = list(payload.tasks)
    if payload.lines:
        defaults = dict(payload.defaults)
        for line in payload.lines.splitlines():
            title = line.strip()
            if not title:
                continue
            items.append(CreateTaskBody(title=title, **defaults))
    results = []
    for item in items:
        conn = kanban_db.connect(board=selected)
        try:
            if item.status and item.status not in INITIAL_TASK_STATUSES:
                raise ValueError("initial status can only be ready/todo/triage; use lifecycle endpoints for others")
            task_id = kanban_db.create_task(
                conn,
                title=item.title,
                body=item.body,
                assignee=item.assignee,
                created_by=item.created_by,
                workspace_kind=item.workspace_kind,
                workspace_path=item.workspace_path,
                tenant=item.tenant,
                priority=item.priority,
                parents=item.parents,
                triage=item.triage,
                idempotency_key=item.idempotency_key,
                max_runtime_seconds=item.max_runtime_seconds,
                skills=item.skills,
            )
            if item.status:
                _set_status_direct(conn, task_id, item.status)
            results.append({"ok": True, "task_id": task_id, "title": item.title})
        except Exception as exc:
            results.append({"ok": False, "title": item.title, "error": str(exc)})
        finally:
            conn.close()
    return {"board": selected, "results": results, "created": sum(1 for r in results if r["ok"])}


@router.get("/tasks/{task_id}")
def get_task(task_id: str, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        return _task_detail(conn, task_id, board=selected)
    finally:
        conn.close()


@router.get("/tasks/{task_id}/raw")
def get_task_raw(task_id: str, board: Optional[str] = Query(None)) -> dict[str, Any]:
    return get_task(task_id, board=board)


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, payload: UpdateTaskBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        task = _apply_task_update(conn, task_id, payload)
        return {"task": task, "board": selected}
    finally:
        conn.close()


@router.post("/tasks/{task_id}/assign")
def assign_task(task_id: str, payload: AssignBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    profile = payload.assignee if payload.assignee is not None else payload.profile
    profile = _normalize_assignee(profile)
    conn = kanban_db.connect(board=selected)
    try:
        try:
            ok = kanban_db.assign_task(conn, task_id, profile)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if not ok:
            raise HTTPException(status_code=404, detail=f"task {task_id} not found")
        return {"task": task_dict(kanban_db.get_task(conn, task_id)), "board": selected}
    finally:
        conn.close()


@router.post("/tasks/{task_id}/claim")
def claim_task(
    task_id: str,
    payload: Optional[ClaimBody] = None,
    board: Optional[str] = Query(None),
    ttl: int = Query(900),
) -> dict[str, Any]:
    selected = _resolve_board(board)
    body = payload or ClaimBody()
    conn = kanban_db.connect(board=selected)
    try:
        task = kanban_db.claim_task(
            conn,
            task_id,
            ttl_seconds=body.ttl_seconds or ttl,
            claimer=body.claimer,
        )
        if task is None:
            raise HTTPException(status_code=409, detail="task is not ready or already claimed")
        return {"task": task_dict(task), "run": run_dict(kanban_db.active_run(conn, task_id)) if kanban_db.active_run(conn, task_id) else None}
    finally:
        conn.close()


@router.post("/tasks/{task_id}/heartbeat")
def heartbeat_task(task_id: str, payload: HeartbeatBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        ok = kanban_db.heartbeat_worker(conn, task_id, note=payload.note)
        claim_extended = None
        if payload.extend_claim:
            claim_extended = kanban_db.heartbeat_claim(
                conn,
                task_id,
                ttl_seconds=payload.ttl_seconds or kanban_db.DEFAULT_CLAIM_TTL_SECONDS,
                claimer=payload.claimer,
            )
        if not ok:
            raise HTTPException(status_code=409, detail="task is not running")
        return {"ok": True, "claim_extended": claim_extended, "task": task_dict(kanban_db.get_task(conn, task_id))}
    finally:
        conn.close()


@router.post("/tasks/{task_id}/comments")
def add_comment(task_id: str, payload: CommentBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="comment body is required")
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        if kanban_db.get_task(conn, task_id) is None:
            raise HTTPException(status_code=404, detail=f"task {task_id} not found")
        comment_id = kanban_db.add_comment(conn, task_id, author=payload.author or "kanban-webui", body=payload.body)
        return {"ok": True, "comment_id": comment_id, "comments": [comment_dict(c) for c in kanban_db.list_comments(conn, task_id)]}
    finally:
        conn.close()


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: str, payload: CompleteBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        results = []
        for item_id in _all_ids(task_id, payload.ids):
            ok = kanban_db.complete_task(conn, item_id, result=payload.result, summary=payload.summary, metadata=payload.metadata)
            results.append({"task_id": item_id, "ok": ok})
        return {"results": results}
    finally:
        conn.close()


@router.post("/tasks/{task_id}/block")
def block_task(task_id: str, payload: BlockBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        results = []
        for item_id in _all_ids(task_id, payload.ids):
            ok = kanban_db.block_task(conn, item_id, reason=payload.reason)
            results.append({"task_id": item_id, "ok": ok})
        return {"results": results}
    finally:
        conn.close()


@router.post("/tasks/{task_id}/unblock")
def unblock_task(task_id: str, payload: Optional[BlockBody] = None, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    ids = payload.ids if payload else []
    conn = kanban_db.connect(board=selected)
    try:
        results = []
        for item_id in _all_ids(task_id, ids):
            ok = kanban_db.unblock_task(conn, item_id)
            results.append({"task_id": item_id, "ok": ok})
        return {"results": results}
    finally:
        conn.close()


@router.post("/tasks/{task_id}/archive")
def archive_task(task_id: str, payload: Optional[BlockBody] = None, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    ids = payload.ids if payload else []
    conn = kanban_db.connect(board=selected)
    try:
        results = []
        for item_id in _all_ids(task_id, ids):
            ok = kanban_db.archive_task(conn, item_id)
            results.append({"task_id": item_id, "ok": ok})
        return {"results": results}
    finally:
        conn.close()


@router.post("/tasks/bulk")
def bulk_update(payload: BulkTaskBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        results = []
        for task_id in payload.ids:
            try:
                task_payload = UpdateTaskBody(
                    status=payload.status,
                    assignee=payload.assignee,
                    priority=payload.priority,
                    result=payload.result,
                    summary=payload.summary,
                    metadata=payload.metadata,
                    block_reason=payload.reason,
                )
                task = _apply_task_update(conn, task_id, task_payload)
                results.append({"task_id": task_id, "ok": True, "task": task})
            except Exception as exc:
                results.append({"task_id": task_id, "ok": False, "error": str(exc)})
        return {"results": results}
    finally:
        conn.close()


@router.post("/links")
def link_tasks(payload: LinkBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        try:
            kanban_db.link_tasks(conn, payload.parent_id, payload.child_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True, "links": links_for(conn, payload.child_id)}
    finally:
        conn.close()


@router.delete("/links")
def unlink_tasks(parent_id: str = Query(...), child_id: str = Query(...), board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        ok = kanban_db.unlink_tasks(conn, parent_id, child_id)
        return {"ok": ok, "links": links_for(conn, child_id)}
    finally:
        conn.close()


@router.get("/tasks/{task_id}/runs")
def task_runs(task_id: str, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        if kanban_db.get_task(conn, task_id) is None:
            raise HTTPException(status_code=404, detail=f"task {task_id} not found")
        return {"runs": [run_dict(r) for r in kanban_db.list_runs(conn, task_id)], "active_run": run_dict(kanban_db.active_run(conn, task_id)) if kanban_db.active_run(conn, task_id) else None}
    finally:
        conn.close()


@router.get("/tasks/{task_id}/events")
def task_events(task_id: str, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        if kanban_db.get_task(conn, task_id) is None:
            raise HTTPException(status_code=404, detail=f"task {task_id} not found")
        return {"events": [event_dict(e) for e in kanban_db.list_events(conn, task_id)]}
    finally:
        conn.close()


@router.get("/tasks/{task_id}/log")
def task_log(task_id: str, board: Optional[str] = Query(None), tail: int = Query(65536, ge=1, le=2_000_000)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        if kanban_db.get_task(conn, task_id) is None:
            raise HTTPException(status_code=404, detail=f"task {task_id} not found")
    finally:
        conn.close()
    path = kanban_db.worker_log_path(task_id, board=selected)
    content = kanban_db.read_worker_log(task_id, tail_bytes=tail, board=selected)
    size = path.stat().st_size if path.exists() else 0
    return {
        "task_id": task_id,
        "path": str(path),
        "exists": content is not None,
        "size_bytes": size,
        "tail_bytes": tail,
        "truncated": size > tail,
        "content": content or "",
    }


@router.get("/tasks/{task_id}/context")
def task_context(task_id: str, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        if kanban_db.get_task(conn, task_id) is None:
            raise HTTPException(status_code=404, detail=f"task {task_id} not found")
        return {"task_id": task_id, "context": kanban_db.build_worker_context(conn, task_id)}
    finally:
        conn.close()


@router.get("/tasks/{task_id}/monitor")
def task_monitor(task_id: str, board: Optional[str] = Query(None), tail: int = Query(65536, ge=1, le=2_000_000)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        task = kanban_db.get_task(conn, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"task {task_id} not found")
        active = kanban_db.active_run(conn, task_id)
        runs = kanban_db.list_runs(conn, task_id)
        events = kanban_db.list_events(conn, task_id)[-50:]
        now = int(time.time())
        heartbeat_at = task.last_heartbeat_at or (active.last_heartbeat_at if active else None)
        heartbeat_age = now - int(heartbeat_at) if heartbeat_at else None
        log = task_log(task_id, board=selected, tail=tail)
        context = kanban_db.build_worker_context(conn, task_id)
        return {
            "board": selected,
            "now": now,
            "task": task_dict(task),
            "current_run": run_dict(active) if active else None,
            "runs": [run_dict(r) for r in runs],
            "heartbeat": {
                "last_heartbeat_at": heartbeat_at,
                "age_seconds": heartbeat_age,
                "overdue": bool(heartbeat_age is not None and heartbeat_age > 300),
            },
            "claim": {
                "lock": task.claim_lock,
                "expires": task.claim_expires,
                "expires_in_seconds": (int(task.claim_expires) - now) if task.claim_expires else None,
            },
            "worker": {
                "pid": task.worker_pid or (active.worker_pid if active else None),
                "max_runtime_seconds": task.max_runtime_seconds or (active.max_runtime_seconds if active else None),
                "elapsed_seconds": (now - int(active.started_at)) if active else None,
            },
            "workspace": {"kind": task.workspace_kind, "path": task.workspace_path},
            "workflow": {"template_id": task.workflow_template_id, "step_key": task.current_step_key, "skills": task.skills},
            "events": [event_dict(e) for e in events],
            "log": log,
            "context_preview": context[:4000],
            "context_truncated": len(context) > 4000,
        }
    finally:
        conn.close()


@router.get("/stats")
def stats(board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        return kanban_db.board_stats(conn)
    finally:
        conn.close()


@router.get("/assignees")
def assignees(board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        return {"assignees": kanban_db.known_assignees(conn)}
    finally:
        conn.close()


@router.get("/events")
def events(board: Optional[str] = Query(None), since: int = Query(0), limit: int = Query(100, ge=1, le=1000)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        rows = conn.execute(
            "SELECT * FROM task_events WHERE id > ? ORDER BY id ASC LIMIT ?",
            (since, limit),
        ).fetchall()
        payload = []
        for row in rows:
            try:
                event_payload = json.loads(row["payload"]) if row["payload"] else None
            except Exception:
                event_payload = None
            payload.append(
                {
                    "id": row["id"],
                    "task_id": row["task_id"],
                    "kind": row["kind"],
                    "payload": event_payload,
                    "created_at": row["created_at"],
                    "run_id": row["run_id"] if "run_id" in row.keys() else None,
                }
            )
        latest = conn.execute("SELECT COALESCE(MAX(id), 0) AS m FROM task_events").fetchone()["m"]
        return {"board": selected, "events": payload, "latest_event_id": int(latest)}
    finally:
        conn.close()


@router.get("/events/stream")
async def events_stream(board: Optional[str] = Query(None), since: int = Query(0), interval: float = Query(0.75, ge=0.2, le=10.0)):
    selected = _resolve_board(board)

    async def gen():
        cursor = since
        while True:
            payload = events(board=selected, since=cursor, limit=100)
            if payload["events"]:
                cursor = payload["events"][-1]["id"]
                yield f"event: kanban\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(interval)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/watch")
def watch(board: Optional[str] = Query(None), since: int = Query(0), limit: int = Query(100, ge=1, le=1000)) -> dict[str, Any]:
    return events(board=board, since=since, limit=limit)


@router.post("/dispatch")
def dispatch(board: Optional[str] = Query(None), dry_run: bool = Query(True), max: int = Query(8), confirm: Optional[str] = Query(None)) -> dict[str, Any]:  # noqa: A002 - query name matches CLI wording
    selected = _resolve_board(board)
    if not dry_run and confirm != "dispatch":
        raise HTTPException(status_code=400, detail="non-dry-run dispatch requires confirm=dispatch")
    conn = kanban_db.connect(board=selected)
    try:
        result = kanban_db.dispatch_once(conn, dry_run=dry_run, max_spawn=max, board=selected)
        try:
            from dataclasses import asdict

            return asdict(result)
        except Exception:
            return {"result": str(result)}
    finally:
        conn.close()


@router.get("/home-channels")
def home_channels(task_id: Optional[str] = Query(None), board: Optional[str] = Query(None)) -> dict[str, Any]:
    homes = _configured_home_channels()
    subscribed: set[tuple[str, str, str]] = set()
    if task_id:
        selected = _resolve_board(board)
        conn = kanban_db.connect(board=selected)
        try:
            subscribed = {_home_subscription_key(sub) for sub in kanban_db.list_notify_subs(conn, task_id)}
        finally:
            conn.close()
    return {"home_channels": [{**home, "subscribed": _home_subscription_key(home) in subscribed} for home in homes]}


@router.post("/tasks/{task_id}/home-subscribe/{platform}")
def subscribe_home_channel(task_id: str, platform: str, board: Optional[str] = Query(None)) -> dict[str, Any]:
    home = _home_for_platform(platform.strip().lower())
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        if kanban_db.get_task(conn, task_id) is None:
            raise HTTPException(status_code=404, detail=f"task {task_id} not found")
        kanban_db.add_notify_sub(
            conn,
            task_id=task_id,
            platform=home["platform"],
            chat_id=home["chat_id"],
            thread_id=home["thread_id"] or None,
        )
        return {"ok": True, "task_id": task_id, "home_channel": home}
    finally:
        conn.close()


@router.delete("/tasks/{task_id}/home-subscribe/{platform}")
def unsubscribe_home_channel(task_id: str, platform: str, board: Optional[str] = Query(None)) -> dict[str, Any]:
    home = _home_for_platform(platform.strip().lower())
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        ok = kanban_db.remove_notify_sub(
            conn,
            task_id=task_id,
            platform=home["platform"],
            chat_id=home["chat_id"],
            thread_id=home["thread_id"] or None,
        )
        return {"ok": ok, "task_id": task_id, "home_channel": home}
    finally:
        conn.close()


@router.post("/notify")
def notify_add(payload: NotifyBody, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        if kanban_db.get_task(conn, payload.task_id) is None:
            raise HTTPException(status_code=404, detail=f"task {payload.task_id} not found")
        kanban_db.add_notify_sub(
            conn,
            task_id=payload.task_id,
            platform=payload.platform,
            chat_id=payload.chat_id,
            thread_id=payload.thread_id,
            user_id=payload.user_id,
        )
        return {"ok": True, "subscriptions": kanban_db.list_notify_subs(conn, payload.task_id)}
    finally:
        conn.close()


@router.get("/notify")
def notify_list(board: Optional[str] = Query(None), task_id: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        return {"subscriptions": kanban_db.list_notify_subs(conn, task_id)}
    finally:
        conn.close()


@router.delete("/notify")
def notify_remove(task_id: str, platform: str, chat_id: str, thread_id: Optional[str] = None, board: Optional[str] = Query(None)) -> dict[str, Any]:
    selected = _resolve_board(board)
    conn = kanban_db.connect(board=selected)
    try:
        ok = kanban_db.remove_notify_sub(conn, task_id=task_id, platform=platform, chat_id=chat_id, thread_id=thread_id)
        return {"ok": ok}
    finally:
        conn.close()


@router.post("/gc")
def gc(
    board: Optional[str] = Query(None),
    event_retention_days: int = Query(30, ge=1),
    log_retention_days: int = Query(30, ge=1),
    confirm: Optional[str] = Query(None),
) -> dict[str, Any]:
    selected = _resolve_board(board)
    if confirm != "gc":
        raise HTTPException(status_code=400, detail="gc requires confirm=gc")
    conn = kanban_db.connect(board=selected)
    try:
        events_deleted = kanban_db.gc_events(conn, older_than_seconds=event_retention_days * 24 * 3600)
    finally:
        conn.close()
    logs_deleted = kanban_db.gc_worker_logs(board=selected, older_than_seconds=log_retention_days * 24 * 3600)
    return {"events_deleted": events_deleted, "logs_deleted": logs_deleted}


@router.get("/daemon")
def daemon_deprecated() -> dict[str, Any]:
    return {
        "deprecated": True,
        "message": "The old kanban daemon command is deprecated. Run the Hermes gateway dispatcher instead; KanbanWebUI is only the human control surface.",
    }
