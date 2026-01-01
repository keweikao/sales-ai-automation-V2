"""
查看所有案件 (不依賴 createdAt 欄位)
"""
import os
from google.cloud import firestore

db = firestore.Client()
cases_ref = db.collection("cases")

print("🔍 查詢所有案件...")
print("=" * 70)

# Get all cases without ordering
cases = list(cases_ref.limit(20).stream())

if not cases:
    print("❌ 找不到任何案件")
    print("\n嘗試列出所有 collections...")
    # List root collections
    for collection in db.collections():
        print(f"  - {collection.id}")
else:
    print(f"找到 {len(cases)} 個案件:\n")
    
    # Sort by case_id locally
    case_list = []
    for doc in cases:
        data = doc.to_dict()
        case_list.append({
            'id': doc.id,
            'customerName': data.get('customerName', 'N/A'),
            'status': data.get('status', 'unknown'),
            'createdAt': data.get('createdAt', None)
        })
    
    # Sort by id descending
    case_list.sort(key=lambda x: x['id'], reverse=True)
    
    for i, case in enumerate(case_list, 1):
        print(f"{i}. {case['id']}")
        print(f"   客戶: {case['customerName']}")
        print(f"   狀態: {case['status']}")
        print(f"   建立: {case['createdAt']}")
        print()

print("=" * 70)
