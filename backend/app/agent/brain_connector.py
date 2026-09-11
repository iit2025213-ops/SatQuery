# app/agent/brain_connector.py

import websockets
import asyncio
import json
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("satquery")


class BrainConnector:
    """WebSocket client for AI Brain communication"""

    def __init__(self, brain_url: str = settings.ai_brain_url):
        self.brain_url = brain_url
        self.connection = None

    async def connect(self) -> bool:
        """Establish WebSocket connection to Brain"""
        try:
            self.connection = await websockets.connect(self.brain_url)
            logger.info(f"Connected to AI Brain: {self.brain_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to AI Brain: {str(e)}")
            return False

    async def send_state_and_get_decision(self, agent_state: dict) -> Optional[dict]:
        """
        Send AgentState to Brain, receive Decision

        Request format:
        {
            "type": "get_decision",
            "agent_state": {...}
        }

        Response format:
        {
            "type": "decision",
            "action": "CALL_TOOL" | "PARALLEL" | "FINAL" | "REPLAN",
            "capability": "...",
            "arguments": {...},
            "reason": "..."
        }
        """
        if not self.connection:
            logger.error("Brain connection not established")
            return None

        try:
            message = {
                "type": "get_decision",
                "agent_state": agent_state
            }

            await self.connection.send(json.dumps(message))
            response_text = await asyncio.wait_for(
                self.connection.recv(),
                timeout=settings.ai_brain_timeout_seconds
            )

            decision = json.loads(response_text)
            logger.info(f"Received decision: {decision.get('action')}")

            return decision

        except asyncio.TimeoutError:
            logger.error("Brain connection timeout")
            return None
        except Exception as e:
            logger.error(f"Error communicating with Brain: {str(e)}")
            return None

    async def close(self):
        """Close WebSocket connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from AI Brain")
