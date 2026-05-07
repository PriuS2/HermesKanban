"""Safe self-update helpers for KanbanWebUI.

The WebUI only updates the current checkout from the fixed ``origin/main`` ref.
It intentionally refuses dirty, non-main, or diverged repositories instead of
trying to stash/reset/merge from the browser.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

from .config import ROOT_DIR, get_settings

REMOTE = "origin"
BRANCH = "main"
REMOTE_REF = f"{REMOTE}/{BRANCH}"
COMMAND_TIMEOUT_SECONDS = 20


class UpdateError(RuntimeError):
    """Base class for update failures surfaced through the API."""


class UpdateBlocked(UpdateError):
    """The repository state is valid, but automatic update is unsafe."""


class UpdateUnavailable(UpdateError):
    """Git or another update prerequisite is unavailable/failing."""


def _git_env() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
    }


def _run_git(repo: Path, *args: str, check: bool = True, timeout: int = COMMAND_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    if shutil.which("git") is None:
        raise UpdateUnavailable("git is not available")
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=_git_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        message = (result.stderr or result.stdout or f"git {' '.join(args)} failed").strip()
        raise UpdateUnavailable(message)
    return result


def _short(sha: Optional[str]) -> Optional[str]:
    return sha[:7] if sha else None


def _current_branch(repo: Path) -> str:
    branch = _run_git(repo, "branch", "--show-current").stdout.strip()
    if branch:
        return branch
    return "HEAD"


def _commit_subjects(repo: Path, *, max_commits: int = 8) -> list[dict[str, str]]:
    result = _run_git(
        repo,
        "log",
        f"--max-count={max_commits}",
        "--format=%H%x00%s",
        f"HEAD..{REMOTE_REF}",
    )
    commits: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        sha, _, subject = line.partition("\x00")
        commits.append({"sha": sha, "short": _short(sha) or "", "subject": subject})
    return commits


def local_git_info(repo: Path = ROOT_DIR) -> dict:
    """Return local Git metadata for service/status without fetching."""
    repo = Path(repo)
    try:
        inside = _run_git(repo, "rev-parse", "--is-inside-work-tree").stdout.strip()
        if inside != "true":
            return {"available": False, "reason": "not a git worktree"}
        commit = _run_git(repo, "rev-parse", "HEAD").stdout.strip()
        branch = _current_branch(repo)
        dirty = bool(_run_git(repo, "status", "--porcelain").stdout.strip())
    except (subprocess.TimeoutExpired, UpdateError) as exc:
        return {"available": False, "reason": str(exc)}
    return {"available": True, "branch": branch, "commit": commit, "short": _short(commit), "dirty": dirty}


def get_update_status(repo: Path = ROOT_DIR, *, fetch: bool = True, max_commits: int = 8) -> dict:
    """Check whether fixed ``origin/main`` can be fast-forwarded safely."""
    repo = Path(repo)
    try:
        inside = _run_git(repo, "rev-parse", "--is-inside-work-tree").stdout.strip()
        if inside != "true":
            raise UpdateUnavailable("not a git worktree")
        if fetch:
            _run_git(repo, "fetch", "--quiet", REMOTE, BRANCH, timeout=60)

        current_branch = _current_branch(repo)
        current_commit = _run_git(repo, "rev-parse", "HEAD").stdout.strip()
        remote_commit = _run_git(repo, "rev-parse", REMOTE_REF).stdout.strip()
        dirty = bool(_run_git(repo, "status", "--porcelain").stdout.strip())
        counts = _run_git(repo, "rev-list", "--left-right", "--count", f"HEAD...{REMOTE_REF}").stdout.strip().split()
        local_ahead_count = int(counts[0]) if len(counts) >= 1 else 0
        remote_ahead_count = int(counts[1]) if len(counts) >= 2 else 0
        ancestor = _run_git(repo, "merge-base", "--is-ancestor", "HEAD", REMOTE_REF, check=False)
        fast_forward = ancestor.returncode == 0
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "enabled": False, "reason": f"git command timed out: {exc}"}
    except UpdateError as exc:
        return {"ok": False, "enabled": False, "reason": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive host failure guard
        return {"ok": False, "enabled": False, "reason": str(exc)}

    update_available = remote_ahead_count > 0
    diverged = local_ahead_count > 0 and remote_ahead_count > 0
    blocked_reason = None
    if update_available:
        if current_branch != BRANCH:
            blocked_reason = "current branch is not main"
        elif dirty:
            blocked_reason = "working tree has uncommitted changes"
        elif diverged or not fast_forward:
            blocked_reason = "local and origin/main have diverged"

    can_update = update_available and blocked_reason is None and fast_forward
    commits = _commit_subjects(repo, max_commits=max_commits) if update_available else []
    return {
        "ok": True,
        "enabled": True,
        "remote": REMOTE,
        "branch": BRANCH,
        "remote_ref": REMOTE_REF,
        "current_branch": current_branch,
        "current_commit": current_commit,
        "current_short": _short(current_commit),
        "remote_commit": remote_commit,
        "remote_short": _short(remote_commit),
        "dirty": dirty,
        "local_ahead_count": local_ahead_count,
        "remote_ahead_count": remote_ahead_count,
        "update_available": update_available,
        "fast_forward": fast_forward,
        "diverged": diverged,
        "can_update": can_update,
        "blocked_reason": blocked_reason,
        "commits": commits,
    }


def _run_uv_sync(repo: Path) -> dict:
    uv = shutil.which("uv")
    if uv is None:
        return {"ran": False, "uv_missing": True}
    result = subprocess.run(
        [uv, "sync"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "uv sync failed").strip()
        raise UpdateUnavailable(output)
    return {"ran": True, "uv_missing": False, "stdout": result.stdout.strip()[-1000:], "stderr": result.stderr.strip()[-1000:]}


def _restart_process() -> None:
    settings = get_settings()
    server = ROOT_DIR / "server.py"
    args = [sys.executable, str(server), "--host", settings.host, "--port", str(settings.port)]
    os.execv(sys.executable, args)


def schedule_self_restart(delay_seconds: float = 0.7) -> None:
    timer = threading.Timer(delay_seconds, _restart_process)
    timer.daemon = True
    timer.start()


def apply_update(
    repo: Path = ROOT_DIR,
    *,
    restart_scheduler: Callable[[], None] = schedule_self_restart,
    sync_runner: Callable[[Path], dict] = _run_uv_sync,
) -> dict:
    """Fast-forward from origin/main, run dependency sync, then schedule restart."""
    repo = Path(repo)
    status = get_update_status(repo=repo, fetch=True)
    if not status.get("ok"):
        raise UpdateUnavailable(status.get("reason") or "update status is unavailable")
    if not status.get("update_available"):
        raise UpdateBlocked("no update available")
    if not status.get("can_update"):
        raise UpdateBlocked(status.get("blocked_reason") or "update is blocked")

    previous_commit = status["current_commit"]
    _run_git(repo, "pull", "--ff-only", REMOTE, BRANCH, timeout=60)
    new_commit = _run_git(repo, "rev-parse", "HEAD").stdout.strip()
    sync_result = sync_runner(repo)
    restart_scheduler()
    return {
        "ok": True,
        "updated": True,
        "previous_commit": previous_commit,
        "previous_short": _short(previous_commit),
        "new_commit": new_commit,
        "new_short": _short(new_commit),
        "sync": sync_result,
        "restarting": True,
    }
