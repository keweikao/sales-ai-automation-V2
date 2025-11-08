# Sales AI Automation System Constitution

## Core Principles

### I. Cost Optimization First

**Principle**: Minimize operational costs through self-hosted solutions while maintaining high quality.

**Rationale**: With 200-250 audio files monthly (avg. 40 minutes each), using OpenAI Whisper API would cost $48-60/month. Self-hosting Faster-Whisper reduces costs to $20-30/month, achieving 60-70% savings.

**Implementation**:

- MUST use self-hosted Faster-Whisper for transcription
- MUST deploy on cost-effective serverless platforms (Cloud Run)
- MUST implement intelligent caching to avoid redundant processing
- MAY use GPU acceleration only when justified by performance requirements

**Success Metrics**: Monthly cost <$30, Cost per file <$0.15, 60%+ savings vs API solutions

### II. Performance & Scalability

**Principle**: System MUST handle parallel processing and scale automatically with workload.

**Rationale**: Current system processes serially (1 file at a time), taking 30-40 minutes total. Event-driven parallel processing can reduce this to 2-5 minutes.

**Implementation**:

- MUST support parallel processing of 10+ concurrent audio files
- MUST use event-driven architecture (no polling loops)
- MUST auto-scale based on workload (Cloud Run 0-10 instances)
- MUST support multiple audio sources (Google Drive, GCS) with unified pipeline

**Success Metrics**: Processing time 2-5 min, 10+ concurrent files, 99.5%+ uptime

### III. Multi-Source Integration

**Principle**: Seamlessly handle audio from multiple sources with unified processing pipeline.

**Rationale**: Different teams use different storage (iCHEF uses Google Drive, other units use GCS). System must support both without creating separate workflows.

**Implementation**:

- MUST support Google Drive and Google Cloud Storage
- MUST use unified queue system (Cloud Tasks) for all sources
- MUST implement source-agnostic processing logic
- SHOULD allow easy addition of new audio sources

### IV. Quality & Reliability

**Principle**: Maintain high transcription quality with automatic error handling and recovery.

**Implementation**:

- MUST implement quality scoring (0-100) for each transcription
- MUST support automatic retries (max 3) with exponential backoff
- MUST log all errors with full context for debugging
- MUST monitor key metrics (success rate, quality scores, processing time)
- SHOULD alert on quality degradation (>5% failure rate)

**Quality Thresholds**: Excellent 90-100, Good 75-89, Acceptable 60-74, Poor 40-59 (review), Failed 0-39 (retry)

### V. Chinese Language Optimization

**Principle**: Optimize specifically for Traditional and Simplified Chinese audio.

**Rationale**: Primary use case is Chinese sales calls. Generic models may have lower accuracy.

**Implementation**:

- MUST use Whisper models with proven Chinese accuracy
- MUST implement Chinese-specific audio preprocessing
- MUST handle code-switching (Chinese-English mixing)
- SHOULD fine-tune models if quality <85%

**Settings**: Primary language: zh, Fallback: auto-detect, Minimum confidence: 0.8

### VI. Traditional Chinese Communication

**Principle**: All user-facing content and assistant responses MUST default to Traditional Chinese.

**Rationale**: Stakeholders operate primarily in Traditional Chinese; consistent language usage prevents confusion and reduces translation overhead.

**Implementation**:

- MUST produce system prompts, Slack notifications, and documentation intended for users in Traditional Chinese.
- MUST configure AI agents to respond in Traditional Chinese unless explicitly instructed otherwise.
- SHOULD note language deviations (e.g., when quoting English text) to maintain clarity.

### VII. Activity Logging & Traceability

**Principle**: Every language model contributing to this project MUST provide auditable traces of its work (documentation, development, deployment) before a task is considered complete.

**Rationale**: Multiple AI assistants collaborate asynchronously; without consistent logs, knowledge is lost and subsequent agents cannot verify prior steps.

**Implementation**:

- MUST document each substantial action（撰寫／修改規格與文件、實作程式碼、測試、部署）於 `DEVELOPMENT_LOG.md` 的「活動紀錄」區段，包含日期、負責 AI 模型、輸出重點與後續待辦。
- MUST update狀態追蹤表（同檔案內的 Outstanding Work Tracker 或後續新增的相同功能文件）以勾選完成項目並標註證據（檔案與行號、相關 commit 或測試結果）。
- MUST 在提交 Pull Request、部署映像或對外發佈前再次記錄最終檢查結果與驗證步驟。
- MAY 補充更細的逐步紀錄於 `docs/activity-log/` 子目錄（若未來建立）但仍需於 `DEVELOPMENT_LOG.md` 摘要。

**Compliance**: 缺漏活動紀錄視為違反憲法流程，後續 AI 助理應優先補齊紀錄再繼續開發。

### VIII. Documentation Hygiene

**Principle**: All committed documentation MUST comply with the repository’s Markdown lint rules to prevent recurring CI failures and ensure readability.

**Implementation**:

- MUST ensure all headings are surrounded by single blank lines (MD022).
- MUST ensure all lists are surrounded by single blank lines (MD032).
- MUST NOT use multiple consecutive blank lines (MD012).
- MUST specify a language for every fenced code block (MD040).
- MUST resolve all reported linting issues before considering a task complete.
- SHOULD reference existing style guides (`DEVELOPMENT_GUIDELINES.md`, `docs/markdown-style.md` if present) when writing or updating docs.

