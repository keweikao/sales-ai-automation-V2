# Implementation Plan: Sales AI Automation System V2.0

**Branch**: `001-sales-ai-automation` | **Date**: 2025-01-29 | **Spec**: [spec.md](./spec.md)

## Summary

Build a scalable, cost-optimized sales AI automation system that processes 200-250 audio files monthly with automated transcription (Faster-Whisper medium model with speaker diarization), multi-agent AI analysis (6 specialized Gemini 2.0 Flash agents for participant profiling, sentiment analysis, needs extraction, competitor intelligence, discovery questionnaires, and sales coaching), and delivers interactive experiences via Slack with conversational follow-up. Complete redesign from legacy GAS+Zeabur system to serverless GCP architecture (Cloud Run, Firestore, Cloud Tasks) with Slack-first interface and asynchronous processing, achieving <$45/month operational cost.

**POC Validation Status (2025-10-29)**: 5/5 core POCs completed - Whisper transcription (91.6% quality, asynchronous processing), multi-agent orchestration (3.28s parallel execution), Gemini structured output (100% compliance), Firestore performance (26ms latency, near-zero cost), and questionnaire extraction (AI-draft + human review mode).

## Technical Context

**Language/Version**: Python 3.11+, TypeScript (Google Apps Script compatibility layer)
**Primary Dependencies**:

- Backend: FastAPI, faster-whisper, google-cloud-firestore, google-cloud-storage, google-cloud-tasks, slack-bolt
- AI: google-generativeai (Gemini 2.0 Flash)
- Audio: ffmpeg, pydub
- Testing: pytest, pytest-asyncio, httpx

**Storage**:

- Primary: Google Cloud Firestore (document database)
- Audio: Google Cloud Storage (with 7-day lifecycle deletion)
- Reporting: Google Sheets (daily sync only)

**Testing**:

- Unit tests: pytest with fixtures
- Integration tests: pytest with TestClient (FastAPI)
- Contract tests: Gemini agent output validation
- E2E tests: Slack interaction simulation

**Target Platform**:

- Cloud Run (serverless containers, 0-10 instances auto-scaling)
- Cloud Functions Gen2 (event triggers for GCS)
- Deployment: asia-east1 (Taiwan) for latency optimization

**Project Type**: Microservices (serverless)

**Performance Goals** (Updated based on POC results):

- End-to-end processing: Asynchronous (20-40 minutes for 40-min audio)
- Transcription: ~40 minutes per 40-min audio with medium model (0.915x real-time with diarization, 91.6% quality)
- Multi-agent analysis: <5 seconds (5 agents parallel, validated at 3.28s)
- Slack notification delivery: <1 minute after analysis completion
- Conversational AI response: <5 seconds
- User experience: Upload → Background processing → Slack notification when ready

**Constraints** (Updated based on POC validation):

- Monthly cost: <$45 (including all 6 agents)
- Cost per file: <$0.18
- Transcription quality: >85% (validated at 91.6% with medium model)
- Success rate: >95%
- Gemini structured output: >95% schema compliance (validated at 100%)
- Concurrent processing: 10+ files without degradation
- Questionnaire extraction: AI-draft mode with human review (45% auto-accuracy, supplemented by sales rep confirmation)

**Scale/Scope**:

- Monthly volume: 200-250 audio files
- Average audio duration: 40 minutes
- Peak concurrency: 10 simultaneous uploads
- Users: ~20-30 sales reps
- Data retention: Transcripts indefinite, audio 7 days
- Historical data: 2+ years of cases

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Cost Optimization First (Principle I)

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Self-hosted Whisper | Faster-Whisper on Cloud Run (not OpenAI API) | ✅ PASS |
| Cost-effective serverless | Cloud Run auto-scaling 0-10 instances | ✅ PASS |
| Intelligent caching | Firestore deduplication by file hash | ✅ PASS |
| GPU acceleration justified | No GPU (CPU-only Whisper sufficient for <5min target) | ✅ PASS |
| **Monthly cost <$30** | **<$45** with multi-agent analysis | ⚠️ JUSTIFIED |

**Cost Justification**: Original $30 target assumed single-agent analysis. Multi-agent architecture (6 agents) adds ~$15/month but provides:

- 15-20% higher accuracy per dimension (participant ID, sentiment, needs)
- Structured outputs for automation (questionnaire auto-completion)
- Independent optimization per analysis type
- ROI: Better sales coaching → higher conversion rates → justifies $15 incremental cost

Breakdown:

- Faster-Whisper (Cloud Run): $18-22/month
- Gemini API (6 agents × 250 files): $12-15/month
- Firestore: $3-5/month
- Cloud Storage: $2-3/month
- Cloud Tasks: $1-2/month
- **Total: $36-47/month** ✅

### ✅ Performance & Scalability (Principle II)

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| 10+ concurrent files | Cloud Run max_instances=10 | ✅ PASS |
| Event-driven (no polling) | Cloud Tasks + Storage triggers | ✅ PASS |
| Auto-scaling | Cloud Run 0-10 instances | ✅ PASS |
| Multi-source support | Unified pipeline for GDrive/GCS/Slack | ✅ PASS |
| Processing time 2-5 min | <4 min target with parallel agents | ✅ PASS |

### ✅ Multi-Source Integration (Principle III)

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Google Drive support | OAuth2 + Drive API v3 | ✅ PASS |
| GCS support | Cloud Storage triggers | ✅ PASS |
| Unified queue | Cloud Tasks for all sources | ✅ PASS |
| Source-agnostic logic | Abstract AudioSource interface | ✅ PASS |

### ✅ Quality & Reliability (Principle IV)

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Quality scoring 0-100 | Multi-factor algorithm (FR-010) | ✅ PASS |
| Auto-retry max 3 attempts | Exponential backoff 60s/120s/240s | ✅ PASS |
| Full error logging | Structured logging to Cloud Logging | ✅ PASS |
| Metrics monitoring | Cloud Monitoring with custom metrics | ✅ PASS |
| Alert on >5% failure | Email/Slack alerts configured | ✅ PASS |

### ✅ Chinese Language Optimization (Principle V)

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Proven Chinese models | Whisper large-v3 (best Chinese accuracy) | ✅ PASS |
| Chinese preprocessing | FFmpeg normalization + VAD | ✅ PASS |
| Code-switching support | Whisper auto-detect with zh primary | ✅ PASS |
| Quality threshold 85% | Fine-tuning if <85% (Phase 3 if needed) | ✅ PASS |

### ⚠️ New Requirements Not in Constitution

The following requirements are **new** and not covered by the constitution but are essential to user stories:

1. **Multi-Agent AI Analysis** (6 specialized agents)
   - Not mentioned in original constitution
   - **Justification**: Provides deeper insights than single-agent approach
   - **Cost impact**: +$15/month (within adjusted budget)
   - **Complexity**: Managed through parallel orchestration

2. **Speaker Diarization**
   - Not mentioned in original constitution
   - **Justification**: Required for participant profiling (User Story 2)
   - **Performance impact**: +20-30% processing time (still <5 min)
   - **Cost impact**: Minimal (same Whisper infrastructure)

3. **Slack-First Architecture**
   - Constitution mentions Slack notifications but not full interactive interface
   - **Justification**: Reduces platform switching (core user request)
   - **Complexity**: Slack SDK + Block Kit + conversational AI
   - **User impact**: Dramatic improvement in engagement

4. **Discovery Questionnaire Auto-Completion**
   - Not mentioned in original constitution
   - **Justification**: Eliminates manual data entry, improves data quality
   - **Cost impact**: Included in Agent 5 (<$2/month incremental)

