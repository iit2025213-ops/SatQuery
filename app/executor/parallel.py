"""Parallel execution support.

Runs independent capabilities concurrently while preserving sequential
execution for capabilities with dependencies.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agent.state import AgentState
from app.evidence.schema import Observation
from app.executor.executor import DefaultExecutor

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """Runs multiple capabilities concurrently via asyncio.gather."""

    def __init__(self, executor: DefaultExecutor) -> None:
        self._executor = executor

    async def run_parallel(
        self,
        tasks: list[dict[str, Any]],
        state: AgentState,
    ) -> list[Observation]:
        """Execute *tasks* concurrently.

        Each task dict should contain ``capability`` and ``arguments``.
        """
        if not tasks:
            return []

        # Validate no mutual dependencies (simple check: no task
        # references another task's output artifact by name)
        self._validate_independence(tasks)

        coros = [
            self._executor.run(
                t["capability"],
                t.get("arguments", {}),
                state,
            )
            for t in tasks
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)

        observations: list[Observation] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Parallel task %s failed: %s",
                    tasks[i].get("capability"),
                    result,
                )
                from app.executor.executor import _error_observation

                observations.append(
                    _error_observation(
                        tasks[i].get("capability", "unknown"), str(result)
                    )
                )
            else:
                observations.append(result)

        return observations

    @staticmethod
    def _validate_independence(tasks: list[dict[str, Any]]) -> None:
        """Raise if tasks have obvious mutual dependencies."""
        output_caps = {t.get("capability", "") for t in tasks}
        for task in tasks:
            args = task.get("arguments", {})
            for value in args.values():
                if isinstance(value, str) and value in output_caps:
                    raise ValueError(
                        f"Parallel task '{task.get('capability')}' depends "
                        f"on '{value}' which is also running in parallel."
                    )
