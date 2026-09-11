# app/models/base.py

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger("satquery")


class BaseAdapter(ABC):
    """Base class for model adapters"""

    @abstractmethod
    async def execute(self, arguments: dict, state, supabase_client):
        """
        Execute the model

        Returns Observation
        """
        pass