**Recommendation**: Update constitution to reflect multi-agent architecture and Slack-first approach as new core principles.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-sales-ai-automation/
├── spec.md              # User stories, requirements, success criteria ✅ COMPLETE
├── plan.md              # This file (technical implementation plan) 🚧 IN PROGRESS
├── research.md          # Phase 0: Technology evaluation and proof-of-concepts
├── data-model.md        # Phase 1: Firestore collections, Gemini prompts structure
├── quickstart.md        # Phase 1: Local dev setup, deployment guide
├── contracts/           # Phase 1: API contracts for all services
│   ├── api-upload.yaml           # Slack upload slash command
│   ├── api-webhook.yaml          # GAS webhook compatibility
│   ├── api-conversational.yaml   # Slack AI follow-up
│   ├── queue-transcription.json  # Cloud Tasks payload
│   ├── queue-analysis.json       # Cloud Tasks payload
│   ├── agent-prompts/            # Gemini agent prompt templates
│   │   ├── agent1-participant.md
│   │   ├── agent2-sentiment.md
│   │   ├── agent3-needs.md
│   │   ├── agent4-competitor.md
│   │   ├── agent5-questionnaire.md
│   │   └── agent6-coach.md
│   └── slack-blocks/             # Slack Block Kit templates
│       ├── analysis-card.json
│       ├── feedback-modal.json
│       └── progress-message.json
└── tasks.md             # Phase 2: Implementation tasks (NOT created yet)
```text

### Source Code (repository root)

```text
sales-ai-automation-v2/
├── services/
│   ├── transcription-service/        # Cloud Run service (Faster-Whisper)
│   │   ├── src/
│   │   │   ├── main.py              # FastAPI app
│   │   │   ├── transcriber.py       # Whisper inference + diarization
│   │   │   ├── audio_processor.py   # FFmpeg preprocessing
│   │   │   ├── quality_scorer.py    # FR-010 implementation
│   │   │   └── models/
│   │   │       └── transcription.py # Pydantic models
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   │       ├── test_transcriber.py
│   │       └── test_quality.py
│   │
│   ├── analysis-service/             # Cloud Run service (Multi-Agent Orchestrator)
│   │   ├── src/
│   │   │   ├── main.py              # FastAPI app
│   │   │   ├── orchestrator.py      # Agent execution coordination
│   │   │   ├── agents/
│   │   │   │   ├── base_agent.py    # Abstract agent interface
│   │   │   │   ├── participant_analyzer.py   # Agent 1
│   │   │   │   ├── sentiment_analyzer.py     # Agent 2
│   │   │   │   ├── needs_extractor.py        # Agent 3
│   │   │   │   ├── competitor_analyzer.py    # Agent 4
│   │   │   │   ├── questionnaire_analyzer.py # Agent 5
│   │   │   │   ├── sales_coach.py            # Agent 6
│   │   │   │   └── customer_summary.py       # Agent 7
│   │   │   ├── prompts/
│   │   │   │   └── [prompt templates matching contracts/]
│   │   │   └── models/
│   │   │       └── analysis.py      # Pydantic models for structured outputs
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   │       ├── test_orchestrator.py
│   │       ├── test_agents.py
│   │       └── fixtures/
│   │           └── sample_transcripts.json
│   │
│   ├── slack-service/                # Cloud Run service (Slack interface)
│   │   ├── src/
│   │   │   ├── main.py              # FastAPI app
│   │   │   ├── commands/
│   │   │   │   └── upload_handler.py         # /錄音分析 slash command
│   │   │   ├── interactions/
│   │   │   │   ├── button_handler.py         # Interactive buttons
│   │   │   │   ├── modal_handler.py          # Feedback modal
│   │   │   │   └── conversational_ai.py      # AI follow-up
│   │   │   ├── notifications/
│   │   │   │   └── analysis_notifier.py      # Block Kit messages
│   │   │   └── models/
│   │   │       └── slack_payloads.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   │       └── test_slack_interactions.py
│   │
│   └── orchestration-service/        # Cloud Run service (Workflow coordination)
│       ├── src/
│       │   ├── main.py              # FastAPI app (receives all triggers)
│       │   ├── triggers/
│       │   │   ├── gcs_trigger.py   # Cloud Storage event handler
│       │   │   ├── gdrive_poller.py # Google Drive Form submissions
│       │   │   └── slack_upload.py  # Slack upload processor
│       │   ├── queue_manager.py     # Cloud Tasks enqueue/dequeue
│       │   ├── case_manager.py      # Firestore case lifecycle
│       │   └── models/
│       │       └── case.py          # Case Pydantic model
│       ├── Dockerfile
│       ├── requirements.txt
│       └── tests/
│           └── test_triggers.py
│
├── shared/                           # Shared utilities
│   ├── firestore_client.py          # Firestore connection singleton
│   ├── storage_client.py            # GCS operations
│   ├── secret_manager.py            # Secret Manager wrapper
│   ├── logger.py                    # Structured logging
│   └── metrics.py                   # Cloud Monitoring metrics
│
├── functions/                        # Cloud Functions (event triggers)
│   ├── gcs-upload-trigger/          # Triggers on GCS bucket upload
│   │   ├── main.py
│   │   └── requirements.txt
│   └── sheets-sync/                 # Daily Sheets sync (Cloud Scheduler)
│       ├── main.py
│       └── requirements.txt
│
├── gas-compatibility/                # Google Apps Script (legacy support)
│   ├── webhook.gs                   # Forwards to orchestration-service
│   └── sheets-monitor.gs            # Monitors Form submissions
│
├── infrastructure/                   # Terraform IaC
│   ├── main.tf                      # Root module
│   ├── modules/
│   │   ├── cloud-run/
│   │   ├── firestore/
│   │   ├── storage/
│   │   ├── tasks/
│   │   └── monitoring/
│   ├── environments/
│   │   ├── dev.tfvars
│   │   ├── staging.tfvars
│   │   └── prod.tfvars
│   └── scripts/
│       ├── deploy.sh
│       └── rollback.sh
│
├── tests/                            # Integration & E2E tests
│   ├── integration/
│   │   ├── test_e2e_upload_to_notification.py
│   │   ├── test_multi_agent_orchestration.py
│   │   └── test_slack_interactions.py
│   ├── contract/
│   │   ├── test_gemini_agent_outputs.py      # Validate structured outputs
│   │   └── test_api_contracts.py
│   └── performance/
│       └── test_concurrent_processing.py      # Load testing
│
├── docs/
│   ├── architecture.md              # System architecture diagram
│   ├── agent-design.md              # Multi-agent design rationale
│   ├── deployment.md                # Deployment procedures
│   └── monitoring.md                # Observability guide
│
├── scripts/
│   ├── setup-dev.sh                 # Local development setup
│   ├── run-local-whisper.sh         # Local Whisper testing
│   └── migrate-from-v1.py           # Data migration from old system
│
├── .github/
│   └── workflows/
│       ├── test.yml                 # CI: Run all tests
│       ├── deploy-dev.yml           # CD: Deploy to dev
│       └── deploy-prod.yml          # CD: Deploy to prod
│
├── pyproject.toml                   # Python project config (shared deps)
├── docker-compose.yml               # Local development environment
├── README.md                        # Project overview
└── memory/
    └── constitution.md              # System principles ✅ EXISTS
