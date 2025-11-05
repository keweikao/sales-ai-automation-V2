# Agent 8 Manager Access Enablement

> 目的：協助系統管理員快速為指定 Slack 使用者開通 Agent 8 權限，並驗證 Firestore 連線是否正常。

---

## 1. 先決條件

- 已安裝並登入 `gcloud`，專案設為 `sales-ai-automation-v2`。

  ```bash
  gcloud config set project sales-ai-automation-v2
  gcloud auth login
  ```
- 具備可讀寫 Firestore 的服務帳號或個人權限。若使用服務帳號，請將憑證 JSON 路徑輸出為環境變數：

  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
  ```
- 確認 Slack 使用者 ID（格式如 `U12345678`），可透過 Slack 使用者個人資訊檢視。

---

## 2. 建立/更新 Firestore 主管文件

Agent 8 會在 `users/{SlackUserId}` 文件中檢查 `role` 欄位，僅 `manager` 或 `admin` 具備權限。以下提供兩種方式：

### 方式 A：使用 gcloud CLI

```bash
SLACK_ID="U12345678"
MANAGER_NAME="王大明"
MANAGER_EMAIL="daming@example.com"
UNIT="IC"

gcloud firestore documents create users/${SLACK_ID} \
  --fields="role=manager,name=${MANAGER_NAME},email=${MANAGER_EMAIL},unit=${UNIT}" \
  --project=sales-ai-automation-v2

# 若文件已存在可改用 update 指令
gcloud firestore documents update users/${SLACK_ID} \
  --update-mask=role,name,email,unit \
  --fields="role=manager,name=${MANAGER_NAME},email=${MANAGER_EMAIL},unit=${UNIT}" \
  --project=sales-ai-automation-v2
```

### 方式 B：使用 Python 腳本

```python
from google.cloud import firestore

SLACK_ID = "U12345678"

payload = {
    "role": "manager",
    "name": "王大明",
    "email": "daming@example.com",
    "unit": "IC"
}

db = firestore.Client(project="sales-ai-automation-v2")
db.collection("users").document(SLACK_ID).set(payload, merge=True)
print(f"✅ 已更新 users/{SLACK_ID}")
```

> 建議：建立或更新後，請在 `DEVELOPMENT_LOG.md` 新增 Session 記錄，並在 Outstanding Work Tracker 勾選「建立 Firestore 主管權限資料」。

---

## 3. 驗證權限

### 3.1 透過 API 測試

```python
from google.cloud import firestore

def has_agent8_access(slack_id: str) -> bool:
    db = firestore.Client(project="sales-ai-automation-v2")
    doc = db.collection("users").document(slack_id).get()
    if not doc.exists:
        return False
    role = doc.to_dict().get("role", "")
    return role in {"manager", "admin"}

print(has_agent8_access("U12345678"))
```

### 3.2 Slack 實測

1. 在已授權帳號中輸入 `/ask-agent8 今天團隊表現如何？`。  
2. 若看到 🤔 等待訊息並收到回答，即表示授權成功。  
3. 未授權帳號會收到 `❌ 抱歉，您沒有使用 Agent 8 的權限。`

---

## 4. Firestore 連線檢查

若需要確認應用程式可直接連線 Firestore，可執行下列指令：

```bash
# 驗證服務帳號是否可讀寫
python - <<'PY'
from google.cloud import firestore

