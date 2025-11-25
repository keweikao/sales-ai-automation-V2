#!/usr/bin/env python3
from google.cloud import firestore
import json

db = firestore.Client()

# Get the most recent case
cases_ref = db.collection('cases')
query = cases_ref.order_by('createdAt', direction=firestore.Query.DESCENDING).limit(1)

for doc in query.stream():
    case_data = doc.to_dict()
    print(f"\n最新案例 ID: {doc.id}")
    print(f"狀態: {case_data.get('status')}")
    print(f"建立時間: {case_data.get('createdAt')}")
    
    # Check transcription
    if 'transcription' in case_data:
        trans = case_data['transcription']
        print(f"\n轉錄狀態:")
        print(f"  - 文字長度: {len(trans.get('text', ''))} 字元")
        print(f"  - 片段數: {len(trans.get('segments', []))}")
        print(f"  - 說話者: {trans.get('speakers', [])}")
    
    # Check analysis results
    if 'analysisResults' in case_data:
        print(f"\n分析結果:")
        for agent_key, agent_data in case_data['analysisResults'].items():
            print(f"  - {agent_key}: {agent_data.get('status', 'unknown')}")
    
    # Check if Slack was notified
    if 'slackNotified' in case_data:
        print(f"\nSlack 通知: {case_data.get('slackNotified')}")
    
    print(f"\n完整資料:")
    print(json.dumps(case_data, indent=2, default=str, ensure_ascii=False))