```text

**Structure Decision**: Microservices architecture with 4 Cloud Run services:

1. **transcription-service**: Isolated Whisper processing (heavy compute, independent scaling)
2. **analysis-service**: Multi-agent orchestrator (GPU-free, parallel Gemini calls)
3. **slack-service**: Slack SDK integration (interactive messages, conversational AI)
4. **orchestration-service**: Central workflow coordinator (receives all triggers, manages queue)

**Rationale**:

- **Separation of concerns**: Transcription (CPU-heavy) scales independently from analysis (API-heavy)
- **Cost optimization**: Slack service runs minimal instances (event-driven), transcription scales to 0 when idle
- **Independent deployment**: Can update Gemini prompts without redeploying Whisper
- **Testing isolation**: Each service has focused unit tests

---

## Architecture Overview

### High-Level Data Flow

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           AUDIO SOURCES                                  │
├─────────────────┬─────────────────┬─────────────────┬──────────────────┤
│ Google Drive    │ GCS Bucket      │ Slack Upload    │ GAS Webhook      │
│ (Form submit)   │ (Direct upload) │ (/錄音分析)      │ (Legacy compat)  │
└────────┬────────┴────────┬────────┴────────┬────────┴────────┬─────────┘
         │                 │                 │                 │
         └─────────────────┴─────────────────┴─────────────────┘
                                   │
                                   ▼
         ┌─────────────────────────────────────────────────────────┐
         │     Orchestration Service (Cloud Run)                   │
         │  - Unified entry point for all sources                  │
         │  - Creates Firestore case document                      │
         │  - Downloads audio to GCS                               │
         │  - Enqueues transcription task                          │
         └────────────────────┬────────────────────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────────────────────┐
         │     Cloud Tasks Queue: transcription-queue              │
         │  - Payload: {caseId, gcsPath, priority}                 │
         │  - Retry policy: 3 attempts, exponential backoff        │
         └────────────────────┬────────────────────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────────────────────┐
         │     Transcription Service (Cloud Run)                   │
         │  - Faster-Whisper large-v3 model                        │
         │  - Speaker diarization enabled                          │
         │  - Quality scoring (FR-010)                             │
         │  - Updates Firestore: transcription text + speakers[]   │
         │  - Enqueues analysis task                               │
         └────────────────────┬────────────────────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────────────────────┐
         │     Cloud Tasks Queue: analysis-queue                   │
         │  - Payload: {caseId, transcriptionId}                   │
         └────────────────────┬────────────────────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────────────────────┐
         │     Analysis Service (Cloud Run)                        │
         │  ┌───────────────────────────────────────────────────┐  │
        │  │  Multi-Agent Orchestrator                         │  │
        │  │  - Fetch transcript + speaker data from Firestore │  │
        │  │  - Execute Agents 1-5 in parallel (asyncio)       │  │
        │  │  - Execute Agent 6 with all results               │  │
        │  │  - Execute Agent 7 for customer summary           │  │
        │  │  - Store structured analysis in Firestore         │  │
         │  └────────────────┬──────────────────────────────────┘  │
         │                   │                                      │
         │  ┌────────────────┴───────────────┐                     │
         │  │  PARALLEL EXECUTION (30-40s)   │                     │
         │  ├────────────┬───────────────────┤                     │
         │  │ Agent 1    │ Agent 2           │                     │
         │  │ Participant│ Sentiment         │                     │
         │  │ (30s)      │ (20s)             │                     │
         │  ├────────────┼───────────────────┤                     │
         │  │ Agent 3    │ Agent 4           │                     │
         │  │ Needs      │ Competitor        │                     │
         │  │ (25s)      │ (20s)             │                     │
         │  ├────────────┴───────────────────┤                     │
         │  │ Agent 5: Questionnaire (25s)   │                     │
         │  └────────────┬───────────────────┘                     │
         │               │                                          │
         │               ▼                                          │
         │  ┌─────────────────────────────────────────────────┐    │
         │  │  Agent 6: Sales Coach Synthesis (20s)           │    │
         │  │  - Combines all agent outputs                   │    │
         │  │  - Generates actionable coaching                │    │
        │  └─────────────────────────────────────────────────┘    │
        │               │                                          │
        │               ▼                                          │
        │  ┌─────────────────────────────────────────────────┐    │
        │  │  Agent 7: Customer Summary (15s)                │    │
        │  │  - Creates client-facing recap & next steps     │    │
        │  │  - Persists to analysis.customerSummary         │    │
        │  └─────────────────────────────────────────────────┘    │
         └────────────────────┬────────────────────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────────────────────┐
         │     Slack Service (Cloud Run)                           │
         │  - Fetch case + analysis from Firestore                 │
         │  - Lookup Slack ID from users collection                │
         │  - Format Block Kit interactive message                 │
         │  - Send to sales rep's DM                               │
         │  - Store thread_ts for conversational AI                │
         └─────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌─────────────────────────────────────────────────────────┐
         │     Sales Rep (Slack Client)                            │
         │  - Receives interactive card                            │
         │  - Can click buttons: [逐字稿][參與者][問卷][追問][回饋]  │
         │  - Can type follow-up questions                         │
         └─────────────────────────────────────────────────────────┘
```text

### Slack Workflow（Updated 2025-10-31）

**架構決策**：所有互動僅透過業務與 Bot 的 **Direct Message（DM）**，不使用 Channel，以確保客戶資料隱私。

#### 層次 1: 音檔上傳與 Agent 6 分析

**用戶操作流程**：
1. 業務在 Slack 左側找到 "Sales AI Bot" 並開啟 DM 對話
2. 拖放音檔（m4a/mp3/wav）到對話中
3. Bot 自動偵測並在 thread 中顯示 `[🎤 分析此錄音]` 按鈕
4. 業務點擊按鈕，開啟 Modal 填寫：
   - 店名（必填）
   - 客戶編號（必填）
   - 客戶手機（必填，用於 SMS）
   - 備註（可選）
5. 提交後，Bot 在 thread 回覆確認訊息並更新按鈕為 `[✓ 已開始分析]`（禁用）
6. 系統處理 30-40 分鐘（轉錄 + Agent 1-6 分析）
7. Bot 在同一 thread 回覆 Agent 6 銷售分析卡片

**防重複機制**：
- **Modal 開啟階段**：不鎖定，用戶可取消並重新點擊
- **Modal 提交階段**：使用 Firestore Transaction 立即鎖定，防止並發提交
- **Cloud 處理失敗**：保持 Slack 鎖定，Cloud Tasks 自動重試（最多 5 次）
- **處理完成**：按鈕保持禁用狀態 `[✓ 已完成分析]`

**技術要點**：
- 僅監聽 `file_shared` 事件的 `shares.private`（DM）
- 使用 `processed_files` collection 追蹤檔案處理狀態
- Cloud Tasks retry policy: max_attempts=5, exponential backoff 60s-600s

#### 層次 2: Agent 7 摘要審核與修改

**用戶操作流程**：
1. Agent 6 完成後，Agent 7 自動執行（約 15 秒）
2. Bot 在同一 thread 回覆客戶摘要預覽（前 500 字元）
3. 提供三個按鈕：
   - `[✏️ 編輯摘要]`：開啟 Modal，可編輯完整 Markdown 內容
   - `[👁️ 完整預覽]`：開啟 Modal，顯示完整摘要（唯讀）
   - `[✅ 確認送出]`：生成網頁並發送 SMS 給客戶
4. 業務可重複編輯，每次儲存後更新預覽並標記「已編輯」
5. 確認無誤後點擊「確認送出」

**編輯機制**：
- 支援 Markdown 格式（標題、列表、粗體等）
- 自動儲存 `lastEditedAt`、`editedBy`、`editHistory`
- 可選功能：AI 輔助編輯（業務在 thread 中提出修改建議，AI 自動應用）

#### 層次 3: 客戶摘要網頁與 SMS 發送

**系統處理流程**：
1. 更新 Firestore `status: "approved"`
2. 將 Markdown 轉換為 HTML，套用 iCHEF branding 模板
3. 部署到 `sales.ichefpos.com/summary/{caseId}`
4. 透過 SMS 服務（Twilio / 三竹資訊）發送網頁連結給客戶
5. Bot 在 thread 回覆成功訊息：
   - SMS 發送狀態
   - 網頁連結
   - `[📊 查看發送紀錄]` 按鈕

**網頁設計**：
- iCHEF logo 與 branding
- 會議摘要（含標題、內容、下一步）
- 聯絡業務按鈕（LINE 連結）
- 記錄客戶查看次數與時間

**錯誤處理**：
- 發送失敗時通知業務並保留重試選項
- 記錄完整錯誤日誌到 Firestore `delivery.smsError`

詳細技術實作請參考 `specs/001-sales-ai-automation/slack-workflow.md`。

### Testing & QA Considerations（新增）

- **Agent 6 / 7**：新增單元測試覆蓋 prompt 整合（mock Gemini 輸出），並撰寫整合測試驗證 Firestore 寫入 `analysis.structured` / `analysis.customerSummary` 的 schema。
- **Slack 摘要流程**：為 `✅ 送出摘要` handler 撰寫 E2E 測試（可用 Slack Bolt testing utilities），確認 thread 更新、@ mention、送出後回覆與錯誤處理。
- **摘要頁渲染**：加入 snapshot 測試（HTML / Markdown），確保必備章節存在且 LINE 連結正確生成。
- **SMS/Email 傳送**：以 stub provider 實作 integration test，驗證成功/失敗記錄寫入 Firestore audit collection。
- **POC 1b（GCS leads）**：執行 `specs/001-sales-ai-automation/poc-tests/poc1b_gcs/download_and_transcribe.py` 的實測，需安裝 `google-cloud-storage`、`google-cloud-core`，並準備 staging bucket；測試時應確認 `poc1b_results.json` 的 latency、標籤與錯誤欄位。
- **POC 6（POS adoption）**：更新後的測試腳本 `test_questionnaire_extraction.py` 需加入覆蓋率門檻檢查；建議在 CI 中提供可重播 transcript fixture 以檢測 regression。

#### Automated Testing Plan — Agent 6 & 7

