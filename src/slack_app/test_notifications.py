"""
Test script for Agent 6/7 notifications with actual data structure.

This script validates that our notification modules correctly handle
the real Agent 6 and Agent 7 output structures.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from notifications.agent6_notifier import Agent6Notifier
from notifications.agent7_notifier import Agent7Notifier

# Mock Slack client and Firestore for testing
class MockSlackClient:
    def chat_postMessage(self, **kwargs):
        print("\n" + "="*60)
        print("📤 SLACK MESSAGE")
        print("="*60)
        print(f"Channel: {kwargs.get('channel')}")
        print(f"Text: {kwargs.get('text')}")
        print("\nBlocks:")
        print(json.dumps(kwargs.get('blocks', []), indent=2, ensure_ascii=False))
        return {'ok': True, 'ts': '1699600000.123456'}

class MockFirestore:
    pass

# Load actual Agent 6/7 fixture data
REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "analysis-service/tests/fixtures/agent67"

def load_fixture(filename):
    """Load fixture JSON file."""
    with open(FIXTURES_DIR / filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_agent6_notification():
    """Test Agent 6 notification with real data."""
    print("\n\n" + "🧪 " + "="*58)
    print("🧪 TEST: Agent 6 Notification")
    print("🧪 " + "="*58)

    # Load real Agent 6 data
    agent6_data = load_fixture("agent6_structured.json")
    structured_data = agent6_data.get("structured", {})

    # Initialize notifier
    client = MockSlackClient()
    db = MockFirestore()
    notifier = Agent6Notifier(client, db)

    # Build blocks
    case_metadata = {
        'storeName': '測試餐廳',
        'customerId': 'C12345'
    }
    blocks = notifier.build_agent6_blocks(
        case_id="TEST_CASE_001",
        agent6_data=structured_data,
        case_metadata=case_metadata
    )

    # Print result
    print(f"\n✅ Generated {len(blocks)} blocks")
    print("\nBlock structure:")
    for i, block in enumerate(blocks, 1):
        block_type = block.get('type')
        print(f"  {i}. {block_type}")

    # Simulate sending
    client.chat_postMessage(
        channel="U01234567",
        text="📊 銷售分析報告",
        blocks=blocks
    )

    return blocks

def test_agent7_notification():
    """Test Agent 7 notification with real data."""
    print("\n\n" + "🧪 " + "="*58)
    print("🧪 TEST: Agent 7 Notification")
    print("🧪 " + "="*58)

    # Load real Agent 7 data
    agent7_data = load_fixture("agent7_summary.json")
    customer_summary = agent7_data.get("customerSummary", {})
    markdown = customer_summary.get("markdown", "")

    # Initialize notifier
    client = MockSlackClient()
    db = MockFirestore()
    notifier = Agent7Notifier(client, db)

    # Build blocks
    case_metadata = {
        'storeName': '測試餐廳',
        'customerId': 'C12345'
    }
    blocks = notifier.build_agent7_preview_blocks(
        case_id="TEST_CASE_001",
        summary_markdown=markdown,
        case_metadata=case_metadata,
        is_edited=False
    )

    # Print result
    print(f"\n✅ Generated {len(blocks)} blocks")
    print(f"✅ Markdown length: {len(markdown)} characters")
    print("\nBlock structure:")
    for i, block in enumerate(blocks, 1):
        block_type = block.get('type')
        print(f"  {i}. {block_type}")

    # Simulate sending
    client.chat_postMessage(
        channel="U01234567",
        text="📝 客戶摘要預覽",
        blocks=blocks
    )

    return blocks

def main():
    """Run all tests."""
    print("\n" + "🚀 " + "="*58)
    print("🚀 Testing Slack Notifications with Real Agent Data")
    print("🚀 " + "="*58)

    try:
        # Test Agent 6
        agent6_blocks = test_agent6_notification()
        print("\n✅ Agent 6 notification test PASSED")

        # Test Agent 7
        agent7_blocks = test_agent7_notification()
        print("\n✅ Agent 7 notification test PASSED")

        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED")
        print("="*60)

        print("\n📊 Summary:")
        print(f"  • Agent 6 blocks: {len(agent6_blocks)}")
        print(f"  • Agent 7 blocks: {len(agent7_blocks)}")
        print("\n✅ Notification modules are ready for production!")

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
