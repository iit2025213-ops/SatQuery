"""LLM provider abstraction.

The ``AgentController`` depends **only** on ``LLMProvider``.
Concrete implementations (Mock, OpenAI, …) are injected at runtime.
"""

from __future__ import annotations

import abc
from typing import Any

from app.agent.decision import Decision


class LLMProvider(abc.ABC):
    """Abstract base for all LLM backends."""

    @abc.abstractmethod
    async def decide(self, context: dict[str, Any]) -> Decision:
        """Given the current context, return the next ``Decision``."""

    @abc.abstractmethod
    async def synthesize(self, context: dict[str, Any]) -> str:
        """Produce a natural-language answer from the accumulated evidence."""
