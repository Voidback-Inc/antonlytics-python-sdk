"""
Antonlytics Python SDK — Memory + Ontology infrastructure for AI agents
and SaaS applications.

Two entry points:

  * ``Agent``        — project-scoped: ingest, chat, retrieval, system prompt.
  * ``Antonlytics``  — account-level: project CRUD, plus ``.agent()`` factory.
"""

from .agent import Agent
from .client import Antonlytics
from .exceptions import AntonlyticsError, APIError, AuthenticationError

__version__ = "2.3.0"  # bumped: ingest_triplets + Antonlytics client
__all__ = [
    "Agent",
    "Antonlytics",
    "AntonlyticsError",
    "APIError",
    "AuthenticationError",
]