1. **Prompt Contract Tests（單元）**
   - 使用 pytest + fixtures 將 `analysis-service/tests/samples/sample_agent_inputs.json` 提供的資料餵入 mock Gemini 回傳（以靜態 JSON 取代 API），驗證：
     - Agent 6 `structured` 物件符合 `analysis.structured` schema（欄位齊全、型別正確、nextActions 正好 3 筆等）。
     - Agent 7 `customerSummary` 與 `markdown` 同步、必要章節與欄位皆存在。
   - 工具：`pydantic` 或 `jsonschema` 自動驗證，若 schema 變動可共用 `analysis/models/structured.py`。
   - **Status**: ✅ `analysis-service/tests/test_agent67_contract.py` 以靜態 fixtures（正向／負向／資訊不足）檢查欄位完整性與必要約束（2025-10-30）。

2. **Snapshot & Markdown Tests**
   - 針對 Agent 7 `markdown` 產出利用 snapshot（如 `pytest-syrupy`）比對，確保章節標題、bullet 結構與說話者引用格式未被意外更動。
   - 另撰寫檢查：`## 摘要`、`## 重點決議`、`## 待跟進事項`、`## 下一步`、`## 聯絡窗口` 均存在；若缺少則測試失敗。

3. **Integration Tests（Service Pipeline）**
   - 於 analysis-service 中新增 integration 測試：
     1. 模擬 Firestore 取得 transcript + Agents 1–5 結果 → 透過 dependency injection 將 Gemini 呼叫替換為 fixture → 執行 Agent 6 → 驗證 Firestore 寫入 `analysis.structured`。
     2. 同理執行 Agent 7 → 驗證 `analysis.customerSummary` 與對應 markdown 存檔。
   - 使用 `pytest-asyncio` + `respx`（或自製 stub client）攔截 HTTP 呼叫避免實際扣款。

4. **CLI Harness Regression**
   - 為 `run_agent6_agent7.py` 建立 smoke 測試：
     - 透過 `subprocess.run` 執行腳本，改以 `--model mock` 參數觸發自定義 mock（於腳本新增選項：若 model=mock 則載入本地 JSON）。
     - 驗證輸出檔案存在且能解析為 JSON（structured、customerSummary）。
   - 將該測試放入 CI 但標記為 `slow`，必要時可透過環境變數關閉真實 API 呼叫。
   - **Status**: ✅ `run_agent6_agent7.py` 新增 `--mock-scenario`，`make test-agent67` 會執行 mock smoke 測試（2025-10-30）。

5. **Edge Case Fixtures**
   - 補充至少三個測試情境：
     - 正向高意願（目前 sample）
     - 負向為主（客戶拒絕導入）
     - 資料不足（Agents 1–5 輸出缺欄位）→ 驗證 Agent 6/7 能回傳 `"UNKNOWN"` 或空陣列且不崩潰。
   - 指定 fixtures 儲存於 `analysis-service/tests/fixtures/agent67/`，並在 README 中標註更新流程。
   - **Status**: ✅ 三種情境 fixture 已建立（positive/negative/insufficient），並於單元測試中驗證（2025-10-30）。

6. **CI Integration**
   - 新增 `make test-agent67` 指令，涵蓋上述單元 + snapshot + harness 流程。
   - 在 GitHub Actions/`lint-and-test.yml` 中加入 matrix job，於推送與 PR 時執行 mock 測試；選擇性地對主幹或 nightly workflow 執行真實 Gemini 端對端測試（需使用低溫度 + 較高超時控制）。
   - **Status**: ✅ `Makefile` target 完成，`.github/workflows/lint.yml` 現已呼叫 `make test-agent67` 於 CI 中執行（2025-10-30）。

### Critical Path Performance Budget

| Stage | Target | Buffer | Total |
|-------|--------|--------|-------|
| 1. Audio download (GDrive/GCS → GCS) | 20s | 10s | 30s |
| 2. Transcription + Diarization (40min audio) | 180s | 60s | 240s (4min) |
| 3. Multi-Agent Analysis (parallel) | 40s | 10s | 50s |
| 4. Slack Notification Formatting + Send | 10s | 5s | 15s |
| **Total End-to-End** | **250s** | **85s** | **335s (5.5min)** |

**Target**: <4 minutes for 90% of cases (240s)
**Stretch Goal**: <3 minutes (achieved by optimizing audio download with streaming)

---

## Phase 0: Research & Proof-of-Concepts

**Objective**: Validate critical technical assumptions before committing to architecture.

**Output**: `research.md` documenting findings and recommendations.

### POC 1: Faster-Whisper Performance with Speaker Diarization ✅ COMPLETED

**Question**: Can Faster-Whisper with speaker diarization process 40-minute Chinese audio in <5 minutes on Cloud Run (CPU-only)?

**Test Results (2025-10-29)**:

**Large-v3 Model Test**:

- Test audio: 25.4 minutes (1521 seconds)
- Processing time: 49.2 minutes (2951 seconds)
- Speed ratio: 1.940x (too slow)
- Quality score: 94.4/100
- Language confidence: 100%

**Medium Model Test** (Recommended):

- Test audio: 25.4 minutes (1521 seconds)
- Processing time: 23.2 minutes (1392 seconds)
- Speed ratio: 0.915x (2.12x faster than large-v3)
- Quality score: 91.6/100 ✅ (exceeds 85% target)
- Language confidence: 100%

**Decision**: ✅ **Use Medium model + Asynchronous processing**

**Rationale**:

- Medium model provides 91.6% quality (well above 85% target)
- 2.12x speed improvement over large-v3
- For 40-min audio: ~37 minutes processing time (acceptable for async workflow)
- No additional GPU cost required
- User experience: Upload → Background processing → Slack notification when ready

**Architecture Impact**:

- Change from synchronous (<5 min) to asynchronous (20-40 min) processing
- Users receive Slack notification when transcription completes
- No real-time expectation, acceptable for sales workflow
- Cost savings: $0 (no GPU required)

---

### POC 2: Multi-Agent Orchestration Performance ✅ COMPLETED

**Question**: Can 5 Gemini agents execute in parallel within 40 seconds total?

**Test Results (2025-10-29)**:

**Model Used**: Gemini 2.0 Flash Exp
**Test Case**: 1 transcript with 5 agents in parallel

| Metric | Target | Actual Result | Status |
|--------|--------|---------------|--------|
| Sequential execution | N/A | 10.16 seconds | ⚠️ Baseline |
| Parallel execution | <40s | **3.28 seconds** | ✅ Excellent |
| Speed-up ratio | >2x | **3.10x** | ✅ Excellent |
| Success rate | 100% | **100%** (5/5 agents) | ✅ Pass |
| Error rate | <5% | **0%** | ✅ Excellent |
| Slowest agent | N/A | 3.27 seconds | ✅ Pass |

**Decision**: ✅ **Parallel execution validated, far exceeds performance targets**

**Key Findings**:

- Parallel execution 3.1x faster than sequential
- All 5 agents complete in 3.28 seconds (12x faster than 40s target)
- No rate limiting issues with concurrent requests
- 100% success rate, 0% errors

**Architecture Impact**:

- Confirmed: Use `asyncio.gather()` for parallel agent execution
- No need for token bucket or queueing (no rate limits encountered)
- Multi-agent analysis contributes <5 seconds to total processing time (negligible)

---

### POC 3: Gemini Structured Output Quality ✅ COMPLETED

**Question**: Can Gemini 2.0 Flash produce consistent structured outputs (JSON) for all 6 agents?

**Test Results (2025-10-29)**:

**Model Used**: Gemini 2.0 Flash with JSON Mode
**Test Cases**: 10 iterations (5 × Agent 1, 5 × Agent 5)
**Configuration**:

- `response_mime_type: "application/json"`
- `temperature: 0.1`
- `max_output_tokens: 8192`

| Metric | Target | Initial Result | After Optimization | Status |
|--------|--------|----------------|-------------------|--------|
| Valid JSON | >99% | 86.7% | **100%** | ✅ Excellent |
| Schema Compliance | >95% | 40.0% | **100%** | ✅ Excellent |
| Field Completeness | >90% | 46.5% | **100%** | ✅ Excellent |
| Avg response time | <3s | N/A | **1.6 seconds** | ✅ Excellent |

**Decision**: ✅ **Gemini 2.0 Flash JSON Mode validated with optimized prompts**

**Key Optimizations**:

1. **Enable JSON Mode**: `response_mime_type: "application/json"` guarantees valid JSON
2. **Explicit Schema in Prompt**: Define complete JSON structure with field constraints
3. **Provide Examples**: Include full example JSON in prompt
4. **Constrain Value Domains**: Specify allowed values (e.g., "決策者 | 影響者 | 使用者")
5. **Mark Required Fields**: Clearly indicate mandatory vs optional fields

