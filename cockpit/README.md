# Cockpit (front end)

The **JARVIS Command Center** UI is maintained in
[`lindsey-creator/conrad-command-center`](https://github.com/lindsey-creator/conrad-command-center).
Goldfront OS (this repo) serves the built `dist/` on Manus and exposes cockpit read APIs.

See [`docs/jarvis-command-center.md`](../docs/jarvis-command-center.md) for wiring, `/health`,
and GHL location IDs.

Build order is deliberate: the Brain gets built and validated FIRST, then the
Command Center goes on top of a Brain that already works. See master-spec §10, step 4.

Modules (in the UI repo):
- JARVIS chat (full pipeline context; live ClickUp)
- Deal Command Center (red/yellow/green idle-day flagging; flywheel revenue by vertical)
- Approval Queue (approve / edit / deny — nothing sends without it)
- Daily Brief (pipeline by vertical + top-three money moves)
