# Slack App Integration Guide

完成 Task 6.1, 6.2, 6.3 的整合指南

## 📋 目錄

- [新增功能](#新增功能)
- [文件結構](#文件結構)
- [整合步驟](#整合步驟)
- [使用範例](#使用範例)
- [測試指南](#測試指南)

---

<a id="新增功能"></a>

## 🎯 新增功能

### Task 6.1: Agent 6 結果顯示

**功能**: 在 Slack 中顯示銷售分析報告（Agent 6）

**特色**:

- 📊 銷售階段顯示
- 🎯 成交健康度評分
- 👥 關鍵決策者列表
- ⚠️ 風險因素提示
- 🎯 建議下一步行動

**檔案**:

- `notifications/agent6_notifier.py`
- `templates/agent6_card.json`

---

### Task 6.2: Agent 7 摘要預覽與按鈕

**功能**: 顯示客戶摘要預覽並提供互動按鈕

**特色**:

- 📝 摘要預覽（前 500 字元）
- ✏️ 編輯按鈕
- 👁️ 完整預覽按鈕
- ✅ 確認送出按鈕
- 📊 字數統計

**檔案**:

- `notifications/agent7_notifier.py`

---

### Task 6.3: 摘要編輯功能

**功能**: 編輯客戶摘要並追蹤修改歷史

**特色**:

- ✏️ Modal 編輯器（支援 Markdown）
- 📝 即時儲存到 Firestore
- 📚 編輯歷史記錄
- ✅ 字數限制驗證（3000 字元）
- 🔄 自動更新預覽訊息

**檔案**:

- `interactions/summary_editor.py`

---

<a id="文件結構"></a>

## 📁 文件結構

```
src/slack_app/
├── notifications/
│   ├── __init__.py
│   ├── agent6_notifier.py      # Task 6.1
│   └── agent7_notifier.py      # Task 6.2
├── interactions/
│   ├── __init__.py
│   └── summary_editor.py       # Task 6.3
├── templates/
│   └── agent6_card.json        # Agent 6 卡片模板
├── integration_example.py      # 整合範例
└── INTEGRATION_README.md       # 本文件
```

---

<a id="整合步驟"></a>

## 🔧 整合步驟

### 步驟 1: 安裝依賴

確保已安裝以下套件：

```bash
pip install slack-bolt slack-sdk google-cloud-firestore
```

### 步驟 2: 環境變數

在 `.env` 或環境中設定：

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token  # For Socket Mode
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### 步驟 3: 匯入模組

在你的主程式中（`main.py` 或 `app.py`）：

```python
from notifications.agent6_notifier import Agent6Notifier
from notifications.agent7_notifier import Agent7Notifier
from interactions.summary_editor import SummaryEditor

# 初始化
agent6_notifier = Agent6Notifier(slack_client, db_client)
agent7_notifier = Agent7Notifier(slack_client, db_client)
summary_editor = SummaryEditor(slack_client, db_client)
```

### 步驟 4: 註冊 Action Handlers

```python
# Task 6.3: 編輯按鈕
@app.action("edit_summary")
def handle_edit_summary(ack, body, logger):
    ack()
    trigger_id = body["trigger_id"]
    case_id = body["actions"][0]["value"].replace("edit_summary_", "")
    summary_editor.open_edit_modal(trigger_id, case_id)

# Task 6.3: 預覽按鈕
@app.action("preview_summary")
def handle_preview_summary(ack, body, logger):
    ack()
    trigger_id = body["trigger_id"]
    case_id = body["actions"][0]["value"].replace("preview_summary_", "")
    summary_editor.open_preview_modal(trigger_id, case_id)

# Task 6.3: Modal 提交
@app.view("edit_summary_modal")
def handle_edit_submission(ack, body, view, logger):
    user_id = body["user"]["id"]
    response = summary_editor.handle_modal_submission(view, user_id)
    ack(response)

# Task 6.2: 確認送出
@app.action("confirm_send_summary")
def handle_confirm_send(ack, body, logger):
    ack()
    case_id = body["actions"][0]["value"].replace("confirm_send_", "")
    # TODO: 實作 Task 6.5, 6.6, 6.7（網頁生成 + SMS）
    pass
```

### 步驟 5: 在分析完成時觸發

在你的分析服務完成後調用：

```python
# 當 Agent 1-7 全部完成時
def on_analysis_complete(case_id: str, user_id: str):
    # 發送 Agent 6 結果
    agent6_notifier.send_agent6_notification(
        case_id=case_id,
        user_id=user_id
    )

    # 發送 Agent 7 預覽
    agent7_notifier.send_agent7_preview(
        case_id=case_id,
        user_id=user_id
    )
```

---

<a id="使用範例"></a>

## 💡 使用範例

### 範例 1: 發送 Agent 6 通知

```python
from notifications.agent6_notifier import Agent6Notifier

agent6 = Agent6Notifier(slack_client, db_client)

# 發送通知
success = agent6.send_agent6_notification(
    case_id="CASE_20251110_001",
    user_id="U01234567",
    thread_ts="1699600000.123456"  # Optional: 回覆到特定 thread
)
```

### 範例 2: 發送 Agent 7 預覽

```python
from notifications.agent7_notifier import Agent7Notifier

agent7 = Agent7Notifier(slack_client, db_client)

# 發送預覽
success = agent7.send_agent7_preview(
    case_id="CASE_20251110_001",
    user_id="U01234567",
    is_edited=False  # 標記是否已編輯
)
```

### 範例 3: 開啟編輯 Modal

```python
from interactions.summary_editor import SummaryEditor

editor = SummaryEditor(slack_client, db_client)

# 開啟編輯 Modal
success = editor.open_edit_modal(
    trigger_id="12345.67890.abcdef",
    case_id="CASE_20251110_001"
)
```

### 範例 4: 完整流程

詳見 `integration_example.py` 中的 `example_complete_analysis_flow()` 函數

---

<a id="測試指南"></a>

## 🧪 測試指南

### 單元測試範例

```python
import pytest
from unittest.mock import Mock, patch
from notifications.agent6_notifier import Agent6Notifier

def test_build_agent6_blocks():
    """測試 Agent 6 block 構建"""
    slack_client = Mock()
    db_client = Mock()
    notifier = Agent6Notifier(slack_client, db_client)

    agent6_data = {
        'salesStage': {'currentStage': '需求探索', 'confidence': 85},
        'dealHealth': {'score': 75, 'status': '中等健康'},
        'keyDecisionMakers': [
            {'name': '張經理', 'role': '決策者', 'influenceLevel': '高'}
        ],
        'nextSteps': [
            {'action': '安排產品展示', 'priority': 'high'}
        ]
    }

    blocks = notifier.build_agent6_blocks(
        case_id="TEST_001",
        agent6_data=agent6_data,
        case_metadata={'storeName': '測試餐廳', 'customerId': 'C001'}
    )

    assert len(blocks) > 0
    assert blocks[0]['type'] == 'header'
```

### 整合測試

```python
# Test in development Slack workspace
def test_integration():
    """整合測試：發送完整通知流程"""
    case_id = "TEST_CASE_001"
    user_id = "U01234567"  # Your Slack user ID

    # 確保 Firestore 有測試資料
    # ... setup test data ...

    # 測試 Agent 6
    success_6 = agent6_notifier.send_agent6_notification(case_id, user_id)
    assert success_6

    # 測試 Agent 7
    success_7 = agent7_notifier.send_agent7_preview(case_id, user_id)
    assert success_7
```

---

## 📊 Firestore 資料結構

### Agent 6 結果

```json
{
  "analysis": {
    "agents": {
      "agent6": {
        "status": "success",
        "data": {
          "salesStage": {
            "currentStage": "需求探索",
            "confidence": 85
          },
          "dealHealth": {
            "score": 75,
            "status": "中等健康"
          },
          "keyDecisionMakers": [
            {
              "name": "張經理",
              "role": "決策者",
              "influenceLevel": "高"
            }
          ],
          "nextSteps": [
            {
              "action": "安排產品展示",
              "priority": "high"
            }
          ],
          "riskFactors": [
            {
              "description": "預算考量"
            }
          ]
        },
        "notificationSentAt": "2025-11-10T10:00:00Z"
      }
    }
  }
}
```

### Agent 7 摘要

```json
{
  "analysis": {
    "customerSummary": {
      "markdown": "# 會議摘要\n\n感謝您...",
      "isEdited": true,
      "editCount": 2,
      "lastEditedAt": "2025-11-10T11:00:00Z",
      "editedBy": "U01234567",
      "editHistory": [
        {
          "previousContent": "...",
          "editedAt": "2025-11-10T10:30:00Z",
          "editedBy": "U01234567",
          "changes": {
            "charactersDiff": 50
          }
        }
      ],
      "previewSentAt": "2025-11-10T10:00:00Z"
    }
  }
}
```

---

## 🚀 下一步

完成 Task 6.1-6.3 後，繼續實作：

- **Task 6.4**: 完整預覽功能（已實作在 `summary_editor.py`）
- **Task 6.5**: 摘要網頁生成
- **Task 6.6**: SMS 發送整合
- **Task 6.7**: 確認送出流程

---

## 📝 注意事項

1. **Thread 追蹤**: 建議在發送 Agent 6/7 通知時使用相同的 `thread_ts`，讓所有通知集中在一個 thread 中
2. **錯誤處理**: 所有函數都有完整的錯誤處理和日誌記錄
3. **Transaction**: 摘要編輯使用 Firestore transaction 確保資料一致性
4. **字數限制**: 摘要編輯限制 3000 字元，可根據需求調整

---

## 🐛 故障排除

### 問題 1: Modal 無法開啟

**解決方案**: 檢查 `trigger_id` 是否有效（有效期僅 3 秒）

### 問題 2: Firestore 更新失敗

**解決方案**: 確認 case_id 存在且資料結構正確

### 問題 3: Slack 通知未送達

**解決方案**: 檢查 Bot Token 權限（chat:write, users:read）

---

## 📞 支援

如有問題，請查看：

- `integration_example.py` - 完整範例
- 測試檔案 - 單元測試範例
- Slack API 文件: <https://api.slack.com/block-kit>

---

**更新日期**: 2025-11-10
**版本**: 1.0.0
**作者**: Claude Code
