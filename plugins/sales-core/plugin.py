"""
Sales Core Plugin.

Provides core sales conversation analysis skills:
- Context Analysis (Agent 1)
- Summary Generation (Agent 4)
- CRM Extraction (Agent 6)
"""

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Type

from core.plugins import Plugin, PluginMetadata
from core.skills import Skill


def _get_skills_module():
    """
    Import skills from the sales-conversation module.

    Handles the hyphenated directory name by using importlib.
    """
    # Get the module path
    project_root = Path(__file__).parent.parent.parent
    skills_path = project_root / "modules" / "03-sales-conversation" / "skills"

    # Add project root to path if needed
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Import using importlib
    spec = importlib.util.spec_from_file_location(
        "sales_conversation_skills",
        skills_path / "__init__.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load skills from {skills_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["sales_conversation_skills"] = module
    spec.loader.exec_module(module)

    return module


# Type hints for IDE support
if TYPE_CHECKING:
    pass


class SalesCorePlugin(Plugin):
    """
    Core sales conversation analysis plugin.

    Provides essential skills for any sales conversation analysis:
    - Context extraction (customer info, meeting context)
    - Summary generation (executive summary)
    - CRM field extraction (Salesforce-ready data)
    """

    _skills_module = None

    @classmethod
    def _get_skills(cls):
        """Lazy-load skills module."""
        if cls._skills_module is None:
            cls._skills_module = _get_skills_module()
        return cls._skills_module

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="sales-core",
            name="Sales Core",
            version="1.0.0",
            description="Core sales conversation analysis skills",
            author="Sales AI Team",
            dependencies=[],  # No dependencies - this is a base plugin
            tags=["sales", "analysis", "core"],
            config_schema={
                "type": "object",
                "properties": {
                    "default_language": {
                        "type": "string",
                        "default": "zh-TW",
                        "description": "Default language for analysis",
                    },
                    "summary_max_length": {
                        "type": "integer",
                        "default": 500,
                        "description": "Maximum summary length in characters",
                    },
                },
            },
        )

    def load(self) -> None:
        """Load the plugin."""
        # Pre-load skills module
        self._get_skills()

        # Register hooks for workflow events
        self.register_hook(
            name="workflow.step.before",
            callback=self._on_step_before,
            description="Log before each workflow step",
            priority=200,  # Low priority
        )

        self.register_hook(
            name="workflow.step.after",
            callback=self._on_step_after,
            description="Log after each workflow step",
            priority=200,
        )

    def get_skills(self) -> list[Type[Skill]]:
        """Return skills provided by this plugin."""
        skills = self._get_skills()
        return [
            skills.ContextAnalysisSkill,
            skills.SummaryGenerationSkill,
            skills.CRMExtractionSkill,
        ]

    def get_workflows(self) -> list[str]:
        """Return workflow definitions provided by this plugin."""
        return [
            "plugins/sales-core/workflows/basic-analysis.yaml",
        ]

    def _on_step_before(self, step_id: str, skill_id: str, **kwargs) -> None:
        """Hook callback before workflow step execution."""
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"[sales-core] Starting step {step_id} with skill {skill_id}")

    def _on_step_after(
        self,
        step_id: str,
        skill_id: str,
        success: bool,
        duration_ms: float,
        **kwargs,
    ) -> None:
        """Hook callback after workflow step execution."""
        import logging

        logger = logging.getLogger(__name__)
        status = "completed" if success else "failed"
        logger.debug(f"[sales-core] Step {step_id} {status} in {duration_ms:.1f}ms")
