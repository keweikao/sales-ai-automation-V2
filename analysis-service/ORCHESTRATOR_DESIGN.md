# Multi-Agent Orchestrator 錯誤處理設計

## 工作流程確認

### 完整流程

```
1. 音檔上傳 (Slack/GCS)
   ↓
2. Transcription Service
   - Whisper 轉錄 + Diarization
   - 寫入 Firestore: transcript + speakers
   - 觸發 Cloud Tasks (analysis-queue)
   ↓
3. Analysis Service (本模組)
   - 從 Firestore 讀取「完成的」transcript
   - 平行執行 Agent 1-5
   - 依序執行 Agent 6-7
   - 寫入結果到 Firestore
   - 觸發 Slack 通知
```

**✅ 確認：轉錄在 Agent 執行前已完成**

## 錯誤處理策略

### 根據需求規格 (FR-019a, FR-028, FR-029)

1. **FR-019a**: System MUST handle agent failures gracefully (continue with partial results)
2. **FR-028**: Auto-retry up to 3 times with exponential backoff (60s, 120s, 240s)
3. **FR-029**: Distinguish retryable vs non-retryable errors

### 採用策略：Graceful Degradation（容錯模式）

#### Agent 1-5 執行策略

- ✅ 平行執行所有 5 個 Agents
- ✅ 即使部分失敗，仍繼續執行其他
- ✅ 收集「部分結果」
- ✅ 標記哪些 Agent 失敗

#### Agent 6 執行條件

```python
if at_least_3_agents_succeeded:
    # 執行 Agent 6，但標註缺失的分析
    agent6_result = run_agent6(
        available_results=successful_agent_results,
        missing_agents=failed_agent_ids
    )
else:
    # 少於 3 個 Agent 成功，資訊不足
    raise InsufficientDataError("Need at least 3/5 agents to succeed")
```

**理由**：

- Agent 6 需要「足夠的資訊」來合成建議
- 5個中至少3個成功 = 60% 資訊完整度（可接受）
- Agent 6 prompt 會被告知哪些資訊缺失

#### Agent 7 執行條件

```python
if agent6_succeeded:
    # Agent 7 依賴 Agent 6 的合成結果
    agent7_result = run_agent7(
        agent6_output=agent6_result,
        available_agent_results=successful_agent_results
    )
```

## 重試機制

### Cloud Tasks 層級重試（推薦）

```yaml
# Cloud Tasks queue configuration
retryConfig:
  maxAttempts: 3
  minBackoff: 60s
  maxBackoff: 240s
  maxDoublings: 2
```

**適用場景**：

- 整個分析任務失敗（< 3 個 Agent 成功）
- Firestore 讀取失敗
- 網路超時

### Agent 層級重試（個別 Agent 內部）

```python
async def _run_agent_with_retry(
    self,
    agent_id: str,
    max_retries: int = 2,  # Agent 內部重試 2 次
    ...
):
    for attempt in range(max_retries + 1):
        try:
            result = await self._run_agent_async(...)
            return result
        except RetryableError as e:
            if attempt < max_retries:
                await asyncio.sleep(5 * (2 ** attempt))  # 5s, 10s
                continue
            return AgentResult(success=False, error=str(e))
```

**適用場景**：

- Gemini API 速率限制 (429)
- 暫時性網路錯誤
- JSON 解析失敗（LLM 輸出格式錯誤）

### 不重試場景

- API Key 無效 (401)
- 無效的 transcript 格式
- 程式邏輯錯誤 (500)

## 失敗通知策略

### Slack 通知內容

```
✅ 分析完成（部分成功）

✅ 參與者分析: 成功
✅ 情緒分析: 成功
❌ 需求提取: 失敗（API 超時）
✅ 競品分析: 成功
❌ 問卷分析: 失敗（格式解析錯誤）

⚠️ 由於部分分析失敗，合成建議可能不完整。
已自動重試 2 次，仍無法完成。

[查看詳細日誌] [重新執行分析]
```

## Firestore 資料結構

### 儲存部分結果

```json
{
  "caseId": "CASE123",
  "analysis": {
    "status": "partial_success",
    "completedAt": "2025-11-06T10:30:00Z",
    "totalDuration": 45.2,
    "agents": {
      "agent1": {
        "status": "success",
        "duration": 28.5,
        "data": { ... }
      },
      "agent2": {
        "status": "success",
        "duration": 22.1,
        "data": { ... }
      },
      "agent3": {
        "status": "failed",
        "duration": 15.3,
        "error": "Gemini API rate limit exceeded",
        "retryCount": 2
      },
      "agent4": {
        "status": "success",
        "duration": 20.8,
        "data": { ... }
      },
      "agent5": {
        "status": "failed",
        "duration": 10.5,
        "error": "JSON parsing failed",
        "retryCount": 2
      }
    },
    "agent6": {
      "status": "success",
      "duration": 18.2,
      "data": { ... },
      "missingInputs": ["agent3", "agent5"],
      "completenessScore": 0.6
    }
  }
}
```

## 實作檢查清單

- [x] Phase 1: 基礎 orchestrator 完成
- [ ] Phase 1.5: 增強錯誤處理
  - [ ] 添加 `min_success_threshold` 參數（預設 3/5）
  - [ ] Agent 層級重試邏輯
  - [ ] 區分 retryable vs non-retryable errors
  - [ ] 詳細的失敗日誌
- [ ] Phase 2: Main.py endpoint 整合
  - [ ] Firestore transcript 讀取
  - [ ] 呼叫 orchestrator
  - [ ] 處理部分失敗情況
  - [ ] 寫入結果到 Firestore
- [ ] Phase 4: Agent 6-7 整合
  - [ ] Agent 6 接收 partial results
  - [ ] Agent 6 prompt 註明缺失資訊
  - [ ] Agent 7 依賴 Agent 6 輸出

## 決策點

### Q: Agent 6 是否應該在部分失敗時執行？

**A: 是，但有條件**

- ✅ 至少 3/5 Agents 成功
- ✅ Agent 6 被告知哪些資訊缺失
- ✅ Slack 通知標註「部分成功」

### Q: 重試應該在哪一層？

**A: 兩層都要**

1. **Agent 層級**：快速重試 (5s, 10s) - 處理暫時性錯誤
2. **Task 層級**：Cloud Tasks 重試 (60s, 120s, 240s) - 處理整體失敗

### Q: 失敗後是否應該通知使用者？

**A: 是，透過 Slack**

- 部分成功：通知但標註缺失
- 完全失敗：通知並提供重試按鈕
- 自動重試：不通知，只記錄日誌
