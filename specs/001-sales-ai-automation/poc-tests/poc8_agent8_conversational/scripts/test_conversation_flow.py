#!/usr/bin/env python3
"""
測試多輪對話和話題切換

這個腳本會自動執行一系列對話場景，測試：
1. 多輪對話的上下文理解
2. 話題切換的檢測
3. 代詞指代的處理
"""

import os
import sys
from pathlib import Path

# 添加 src 到路徑
current_dir = Path(__file__).parent
project_dir = current_dir.parent
sys.path.insert(0, str(project_dir / "src"))

# 設置測試模式
os.environ["TEST_MODE"] = "true"

from agents.conversational_agent8 import ConversationalAgent8


def test_scenario(agent, user_id, scenario_name, questions):
    """
    測試一個對話場景

    Args:
        agent: Agent 8 實例
        user_id: 用戶 ID
        scenario_name: 場景名稱
        questions: 問題列表
    """
    print(f"\n{'=' * 80}")
    print(f"🎬 場景: {scenario_name}")
    print("=" * 80)

    for i, question in enumerate(questions, 1):
        print(f"\n[輪次 {i}] 用戶: {question}")
        print("-" * 80)

        result = agent.generate_answer(question, user_id)

        if result["success"]:
            print(f"\n✅ Agent 8:\n{result['answer']}")

            # 顯示元數據
            print(f"\n📊 元數據:")
            print(f"  • 問題類型: {result['params']['type']}")
            print(f"  • 查詢案件數: {result['totalCases']}")
            print(f"  • 話題切換: {'是' if result.get('isTopicSwitch') else '否'}")
            print(f"  • 包含代詞: {'是' if result.get('context', {}).get('hasPronouns') else '否'}")
        else:
            print(f"\n❌ 錯誤: {result.get('error')}")

    print(f"\n{'=' * 80}\n")


def main():
    """主函數"""
    print("=" * 80)
    print("🧪 Agent 8 多輪對話和話題切換測試")
    print("=" * 80)

    # 初始化 Agent 8
    print("\n📦 初始化 Agent 8...")
    agent = ConversationalAgent8(test_mode=True)
    print("✅ 初始化完成\n")

    # 場景 1: 團隊概況 → 個人深入
    test_scenario(
        agent,
        user_id="test_user_1",
        scenario_name="場景 1：團隊概況追問個人細節",
        questions=[
            "今天團隊表現如何？",
            "王小明的情況詳細說明？",
            "他最好的案件是哪個？"
        ]
    )

    # 清除對話歷史
    agent.conversation_manager.clear_conversation("test_user_1")

    # 場景 2: 低健康度案件 → 話題切換到競品
    test_scenario(
        agent,
        user_id="test_user_2",
        scenario_name="場景 2：低健康度案件 → 切換到競品情報",
        questions=[
            "健康度低於 50 的案件有哪些？",
            "Eats365 最近被提到幾次？",  # 話題切換
            "客戶怎麼評價他們？"
        ]
    )

    # 清除對話歷史
    agent.conversation_manager.clear_conversation("test_user_2")

    # 場景 3: 個人績效 → 切換到其他人 → 對比
    test_scenario(
        agent,
        user_id="test_user_3",
        scenario_name="場景 3：個人績效對比",
        questions=[
            "王小明本週表現如何？",
            "陳美玲呢？",  # 話題切換但保持問題類型
            "他們兩個誰比較好？"
        ]
    )

    # 清除對話歷史
    agent.conversation_manager.clear_conversation("test_user_3")

    # 場景 4: 產品需求 → 案件詳情
    test_scenario(
        agent,
        user_id="test_user_4",
        scenario_name="場景 4：產品需求 → 相關案件",
        questions=[
            "掃碼點餐功能的需求如何？",
            "哪些案件提到這個需求？",
            "這些案件的健康度怎麼樣？"
        ]
    )

    print("=" * 80)
    print("✅ 測試完成！")
    print("=" * 80)


if __name__ == "__main__":
    # 檢查是否設置了 GEMINI_API_KEY
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ 錯誤: 請先設置 GEMINI_API_KEY 環境變數")
        print("\n使用方法:")
        print("  export GEMINI_API_KEY='your-api-key'")
        print("  python scripts/test_conversation_flow.py")
        sys.exit(1)

    main()