**Compliance**: Pull requests or commits that introduce lint violations MUST be corrected before work is considered complete. Outstanding Work Tracker entries should reflect any lint fixes performed.

### IX. Automated Workflows & Input Handling

#### Log Detection & Auto-Archiving

1. **Detection**: When user input is received, analyze it for log/error characteristics (e.g., length > 20 lines, presence of keywords like `Traceback`, `Exception`, `[ERROR]`).
2. **Auto-Archiving**: If the input is identified as a log, immediately save the full content to a temporary file at `tmp/auto_log_<timestamp>.log`.
3. **Confirmation & Analysis**:
    - Respond to the user with a brief confirmation, acknowledging the detection and providing the path to the saved file.
    - Immediately invoke the `speckit-debugger` subagent to analyze the newly created file in the background.
    - Present the concise analysis from the subagent as the final response.
    - This ensures the large log content is removed from the conversational context for subsequent turns, optimizing token usage.

#### Proactive Subagent Recommendation (SOP)

1. **Analyze Intent**: Upon receiving a user request, first analyze the user's intent (e.g., implementation, research, testing, planning).
2. **Propose Action**: Instead of executing immediately, formulate a plan and propose the use of the most appropriate subagent(s) or workflow(s).
3. **Await Confirmation**: The proposal must be presented to the user for confirmation. The response should be phrased as a clear question, awaiting an affirmative response (e.g., "同意", "ok").
4. **Execute on Approval**: Only after receiving explicit user confirmation, proceed with the execution of the proposed subagent or workflow.
5. **Exception**: This SOP does not apply to fully automated workflows that have their own explicit triggers, such as the "Log Detection & Auto-Archiving" rule.

## Integration Requirements

### Backward Compatibility

- MUST maintain compatibility with existing Google Apps Script webhooks
- MUST support existing Google Sheets data structure
- MUST preserve current Slack notification format
- MUST allow gradual migration (run both systems in parallel)

### Integration Points

- Google Apps Script (webhook callbacks)
- Google Sheets (data sync)
- Slack API (notifications)
- Gemini AI (analysis)

## Security & Privacy

### Data Protection

- MUST process all audio on GCP (no third-party APIs for transcription)
- MUST use service accounts with minimal required permissions
- MUST encrypt data in transit (HTTPS) and at rest
- MUST implement access logging for audit trails
- MUST auto-delete audio files after processing (configurable retention: 7-90 days)

### Security Requirements

- Service accounts follow principle of least privilege
- No API keys in code (use Secret Manager)
- All endpoints require authentication
- Regular security audits

## Technology Standards

### Approved Stack

**Backend**: Cloud Run, Cloud Functions, Firestore, Cloud Tasks, Cloud Storage
**AI/ML**: Faster-Whisper (transcription), Google Gemini API (analysis)
**Integration**: Google Apps Script, Slack API, Google Sheets API
**Languages**: Python 3.11+, TypeScript

### Prohibited Patterns

❌ OpenAI Whisper API (cost too high)
❌ Always-on servers (use serverless)
❌ Polling loops (use event triggers)
❌ Hardcoded credentials (use Secret Manager)
❌ Synchronous processing chains (use queues)

### 轉錄管線基線配置

- **必備依賴**：部署或本地測試前必須安裝 `torch>=2.9.0`、`torchaudio>=2.9.0`、`faster-whisper==1.2.0`、`tqdm==4.65.0`、`requests`，以及系統層級的 `ffmpeg`（提供 `ffprobe`）。
- **資源限制策略**：若執行環境為 CPU 且記憶體不足以支撐 `small` 以上模型，POC 及回歸測試應先以 `tiny` 模型 + `workers=1` 確認流程可完整跑通，再評估升級模型或調整參數。
- **錯誤預防**：禁止向 `faster-whisper` 傳入已移除的 VAD 參數（如 `window_size_samples`），避免因版本差異導致所有分段失敗。
- **執行驗證**：每次更新管線或環境後，必須重新執行 POC1 長音檔測試並將結果輸出到 `poc1_optimized_results.json`，以確保速度與品質門檻仍達標。

## Development Workflow

1. **Specification First**: Define requirements in spec.md, clarify ambiguities, get approval
2. **Technical Planning**: Document architecture in plan.md, define APIs in contracts/, review
3. **Task Breakdown**: Create detailed tasks.md, identify dependencies, estimate effort
4. **Implementation**: Follow TDD for critical paths, document as you go
5. **Review & Deploy**: Code review required, integration tests, staging first, monitor

## Observability

### Required Monitoring

- MUST log all processing stages with structured logging
- MUST emit metrics (Cloud Monitoring)
- MUST set up alerts for critical failures
- SHOULD create dashboards for key metrics

### Key Metrics

- Transcription success rate
- Average processing time
- Quality score distribution
- Error rates by stage
- Cost per transaction

## Governance

This constitution supersedes all other development practices and decisions. All pull requests and code reviews MUST verify compliance with these principles.

**Amendment Process**: Changes require documentation of rationale, impact assessment, team approval, and updating of dependent templates.

**Compliance Review**: All features MUST comply with core principles, meet quality thresholds, include tests, be documented, and pass security review.

**Version**: 1.0.1 | **Ratified**: 2025-10-27 | **Last Amended**: 2025-10-30