**Prompt Design Best Practices**:

- More important than model parameters for schema compliance
- Complete schema definition in prompt → 100% compliance
- Examples reduce hallucination and improve structure consistency

**Architecture Impact**:

- Use Gemini 2.0 Flash (not 1.5 Flash) for all agents
- JSON Mode enabled for all structured outputs
- No need for function calling fallback
- Prompt templates validated and ready for production

---

### POC 4: Slack Block Kit Interactivity

**Question**: Can Slack Block Kit + FastAPI handle interactive buttons, modals, and threaded conversations?

**Approach**:

1. Implement prototype Slack app with:
   - Slash command `/test-upload`
   - Interactive message with 5 buttons
   - Modal form for feedback
   - Threaded message detection
2. Test:
   - Button click latency (target: <1s response)
   - Modal submission (target: <2s save to Firestore)
   - Threaded conversation context retrieval (target: <500ms)

**Success Criteria**:

- All interactions respond within 3s (Slack timeout)
- Thread context retrieval <500ms
- No dropped events under load (10 simultaneous interactions)

**Fallback**: If performance insufficient, use Slack Socket Mode (WebSocket, not HTTP).

---

### POC 5: Firestore Query Performance

**Question**: Can Firestore handle real-time queries for 200-250 cases/month with complex filters?

**Approach**:

1. Design Firestore schema (see Phase 1)
2. Seed 1000 test cases
3. Test queries:
   - Fetch case by ID (target: <100ms)
   - Fetch all cases for sales rep (target: <200ms)
   - Aggregate daily metrics (target: <500ms)
4. Measure:
   - Read/write costs
   - Query latency
   - Index requirements

**Success Criteria**:

- Case fetch by ID: <100ms
- Complex filters: <300ms
- Monthly Firestore cost: <$5

**Fallback**: If costs exceed budget, use BigQuery for aggregations (not real-time).

---

### POC 6: Discovery Questionnaire Extraction Accuracy

**Question**: Can Agent 5 accurately extract questionnaire responses from conversation without explicit Q&A structure?

**Approach**:

1. Create 15 test transcripts with varying explicitness:
   - Explicit: "我們有用掃碼點餐" → current_status: "使用中"
   - Implicit: "客人都老人家不會用手機" → barriers: ["customer_adoption"]
   - Mixed signals: "想要省人力但擔心成本" → perceived_value + barriers
2. Design prompt with iCHEF feature catalog
3. Measure:
   - Topic detection accuracy (did it find all discussed features?)
   - Response extraction accuracy (correct status, reasons, barriers?)
   - Confidence score calibration (high confidence = accurate?)
   - Completeness score accuracy

**Success Criteria**:

- Topic detection recall: >85% (finds 85% of discussed features)
- Response accuracy: >75% (responses match ground truth)
- Confidence calibration: High confidence (>80) → >90% accurate

**Validation**: Sales reps review 30 auto-completed questionnaires, rate accuracy >3.5/5.0.

**Fallback**: If accuracy <75%, add explicit questionnaire checklist to Slack notification (sales rep fills gaps).

---

## Phase 1: Detailed Design

**Objective**: Design data models, API contracts, agent prompts, and deployment architecture.

**Output**:

- `data-model.md`: Firestore collections, Gemini prompt templates
- `contracts/`: API specs (OpenAPI), queue payloads (JSON), Slack blocks (JSON)
- `quickstart.md`: Local dev setup, deployment guide

### 1.1 Data Model Design

**File**: `data-model.md`

**Contents**:

#### Firestore Collections

##### Collection: `cases`

