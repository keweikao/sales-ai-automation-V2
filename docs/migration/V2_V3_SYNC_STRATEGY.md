# V2/V3 並行開發同步策略

## 核心問題

在 V3 開發期間，V2 仍在持續開發新功能。需要確保：
1. V2 的新功能能夠映射到 V3
2. 共享資源（prompts、schemas）只維護一份
3. 減少重複工作

---

## 策略：共享資源 + 功能同步清單

### 架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                        共享資源層                                │
│  /shared/                                                       │
│  ├── prompts/           # LLM Prompts（V2/V3 共用）              │
│  │   ├── meddic/        # MEDDIC 分析 prompts                   │
│  │   │   ├── agent2-buyer.md                                   │
│  │   │   ├── agent3-seller.md                                  │
│  │   │   └── global-context.md                                 │
│  │   └── templates/     # 通用模板                              │
│  ├── schemas/           # 業務規則定義（JSON/YAML）              │
│  │   ├── meddic.yaml    # MEDDIC 框架定義                       │
│  │   ├── lead-status.yaml                                      │
│  │   └── commitment-events.yaml                                │
│  ├── config/            # 共享配置                              │
│  │   └── feature-flags.yaml                                    │
│  └── docs/              # 共享文檔                              │
│      └── constitution.md                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          │                                       │
          ▼                                       ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│    V2 (Python)          │         │    V3 (TypeScript)      │
│                         │         │                         │
│  讀取 shared/prompts/   │         │  讀取 shared/prompts/   │
│  讀取 shared/schemas/   │         │  讀取 shared/schemas/   │
│                         │         │                         │
│  Python 實作            │         │  TypeScript 實作        │
│  └── 使用 prompts       │         │  └── 使用 prompts       │
│  └── 驗證 schemas       │         │  └── 驗證 schemas       │
└─────────────────────────┘         └─────────────────────────┘
```

---

## 實作步驟

### Step 1：建立共享資源目錄

```bash
# 在 V2 專案中建立 shared 目錄
mkdir -p shared/{prompts/meddic,prompts/templates,schemas,config,docs}

