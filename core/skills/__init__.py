"""
Skills system for modular, composable functionality.

Skills are atomic units of work that can be composed into workflows.
Each skill has a well-defined interface with typed inputs and outputs.
"""

from .base import (
    Skill,
    LLMSkill,
    CompositeSkill,
    SkillCategory,
    SkillMetadata,
    SkillContext,
    SkillResult,
)
from .registry import (
    SkillRegistry,
    SkillNotFoundError,
    SkillRegistrationError,
    skill,
)

__all__ = [
    # Base classes
    "Skill",
    "LLMSkill",
    "CompositeSkill",
    # Data classes
    "SkillCategory",
    "SkillMetadata",
    "SkillContext",
    "SkillResult",
    # Registry
    "SkillRegistry",
    "SkillNotFoundError",
    "SkillRegistrationError",
    "skill",
]
