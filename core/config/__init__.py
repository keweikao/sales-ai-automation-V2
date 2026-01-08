"""
Configuration management for Sales AI Automation V2.1

Provides centralized settings with environment-specific overrides.
"""

from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
