#!/usr/bin/env python3
"""
Utility script for executing Agent 6 (Sales Coach Synthesizer) and Agent 7 (Customer Summary)
using the current prompt drafts and sample outputs from Agents 1–5.

New in this version:
- `--agents {both,6,7}` lets you run each agent independently.
- When running Agent 7 only, provide `--agent6-structured-input` or use `--mock-scenario`.

Requirements
------------
- python >= 3.9
- google-generativeai >= 0.6.0
- GEMINI_API_KEY environment variable
  (⬆️ Not required if you run with `--mock-scenario`, which loads local fixtures.)

Usage
-----
    export GEMINI_API_KEY="your-key"
    python analysis-service/src/agents/run_agent6_agent7.py \
        --inputs analysis-service/tests/samples/sample_agent_inputs.json \
        --output-dir ./tmp/agent67

Mock Mode
---------
    python analysis-service/src/agents/run_agent6_agent7.py --mock-scenario positive \
        --agents both --output-dir ./tmp/agent67_mock

Available scenarios: positive | negative | insufficient

The script loads the transcript, merges Agent 1–5 outputs, runs Agent 6 and/or Agent 7,
prints the structured results, and optionally writes them to disk for review.
"""

from __future__ import annotations

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

from agents.agent6_sales_coach import SalesCoachAgent  # pylint: disable=wrong-import-position

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
MOCK_FIXTURE_DIR = REPO_ROOT / "analysis-service" / "tests" / "fixtures" / "agent67"

MOCK_SCENARIOS = {
    "positive": {
        "agent6": MOCK_FIXTURE_DIR / "agent6_structured.json",
        "agent7": MOCK_FIXTURE_DIR / "agent7_summary.json",
    },
    "negative": {
        "agent6": MOCK_FIXTURE_DIR / "agent6_structured_negative.json",
        "agent7": MOCK_FIXTURE_DIR / "agent7_summary_negative.json",
    },
    "insufficient": {
        "agent6": MOCK_FIXTURE_DIR / "agent6_structured_insufficient.json",
        "agent7": MOCK_FIXTURE_DIR / "agent7_summary_insufficient.json",
    },
}


def load_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def extract_json(payload: str) -> Dict[str, Any]:
    """
    Attempt to parse the first JSON object contained in `payload`.
    Handles cases where Gemini wraps the response in code fences or commentary.
    """
    start = payload.find("{")
    end = payload.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object detected in model response.")
    snippet = payload[start : end + 1]
    return json.loads(snippet)


def configure_model(model_name: str, temperature: float) -> genai.GenerativeModel:
    try:
        api_key = os.environ["GEMINI_API_KEY"]
    except KeyError as exc:
        raise SystemExit("GEMINI_API_KEY environment variable is required.") from exc

    genai.configure(api_key=api_key)
    generation_config = genai.types.GenerationConfig(
        temperature=temperature,
        candidate_count=1,
        response_mime_type="text/plain",
    )
    return genai.GenerativeModel(model_name, generation_config=generation_config)


def build_agent7_prompt(
    prompt_template: str,
    transcript: str,
    inputs: Dict[str, Any],
    agent6_structured: Dict[str, Any],
) -> str:
    context = {
        "caseId": inputs.get("caseId"),
        "customer": inputs.get("customer", {}),
        "agentOutputs": {
            **inputs.get("agentOutputs", {}),
            "agent6_sales_coach": agent6_structured,
        },
    }
    serialized_context = json.dumps(context, ensure_ascii=False, indent=2)

    return (
        f"{prompt_template}\n\n"
        "=== Case Context (JSON) ===\n"
        f"{serialized_context}\n\n"
        "=== Transcript (Raw) ===\n"
        f"{transcript.strip()}\n"
    )


def run_model(
    model: genai.GenerativeModel,
    prompt: str,
) -> Tuple[str, float]:
    start = time.time()
    response = model.generate_content(prompt)
    duration = time.time() - start

    if hasattr(response, "text") and response.text:
        text_output = response.text
    else:
        # Fallback: concatenate candidate parts if `.text` missing
        text_fragments = []
        candidates = getattr(response, "candidates", []) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            parts = getattr(content, "parts", None)
            if parts:
                for part in parts:
                    text_value = getattr(part, "text", None)
                    if text_value:
                        text_fragments.append(text_value)
            else:
                text_value = getattr(content, "text", None)
                if text_value:
                    text_fragments.append(text_value)

        text_output = "\n".join(text_fragments).strip()

    if not text_output:
        text_output = str(response)

    return text_output.strip(), duration


def save_output(directory: Path, filename: str, content: Any) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / filename).open("w", encoding="utf-8") as fh:
        if isinstance(content, str):
            fh.write(content)
        else:
            json.dump(content, fh, ensure_ascii=False, indent=2)