```typescript
// Document ID: {YYYYMM}-{UNIT}{###} (e.g., "202501-IC001")
{
  // === Metadata ===
  caseId: string,              // Same as document ID
  createdAt: Timestamp,
  updatedAt: Timestamp,
  status: "pending" | "transcribing" | "analyzing" | "awaiting_review" | "approved" | "sent" | "failed",
  sourceType: "google_drive" | "gcs" | "slack",

  // === Customer & Sales Rep ===
  customerName: string,
  customerId: string,          // 客戶編號（新增）
  customerPhone: string,       // 客戶手機（用於 SMS，新增）
  salesRepEmail: string,       // Index for queries
  salesRepName: string,
  salesRepSlackId: string,     // 業務的 Slack ID（新增）
  unit: string,                // "IC" | "OTHER"

  // === Audio File ===
  audio: {
    fileName: string,
    slackFileId: string,       // Slack file ID（Slack 上傳時有值，新增）
    originalUrl: string,       // Google Drive or GCS
    gcsPath: string,           // gs://bucket/path (processed copy)
    duration: number,          // Seconds
    format: string,            // "m4a" | "mp3" | "wav"
    fileSize: number,          // Bytes
    uploadedAt: Timestamp,
    deleteAt: Timestamp,       // createdAt + 7 days
  },

  // === Transcription ===
  transcription: {
    text: string,              // Full transcript
    language: string,          // Detected: "zh" | "zh-TW" | "zh-CN"
    qualityScore: number,      // 0-100 (FR-010)
    qualityFactors: {
      languageConfidence: number,
      coherenceScore: number,
      charTimeRatio: number,
      repetitionScore: number,
      speakerSeparationScore: number,
    },
    speakers: [
      {
        speakerId: string,     // "Speaker 1", "Speaker 2"
        segments: [
          {
            start: number,     // Timestamp in seconds
            end: number,
            text: string,
          }
        ],
        totalDuration: number, // Seconds
        speakingPercentage: number, // 0-100
      }
    ],
    model: string,             // "faster-whisper-large-v3"
    processedAt: Timestamp,
    processingTime: number,    // Seconds
  },

  // === Multi-Agent Analysis ===
  analysis: {
    // Agent 1: Participant Profile Analyzer
    participants: [
      {
        speakerId: string,     // Maps to transcription.speakers[].speakerId
        role: string,          // "老闆/決策者" | "店長/使用者" | "財務主管" | "觀察者"
        roleConfidence: number, // 0-100
        personalityType: "analytical" | "driver" | "amiable" | "expressive",
        decisionPower: number, // 0-100
        influenceLevel: "primary" | "secondary" | "observer",
        concerns: [
          {
            concern: string,
            keyPhrases: string[],
          }
        ],
        interests: string[],
      }
    ],

    // Agent 2: Sentiment & Attitude Analyzer
    sentiment: {
      overall: "positive" | "neutral" | "negative",
      overallConfidence: number, // 0-100
      trustLevel: number,        // 0-100
      engagementLevel: number,   // 0-100
      techAdoptionLevel: number, // 0-100 與談者對科技/新系統的接受度
      emotionCurve: [
        {
          timeRange: string,   // "0-10min"
          sentiment: "positive" | "neutral" | "negative",
          intensity: number,   // 0-100
          keyMoments: string[],
        }
      ],
      buyingSignals: [
        {
          signal: string,
          timestamp: number,   // Seconds
          strength: "strong" | "medium" | "weak",
          quote: string,
        }
      ],
      objectionSignals: [
        {
          objection: string,
          timestamp: number,
          severity: "high" | "medium" | "low",
          quote: string,
        }
      ],
    },

    // Agent 3: Product Needs Extractor
    productNeeds: {
      explicitNeeds: [
        {
          need: string,
          quotes: string[],
          priority: "high" | "medium" | "low",
        }
      ],
      implicitNeeds: [
        {
          need: string,
          inferredFrom: string, // Pain point
          confidence: number,   // 0-100
        }
      ],
      recommendedProducts: [
        {
          productId: string,   // "pos-basic" (from product catalog)
          productName: string,
          fitScore: "perfect" | "good" | "moderate",
          reasoning: string,
        }
      ],
      budget: {
        estimatedMin: number,
        estimatedMax: number,
        flexibility: "high" | "medium" | "low",
        paymentPreference: "full" | "installment" | "subscription" | "unknown",
        priceAnchoring: string[], // Competitor prices mentioned
      },
      decisionTimeline: {
        urgency: "immediate" | "within_month" | "within_quarter" | "long_term",
        expectedDecisionDate: string, // "2025-02" or null
        drivingFactors: string[],
      },
    },

    // Agent 4: Competitor Intelligence Analyzer
    competitors: [
      {
        name: string,
        mentionCount: number,
        contexts: string[],    // Quotes where mentioned
        customerOpinion: {
          pros: string[],
          cons: string[],
          satisfactionScore: number, // 0-100
        },
        relationshipStatus: "current_user" | "past_user" | "evaluating" | "heard_about",
        ourAdvantages: string[], // What we do better
        winningStrategy: string,
        conversionProbability: number, // 0-100
      }
    ],

    // Agent 5: Discovery Questionnaire Analyzer
    discoveryQuestionnaires: [
      {
        topic: string,                // "線上訂位" | "掃碼點餐"
        featureCategory: string,      // "線上整合服務" | "點餐與訂單管理" | ...
        currentStatus: "使用中" | "未使用" | "考慮中" | "曾使用過" | "未提及",
        statusReason: string,         // 為何判斷為此現況
        motivationSummary: string,    // 為何想導入或不導入（整體摘要）
        hasNeed: true | false | null, // null = 未明確表態
        hasNeedReason: string,
        needReasons: [
          {
            reason: string,
            quote: string,
            confidence: number,       // 0-100
            reasoning: string,        // 判斷依據
          }
        ],
        noNeedReasons: [
          {
            reason: string,
            quote: string,
            confidence: number,
            reasoning: string,
          }
        ],
        perceivedValue: {
          score: number,              // 0-100
          aspects: [
            {
              aspect: string,         // "節省人力"
              sentiment: "positive" | "negative" | "neutral",
              quote: string,
            }
          ],
          valueReason: string,
        },
        implementationWillingness: "high" | "medium" | "low" | "none" | "未提及",
        willingnessReason: string,
        barriers: [
          {
            type: "budget" | "technology" | "personnel" | "timing" | "customer_adoption" | "other",
            severity: "high" | "medium" | "low",
            detail: string,
            quote: string,
          }
        ],
        timeline: {
          consideration: string,      // 例："兩週內"、"3-6個月內"、"未提及"
          urgency: "high" | "medium" | "low" | "未提及",
          timelineReason: string,
        },
        completenessScore: number,    // 0-100
        completenessReason: string,
        additionalContext: string,
      }
    ],

    // Agent 6: Sales Coach Synthesizer
    structured: {
      keyDecisionMaker: {
        name: string,          // From participant analysis
        role: string,
        primaryConcerns: string[],
      },
      dealHealth: {
        score: number,         // 0-100
        sentiment: "positive" | "neutral" | "negative",
        reasoning: string,
      },
      recommendedBundle: {
        products: string[],
        pricingStrategy: string,
        totalEstimate: number,
      },
      competitivePositioning: string, // Only if competitors present
      salesStage: "立即報價型" | "需要證明型" | "教育培養型" | "時機未到型",
      maximumRisk: {
        risk: string,
        mitigation: string,
      },
      nextActions: [
        {
          action: string,
          deadline: string,    // "within 48h" | "before 2025-02-05"
          priority: 1 | 2 | 3,
        }
      ],
      talkTracks: [
        {
          situation: string,   // "If customer mentions budget concern"
          response: string,
        }
      ],
      repFeedback: {
        strengths: string[],
        improvements: string[],
      },
    },
    rawOutput: string,         // Full Gemini response (v7.0 format for comparison)

    // Agent 7: Customer Summary（新增編輯功能）
    customerSummary: {
      summary: string,          // 2-3 sentence recap (Traditional Chinese)
      markdown: string,         // 當前版本的 Markdown
      originalMarkdown: string, // AI 原始生成的版本（用於比對）
      lastEditedAt: Timestamp,  // 最後編輯時間
      editedBy: string,         // 編輯者 Slack ID
      editHistory: [            // 編輯歷史（可選）
        {
          markdown: string,
          editedAt: Timestamp,
          editedBy: string,
          comment: string,      // 編輯原因
        }
      ],
      keyDecisions: [
        {
          title: string,
          speakerId: string,
          timestamp: string,
          quote: string,
        }
      ],
      nextSteps: {
        customer: [
          {
            description: string,
            owner: string,
            dueDate: string | null,
          }
        ],
        ichef: [
          {
            description: string,
            owner: string,
            dueDate: string | null,
          }
        ],
      },
      upcomingMilestone: {
        status: "scheduled" | "proposed" | "pending",
        date: string | null,
        note: string,
      },
      contacts: {
        customer: string,
        ichef: string,
      },
    },

    // Orchestration metadata
    agentExecutionLog: [
      {
        agentId: "agent1" | "agent2" | "agent3" | "agent4" | "agent5" | "agent6" | "agent7",
        startedAt: Timestamp,
        completedAt: Timestamp,
        durationMs: number,
        tokensUsed: number,
        status: "success" | "failed" | "partial",
        errorMessage: string,  // If failed
      }
    ],
    totalAnalysisTime: number, // Seconds
    completedAt: Timestamp,
  },

  // === Slack Notification（更新）===
  notification: {
    slackChannelId: string,          // DM channel ID（就是 user_id）
    slackThreadTs: string,           // Thread timestamp（音檔訊息的 ts）
    slackFileId: string,             // Slack file ID
    agent6MessageTs: string,         // Agent 6 分析卡片的 message_ts
    agent7MessageTs: string,         // Agent 7 摘要預覽的 message_ts
    agent6SentAt: Timestamp,
    agent7SentAt: Timestamp,
    deliveryStatus: "sent" | "failed" | "skipped",
    errorMessage: string,
  },

  // === 客戶摘要發送（新增）===
  delivery: {
    smsStatus: "pending" | "sent" | "failed",
    smsSid: string,                  // SMS 服務商的訊息 ID
    customerPhone: string,           // 發送目標號碼
    sentAt: Timestamp,
    failedAt: Timestamp,
    smsError: string,
    summaryUrl: string,              // 完整網址
    shortUrl: string,                // 短網址（可選）
    viewCount: number,               // 客戶查看次數
    firstViewedAt: Timestamp,        // 首次查看時間
    lastViewedAt: Timestamp,         // 最後查看時間
    completedAt: Timestamp,          // 整個流程完成時間
  },

  // === Feedback ===
  feedback: {
    accuracyRating: number,    // 1-5 stars
    dealStatus: "won" | "lost" | "tracking",
    comments: string,
    submittedAt: Timestamp,
  },

  // === Conversational AI ===
  conversations: [
    {
      question: string,
      answer: string,
      askedAt: Timestamp,
      tokensUsed: number,
    }
  ],

  // === System Metrics ===
  metrics: {
    downloadTime: number,      // Seconds
    transcriptionTime: number,
    analysisTime: number,
    notificationTime: number,
    totalTime: number,
    costs: {
      compute: number,         // USD
      geminiTokens: number,    // USD
      storage: number,         // USD
      total: number,           // USD
    },
  },

  // === Retry Logic ===
  retryCount: number,
  lastError: {
    stage: string,             // "transcription" | "analysis" | "notification"
    message: string,
    occurredAt: Timestamp,
  },
}
```text

**Indexes**:

- `salesRepEmail` (for queries: "get my cases")
- `status` (for monitoring: "count pending cases")
- `createdAt` (for reporting: "cases this month")
- Composite: `salesRepEmail + createdAt` (for "my recent cases")

---

##### Collection: `users`

```typescript
// Document ID: email (e.g., "john@ichef.com")
{
  email: string,
  slackId: string,             // "U12345ABC" for Slack API
  lineId: string,              // LINE 官方帳號 ID（新增，用於摘要網頁）
  phone: string,               // 業務電話（新增）
  name: string,
  unit: string,                // "IC" | "OTHER"
  active: boolean,
  welcomed: boolean,           // 是否已發送歡迎訊息（新增）
  firstOpenedAt: Timestamp,    // 首次開啟 Bot 對話時間（新增）
  createdAt: Timestamp,
  updatedAt: Timestamp,
}
```text

**Indexes**: None (query by document ID)

---

##### Collection: `processed_files`（新增）

```typescript
// Document ID: slack_file_id
{
  slackFileId: string,              // Slack file ID（主鍵）
  status: "processing" | "completed" | "failed",
  locked: boolean,                  // 防止並發處理
  lockedAt: Timestamp,

  // 關聯資訊
  caseId: string,                   // 對應的 case ID
  channelId: string,                // DM channel ID
  messageTs: string,                // 音檔訊息的 timestamp
  threadTs: string,                 // Bot 回覆訊息的 timestamp

  // 檔案資訊
  fileName: string,
  fileSize: number,

  // 客戶資訊
  customerName: string,
  customerId: string,
  customerPhone: string,

  // 處理者
  processedBy: string,              // 業務的 Slack ID

  // 時間戳
  processedAt: Timestamp,           // 開始處理時間
  completedAt: Timestamp,           // 完成時間
  failedAt: Timestamp,              // 失敗時間
}
```text

