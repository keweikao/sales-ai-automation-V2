#!/usr/bin/env python3
"""
範例腳本：使用程式碼智能工具分析專案
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.code_intelligence.repo_analyzer import SalesAIRepoAnalyzer  # noqa: E402
from tools.code_intelligence.symbol_indexer import SmartCodeSearch  # noqa: E402

def main():
    print("=" * 60)
    print("Sales AI Automation V2 - 程式碼智能分析範例")
    print("=" * 60)
    
    # 建立分析器
    analyzer = SalesAIRepoAnalyzer()
    searcher = SmartCodeSearch()
    
    # 1. 找出所有 AI 代理
    print("\n📌 步驟 1: 找出所有 AI 代理")
    print("-" * 60)
    agents = analyzer.find_agent_implementations()
    print(f"找到 {len(agents)} 個代理:")
    for agent in agents[:7]:  # 顯示前 7 個
        print(f"  • {agent['file'].split('/')[-1]}:{agent['line']}")
    
    # 2. 提取 API 端點
    print("\n📌 步驟 2: 提取 API 端點")
    print("-" * 60)
    endpoints = analyzer.extract_api_endpoints()
    print(f"找到 {len(endpoints)} 個端點:")
    for ep in endpoints[:5]:  # 顯示前 5 個
        print(f"  • {ep['file'].split('/')[-1]}:{ep['line']}")
        print(f"    {ep['content'].strip()}")
    
    # 3. 建立符號索引
    print("\n📌 步驟 3: 建立符號索引")
    print("-" * 60)
    result = searcher.build_index(force_rebuild=True)
    if result["status"] == "success":
        print("✓ 索引建立成功")
        print(f"  總符號數: {result['total_symbols']}")
    
    # 4. 搜尋程式碼
    print("\n📌 步驟 4: 搜尋程式碼")
    print("-" * 60)
    query = "transcribe"
    results = searcher.search(query, limit=5)
    print(f"搜尋 '{query}' 的結果:")
    for r in results:
        print(f"  • {r['name']} ({r['type']})")
        print(f"    {r['file'].split('/')[-1]}:{r['line_start']}")
    
    # 5. 獲取索引統計
    print("\n📌 步驟 5: 索引統計")
    print("-" * 60)
    stats = searcher.get_stats()
    if stats["status"] == "success":
        print(f"總符號數: {stats['total_symbols']}")
        print("類型分布:")
        for symbol_type, count in sorted(stats['type_distribution'].items(), 
                                        key=lambda x: x[1], reverse=True)[:5]:
            print(f"  • {symbol_type}: {count}")
    
    print("\n" + "=" * 60)
    print("✓ 分析完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
