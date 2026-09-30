"""Model access.

One place that knows how to build a chat model, so every node stays
provider-agnostic. Swap providers by changing ``BMAD_MODEL`` (see
``.env.example``) -- no code changes.
"""

from __future__ import annotations

from functools import lru_cache

from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from .config import settings


@lru_cache(maxsize=8)
def _cached(model: str, temperature: float):
    if model.startswith("claude-code"):
        from .claude_code_llm import ClaudeCodeChatModel

        _, _, alias = model.partition(":")
        return ClaudeCodeChatModel(model=alias, temperature=temperature)
    return init_chat_model(model, temperature=temperature)


def get_llm(temperature: float = 0.4):
    """Plain chat model for prose (documents, persona dialogue)."""
    return _cached(settings.model, temperature)


def get_structured_llm(schema: type[BaseModel], temperature: float = 0.1):
    """Chat model constrained to a pydantic schema -- used for every gate
    (route decisions, PASS/CONCERNS/FAIL, grades, triage verdicts) so the
    graph branches on a typed field instead of parsing prose."""
    return get_llm(temperature=temperature).with_structured_output(schema)
