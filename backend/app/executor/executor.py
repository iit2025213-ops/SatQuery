# app/executor/executor.py

import asyncio
import logging
from typing import List, Optional

from app.config import settings

logger = logging.getLogger("satquery")


class Executor:
    """Executes LLM decisions with validation"""

    def __init__(self, registry):
        self.registry = registry

    def validate_decision(self, decision: dict) -> bool:
        """Validate LLM decision output"""
        required_fields = ["action"]

        for field in required_fields:
            if field not in decision:
                logger.error(f"Invalid decision: missing {field}")
                return False

        action = decision.get("action")
        valid_actions = ["CALL_TOOL", "PARALLEL", "FINAL", "REPLAN"]

        if action not in valid_actions:
            logger.error(f"Invalid action: {action}")
            return False

        if action == "CALL_TOOL" and "capability" not in decision:
            logger.error("CALL_TOOL missing capability")
            return False

        return True

    async def execute_capability(self, capability_name: str, arguments: dict, state, supabase_client):
        """Execute a single capability"""
        from app.agent.state import Observation

        # Get capability from registry
        capability = self.registry.get_capability(capability_name)

        if not capability:
            logger.error(f"Unknown capability: {capability_name}")
            return Observation(
                step_number=state.current_step,
                source_capability=capability_name,
                status="failed",
                result={"error": f"Unknown capability: {capability_name}"}
            )

        # Validate prerequisites
        prereq_valid, prereq_reason = await self.validate_prerequisites(
            capability_name,
            arguments,
            state,
            supabase_client
        )

        if not prereq_valid:
            logger.warning(f"Prerequisites not met: {prereq_reason}")
            return Observation(
                step_number=state.current_step,
                source_capability=capability_name,
                status="blocked",
                result={"error": prereq_reason}
            )

        # Get adapter and execute with retries
        adapter = self.registry.get_adapter(capability_name)

        for attempt in range(settings.max_retries_per_task):
            try:
                logger.info(f"Executing {capability_name} (attempt {attempt + 1})")

                observation = await adapter.execute(arguments, state, supabase_client)

                logger.info(f"Capability {capability_name} succeeded")
                return observation

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")

                if attempt == settings.max_retries_per_task - 1:
                    logger.error(f"Capability {capability_name} failed after {settings.max_retries_per_task} attempts")
                    return Observation(
                        step_number=state.current_step,
                        source_capability=capability_name,
                        status="failed",
                        result={"error": str(e)}
                    )

    async def validate_prerequisites(self, capability_name: str, arguments: dict, state, supabase_client):
        """Check hard safety gates before execution"""

        # Example: Change detection requires 2 images
        if capability_name == "detect_bitemporal_change":
            if len(state.input_assets) < 2:
                return False, "Two images required for change detection"

            # Validate spatial compatibility
            # (implement actual validation)
            return True, ""

        # Add more capability-specific checks

        return True, ""

    async def execute_parallel(self, tasks: List[dict], state, supabase_client) -> List:
        """Execute independent tasks concurrently"""

        # Create tasks
        async_tasks = [
            self.execute_capability(
                task.get("capability"),
                task.get("arguments", {}),
                state,
                supabase_client
            )
            for task in tasks
        ]

        # Run concurrently
        results = await asyncio.gather(*async_tasks)

        return results
