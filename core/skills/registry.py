"""
Skills Registry for discovering and managing skills.

The registry provides:
- Skill registration and discovery
- Dependency injection for skill instances
- Skill validation and metadata access
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Callable, Optional, Type

from .base import Skill, SkillCategory, SkillMetadata

logger = logging.getLogger(__name__)


class SkillNotFoundError(Exception):
    """Raised when a skill is not found in the registry."""
    pass


class SkillRegistrationError(Exception):
    """Raised when skill registration fails."""
    pass


class SkillRegistry:
    """
    Central registry for all skills.

    Supports:
    - Manual registration via register()
    - Auto-discovery from directories via discover()
    - Lazy instantiation with dependency injection
    """

    _instance: Optional["SkillRegistry"] = None

    def __init__(self):
        # skill_id -> skill class or factory
        self._skills: dict[str, Type[Skill] | Callable[[], Skill]] = {}

        # skill_id -> cached instance
        self._instances: dict[str, Skill] = {}

        # skill_id -> metadata (for quick lookup without instantiation)
        self._metadata: dict[str, SkillMetadata] = {}

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful for testing)."""
        cls._instance = None

    def register(
        self,
        skill_class: Type[Skill] | Callable[[], Skill],
        skill_id: Optional[str] = None,
    ) -> None:
        """
        Register a skill class or factory.

        Args:
            skill_class: Skill class or factory function
            skill_id: Optional override for skill ID (uses metadata.id by default)
        """
        # Get metadata from class
        if hasattr(skill_class, "metadata"):
            if isinstance(skill_class.metadata, property):
                # Need to instantiate to get metadata
                try:
                    instance = skill_class()
                    metadata = instance.metadata
                except Exception:
                    if skill_id is None:
                        raise SkillRegistrationError(
                            f"Cannot determine skill ID for {skill_class}. "
                            "Provide skill_id parameter or ensure metadata is accessible."
                        )
                    metadata = None
            else:
                metadata = skill_class.metadata
        else:
            metadata = None

        # Determine skill ID
        final_id = skill_id or (metadata.id if metadata else None)
        if final_id is None:
            raise SkillRegistrationError(
                f"Cannot register skill {skill_class}: no ID provided"
            )

        # Check for duplicates
        if final_id in self._skills:
            logger.warning(f"Overwriting existing skill: {final_id}")

        self._skills[final_id] = skill_class
        if metadata:
            self._metadata[final_id] = metadata

        logger.debug(f"Registered skill: {final_id}")

    def unregister(self, skill_id: str) -> bool:
        """
        Remove a skill from the registry.

        Returns:
            True if skill was removed, False if not found
        """
        if skill_id in self._skills:
            del self._skills[skill_id]
            self._instances.pop(skill_id, None)
            self._metadata.pop(skill_id, None)
            return True
        return False

    def get(self, skill_id: str, **kwargs) -> Skill:
        """
        Get a skill instance by ID.

        Instantiates the skill if not already cached.

        Args:
            skill_id: The skill identifier
            **kwargs: Arguments to pass to skill constructor

        Returns:
            Skill instance

        Raises:
            SkillNotFoundError: If skill is not registered
        """
        if skill_id not in self._skills:
            raise SkillNotFoundError(f"Skill not found: {skill_id}")

        # Return cached instance if no kwargs and already instantiated
        if not kwargs and skill_id in self._instances:
            return self._instances[skill_id]

        # Instantiate
        skill_class = self._skills[skill_id]
        if callable(skill_class) and not isinstance(skill_class, type):
            # It's a factory function
            instance = skill_class(**kwargs) if kwargs else skill_class()
        else:
            # It's a class
            instance = skill_class(**kwargs) if kwargs else skill_class()

        # Cache if no custom kwargs
        if not kwargs:
            self._instances[skill_id] = instance

        return instance

    def has(self, skill_id: str) -> bool:
        """Check if a skill is registered."""
        return skill_id in self._skills

    def list_skills(self, category: Optional[SkillCategory] = None) -> list[str]:
        """
        List all registered skill IDs.

        Args:
            category: Optional filter by category

        Returns:
            List of skill IDs
        """
        if category is None:
            return list(self._skills.keys())

        return [
            skill_id
            for skill_id, metadata in self._metadata.items()
            if metadata.category == category
        ]

    def get_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        """Get metadata for a skill without instantiating it."""
        return self._metadata.get(skill_id)

    def discover(self, path: str | Path, pattern: str = "*.py") -> int:
        """
        Discover and register skills from a directory.

        Scans Python files for Skill subclasses and registers them.

        Args:
            path: Directory to scan
            pattern: Glob pattern for files to scan

        Returns:
            Number of skills discovered
        """
        path = Path(path)
        if not path.exists():
            logger.warning(f"Discovery path does not exist: {path}")
            return 0

        discovered = 0
        for file_path in path.glob(pattern):
            if file_path.name.startswith("_"):
                continue

            try:
                count = self._discover_from_file(file_path)
                discovered += count
            except Exception as e:
                logger.error(f"Failed to discover skills from {file_path}: {e}")

        logger.info(f"Discovered {discovered} skills from {path}")
        return discovered

    def _discover_from_file(self, file_path: Path) -> int:
        """Discover skills from a single Python file."""
        # Load module
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return 0

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find Skill subclasses
        discovered = 0
        for name in dir(module):
            if name.startswith("_"):
                continue

            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, Skill)
                and obj is not Skill
                and hasattr(obj, "metadata")
            ):
                try:
                    self.register(obj)
                    discovered += 1
                except SkillRegistrationError as e:
                    logger.warning(f"Could not register {name}: {e}")

        return discovered

    def clear_cache(self) -> None:
        """Clear all cached skill instances."""
        self._instances.clear()

    def __len__(self) -> int:
        """Return number of registered skills."""
        return len(self._skills)

    def __contains__(self, skill_id: str) -> bool:
        """Check if skill is registered."""
        return skill_id in self._skills


# Decorator for easy skill registration
def skill(skill_id: Optional[str] = None):
    """
    Decorator to register a skill class.

    Usage:
        @skill("my-plugin.my-skill")
        class MySkill(Skill):
            ...
    """
    def decorator(cls: Type[Skill]) -> Type[Skill]:
        SkillRegistry.get_instance().register(cls, skill_id=skill_id)
        return cls
    return decorator
