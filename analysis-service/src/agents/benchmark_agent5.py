#!/usr/bin/env python3
"""
Utility script for benchmarking Agent 5 (Questionnaire Agent) locally.

Requirements
------------
- python >= 3.9
- google-generativeai >= 0.6.0
- GEMINI_API_KEY environment variable
  (⬆️ Not required if you run with --mock-scenario, which loads local fixtures.)

Usage
-----
    export GEMINI_API_KEY="your-key"
    python analysis-service/src/agents/benchmark_agent5.py \
        --inputs analysis-service/tests/samples/sample_agent_inputs.json \
        --transcript analysis-service/tests/samples/sample_transcript.txt \
        --output-dir ./tmp/agent5_benchmark

Mock Mode
---------
    python analysis-service/src/agents/benchmark_agent5.py --mock-scenario positive \
        --output-dir ./tmp/agent5_mock

Available scenarios: positive | negative | insufficient

The script loads the transcript and other agent outputs, runs Agent 5,
prints the structured results, and optionally writes them to disk for review.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import google.generativeai as genai
except ImportError as exc:  # pragma: no cover - convenience guard for local runs
    raise SystemExit(
        "Missing dependency: google-generativeai. "
        "Install with `pip install google-generativeai`."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:  # pragma: no cover - CLI helper path setup
    sys.path.insert(0, str(MODULE_ROOT))

from agents.agent5_questionnaire import QuestionnaireAgent  # pylint: disable=wrong-import-position

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
MOCK_FIXTURE_DIR = REPO_ROOT / "analysis-service" / "tests" / "fixtures" / "agent5"

MOCK_SCENARIOS = {
    "positive": {
        "agent5": MOCK_FIXTURE_DIR / "agent5_structured.json",
    },
    "negative": {
        "agent5": MOCK_FIXTURE_DIR / "agent5_structured_negative.json",
    },
    "insufficient": {
        "agent5": MOCK_FIXTURE_DIR / "agent5_structured_insufficient.json",
    },
}


def load_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_output(directory: Path, filename: str, content: Any) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / filename).open("w", encoding="utf-8") as fh:
        if isinstance(content, str):
            fh.write(content)
        else:
            json.dump(content, fh, ensure_ascii=False, indent=2)


def execute_agent5(
    inputs: Dict[str, Any],
    transcript: str,
    output_dir: Path,
    mock_agent5: Optional[Dict[str, Any]],
    model_name: str,
    temperature: float,
) -> Tuple[Dict[str, Any], float]:
    if mock_agent5 is not None:
        agent5_structured = mock_agent5
        duration = 0.0
    else:
        agent = QuestionnaireAgent(model_name=model_name, temperature=temperature)
        start = time.time()
        agent5_structured = agent.analyze(
            transcript_segments=inputs.get("transcript_segments", []),
            participant_insights=inputs.get("agentOutputs", {}).get("agent1_participant"),
            sentiment_insights=inputs.get("agentOutputs", {}).get("agent2_sentiment"),
            product_needs=inputs.get("agentOutputs", {}).get("agent3_product_needs"),
            questionnaire=inputs.get("questionnaire"),
            conversation_metadata=inputs.get("conversationMetadata"),
        )
        duration = time.time() - start

    save_output(output_dir, "agent5_structured.json", agent5_structured)

    print("\n=== Agent 5 (Questionnaire) ===")
    print(f"- Duration: {duration:.2f}s")
    print(json.dumps(agent5_structured, ensure_ascii=False, indent=2))

    return agent5_structured, duration


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Agent 5 locally for benchmarking.")
    parser.add_argument(
        "--inputs",
        type=Path,
        required=False,
        default=REPO_ROOT / "analysis-service" / "tests" / "samples" / "sample_agent_inputs.json",
        help="Path to JSON file containing transcript + Agent1-5 outputs.",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        required=False,
        default=REPO_ROOT / "analysis-service" / "tests" / "samples" / "sample_transcript.txt",
        help="Path to raw transcript file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./tmp/agent5_benchmark"),
        help="Directory to write outputs.",
    )
    parser.add_argument(
        "--mock-scenario",
        choices=list(MOCK_SCENARIOS.keys()),
        help="Use bundled fixtures instead of real Gemini calls.",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-pro",
        help="Gemini model name.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Generation temperature.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    inputs = load_json(args.inputs)
    transcript = load_file(args.transcript)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    mock_agent5 = None
    if args.mock_scenario:
        scenario = MOCK_SCENARIOS[args.mock_scenario]
        mock_agent5 = load_json(scenario["agent5"])

    execute_agent5(
        inputs=inputs,
        transcript=transcript,
        output_dir=output_dir,
        mock_agent5=mock_agent5,
        model_name=args.model,
        temperature=args.temperature,
    )


if __name__ == "__main__":
    main()
