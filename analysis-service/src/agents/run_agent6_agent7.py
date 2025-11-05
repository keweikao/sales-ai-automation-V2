#!/usr/bin/env python3
"""
Utility script for executing Agent 6 (Sales Coach Synthesizer) and Agent 7 (Customer Summary)
using the current prompt drafts and sample outputs from Agents 1–5.

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
        --output-dir ./tmp/agent67_mock

Available scenarios: positive | negative | insufficient

The script loads the transcript, merges Agent 1–5 outputs, runs Agent 6 then Agent 7,
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


def build_agent6_prompt(
    prompt_template: str,
    transcript: str,
    inputs: Dict[str, Any],
) -> str:
    context = {
        "caseId": inputs.get("caseId"),
        "customer": inputs.get("customer", {}),
        "agents": {
            key: value
            for key, value in inputs.get("agentOutputs", {}).items()
            if key.startswith("agent")
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute Agent 6 and Agent 7 prompts.")
    parser.add_argument(
        "--inputs",
        type=Path,
        default=Path("analysis-service/tests/samples/sample_agent_inputs.json"),
        help="Path to JSON file containing transcript reference and Agent 1–5 outputs.",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash-exp",
        help="Gemini model name (default: gemini-2.0-flash-exp).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Sampling temperature for Gemini (default: 0.3).",
    )
    parser.add_argument(
        "--mock-scenario",
        choices=sorted(MOCK_SCENARIOS.keys()),
        default=None,
        help="Use predefined mock responses instead of calling Gemini.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional directory to write agent outputs.",
    )

    args = parser.parse_args()

    inputs_path = args.inputs if args.inputs.is_absolute() else (REPO_ROOT / args.inputs)
    if not inputs_path.exists():
        raise SystemExit(f"Input file not found: {inputs_path}")

    inputs = load_json(inputs_path)

    transcript_path = inputs.get("transcriptPath")
    if not transcript_path:
        raise SystemExit("`transcriptPath` missing from inputs JSON.")

    transcript_file = (
        Path(transcript_path)
        if Path(transcript_path).is_absolute()
        else (REPO_ROOT / transcript_path)
    )

    if not transcript_file.exists():
        raise SystemExit(f"Transcript file not found: {transcript_file}")

    transcript_text = load_file(transcript_file)

    agent6_prompt = load_file(PROMPT_DIR / "agent6-coach.md")
    agent7_prompt = load_file(PROMPT_DIR / "agent7-summary.md")

    use_mock = args.mock_scenario is not None
    if not use_mock:
        model = configure_model(args.model, args.temperature)
    else:
        mock_paths = MOCK_SCENARIOS[args.mock_scenario]
        if not mock_paths["agent6"].exists() or not mock_paths["agent7"].exists():
            raise SystemExit(f"Mock fixtures missing for scenario '{args.mock_scenario}'")

    # ----- Agent 6 -----
    if use_mock:
        mock_payload = load_json(mock_paths["agent6"])
        agent6_raw = json.dumps(mock_payload, ensure_ascii=False, indent=2)
        agent6_structured = mock_payload.get("structured", {})
        agent6_duration = 0.0
        print("[Mock Mode] Loaded Agent 6 fixture:", mock_paths["agent6"])
    else:
        combined_agent6_prompt = build_agent6_prompt(agent6_prompt, transcript_text, inputs)
        agent6_raw, agent6_duration = run_model(model, combined_agent6_prompt)

        try:
            agent6_structured = extract_json(agent6_raw)
        except (ValueError, json.JSONDecodeError) as exc:
            print("\n[Agent 6] Failed to parse JSON response. Raw output preserved.", file=sys.stderr)
            print(str(exc), file=sys.stderr)
            agent6_structured = {}

    print("=== Agent 6: Sales Coach Synthesizer ===")
    print(f"Duration: {agent6_duration:.2f}s")
    print(json.dumps(agent6_structured, ensure_ascii=False, indent=2))

    # ----- Agent 7 -----
    if use_mock:
        mock_payload = load_json(mock_paths["agent7"])
        agent7_raw = json.dumps(mock_payload, ensure_ascii=False, indent=2)
        agent7_structured = mock_payload.get("customerSummary", {})
        agent7_duration = 0.0
        print("[Mock Mode] Loaded Agent 7 fixture:", mock_paths["agent7"])
    else:
        combined_agent7_prompt = build_agent7_prompt(
            agent7_prompt,
            transcript_text,
            inputs,
            agent6_structured,
        )
        agent7_raw, agent7_duration = run_model(model, combined_agent7_prompt)

        try:
            agent7_structured = extract_json(agent7_raw)
        except (ValueError, json.JSONDecodeError) as exc:
            print("\n[Agent 7] Failed to parse JSON response. Raw output preserved.", file=sys.stderr)
            print(str(exc), file=sys.stderr)
            agent7_structured = {}

    print("\n=== Agent 7: Customer Summary ===")
    print(f"Duration: {agent7_duration:.2f}s")
    print(json.dumps(agent7_structured, ensure_ascii=False, indent=2))

    if args.output_dir:
        output_dir = (
            args.output_dir
            if args.output_dir.is_absolute()
            else (REPO_ROOT / args.output_dir)
        )
        save_output(output_dir, "agent6_raw.txt", agent6_raw)
        save_output(output_dir, "agent6_structured.json", agent6_structured)
        save_output(output_dir, "agent7_raw.txt", agent7_raw)
        save_output(output_dir, "agent7_structured.json", agent7_structured)
        print(f"\nOutputs saved to {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
