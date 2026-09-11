# app/agent/controller.py

import asyncio
import logging
from typing import List

from app.agent.brain_connector import BrainConnector
from app.agent.state import AgentState, Observation
from app.config import settings

logger = logging.getLogger("satquery")


class AgentController:
    """Main agent loop orchestrator"""

    def __init__(self, brain_connector: BrainConnector, executor):
        self.brain = brain_connector
        self.executor = executor

    async def run_agent_loop(self, job_id: str, query: str, asset_ids: List[str], supabase_client) -> dict:
        """
        Main agentic loop

        Flow:
        1. Initialize AgentState
        2. Send to Brain
        3. Brain returns decision
        4. Executor validates + executes
        5. Collect observation
        6. Loop back to step 2
        7. Until Brain says FINAL
        """

        # Initialize state
        state = AgentState(
            job_id=job_id,
            user_request=query,
            input_assets=asset_ids
        )

        # Connect to Brain
        if not await self.brain.connect():
            logger.error(f"Failed to connect to Brain for job {job_id}")
            return {"status": "failed", "reason": "Brain connection failed"}

        try:
            step_count = 0
            max_steps = settings.max_agent_steps

            while not state.finished and step_count < max_steps:
                step_count += 1
                state.current_step = step_count

                # Send state to Brain
                logger.info(f"[Job {job_id}] Step {step_count}: Sending state to Brain")
                decision = await self.brain.send_state_and_get_decision(state.to_dict())

                if not decision:
                    obs = Observation(
                        step_number=step_count,
                        source_capability="brain_connector",
                        status="failed",
                        result={"error": "Brain connection failed"}
                    )
                    state.add_observation(obs)
                    break

                # Process decision
                action = decision.get("action")

                if action == "CALL_TOOL":
                    # Single tool execution
                    capability = decision.get("capability")
                    arguments = decision.get("arguments", {})

                    logger.info(f"[Job {job_id}] Step {step_count}: Executing {capability}")

                    observation = await self.executor.execute_capability(
                        capability,
                        arguments,
                        state,
                        supabase_client
                    )

                    state.add_observation(observation)

                elif action == "PARALLEL":
                    # Multiple tool execution
                    tasks = decision.get("tasks", [])

                    logger.info(f"[Job {job_id}] Step {step_count}: Executing {len(tasks)} tasks in parallel")

                    observations = await self.executor.execute_parallel(
                        tasks,
                        state,
                        supabase_client
                    )

                    for obs in observations:
                        state.add_observation(obs)

                elif action == "FINAL":
                    # Brain says we're done
                    state.finished = True
                    state.final_result = decision.get("answer")
                    state.confidence = decision.get("confidence")

                    logger.info(f"[Job {job_id}] Completed: {state.final_result}")

                elif action == "REPLAN":
                    # Brain wants to replan
                    state.replans += 1
                    if state.replans > settings.max_replans:
                        state.finished = True
                        obs = Observation(
                            step_number=step_count,
                            source_capability="controller",
                            status="failed",
                            result={"error": "Max replans exceeded"}
                        )
                        state.add_observation(obs)

                    logger.info(f"[Job {job_id}] Replan {state.replans}")

                else:
                    logger.error(f"[Job {job_id}] Unknown action: {action}")
                    break

                # Save state to database
                await self.save_job_state(job_id, state, supabase_client)

                # Emit WebSocket event
                await self.emit_event(job_id, {
                    "type": "step_completed",
                    "step": step_count,
                    "capability": decision.get("capability") if action == "CALL_TOOL" else None,
                    "status": "success" if action != "CALL_TOOL" else state.observations[-1].status
                })

            # Final save
            await self.save_job_state(job_id, state, supabase_client)

            return {"status": "completed", "result": state.final_result}

        finally:
            await self.brain.close()

    async def save_job_state(self, job_id: str, state: AgentState, supabase_client):
        """Save agent state to database"""
        try:
            supabase_client.get_admin_client().table("jobs").update({
                "agent_state": state.to_dict(),
                "current_step": state.current_step,
                "status": "completed" if state.finished else "running",
                "final_answer": state.final_result,
                "confidence": state.confidence
            }).eq("job_id", job_id).execute()
        except Exception as e:
            logger.error(f"Failed to save job state: {str(e)}")

    async def emit_event(self, job_id: str, event: dict):
        """Emit WebSocket event (implemented in MEGAPROMPT 9)"""
        pass
