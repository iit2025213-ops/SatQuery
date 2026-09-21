"""Context builder.

Constructs a *bounded* prompt payload for the LLM from the current
``AgentState``.  Large binary data is never included — only IDs, URIs,
and compact summaries.
"""

from __future__ import annotations

from typing import Any

from app.agent.state import AgentState
from app.evidence.schema import Observation


# Maximum number of recent observations to include verbatim.
_MAX_RECENT_OBS = 10


class ContextBuilder:
    """Builds a structured context dict from ``AgentState``."""

    def build(
        self,
        state: AgentState,
        *,
        available_capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return a JSON-serialisable context dict for the LLM."""
        from app.registry.capabilities import BUILTIN_CAPABILITIES
        
        cap_details = []
        for c in (available_capabilities or []):
            if c in BUILTIN_CAPABILITIES:
                defi = BUILTIN_CAPABILITIES[c]
                reqs = []
                if defi.required_asset_count == 1:
                    reqs.append("(Requires argument: 'asset')")
                elif defi.required_asset_count == 2:
                    if defi.requires_temporal_pair:
                        reqs.append("(Requires arguments: 'before_asset', 'after_asset')")
                    else:
                        reqs.append("(Requires arguments: 'before_asset', 'after_asset')")
                desc = f"{defi.name} - {defi.description} {' '.join(reqs)}"
                cap_details.append(desc)
            else:
                cap_details.append(c)

        recent_obs = state.observations[-_MAX_RECENT_OBS:]
        return {
            "user_request": state.request,
            "current_goal": state.current_goal or state.request,
            "input_assets": [
                {
                    "asset_id": a.asset_id,
                    "uri": a.uri,
                    "modality": a.modality,
                    "format": a.format,
                    "metadata": a.metadata,
                }
                for a in state.input_assets
            ],
            "observations": [
                self._summarise_observation(o) for o in recent_obs
            ],
            "artifact_ids": state.artifact_ids,
            "executed_capabilities": [
                t.capability for t in state.executed_tasks
            ],
            "failed_capabilities": [
                {"capability": t.capability, "error": t.error}
                for t in state.failed_tasks
            ],
            "step_count": state.step_count,
            "replans": state.replans,
            "verification_status": state.verification_status,
            "confidence": state.confidence,
            "available_capabilities": cap_details,
        }

    @staticmethod
    def _summarise_observation(obs: Observation) -> dict[str, Any]:
        """Compact representation of an observation for LLM context."""
        return {
            "evidence_id": obs.evidence_id,
            "capability": obs.source.capability,
            "type": obs.type.value,
            "status": obs.status.value,
            "result": obs.result,
            "confidence": obs.confidence,
            "artifacts": obs.artifacts,
            "error": obs.error_message if obs.error_message else None,
        }
