# Hermes KanbanWebUI

Standalone, Trello-like WebUI for Hermes Kanban.

- Uses the existing `hermes_cli.kanban_db` module and existing SQLite board DBs.
- Does not fork the Hermes dashboard plugin.
- Default URL: <http://127.0.0.1:8790>
- UI language: Korean by default, English toggle in the top bar.
- MVP scope: full `hermes kanban` CLI parity surfaces plus a readable board UI and Live Run Monitor.

## Run locally

```bash
cd /home/tjseh0091/workspace/HermesKanban
uv run python server.py --host 127.0.0.1 --port 8790
```

The repo includes dependencies in `pyproject.toml`; `uv run` creates/uses `.venv` automatically.
If Hermes is not importable, set:

```bash
export HERMES_AGENT_ROOT=/home/tjseh0091/.hermes/hermes-agent
```

## Start/stop scripts

Installed for this machine:

```bash
hermes-kanban-webui-start
hermes-kanban-webui-stop
```

State/log paths:

- state: `/home/tjseh0091/.hermes/kanban-webui/`
- log: `/home/tjseh0091/.hermes/logs/kanban-webui.log`
- pid: `/home/tjseh0091/.hermes/kanban-webui/kanban-webui.pid`

## Optional auth

Local-only use has no token by default. To require auth on `/api/*`:

```bash
export HERMES_KANBAN_WEBUI_TOKEN=$(openssl rand -hex 32)
```

Then send `X-Kanban-Token` or `Authorization: Bearer <token>`.

## Localhost/Tailscale security

- The app binds to `127.0.0.1` by default.
- Mutating methods reject cross-origin browser requests using `Origin`, `Referer`, and `Sec-Fetch-Site` checks.
- Unknown `Host` headers are rejected to reduce DNS-rebinding risk. Allowed hosts are loopback names/IPs, Tailscale `100.64.0.0/10` IPs, and comma-separated names in `HERMES_KANBAN_WEBUI_ALLOWED_HOSTS`.
- Tokens are accepted only through headers, not query strings.

## API highlights

- `GET /health`
- `POST /api/init`
- `GET/POST/PATCH/DELETE /api/boards...`
- `GET /api/board`
- `POST /api/tasks`
- `PATCH /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/claim`
- `POST /api/tasks/{task_id}/heartbeat`
- `POST /api/tasks/{task_id}/complete|block|unblock|archive`
- `GET /api/tasks/{task_id}/monitor`
- `GET /api/tasks/{task_id}/log|context|runs|events`
- `GET /api/events` and `GET /api/events/stream`
- `GET /api/stats`, `GET /api/assignees`
- `POST /api/dispatch` (`dry_run=true` by default; non-dry-run requires `confirm=dispatch`)
- `POST /api/gc` requires `confirm=gc`

## Tests

```bash
uv run --extra test python -m pytest -q
```

Current suite covers health/config, board CRUD/switch, task lifecycle, Live Run Monitor, auth, static shell, drag/drop contract, and CLI parity registry.

## Deferred

- Tailscale-only proxy and hardening are intentionally left for the next operations phase.
- Workflow Template Builder is intentionally out of MVP; implement after core board/API/CLI parity is stable.
