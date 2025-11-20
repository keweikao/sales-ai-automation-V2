
# Agent 6 / Agent 7 分析說明（已拆分）

> 最新決策：Agent 6（內部銷售教練）與 Agent 7（客戶摘要）改為獨立執行與維護。  
> 本檔案提供用途對照與 Slack 展示示例，詳細 prompt 另見 `analysis-service/src/agents/prompts/`.

## 功能定位差異

| 項目 | Agent 6：Sales Coach Synthesizer | Agent 7：Customer Summary |
|------|----------------------------------|---------------------------|
| 受眾 | iCHEF 內部業務主管/銷售 | 客戶（以 Slack/匯出為主） |
| 主要輸出 | `analysis.structured`, `analysis.rawOutput` | `analysis.customerSummary` |
| 語氣 | 教練式、犀利、直指痛點 | 對客戶友好、行動明確 |
| 參考資料 | Transcript + Agents 1-5 | Transcript + Agents 1-6 |

## Firestore 寫入對應

```
cases/{caseId}/analysis/
├── structured (Agent 6)
├── rawOutput (Agent 6)
└── customerSummary (Agent 7)
```

## Slack 展示

- Agent 6：內部卡片（銷售健康度、風險、下一步行動）  
- Agent 7：客戶可讀摘要（重點決議、待辦、里程碑）

## Agent 6 JSON 契約重點

- `structured` 寫入 `cases/{caseId}/analysis.structured`，欄位須符合 `specs/001-sales-ai-automation/spec.md:642-657`：
  - `keyDecisionMaker`: 含 `name`、`role`、`primaryConcerns[]`（至少 1 筆）。
  - `dealHealth`: `score` 0-100、`sentiment` 只能 `positive|neutral|negative`、`reasoning` 需引用證據。
  - `recommendedBundle`: `products[]`（iCHEF 模組名）、`pricingStrategy`、`pricingDirection`（`below_baseline|match_baseline|above_baseline`）、`referencePoint`、`totalEstimate`（含 `currency|min|max|notes`）、`pricingNotes[]`（每筆含 `type` = `software|hardware`）。
  - `competitivePositioning`: 可為 `null`。
  - `salesStage`: 允許值 `立即報價型|需要證明型|教育培養型|時機未到型`。
  - `maximumRisk`: 需同時給 `risk` 與 `mitigation`。
  - `nextActions`: **必須剛好 3 筆**，包含 `action`、`deadline`（`within XXh` 或 `YYYY-MM-DD`）、`priority`（1-3 不重複）。
  - `talkTracks`: 至少 2 條，含 `situation`、`response`。
  - `repFeedback`: `strengths[]`、`improvements[]` 各至少 2 條。
- `rawOutput`：Markdown 至少包含章節 `## 30秒快速掃描`、`## 三個關鍵`、`## 成交階段判斷`、`## 最大風險`、`## 下一步行動`、`## 業務員改進建議`。
- `analysis.agents.agent6` 需記錄 `status`、`duration`、`retryCount` 與 `data`（同上），供 Slack notifier 與 Agent 7 使用。

## 資料來源對照

| Agent 6 欄位 | 主要來源 | 備註 |
|--------------|---------|------|
| `keyDecisionMaker` | Agent 1 Participant (`decisionPower`, `influenceLevel`) | 缺欄位時以 transcript 引述或回傳 `"UNKNOWN"` |
| `dealHealth` | Agent 2 Sentiment + Agent 3 Needs（信任度、需求強度） | `score` 需描述加總邏輯，`reasoning` 引用代理輸出 |
| `recommendedBundle` | Agent 3 Needs、會議逐字稿 | 僅可列 iCHEF 既有模組，硬體額外以 `pricingNotes` 標示 |
| `competitivePositioning` | Agent 4 Competitor | 無競品資訊時設為 `null` |
| `maximumRisk` | Agent 2/3/5 的負向訊號 + transcript | 若無明確風險，描述「目前證據不足」 |
| `nextActions` | Agent 3 Needs + 業務流程規範 | 依優先順序產出 3 條行動，需含期限 |
| `talkTracks` | Transcript + Agent 5 問卷結果 | 提供可直接複製的話術 |
| `repFeedback` | Transcript + Agent 2 情緒觀察 | `strengths/improvements` 各 >=2 筆，需引用具體對話 |
| `rawOutput` | Prompt 內六步框架 | 與 `structured` 同步，方便人工檢視 |

