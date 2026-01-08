"""
Prompt Evolver - A/B testing and evolution of agent prompts.

Enables data-driven improvement of prompts based on real-world outcomes.
"""

import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid
import math

from core.schemas.outcome import LearningSignal, PromptImprovement

logger = logging.getLogger(__name__)


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class PromptVariant:
    """A prompt variant for A/B testing."""
    name: str
    prompt: str
    description: str = ""


@dataclass
class VariantAssignment:
    """Record of which variant was assigned to a case."""
    case_id: str
    variant_name: str
    assigned_at: datetime


@dataclass
class VariantMetrics:
    """Metrics for a prompt variant."""
    sample_size: int
    win_rate: float
    avg_meddic_accuracy: float
    suggestion_acceptance_rate: float
    summary_edit_rate: float


@dataclass
class ABExperiment:
    """An A/B test comparing prompt variants."""
    id: str
    agent_id: str
    hypothesis: str
    control: PromptVariant
    treatment: PromptVariant
    success_metric: str  # "win_rate", "acceptance_rate", etc.
    required_sample_size: int
    status: ExperimentStatus = ExperimentStatus.DRAFT
    assignments: List[VariantAssignment] = field(default_factory=list)
    control_metrics: Optional[VariantMetrics] = None
    treatment_metrics: Optional[VariantMetrics] = None
    winner: Optional[str] = None
    p_value: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class PromptVersion:
    """A versioned prompt for an agent."""
    agent_id: str
    version: int
    prompt: str
    description: str
    source: str  # "manual", "experiment", "auto_evolution"
    performance_score: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = False


