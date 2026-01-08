"""
Plugin system for modular feature organization.

Plugins can package skills, workflows, and hooks together
for easy distribution and management.
"""

from .base import (
    Plugin,
    PluginHook,
    PluginMetadata,
    PluginState,
)
from .manager import (
    PluginManager,
    PluginError,
    PluginNotFoundError,
    PluginLoadError,
    PluginDependencyError,
)

__all__ = [
    # Base classes
    "Plugin",
    "PluginHook",
    "PluginMetadata",
    "PluginState",
    # Manager
    "PluginManager",
    # Exceptions
    "PluginError",
    "PluginNotFoundError",
    "PluginLoadError",
    "PluginDependencyError",
]