**Indexes**:
- `caseId` (for reverse lookup)
- `processedBy` (for user queries)
- `status` (for monitoring)

---

##### Collection: `questionnaire_templates` (Phase 3 - Optional)

```typescript
// Document ID: auto-generated
{
  templateId: string,          // "qr-ordering-v2"
  featureName: string,         // "掃碼點餐"
  featureCategory: string,     // "點餐與訂單管理"
  questions: [
    {
      questionKey: string,     // "current_status"
      questionText: string,    // "目前是否使用掃碼點餐?"
      expectedDataType: "boolean" | "text" | "enum",
      enumOptions: string[],   // If dataType = enum
    }
  ],
  active: boolean,
  createdAt: Timestamp,
  version: number,
}
```text

---

#### Gemini Agent Prompt Templates

**File**: `contracts/agent-prompts/agent1-participant.md`

```markdown
# Agent 1: Participant Profile Analyzer

## Role
You are an expert sales psychologist analyzing participants in B2B sales conversations.

## Input
- Full transcript with speaker diarization
- Speaking time percentage for each speaker

## Task
For EACH identified speaker, analyze and return structured JSON:

{
  "participants": [
    {
      "speakerId": "Speaker 1",
      "role": "<老闆/決策者 | 店長/使用者 | 財務主管 | 觀察者>",
      "roleConfidence": <0-100>,
      "personalityType": "<analytical | driver | amiable | expressive>",
      "decisionPower": <0-100>,
      "influenceLevel": "<primary | secondary | observer>",
      "concerns": [
        {
          "concern": "<brief description>",
          "keyPhrases": ["<quote 1>", "<quote 2>"]
        }
      ],
      "interests": ["<interest 1>", "<interest 2>"]
    }
  ]
}

## Decision Power Scoring
- 90-100: Final decision maker (老闆, CEO)
- 70-89: Strong influencer (店長, 部門主管)
- 40-69: Moderate influencer (財務, IT)
- 0-39: Observer/gatherer (助理, trainee)

## Personality Detection
- **Analytical**: Asks detailed questions, wants data, slower decision
- **Driver**: Results-focused, direct, fast decision
- **Amiable**: Relationship-focused, collaborative, needs consensus
- **Expressive**: Enthusiastic, storyteller, emotional

## Output Format
Return ONLY valid JSON. No markdown, no explanation.
```text

**(Similar prompt templates for Agents 2-6 to be created in Phase 1)**

---

### 1.2 API Contracts

**File**: `contracts/api-upload.yaml`

```yaml
openapi: 3.0.0
info:
  title: Slack Upload API
  version: 1.0.0

paths:
  /slack/commands/upload:
    post:
      summary: Handle /錄音分析 slash command
      requestBody:
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                command: { type: string, example: "/錄音分析" }
                user_id: { type: string, example: "U12345ABC" }
                channel_id: { type: string }
                trigger_id: { type: string }
      responses:
        '200':
          description: Show upload modal
          content:
            application/json:
              schema:
                type: object
                properties:
                  response_type: { type: string, example: "ephemeral" }
                  trigger_id: { type: string }
                  view:
                    type: object
                    properties:
                      type: { type: string, example: "modal" }
                      title: { type: object }
                      blocks: { type: array }

  /slack/interactions:
    post:
      summary: Handle button clicks and modal submissions
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                type: { type: string, enum: [block_actions, view_submission] }
                user: { type: object }
                actions: { type: array }
                view: { type: object }
      responses:
        '200':
          description: Acknowledge interaction
```text

---

**File**: `contracts/queue-transcription.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Transcription Queue Payload",
  "type": "object",
  "required": ["caseId", "gcsPath"],
  "properties": {
    "caseId": {
      "type": "string",
      "pattern": "^\\d{6}-[A-Z]+\\d{3}$",
      "example": "202501-IC001"
    },
    "gcsPath": {
      "type": "string",
      "pattern": "^gs://[a-z0-9-]+/.+$",
      "example": "gs://sales-audio-v2/202501-IC001.m4a"
    },
    "priority": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "default": 5
    },
    "options": {
      "type": "object",
      "properties": {
        "enableDiarization": { "type": "boolean", "default": true },
        "language": { "type": "string", "default": "zh" },
        "model": { "type": "string", "default": "large-v3" }
      }
    }
  }
}
```text

---

### 1.3 Quickstart Guide

**File**: `quickstart.md`

```markdown
# Quickstart: Local Development

## Prerequisites
- Python 3.11+
- Docker Desktop
- GCP account with billing enabled
- Slack workspace (for testing)

## 1. Clone Repository
git clone https://github.com/your-org/sales-ai-automation-v2.git
cd sales-ai-automation-v2

## 2. Install Dependencies
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

## 3. Setup GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login

## 4. Configure Secrets
cp .env.example .env
# Edit .env with your keys:
# - SLACK_BOT_TOKEN
# - SLACK_SIGNING_SECRET
# - GEMINI_API_KEY
# - GCP_PROJECT_ID

## 5. Run Local Services
docker-compose up -d

This starts:
- Firestore Emulator (localhost:8080)
- Cloud Storage Emulator (localhost:4443)
- Slack Event Mock (localhost:3000)

## 6. Run Transcription Service
cd services/transcription-service
uvicorn src.main:app --reload --port 8001

## 7. Test Upload
curl -X POST http://localhost:8001/transcribe \
  -H "Content-Type: application/json" \
  -d '{"caseId": "202501-TEST001", "audioUrl": "test-audio.m4a"}'

## Deployment
See `docs/deployment.md`
```text

---

## Phase 2: Implementation Tasks

**Objective**: Break down implementation into 2-week sprints with clear acceptance criteria.

**Output**: `tasks.md` (created by `/speckit.tasks` command - **NOT part of this plan**)

**High-Level Task Breakdown** (for reference):

### Sprint 1: Foundation (Week 1-2)

- [ ] Setup GCP project, Terraform IaC
- [ ] Deploy Firestore, Cloud Storage, Cloud Tasks
- [ ] Implement orchestration-service skeleton
- [ ] Implement shared utilities (Firestore client, logger, metrics)
- [ ] Setup CI/CD pipelines

### Sprint 2: Transcription Service (Week 3-4)

- [ ] Implement transcription-service with Faster-Whisper
- [ ] Implement speaker diarization
- [ ] Implement quality scoring (FR-010)
- [ ] Unit tests for transcription logic
- [ ] Deploy to Cloud Run (dev environment)

### Sprint 3: Multi-Agent Analysis (Week 5-6)

- [ ] Implement analysis-service orchestrator
- [ ] Implement Agent 1: Participant Analyzer
- [ ] Implement Agent 2: Sentiment Analyzer
- [ ] Implement Agent 3: Needs Extractor
- [ ] Unit tests for each agent
- [ ] Integration test: End-to-end transcription → analysis

### Sprint 4: Multi-Agent Analysis (Cont.) (Week 7-8)

- [ ] Implement Agent 4: Competitor Analyzer
- [ ] Implement Agent 5: Questionnaire Analyzer
- [ ] Implement Agent 6: Sales Coach Synthesizer
- [ ] Implement Agent 7: Customer Summary Generator
- [ ] Contract tests: Validate JSON outputs against schemas
- [ ] Performance test: Parallel execution <40s

### Sprint 5: Slack Integration (Week 9-10)

- [ ] Implement slack-service skeleton
- [ ] Implement `/錄音分析` slash command + upload modal
- [ ] Implement interactive Block Kit messages
- [ ] Implement button handlers (transcript, participants, questionnaire)
- [ ] Implement conversational AI follow-up
- [ ] Implement feedback modal
- [ ] Implement summary review workflow（thread @業務、修改提醒、送出按鈕）

### Sprint 6: Integration & Polish (Week 11-12)

- [ ] E2E test: Upload via Slack → Notification
- [ ] Google Sheets daily sync function
- [ ] GAS webhook compatibility layer
- [ ] Render customer summary HTML page（永久連結 + LINE 聯絡按鈕）
- [ ] Integrate SMS/Email delivery for summary links
- [ ] Audit Firestore writes for Agent 6/7 outputs
- [ ] Google Drive polling (Form submissions)
- [ ] Monitoring dashboards (Cloud Monitoring)
- [ ] Alert configuration (Slack + Email)

