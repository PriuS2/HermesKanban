from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class GitPair:
    origin: Path
    local: Path
    other: Path


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed in {cwd}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def configure_identity(repo: Path) -> None:
    git(repo, "config", "user.email", "kanban-test@example.com")
    git(repo, "config", "user.name", "Kanban Test")


def commit_file(repo: Path, rel: str, content: str, subject: str) -> str:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    git(repo, "add", rel)
    git(repo, "commit", "-m", subject)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


@pytest.fixture()
def git_pair(tmp_path: Path) -> GitPair:
    origin = tmp_path / "origin.git"
    local = tmp_path / "local"
    other = tmp_path / "other"

    git(tmp_path, "init", "--bare", str(origin))
    local.mkdir()
    git(local, "init")
    git(local, "checkout", "-b", "main")
    configure_identity(local)
    commit_file(local, "README.md", "initial\n", "initial commit")
    git(local, "remote", "add", "origin", str(origin))
    git(local, "push", "-u", "origin", "main")
    git(origin, "symbolic-ref", "HEAD", "refs/heads/main")

    git(tmp_path, "clone", str(origin), str(other))
    configure_identity(other)
    git(other, "checkout", "main")
    return GitPair(origin=origin, local=local, other=other)


def advance_remote(pair: GitPair, subject: str = "remote update") -> str:
    idx = len(list(pair.other.glob("remote-*.txt"))) + 1
    sha = commit_file(pair.other, f"remote-{idx}.txt", f"remote {idx}\n", subject)
    git(pair.other, "push", "origin", "main")
    return sha


def test_update_status_reports_no_update_when_head_matches_origin_main(git_pair: GitPair):
    from kanban_webui import app_update

    status = app_update.get_update_status(repo=git_pair.local, fetch=True)

    assert status["ok"] is True
    assert status["enabled"] is True
    assert status["current_branch"] == "main"
    assert status["update_available"] is False
    assert status["can_update"] is False
    assert status["dirty"] is False
    assert status["diverged"] is False
    assert status["blocked_reason"] is None


def test_update_status_reports_available_when_origin_main_is_ahead(git_pair: GitPair):
    from kanban_webui import app_update

    remote_sha = advance_remote(git_pair, "feat: remote update")
    status = app_update.get_update_status(repo=git_pair.local, fetch=True)

    assert status["update_available"] is True
    assert status["can_update"] is True
    assert status["remote_commit"] == remote_sha
    assert status["remote_short"] == remote_sha[:7]
    assert status["remote_ahead_count"] == 1
    assert status["local_ahead_count"] == 0
    assert status["commits"] == [{"sha": remote_sha, "short": remote_sha[:7], "subject": "feat: remote update"}]


def test_update_status_blocks_dirty_worktree(git_pair: GitPair):
    from kanban_webui import app_update

    advance_remote(git_pair)
    (git_pair.local / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    status = app_update.get_update_status(repo=git_pair.local, fetch=True)

    assert status["update_available"] is True
    assert status["dirty"] is True
    assert status["can_update"] is False
    assert "uncommitted" in status["blocked_reason"]


def test_update_status_blocks_non_main_branch(git_pair: GitPair):
    from kanban_webui import app_update

    advance_remote(git_pair)
    git(git_pair.local, "checkout", "-b", "feature/test")
    status = app_update.get_update_status(repo=git_pair.local, fetch=True)

    assert status["current_branch"] == "feature/test"
    assert status["update_available"] is True
    assert status["can_update"] is False
    assert "main" in status["blocked_reason"]


def test_update_status_blocks_diverged_history(git_pair: GitPair):
    from kanban_webui import app_update

    commit_file(git_pair.local, "local.txt", "local\n", "local only")
    advance_remote(git_pair)
    status = app_update.get_update_status(repo=git_pair.local, fetch=True)

    assert status["update_available"] is True
    assert status["remote_ahead_count"] == 1
    assert status["local_ahead_count"] == 1
    assert status["diverged"] is True
    assert status["can_update"] is False
    assert "diverged" in status["blocked_reason"]


def test_apply_update_fast_forwards_and_schedules_restart(git_pair: GitPair):
    from kanban_webui import app_update

    remote_sha = advance_remote(git_pair, "feat: update app")
    scheduled: list[bool] = []

    result = app_update.apply_update(
        repo=git_pair.local,
        restart_scheduler=lambda: scheduled.append(True),
        sync_runner=lambda repo: {"ran": False, "uv_missing": True},
    )

    assert result["ok"] is True
    assert result["updated"] is True
    assert result["previous_commit"] != remote_sha
    assert result["new_commit"] == remote_sha
    assert result["new_short"] == remote_sha[:7]
    assert result["restarting"] is True
    assert result["sync"]["uv_missing"] is True
    assert scheduled == [True]
    assert git(git_pair.local, "rev-parse", "HEAD").stdout.strip() == remote_sha


def test_apply_update_rejects_dirty_worktree(git_pair: GitPair):
    from kanban_webui import app_update

    advance_remote(git_pair)
    (git_pair.local / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(app_update.UpdateBlocked) as exc:
        app_update.apply_update(
            repo=git_pair.local,
            restart_scheduler=lambda: None,
            sync_runner=lambda repo: {"ran": False},
        )

    assert "uncommitted" in str(exc.value)


def test_update_status_endpoint_returns_update_payload(client, monkeypatch):
    from kanban_webui import kanban_api

    payload = {
        "ok": True,
        "enabled": True,
        "update_available": True,
        "can_update": True,
        "current_short": "940e789",
        "remote_short": "abc1234",
    }
    monkeypatch.setattr(kanban_api.app_update, "get_update_status", lambda: payload)

    response = client.get("/api/app/update-status")

    assert response.status_code == 200
    assert response.json() == payload


def test_update_endpoint_succeeds_and_reports_restarting(client, monkeypatch):
    from kanban_webui import kanban_api

    payload = {"ok": True, "updated": True, "new_short": "abc1234", "restarting": True}
    monkeypatch.setattr(kanban_api.app_update, "apply_update", lambda: payload)

    response = client.post("/api/app/update")

    assert response.status_code == 200
    assert response.json() == payload


def test_update_endpoint_returns_409_when_update_blocked(client, monkeypatch):
    from kanban_webui import kanban_api

    def blocked():
        raise kanban_api.app_update.UpdateBlocked("working tree has uncommitted changes")

    monkeypatch.setattr(kanban_api.app_update, "apply_update", blocked)

    response = client.post("/api/app/update")

    assert response.status_code == 409
    assert response.json()["detail"] == "working tree has uncommitted changes"


def test_update_endpoint_returns_503_when_update_unavailable(client, monkeypatch):
    from kanban_webui import kanban_api

    def unavailable():
        raise kanban_api.app_update.UpdateUnavailable("git fetch failed")

    monkeypatch.setattr(kanban_api.app_update, "apply_update", unavailable)

    response = client.post("/api/app/update")

    assert response.status_code == 503
    assert response.json()["detail"] == "git fetch failed"


def test_service_status_includes_local_git_info(client, monkeypatch):
    from kanban_webui import service_status

    monkeypatch.setattr(
        service_status.app_update,
        "local_git_info",
        lambda: {"available": True, "branch": "main", "short": "abc1234"},
    )

    response = client.get("/api/service/status")

    assert response.status_code == 200
    assert response.json()["git"] == {"available": True, "branch": "main", "short": "abc1234"}
