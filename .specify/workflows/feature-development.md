# Complete Feature Development Workflow

Use this workflow for developing a complete feature from spec to deployment.

## Workflow Stages

### Stage 1: Research & Planning (15 min)
```
階段 1：研究與規劃

Subagent 1 (speckit-researcher): 
研究功能需求「使用者認證系統」
- 搜尋 constitution 的安全性原則
- 搜尋 spec 的認證需求
- 搜尋 plan 的技術方案
- 生成研究報告

Subagent 2 (speckit-planner):
分析任務相依性
- 載入所有相關任務
- 建立執行計畫
- 識別平行批次

請平行執行並生成報告。
```

### Stage 2: Test-Driven Development (20 min)
```
階段 2：測試驅動開發

Subagent 1 (speckit-tester): 撰寫任務 2.1 的測試
Subagent 2 (speckit-tester): 撰寫任務 2.2 的測試
Subagent 3 (speckit-tester): 撰寫任務 2.3 的測試

每個 subagent：
- 使用 MCP API 取得驗收標準
- 撰寫測試（先寫測試）
- 執行測試（應該失敗）
- 報告測試覆蓋率

請平行執行。
```

### Stage 3: Implementation (30 min)
```
階段 3：實作

根據測試，平行實作任務：

Subagent 1 (speckit-implementer): 實作任務 2.1
Subagent 2 (speckit-implementer): 實作任務 2.2
Subagent 3 (speckit-implementer): 實作任務 2.3

每個 subagent：
- 使用 MCP API 取得任務資訊
- 實作功能讓測試通過
- 執行測試驗證
- Token < 3,500

請平行執行。
```

### Stage 4: Documentation (10 min)
```
階段 4：文件

Subagent 1 (speckit-documenter): 更新 API 文件
Subagent 2 (speckit-documenter): 更新使用者指南
Subagent 3 (speckit-documenter): 更新技術文件

每個 subagent：
- 使用 MCP API 取得任務內容
- 更新相關文件
- 加入程式碼範例

請平行執行。
```

### Stage 5: Integration & Validation (10 min)
```
階段 5：整合驗證（主 Agent）

- 執行完整測試套件
- 驗證所有驗收標準
- 檢查程式碼品質
- 生成功能報告
```

## Example Usage

```
開發完整功能：使用者認證系統

相關任務：2.1, 2.2, 2.3

請使用 feature-development workflow：
1. Research & Planning (parallel)
2. TDD (parallel)
3. Implementation (parallel)
4. Documentation (parallel)
5. Integration (main agent)

確保所有 subagents 使用 MCP API。
```

## Expected Timeline

```
Stage 1: Research & Planning     [  15 min ] 🔍
Stage 2: TDD                      [  20 min ] ✍️
Stage 3: Implementation           [  30 min ] 🔨
Stage 4: Documentation            [  10 min ] 📝
Stage 5: Integration             [  10 min ] ✅
----------------------------------------
Total:                            [  85 min ]

vs. Traditional (sequential):    [ 240 min ]
Time Saved:                      [ 155 min ] (65%)
```
