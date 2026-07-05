"""
Persona + voice (master spec §5.3).

Encodes the decision framework (Dan Martell 4-part framework + flywheel logic)
and communication style so an answer sounds like Lindsey, not generic AI.

STUB: the persona system prompt gets assembled here from config + voice examples
pulled from the knowledge base. Build in Cowork.
"""

from brain.config import CORE_MARKETS, PREFERRED_DSCR_LENDER, FLYWHEEL_TOUCHES


def build_persona_prompt(voice_examples: list[str] | None = None) -> str:
    """Assemble the system prompt that makes the reasoning agent answer as Lindsey."""
    # TODO(cowork): layer voice examples + framework on top of these facts
    raise NotImplementedError("Build in Cowork — see master-spec §5.3")
