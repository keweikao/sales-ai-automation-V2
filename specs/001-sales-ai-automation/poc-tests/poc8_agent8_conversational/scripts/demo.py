#!/usr/bin/env python3
"""
Agent 8 演示腳本 - 展示核心功能

這個腳本會執行一個精心設計的演示場景，展示：
1. 團隊整體分析
2. 個人績效深入
3. 多輪對話理解
4. 話題切換處理
5. 競品情報分析

適合向團隊或主管展示 Agent 8 的能力。
"""

import os
import sys
import time
from pathlib import Path

# 添加 src 到路徑
current_dir = Path(__file__).parent
project_dir = current_dir.parent
sys.path.insert(0, str(project_dir / "src"))

# 設置測試模式
os.environ["TEST_MODE"] = "true"

from agents.conversational_agent8 import ConversationalAgent8


def print_header(title):
    """打印標題"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_section(title):
    """打印區塊標題"""
    print("\n" + "─" * 80)
    print(f"  {title}")
    print("─" * 80)


def ask_agent(agent, user_id, question, pause=True):
    """
    向 Agent 提問並顯示結果

    Args:
        agent: Agent 8 實例
        user_id: 用戶 ID
        question: 問題
        pause: 是否暫停等待用戶按鍵
    """
    print(f"\n💬 主管: {question}")
    print("\n🤔 思考中...")

    result = agent.generate_answer(question, user_id)

    if result["success"]:
        print(f"\n🤖 Agent 8:\n")
        print(result["answer"])

        # 顯示元數據
        print_section("元數據")
        print(f"📊 查詢案件數: {result['totalCases']} 個")
        print(f"🏷️  問題類型: {result['params']['type']}")
        print(f"🔄 話題切換: {'是（重新搜集資訊）' if result.get('isTopicSwitch') else '否（延續對話）'}")

        if result.get('context', {}).get('hasPronouns'):
            print(f"💬 包含代詞: 是（參考對話歷史）")

        if result.get('teamStats'):
            stats = result['teamStats']
            if stats.get('avgHealthScore'):
                print(f"📈 團隊平均健康度: {stats['avgHealthScore']} 分")

    else:
        print(f"\n❌ 錯誤: {result.get('error', '未知錯誤')}")

    if pause:
        input("\n按 Enter 繼續...")


def run_demo():
    """執行演示"""
    print_header("🎬 Agent 8 對話式交互 - 功能演示")

    print("""
這個演示將展示 Agent 8 的核心能力：

✅ 自然語言理解：用繁體中文提問，Agent 8 自動理解問題意圖
✅ 數據查詢分析：從 30 個模擬案件中查詢相關數據
✅ 洞察和建議：提供有價值的業務洞察和可執行建議
✅ 多輪對話：理解上下文，支持追問和代詞指代
✅ 話題切換：檢測話題改變，重新搜集資訊

按 Enter 開始演示...
    """)
    input()

    # 初始化 Agent 8
    print_section("初始化 Agent 8")
    print("📦 正在初始化...")
    agent = ConversationalAgent8(test_mode=True)
    print("✅ 初始化完成！")
    print(f"📊 載入測試數據: 30 個模擬案件")

    user_id = "demo_user"

    # 場景 1: 團隊整體分析
    print_header("場景 1: 團隊整體分析")
    print("主管想了解團隊整體表現...")
    time.sleep(1)

    ask_agent(agent, user_id, "今天團隊表現如何？")

    # 場景 2: 個人績效深入
    print_header("場景 2: 個人績效深入分析")
    print("主管注意到王小明表現優異，想了解更多細節...")
    time.sleep(1)

    ask_agent(agent, user_id, "王小明的情況詳細說明？")

    # 場景 3: 多輪對話 - 代詞指代
    print_header("場景 3: 多輪對話 - 代詞指代")
    print("主管使用代詞「他」追問，Agent 8 會理解指的是「王小明」...")
    time.sleep(1)

    ask_agent(agent, user_id, "他最好的案件是哪個？")

    # 場景 4: 話題切換 - 風險案件
    print_header("場景 4: 話題切換 - 關注風險案件")
    print("主管切換話題，想了解需要關注的低健康度案件...")
    time.sleep(1)

    ask_agent(agent, user_id, "健康度低於 50 的案件有哪些？")

    # 場景 5: 話題切換 - 競品情報
    print_header("場景 5: 話題切換 - 競品情報分析")
    print("主管再次切換話題，想了解競品情況...")
    time.sleep(1)

    ask_agent(agent, user_id, "Eats365 最近被提到幾次？", pause=False)

    # 總結
    print_header("演示完成！")

    # 顯示對話摘要
    print("\n📊 對話摘要:")
    summary = agent.conversation_manager.get_summary(user_id)
    print(summary)

    print("""
\n✅ Agent 8 核心能力展示完畢！

💡 主要亮點：
1. ✅ 準確理解繁體中文問題，識別問題類型
2. ✅ 自動查詢相關數據（30 個案件中精準篩選）
3. ✅ 提供結構化回答（數據 + 洞察 + 建議）
4. ✅ 理解代詞指代（「他」= 王小明）
5. ✅ 檢測話題切換並重新查詢數據
6. ✅ 回答使用繁體中文，語氣專業友善

🚀 下一步：
• 整合到 Slack App（/ask-agent8 命令）
• 配置主管權限
• 部署到生產環境

💰 成本：約 $0.11/月（極低）

📞 如有問題，請查看 POC8_REPORT.md 完整測試報告
    """)


def main():
    """主函數"""
    # 檢查是否設置了 GEMINI_API_KEY
    if not os.getenv("GEMINI_API_KEY"):
        print("=" * 80)
        print("❌ 錯誤: 請先設置 GEMINI_API_KEY 環境變數")
        print("=" * 80)
        print("\n使用方法:")
        print("  export GEMINI_API_KEY='your-api-key'")
        print("  python scripts/demo.py")
        print("\n或從現有配置載入:")
        print("  source ../../../.env")
        print("  python scripts/demo.py")
        print()
        sys.exit(1)

    try:
        run_demo()
    except KeyboardInterrupt:
        print("\n\n👋 演示中斷\n")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {str(e)}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
