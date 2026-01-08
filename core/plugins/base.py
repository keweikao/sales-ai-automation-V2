"""
Plugin base classes and interfaces.

Defines the contract for plugins that can extend the system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Type

from core.skills import Skill, SkillRegistry


class PluginState(str, Enum):
    """Plugin lifecycle states."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """Metadata describing a plugin."""
    id: str  # Unique identifier, e.g., "sales-meddic"
    name: str  # Human-readable name
    version: str  # Semantic version
    description: str
    author: Optional[str] = None
    dependencies: list[str] = field(default_factory=list)  # Plugin IDs
    tags: list[str] = field(default_factory=list)
    config_schema: Optional[dict[str, Any]] = None  # JSON Schema for config


@dataclass
class PluginHook:
    """A hook point that plugins can register callbacks for."""
    name: str
    description: str
    callback: Callable[..., Any]
    priority: int = 100  # Lower = higher priority


class Plugin(ABC):
    """
    Base class for all plugins.

    Plugins can:
    - Register skills with the skill registry
    - Register workflows
    - Add hooks for lifecycle events
    - Provide configuration
    """

    def __init__(self):
        self._state = PluginState.UNLOADED
        self._config: dict[str, Any] = {}
        self._hooks: list[PluginHook] = []

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @property
    def state(self) -> PluginState:
        """Current plugin state."""
        return self._state

    @property
    def config(self) -> dict[str, Any]:
        """Current plugin configuration."""
        return self._config

    def configure(self, config: dict[str, Any]) -> None:
        """
        Configure the plugin.

        Called before load() with user/system configuration.
        """
        self._config = config

    @abstractmethod
    def load(self) -> None:
        """
        Load the plugin.

        Called when the plugin is first loaded.
        Register skills, workflows, and hooks here.
        """
        pass

    def enable(self) -> None:
        """
        Enable the plugin.

        Called after load() or when re-enabling a disabled plugin.
        Override for custom enable logic.
        """
        self._state = PluginState.ENABLED

    def disable(self) -> None:
        """
        Disable the plugin.

        Called to temporarily disable without unloading.
        Override for custom disable logic.
        """
        self._state = PluginState.DISABLED

    def unload(self) -> None:
        """
        Unload the plugin.

        Called when the plugin is being removed.
        Clean up resources here.
        """
        self._state = PluginState.UNLOADED

    def get_skills(self) -> list[Type[Skill]]:
        """
        Return list of skill classes provided by this plugin.

        Override to provide skills.
        """
        return []

    def get_workflows(self) -> list[str]:
        """
        Return list of workflow definition paths.

        Override to provide workflow definitions.
        """
        return []

    def get_hooks(self) -> list[PluginHook]:
        """Return registered hooks."""
        return self._hooks

    def register_hook(
        self,
        name: str,
        callback: Callable[..., Any],
        description: str = "",
        priority: int = 100,
    ) -> None:
        """Register a hook callback."""
        self._hooks.append(
            PluginHook(
                name=name,
                callback=callback,
                description=description,
                priority=priority,
            )
        )

    def register_skills(self, registry: SkillRegistry) -> None:
        """
        Register all skills with the registry.

        Default implementation registers skills from get_skills().
        Override for custom registration logic.
        """
        for skill_class in self.get_skills():
            registry.register(skill_class)
