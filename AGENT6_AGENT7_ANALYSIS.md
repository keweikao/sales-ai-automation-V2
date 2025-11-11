# Agent 6 & Agent 7 完整分析文檔

## 📋 目錄

- [Agent 6: Sales Coach Synthesizer](#agent-6-sales-coach-synthesizer)
- [Agent 7: Customer Summary Generator](#agent-7-customer-summary-generator)
- [數據結構對比](#數據結構對比)
- [實際輸出範例](#實際輸出範例)
- [Slack 通知展示](#slack-通知展示)

---

## Agent 6: Sales Coach Synthesizer

### 🎯 角色定位

**銷售分析教練**，具備以下特質：

- 資深 B2B 銷售專家（10+ 年 SaaS 經驗）
- 百萬圓桌會員背景
- iCHEF 系統專家
- 站在公司利益，維護客戶信任
- 誠實指出不足，拒絕空泛理論

### 📊 分析框架（6 大維度）

1. **30 秒快速檢視**
   - 判斷痛點、預算、時程壓力、決策權

2. **三個關鍵**
   - 最在乎什麼
   - 最大顧慮
   - 突破口

3. **成交階段判斷**（四選一）
   - 立即報價型
   - 需要證明型
   - 教育培養型
   - 時機未到型

4. **最大風險**
   - 說明最可能失單原因
   - 提供錯失機會的緊急對策

5. **下一步行動**
   - 具體行動
   - 黃金話術
   - 必問問題

6. **業務員改進建議**
   - 問題
   - 引用證據
   - 改進示範
   - 預期成效

### 📦 輸出結構（Structured）

```json
{
  "keyDecisionMaker": {
    "name": "張總",
    "role": "餐廳老闆／決策者",
    "primaryConcerns": [
      "尖峰時段人手不足造成客訴",
      "熟齡客人不熟悉掃碼流程"
    ]
  },
  "dealHealth": {
    "score": 82,                    // 0-100
    "sentiment": "positive",        // positive/neutral/negative
    "reasoning": "Agent2 指出信任度 78，客戶願意一個月內導入並主動要求參訪。"
  },
  "salesStage": "需要證明型",       // 字串（四選一）
  "maximumRisk": {
    "risk": "熟齡客群不會掃碼導致抱怨，進而延後導入。",
    "mitigation": "提供桌邊備援流程與員工手卡，並安排客戶見證影片強化信心。"
  },
  "nextActions": [                  // 必須正好 3 個
    {
      "action": "48 小時內寄出成功案例與 ROI 試算表，凸顯人力節省數字。",
      "deadline": "within 48h",
      "priority": 1                 // 1=最高
    },
    {
      "action": "協調信義區 Bella Vita 參訪日期，鎖定下週三下午。",
      "deadline": "within 72h",
      "priority": 2
    },
    {
      "action": "準備熟齡客人備援 SOP 與桌上立牌設計，會前先寄草稿。",
      "deadline": "before 2025-11-05",
      "priority": 3
    }
  ],
  "recommendedBundle": {
    "products": ["掃碼點餐", "智慧菜單推薦"],
    "pricingStrategy": "採標準方案，導入後 45 天視營運調整；熟齡客群配備人工備援。",
    "pricingDirection": "match_baseline",  // below_baseline/match_baseline/above_baseline
    "referencePoint": "客戶接受月費 3,500 元，只要求 ROI，故維持 baseline 並強化價值對焦。",
    "totalEstimate": {
      "currency": "TWD",
      "min": 3200,
      "max": 3800,
      "notes": "僅包含軟體訂閱與 QR 物料，不含額外 iPad 硬體。"
    },
    "pricingNotes": [
      {
        "type": "software",
        "detail": "月費 3,500 元可涵蓋 POS + 掃碼點餐，保持 baseline。",
        "evidence": "客戶詢問『會很貴嗎』後接受 3,500 元方案。"
      }
    ]
  },
  "talkTracks": [                   // 至少 2 個
    {
      "situation": "客戶擔心熟齡客人不會掃碼",
      "response": "「張總，像您提到的熟齡客人，我們都會留桌邊人工備援，服務生只要拿平板幫忙結帳，他們也會覺得更貼心。」"
    }
  ],
  "repFeedback": {
    "strengths": [
      "主動舉例 Bella Vita 成功案例提升信任。",
      "清楚回應導入時程與服務流程，展現掌握度。"
    ],
    "improvements": [
      "價格討論時可先問客戶 ROI 指標，避免只報方案費用。",
      "可提前說明熟齡客人備援流程，減少客戶顧慮。"
    ]
  },
  "competitivePositioning": null    // 若無競品資料
}
```

### 🎨 輸出風格

- 直接、簡潔，段落 ≤3 行
- **粗體**標記關鍵詞
- 街頭智慧語言，避免學術名詞
- 必須引用 Agents 1-5 的分析結果佐證
- 數字具體（如「成交率有機會 +20%」）

---

## Agent 7: Customer Summary Generator

### 🎯 角色定位

**iCHEF 資深銷售顧問**（會議主談業務）

- 熟悉客戶痛點與 iCHEF 解決方案
- 擅長用「我／我們」的語氣撰寫跟進訊息
- 語氣需延續逐字稿中業務的說話風格
- 目標：產出可直接分享給客戶的摘要

### 📝 內容框架（5 大章節）

1. **摘要**（2-3 句）
   - 會議目標
   - 主要結論
   - 下一步方向

2. **重點決議**（至少 2 項）
   - 引用逐字稿片段
   - 附上說話者與時間戳

3. **待跟進事項**
   - 客戶待辦（至少 1 項）
   - iCHEF 待辦（至少 1 項）
   - 各自負責人與期限

4. **下一步**
   - 下一個里程碑
   - 建議追蹤時間

5. **聯絡窗口**
   - 客戶聯絡人
   - iCHEF 聯絡人

### 📦 輸出結構（CustomerSummary）

```json
{
  "customerSummary": {
    "summary": "我們討論掃碼點餐如何解決尖峰人力不足，張總接受月費 3,500 元，只要求看到成功案例與熟齡客群備援方案。下一步是安排 Bella Vita 參訪並寄出 ROI 試算與桌邊服務 SOP。",
    "keyDecisions": [
      {
        "title": "確認掃碼點餐導入方向",
        "speakerId": "Speaker 2",
        "timestamp": "00:06:40",
        "quote": "如果效果好的話，我們應該在一個月內就會導入。"
      },
      {
        "title": "需要安排成功案例參訪",
        "speakerId": "Speaker 2",
        "timestamp": "00:05:52",
        "quote": "你可以安排我去參觀嗎？"
      }
    ],
    "nextSteps": {
      "customer": [
        {
          "description": "確認參訪時間、帶兩位店長一同前往",
          "owner": "張總",
          "dueDate": "2025-11-03"
        }
      ],
      "ichef": [
        {
          "description": "48 小時內寄出 ROI 試算、熟齡備援 SOP 與成功案例資料",
          "owner": "Kevin",
          "dueDate": "2025-10-31"
        },
        {
          "description": "協調 Bella Vita 參訪行程，鎖定下週三下午",
          "owner": "Kevin",
          "dueDate": "2025-11-02"
        }
      ]
    },
    "upcomingMilestone": {
      "status": "scheduled",        // scheduled/suggested
      "date": "2025-11-08",
      "note": "Bella Vita 參訪後確認導入日期"
    },
    "contacts": {
      "customer": {
        "name": "張總",
        "role": "餐廳老闆",
        "email": null,
        "phone": "待補"
      },
      "ichef": {
        "name": "Kevin",
        "role": "iCHEF 業務經理",
        "email": "kevin@ichefpos.com",
        "phone": null
      }
    }
  },
  "markdown": "## 摘要\n- **導入焦點**：掃碼點餐解決尖峰時段人手不足。\n- **決策現況**：月費 3,500 元可接受，待參訪確認後一個月內導入。\n- **顧慮對策**：熟齡客人改由桌邊備援與員工引導。\n\n## 重點決議\n- **確認掃碼點餐導入方向（Speaker 2, 00:06:40）**：「如果效果好的話，我們應該在一個月內就會導入。」\n- **需要安排成功案例參訪（Speaker 2, 00:05:52）**：「你可以安排我去參觀嗎？」\n\n## 待跟進事項\n- **客戶**：張總 — 確認參訪時間並通知兩位店長（2025-11-03）。\n- **iCHEF**：Kevin — 48 小時內寄出 ROI 試算與熟齡備援 SOP；協調 Bella Vita 參訪（2025-10-31／2025-11-02）。\n\n## 下一步\n- **里程碑**：2025-11-08 Bella Vita 參訪後確認導入日期。\n- **建議追蹤**：參訪結束後 24 小時內回電，敲定導入與教育訓練時程。\n\n## 聯絡窗口\n- **客戶**：張總（餐廳老闆）｜電話：待補\n- **iCHEF**：Kevin（iCHEF 業務經理）｜Email：kevin@ichefpos.com"
}
```

### 🎨 輸出風格

- 專業、易讀
- 仿照逐字稿中業務的說話風格
- 使用業務常用詞（如「我們這邊」「沒問題我會安排」）
- 避免過度行銷口吻
- 保持客戶可讀性

---

## 數據結構對比

| 欄位 | Agent 6 | Agent 7 | 用途 |
|------|---------|---------|------|
| **主要受眾** | 內部業務團隊 | 客戶 | 決定語氣與內容深度 |
| **決策者** | `keyDecisionMaker` (單數物件) | `contacts.customer` | Agent 6 詳細分析，Agent 7 簡單聯絡資訊 |
| **健康度** | `dealHealth` (score + sentiment + reasoning) | - | 僅內部使用 |
| **階段** | `salesStage` (字串) | - | 僅內部使用 |
| **風險** | `maximumRisk` | - | 僅內部使用 |
| **行動** | `nextActions` (3 項，含 priority + deadline) | `nextSteps` (分 customer/ichef) | Agent 6 建議，Agent 7 已確認事項 |
| **定價** | `recommendedBundle` (詳細策略) | - | 僅內部使用 |
| **話術** | `talkTracks` | - | 僅內部使用 |
| **反饋** | `repFeedback` | - | 僅內部使用 |
| **摘要** | `rawOutput` (教練式) | `markdown` (客戶友好) | 不同受眾 |
| **決議** | - | `keyDecisions` (含引用) | 客戶需要具體記錄 |
| **里程碑** | - | `upcomingMilestone` | 客戶需要清楚的時間線 |

---

## 實際輸出範例

### Agent 6 實際輸出（Positive Scenario）

**關鍵決策者**：

- 張總（餐廳老闆／決策者）
- 主要考量：尖峰時段人手不足、熟齡客人不熟悉掃碼流程

**成交健康度**：82/100 (POSITIVE)

- 理由：Agent2 指出信任度 78，客戶願意一個月內導入並主動要求參訪

**銷售階段**：需要證明型

**最大風險**：

- 風險：熟齡客群不會掃碼導致抱怨，進而延後導入
- 對策：提供桌邊備援流程與員工手卡，並安排客戶見證影片強化信心

**下一步行動**（按優先級）：

1. 🔴 48 小時內寄出成功案例與 ROI 試算表 (within 48h)
2. 🟡 協調信義區 Bella Vita 參訪日期 (within 72h)
3. 🟢 準備熟齡客人備援 SOP (before 2025-11-05)

---

### Agent 7 實際輸出（Positive Scenario）

**一句話摘要**：
我們討論掃碼點餐如何解決尖峰人力不足，張總接受月費 3,500 元，只要求看到成功案例與熟齡客群備援方案。下一步是安排 Bella Vita 參訪並寄出 ROI 試算與桌邊服務 SOP。

**重點決議**：

1. 確認掃碼點餐導入方向 (Speaker 2, 00:06:40)
   > "如果效果好的話，我們應該在一個月內就會導入。"
2. 需要安排成功案例參訪 (Speaker 2, 00:05:52)
   > "你可以安排我去參觀嗎？"

**待跟進事項**：

- **客戶**：張總 — 確認參訪時間、帶兩位店長（2025-11-03）
- **iCHEF**：Kevin — 寄出 ROI 試算（2025-10-31）、協調參訪（2025-11-02）

**下一步里程碑**：
2025-11-08 Bella Vita 參訪後確認導入日期

---

## Slack 通知展示

### Agent 6 通知（內部業務）

```

📊 銷售分析報告 (Agent 6)

案件編號: CASE_20251110_001
客戶: 張總的餐廳

━━━━━━━━━━━━━━━━━━━━━━

🎯 銷售階段

需要證明型



🟢 成交健康度
POSITIVE (82/100)
Agent2 指出信任度 78，客戶願意一個月內導入並主動要求參訪。

━━━━━━━━━━━━━━━━━━━━━━

👤 關鍵決策者
• 張總 (餐廳老闆／決策者)

主要考量：
  • 尖峰時段人手不足造成客訴
    • 熟齡客人不熟悉掃碼流程
  
  ⚠️ 最大風險
熟齡客群不會掃碼導致抱怨，進而延後導入。

對策： 提供桌邊備援流程與員工手卡...



━━━━━━━━━━━━━━━━━━━━━━



🎯 建議下一步行動

1. 🔴 48 小時內寄出成功案例與 ROI 試算表 within 48h
2. 🟡 協調信義區 Bella Vita 參訪日期 within 72h
3. 🟢 準備熟齡客人備援 SOP before 2025-11-05

━━━━━━━━━━━━━━━━━━━━━━

[📄 查看完整分析] [💬 詢問 Agent 8]
```

### Agent 7 通知（準備給客戶）

```
📝 客戶摘要預覽

案件編號: CASE_20251110_001
客戶: 張總的餐廳

━━━━━━━━━━━━━━━━━━━━━━

摘要預覽:
我們討論掃碼點餐如何解決尖峰人力不足，張總接受月費 3,500 元，
只要求看到成功案例與熟齡客群備援方案。下一步是安排 Bella Vita
參訪並寄出 ROI 試算與桌邊服務 SOP...

━━━━━━━━━━━━━━━━━━━━━━

📊 字數: 650 字元 | 行數: 32

[✏️ 編輯摘要] [👁️ 完整預覽] [✅ 確認送出]

⚠️ 點擊「確認送出」後，系統將生成網頁並發送簡訊給客戶
```

---

## 核心差異總結

### Agent 6（內部分析）

- **目的**：幫助業務團隊理解客戶、提升成交率
- **內容**：詳細分析、風險評估、話術建議、反饋
- **語氣**：直接、專業、教練式
- **數據**：定量（分數、優先級）+ 定性（推理、證據）

### Agent 7（客戶摘要）

- **目的**：提供客戶可讀的會議記錄
- **內容**：決議、待辦、時間線、聯絡方式
- **語氣**：友好、專業、延續業務風格
- **數據**：具體行動、明確期限、引用原話

---

## 技術實作對應

### Firestore 數據路徑

```
cases/{caseId}/
  └── analysis/
      ├── agents/
      │   └── agent6/
      │       ├── status: "success"
      │       ├── data: { structured object }
      │       └── rawOutput: "markdown text"
      └── customerSummary/
          ├── summary: "one-liner"
          ├── markdown: "full markdown"
          ├── keyDecisions: [...]
          ├── nextSteps: {...}
          └── upcomingMilestone: {...}
```

### Slack 通知觸發時機

1. **Agent 6 完成** → 發送內部銷售分析通知
2. **Agent 7 完成** → 發送客戶摘要預覽（待編輯）
3. **業務編輯確認** → 生成客戶網頁 + 發送簡訊

---

**文件版本**: 1.0.0
**更新日期**: 2025-11-10
**作者**: Claude Code