class PromptEvolver:
    """
    Manages prompt evolution through A/B testing and automated improvements.

    This is the "brain" that allows agents to get smarter over time.
    """

    def __init__(self, firestore_client):
        self.firestore = firestore_client
        self.active_experiments: Dict[str, ABExperiment] = {}
        self.prompt_history: Dict[str, List[PromptVersion]] = {}

    # =========================================================================
    # Experiment Management
    # =========================================================================

    async def create_experiment(
        self,
        agent_id: str,
        hypothesis: str,
        control_prompt: str,
        treatment_prompt: str,
        success_metric: str = "win_rate",
        sample_size: int = 100,
        control_description: str = "Current prompt",
        treatment_description: str = "New prompt variation",
    ) -> ABExperiment:
        """Create a new A/B test experiment."""
        experiment = ABExperiment(
            id=f"exp_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            agent_id=agent_id,
            hypothesis=hypothesis,
            control=PromptVariant(
                name="control",
                prompt=control_prompt,
                description=control_description
            ),
            treatment=PromptVariant(
                name="treatment",
                prompt=treatment_prompt,
                description=treatment_description
            ),
            success_metric=success_metric,
            required_sample_size=sample_size,
            status=ExperimentStatus.DRAFT,
        )

        # Store in Firestore
        await self._store_experiment(experiment)

        logger.info(f"Created experiment {experiment.id} for agent {agent_id}")
        return experiment

    async def start_experiment(self, experiment_id: str) -> ABExperiment:
        """Start running an experiment."""
        experiment = await self._load_experiment(experiment_id)

        if experiment.status != ExperimentStatus.DRAFT:
            raise ValueError(f"Experiment {experiment_id} is not in draft status")

        experiment.status = ExperimentStatus.RUNNING
        self.active_experiments[experiment_id] = experiment

        await self._store_experiment(experiment)

        logger.info(f"Started experiment {experiment_id}")
        return experiment

    async def assign_variant(
        self,
        experiment_id: str,
        case_id: str
    ) -> PromptVariant:
        """Assign a case to a variant (50/50 random split)."""
        experiment = self.active_experiments.get(experiment_id)
        if not experiment:
            experiment = await self._load_experiment(experiment_id)
            self.active_experiments[experiment_id] = experiment

        if experiment.status != ExperimentStatus.RUNNING:
            # Return control if experiment not running
            return experiment.control

        # 50/50 random assignment
        variant = random.choice([experiment.control, experiment.treatment])

        # Record assignment
        assignment = VariantAssignment(
            case_id=case_id,
            variant_name=variant.name,
            assigned_at=datetime.utcnow()
        )
        experiment.assignments.append(assignment)

        # Store assignment
        await self._store_assignment(experiment_id, assignment)

        return variant

    async def get_active_prompt(
        self,
        agent_id: str,
        case_id: Optional[str] = None
    ) -> str:
        """
        Get the active prompt for an agent, considering experiments.

        If there's an active experiment and a case_id is provided,
        assigns the case to a variant.
        """
        # Check for active experiments
        active_exp = await self._get_active_experiment(agent_id)

        if active_exp and case_id:
            variant = await self.assign_variant(active_exp.id, case_id)
            return variant.prompt

        # Return current active prompt version
        current_version = await self._get_active_version(agent_id)
        if current_version:
            return current_version.prompt

        raise ValueError(f"No active prompt found for agent {agent_id}")

    # =========================================================================
    # Experiment Analysis
    # =========================================================================

    async def analyze_experiment(
        self,
        experiment_id: str
    ) -> Dict[str, Any]:
        """Analyze experiment results and determine if there's a winner."""
        experiment = await self._load_experiment(experiment_id)

        # Get outcomes for all assigned cases
        control_cases = [
            a.case_id for a in experiment.assignments
            if a.variant_name == "control"
        ]
        treatment_cases = [
            a.case_id for a in experiment.assignments
            if a.variant_name == "treatment"
        ]

        # Calculate metrics for each variant
        control_metrics = await self._calculate_variant_metrics(
            control_cases, experiment.success_metric
        )
        treatment_metrics = await self._calculate_variant_metrics(
            treatment_cases, experiment.success_metric
        )

        experiment.control_metrics = control_metrics
        experiment.treatment_metrics = treatment_metrics

        # Check if we have enough samples
        total_samples = control_metrics.sample_size + treatment_metrics.sample_size
        if total_samples >= experiment.required_sample_size:
            # Calculate statistical significance
            p_value = self._calculate_significance(
                control_metrics, treatment_metrics, experiment.success_metric
            )
            experiment.p_value = p_value

            # Determine winner if significant
            if p_value < 0.05:
                winner = self._determine_winner(
                    control_metrics, treatment_metrics, experiment.success_metric
                )
                experiment.winner = winner
                experiment.status = ExperimentStatus.COMPLETED
                experiment.completed_at = datetime.utcnow()

                logger.info(
                    f"Experiment {experiment_id} completed. "
                    f"Winner: {winner}, p-value: {p_value:.4f}"
                )

        await self._store_experiment(experiment)

        return {
            "experiment_id": experiment_id,
            "status": experiment.status.value,
            "control_metrics": control_metrics,
            "treatment_metrics": treatment_metrics,
            "p_value": experiment.p_value,
            "winner": experiment.winner,
            "samples_remaining": max(
                0, experiment.required_sample_size - total_samples
            ),
        }

    async def _calculate_variant_metrics(
        self,
        case_ids: List[str],
        primary_metric: str
    ) -> VariantMetrics:
        """Calculate metrics for a set of cases."""
        if not case_ids:
            return VariantMetrics(
                sample_size=0,
                win_rate=0.0,
                avg_meddic_accuracy=0.0,
                suggestion_acceptance_rate=0.0,
                summary_edit_rate=0.0,
            )

        # Get outcomes for these cases
        outcomes = []
        for case_id in case_ids:
            doc = self.firestore.collection("outcomes").document(case_id).get()
            if doc.exists:
                outcomes.append(doc.to_dict())

        # Get feedback for these cases
        feedback = []
        for case_id in case_ids:
            docs = (
                self.firestore.collection("feedback")
                .where("case_id", "==", case_id)
                .stream()
            )
            feedback.extend([d.to_dict() for d in docs])

        # Calculate metrics
        wins = sum(1 for o in outcomes if o.get("actual_outcome") == "closed_won")
        win_rate = wins / len(outcomes) if outcomes else 0.0

        # MEDDIC accuracy
        meddic_errors = [
            o.get("prediction_error", 0.5) for o in outcomes
        ]
        avg_meddic_accuracy = 1 - (sum(meddic_errors) / len(meddic_errors)) if meddic_errors else 0.5

        # Suggestion acceptance
        suggestion_fb = [f for f in feedback if f.get("feedback_type") == "suggestion_response"]
        accepted = sum(1 for f in suggestion_fb if f.get("response") == "accepted")
        acceptance_rate = accepted / len(suggestion_fb) if suggestion_fb else 0.0

        # Summary edits
        edit_fb = [f for f in feedback if f.get("feedback_type") == "summary_edit"]
        edit_rate = len(edit_fb) / len(case_ids) if case_ids else 0.0

        return VariantMetrics(
            sample_size=len(case_ids),
            win_rate=win_rate,
            avg_meddic_accuracy=avg_meddic_accuracy,
            suggestion_acceptance_rate=acceptance_rate,
            summary_edit_rate=edit_rate,
        )

    def _calculate_significance(
        self,
        control: VariantMetrics,
        treatment: VariantMetrics,
        metric_name: str
    ) -> float:
        """Calculate p-value using two-proportion z-test."""
        # Get the relevant metric values
        if metric_name == "win_rate":
            p1, n1 = control.win_rate, control.sample_size
            p2, n2 = treatment.win_rate, treatment.sample_size
        elif metric_name == "acceptance_rate":
            p1, n1 = control.suggestion_acceptance_rate, control.sample_size
            p2, n2 = treatment.suggestion_acceptance_rate, treatment.sample_size
        else:
            # Default to win_rate
            p1, n1 = control.win_rate, control.sample_size
            p2, n2 = treatment.win_rate, treatment.sample_size

        if n1 == 0 or n2 == 0:
            return 1.0  # Not significant

        # Pooled proportion
        p_pooled = (p1 * n1 + p2 * n2) / (n1 + n2)

        if p_pooled == 0 or p_pooled == 1:
            return 1.0

        # Standard error
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))

        if se == 0:
            return 1.0

        # Z-score
        z = abs(p1 - p2) / se

        # Two-tailed p-value (approximation)
        p_value = 2 * (1 - self._normal_cdf(z))

        return p_value

    def _normal_cdf(self, x: float) -> float:
        """Approximate normal CDF."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _determine_winner(
        self,
        control: VariantMetrics,
        treatment: VariantMetrics,
        metric_name: str
    ) -> str:
        """Determine which variant won."""
        if metric_name == "win_rate":
            return "treatment" if treatment.win_rate > control.win_rate else "control"
        elif metric_name == "acceptance_rate":
            return "treatment" if treatment.suggestion_acceptance_rate > control.suggestion_acceptance_rate else "control"
        elif metric_name == "edit_rate":
            # Lower is better for edit rate
            return "treatment" if treatment.summary_edit_rate < control.summary_edit_rate else "control"
        return "control"

    # =========================================================================
    # Prompt Promotion
    # =========================================================================

    async def promote_winning_prompt(
        self,
        experiment_id: str
    ) -> PromptVersion:
        """Promote the winning prompt to active status."""
        experiment = await self._load_experiment(experiment_id)

        if not experiment.winner:
            raise ValueError(f"Experiment {experiment_id} has no winner yet")

        winning_variant = (
            experiment.treatment if experiment.winner == "treatment"
            else experiment.control
        )

        # Get current version number
        versions = await self._get_all_versions(experiment.agent_id)
        next_version = max([v.version for v in versions], default=0) + 1

        # Create new version
        new_version = PromptVersion(
            agent_id=experiment.agent_id,
            version=next_version,
            prompt=winning_variant.prompt,
            description=f"From experiment {experiment_id}: {winning_variant.description}",
            source="experiment",
            performance_score=self._get_metric_value(
                experiment.treatment_metrics if experiment.winner == "treatment"
                else experiment.control_metrics,
                experiment.success_metric
            ),
            active=True,
        )

        # Deactivate old version
        await self._deactivate_current_version(experiment.agent_id)

        # Store new version
        await self._store_version(new_version)

        logger.info(
            f"Promoted {experiment.winner} prompt to version {next_version} "
            f"for agent {experiment.agent_id}"
        )

        return new_version

    def _get_metric_value(
        self,
        metrics: Optional[VariantMetrics],
        metric_name: str
    ) -> float:
        """Get specific metric value."""
        if not metrics:
            return 0.0
        if metric_name == "win_rate":
            return metrics.win_rate
        if metric_name == "acceptance_rate":
            return metrics.suggestion_acceptance_rate
        return 0.0

    # =========================================================================
    # Auto-Evolution Based on Learning Signals
    # =========================================================================

    async def propose_improvement(
        self,
        agent_id: str,
        learning_signal: LearningSignal
    ) -> Optional[PromptImprovement]:
        """
        Propose a prompt improvement based on a learning signal.

        This is where we translate feedback into concrete prompt changes.
        """
        current_prompt = await self._get_active_version(agent_id)
        if not current_prompt:
            return None

        # Generate improved prompt section based on signal
        improved_section = await self._generate_improvement(
            current_prompt.prompt,
            learning_signal
        )

        if not improved_section:
            return None

        improvement = PromptImprovement(
            improvement_id=f"imp_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            signal_ids=[learning_signal.signal_id],
            original_prompt_section=self._extract_relevant_section(
                current_prompt.prompt, learning_signal
            ),
            improved_prompt_section=improved_section,
            change_rationale=learning_signal.action_recommended,
            status="proposed",
        )

        # Store improvement
        await self._store_improvement(improvement)

        return improvement

    async def _generate_improvement(
        self,
        current_prompt: str,
        signal: LearningSignal
    ) -> Optional[str]:
        """
        Generate improved prompt section based on learning signal.

        In production, this could use an LLM to generate improvements.
        """
        # This is a simplified implementation
        # In production, you'd use an LLM to generate the improvement

        insight = signal.insight.lower()

        if "rejection" in insight or "rejected" in insight:
            return """
