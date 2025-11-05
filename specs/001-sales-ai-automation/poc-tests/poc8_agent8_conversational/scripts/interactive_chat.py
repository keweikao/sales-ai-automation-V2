#!/usr/bin/env python3
"""
互動式對話測試 - 與 Agent 8 進行多輪對話

支持：
- 多輪對話
- 話題切換
- 對話歷史查看
- 對話摘要

用法：
    python scripts/interactive_chat.py
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


class InteractiveChat:
    """互動式對話介面"""

    def __init__(self):
        """初始化"""
        print("=" * 80)
        print("🤖 Agent 8 互動式對話")
        print("=" * 80)
        print("\n📦 初始化 Agent 8...")

        self.agent = ConversationalAgent8(test_mode=True)
        self.user_id = "interactive_user"

        print("✅ 初始化完成\n")
        self._print_help()

    def _print_help(self):
        """打印幫助資訊"""
        print("\n" + "=" * 80)
        print("💡 使用說明")
        print("=" * 80)
        print("\n你可以用自然語言提問，例如：")
        print("  • 今天團隊表現如何？")
        print("  • 王小明本週表現如何？")
        print("  • 健康度低於 50 的案件有哪些？")
        print("  • Eats365 最近被提到幾次？")
        print("  • 掃碼點餐功能的需求如何？")
        print("\n特殊命令：")
        print("  /help    - 顯示此幫助")
        print("  /history - 查看對話歷史")
        print("  /summary - 查看對話摘要")
        print("  /clear   - 清除對話歷史")
        print("  /quit    - 退出")
        print("=" * 80 + "\n")

    def _handle_command(self, command: str) -> bool:
        """
        處理特殊命令

        Args:
            command: 命令

        Returns:
            是否應該繼續
        """
        if command == "/help":
            self._print_help()
            return True

        elif command == "/history":
            history = self.agent.conversation_manager.get_conversation_history(self.user_id)
            if not history:
                print("\n📭 尚無對話歷史\n")
            else:
                print("\n" + "=" * 80)
                print(f"📜 對話歷史（共 {len(history)} 輪）")
                print("=" * 80 + "\n")
                for i, turn in enumerate(history, 1):
                    print(f"--- 第 {i} 輪 ---")
                    print(f"🙋 用戶: {turn['question']}")
                    print(f"🤖 Agent: {turn['answer'][:200]}...")
                    print(f"📊 查詢案件數: {turn['totalCases']}")
                    print(f"🏷️ 問題類型: {turn['params'].get('type')}")
                    if turn.get('metadata', {}).get('isTopicSwitch'):
                        print(f"🔄 （話題切換）")
                    print()
            return True

        elif command == "/summary":
            summary = self.agent.conversation_manager.get_summary(self.user_id)
            print("\n" + "=" * 80)
            print("📊 對話摘要")
            print("=" * 80 + "\n")
            print(summary)
            print()
            return True

        elif command == "/clear":
            self.agent.conversation_manager.clear_conversation(self.user_id)
            print("\n✅ 對話歷史已清除\n")
            return True

        elif command == "/quit":
            print("\n👋 再見！\n")
            return False

        else:
            print(f"\n❌ 未知命令: {command}")
            print("輸入 /help 查看可用命令\n")
            return True

    def run(self):
        """運行互動式對話"""
        turn_number = 0

        while True:
            try:
                # 獲取用戶輸入
                turn_number += 1
                user_input = input(f"\n[第 {turn_number} 輪] 你: ").strip()

                if not user_input:
                    turn_number -= 1
                    continue

                # 處理命令
                if user_input.startswith("/"):
                    should_continue = self._handle_command(user_input)
                    turn_number -= 1
                    if not should_continue:
                        break
                    continue

                # 生成回答
                print("\n🤔 思考中...")

                result = self.agent.generate_answer(
                    question=user_input,
                    user_id=self.user_id
                )

                if result["success"]:
                    print(f"\n🤖 Agent 8:\n")
                    print(result["answer"])

                    # 顯示元數據
                    print(f"\n{'─' * 80}")
                    print(f"📊 數據: 查詢到 {result['totalCases']} 個案件")
                    print(f"🏷️ 問題類型: {result['params']['type']}")

                    if result.get("isTopicSwitch"):
                        print(f"🔄 話題切換: 是（重新搜集資訊）")
                    else:
                        print(f"🔄 話題切換: 否（延續對話）")

                    if result.get("context", {}).get("hasPronouns"):
                        print(f"💬 包含代詞: 是（參考對話歷史）")

                    print(f"{'─' * 80}")

                else:
                    print(f"\n❌ 錯誤: {result.get('error', '未知錯誤')}")

            except KeyboardInterrupt:
                print("\n\n👋 再見！\n")
                break

            except Exception as e:
                print(f"\n❌ 發生錯誤: {str(e)}\n")


def main():
    """主函數"""
    # 檢查是否設置了 GEMINI_API_KEY
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ 錯誤: 請先設置 GEMINI_API_KEY 環境變數")
        print("\n使用方法:")
        print("  export GEMINI_API_KEY='your-api-key'")
        print("  python scripts/interactive_chat.py")
        sys.exit(1)

    chat = InteractiveChat()
    chat.run()


if __name__ == "__main__":
    main()