### Sprint 7: Migration & Launch (Week 13-14)

- [ ] Data migration script from V1
- [ ] Parallel run (V1 + V2 both active)
- [ ] User training (Slack usage guide)
- [ ] Production deployment
- [ ] Post-launch monitoring

---

## Complexity Tracking

*No Constitution violations requiring justification. All new requirements (multi-agent, speaker diarization, Slack-first) are essential to user stories and have been documented above.*

---

## User Decisions ✅ CONFIRMED

All key decisions have been confirmed by the user on 2025-01-29:

### 1. iCHEF Product Catalog for Agent 3 ✅

**Decision**: Use iCHEF official website (<https://www.ichefpos.com/>) as product catalog reference

**Product Catalog Structure**:

#### Core Products

1. **餐飲 POS 系統**
   - 解決痛點：提升出餐速度、減少人力依賴、即時營運掌控
   - 目標客群：小吃店、質感餐酒館、連鎖品牌

2. **線上訂位系統**
   - 解決痛點：接單效率提升 2 倍（從 30 組到 60 組/天）
   - 功能：預收訂金、實時管理、自動提醒

3. **掃碼點餐（QR Code）**
   - 業績提升：客單價 +$18
   - 使用者行為：27% 團體客各自用手機點餐

4. **雲端餐廳（Online Store）**
   - 解決痛點：建立自有流量，24 小時線上營業
   - 整合：Google、LINE 導流

5. **線上外帶/配送**
   - 解決痛點：不依賴外送平台，建立品牌自有流量

6. **總部系統**
   - 功能：多店管理、集中控管

#### Upgrade Path for Agent 3 Recommendations

- **新客入門**：POS 系統 + 線上訂位
- **成長驅動**：掃碼點餐 + 智慧推薦 → 客單價提升
- **擴張路徑**：雲端餐廳 → 總部系統（連鎖管理）

---

### 2. Discovery Questionnaire Templates (Agent 5) ✅

**Decision**: Option B - Prompt-based approach (no Firestore templates in MVP)

**Feature Categories (22 specific features across 6 categories)**:

#### 1️⃣ 點餐與訂單管理

- 掃碼點餐（QR Code 掃碼點餐）
- 多人掃碼點餐
- 套餐加價購
- 智慧菜單推薦
- POS 點餐系統
- 線上點餐接單

#### 2️⃣ 線上整合服務

- 線上訂位管理
- 線上外帶自取
- 雲端餐廳（Online Store）
- Google 整合
- LINE 整合
- 外送平台整合
- 聯絡式外帶服務

#### 3️⃣ 成本與庫存管理

- 成本控管
- 庫存管理
- 帳款管理

#### 4️⃣ 業績與銷售分析

- 銷售分析
- 報表生成功能

#### 5️⃣ 客戶關係管理

- 零秒集點（忠誠點數系統 2.0）
- 會員管理

#### 6️⃣ 企業級功能

- 總部系統
- 連鎖品牌管理

**Implementation**: Agent 5 system prompt will include complete feature list. Agent should flexibly detect any mentioned features from conversation.

---

### 3. Disaster Recovery Strategy ✅

**Decision**: Option A (Simple) - Wait for recovery, accept rare downtime

**Rationale**:

- Monthly volume is low (200-250 files)
- $0 extra cost
- Acceptable trade-off: Potential 1-2 hour downtime per year vs +$15-20/month

---

### 4. Questionnaire Prompt Design ✅

**Decision**: Current structure approved, iterate if issues arise

**Structure**:

- current_status（使用狀態）
- need_reasons（需求原因 + quotes + confidence）
- perceived_value（價值評估）
- barriers（阻礙因素）
- timeline（考慮時程）
- confidence scores（信心分數 0-100）

**User Feedback**: "沒問題，有問題再改"

---

### 5. Multi-Agent Architecture ✅

**Decision**: Approved - Use 6-agent architecture

**Confirmation**:

- Agents 1-5 execute in parallel
- Agent 6 synthesizes all results
- Cost: +$15/month acceptable
- Performance: +10-15 seconds acceptable
- Accuracy improvement: 15-20% justifies cost

**User Feedback**: "可以，請使用多 Agent"

---

## Next Steps

**Immediate**:

1. User reviews this plan and answers 5 open questions above
2. User reviews spec.md (already complete) for final approval
3. Decide: Proceed to Phase 0 (POCs) or skip to Phase 1 (design)?

**Recommended Sequence**:

1. **This Week**: Run POCs 1-6 (validate critical assumptions) → Output: `research.md`
2. **Next Week**: Detailed design (data models, prompts, contracts) → Output: `data-model.md`, `contracts/`, `quickstart.md`
3. **Week 3**: Create implementation tasks → Output: `tasks.md` (via `/speckit.tasks`)
4. **Week 4+**: Begin Sprint 1

**Alternative (Fast-Track)**:

- Skip POCs, proceed directly to implementation (higher risk if assumptions are wrong)
- Recommendation: **Do NOT skip POCs** - Speaker diarization performance and Gemini structured output quality are critical unknowns

**Backlog / TODO**:

- **POC 1b**: Cloud Storage leads ingestion → download → transcription pipeline → `sourceType=leads` tagging（待完成，暫時排在 POC 7 之後）
- **POC 1 (Slack)**: 上傳來源需標記 `sourceType=slack` + `stage=opportunity`，並驗證轉錄管線與 Firestore 寫入一致（排程於 POC 7 後統一調整）
- **Agent 6 & 7 Integration**: 已完成 prompt（agent6-coach.md, agent7-summary.md），尚需實作 Gemini 呼叫、結果驗證與 Firestore 寫入流程
- **Slack 摘要工作流**: Thread @業務 → 修訂 → `✅ 送出` 按鈕 → 產出客戶摘要頁面（永久連結）
- **摘要頁面與簡訊**: 建置 markdown→HTML 管線、LINE 聯絡按鈕、SMS/Email 發送與送達紀錄
- **測試強化**: Agent 6/7 實測（含語氣模擬）、POC6 prompt 迭代（提升正/負覆蓋率）、端到端自動化測試

---

## Cost Estimate Validation

### Monthly Cost Breakdown (250 files/month)

| Service | Unit Cost | Usage | Monthly Cost |
|---------|-----------|-------|--------------|
| **Cloud Run (Transcription)** | $0.00002400/vCPU-sec | 250 files × 240s × 2 vCPU | $28.80 |
| **Cloud Run (Analysis)** | $0.00002400/vCPU-sec | 250 files × 50s × 1 vCPU | $0.30 |
| **Cloud Run (Slack/Orchestration)** | $0.00002400/vCPU-sec | 250 files × 10s × 1 vCPU | $0.06 |
| **Gemini API Tokens** | $0.075/1M input, $0.30/1M output | 250 files × (10K input + 2K output) × 6 agents | $13.50 |
| **Firestore Reads** | $0.06/100K | 250 cases × 50 reads | $0.08 |
| **Firestore Writes** | $0.18/100K | 250 cases × 30 writes | $0.14 |
| **Firestore Storage** | $0.18/GB | 2GB (2 years of data) | $0.36 |
| **Cloud Storage** | $0.020/GB | 5GB (rolling 7 days) | $0.10 |
| **Cloud Tasks** | $0.40/1M tasks | 1000 tasks/month | $0.00 |
| **Cloud Functions** | $0.40/1M invocations | 500 invocations | $0.00 |
| **Networking** | $0.12/GB egress | 250 files × 80MB | $2.40 |
| **Cloud Logging** | $0.50/GB | 2GB/month | $1.00 |
| **Cloud Monitoring** | Free tier | <150 metrics | $0.00 |
| **TOTAL** | | | **$46.74** |

**Status**: ⚠️ Slightly over $45 budget

**Optimization Options** (if needed):

1. Reduce Gemini token usage (shorter prompts, fewer examples) → Save $2-3/month
2. Use Gemini 1.5 Flash-8B (cheaper model, slight quality trade-off) → Save $5-7/month
3. Reduce Cloud Run vCPU for transcription (1 vCPU instead of 2, slower but still <5min) → Save $14/month

**Recommendation**: Launch with current architecture, monitor actual costs, optimize only if exceeds $50/month.

---

**End of Plan**
