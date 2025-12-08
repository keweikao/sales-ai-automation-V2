#!/usr/bin/env python3
"""
測試更新後的 Agent Prompts

使用真實的銷售對話轉錄檔案來測試所有 4 個 Agent 的新 prompts。
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# 添加 analysis-service 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "analysis-service" / "src"))

from agents.agent1_context import ContextAgent
from agents.agent2_buyer import BuyerAgent
from agents.agent3_seller import SellerAgent
from agents.agent4_summary import SummaryAgent


def parse_transcript_file(filepath: str) -> List[Dict[str, Any]]:
    """
    解析轉錄檔案，將其轉換為 Agent 可以處理的格式
    
    格式: [HH:MM] Speaker: 文字內容
    """
    segments = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            # 解析格式: [00:01] Speaker: 文字內容
            if line.startswith('[') and ']' in line:
                try:
                    # 提取時間戳
                    time_end = line.index(']')
                    timestamp = line[1:time_end]  # 移除 []
                    
                    # 轉換 MM:SS 為秒數
                    time_parts = timestamp.split(':')
                    if len(time_parts) == 2:
                        minutes, seconds = map(int, time_parts)
                        total_seconds = minutes * 60 + seconds
                    else:
                        total_seconds = 0
                    
                    # 提取說話者和文字
                    rest = line[time_end + 1:].strip()
                    if ':' in rest:
                        speaker_end = rest.index(':')
                        speaker = rest[:speaker_end].strip()
                        text = rest[speaker_end + 1:].strip()
                    else:
                        speaker = "Unknown"
                        text = rest
                    
                    segments.append({
                        "start": total_seconds,
                        "end": total_seconds + 5,  # 假設每段持續 5 秒
                        "speaker": speaker,
                        "speakerId": speaker,
                        "text": text
                    })
                except (ValueError, IndexError) as e:
                    print(f"警告: 無法解析第 {line_num} 行: {line[:50]}... 錯誤: {e}")
                    continue
    
    print(f"✓ 成功解析 {len(segments)} 個對話片段")
    return segments


def test_agent1_context(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """測試 Agent 1: 戰場偵查"""
    print("\n" + "="*60)
    print("🔍 測試 Agent 1: 戰場偵查 (Context & Structure)")
    print("="*60)
    
    agent = ContextAgent(
        model_name="gemini-2.0-flash-exp",
        temperature=0.2
    )
    
    result = agent.analyze(transcript_segments=segments)
    
    print("\n📊 Agent 1 分析結果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return result


def test_agent2_buyer(segments: List[Dict[str, Any]], context_insights: Dict[str, Any]) -> Dict[str, Any]:
    """測試 Agent 2: MEDDIC 買家分析"""
    print("\n" + "="*60)
    print("🧠 測試 Agent 2: MEDDIC 買家分析")
    print("="*60)
    
    agent = BuyerAgent(
        model_name="gemini-2.0-flash-exp",
        temperature=0.2
    )
    
    result = agent.analyze(
        transcript_segments=segments,
        context_insights=context_insights
    )
    
    print("\n📊 Agent 2 分析結果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return result


def test_agent3_seller(
    segments: List[Dict[str, Any]], 
    context_insights: Dict[str, Any],
    buyer_insights: Dict[str, Any]
) -> Dict[str, Any]:
    """測試 Agent 3: 銷售預測專家"""
    print("\n" + "="*60)
    print("📈 測試 Agent 3: 銷售預測專家")
    print("="*60)
    
    agent = SellerAgent(
        model_name="gemini-2.0-flash-exp",
        temperature=0.2
    )
    
    result = agent.analyze(
        transcript_segments=segments,
        context_insights=context_insights,
        buyer_insights=buyer_insights
    )
    
    print("\n📊 Agent 3 分析結果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return result


def test_agent4_summary(segments: List[Dict[str, Any]], context_insights: Dict[str, Any]) -> Dict[str, Any]:
    """測試 Agent 4: 會議記錄秘書"""
    print("\n" + "="*60)
    print("📝 測試 Agent 4: 會議記錄秘書")
    print("="*60)
    
    agent = SummaryAgent(
        model_name="gemini-2.0-flash-exp",
        temperature=0.2
    )
    
    result = agent.analyze(
        transcript_segments=segments,
        context_insights=context_insights
    )
    
    print("\n📊 Agent 4 分析結果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return result


def main():
    """主測試流程"""
    print("🚀 開始測試更新後的 Agent Prompts")
    print("="*60)
    
    # 1. 解析轉錄檔案
    transcript_file = Path(__file__).parent.parent / "202512-IC001_transcript_fixed.txt"
    
    if not transcript_file.exists():
        print(f"❌ 錯誤: 找不到轉錄檔案 {transcript_file}")
        sys.exit(1)
    
    print(f"\n📄 讀取轉錄檔案: {transcript_file.name}")
    segments = parse_transcript_file(str(transcript_file))
    
    if not segments:
        print("❌ 錯誤: 無法解析任何對話片段")
        sys.exit(1)
    
    # 2. 依序測試所有 Agents
    results = {}
    
    try:
        # Agent 1: Context
        results['agent1_context'] = test_agent1_context(segments)
        
        # Agent 2: Buyer (需要 Agent 1 的結果)
        results['agent2_buyer'] = test_agent2_buyer(segments, results['agent1_context'])
        
        # Agent 3: Seller (需要 Agent 1 和 Agent 2 的結果)
        results['agent3_seller'] = test_agent3_seller(
            segments,
            results['agent1_context'],
            results['agent2_buyer']
        )
        
        # Agent 4: Summary (需要 Agent 1 的結果)
        results['agent4_summary'] = test_agent4_summary(segments, results['agent1_context'])
        
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 3. 儲存完整結果
    output_file = Path(__file__).parent / "test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print(f"✅ 測試完成！結果已儲存至: {output_file}")
    print("="*60)
    
    # 4. 顯示關鍵摘要
    print("\n📋 關鍵結果摘要:")
    print("-" * 60)
    
    if 'agent1_context' in results:
        print(f"\n🔍 Agent 1 - 識別到 {len(results['agent1_context'].get('speakers', []))} 位說話者")
        print(f"   對話階段: {len(results['agent1_context'].get('stages', []))} 個")
    
    if 'agent2_buyer' in results:
        meddic = results['agent2_buyer'].get('meddic', {})
        print(f"\n🧠 Agent 2 - Champion: {meddic.get('champion', 'N/A')}")
        print(f"   Trust Score: {results['agent2_buyer'].get('psychology', {}).get('trustScore', 'N/A')}")
    
    if 'agent3_seller' in results:
        forecast = results['agent3_seller'].get('forecast', {})
        print(f"\n📈 Agent 3 - Deal Health: {results['agent3_seller'].get('dealHealth', {}).get('score', 'N/A')}/100")
        print(f"   Forecast: {forecast.get('category', 'N/A')}")
        print(f"   預計成交日: {forecast.get('estimatedCloseDate', 'N/A')}")
    
    if 'agent4_summary' in results:
        print(f"\n📝 Agent 4 - 會議主旨: {results['agent4_summary'].get('email_subject', 'N/A')}")


if __name__ == "__main__":
    main()