## 缺資料與例外處理

1. **缺參與者資料**：`keyDecisionMaker.name/role` 設 `"UNKNOWN"`，`primaryConcerns` 可填 `["UNKNOWN"]` 並在 `dealHealth.reasoning` 說明原因。
2. **情緒或需求缺失**：`dealHealth.sentiment` 改用 `neutral`，`score` 介於 40-60，`reasoning` 寫「因 Agent 2/3 缺資料」。
3. **競品未出現**：`competitivePositioning = null`，同時在 `rawOutput` 標記「無競品資訊」避免臆測。
4. **無法給期限**：`nextActions.deadline` 允許 `"within 7d"` 或 `"before YYYY-MM-DD"`，不可為空；若確無資訊，填 `"within 7d"` 並在 `rawOutput` 註解待確認。
5. **取代文字**：任何欄位若無可信內容，一律填 `"UNKNOWN"` 或空陣列，不可省略欄位，確保 `analysis-service/tests/test_agent67_contract.py` 可通過。

## 範例輸出（節錄）

```json
{
  "structured": {
    "keyDecisionMaker": {
      "name": "張總",
      "role": "餐廳老闆／決策者",
      "primaryConcerns": ["尖峰時段人手不足造成客訴", "熟齡客人不熟悉掃碼流程"]
    },
    "dealHealth": {
      "score": 82,
      "sentiment": "positive",
      "reasoning": "Agent2 指出信任度 78，客戶願意一個月內導入並主動要求參訪。"
    },
    "recommendedBundle": {
      "products": ["掃碼點餐", "智慧菜單推薦"],
      "pricingDirection": "match_baseline",
      "pricingNotes": [{"type": "software", "detail": "...", "evidence": "..."}]
    },
    "maximumRisk": {"risk": "熟齡客群不會掃碼", "mitigation": "提供備援流程"},
    "nextActions": [
      {"action": "寄 ROI 試算", "deadline": "within 48h", "priority": 1},
      {"action": "安排參訪", "deadline": "within 72h", "priority": 2},
      {"action": "提供 SOP 草稿", "deadline": "before 2025-11-05", "priority": 3}
    ],
    "talkTracks": [{"situation": "熟齡顧客", "response": "…"}],
    "repFeedback": {
      "strengths": ["舉例成功案例"],
      "improvements": ["價格討論可先問 ROI"]
    }
  },
  "rawOutput": "## 30秒快速掃描\\n- **痛點** …"
}
```

> 完整版本請參考 `analysis-service/tests/fixtures/agent67/agent6_structured.json`，測試會將此檔作為合約範例。

## 下游消費者需求

- **Slack Notifier**（`src/slack_app/notifications/agent6_notifier.py`）：
  - 依賴 `salesStage`、`dealHealth.score/sentiment/reasoning`、`keyDecisionMaker.*`、`maximumRisk`、`nextActions[]`；任何欄位遺漏會導致卡片缺內容。
  - 送訊息後會寫入 `analysis.agents.agent6.notificationSentAt`，需保證這個欄位存在於 Firestore。
- **Agent 7**：`analysis-service/src/agents/run_agent6_agent7.py` 會將 `agent6_structured` 注入 prompt，欄位命名需與此文件一致，否則 `customerSummary` 缺上下文。
- **測試/CI**：`analysis-service/tests/test_agent67_contract.py` 檢查欄位完整性、枚舉值與 Markdown 章節；修改 schema 時務必同步更新 fixture 與本文。
- **Firestore 客戶端**：任何寫入必須使用 `case_ref.update({"analysis.structured": ..., "analysis.rawOutput": ...})` 的 merge 模式，避免覆寫其他 Agent 結果。

## 測試與回歸

- `make test-agent67` 會分別跑 Agent 6/7 的 mock Fixtures（需要 `pytest`）。  
- `analysis-service/src/agents/run_agent6_agent7.py --agents 6` / `--agents 7` 可單獨驗證 prompt 與輸出。
