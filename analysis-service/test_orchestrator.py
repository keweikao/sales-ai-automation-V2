#!/usr/bin/env python3
"""
Test script for Multi-Agent Orchestrator.

Usage:
    export GEMINI_API_KEY="your-key"
    python test_orchestrator.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestrator import MultiAgentOrchestrator


# Sample transcript for testing
SAMPLE_TRANSCRIPT = [
    {
        "start": 0.0,
        "end": 5.2,
        "speaker": "Speaker 1",
        "text": "你好，我是 iCHEF 的業務代表，今天來介紹我們的 POS 系統"
    },
    {
        "start": 5.5,
        "end": 8.1,
        "speaker": "Speaker 2",
        "text": "你好，我是這間餐廳的老闆"
    },
    {
        "start": 8.5,
        "end": 15.3,
        "speaker": "Speaker 1",
        "text": "請問您目前使用什麼系統來管理點餐和結帳呢？"
    },
    {
        "start": 15.8,
        "end": 22.5,
        "speaker": "Speaker 2",
        "text": "我們現在用的是傳統收銀機，很多功能都沒有，報表也不方便"
    },
    {
        "start": 23.0,
        "end": 35.2,
        "speaker": "Speaker 1",
        "text": "了解。那您覺得目前最需要改善的是哪些部分？比如點餐效率、庫存管理、還是報表分析？"
    },
    {
        "start": 35.8,
        "end": 45.5,
        "speaker": "Speaker 2",
        "text": "主要是報表和庫存管理。我們常常不知道哪些菜賣得好，食材也常常缺貨或過期"
    },
]

SPEAKER_STATS = {
    "Speaker 1": 55.0,  # 業務 55%
    "Speaker 2": 45.0,  # 老闆 45%
}

CONVERSATION_METADATA = {
    "customer_name": "測試餐廳",
    "sales_rep": "王小美",
    "date": "2025-11-06",
}


async def main():
    print("=" * 60)
    print("Multi-Agent Orchestrator Test")
    print("=" * 60)

    orchestrator = MultiAgentOrchestrator()

    print("\n📊 Starting analysis with 5 agents in parallel...")
    print(f"Transcript segments: {len(SAMPLE_TRANSCRIPT)}")
    print(f"Speakers: {len(SPEAKER_STATS)}")

    try:
        result = await orchestrator.analyze_transcript(
            case_id="TEST_CASE_001",
            transcript_segments=SAMPLE_TRANSCRIPT,
            speaker_statistics=SPEAKER_STATS,
            conversation_metadata=CONVERSATION_METADATA,
        )

        print("\n✅ Analysis Complete!")
        print("-" * 60)

        # Print summary
        summary = orchestrator.get_analysis_summary(result)
        print(f"\nCase ID: {summary['case_id']}")
        print(f"Success: {summary['success']}")
        print(f"Total Duration: {summary['total_duration']}s")

        print("\n📋 Agent Results:")
        for agent_id, agent_summary in summary['agents'].items():
            status = "✅" if agent_summary['success'] else "❌"
            print(f"  {status} {agent_id}: {agent_summary['duration']}s")
            if not agent_summary['success']:
                print(f"     Error: {agent_summary.get('error', 'Unknown')}")

        # Print detailed results for Agent 1 as example
        if result.success:
            print("\n" + "=" * 60)
            print("Sample Output - Agent 1 (Participant Profile)")
            print("=" * 60)
            agent1_data = result.get_agent_data("agent1")
            if agent1_data:
                print(json.dumps(agent1_data, ensure_ascii=False, indent=2))

        return 0 if result.success else 1

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
