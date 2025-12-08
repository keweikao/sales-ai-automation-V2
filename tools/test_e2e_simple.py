#!/usr/bin/env python3
"""
簡化版端到端測試 - 跳過 GCS 上傳，直接測試分析流程

使用方式:
    python3 tools/test_e2e_simple.py
"""

import os
import sys
import time
import json
import requests
from google.cloud import firestore

# 配置
GCP_PROJECT_ID = "sales-ai-automation-v2"
ANALYSIS_SERVICE_URL = "https://analysis-service-497329205771.asia-east1.run.app"

# 顏色輸出
class Colors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    OKCYAN = '\033[96m'
    WARNING = '\033[93m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

def print_step(step_num, description):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}步驟 {step_num}: {description}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(message):
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def main():
    case_id = f"e2e-test-{int(time.time())}"
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("="*60)
    print("端到端整合測試（簡化版）")
    print("="*60)
    print(f"{Colors.ENDC}\n")
    
    print_info(f"測試案件 ID: {case_id}")
    
    # 初始化 Firestore
    db = firestore.Client(project=GCP_PROJECT_ID)
    
    # 步驟 1: 建立測試案件並載入轉錄數據
    print_step(1, "建立測試案件並載入轉錄數據")
    
    try:
        # 載入測試轉錄
        transcript_path = "/Users/stephen/Desktop/sales-ai-automation-V2/202512-IC001_transcript_fixed.txt"
        
        if not os.path.exists(transcript_path):
            print_error(f"找不到測試轉錄檔案: {transcript_path}")
            return False
        
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        
        # 解析轉錄
        import re
        segments = []
        lines = transcript_text.strip().split('\n')
        pattern = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*([^:]+):\s*(.+)')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = pattern.match(line)
            if match:
                time_str, speaker, content = match.groups()
                parts = time_str.split(':')
                
                if len(parts) == 2:
                    seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    continue
                
                segments.append({
                    'start': float(seconds),
                    'end': float(seconds + 5),
                    'speaker': speaker.strip(),
                    'text': content.strip()
                })
        
        print_success(f"解析轉錄: {len(segments)} 個片段")
        
        # 建立 Firestore 案件
        case_ref = db.collection('cases').document(case_id)
        case_ref.set({
            'caseId': case_id,
            'gcsUri': f'gs://test-bucket/{case_id}.m4a',
            'status': 'transcribed',
            'uploadedBy': 'e2e-test@example.com',
            'channel_id': 'C_TEST_CHANNEL',
            'message_ts': str(time.time()),
            'thread_ts': str(time.time()),
            'transcription': {
                'text': transcript_text,
                'segments': segments,
                'language': 'zh-TW',
                'duration': 3000,
            },
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP,
        })
        
        print_success(f"Firestore 案件已建立: {case_id}")
        
    except Exception as e:
        print_error(f"建立案件失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 步驟 2: 觸發分析服務
    print_step(2, "觸發分析服務 (4 Agents)")
    
    try:
        payload = {'caseId': case_id}
        
        print_info(f"調用分析服務: {ANALYSIS_SERVICE_URL}/analyze")
        response = requests.post(
            f"{ANALYSIS_SERVICE_URL}/analyze",
            json=payload,
            timeout=300
        )
        
        if response.status_code == 200:
            print_success("分析服務已觸發")
            
            # 等待分析完成
            print_info("等待分析完成...")
            max_wait = 300
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                case_data = case_ref.get().to_dict()
                status = case_data.get('status')
                analysis = case_data.get('analysis', {})
                
                print_info(f"當前狀態: {status}, 分析狀態: {analysis.get('status', 'unknown')}")
                
                if status == 'analyzed' or analysis.get('status') == 'completed':
                    print_success("分析完成！")
                    break
                
                time.sleep(10)
            
        else:
            print_error(f"分析服務返回錯誤: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print_error(f"觸發分析失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 步驟 3: 驗證結果
    print_step(3, "驗證分析結果")
    
    try:
        case_data = case_ref.get().to_dict()
        
        # 檢查轉錄
        transcription = case_data.get('transcription', {})
        if transcription:
            print_success(f"✓ 轉錄數據: {len(transcription.get('segments', []))} 個片段")
        
        # 檢查分析
        analysis = case_data.get('analysis', {})
        if analysis:
            print_success("✓ 分析數據存在")
            
            agents = analysis.get('agents', {})
            for agent_id in ['agent1', 'agent2', 'agent3', 'agent4']:
                agent_data = agents.get(agent_id, {})
                status = agent_data.get('status', 'unknown')
                
                if status == 'success':
                    print_success(f"  ✓ {agent_id}: 成功")
                    # 檢查報告
                    metadata = agent_data.get('metadata', {})
                    if metadata.get('report'):
                        print_info(f"    - 報告長度: {len(metadata['report'])} 字元")
                else:
                    print_error(f"  ✗ {agent_id}: {status}")
                    if agent_data.get('error'):
                        print_error(f"    錯誤: {agent_data['error']}")
        
        # 檢查 Slack 通知
        notification = case_data.get('notification', {})
        if notification:
            print_success(f"✓ Slack 通知: thread_ts={notification.get('slackThreadTs')}")
        else:
            print_warning("⚠ 尚未發送 Slack 通知")
        
        # 總結
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("="*60)
        print("測試總結")
        print("="*60)
        print(f"{Colors.ENDC}\n")
        
        all_agents_success = all(
            agents.get(f'agent{i}', {}).get('status') == 'success'
            for i in range(1, 5)
        )
        
        if all_agents_success:
            print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 所有 Agent 測試通過！{Colors.ENDC}\n")
        else:
            print(f"{Colors.WARNING}{Colors.BOLD}⚠ 部分 Agent 失敗{Colors.ENDC}\n")
        
        print_info(f"測試案件 ID: {case_id}")
        print_info(f"Firestore 路徑: cases/{case_id}")
        print_info(f"查看完整數據: https://console.firebase.google.com/project/{GCP_PROJECT_ID}/firestore/data/cases/{case_id}")
        
        return all_agents_success
        
    except Exception as e:
        print_error(f"驗證失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
