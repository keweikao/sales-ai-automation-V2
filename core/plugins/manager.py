"""
Plugin Manager for discovering, loading, and managing plugins.
"""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Callable, Optional, Type

from core.skills import SkillRegistry
from core.workflows import WorkflowLoader

from .base import Plugin, PluginHook, PluginMetadata, PluginState


logger = logging.getLogger(__name__)


class PluginError(Exception):
    """Base exception for plugin errors."""
    pass


class PluginNotFoundError(PluginError):
    """Raised when a plugin is not found."""
    pass


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""
    pass


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies are not satisfied."""
    pass


class PluginManager:
    """
    Manages plugin lifecycle and registration.

    Singleton pattern - use get_instance() to get the global instance.
    """

    _instance: Optional["PluginManager"] = None

    @classmethod
    def get_instance(cls) -> "PluginManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}
        self._hooks: dict[str, list[PluginHook]] = {}
        self._skill_registry = SkillRegistry.get_instance()
        self._workflow_loader = WorkflowLoader()
        self._config: dict[str, dict[str, Any]] = {}

    @property
    def plugins(self) -> dict[str, Plugin]:
        """Return all registered plugins."""
        return self._plugins.copy()

    def configure(self, config: dict[str, dict[str, Any]]) -> None:
        """
        Set plugin configurations.

        Args:
            config: Dict mapping plugin_id to plugin config
        """
        self._config = config

    def discover(self, path: str | Path) -> list[str]:
        """
        Discover plugins in a directory.

        Looks for Python packages with a plugin.py or __init__.py
        that exports a Plugin subclass.

        Args:
            path: Directory to search for plugins

        Returns:
            List of discovered plugin IDs
        """
        path = Path(path)
        discovered = []

        if not path.exists():
            logger.warning(f"Plugin directory does not exist: {path}")
            return discovered

        for item in path.iterdir():
            if not item.is_dir():
                continue

            # Skip private directories
            if item.name.startswith("_"):
                continue

            # Look for plugin.py or __init__.py with Plugin class
            plugin_file = item / "plugin.py"
            if not plugin_file.exists():
                plugin_file = item / "__init__.py"

            if plugin_file.exists():
                try:
                    plugin_id = self._load_plugin_from_file(plugin_file)
                    if plugin_id:
                        discovered.append(plugin_id)
                except Exception as e:
                    logger.error(f"Failed to discover plugin in {item}: {e}")

        return discovered

    def _load_plugin_from_file(self, file_path: Path) -> Optional[str]:
        """Load a plugin from a Python file."""
        spec = importlib.util.spec_from_file_location(
            f"plugin_{file_path.parent.name}",
            file_path,
        )
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find Plugin subclass
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, Plugin)
                and obj is not Plugin
            ):
                plugin = obj()
                self._register_plugin(plugin)
                return plugin.metadata.id

        return None

    def register(self, plugin_class: Type[Plugin]) -> str:
        """
        Register a plugin class.

        Args:
            plugin_class: Plugin class to register

        Returns:
            Plugin ID
        """
        plugin = plugin_class()
        return self._register_plugin(plugin)

    def _register_plugin(self, plugin: Plugin) -> str:
        """Register a plugin instance."""
        plugin_id = plugin.metadata.id

        if plugin_id in self._plugins:
            logger.warning(f"Plugin {plugin_id} already registered, replacing")

        self._plugins[plugin_id] = plugin
        logger.info(f"Registered plugin: {plugin_id}")

        return plugin_id

    def load(self, plugin_id: str) -> None:
        """
        Load a plugin by ID.

        Args:
            plugin_id: ID of the plugin to load

        Raises:
            PluginNotFoundError: If plugin is not registered
            PluginDependencyError: If dependencies are not satisfied
            PluginLoadError: If plugin fails to load
        """
        if plugin_id not in self._plugins:
            raise PluginNotFoundError(f"Plugin not found: {plugin_id}")

        plugin = self._plugins[plugin_id]

        # Check if already loaded
        if plugin.state in (PluginState.LOADED, PluginState.ENABLED):
            logger.debug(f"Plugin {plugin_id} already loaded")
            return

        # Check dependencies
        self._check_dependencies(plugin)

        # Configure
        plugin_config = self._config.get(plugin_id, {})
        plugin.configure(plugin_config)

        # Load
        try:
            plugin._state = PluginState.LOADING
            plugin.load()
            plugin._state = PluginState.LOADED

            # Register skills
            plugin.register_skills(self._skill_registry)

            # Register hooks
            for hook in plugin.get_hooks():
                self._register_hook(hook)

            logger.info(f"Loaded plugin: {plugin_id}")

        except Exception as e:
            plugin._state = PluginState.ERROR
            raise PluginLoadError(f"Failed to load plugin {plugin_id}: {e}") from e

    def _check_dependencies(self, plugin: Plugin) -> None:
        """Check if plugin dependencies are satisfied."""
        for dep_id in plugin.metadata.dependencies:
            if dep_id not in self._plugins:
                raise PluginDependencyError(
                    f"Plugin {plugin.metadata.id} requires {dep_id} which is not registered"
                )

            dep_plugin = self._plugins[dep_id]
            if dep_plugin.state not in (PluginState.LOADED, PluginState.ENABLED):
                raise PluginDependencyError(
                    f"Plugin {plugin.metadata.id} requires {dep_id} which is not loaded"
                )

    def _register_hook(self, hook: PluginHook) -> None:
        """Register a hook callback."""
        if hook.name not in self._hooks:
            self._hooks[hook.name] = []

        self._hooks[hook.name].append(hook)
        # Sort by priority (lower = higher priority)
        self._hooks[hook.name].sort(key=lambda h: h.priority)

    def enable(self, plugin_id: str) -> None:
        """Enable a loaded plugin."""
        if plugin_id not in self._plugins:
            raise PluginNotFoundError(f"Plugin not found: {plugin_id}")

        plugin = self._plugins[plugin_id]

        if plugin.state == PluginState.UNLOADED:
            self.load(plugin_id)

        plugin.enable()
        logger.info(f"Enabled plugin: {plugin_id}")

    def disable(self, plugin_id: str) -> None:
        """Disable a plugin without unloading."""
        if plugin_id not in self._plugins:
            raise PluginNotFoundError(f"Plugin not found: {plugin_id}")

        plugin = self._plugins[plugin_id]
        plugin.disable()
        logger.info(f"Disabled plugin: {plugin_id}")

    def unload(self, plugin_id: str) -> None:
        """Unload a plugin."""
        if plugin_id not in self._plugins:
            raise PluginNotFoundError(f"Plugin not found: {plugin_id}")

        plugin = self._plugins[plugin_id]
        plugin.unload()

        # Remove hooks
        for hook_name in list(self._hooks.keys()):
            self._hooks[hook_name] = [
                h for h in self._hooks[hook_name]
                if h not in plugin.get_hooks()
            ]

        logger.info(f"Unloaded plugin: {plugin_id}")

    def load_all(self) -> list[str]:
        """
        Load all registered plugins.

        Returns:
            List of successfully loaded plugin IDs
        """
        loaded = []
        # Sort by dependencies
        sorted_plugins = self._topological_sort()

        for plugin_id in sorted_plugins:
            try:
                self.load(plugin_id)
                loaded.append(plugin_id)
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_id}: {e}")

        return loaded

    def enable_all(self) -> list[str]:
        """
        Enable all loaded plugins.

        Returns:
            List of successfully enabled plugin IDs
        """
        enabled = []
        for plugin_id, plugin in self._plugins.items():
            try:
                if plugin.state == PluginState.LOADED:
                    self.enable(plugin_id)
                    enabled.append(plugin_id)
            except Exception as e:
                logger.error(f"Failed to enable plugin {plugin_id}: {e}")

        return enabled

    def _topological_sort(self) -> list[str]:
        """Sort plugins by dependencies (topological sort)."""
        # Build dependency graph
        in_degree: dict[str, int] = {}
        graph: dict[str, list[str]] = {}

        for plugin_id, plugin in self._plugins.items():
            in_degree.setdefault(plugin_id, 0)
            graph.setdefault(plugin_id, [])

            for dep_id in plugin.metadata.dependencies:
                if dep_id in self._plugins:
                    in_degree[plugin_id] = in_degree.get(plugin_id, 0) + 1
                    graph.setdefault(dep_id, []).append(plugin_id)

        # Kahn's algorithm
        queue = [pid for pid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for neighbor in graph.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def emit(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        """
        Emit a hook event.

        Calls all registered callbacks for the hook.

        Args:
            hook_name: Name of the hook
            *args: Positional arguments to pass to callbacks
            **kwargs: Keyword arguments to pass to callbacks

        Returns:
            List of callback results
        """
        results = []

        for hook in self._hooks.get(hook_name, []):
            try:
                result = hook.callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook {hook_name} callback failed: {e}")

        return results

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID."""
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[PluginMetadata]:
        """List all registered plugins."""
        return [p.metadata for p in self._plugins.values()]

    def get_plugin_state(self, plugin_id: str) -> Optional[PluginState]:
        """Get the state of a plugin."""
        plugin = self._plugins.get(plugin_id)
        return plugin.state if plugin else None
