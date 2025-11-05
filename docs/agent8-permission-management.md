# Agent 8 權限管理文檔

**最後更新**：2025-11-04

---

## 概述

Agent 8 是業務主管專屬的智能助理，僅開放給有權限的主管使用。權限資訊儲存在 Firestore 的 `users` Collection 中。

---

## Firestore Schema

### Collection: `users`

每個用戶的權限資訊儲存在獨立的 Document 中，Document ID 為 Slack User ID。

**Document ID**: `{slack_user_id}`

**欄位**：

```json
{
  "userId": "U12345678",          // Slack User ID
  "role": "manager",               // 角色：manager, admin, user
  "name": "王大明",                // 用戶名稱
  "email": "wang@example.com",     // Email
  "department": "業務部",          // 部門
  "createdAt": "2025-11-04T...",   // 建立時間
  "updatedAt": "2025-11-04T..."    // 更新時間
}
```

### 角色說明

| 角色 | 說明 | 權限 |
|------|------|------|
| `admin` | 系統管理員 | 完整權限，可使用 Agent 8 |
| `manager` | 業務主管 | 可使用 Agent 8 |
| `user` | 一般用戶 | 無法使用 Agent 8 |

---

## 添加主管權限

### 方法 1：使用 Firestore Console（推薦）

1. 前往 [Firestore Console](https://console.cloud.google.com/firestore)
2. 選擇 `users` Collection
3. 點擊「新增文件」
4. 輸入以下資訊：
   - **文件 ID**: Slack User ID（例如：`U12345678`）
   - **欄位**：
     ```
     userId: U12345678
     role: manager
     name: 王大明
     email: wang@example.com
     department: 業務部
     createdAt: [自動時間戳記]
     updatedAt: [自動時間戳記]
     ```
5. 點擊「儲存」

### 方法 2：使用 Python Script

創建檔案 `scripts/add_manager.py`：

```python
#!/usr/bin/env python3
"""
添加 Agent 8 主管權限
"""

from google.cloud import firestore
from datetime import datetime
import sys

def add_manager(user_id: str, name: str, email: str, department: str = "業務部"):
    """
    添加主管權限

    Args:
        user_id: Slack User ID
        name: 用戶名稱
        email: Email
        department: 部門
    """
    db = firestore.Client()

    user_data = {
        "userId": user_id,
        "role": "manager",
        "name": name,
        "email": email,
        "department": department,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }

    db.collection("users").document(user_id).set(user_data)

    print(f"✅ 已添加主管權限：{name} ({user_id})")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法：python add_manager.py <user_id> <name> <email> [department]")
        print("範例：python add_manager.py U12345678 王大明 wang@example.com 業務部")
        sys.exit(1)

    user_id = sys.argv[1]
    name = sys.argv[2]
    email = sys.argv[3]
    department = sys.argv[4] if len(sys.argv) > 4 else "業務部"

    add_manager(user_id, name, email, department)
```

**執行**：

```bash
python scripts/add_manager.py U12345678 王大明 wang@example.com 業務部
```

---

## 查詢 Slack User ID

### 方法 1：使用 Slack App（最簡單）

1. 在 Slack 中，點擊用戶頭像
2. 選擇「檢視個人檔案」
3. 點擊「更多」→「複製成員 ID」

### 方法 2：使用 Slack API

```python
from slack_sdk import WebClient
import os

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

# 使用 Email 查詢
response = client.users_lookupByEmail(email="wang@example.com")
user_id = response["user"]["id"]
print(f"User ID: {user_id}")
```

---

## 移除主管權限

### 方法 1：刪除 Document（完全移除）

```python
from google.cloud import firestore

db = firestore.Client()
db.collection("users").document("U12345678").delete()
print("✅ 已移除權限")
```

### 方法 2：更改角色（保留記錄）

```python
from google.cloud import firestore
from datetime import datetime

db = firestore.Client()
db.collection("users").document("U12345678").update({
    "role": "user",
    "updatedAt": datetime.utcnow()
})
print("✅ 已更改為 user 角色")
```

---

## 批量添加主管

創建 CSV 檔案 `managers.csv`：

```csv
user_id,name,email,department
U12345678,王大明,wang@example.com,業務部
U87654321,陳美玲,chen@example.com,業務部
U11223344,李大華,lee@example.com,業務部
```

執行批量添加腳本：

```python
#!/usr/bin/env python3
"""
批量添加主管權限
"""

import csv
from google.cloud import firestore
from datetime import datetime

def batch_add_managers(csv_file: str):
    """
    從 CSV 批量添加主管

    Args:
        csv_file: CSV 檔案路徑
    """
    db = firestore.Client()
    batch = db.batch()

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0

        for row in reader:
            user_ref = db.collection("users").document(row["user_id"])
            user_data = {
                "userId": row["user_id"],
                "role": "manager",
                "name": row["name"],
                "email": row["email"],
                "department": row.get("department", "業務部"),
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
            batch.set(user_ref, user_data)
            count += 1

        batch.commit()
        print(f"✅ 已添加 {count} 位主管")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法：python batch_add_managers.py <csv_file>")
        sys.exit(1)

    batch_add_managers(sys.argv[1])
```

---

## 驗證權限

測試用戶是否有權限：

```python
from google.cloud import firestore

def check_permission(user_id: str) -> bool:
    """
    檢查用戶權限

    Args:
        user_id: Slack User ID

    Returns:
        是否有權限
    """
    db = firestore.Client()
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        return False

    user_data = user_doc.to_dict()
    return user_data.get("role") in ["manager", "admin"]


# 測試
user_id = "U12345678"
has_permission = check_permission(user_id)
print(f"User {user_id} 權限：{'✅ 有' if has_permission else '❌ 無'}")
```

---

## 常見問題

### Q1: 為什麼用戶收到「沒有權限」訊息？

**檢查步驟**：
1. 確認 Slack User ID 正確
2. 確認 Firestore 中有該用戶的 Document
3. 確認 `role` 欄位為 `manager` 或 `admin`
4. 檢查 Cloud Run 環境變數 `GCP_PROJECT_ID` 是否正確

### Q2: 如何查看所有有權限的主管？

```python
from google.cloud import firestore

db = firestore.Client()
docs = db.collection("users").where("role", "in", ["manager", "admin"]).stream()

print("有權限的主管：")
for doc in docs:
    data = doc.to_dict()
    print(f"- {data['name']} ({data['userId']})")
```

### Q3: 權限變更需要多久生效？

**立即生效**。每次用戶使用 `/ask-agent8` 命令時都會即時查詢 Firestore 確認權限。

---

## 安全建議

1. **最小權限原則**：只給需要的主管開放權限
2. **定期審查**：每季度檢查權限清單
3. **日誌監控**：監控 Agent 8 使用日誌，發現異常立即處理
4. **備份權限清單**：定期導出權限清單備份

---

## 監控與日誌

### 查看 Agent 8 使用日誌

Cloud Run 日誌中會記錄：
- 權限檢查結果
- 用戶提問
- 回答成功/失敗

**查詢日誌**：

```bash
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"Agent 8\"" \
  --limit 50 \
  --format json
```

---

## 相關文檔

- [Agent 8 用戶使用指南](./agent8-user-guide.md)
- [Agent 8 開發文檔](../specs/001-sales-ai-automation/AGENT8_CONVERSATIONAL.md)
- [POC 8 測試報告](../specs/001-sales-ai-automation/poc-tests/poc8_agent8_conversational/POC8_REPORT.md)
