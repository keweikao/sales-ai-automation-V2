#!/usr/bin/env python3
"""
POC 2: Multi-Agent Parallel Orchestration

Tests if 5 Gemini agents can execute in parallel within 40 seconds.

Usage:
    export GEMINI_API_KEY="your-key"
    python test_parallel.py --transcript test_transcript.txt
"""

import argparse
import asyncio
import time
import json
from pathlib import Path
from typing import Dict, List
import os

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai not installed. Run: pip install google-generativeai")
    exit(1)


class AgentOrchestrator:
    """Orchestrates multiple Gemini agents in parallel"""

    def __init__(self, api_key: str, model_name="gemini-2.0-flash-exp"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name

    async def run_agent(self, agent_id: str, prompt: str, transcript: str) -> Dict:
        """Run a single agent asynchronously"""
        start_time = time.time()

        try:
            full_prompt = f"{prompt}\n\nTranscript:\n{transcript}"

            response = await self.model.generate_content_async(full_prompt)

            duration = time.time() - start_time

            return {
                "agent_id": agent_id,
                "success": True,
                "duration": duration,
                "output": response.text,
                "tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0,
                "error": None
            }

        except Exception as e:
            duration = time.time() - start_time
            return {
                "agent_id": agent_id,
                "success": False,
                "duration": duration,
                "output": None,
                "tokens": 0,
                "error": str(e)
            }

    async def run_agents_parallel(self, transcript: str, agent_configs: Dict) -> Dict:
        """Run all agents in parallel"""
        print(f"Running {len(agent_configs)} agents in parallel...")

        start_time = time.time()

        # Create tasks for all agents
        tasks = [
            self.run_agent(agent_id, config["prompt"], transcript)
            for agent_id, config in agent_configs.items()
        ]

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_duration = time.time() - start_time

        # Process results
        agent_results = {}
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Exception: {result}")
                continue

            agent_id = result["agent_id"]
            agent_results[agent_id] = result

            status = "✅" if result["success"] else "❌"
            print(f"{status} {agent_id}: {result['duration']:.2f}s, {result['tokens']} tokens")

        return {
            "parallel_duration": total_duration,
            "agent_results": agent_results,
            "total_agents": len(agent_configs),
            "successful_agents": sum(1 for r in agent_results.values() if r["success"]),
            "failed_agents": sum(1 for r in agent_results.values() if not r["success"]),
            "max_agent_time": max((r["duration"] for r in agent_results.values()), default=0),
            "total_tokens": sum(r["tokens"] for r in agent_results.values())
        }

    async def run_sequential(self, transcript: str, agent_configs: Dict) -> Dict:
        """Run all agents sequentially (for comparison)"""
        print(f"Running {len(agent_configs)} agents sequentially...")

        start_time = time.time()
        agent_results = {}

        for agent_id, config in agent_configs.items():
            result = await self.run_agent(agent_id, config["prompt"], transcript)
            agent_results[agent_id] = result

            status = "✅" if result["success"] else "❌"
            print(f"{status} {agent_id}: {result['duration']:.2f}s")

        total_duration = time.time() - start_time

        return {
            "sequential_duration": total_duration,
            "agent_results": agent_results,
            "total_agents": len(agent_configs),
            "successful_agents": sum(1 for r in agent_results.values() if r["success"]),
            "total_tokens": sum(r["tokens"] for r in agent_results.values())
        }


def create_mock_agent_configs() -> Dict:
    """Create mock agent configurations for testing"""
    return {
        "agent1_participant": {
            "prompt": """You are a participant analyzer. Analyze the conversation and identify each speaker's role, personality, and concerns.
Return a brief JSON summary with: speakerId, role, personalityType, decisionPower (0-100).
Keep response under 500 tokens.""",
            "expected_time": 30
        },
        "agent2_sentiment": {
            "prompt": """You are a sentiment analyzer. Analyze the emotional tone of the conversation.
Return a brief JSON summary with: overallSentiment, trustLevel (0-100), buyingSignals[], objections[].
Keep response under 400 tokens.""",
            "expected_time": 20
        },
        "agent3_needs": {
            "prompt": """You are a product needs extractor. Identify customer needs and recommend products.
Return a brief JSON summary with: explicitNeeds[], implicitNeeds[], recommendedProducts[].
Keep response under 600 tokens.""",
            "expected_time": 25
        },
        "agent4_competitor": {
            "prompt": """You are a competitor intelligence analyzer. Identify competitors mentioned and customer opinions.
Return a brief JSON summary with: competitors[], customerOpinions{}, competitiveAdvantages[].
Keep response under 300 tokens.""",
            "expected_time": 20
        },
        "agent5_questionnaire": {
            "prompt": """You are a discovery questionnaire analyzer. Extract structured questionnaire responses.
Return a brief JSON summary with: discoveredFeatures[], currentStatus, implementationWillingness.
Keep response under 500 tokens.""",
            "expected_time": 25
        }
    }


async def test_parallel_vs_sequential(transcript_path: str, api_key: str):
    """Compare parallel vs sequential execution"""

    # Load transcript
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = f.read()

    print(f"Transcript length: {len(transcript)} characters\n")

    # Create orchestrator
    orchestrator = AgentOrchestrator(api_key)
    agent_configs = create_mock_agent_configs()

    # Test 1: Sequential execution
    print(f"{'='*60}")
    print("TEST 1: SEQUENTIAL EXECUTION")
    print(f"{'='*60}\n")

    seq_result = await orchestrator.run_sequential(transcript, agent_configs)
    print(f"\nSequential Total Time: {seq_result['sequential_duration']:.2f}s")

    # Test 2: Parallel execution
    print(f"\n{'='*60}")
    print("TEST 2: PARALLEL EXECUTION")
    print(f"{'='*60}\n")

    par_result = await orchestrator.run_agents_parallel(transcript, agent_configs)
    print(f"\nParallel Total Time: {par_result['parallel_duration']:.2f}s")

    # Compare results
    print(f"\n{'='*60}")
    print("COMPARISON")
    print(f"{'='*60}")

    speedup = seq_result['sequential_duration'] / par_result['parallel_duration']
    print(f"Sequential: {seq_result['sequential_duration']:.2f}s")
    print(f"Parallel: {par_result['parallel_duration']:.2f}s")
    print(f"Speedup: {speedup:.2f}x")
    print(f"Max Single Agent Time: {par_result['max_agent_time']:.2f}s")

    # Success criteria check
    success = (
        par_result['parallel_duration'] <= 40 and      # <40s target
        par_result['failed_agents'] == 0 and           # No failures
        par_result['parallel_duration'] <= par_result['max_agent_time'] * 1.5  # Reasonable parallelization
    )

    print(f"\nSuccess Rate: {par_result['successful_agents']}/{par_result['total_agents']}")
    print(f"Error Rate: {par_result['failed_agents']}/{par_result['total_agents']} ({par_result['failed_agents']/par_result['total_agents']*100:.1f}%)")

    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\nPOC 2 Result: {status}")
    print(f"{'='*60}\n")

    # Save results
    results = {
        "sequential": seq_result,
        "parallel": par_result,
        "speedup": speedup,
        "success": success
    }

    with open("poc2_results.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("Detailed results saved to: poc2_results.json")

    return results


async def load_test(transcript_path: str, api_key: str, concurrent_cases=10):
    """Test concurrent processing of multiple cases (simulates real load)"""

    print(f"\n{'='*60}")
    print(f"LOAD TEST: {concurrent_cases} CONCURRENT CASES")
    print(f"{'='*60}\n")

    # Load transcript
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = f.read()

    orchestrator = AgentOrchestrator(api_key)
    agent_configs = create_mock_agent_configs()

    start_time = time.time()

    # Create tasks for concurrent cases (each case runs 5 agents in parallel)
    tasks = [
        orchestrator.run_agents_parallel(transcript, agent_configs)
        for _ in range(concurrent_cases)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_duration = time.time() - start_time

    # Analyze results
    successful_cases = sum(1 for r in results if isinstance(r, dict) and r.get("failed_agents", 1) == 0)
    total_api_calls = concurrent_cases * 5  # 5 agents per case

    print(f"Total Time: {total_duration:.2f}s")
    print(f"Successful Cases: {successful_cases}/{concurrent_cases}")
    print(f"Total API Calls: {total_api_calls}")
    print(f"Average Time per Case: {total_duration/concurrent_cases:.2f}s")

    # Check for rate limit errors
    rate_limit_errors = sum(
        1 for r in results
        if isinstance(r, dict) and any(
            "rate limit" in str(ar.get("error", "")).lower()
            for ar in r.get("agent_results", {}).values()
        )
    )

    error_rate = rate_limit_errors / concurrent_cases * 100
    print(f"Rate Limit Errors: {rate_limit_errors} ({error_rate:.1f}%)")

    success = error_rate < 5  # <5% error rate acceptable

    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\nLoad Test Result: {status}")
    print(f"{'='*60}\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="POC 2: Test Multi-Agent Parallel Orchestration")
    parser.add_argument("--transcript", type=str, required=True, help="Path to test transcript")
    parser.add_argument("--load-test", action="store_true", help="Run load test with 10 concurrent cases")
    parser.add_argument("--api-key", type=str, help="Gemini API key (or set GEMINI_API_KEY env var)")

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: Please provide --api-key or set GEMINI_API_KEY environment variable")
        return

    # Run tests
    if args.load_test:
        asyncio.run(load_test(args.transcript, api_key))
    else:
        asyncio.run(test_parallel_vs_sequential(args.transcript, api_key))


if __name__ == "__main__":
    main()
