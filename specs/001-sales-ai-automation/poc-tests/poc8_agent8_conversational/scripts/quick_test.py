#!/usr/bin/env python3
"""
快速測試腳本 - 測試 Agent 8 的完整流程

用法：
    python scripts/quick_test.py
"""

import os
import sys
import json
from pathlib import Path

# 添加 src 到路徑
current_dir = Path(__file__).parent
project_dir = current_dir.parent
sys.path.insert(0, str(project_dir / "src"))

# 設置測試模式
os.environ["TEST_MODE"] = "true"

from agents.conversational_agent8 import ConversationalAgent8


def main():
    """主函數"""
    print("=" * 80)
    print("🚀 Agent 8 快速測試")
    print("=" * 80)

    # 初始化 Agent 8
    print("\n📦 初始化 Agent 8...")
    agent = ConversationalAgent8(test_mode=True)
    print("✅ 初始化完成")

    # 測試問題
    test_questions = [
        "今天團隊表現如何？",
        "王小明本週表現如何？",
        "健康度低於 50 的案件有哪些？",
    ]

    conversation_history = []

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'=' * 80}")
        print(f"問題 {i}: {question}")
        print("-" * 80)

        try:
            result = agent.generate_answer(question, conversation_history)

            if result["success"]:
                print(f"\n✅ 成功生成回答")
                print(f"\n【回答】\n{result['answer']}")
                print(f"\n【數據統計】")
                print(f"  - 查詢到 {result['totalCases']} 個案件")
                print(f"  - 問題類型: {result['params']['type']}")

                # 保存到對話歷史
                conversation_history.append({
                    "question": question,
                    "answer": result["answer"]
                })
            else:
                print(f"\n❌ 生成回答失敗")
                print(f"錯誤: {result.get('error', '未知錯誤')}")

        except Exception as e:
            print(f"\n❌ 執行失敗")
            print(f"錯誤: {str(e)}")

    print(f"\n{'=' * 80}")
    print(f"✅ 測試完成！共測試 {len(test_questions)} 個問題")
    print("=" * 80)


if __name__ == "__main__":
    # 檢查是否設置了 GEMINI_API_KEY
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ 錯誤: 請先設置 GEMINI_API_KEY 環境變數")
        print("\n使用方法:")
        print("  export GEMINI_API_KEY='your-api-key'")
        print("  python scripts/quick_test.py")
        sys.exit(1)

    main()
