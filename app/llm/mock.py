"""Mock LLM provider.

The ``MockLLM`` inspects ``AgentState`` evidence to produce decisions
that demonstrably depend on prior observations.  This is the backbone
of Phase 1 — the entire Brain runs without an API key.

Each *scenario* is a small state machine:  the mock examines what
observations already exist and decides the next action accordingly.
"""

from __future__ import annotations

from typing import Any

from app.agent.decision import ActionType, Decision
from app.llm.base import LLMProvider


class MockLLM(LLMProvider):
    """Deterministic mock that adapts decisions to observed evidence.

    The mock never follows a fixed list.  Instead it inspects the context
    (observations, executed capabilities, failures) and picks the logical
    next step.  Tests can verify that later decisions depend on earlier
    observations.
    """

    async def decide(self, context: dict[str, Any]) -> Decision:
        observations = context.get("observations", [])
        executed = context.get("executed_capabilities", [])
        failed = context.get("failed_capabilities", [])
        step = context.get("step_count", 0)
        replans = context.get("replans", 0)

        # ----------------------------------------------------------
        # 1.  No observations yet → always validate first
        # ----------------------------------------------------------
        if not observations:
            return Decision(
                action=ActionType.CALL_CAPABILITY,
                capability="validate_remote_sensing_input",
                arguments=self._first_asset_arg(context),
                reason="No evidence yet — validate the input first.",
            )

        last_obs = observations[-1]
        last_status = last_obs.get("status", "success")
        last_cap = last_obs.get("capability", "")
        last_result = last_obs.get("result", {})

        # ----------------------------------------------------------
        # 2.  Last capability failed → retry or replan
        # ----------------------------------------------------------
        if last_status in ("failure", "timeout", "invalid_input"):
            retry_count = sum(
                1 for f in failed if f.get("capability") == last_cap
            )
            if retry_count < 2:
                return Decision(
                    action=ActionType.RETRY,
                    capability=last_cap,
                    arguments=self._first_asset_arg(context),
                    reason=f"Retrying {last_cap} after failure.",
                )
            return Decision(
                action=ActionType.REPLAN,
                reason=f"{last_cap} failed repeatedly — replanning.",
            )

        # ----------------------------------------------------------
        # 3.  Validation done — decide next based on modality
        # ----------------------------------------------------------
        if last_cap == "validate_remote_sensing_input":
            modality = last_result.get("modality", "optical")
            if modality == "sar":
                return Decision(
                    action=ActionType.CALL_CAPABILITY,
                    capability="analyze_sar_image",
                    arguments=self._first_asset_arg(context),
                    reason="Validation shows SAR modality — using SAR analysis.",
                )
            return Decision(
                action=ActionType.CALL_CAPABILITY,
                capability="interpret_scene",
                arguments=self._first_asset_arg(context),
                reason="Validation passed — interpreting the scene.",
            )

        # ----------------------------------------------------------
        # 4.  Temporal pair validation done → change detection
        # ----------------------------------------------------------
        if last_cap == "validate_temporal_pair":
            return Decision(
                action=ActionType.CALL_CAPABILITY,
                capability="detect_bitemporal_change",
                arguments=self._temporal_pair_args(context),
                reason="Temporal pair valid — running change detection.",
            )

        # ----------------------------------------------------------
        # 5.  Change detection done → area calculation
        # ----------------------------------------------------------
        if last_cap == "detect_bitemporal_change":
            return Decision(
                action=ActionType.CALL_CAPABILITY,
                capability="calculate_changed_area",
                arguments={"change_mask": last_result.get("change_mask_artifact", "")},
                reason="Change detected — calculating changed area.",
            )

        # ----------------------------------------------------------
        # 6.  After replanning — try an alternative
        # ----------------------------------------------------------
        if replans > 0 and "interpret_scene" not in executed:
            return Decision(
                action=ActionType.CALL_CAPABILITY,
                capability="interpret_scene",
                arguments=self._first_asset_arg(context),
                reason="Replanning — attempting scene interpretation.",
            )

        # ----------------------------------------------------------
        # 7.  Default — enough evidence, finalise
        # ----------------------------------------------------------
        return Decision(
            action=ActionType.FINAL,
            final_answer=self._build_mock_answer(observations),
            final_confidence=0.85,
            reason="Sufficient evidence gathered.",
        )

    async def synthesize(self, context: dict[str, Any]) -> str:
        observations = context.get("observations", [])
        parts = ["Based on the analysis:"]
        for obs in observations:
            if obs.get("status") == "success":
                parts.append(
                    f"- {obs.get('capability', '?')}: {obs.get('result', {})}"
                )
        return " ".join(parts) if len(parts) > 1 else "Analysis complete."

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _first_asset_arg(context: dict[str, Any]) -> dict[str, Any]:
        assets = context.get("input_assets", [])
        if assets:
            return {"asset": assets[0].get("asset_id", "asset_001")}
        return {"asset": "asset_001"}

    @staticmethod
    def _temporal_pair_args(context: dict[str, Any]) -> dict[str, Any]:
        assets = context.get("input_assets", [])
        if len(assets) >= 2:
            return {
                "before_asset": assets[0].get("asset_id", "asset_001"),
                "after_asset": assets[1].get("asset_id", "asset_002"),
            }
        return {"before_asset": "asset_001", "after_asset": "asset_002"}

    @staticmethod
    def _build_mock_answer(observations: list[dict[str, Any]]) -> str:
        results = []
        for obs in observations:
            if obs.get("status") == "success":
                cap = obs.get("capability", "unknown")
                result = obs.get("result", {})
                results.append(f"{cap}: {result}")
        if results:
            return "Analysis complete. " + "; ".join(results)
        return "Analysis complete with no actionable findings."
