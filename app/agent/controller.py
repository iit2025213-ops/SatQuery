"""Agent controller — the continuous closed-loop engine.

This is the heart of SatQuery.  After every meaningful observation the
LLM is called *again* to decide what to do next.  The controller never
executes a static pre-computed plan.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.agent.context import ContextBuilder
from app.agent.decision import (
    ActionType,
    Decision,
    DecisionValidationError,
    validate_decision,
)
from app.agent.state import AgentState, AssetReference, TaskRecord
from app.agent.trace import TraceRecorder
from app.config import Settings
from app.critic.critic import Critic
from app.evidence.confidence import ConfidenceEngine
from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
)
from app.executor.executor import DefaultExecutor
from app.executor.parallel import ParallelExecutor
from app.llm.base import LLMProvider
from app.registry.registry import CapabilityRegistry

logger = logging.getLogger(__name__)


class AgentController:
    """Continuous closed-loop agent.

    Parameters
    ----------
    llm:
        The LLM provider (mock or real).
    executor:
        The capability executor (mock / local / lightning).
    registry:
        The capability registry.
    settings:
        Application settings.
    """

    def __init__(
        self,
        llm: LLMProvider,
        executor: DefaultExecutor,
        registry: CapabilityRegistry,
        settings: Settings | None = None,
    ) -> None:
        self.llm = llm
        self.executor = executor
        self.registry = registry
        self.settings = settings or Settings()
        self.context_builder = ContextBuilder()
        self.trace = TraceRecorder()
        self.critic = Critic()
        self.confidence_engine = ConfidenceEngine()
        self._parallel = ParallelExecutor(executor)

    # ==================================================================
    # PUBLIC ENTRY POINT
    # ==================================================================

    async def run(
        self,
        request: str,
        *,
        input_assets: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute the full agent loop and return a structured result."""
        state = self._init_state(request, input_assets, metadata)

        while state.step_count < self.settings.max_steps:
            state.step_count += 1

            # 1. Build context
            context = self.context_builder.build(
                state,
                available_capabilities=self.registry.list_capabilities(),
            )

            # 2. Ask the LLM
            try:
                decision = await self.llm.decide(context)
            except Exception as exc:
                logger.exception("LLM decide failed at step %d", state.step_count)
                self.trace.record(
                    action="LLM_ERROR",
                    status="failure",
                    rationale=str(exc),
                )
                break

            # 3. Validate decision
            try:
                known_caps = set(self.registry.list_capabilities())
                asset_ids = {a.asset_id for a in state.input_assets}
                validate_decision(decision, known_caps, asset_ids)
            except DecisionValidationError as exc:
                logger.warning("Invalid decision at step %d: %s", state.step_count, exc)
                obs = Observation(
                    source=EvidenceSource(capability="decision_validation", backend="controller"),
                    type=EvidenceType.ERROR,
                    status=ObservationStatus.FAILURE,
                    result={"invalid_decision": decision.model_dump(mode="json")},
                    error_message=str(exc),
                )
                state.add_observation(obs)
                self.trace.record(
                    action="INVALID_DECISION",
                    status="rejected",
                    rationale=str(exc),
                )
                continue  # let the LLM try again

            # 4. Record decision in history
            state.current_decision = decision.model_dump(mode="json")
            state.decision_history.append(state.current_decision)

            # 4.5 Process Specialist Evaluations (Closed-Loop Vision)
            if decision.specialist_evaluations:
                for ev_id, score in decision.specialist_evaluations.items():
                    for obs in state.observations:
                        if obs.evidence_id == ev_id:
                            # Attach LLM confidence score to the observation
                            if isinstance(obs.result, dict):
                                obs.result["llm_evaluation_score"] = score
                    # Log the evaluation to the trace
                    self.trace.record(
                        action="EVALUATE_SPECIALIST",
                        capability=ev_id,
                        confidence=score,
                        status="evaluated",
                        rationale=f"LLM assigned score {score:.2f} to evidence {ev_id}",
                    )

            # 5. Dispatch based on action
            if decision.action == ActionType.FINAL:
                self._handle_final(decision, state)
                break

            if decision.action == ActionType.CALL_CAPABILITY:
                await self._handle_call(decision, state)

            elif decision.action == ActionType.PARALLEL:
                await self._handle_parallel(decision, state)

            elif decision.action == ActionType.RETRY:
                await self._handle_retry(decision, state)

            elif decision.action == ActionType.REPLAN:
                self._handle_replan(decision, state)

            elif decision.action == ActionType.REQUEST_INPUT:
                self._handle_request_input(decision, state)
                break  # pause for user

            elif decision.action == ActionType.CONVERSATIONAL:
                # Pure conversational response — no models invoked
                self._handle_conversational(decision, state)
                break

        # Guard: max steps exceeded
        if state.final_result is None:
            state.final_result = {
                "answer": "Maximum steps reached without a conclusive answer.",
                "confidence": 0.0,
                "status": "incomplete",
            }
            self.trace.record(action="MAX_STEPS", status="exceeded")

        return self._build_result(state)

    # ==================================================================
    # ACTION HANDLERS
    # ==================================================================

    async def _handle_call(self, decision: Decision, state: AgentState) -> None:
        """Execute a single capability."""
        self.trace.start_timer()

        obs = await self.executor.run(
            decision.capability, decision.arguments, state
        )

        latency = self.trace.stop_timer()
        state.add_observation(obs)

        record = TaskRecord(
            task_id=obs.evidence_id,
            capability=decision.capability,
            status=obs.status.value,
            evidence_id=obs.evidence_id,
            error=obs.error_message,
        )
        state.record_task(record)

        self.trace.record(
            action="CALL_CAPABILITY",
            capability=decision.capability,
            model=obs.source.model,
            backend=obs.source.backend,
            input_refs=list(decision.arguments.keys()),
            output_refs=[obs.evidence_id] + obs.artifacts,
            status=obs.status.value,
            latency_s=latency,
            confidence=obs.confidence,
            rationale=decision.reason,
        )

    async def _handle_parallel(self, decision: Decision, state: AgentState) -> None:
        """Execute independent capabilities concurrently."""
        self.trace.start_timer()

        try:
            observations = await self._parallel.run_parallel(
                decision.parallel_capabilities, state
            )
        except ValueError as exc:
            self.trace.stop_timer()
            logger.warning("Invalid parallel decision at step %d: %s", self._steps, exc)
            self.trace.record(
                action="INVALID_DECISION",
                status="rejected",
                rationale=str(exc),
            )
            return

        latency = self.trace.stop_timer()

        for obs in observations:
            state.add_observation(obs)
            record = TaskRecord(
                task_id=obs.evidence_id,
                capability=obs.source.capability,
                status=obs.status.value,
                evidence_id=obs.evidence_id,
                error=obs.error_message,
            )
            state.record_task(record)

        self.trace.record(
            action="PARALLEL",
            capability=", ".join(
                t.get("capability", "") for t in decision.parallel_capabilities
            ),
            status="completed",
            latency_s=latency,
            rationale=decision.reason,
        )

    async def _handle_retry(self, decision: Decision, state: AgentState) -> None:
        """Retry a previously failed capability."""
        # Count prior retries
        prior = sum(
            1
            for t in state.failed_tasks
            if t.capability == decision.capability
        )
        if prior >= self.settings.max_retries_per_task:
            obs = Observation(
                source=EvidenceSource(
                    capability=decision.capability, backend="controller"
                ),
                type=EvidenceType.ERROR,
                status=ObservationStatus.FAILURE,
                result={"error": "Max retries exceeded"},
                error_message=f"Max retries ({self.settings.max_retries_per_task}) exceeded for {decision.capability}",
            )
            state.add_observation(obs)
            self.trace.record(
                action="RETRY_EXCEEDED",
                capability=decision.capability,
                status="failure",
                rationale=f"Exceeded {self.settings.max_retries_per_task} retries.",
            )
            return

        # Re-execute
        await self._handle_call(decision, state)

    def _handle_replan(self, decision: Decision, state: AgentState) -> None:
        """Record a replan event."""
        state.replans += 1
        if state.replans > self.settings.max_replans:
            obs = Observation(
                source=EvidenceSource(capability="replan", backend="controller"),
                type=EvidenceType.ERROR,
                status=ObservationStatus.FAILURE,
                result={"error": "Max replans exceeded"},
                error_message=f"Max replans ({self.settings.max_replans}) exceeded",
            )
            state.add_observation(obs)
        self.trace.record(
            action="REPLAN",
            status="replanned",
            rationale=decision.reason,
        )

    def _handle_request_input(self, decision: Decision, state: AgentState) -> None:
        """Pause execution to request user input."""
        state.final_result = {
            "answer": decision.reason,
            "status": "awaiting_input",
            "confidence": 0.0,
        }
        self.trace.record(
            action="REQUEST_INPUT",
            status="paused",
            rationale=decision.reason,
        )

    def _handle_conversational(self, decision: Decision, state: AgentState) -> None:
        """Handle pure conversational responses — no models invoked."""
        state.final_result = {
            "answer": decision.final_answer or decision.reason,
            "confidence": 1.0,
            "status": "conversational",
        }
        self.trace.record(
            action="CONVERSATIONAL",
            status="complete",
            rationale=decision.reason,
        )

    def _handle_final(self, decision: Decision, state: AgentState) -> None:
        """Finalise the agent run."""
        # Optional verification
        verification = self.critic.evaluate(state.observations)
        state.verification_status = "passed" if verification.sufficient else "failed"

        # Confidence
        state.confidence = self.confidence_engine.compute(state.observations)

        state.final_result = {
            "answer": decision.final_answer,
            "confidence": decision.final_confidence or state.confidence,
            "status": "complete",
            "verification": verification.model_dump(),
        }
        self.trace.record(
            action="FINAL",
            status="complete",
            confidence=state.confidence,
            rationale=decision.reason,
        )

    # ==================================================================
    # HELPERS
    # ==================================================================

    def _init_state(
        self,
        request: str,
        input_assets: list[dict[str, Any]] | None,
        metadata: dict[str, Any] | None,
    ) -> AgentState:
        assets = [
            AssetReference(**a) for a in (input_assets or [])
        ]
        return AgentState(
            request=request,
            input_assets=assets,
            metadata=metadata or {},
            current_goal=request,
        )

    def _build_result(self, state: AgentState) -> dict[str, Any]:
        return {
            "answer": (state.final_result or {}).get("answer", ""),
            "confidence": state.confidence or 0.0,
            "status": (state.final_result or {}).get("status", "unknown"),
            "evidence": [
                {
                    "evidence_id": o.evidence_id,
                    "capability": o.source.capability,
                    "type": o.type.value,
                    "status": o.status.value,
                    "confidence": o.confidence,
                }
                for o in state.observations
            ],
            "artifact_ids": state.artifact_ids,
            "verification": (state.final_result or {}).get("verification"),
            "trace": self.trace.to_dicts(),
            "step_count": state.step_count,
            "replans": state.replans,
        }