# 移動現有 prompts 到共享目錄
mv modules/03-sales-conversation/meddic/agents/prompts/* shared/prompts/meddic/
mv templates/prompts/* shared/prompts/templates/
mv memory/constitution.md shared/docs/

# 建立 symlink 保持向後相容
ln -s ../../shared/prompts/meddic modules/03-sales-conversation/meddic/agents/prompts
ln -s ../shared/docs/constitution.md memory/constitution.md
```

### Step 2：建立業務規則 Schema（YAML 格式，語言無關）

```yaml
# shared/schemas/meddic.yaml
version: "1.0"
name: "MEDDIC Framework"
description: "銷售資格評估框架"

dimensions:
  - name: "Metrics"
    key: "metrics"
    description: "量化指標 - 客戶期望的可衡量結果"
    rating_levels:
      - level: "strong"
        score_range: [80, 100]
        criteria: "明確量化目標，有時間框架"
      - level: "moderate"
        score_range: [50, 79]
        criteria: "有目標但不夠具體"
      - level: "weak"
        score_range: [20, 49]
        criteria: "模糊或不確定"
      - level: "not_discussed"
        score_range: [0, 19]
        criteria: "未提及"

  - name: "Economic Buyer"
    key: "economic_buyer"
    description: "經濟決策者 - 有預算權限的人"
    # ... 其他維度

commitment_events:
  - id: "CE1"
    name: "Time"
    description: "安排安裝或教育訓練時間"
    signals:
      - "確認可以的日期"
      - "排出訓練時間"

  - id: "CE2"
    name: "Data"
    description: "提供菜單、桌位、庫存資料"
    signals:
      - "提供菜單檔案"
      - "確認桌位數量"

  - id: "CE3"
    name: "Money"
    description: "簽約或付訂金"
    signals:
      - "確認付款方式"
      - "簽署合約"

customer_types:
  - id: "impulsive"
    name: "衝動型"
    description: "重視速度和便利性"

  - id: "calculated"
    name: "精算型"
    description: "重視成本和 ROI"

  - id: "conservative"
    name: "保守觀望型"
    description: "重視安全性和參考案例"
```

### Step 3：建立同步腳本

```bash
#!/bin/bash
# shared/scripts/sync-to-v3.sh

V2_ROOT="/home/user/sales-ai-automation-V2"
V3_ROOT="/home/user/Sales_ai_automation_v3"

echo "🔄 Syncing shared resources from V2 to V3..."

# Sync prompts
rsync -av --delete \
  "$V2_ROOT/shared/prompts/" \
  "$V3_ROOT/shared/prompts/"

# Sync schemas
rsync -av --delete \
  "$V2_ROOT/shared/schemas/" \
  "$V3_ROOT/shared/schemas/"

# Sync docs
rsync -av --delete \
  "$V2_ROOT/shared/docs/" \
  "$V3_ROOT/shared/docs/"

# Sync config
rsync -av --delete \
  "$V2_ROOT/shared/config/" \
  "$V3_ROOT/shared/config/"

echo "✅ Sync complete!"

# Generate TypeScript types from YAML schemas
echo "📝 Generating TypeScript types..."
cd "$V3_ROOT"
bun run generate:types
```

### Step 4：建立功能同步清單

```markdown
<!-- shared/docs/FEATURE_SYNC.md -->
# V2/V3 功能同步清單

當在 V2 開發新功能時，記錄需要在 V3 實作的對應功能。

## 待同步功能

| V2 功能 | V2 檔案 | V3 狀態 | V3 負責 Agent | 備註 |
|---------|---------|---------|---------------|------|
| 例：新增 Agent7 | modules/03-.../agent7.py | ⏳ Pending | Agent D | 需要新增 prompt |

## 已同步功能

| V2 功能 | V2 日期 | V3 完成日期 | 說明 |
|---------|---------|-------------|------|
| 初始 MEDDIC 分析 | 2025-01 | - | 初始功能 |

## 同步規則

1. **Prompt 變更**：直接在 `shared/prompts/` 修改，兩邊自動同步
2. **Schema 變更**：在 `shared/schemas/` 修改，執行 `sync-to-v3.sh`
3. **API 新功能**：在本清單記錄，由對應 Agent 實作
4. **業務邏輯變更**：更新 `shared/docs/` 的業務規則文檔
```

---

## V3 讀取共享資源的方式

### 讀取 Prompts

```typescript
// apps/server/src/lib/prompts.ts
import { readFile } from 'fs/promises'
import { join } from 'path'

const PROMPTS_DIR = join(process.cwd(), '../../shared/prompts')

export async function loadPrompt(path: string): Promise<string> {
  const fullPath = join(PROMPTS_DIR, path)
  return readFile(fullPath, 'utf-8')
}

// 使用
const buyerPrompt = await loadPrompt('meddic/agent2-buyer.md')
const globalContext = await loadPrompt('meddic/global-context.md')
```

### 讀取 Schemas（生成 TypeScript 類型）

```typescript
// packages/shared/src/schemas/meddic.ts
// 由 YAML schema 自動生成

export interface MEDDICDimension {
  name: string
  key: string
  description: string
  ratingLevels: RatingLevel[]
}

export interface RatingLevel {
  level: 'strong' | 'moderate' | 'weak' | 'not_discussed'
  scoreRange: [number, number]
  criteria: string
}

export interface CommitmentEvent {
  id: 'CE1' | 'CE2' | 'CE3'
  name: string
  description: string
  signals: string[]
}

export interface CustomerType {
  id: 'impulsive' | 'calculated' | 'conservative'
  name: string
  description: string
}

// 從 YAML 載入的資料
export const MEDDIC_SCHEMA = {
  dimensions: [...],
  commitmentEvents: [...],
  customerTypes: [...],
}
```

---

## 並行開發工作流程

### 場景 1：V2 新增 Prompt

```
1. 在 V2 修改 shared/prompts/meddic/agent2-buyer.md
2. Commit 到 V2 repo
3. 執行 sync-to-v3.sh
4. V3 自動獲得新 prompt
```

### 場景 2：V2 新增 API 功能

```
1. 在 V2 開發新的 router endpoint
2. 在 FEATURE_SYNC.md 記錄需要同步
3. 分配給對應的 V3 Agent 實作
4. V3 Agent 實作後更新同步狀態
```

### 場景 3：V2 修改業務規則

```
1. 更新 shared/schemas/meddic.yaml
2. 更新 shared/docs/ 相關文檔
3. 執行 sync-to-v3.sh
4. V3 重新生成 TypeScript 類型
5. V3 修改受影響的程式碼
```

---

## 目錄結構最終形態

```
sales-ai-automation-V2/
├── shared/                        # 🟢 共享資源（主要維護處）
│   ├── prompts/
│   │   ├── meddic/
│   │   │   ├── agent2-buyer.md
│   │   │   ├── agent3-seller.md
│   │   │   ├── agent4-summary.md
│   │   │   ├── agent6-crm-extractor.md
│   │   │   └── global-context.md
│   │   └── templates/
│   │       ├── mcp-context-optimization.md
│   │       └── mcp-tool-discovery.md
│   ├── schemas/
│   │   ├── meddic.yaml
│   │   ├── lead.yaml
│   │   ├── conversation.yaml
│   │   └── commitment-events.yaml
│   ├── config/
│   │   ├── feature-flags.yaml
│   │   └── env-template.yaml
│   ├── docs/
│   │   ├── constitution.md
│   │   ├── FEATURE_SYNC.md
│   │   └── business-rules.md
│   └── scripts/
│       └── sync-to-v3.sh
│
├── modules/                       # V2 Python 模組
│   └── 03-sales-conversation/
│       └── meddic/
│           └── agents/
│               └── prompts -> ../../../../../shared/prompts/meddic  # symlink
│
├── api-gateway/                   # V2 FastAPI
├── core/                          # V2 Python core
└── ...

Sales_ai_automation_v3/
├── shared/                        # 🟢 從 V2 同步過來
│   ├── prompts/                   # rsync from V2
│   ├── schemas/                   # rsync from V2
│   ├── config/                    # rsync from V2
│   └── docs/                      # rsync from V2
│
├── apps/
│   ├── server/                    # V3 TypeScript 後端
│   │   └── src/
│   │       ├── lib/
│   │       │   └── prompts.ts     # 讀取 shared/prompts
│   │       └── ...
│   └── web/                       # V3 React 前端
│
├── packages/
│   ├── db/                        # Drizzle schema
│   ├── ui/                        # UI 元件
│   └── shared/                    # 從 YAML schema 生成的 TS 類型
│       └── src/
│           └── schemas/
│               └── meddic.ts      # 自動生成
└── ...
```

---

## 自動化同步（GitHub Actions）

```yaml
# .github/workflows/sync-shared.yml
name: Sync Shared Resources

on:
  push:
    paths:
      - 'shared/**'
    branches:
      - main

jobs:
  sync-to-v3:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          repository: your-org/sales-ai-automation-V3
          token: ${{ secrets.V3_REPO_TOKEN }}
          path: v3

      - uses: actions/checkout@v4
        with:
          path: v2

      - name: Sync shared resources
        run: |
          rsync -av --delete v2/shared/ v3/shared/

      - name: Commit and push to V3
        working-directory: v3
        run: |
          git config user.name "Sync Bot"
          git config user.email "bot@example.com"
          git add shared/
          git diff --staged --quiet || git commit -m "sync: update shared resources from V2"
          git push
```

---

## 總結

| 問題 | 解決方案 |
|------|----------|
| V2 結構如何融入 V3？ | 建立 `shared/` 目錄，存放可共用資源 |
| Prompts 如何共享？ | 存放在 `shared/prompts/`，兩邊讀取同一份 |
| 業務規則如何同步？ | 用 YAML schema，生成 TypeScript 類型 |
| V2 新功能如何同步到 V3？ | 記錄在 `FEATURE_SYNC.md`，分配 Agent 實作 |
| 如何自動化？ | GitHub Actions 監控 `shared/` 變更自動同步 |