def execute_agent6(
    inputs: Dict[str, Any],
    transcript: str,
    output_dir: Path,
    mock_agent6: Optional[Dict[str, Any]],
    model_name: str,
    temperature: float,
) -> Tuple[Dict[str, Any], str, float]:
    if mock_agent6 is not None:
        agent6_structured = mock_agent6
        raw_output = json.dumps(agent6_structured, ensure_ascii=False, indent=2)
        duration = 0.0
    else:
        agent = SalesCoachAgent(model_name=model_name, temperature=temperature)
        case_metadata = {
            "caseId": inputs.get("caseId"),
            "customer": inputs.get("customer", {}),
        }
        start = time.time()
        agent_response = agent.invoke(
            agent_outputs=inputs.get("agentOutputs", {}),
            transcript_text=transcript,
            case_metadata=case_metadata,
            conversation_metadata=inputs.get("conversationMetadata"),
        )
        agent6_structured = agent_response.data
        raw_output = agent_response.raw_text
        duration = time.time() - start

    save_output(output_dir, "agent6_raw.txt", raw_output)
    save_output(output_dir, "agent6_structured.json", agent6_structured)

    print("\n=== Agent 6 (Sales Coach) ===")
    print(f"- Duration: {duration:.2f}s")
    print(json.dumps(agent6_structured, ensure_ascii=False, indent=2))

    return agent6_structured, raw_output, duration


def execute_agent7(
    inputs: Dict[str, Any],
    transcript: str,
    prompt_template: str,
    output_dir: Path,
    mock_agent7: Optional[Dict[str, Any]],
    model_name: str,
    temperature: float,
    agent6_structured: Dict[str, Any],
) -> Tuple[Dict[str, Any], str, float]:
    if mock_agent7 is not None:
        agent7_summary = mock_agent7
        raw_output = json.dumps(agent7_summary, ensure_ascii=False, indent=2)
        duration = 0.0
    else:
        model = configure_model(model_name, temperature)
        prompt7 = build_agent7_prompt(prompt_template, transcript, inputs, agent6_structured)
        raw_output, duration = run_model(model, prompt7)
        agent7_summary = extract_json(raw_output)

    save_output(output_dir, "agent7_raw.txt", raw_output)
    save_output(output_dir, "agent7_summary.json", agent7_summary)

    print("\n=== Agent 7 (Customer Summary) ===")
    print(f"- Duration: {duration:.2f}s")
    print(json.dumps(agent7_summary, ensure_ascii=False, indent=2))

    return agent7_summary, raw_output, duration


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Agent 6 and/or Agent 7 locally.")
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
        default=Path("./tmp/agent67"),
        help="Directory to write outputs.",
    )
    parser.add_argument(
        "--mock-scenario",
        choices=list(MOCK_SCENARIOS.keys()),
        help="Use bundled fixtures instead of real Gemini calls.",
    )
    parser.add_argument(
        "--agents",
        choices=["both", "6", "7"],
        default="both",
        help="Choose which agent(s) to run.",
    )
    parser.add_argument(
        "--agent6-structured-input",
        type=Path,
        help="Path to existing Agent 6 structured JSON (required when running only Agent 7 without mock).",
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

    run_agent6_flag = args.agents in ("both", "6")
    run_agent7_flag = args.agents in ("both", "7")

    if not (run_agent6_flag or run_agent7_flag):
        raise SystemExit("At least one agent must be selected.")

    inputs = load_json(args.inputs)
    transcript = load_file(args.transcript)
    prompt_agent7 = load_file(PROMPT_DIR / "agent7-summary.md")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    mock_agent6 = None
    mock_agent7 = None
    if args.mock_scenario:
        scenario = MOCK_SCENARIOS[args.mock_scenario]
        mock_agent6 = load_json(scenario["agent6"])
        mock_agent7 = load_json(scenario["agent7"])

    agent6_structured: Optional[Dict[str, Any]] = None

    if run_agent6_flag:
        agent6_structured, _, _ = execute_agent6(
            inputs=inputs,
            transcript=transcript,
            output_dir=output_dir,
            mock_agent6=mock_agent6,
            model_name=args.model,
            temperature=args.temperature,
        )
    elif run_agent7_flag:
        if mock_agent6 is not None:
            agent6_structured = mock_agent6
        elif args.agent6_structured_input:
            agent6_structured = load_json(args.agent6_structured_input)
        else:
            raise SystemExit(
                "Running only Agent 7 requires either --mock-scenario "
                "or --agent6-structured-input pointing to an existing JSON file."
            )

    if run_agent7_flag:
        assert agent6_structured is not None
        execute_agent7(
            inputs=inputs,
            transcript=transcript,
            prompt_template=prompt_agent7,
            output_dir=output_dir,
            mock_agent7=mock_agent7,
            model_name=args.model,
            temperature=args.temperature,
            agent6_structured=agent6_structured,
        )


if __name__ == "__main__":
    main()
