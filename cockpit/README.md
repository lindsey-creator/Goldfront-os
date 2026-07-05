# Cockpit (front end)

The React interface (master spec §6). Build order is deliberate: the Brain
gets built and validated FIRST, then the Cockpit goes on top of a Brain that
already works. See master-spec §10, step 4.

Modules to build:
- AI Chat (full pipeline context; live ClickUp via MCP)
- Deal Command Center (red/yellow/green idle-day flagging; flywheel revenue by vertical)
- Approval Queue (approve / edit / deny — nothing sends without it)
- Daily Brief (pipeline by vertical + top-three money moves)
