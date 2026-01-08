"""
Workflow Loader for parsing workflow definitions from YAML/Markdown.

Supports loading workflows from:
- YAML files
- Markdown files with YAML frontmatter
- Python dictionaries
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

import yaml

from .schema import (
    Workflow,
    WorkflowMetadata,
    WorkflowPhase,
    WorkflowStep,
    WorkflowTrigger,
    ExecutionMode,
    Condition,
    ConditionOperator,
    RetryConfig,
    QualityCheck,
    StepInput,
    StepOutput,
)

logger = logging.getLogger(__name__)


class WorkflowLoadError(Exception):
    """Raised when workflow loading fails."""
    pass


class WorkflowLoader:
    """
    Loads workflow definitions from various sources.

    Supports YAML files, Markdown with YAML frontmatter, and dicts.
    """

    def load_file(self, path: str | Path) -> Workflow:
        """
        Load a workflow from a file.

        Automatically detects format based on extension.
        """
        path = Path(path)
        if not path.exists():
            raise WorkflowLoadError(f"Workflow file not found: {path}")

        content = path.read_text(encoding="utf-8")

        if path.suffix in (".yaml", ".yml"):
            return self.load_yaml(content)
        elif path.suffix == ".md":
            return self.load_markdown(content)
        else:
            raise WorkflowLoadError(f"Unsupported file format: {path.suffix}")

    def load_yaml(self, content: str) -> Workflow:
        """Load a workflow from YAML content."""
        try:
            data = yaml.safe_load(content)
            return self.load_dict(data)
        except yaml.YAMLError as e:
            raise WorkflowLoadError(f"Invalid YAML: {e}") from e

    def load_markdown(self, content: str) -> Workflow:
        """
        Load a workflow from Markdown with YAML frontmatter.

        Expected format:
        ```
        ---
        id: my-workflow
        name: My Workflow
        ...
        ---

        # My Workflow

        Description in markdown...
        ```
        """
        # Extract YAML frontmatter
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not match:
            raise WorkflowLoadError("No YAML frontmatter found in Markdown file")

        yaml_content = match.group(1)
        markdown_body = content[match.end():]

        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise WorkflowLoadError(f"Invalid YAML frontmatter: {e}") from e

        # Add markdown body as description if not set
        if not data.get("description") and markdown_body.strip():
            # Extract first paragraph as description
            first_para = markdown_body.strip().split("\n\n")[0]
            # Remove markdown headers
            first_para = re.sub(r"^#+\s+", "", first_para)
            data["description"] = first_para.strip()

        return self.load_dict(data)

    def load_dict(self, data: dict[str, Any]) -> Workflow:
        """Load a workflow from a dictionary."""
        if not isinstance(data, dict):
            raise WorkflowLoadError("Workflow data must be a dictionary")

        # Parse metadata
        metadata = self._parse_metadata(data)

        # Parse triggers
        triggers = [
            self._parse_trigger(t)
            for t in data.get("triggers", [])
        ]

        # Parse phases
        phases = [
            self._parse_phase(p)
            for p in data.get("phases", [])
        ]

        # Parse global retry config
        retry = None
        if "retry" in data:
            retry = self._parse_retry(data["retry"])

        return Workflow(
            metadata=metadata,
            triggers=triggers,
            phases=phases,
            initial_state=data.get("initial_state", {}),
            timeout_seconds=data.get("timeout_seconds", 600.0),
            retry=retry,
        )

    def _parse_metadata(self, data: dict[str, Any]) -> WorkflowMetadata:
        """Parse workflow metadata."""
        # Support both nested and flat structure
        meta = data.get("metadata", data)

        if "id" not in meta:
            raise WorkflowLoadError("Workflow must have an 'id' field")
        if "name" not in meta:
            raise WorkflowLoadError("Workflow must have a 'name' field")

        return WorkflowMetadata(
            id=meta["id"],
            name=meta["name"],
            version=meta.get("version", "1.0.0"),
            description=meta.get("description"),
            author=meta.get("author"),
            tags=meta.get("tags", []),
        )

    def _parse_trigger(self, data: dict[str, Any]) -> WorkflowTrigger:
        """Parse a workflow trigger."""
        conditions = [
            self._parse_condition(c)
            for c in data.get("conditions", [])
        ]
        return WorkflowTrigger(
            event=data["event"],
            conditions=conditions,
        )

    def _parse_phase(self, data: dict[str, Any]) -> WorkflowPhase:
        """Parse a workflow phase."""
        mode = ExecutionMode(data.get("mode", "sequential"))
        steps = [
            self._parse_step(s)
            for s in data.get("steps", [])
        ]
        return WorkflowPhase(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            mode=mode,
            steps=steps,
        )

    def _parse_step(self, data: dict[str, Any]) -> WorkflowStep:
        """Parse a workflow step."""
        # Parse inputs
        inputs = []
        for inp in data.get("inputs", []):
            if isinstance(inp, str):
                # Simple format: "state.field -> param_name"
                parts = inp.split("->")
                if len(parts) == 2:
                    inputs.append(StepInput(
                        from_state=parts[0].strip(),
                        to_param=parts[1].strip(),
                    ))
            else:
                inputs.append(StepInput(
                    from_state=inp["from_state"],
                    to_param=inp["to_param"],
                    required=inp.get("required", True),
                    default=inp.get("default"),
                ))

        # Parse outputs
        outputs = []
        for out in data.get("outputs", []):
            if isinstance(out, str):
                # Simple format: "result.field -> state.field"
                parts = out.split("->")
                if len(parts) == 2:
                    outputs.append(StepOutput(
                        from_result=parts[0].strip(),
                        to_state=parts[1].strip(),
                    ))
            else:
                outputs.append(StepOutput(
                    from_result=out["from_result"],
                    to_state=out["to_state"],
                ))

        # Parse condition
        condition = None
        if "condition" in data:
            condition = self._parse_condition(data["condition"])

        # Parse retry
        retry = None
        if "retry" in data:
            retry = self._parse_retry(data["retry"])

        # Parse quality check
        quality_check = None
        if "quality_check" in data:
            qc = data["quality_check"]
            quality_check = QualityCheck(
                enabled=qc.get("enabled", True),
                max_refinements=qc.get("max_refinements", 2),
                rules=qc.get("rules", []),
            )

        return WorkflowStep(
            id=data["id"],
            skill=data["skill"],
            name=data.get("name"),
            description=data.get("description"),
            inputs=inputs,
            outputs=outputs,
            condition=condition,
            retry=retry,
            timeout_seconds=data.get("timeout_seconds", 120.0),
            quality_check=quality_check,
            depends_on=data.get("depends_on", []),
        )

    def _parse_condition(self, data: dict[str, Any]) -> Condition:
        """Parse a condition."""
        operator = ConditionOperator(data.get("operator", "equals"))
        return Condition(
            field=data["field"],
            operator=operator,
            value=data.get("value"),
        )

    def _parse_retry(self, data: dict[str, Any]) -> RetryConfig:
        """Parse retry configuration."""
        return RetryConfig(
            max_attempts=data.get("max_attempts", 3),
            backoff_seconds=data.get("backoff_seconds", 1.0),
            backoff_multiplier=data.get("backoff_multiplier", 2.0),
            retryable_errors=data.get("retryable_errors", [
                "timeout", "rate_limit", "503", "429"
            ]),
        )


# Convenience function for loading workflows
def load_workflow(source: str | Path | dict) -> Workflow:
    """
    Load a workflow from various sources.

    Args:
        source: File path, YAML string, or dictionary

    Returns:
        Parsed Workflow object
    """
    loader = WorkflowLoader()

    if isinstance(source, dict):
        return loader.load_dict(source)
    elif isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        return loader.load_file(source)
    elif isinstance(source, str):
        # Try to parse as YAML
        return loader.load_yaml(source)
    else:
        raise WorkflowLoadError(f"Cannot load workflow from: {type(source)}")
