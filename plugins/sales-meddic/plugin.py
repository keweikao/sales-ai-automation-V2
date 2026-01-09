"""
Sales MEDDIC Plugin.

Provides MEDDIC-specific sales methodology analysis skills:
- Buyer Analysis (Agent 2)
- Seller Coaching (Agent 3)
- Coach Evaluation (Agent 5)

Depends on sales-core plugin for Context Analysis.
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
    # Check if already loaded
    if "sales_conversation_skills" in sys.modules:
        return sys.modules["sales_conversation_skills"]

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


class SalesMeddicPlugin(Plugin):
    """
    MEDDIC methodology sales analysis plugin.

    Provides specialized skills for MEDDIC-based sales analysis:
    - Buyer analysis (MEDDIC qualification)
    - Seller coaching (performance evaluation)
    - Coach alerts (real-time notifications)

    Depends on:
    - sales-core: For context analysis
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
            id="sales-meddic",
            name="Sales MEDDIC",
            version="1.0.0",
            description="MEDDIC methodology sales analysis skills",
            author="Sales AI Team",
            dependencies=["sales-core"],  # Requires sales-core for context
            tags=["sales", "meddic", "qualification", "coaching"],
            config_schema={
                "type": "object",
                "properties": {
                    "enable_coach_alerts": {
                        "type": "boolean",
                        "default": True,
                        "description": "Enable real-time coaching alerts",
                    },
                    "progress_score_threshold": {
                        "type": "integer",
                        "default": 80,
                        "description": "Threshold for close-now alerts",
                    },
                    "enable_manager_alerts": {
                        "type": "boolean",
                        "default": True,
                        "description": "Enable manager escalation alerts",
                    },
                    "consecutive_low_threshold": {
                        "type": "integer",
                        "default": 3,
                        "description": "Consecutive low scores before manager alert",
                    },
                },
            },
        )

    def load(self) -> None:
        """Load the plugin."""
        # Pre-load skills module
        self._get_skills()

        # Register hooks for MEDDIC-specific events
        self.register_hook(
            name="analysis.complete",
            callback=self._on_analysis_complete,
            description="Evaluate coaching alerts after analysis",
            priority=100,  # High priority
        )

        self.register_hook(
            name="skill.buyer.complete",
            callback=self._on_buyer_complete,
            description="Post-process buyer analysis",
            priority=100,
        )

    def get_skills(self) -> list[Type[Skill]]:
        """Return skills provided by this plugin."""
        skills = self._get_skills()
        return [
            skills.BuyerAnalysisSkill,
            skills.SellerCoachingSkill,
            skills.CoachEvaluationSkill,
        ]

    def get_workflows(self) -> list[str]:
        """Return workflow definitions provided by this plugin."""
        return [
            "plugins/sales-meddic/workflows/full-meddic-analysis.yaml",
        ]

    def _on_analysis_complete(
        self,
        case_id: str,
        context_insights: dict,
        buyer_insights: dict,
        seller_insights: dict,
        **kwargs,
    ) -> dict | None:
        """
        Hook callback after full analysis is complete.

        Evaluates if coaching alerts should be triggered.
        """
        import logging

        logger = logging.getLogger(__name__)

        if not self.config.get("enable_coach_alerts", True):
            return None

        try:
            skills = self._get_skills()
            coach_skill = skills.CoachEvaluationSkill()

            # Check if we should alert
            from core.skills import SkillContext

            result = coach_skill.execute(
                input_data=skills.CoachInput(
                    case_id=case_id,
                    rep_id=kwargs.get("rep_id", ""),
                    rep_name=kwargs.get("rep_name", ""),
                    store_name=kwargs.get("store_name", ""),
                    context_insights=context_insights,
                    buyer_insights=buyer_insights,
                    seller_insights=seller_insights,
                ),
                context=SkillContext(case_id=case_id),
            )

            if result.success and result.data.should_alert:
                logger.info(f"[sales-meddic] Coach alert triggered for case {case_id}")
                return {
                    "alert": result.data.alert,
                    "slack_blocks": result.data.slack_blocks,
                }

            return None

        except Exception as e:
            logger.error(f"[sales-meddic] Coach evaluation failed: {e}")
            return None

    def _on_buyer_complete(
        self,
        case_id: str,
        buyer_data: dict,
        **kwargs,
    ) -> None:
        """Hook callback after buyer analysis completes."""
        import logging

        logger = logging.getLogger(__name__)
        meddic_score = buyer_data.get("meddic_score", 0)
        logger.debug(f"[sales-meddic] Case {case_id} MEDDIC score: {meddic_score}")
