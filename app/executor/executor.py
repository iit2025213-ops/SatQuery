"""Capability executor.

The executor resolves a capability through the registry, validates
preconditions, runs the adapter, and normalises the output.  The
``AgentController`` only calls ``executor.run(…)`` — it never touches
adapters or the registry directly.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.state import AgentState
from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
)
from app.geospatial.validation import validate_preconditions
from app.registry.registry import CapabilityRegistry

logger = logging.getLogger(__name__)


class DefaultExecutor:
    """Standard executor for running capabilities.
    
    Routes inputs through registry resolution, precondition validation,
    adapter execution, and output normalization.
    """

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    async def run(
        self,
        capability: str,
        arguments: dict[str, Any],
        state: AgentState,
    ) -> Observation:
        # 1. Resolve capability
        try:
            definition, adapter = self.registry.resolve(capability)
        except KeyError:
            return _error_observation(capability, f"Unknown capability: {capability}")

        # 2. Precondition validation gate
        valid, reason = validate_preconditions(definition, arguments, state)
        if not valid:
            logger.warning("Precondition failed for %s: %s", capability, reason)
            return Observation(
                source=EvidenceSource(capability=capability, backend="executor"),
                type=EvidenceType.VALIDATION,
                status=ObservationStatus.INVALID_INPUT,
                result={"validation_error": reason},
                error_message=reason,
            )

        # 3. Adapter-level input validation
        ok, err = adapter.validate_input(arguments)
        if not ok:
            return _error_observation(capability, err)

        # 4. Execute
        try:
            # Inject capability name and state for normalizers/validators that need it
            arguments_with_meta = {**arguments, "_capability": capability, "_state": state}
            raw = await adapter.predict(arguments_with_meta)
        except Exception as exc:
            logger.exception("Adapter predict failed for %s", capability)
            return _error_observation(capability, str(exc))

        # 5. Normalise
        try:
            observation = adapter.normalize_output(raw, arguments_with_meta)
        except Exception as exc:
            logger.exception("Output normalisation failed for %s", capability)
            return _error_observation(capability, f"Normalisation error: {exc}")

        return observation


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _error_observation(capability: str, message: str) -> Observation:
    return Observation(
        source=EvidenceSource(capability=capability, backend="executor"),
        type=EvidenceType.ERROR,
        status=ObservationStatus.FAILURE,
        result={"error": message},
        error_message=message,
    )
