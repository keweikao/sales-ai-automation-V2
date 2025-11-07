#!/usr/bin/env python3
"""清除 Firestore 測試資料"""
import os
os.environ["GOOGLE_CLOUD_PROJECT"] = "sales-ai-automation-v2"

from google.cloud import firestore

db = firestore.Client()

print("🔍 查詢現有資料...")

# 查詢所有案件
cases = list(db.collection("cases").stream())
print(f"\n找到 {len(cases)} 個案件:")
for case in cases:
    data = case.to_dict()
    status = data.get('status', 'unknown')
    customer = data.get('customer', {})
    print(f"  - {case.id}: {customer.get('name', 'N/A')} (狀態: {status})")

# 查詢所有已處理檔案
files = list(db.collection("processed_files").stream())
print(f"\n找到 {len(files)} 個已處理檔案:")
for f in files:
    data = f.to_dict()
    status = data.get('status', 'unknown')
    filename = data.get('fileName', 'N/A')
    print(f"  - {f.id}: {filename} (狀態: {status})")

# 詢問是否刪除
print("\n" + "="*60)
response = input("是否要刪除所有資料? (yes/no): ").strip()

if response.lower() == "yes":
    print("\n🗑️  刪除案件...")
    for case in cases:
        case.reference.delete()
        print(f"  ✓ 刪除案件 {case.id}")

    print("\n🗑️  刪除已處理檔案...")
    for f in files:
        f.reference.delete()
        print(f"  ✓ 刪除檔案記錄 {f.id}")

    print("\n✅ 清理完成！")
else:
    print("\n❌ 取消清理")