When providing suggestions, ensure they are:
- Immediately actionable by the sales rep
- Specific to the current conversation context
- Not dependent on information the rep may not have
- Phrased as options rather than directives
"""

        if "edit" in insight or "summary" in insight:
            return """
When generating summaries:
- Use a professional but conversational tone
- Include specific next steps with dates if mentioned
- Verify customer names and company details
- Keep length appropriate for the conversation depth
"""

        if "score" in insight or "meddic" in insight:
            return """
When calculating MEDDIC scores:
- Weight Economic Buyer identification heavily
- Consider explicit vs implicit signals differently
- Adjust for industry-specific buying patterns
- Include uncertainty ranges for ambiguous situations
"""

        return None

    def _extract_relevant_section(
        self,
        prompt: str,
        signal: LearningSignal
    ) -> str:
        """Extract the section of prompt relevant to the signal."""
        # Simplified - in production, use more sophisticated extraction
        insight = signal.insight.lower()

        if "suggestion" in insight:
            # Find suggestion-related section
            if "suggestion" in prompt.lower():
                start = prompt.lower().find("suggestion")
                return prompt[max(0, start-100):start+500]

        return prompt[:500]  # Default: first 500 chars

    # =========================================================================
    # Storage Methods
    # =========================================================================

    async def _store_experiment(self, experiment: ABExperiment):
        """Store experiment in Firestore."""
        doc_ref = self.firestore.collection("experiments").document(experiment.id)
        await doc_ref.set({
            "id": experiment.id,
            "agent_id": experiment.agent_id,
            "hypothesis": experiment.hypothesis,
            "control_prompt": experiment.control.prompt,
            "control_description": experiment.control.description,
            "treatment_prompt": experiment.treatment.prompt,
            "treatment_description": experiment.treatment.description,
            "success_metric": experiment.success_metric,
            "required_sample_size": experiment.required_sample_size,
            "status": experiment.status.value,
            "winner": experiment.winner,
            "p_value": experiment.p_value,
            "created_at": experiment.created_at,
            "completed_at": experiment.completed_at,
        })

    async def _load_experiment(self, experiment_id: str) -> ABExperiment:
        """Load experiment from Firestore."""
        doc = self.firestore.collection("experiments").document(experiment_id).get()
        if not doc.exists:
            raise ValueError(f"Experiment {experiment_id} not found")

        data = doc.to_dict()

        # Load assignments
        assignments_docs = (
            self.firestore.collection("experiment_assignments")
            .where("experiment_id", "==", experiment_id)
            .stream()
        )
        assignments = [
            VariantAssignment(
                case_id=d.to_dict()["case_id"],
                variant_name=d.to_dict()["variant_name"],
                assigned_at=d.to_dict()["assigned_at"]
            )
            for d in assignments_docs
        ]

        return ABExperiment(
            id=data["id"],
            agent_id=data["agent_id"],
            hypothesis=data["hypothesis"],
            control=PromptVariant(
                name="control",
                prompt=data["control_prompt"],
                description=data.get("control_description", "")
            ),
            treatment=PromptVariant(
                name="treatment",
                prompt=data["treatment_prompt"],
                description=data.get("treatment_description", "")
            ),
            success_metric=data["success_metric"],
            required_sample_size=data["required_sample_size"],
            status=ExperimentStatus(data["status"]),
            assignments=assignments,
            winner=data.get("winner"),
            p_value=data.get("p_value"),
            created_at=data["created_at"],
            completed_at=data.get("completed_at"),
        )

    async def _store_assignment(
        self,
        experiment_id: str,
        assignment: VariantAssignment
    ):
        """Store variant assignment."""
        doc_id = f"{experiment_id}_{assignment.case_id}"
        await self.firestore.collection("experiment_assignments").document(doc_id).set({
            "experiment_id": experiment_id,
            "case_id": assignment.case_id,
            "variant_name": assignment.variant_name,
            "assigned_at": assignment.assigned_at,
        })

    async def _get_active_experiment(
        self,
        agent_id: str
    ) -> Optional[ABExperiment]:
        """Get active experiment for an agent."""
        docs = (
            self.firestore.collection("experiments")
            .where("agent_id", "==", agent_id)
            .where("status", "==", ExperimentStatus.RUNNING.value)
            .limit(1)
            .stream()
        )

        for doc in docs:
            return await self._load_experiment(doc.id)

        return None

    async def _get_active_version(
        self,
        agent_id: str
    ) -> Optional[PromptVersion]:
        """Get active prompt version for an agent."""
        docs = (
            self.firestore.collection("prompt_versions")
            .where("agent_id", "==", agent_id)
            .where("active", "==", True)
            .limit(1)
            .stream()
        )

        for doc in docs:
            data = doc.to_dict()
            return PromptVersion(
                agent_id=data["agent_id"],
                version=data["version"],
                prompt=data["prompt"],
                description=data["description"],
                source=data["source"],
                performance_score=data.get("performance_score"),
                active=True,
            )

        return None

    async def _get_all_versions(
        self,
        agent_id: str
    ) -> List[PromptVersion]:
        """Get all versions for an agent."""
        docs = (
            self.firestore.collection("prompt_versions")
            .where("agent_id", "==", agent_id)
            .stream()
        )

        versions = []
        for doc in docs:
            data = doc.to_dict()
            versions.append(PromptVersion(
                agent_id=data["agent_id"],
                version=data["version"],
                prompt=data["prompt"],
                description=data["description"],
                source=data["source"],
                performance_score=data.get("performance_score"),
                active=data.get("active", False),
            ))

        return versions

    async def _deactivate_current_version(self, agent_id: str):
        """Deactivate current active version."""
        docs = (
            self.firestore.collection("prompt_versions")
            .where("agent_id", "==", agent_id)
            .where("active", "==", True)
            .stream()
        )

        for doc in docs:
            await doc.reference.update({"active": False})

    async def _store_version(self, version: PromptVersion):
        """Store prompt version."""
        doc_id = f"{version.agent_id}_v{version.version}"
        await self.firestore.collection("prompt_versions").document(doc_id).set({
            "agent_id": version.agent_id,
            "version": version.version,
            "prompt": version.prompt,
            "description": version.description,
            "source": version.source,
            "performance_score": version.performance_score,
            "active": version.active,
            "created_at": version.created_at,
        })

    async def _store_improvement(self, improvement: PromptImprovement):
        """Store prompt improvement."""
        await self.firestore.collection("prompt_improvements").document(
            improvement.improvement_id
        ).set(improvement.model_dump())
