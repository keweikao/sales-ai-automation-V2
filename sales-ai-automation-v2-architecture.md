# Sales AI Automation V2.0 - 完整專案架構

## 📋 目錄

1. [系統總覽](#系統總覽)
2. [完整檔案結構](#完整檔案結構)
3. [模組詳細說明](#模組詳細說明)
4. [Claude Code Subagent 分工](#claude-code-subagent-分工)
5. [共用介面定義](#共用介面定義)
6. [開發規範](#開發規範)
7. [Git 分支策略](#git-分支策略)
8. [啟動指令](#啟動指令)

---

## 系統總覽

### 客戶生命週期覆蓋

```
廣告獲客 → MQL 開發 → 業務跟進 → 成交導入 → 客戶成功 → 分析優化
   │          │          │          │          │          │
   01         02         03         04         05         06
```

### 核心設計原則

1. **模組獨立**：每個模組有獨立的資料夾，可單獨開發測試
2. **統一介面**：所有模組透過 `core/` 的介面溝通
3. **事件驅動**：模組間透過 Journey Log 記錄事件，解耦合
4. **Skill 對應**：每個模組有對應的 Claude Code Skill

---

## 完整檔案結構

```
sales-ai-automation-V2/
│
├── 📁 .claude/                                    # ⚡ Claude Code 設定
│   ├── settings.json                              # 全域設定
│   └── 📁 skills/                                 # Skills 定義
│       ├── 📁 00-core-skill/                      # 核心開發 Skill
│       │   └── SKILL.md
│       ├── 📁 01-lead-source-skill/               # 廣告追蹤 Skill
│       │   └── SKILL.md
│       ├── 📁 02-mql-skill/                       # MQL 開發 Skill
│       │   └── SKILL.md
│       ├── 📁 03-sales-analysis-skill/            # 銷售分析 Skill
│       │   └── SKILL.md
│       ├── 📁 04-deal-onboarding-skill/           # 成交導入 Skill
│       │   └── SKILL.md
│       ├── 📁 05-customer-success-skill/          # 客戶成功 Skill
│       │   └── SKILL.md
│       └── 📁 06-analytics-skill/                 # 分析報表 Skill
│           └── SKILL.md
│
├── 📁 core/                                       # 🔒 核心層（Agent A 專屬）
│   │
│   ├── 📁 config/                                 # 環境設定
│   │   ├── __init__.py
│   │   ├── settings.py                            # 全域設定載入
│   │   ├── constants.py                           # 常數定義
│   │   └── environments/
│   │       ├── development.yaml
│   │       ├── staging.yaml
│   │       └── production.yaml
│   │
│   ├── 📁 database/                               # 資料層
│   │   ├── __init__.py
│   │   ├── connection.py                          # DB 連線管理
│   │   ├── 📁 models/                             # 資料模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py                            # 基礎模型
│   │   │   ├── lead.py                            # 潛在客戶
│   │   │   ├── conversation.py                    # 對話記錄
│   │   │   ├── deal.py                            # 成交記錄
│   │   │   ├── journey_event.py                   # 🌟 客戶歷程事件
│   │   │   ├── customer_profile.py                # 🌟 客戶畫像
│   │   │   └── analytics_event.py                 # 分析事件
│   │   │
│   │   ├── 📁 repositories/                       # 資料存取層
│   │   │   ├── __init__.py
│   │   │   ├── base_repository.py
│   │   │   ├── lead_repository.py
│   │   │   ├── conversation_repository.py
│   │   │   ├── deal_repository.py
│   │   │   ├── journey_repository.py              # 🌟 歷程存取
│   │   │   └── profile_repository.py              # 🌟 畫像存取
│   │   │
│   │   └── 📁 migrations/                         # 資料庫遷移
│   │       └── ...
│   │
│   ├── 📁 llm/                                    # LLM 呼叫層
│   │   ├── __init__.py
│   │   ├── client.py                              # LLM 客戶端封裝
│   │   ├── prompt_manager.py                      # Prompt 管理
│   │   ├── token_tracker.py                       # Token 使用追蹤
│   │   └── 📁 prompts/                            # 共用 Prompt 模板
│   │       ├── base_system.md
│   │       └── ichef_context.md
│   │
│   ├── 📁 interfaces/                             # 🌟 模組間介面定義
│   │   ├── __init__.py
│   │   ├── events.py                              # 事件類型定義
│   │   ├── journey_logger.py                      # 歷程記錄介面
│   │   └── module_registry.py                     # 模組註冊
│   │
│   └── 📁 utils/                                  # 共用工具
│       ├── __init__.py
│       ├── date_time_utils.py
│       ├── text_utils.py
│       ├── validators.py
│       └── decorators.py
│
├── 📁 modules/                                    # 功能模組
│   │
│   ├── 📁 01-lead-source/                         # 🟢 Agent B 負責
│   │   ├── __init__.py
│   │   ├── README.md                              # 模組說明
│   │   ├── config.yaml                            # 模組專屬設定
│   │   │
│   │   ├── 📁 google_ads/                         # Google Ads 整合
│   │   │   ├── __init__.py
│   │   │   ├── client.py                          # API 客戶端
│   │   │   ├── campaign_fetcher.py                # 廣告活動資料
│   │   │   └── conversion_tracker.py              # 轉換追蹤
│   │   │
│   │   ├── 📁 facebook_ads/                       # Facebook Ads 整合
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── lead_form_handler.py               # 名單表單處理
│   │   │   └── pixel_events.py                    # Pixel 事件
│   │   │
│   │   ├── 📁 squarespace/                        # Squarespace 整合
│   │   │   ├── __init__.py
│   │   │   ├── webhook_handler.py                 # Webhook 接收
│   │   │   └── form_parser.py                     # 表單解析
│   │   │
│   │   ├── 📁 utm_tracking/                       # UTM 追蹤
│   │   │   ├── __init__.py
│   │   │   ├── parser.py                          # UTM 解析器
│   │   │   └── attribution.py                     # 歸因邏輯
│   │   │
│   │   ├── 📁 handlers/                           # 事件處理器
│   │   │   ├── __init__.py
│   │   │   └── lead_ingestion_handler.py          # 統一入口
│   │   │
│   │   └── 📁 tests/                              # 模組測試
│   │       ├── __init__.py
│   │       ├── test_google_ads.py
│   │       ├── test_facebook_ads.py
│   │       └── test_utm_parser.py
│   │
│   ├── 📁 02-mql-qualification/                   # 🟡 Agent C 負責
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── config.yaml
│   │   │
│   │   ├── 📁 transcription/                      # 音檔轉文字
│   │   │   ├── __init__.py
│   │   │   ├── audio_fetcher.py                   # 音檔獲取
│   │   │   ├── transcriber.py                     # 轉錄服務
│   │   │   └── speaker_diarization.py             # 說話者識別
│   │   │
│   │   ├── 📁 first_contact_analyzer/             # 首次聯繫分析
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py                        # 分析主程式
│   │   │   ├── quality_scorer.py                  # 品質評分
│   │   │   └── 📁 prompts/
│   │   │       └── first_contact_analysis.md
│   │   │
│   │   ├── 📁 lead_scoring/                       # MQL 評分
│   │   │   ├── __init__.py
│   │   │   ├── scorer.py                          # 評分引擎
│   │   │   ├── criteria.py                        # 評分標準
│   │   │   └── thresholds.py                      # 門檻設定
│   │   │
│   │   ├── 📁 assignment/                         # 自動指派
│   │   │   ├── __init__.py
│   │   │   ├── engine.py                          # 指派引擎
│   │   │   ├── rules.py                           # 指派規則
│   │   │   └── load_balancer.py                   # 負載平衡
│   │   │
│   │   ├── 📁 handlers/
│   │   │   ├── __init__.py
│   │   │   └── mql_processing_handler.py
│   │   │
│   │   └── 📁 tests/
│   │       └── ...
│   │
│   ├── 📁 03-sales-conversation/                  # 🔵 Agent D 負責
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── config.yaml
│   │   │
│   │   ├── 📁 transcript_analyzer/                # 對話分析（現有）
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py
│   │   │   ├── context_extractor.py               # 上下文提取
│   │   │   ├── buyer_analyzer.py                  # 買方分析
│   │   │   ├── seller_coach.py                    # 賣方教練
│   │   │   └── 📁 prompts/
│   │   │       ├── context_analysis.md
│   │   │       ├── buyer_analysis.md
│   │   │       └── seller_coaching.md
│   │   │
│   │   ├── 📁 meddic/                             # MEDDIC 評分（現有）
│   │   │   ├── __init__.py
│   │   │   ├── qualifier.py
│   │   │   ├── scoring_framework.py
│   │   │   └── 📁 prompts/
│   │   │       └── meddic_evaluation.md
│   │   │
│   │   ├── 📁 coaching/                           # 教練回饋（現有）
│   │   │   ├── __init__.py
│   │   │   ├── report_generator.py
│   │   │   └── 📁 templates/
│   │   │       └── coaching_report.md
│   │   │
│   │   ├── 📁 handlers/
│   │   │   ├── __init__.py
│   │   │   └── conversation_analysis_handler.py
│   │   │
│   │   └── 📁 tests/
│   │       └── ...
│   │
│   ├── 📁 04-deal-onboarding/                     # 🟣 Agent E 負責
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── config.yaml
│   │   │
│   │   ├── 📁 deal_capture/                       # 成交資訊捕捉
│   │   │   ├── __init__.py
│   │   │   ├── capturer.py                        # 成交記錄器
│   │   │   └── validators.py                      # 資料驗證
│   │   │
│   │   ├── 📁 decision_logger/                    # 🌟 決策記錄
│   │   │   ├── __init__.py
│   │   │   ├── logger.py                          # 決策記錄器
│   │   │   ├── decision_extractor.py              # 從對話提取決策點
│   │   │   └── 📁 prompts/
│   │   │       └── decision_extraction.md
│   │   │
│   │   ├── 📁 profile_builder/                    # 🌟 客戶畫像建立
│   │   │   ├── __init__.py
│   │   │   ├── builder.py                         # 畫像建構器
│   │   │   ├── aggregator.py                      # 歷程彙整
│   │   │   └── 📁 prompts/
│   │   │       └── profile_synthesis.md
│   │   │
│   │   ├── 📁 handoff/                            # 交接產生
│   │   │   ├── __init__.py
│   │   │   ├── generator.py                       # 交接文件產生
│   │   │   └── 📁 templates/
│   │   │       └── handoff_template.md
│   │   │
│   │   ├── 📁 handlers/
│   │   │   ├── __init__.py
│   │   │   └── deal_closed_handler.py
│   │   │
│   │   └── 📁 tests/
│   │       └── ...
│   │
│   ├── 📁 05-customer-success/                    # 🟠 Agent E 負責（同上）
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── config.yaml
│   │   │
│   │   ├── 📁 journey_analyzer/                   # 🌟 歷程分析
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py                        # 歷程分析器
│   │   │   ├── insight_extractor.py               # 洞察提取
│   │   │   └── 📁 prompts/
│   │   │       └── journey_analysis.md
│   │   │
│   │   ├── 📁 timing_recommender/                 # 🌟 時機建議
│   │   │   ├── __init__.py
│   │   │   ├── recommender.py                     # 時機推薦器
│   │   │   ├── lifecycle_stages.py                # 生命週期階段
│   │   │   └── trigger_rules.py                   # 觸發規則
│   │   │
│   │   ├── 📁 angle_suggester/                    # 🌟 切角建議
│   │   │   ├── __init__.py
│   │   │   ├── suggester.py                       # 切角建議器
│   │   │   ├── script_generator.py                # 話術產生
│   │   │   └── 📁 prompts/
│   │   │       ├── angle_suggestion.md
│   │   │       └── opening_script.md
│   │   │
│   │   ├── 📁 health_monitor/                     # 健康度監控
│   │   │   ├── __init__.py
│   │   │   ├── scorer.py                          # 健康度評分
│   │   │   ├── risk_detector.py                   # 流失風險偵測
│   │   │   └── alert_rules.py                     # 警示規則
│   │   │
│   │   ├── 📁 handlers/
│   │   │   ├── __init__.py
│   │   │   ├── cs_recommendation_handler.py
│   │   │   └── health_check_handler.py
│   │   │
│   │   └── 📁 tests/
│   │       └── ...
│   │
│   └── 📁 06-analytics/                           # 🔴 Agent F 負責
│       ├── __init__.py
│       ├── README.md
│       ├── config.yaml
│       │
│       ├── 📁 funnel_analysis/                    # 漏斗分析
│       │   ├── __init__.py
│       │   ├── calculator.py                      # 漏斗計算
│       │   ├── stage_metrics.py                   # 階段指標
│       │   └── conversion_rates.py                # 轉換率
│       │
│       ├── 📁 rep_performance/                    # 業務表現
│       │   ├── __init__.py
│       │   ├── metrics.py                         # 表現指標
│       │   ├── comparator.py                      # 比較分析
│       │   └── trend_analyzer.py                  # 趨勢分析
│       │
│       ├── 📁 customer_insights/                  # 客戶洞察
│       │   ├── __init__.py
│       │   ├── segment_analyzer.py                # 客群分析
│       │   ├── behavior_patterns.py               # 行為模式
│       │   └── churn_predictor.py                 # 流失預測
│       │
│       ├── 📁 cs_effectiveness/                   # CS 成效
│       │   ├── __init__.py
│       │   ├── metrics.py                         # CS 指標
│       │   └── roi_calculator.py                  # ROI 計算
│       │
│       ├── 📁 dashboard_api/                      # Dashboard API
│       │   ├── __init__.py
│       │   ├── routes.py                          # API 路由
│       │   ├── schemas.py                         # 資料結構
│       │   └── aggregators.py                     # 資料彙整
│       │
│       ├── 📁 handlers/
│       │   ├── __init__.py
│       │   └── report_generation_handler.py
│       │
│       └── 📁 tests/
│           └── ...
│
├── 📁 integrations/                               # 外部整合層
│   │
│   ├── 📁 slack/                                  # 🔵 Agent D 主責
│   │   ├── __init__.py
│   │   ├── client.py                              # Slack 客戶端
│   │   ├── message_builder.py                     # 訊息建構
│   │   ├── event_handler.py                       # 事件處理
│   │   ├── 📁 bots/
│   │   │   ├── sales_bot.py                       # 銷售 Bot
│   │   │   └── cs_bot.py                          # CS Bot
│   │   └── 📁 templates/
│   │       ├── analysis_report.json               # Block Kit 模板
│   │       └── cs_recommendation.json
│   │
│   ├── 📁 google_workspace/                       # 🟢 Agent B 主責
│   │   ├── __init__.py
│   │   ├── auth.py                                # 認證
│   │   ├── sheets_client.py                       # Sheets 操作
│   │   ├── drive_client.py                        # Drive 操作
│   │   └── docs_client.py                         # Docs 操作
│   │
│   └── 📁 notifications/                          # 通知服務
│       ├── __init__.py
│       ├── dispatcher.py                          # 通知分發
│       └── channels/
│           ├── slack_channel.py
│           ├── email_channel.py
│           └── webhook_channel.py
│
├── 📁 infrastructure/                             # 🔒 Agent A 專屬
│   │
│   ├── 📁 docker/
│   │   ├── Dockerfile                             # 主應用 Dockerfile
│   │   ├── Dockerfile.worker                      # Worker Dockerfile
│   │   └── docker-compose.yaml                    # 本地開發用
│   │
│   ├── 📁 gcp/
│   │   ├── cloudbuild.yaml                        # Cloud Build 設定
│   │   ├── cloud-run-service.yaml                 # Cloud Run 設定
│   │   └── 📁 terraform/                          # IaC（可選）
│   │       └── ...
│   │
│   └── 📁 scripts/
│       ├── setup.sh                               # 環境設定
│       ├── deploy.sh                              # 部署腳本
│       └── migrate.sh                             # 資料庫遷移
│
├── 📁 tests/                                      # 整合測試
│   ├── __init__.py
│   ├── conftest.py                                # pytest 設定
│   ├── 📁 integration/
│   │   ├── test_lead_to_mql_flow.py
│   │   ├── test_sales_to_deal_flow.py
│   │   └── test_deal_to_cs_flow.py
│   └── 📁 e2e/
│       └── test_full_lifecycle.py
│
├── 📁 docs/                                       # 文件
│   ├── architecture.md                            # 架構說明
│   ├── api-reference.md                           # API 文件
│   ├── 📁 modules/
│   │   ├── 01-lead-source.md
│   │   ├── 02-mql-qualification.md
│   │   ├── 03-sales-conversation.md
│   │   ├── 04-deal-onboarding.md
│   │   ├── 05-customer-success.md
│   │   └── 06-analytics.md
│   └── 📁 guides/
│       ├── local-development.md
│       ├── deployment.md
│       └── adding-new-module.md
│
├── .env.example                                   # 環境變數範本
├── .gitignore
├── pyproject.toml                                 # Python 專案設定
├── requirements.txt                               # Python 依賴
├── requirements-dev.txt                           # 開發依賴
├── package.json                                   # Node.js 依賴（如需要）
├── README.md                                      # 專案說明
└── AGENTS.md                                      # Agent 開發指南
```

---

## 模組詳細說明

### 核心層 (core/)

**職責**：提供所有模組共用的基礎設施

| 子目錄 | 說明 | 修改限制 |
|--------|------|----------|
| `config/` | 環境設定載入 | 🔒 僅 Agent A |
| `database/models/` | 資料模型定義 | 🔒 僅 Agent A |
| `database/repositories/` | 資料存取介面 | 🔒 僅 Agent A |
| `llm/` | LLM 呼叫封裝 | 🔒 僅 Agent A |
| `interfaces/` | 模組間介面 | 🔒 僅 Agent A |
| `utils/` | 共用工具 | 🔒 僅 Agent A |

### 模組間依賴關係

```
                    ┌─────────────────┐
                    │      core/      │
                    │  (Agent A 專屬) │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 01-lead-source  │ │ 02-mql-qual     │ │ 03-sales-conv   │
│   (Agent B)     │ │   (Agent C)     │ │   (Agent D)     │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         │    lead_id        │    lead_id        │
         └──────────────────►└──────────────────►│
                                                 │
         ┌───────────────────────────────────────┘
         │
         ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 04-deal-onboard │ │ 05-customer-suc │ │ 06-analytics    │
│   (Agent E)     │ │   (Agent E)     │ │   (Agent F)     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Claude Code Subagent 分工

### 總覽

| Agent | 負責範圍 | 工作目錄 | 可修改的路徑 |
|-------|----------|----------|--------------|
| **A** | Core + Infra | `/` | `core/`, `infrastructure/`, `tests/integration/`, 根目錄設定檔 |
| **B** | Lead Source | `/modules/01-lead-source` | `modules/01-lead-source/`, `integrations/google_workspace/` |
| **C** | MQL | `/modules/02-mql-qualification` | `modules/02-mql-qualification/` |
| **D** | Sales | `/modules/03-sales-conversation` | `modules/03-sales-conversation/`, `integrations/slack/` |
| **E** | Deal + CS | `/modules/04-deal-onboarding` | `modules/04-deal-onboarding/`, `modules/05-customer-success/` |
| **F** | Analytics | `/modules/06-analytics` | `modules/06-analytics/` |

### 🔒 鎖定檔案清單（僅 Agent A 可修改）

```
# 根目錄設定
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── package.json
├── .env.example
├── README.md
├── AGENTS.md

# 核心層
├── core/**/*

# 基礎建設
├── infrastructure/**/*

# 整合測試
├── tests/integration/**/*
├── tests/e2e/**/*
```

### 各 Agent 的 SKILL.md 範例

#### Agent A - Core Skill

```markdown
# Core Development Skill

## 你的職責

你負責開發和維護 Sales AI Automation V2 的核心層，包括：

1. 資料模型設計 (`core/database/models/`)
2. 資料存取介面 (`core/database/repositories/`)
3. LLM 呼叫封裝 (`core/llm/`)
4. 模組間介面定義 (`core/interfaces/`)
5. 基礎建設和部署 (`infrastructure/`)

## 你只能修改

- `core/` 目錄下的所有檔案
- `infrastructure/` 目錄下的所有檔案
- `tests/integration/` 和 `tests/e2e/`
- 根目錄的設定檔（pyproject.toml, requirements.txt 等）

## 你不能修改

- `modules/` 目錄下的任何檔案
- `integrations/` 目錄下的任何檔案
- `.claude/skills/` 中其他模組的 SKILL.md

## 關鍵設計原則

1. **介面穩定性**：`core/interfaces/` 定義的介面一旦發布，不得破壞相容性
2. **向下相容**：修改資料模型時必須提供遷移腳本
3. **文件優先**：任何介面變更必須更新對應文件

## 常用指令

```bash
# 資料庫遷移
python -m alembic upgrade head

# 執行整合測試
pytest tests/integration/ -v

# 部署到 staging
./infrastructure/scripts/deploy.sh staging
```
```

#### Agent D - Sales Analysis Skill

```markdown
# Sales Analysis Skill

## 你的職責

你負責開發銷售對話分析模組，包括：

1. 對話逐字稿分析
2. MEDDIC 評分
3. 銷售教練回饋
4. Slack Bot 整合

## 你只能修改

- `modules/03-sales-conversation/` 目錄下的所有檔案
- `integrations/slack/` 目錄下的所有檔案

## 你不能修改

- `core/` 目錄
- 其他 `modules/` 目錄
- `infrastructure/` 目錄

## 如何記錄歷程事件

使用 `core/interfaces/journey_logger.py` 記錄分析結果：

```python
from core.interfaces.journey_logger import JourneyLogger

logger = JourneyLogger()

await logger.log_event(
    lead_id="xxx",
    stage="sales",
    event_type="conversation_analyzed",
    summary="銷售對話分析完成，MEDDIC 評分 72 分",
    ai_insights={
        "meddic_score": 72,
        "key_risks": ["預算未確認", "時程壓力"],
        "strengths": ["明確的痛點", "有決策權"]
    },
    decision_factors=["價格敏感", "需要報表功能"],
    recommended_actions=["追蹤預算確認", "提供 ROI 試算"],
    tags=["price_sensitive", "needs_reporting"]
)
```

## Slack Bot 開發規範

- 使用 `integrations/slack/templates/` 中的 Block Kit 模板
- 訊息長度不超過 3000 字元
- 重要資訊放在訊息開頭
```

---

## 共用介面定義

### Journey Logger 介面

```python
# core/interfaces/journey_logger.py

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime

class JourneyLoggerInterface(ABC):
    """
    所有模組必須透過此介面記錄客戶歷程事件。
    這是模組間解耦的關鍵。
    """
    
    @abstractmethod
    async def log_event(
        self,
        lead_id: str,
        stage: str,                          # lead_source / mql / sales / deal / cs
        event_type: str,                     # 事件類型
        summary: str,                        # 事件摘要（給人看）
        ai_insights: Dict = None,            # AI 產生的結構化洞察
        decision_factors: List[str] = None,  # 決策因素
        recommended_actions: List[str] = None, # 建議動作
        tags: List[str] = None,              # 標籤
        source_data_ref: str = None,         # 原始資料參考
        metadata: Dict = None                # 其他元資料
    ) -> str:
        """記錄一筆歷程事件，回傳 event_id"""
        pass
    
    @abstractmethod
    async def get_journey(
        self,
        lead_id: str,
        stages: List[str] = None,            # 篩選特定階段
        limit: int = 50
    ) -> List[Dict]:
        """取得客戶的歷程事件"""
        pass
    
    @abstractmethod
    async def get_insights_summary(
        self,
        lead_id: str
    ) -> Dict:
        """彙整客戶的所有洞察（給 CS Agent 用）"""
        pass
```

### 事件類型定義

```python
# core/interfaces/events.py

from enum import Enum

class Stage(str, Enum):
    LEAD_SOURCE = "lead_source"
    MQL = "mql"
    SALES = "sales"
    DEAL = "deal"
    CS = "cs"

class EventType(str, Enum):
    # Lead Source 事件
    LEAD_CREATED = "lead_created"
    UTM_CAPTURED = "utm_captured"
    
    # MQL 事件
    FIRST_CONTACT_ANALYZED = "first_contact_analyzed"
    MQL_SCORED = "mql_scored"
    LEAD_ASSIGNED = "lead_assigned"
    
    # Sales 事件
    CONVERSATION_ANALYZED = "conversation_analyzed"
    MEDDIC_EVALUATED = "meddic_evaluated"
    COACHING_GENERATED = "coaching_generated"
    
    # Deal 事件
    DEAL_CLOSED = "deal_closed"
    DECISION_CAPTURED = "decision_captured"
    PROFILE_BUILT = "profile_built"
    HANDOFF_GENERATED = "handoff_generated"
    
    # CS 事件
    TIMING_RECOMMENDED = "timing_recommended"
    ANGLE_SUGGESTED = "angle_suggested"
    HEALTH_UPDATED = "health_updated"
    RISK_DETECTED = "risk_detected"
```

---

## 開發規範

### 模組開發 Checklist

每個模組開發前，確認以下事項：

- [ ] 閱讀 `core/interfaces/` 了解可用介面
- [ ] 確認你的 Agent 編號和可修改範圍
- [ ] 在模組目錄建立 `README.md` 說明模組用途
- [ ] 所有對外 API 都要有型別標註
- [ ] 使用 `JourneyLogger` 記錄重要事件
- [ ] 模組測試放在 `modules/XX/tests/`

### 命名規範

```python
# 檔案命名：snake_case
lead_scoring.py
decision_extractor.py

# 類別命名：PascalCase
class LeadScorer:
class DecisionExtractor:

# 函式命名：snake_case
def calculate_score():
def extract_decisions():

# 常數命名：UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
```

### Commit Message 格式

```
[模組編號] 類型: 簡短說明

範例：
[core] feat: 新增 JourneyLogger 介面
[03-sales] fix: 修正 MEDDIC 評分計算錯誤
[05-cs] refactor: 重構切角建議邏輯
```

---

## Git 分支策略

```
main                                    # 正式環境
├── develop                             # 開發整合
│   ├── feature/core-journey-logger     # Agent A
│   ├── feature/lead-source-google-ads  # Agent B
│   ├── feature/mql-transcription       # Agent C
│   ├── feature/sales-meddic-v2         # Agent D
│   ├── feature/deal-profile-builder    # Agent E
│   └── feature/analytics-funnel        # Agent F
│
└── release/v2.1.0                      # 發布分支
```

### 分支命名規則

```
feature/[模組簡稱]-[功能描述]
bugfix/[模組簡稱]-[問題描述]
refactor/[模組簡稱]-[重構描述]

範例：
feature/core-journey-logger
feature/lead-google-ads-integration
feature/mql-first-contact-analyzer
feature/sales-coaching-v2
feature/deal-profile-builder
feature/cs-angle-suggester
feature/analytics-funnel-metrics
```

---

## 啟動指令

### Agent A（Core + Infra）

```bash
cd ~/sales-ai-automation-V2
claude

# 進入後貼上以下 prompt：
"""
我是 Agent A，負責 Core 和 Infrastructure 開發。

我的工作範圍：
- core/ 目錄
- infrastructure/ 目錄
- tests/integration/ 和 tests/e2e/
- 根目錄設定檔

請先讀取 .claude/skills/00-core-skill/SKILL.md
"""
```

### Agent B（Lead Source）

```bash
cd ~/sales-ai-automation-V2/modules/01-lead-source
claude

# 進入後貼上以下 prompt：
"""
我是 Agent B，負責 Lead Source 模組開發。

我的工作範圍：
- modules/01-lead-source/
- integrations/google_workspace/

我不能修改：
- core/ 目錄
- 其他 modules/ 目錄
- infrastructure/ 目錄

請先讀取 ../../.claude/skills/01-lead-source-skill/SKILL.md
"""
```

### Agent C（MQL）

```bash
cd ~/sales-ai-automation-V2/modules/02-mql-qualification
claude

# 進入後貼上以下 prompt：
"""
我是 Agent C，負責 MQL Qualification 模組開發。

我的工作範圍：
- modules/02-mql-qualification/

我不能修改：
- core/ 目錄
- 其他 modules/ 目錄
- infrastructure/ 目錄

請先讀取 ../../.claude/skills/02-mql-skill/SKILL.md
"""
```

### Agent D（Sales Conversation）

```bash
cd ~/sales-ai-automation-V2/modules/03-sales-conversation
claude

# 進入後貼上以下 prompt：
"""
我是 Agent D，負責 Sales Conversation 模組開發。

我的工作範圍：
- modules/03-sales-conversation/
- integrations/slack/

我不能修改：
- core/ 目錄
- 其他 modules/ 目錄
- infrastructure/ 目錄

請先讀取 ../../.claude/skills/03-sales-analysis-skill/SKILL.md
"""
```

### Agent E（Deal + CS）

```bash
cd ~/sales-ai-automation-V2/modules/04-deal-onboarding
claude

# 進入後貼上以下 prompt：
"""
我是 Agent E，負責 Deal Onboarding 和 Customer Success 模組開發。

我的工作範圍：
- modules/04-deal-onboarding/
- modules/05-customer-success/

我不能修改：
- core/ 目錄
- 其他 modules/ 目錄
- infrastructure/ 目錄

請先讀取 ../../.claude/skills/04-deal-onboarding-skill/SKILL.md
請先讀取 ../../.claude/skills/05-customer-success-skill/SKILL.md
"""
```

### Agent F（Analytics）

```bash
cd ~/sales-ai-automation-V2/modules/06-analytics
claude

# 進入後貼上以下 prompt：
"""
我是 Agent F，負責 Analytics 模組開發。

我的工作範圍：
- modules/06-analytics/

我不能修改：
- core/ 目錄
- 其他 modules/ 目錄
- infrastructure/ 目錄

請先讀取 ../../.claude/skills/06-analytics-skill/SKILL.md
"""
```

---

## 附錄：快速開始

### 1. 初始化專案

```bash
# Clone 專案
git clone https://github.com/keweikao/sales-ai-automation-V2.git
cd sales-ai-automation-V2

# 建立虛擬環境
python -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 複製環境變數
cp .env.example .env
# 編輯 .env 填入必要的 API keys
```

### 2. 建立資料庫

```bash
# 執行資料庫遷移
python -m alembic upgrade head
```

### 3. 啟動開發

```bash
# 開啟多個終端機，分別啟動不同的 Agent
# 參考上方「啟動指令」章節
```

---

*文件版本：v1.0*
*最後更新：2026-01-07*
