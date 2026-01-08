"""
Abstract interfaces for services.

Defines contracts that service implementations must follow.
"""

from .journey_logger import JourneyLogger

__all__ = ["JourneyLogger"]