db = firestore.Client(project="sales-ai-automation-v2")
test_ref = db.collection("_connectivity_checks").document("agent8_access")
test_ref.set({"connected": True}, merge=True)
print("✅ Firestore 連線成功")
PY
```

完成後，可選擇刪除 `_connectivity_checks/agent8_access` 測試文件：

```bash
gcloud firestore documents delete _connectivity_checks/agent8_access --project=sales-ai-automation-v2
```

---

## 5. 常見問題

| 問題 | 解法 |
|------|------|
| `/ask-agent8` 仍提示無權限 | 再次確認 Firestore 文件 ID 是否為 Slack 使用者 ID、`role` 是否設定為 `manager`/`admin`，並確保部署環境對應的服務帳號有讀取權限。 |
| CLI 顯示 `PERMISSION_DENIED` | 確認當前 gcloud 身份是否具備 `roles/datastore.user` 或更高權限。 |
| Python 腳本連線失敗 | 檢查 `GOOGLE_APPLICATION_CREDENTIALS` 路徑是否正確、專案 ID 是否為 `sales-ai-automation-v2`。 |

---

## 6. 將 Agent 1–7 分析結果寫入 Firestore

以下腳本會將現有測試輸出（位於 `analysis-service/tests`）映射到 `cases/{CASE_ID}` 的 `analysis` 欄位，便於本地或 Cloud Run 環境驗證整個流程。請先依需求調整 `CASE_ID` 與其他欄位。

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export GCP_PROJECT_ID=sales-ai-automation-v2

python - <<'PY'
import json
from pathlib import Path
from datetime import datetime, timezone
from google.cloud import firestore

PROJECT = "sales-ai-automation-v2"
CASE_ID = "CASE-SAMPLE-001"   # TODO: 改成實際 caseId（也是文件 ID）
TRANSCRIPT_PATH = Path("test-data/transcripts/test_01_positive_qr_ordering.txt")

# 載入各 Agent 測試輸出
base_payload = json.loads(Path("analysis-service/tests/samples/sample_agent_inputs.json").read_text(encoding="utf-8"))
agent_outputs = base_payload["agentOutputs"]

agent6 = json.loads(Path("analysis-service/tests/fixtures/agent67/agent6_structured.json").read_text(encoding="utf-8"))
agent7 = json.loads(Path("analysis-service/tests/fixtures/agent67/agent7_summary.json").read_text(encoding="utf-8"))

# Firestore 連線
db = firestore.Client(project=PROJECT)
case_ref = db.collection("cases").document(CASE_ID)

# 若文件不存在可先建立基礎欄位
case_ref.set(
    {
        "caseId": CASE_ID,
        "customerName": base_payload["customer"]["company"],
        "salesRepName": base_payload["customer"]["ichefRep"]["name"],
        "salesRepSlackId": "U_pending",  # TODO: 改成實際業務的 Slack ID
        "status": "analyzing",
        "createdAt": firestore.SERVER_TIMESTAMP,
        "analysis": {},
    },
    merge=True,
)

analysis_payload = {
    "participants": agent_outputs["agent1_participant"]["participants"],
    "sentiment": agent_outputs["agent2_sentiment"],
    "productNeeds": agent_outputs["agent3_product_needs"],
    "competitors": agent_outputs["agent4_competitor"]["topCompetitors"],
    "discoveryQuestionnaires": agent_outputs["agent5_questionnaire"]["questionnaires"],
    "structured": agent6["structured"],
    "rawOutput": agent6["rawOutput"],
    "customerSummary": agent7["customerSummary"],
    "agentExecutionLog": [
        {"agentId": "agent1", "status": "success", "completedAt": datetime.now(timezone.utc)},
        {"agentId": "agent2", "status": "success", "completedAt": datetime.now(timezone.utc)},
        {"agentId": "agent3", "status": "success", "completedAt": datetime.now(timezone.utc)},
        {"agentId": "agent4", "status": "success", "completedAt": datetime.now(timezone.utc)},
        {"agentId": "agent5", "status": "success", "completedAt": datetime.now(timezone.utc)},
        {"agentId": "agent6", "status": "success", "completedAt": datetime.now(timezone.utc)},
        {"agentId": "agent7", "status": "success", "completedAt": datetime.now(timezone.utc)},
    ],
}

# 將分析結果寫入
case_ref.set({"analysis": analysis_payload}, merge=True)
print(f"✅ 已更新 cases/{CASE_ID}.analysis")
PY
```

> 若要改用實際分析輸出，可將腳本中載入 JSON 的路徑換成真實檔案，或是由服務直接寫入。

### 驗證寫入內容

```bash
gcloud firestore documents describe cases/CASE-SAMPLE-001 --project=sales-ai-automation-v2
```

- 檢查 `analysis.participants` 等欄位是否已存在。  
- 可進一步在 Slack Flow 或 Cloud Run 服務中讀取同一份 case，驗證資料串接是否完成。

---

完成授權與資料寫入後，即可進入 Agent 8 的 Cloud Run 部署與整合測試流程。請務必在 `DEVELOPMENT_LOG.md` 紀錄此次操作並附上依據，再繼續後續開發。
