# Command Center — Runnable Actions

What you can **run** from the deck (not just view). All actions hit the Brain API (`goldfront-os`).

## Quick RUN strip (dashboard)

Below **Ask Echo** on the main dashboard:

| Button | API | What it does |
|--------|-----|----------------|
| **Sync ClickUp** | `POST /ingest/clickup` | Full workspace pull into Brain memory; flashes ingest counts |
| **Refresh all** | (client) | Refetches every cockpit lane (watch, pulse, brief, GHL, etc.) |
| **Open Stack** | `#connections` | Jump to connector setup |

Operating rule shown inline: **New ClickUp tasks → Lindsey for review** (per `OPERATING_BRAIN.md`).

## ClickUp — every task row

On **Watch**, **Team Pulse** (overdue + gaps), **Daily Brief** commitments, and Fieldy-flagged items when `clickup_task_id` is present:

| Control | API | What it does |
|---------|-----|----------------|
| **Done** | `POST /clickup/tasks/{id}/complete` | Marks task complete/closed in ClickUp |
| **Assign** | Opens Quick Assign sheet → `POST /clickup/tasks/{id}/assign` | Assigns workspace member (`GET /clickup/members` for roster) |
| **Open** | `POST /clickup/tasks/{id}/reopen` | Reopens task |

Status/name patch (programmatic): `PATCH /clickup/tasks/{id}` with `{ "status", "name" }`.

## Echo — voice + chat

**Ask Echo** (`POST /chat`) — before Claude reasoning, simple commands are parsed:

| Say / type | Action |
|------------|--------|
| "Sync ClickUp" / "refresh clickup" | Runs `POST /ingest/clickup`, returns confirmation with counts |
| "Mark task {id} done" / "complete task {id}" | Runs complete endpoint for that task id |

Other Echo modes:

| Mode | API | What it does |
|------|-----|----------------|
| **Route → ClickUp task** | `POST /tasks` | Queues task for approval → creates in ClickUp on approve |
| **Draft → Approval Queue** | `POST /chat` + `wants_draft` | Draft queued; approve/deny via approvals API |
| **Deal numbers** | `POST /chat` + `deal` | Engine-grounded narration |

Approvals: `GET /approvals/pending`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/deny`.

## GHL (read + deep link)

| Control | What it does |
|---------|----------------|
| **Open in GHL** (per lead row) | Opens `https://app.gohighlevel.com/v2/location/{locationId}/contacts/detail/{contactId}` — no API write |

CRM metrics are read-only from `GET /crm/ghl`.

## Feed the Brain (`#echo` page)

| Button | API | What it does |
|--------|-----|----------------|
| **Sync ClickUp now** | `POST /ingest/clickup` | Same ingest as dashboard RUN strip |
| **Save** (voice lines) | `POST /train/voice` | Train voice memory |
| **Train decision** | `POST /train/deal-decision` | Store deal + rules comparison |
| **Validate stored history** | `GET /validation/shadow` | Shadow-mode match rate |
| **Upload CSV** | `POST /validation/shadow` | Batch dry-run |

## Ingest (background + manual)

| Endpoint | What it does |
|----------|----------------|
| `POST /ingest/clickup` | Force full ClickUp sync |
| `GET /ingest/clickup/status` | Last sync time + counts |
| `POST /ingest/fieldy` | Pull Fieldy conversations |

Auto-sync: ClickUp every 15 minutes when configured (Brain startup + interval).

## Connectors

`GET /connectors/status` — which sources are live (never exposes secrets).

Setup: **Stack** nav → `#connections`.

---

**Deploy note:** Build Command Center (`npm run build` in `conrad-command-center`), then serve via Brain (`uvicorn brain.main:app`) so API + UI share one origin in production.
