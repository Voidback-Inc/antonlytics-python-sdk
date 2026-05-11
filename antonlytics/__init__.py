"""
Antonlytics Python SDK - Memory for AI Agents

Simple SDK for giving your AI agent persistent memory.
"""

from .agent import Agent
from .exceptions import AntonlyticsError, APIError, AuthenticationError

__version__ = "2.1.0"
__all__ = ["Agent", "AntonlyticsError", "APIError", "AuthenticationError"]
