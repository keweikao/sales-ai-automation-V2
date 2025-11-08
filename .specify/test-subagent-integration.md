# Subagent 整合測試

驗證 Subagent + MCP 整合是否正常運作。

## 測試 1：基本 Subagent 呼叫

```
使用 speckit-implementer subagent 檢查系統：

請執行：
1. 使用 MCP API 取得任務 1.1 的資訊
2. 報告任務詳情
3. 報告 token 使用量

預期：
- 成功取得任務資訊
- Token < 1,500
- 包含相關的 spec 和 plan 內容
```

## 測試 2：平行執行

```
測試平行執行能力：

使用 2 個 speckit-researcher subagents 平行研究：
- Subagent 1: 研究「認證需求」
- Subagent 2: 研究「授權需求」

每個使用 MCP API。

預期：
- 兩個 subagents 同時執行
- 各自獨立的結果
- 總 token < 3,000
```

## 測試 3：完整工作流程

```
測試完整 parallel-tasks workflow：

使用 parallel-tasks workflow 模擬實作任務 1.1, 1.2

要求：
- 使用 speckit-planner 規劃
- 使用 speckit-implementer 實作（模擬）
- 報告詳細的 token 使用

預期：
- 順利完成所有階段
- 總 token < 8,000
- 時間效率提升
```

## 執行測試

依序執行上述測試，確認：

- [ ] 測試 1 通過
- [ ] 測試 2 通過
- [ ] 測試 3 通過

如果全部通過，Subagent 整合成功！
