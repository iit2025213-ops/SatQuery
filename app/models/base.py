"""Base model adapter.

Every specialist model (GeoChat, ChangeFormer, …) implements this
interface.  The executor calls adapters through this contract — it
never touches raw model internals.
"""

from __future__ import annotations

import abc
from typing import Any

from app.evidence.schema import Observation


class BaseModelAdapter(abc.ABC):
    """Common interface for all specialist model adapters."""

    @abc.abstractmethod
    def validate_input(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Check that *arguments* are valid for this adapter.

        Returns (is_valid, error_message).  An empty error_message
        indicates success.
        """

    @abc.abstractmethod
    async def predict(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Run inference and return raw results.

        In mock mode this returns plausible synthetic data.
        In production this calls the real model.
        """

    @abc.abstractmethod
    def normalize_output(
        self,
        raw: dict[str, Any],
        arguments: dict[str, Any],
    ) -> Observation:
        """Convert raw model output to a standardised ``Observation``."""
