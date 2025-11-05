# POC 8 快速開始

快速測試 Agent 8 對話式交互功能。

## 前置要求

1. **Python 3.9+**
2. **Gemini API Key** - 從 [Google AI Studio](https://makersuite.google.com/app/apikey) 獲取

## 安裝依賴

```bash
# 進入 POC 8 目錄
cd specs/001-sales-ai-automation/poc-tests/poc8_agent8_conversational

# 創建虛擬環境
python -m venv venv

# 啟動虛擬環境
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt
```

## 設置環境變數

```bash
# 設置 Gemini API Key
export GEMINI_API_KEY='your-gemini-api-key-here'

# 設置測試模式（使用本地 JSON 數據）
export TEST_MODE=true
```

## 快速測試

### 方法 1：運行快速測試腳本

```bash
python scripts/quick_test.py
```

這會測試 3 個基本問題：
- 今天團隊表現如何？
- 王小明本週表現如何？
- 健康度低於 50 的案件有哪些？

### 方法 2：交互式測試

```python
# 啟動 Python
python

# 運行以下代碼
import os
os.environ["TEST_MODE"] = "true"

from src.agents.conversational_agent8 import ConversationalAgent8

agent = ConversationalAgent8(test_mode=True)

# 測試單個問題
result = agent.generate_answer("今天團隊表現如何？")
print(result["answer"])
```

### 方法 3：測試個別模塊

```bash
# 測試問題解析
cd src/agents
python question_parser.py

# 測試數據查詢
python data_fetcher.py

# 測試完整流程
python conversational_agent8.py
```

## 預期結果

✅ **成功標誌**：
- 問題被正確解析（識別類型和參數）
- 查詢到相關案件
- 生成繁體中文回答
- 回答包含數據、洞察和建議

❌ **如果失敗**：
1. 檢查 `GEMINI_API_KEY` 是否正確設置
2. 檢查是否安裝了所有依賴 (`pip install -r requirements.txt`)
3. 檢查測試數據是否存在 (`test_data/firestore_mock_cases.json`)

## 測試數據說明

- **30 個模擬案件**：涵蓋 5 個業務，健康度 36-96 分
- **時間範圍**：2025-10-29 至 2025-11-04
- **業務**：王小明、陳美玲、李大華、張志強、林雅婷

## 下一步

完成快速測試後，可以：

1. **運行完整測試**：`pytest tests/`
2. **檢查準確率**：查看 `results/` 目錄
3. **調整 Prompt**：修改 `conversational_agent8.py` 中的 Prompt

## 常見問題

### Q1: ImportError: No module named 'google.generativeai'

**解決**：
```bash
pip install google-generativeai
```

### Q2: ValueError: GEMINI_API_KEY 未設定

**解決**：
```bash
export GEMINI_API_KEY='your-key'
```

### Q3: 回答不是繁體中文

**解決**：檢查 Prompt 中是否強調了「必須使用繁體中文」

### Q4: 查詢結果為空

**解決**：
- 檢查時間範圍是否正確
- 檢查測試數據是否載入 (`TEST_MODE=true`)
- 使用 `data_fetcher.py` 單獨測試

## 範例輸出

```
================================================================================
問題 1: 今天團隊表現如何？
--------------------------------------------------------------------------------

✅ 成功生成回答

【回答】
今日團隊完成 8 件案件，整體表現良好！

📊 **關鍵數據**
• 完成案件數：8 件
• 平均健康度：78.5 分
• 表現優異：王小明（3 件，健康度 88 分）

💡 **洞察**
• 整體健康度高於團隊平均值
• 王小明在需求確認型案件表現突出

✅ **建議**
• 關注陳美玲的 #202501-IC003（健康度 45）
• 建議安排與客戶老闆的會議

【數據統計】
  - 查詢到 8 個案件
  - 問題類型: team_overview
```
