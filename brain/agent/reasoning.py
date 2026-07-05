"""
Reasoning agent (master spec §5.4).

Claude, given full context on every call: relevant memory + the deal + the
engine's output. Produces recommendations and drafts.

HARD RULE (§3.1): this agent NARRATES the numbers the engine produced. It never
computes them. Pass engine output in; do not ask the model to do arithmetic.
HARD RULE (§3.3): drafts go to the Approval Queue, never straight out.

STUB: build in Cowork.
"""


def reason(user_message: str, context: dict) -> dict:
    """context carries memory hits + engine output. Returns narration + any draft."""
    raise NotImplementedError("Build in Cowork — see master-spec §5.4")
