# Cloud Tasks MCP Tool Wrapper

## 概述

這個 MCP Server 提供了 Google Cloud Tasks 的簡化操作介面，減少重複程式碼並標準化任務建立模式。

## 功能

### 1. `cloud_tasks_create_http_task`

建立一個通用的 HTTP POST 任務。

**參數**:

- `project` (必須): GCP 專案 ID
- `location` (必須): 佇列位置 (例如 'asia-east1')
- `queue` (必須): 佇列名稱
- `url` (必須): 目標 URL
- `payload` (必須): JSON payload
- `service_account_email` (可選): 驗證用的服務帳號
- `schedule_seconds` (可選): 延遲執行的秒數，預設為 0
- `task_name` (可選): 自訂任務名稱

**範例**:

```python
# 使用 MCP tool (透過 Claude Code)
result = mcp__cloud_tasks.create_http_task(
    project="sales-ai-automation-v2",
    location="asia-east1",
    queue="my-queue",
    url="https://my-service.run.app/process",
    payload={"key": "value"},
    service_account_email="my-sa@project.iam.gserviceaccount.com"
)
```

### 2. `cloud_tasks_create_transcription_task`

建立轉錄任務（專案特定的簡化版本）。

**參數**:

- `case_id` (必須): Firestore case 文件 ID
- `gcs_path` (必須): GCS 音檔路徑 (例如 'gs://bucket/path/file.mp3')
- `project` (可選): 預設為 'sales-ai-automation-v2'
- `location` (可選): 預設為 'asia-east1'
- `queue` (可選): 預設為 'transcription-queue'
- `service_url` (可選): 覆寫轉錄服務 URL
- `service_account` (可選): 覆寫服務帳號

**範例**:

```python
# 使用 MCP tool (最簡化)
result = mcp__cloud_tasks.create_transcription_task(
    case_id="CASE123",
    gcs_path="gs://my-bucket/audio/sample.mp3"
)
```

**對比原始寫法**:

```python
# 原始寫法 (需要 15-20 行)
from google.cloud import tasks_v2

client = tasks_v2.CloudTasksClient()
queue_path = client.queue_path("sales-ai-automation-v2", "asia-east1", "transcription-queue")
task = {
    "http_request": {
        "http_method": tasks_v2.HttpMethod.POST,
        "url": "https://transcription-service-497329205771.asia-east1.run.app/transcribe",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"caseId": "CASE123", "gcsPath": "gs://..."}).encode(),
        "oidc_token": {
            "service_account_email": "497329205771-compute@developer.gserviceaccount.com"
        }
    }
}
response = client.create_task(request={"parent": queue_path, "task": task})

# MCP 簡化寫法 (1 行)
result = mcp__cloud_tasks.create_transcription_task(case_id="CASE123", gcs_path="gs://...")
```

### 3. `cloud_tasks_create_analysis_task`

建立分析任務（專案特定的簡化版本）。

**參數**:

- `case_id` (必須): Firestore case 文件 ID
- `project` (可選): 預設為 'sales-ai-automation-v2'
- `location` (可選): 預設為 'asia-east1'
- `queue` (可選): 預設為 'analysis-queue'
- `service_url` (可選): 覆寫分析服務 URL
- `service_account` (可選): 覆寫服務帳號

**範例**:

```python
# 使用 MCP tool
result = mcp__cloud_tasks.create_analysis_task(case_id="CASE123")
```

### 4. `cloud_tasks_list_tasks`

列出佇列中的任務。

**參數**:

- `project` (必須): GCP 專案 ID
- `location` (必須): 佇列位置
- `queue` (必須): 佇列名稱
- `limit` (可選): 最多返回的任務數量，預設為 10

**範例**:

```python
# 使用 MCP tool
result = mcp__cloud_tasks.list_tasks(
    project="sales-ai-automation-v2",
    location="asia-east1",
    queue="transcription-queue",
    limit=20
)
```

## 安裝

### 方法 1: 使用建置腳本

```bash
cd /path/to/sales-ai-automation-V2
./scripts/setup_mcp_infrastructure.sh
```

### 方法 2: 手動配置

1. 確保 `tools/cloud_tasks/mcp_server.py` 存在

2. 在 `~/.claude/mcp_config.json` 中加入:

```json
{
  "mcpServers": {
    "cloud_tasks": {
      "command": "python3",
      "args": ["/path/to/sales-ai-automation-V2/tools/cloud_tasks/mcp_server.py"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/credentials.json",
        "GCP_PROJECT": "sales-ai-automation-v2"
      },
      "disabled": false
    }
  }
}
```

3. 重啟 Claude Code

## 測試

```bash
# 測試 MCP server 是否正常運作
echo '{"method": "tools/list"}' | python3 tools/cloud_tasks/mcp_server.py

# 應該返回 4 個工具的定義
```

## Token 節省效果

| 操作 | 原始寫法 | MCP 簡化 | 節省 |
|------|---------|---------|------|
| 建立 transcription task | ~800 tokens | ~150 tokens | 81% |
| 建立 analysis task | ~700 tokens | ~120 tokens | 83% |
| 列出佇列任務 | ~600 tokens | ~100 tokens | 83% |
| 建立自訂 HTTP task | ~900 tokens | ~200 tokens | 78% |

## 與現有程式碼整合

### 替代 `trigger_analysis.py`

**原本**:

```python
# trigger_analysis.py - 60 行
import sys
from google.cloud import tasks_v2
# ... 省略 ...

def create_analysis_task(case_id: str, project_id: str = "sales-ai-automation-v2"):
    client = tasks_v2.CloudTasksClient()
    # ... 省略 15 行 ...
    response = client.create_task(request={"parent": queue_path, "task": task})
    return response
```

**使用 MCP 後**:

```python
# 在 Claude Code 對話中
result = mcp__cloud_tasks.create_analysis_task(case_id="CASE123")
print(result)
```

### 替代 `file_pipeline.py` 中的 `enqueue_transcription_task`

**原本**:

```python
# file_pipeline.py
def enqueue_transcription_task(case_id: str, gcs_path: str):
    client = tasks_v2.CloudTasksClient()
    queue_path = client.queue_path(...)
    # ... 省略 20 行 ...
```

**使用 MCP 後**:

```python
# 在 Claude Code 對話中執行
result = mcp__cloud_tasks.create_transcription_task(
    case_id=case_id,
    gcs_path=gcs_path
)
```

## 錯誤處理

所有函式都會返回標準化的結果格式：

**成功**:

```json
{
  "success": true,
  "task_name": "projects/.../locations/.../queues/.../tasks/...",
  "schedule_time": "2025-11-11T12:00:00",
  "queue": "...",
  "url": "...",
  "payload": {...}
}
```

**失敗**:

```json
{
  "error": "Error message here",
  "success": false
}
```

## 最佳實踐

1. **使用專案特定函式**: 優先使用 `create_transcription_task` 和 `create_analysis_task`，它們已包含專案預設值
2. **批次操作**: 如需建立多個任務，考慮在主對話中使用迴圈呼叫 MCP tool
3. **錯誤處理**: 總是檢查返回的 `success` 欄位

## 相關文件

- [QUICK_START_FOR_AI.md](../../QUICK_START_FOR_AI.md) - MCP 使用指南
- [TOKEN_OPTIMIZATION_GUIDE.md](../../TOKEN_OPTIMIZATION_GUIDE.md) - Token 優化策略
- [Google Cloud Tasks 文件](https://cloud.google.com/tasks/docs)
