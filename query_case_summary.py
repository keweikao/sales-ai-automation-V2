#!/usr/bin/env python3
"""
Quick summary query for any case
Usage: python3 query_case_summary.py <CASE_ID>
"""

import sys
from google.cloud import firestore

def get_case_summary(case_id: str):
    """Get a quick summary of a case"""
    try:
        db = firestore.Client()
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        
        if not case_doc.exists:
            print(f"\n❌ Case {case_id} not found")
            return
        
        data = case_doc.to_dict()
        
        # Firestore flattens nested fields with dot notation
        step = data.get('analysis.transcription.step', 'N/A')
        progress = data.get('analysis.transcription.progress', 0)
        error = data.get('analysis.transcription.error')
        detail = data.get('analysis.transcription.detail')
        total_chunks = data.get('analysis.transcription.totalChunks', 0)
        completed_chunks = data.get('analysis.transcription.completedChunks', 0)
        updated_at = data.get('analysis.transcription.updatedAt')
        
        print(f"\n{'='*70}")
        print(f"  案件摘要: {case_id}")
        print(f"{'='*70}")
        print(f"客戶: {data.get('customerName', 'N/A')}")
        print(f"業務: {data.get('salesRepName', 'N/A')}")
        print(f"案件狀態: {data.get('status', 'N/A')}")
        print(f"創建時間: {data.get('createdAt', 'N/A')}")
        print(f"\n轉錄狀態:")
        print(f"  步驟: {step}")
        print(f"  進度: {progress*100:.1f}%")
        print(f"  分塊: {completed_chunks}/{total_chunks}")
        print(f"  最後更新: {updated_at}")
        
        if error:
            print(f"\n  ❌ 錯誤: {error}")
            print(f"  狀態: 轉錄失敗")
        elif step == "completed":
            print(f"  ✅ 狀態: 轉錄完成")
        elif step in ["transcribing", "in_progress"]:
            print(f"  ⏳ 狀態: 轉錄進行中")
        
        if detail:
            detail_str = str(detail)
            if len(detail_str) > 200:
                print(f"\n轉錄預覽:\n  {detail_str[:200]}...")
                print(f"  (總長度: {len(detail_str)} 字元)")
            else:
                print(f"\n轉錄詳情:\n  {detail_str}")
        
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ 查詢錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    case_id = sys.argv[1] if len(sys.argv) > 1 else "202511-IC011"
    get_case_summary(case_id)
