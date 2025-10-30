# Feature Specification: Sales AI Automation System V2.0

**Feature Branch**: `001-sales-ai-automation`
**Created**: 2025-10-27
**Last Updated**: 2025-01-29
**Status**: Draft
**Input**: Build a scalable, cost-optimized sales AI automation system that supports multiple audio sources (Google Drive, GCS, Slack), performs automated transcription with speaker diarization using self-hosted Whisper, multi-agent AI analysis using Gemini for deep insights (participant profiling, sentiment analysis, product needs extraction, competitor intelligence), and delivers interactive experiences via Slack with conversational AI follow-up.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Audio Upload with Speaker Diarization (Priority: P1)

**As a** sales representative
**I want to** upload my sales call recording and have it automatically transcribed with speaker identification
**So that** I can see who said what during the conversation, enabling better analysis of participant roles and dynamics

**Why this priority**: This is the foundational capability - without reliable transcription and speaker separation, no downstream analysis (especially participant profiling) is possible. Speaker diarization enables identification of decision makers vs. influencers.

**Independent Test**: Upload a 40-minute Chinese sales call with 2-3 participants via Slack. System should detect the upload, process it with speaker separation, and return accurate transcription with speaker labels (Speaker 1, Speaker 2, Speaker 3) within 5 minutes. Can be verified by checking transcription quality and speaker boundary accuracy.

**Acceptance Scenarios**:

1. **Given** a sales rep has recorded a sales call on iPhone (m4a format, Chinese language) with 2-3 participants
   **When** they click the 'Upload Audio' button in the designated Slack channel, fill out the Customer ID and Store Name, and upload the file
   **Then** system should:
   - Immediately acknowledge upload with case ID
   - Send real-time progress updates in Slack thread
   - Download and queue the file for processing
   - Transcribe using Whisper with speaker diarization enabled
   - Identify and label distinct speakers (Speaker 1, 2, 3...)
   - Calculate speaking time percentage for each participant
   - Return text with >85% quality score
   - Complete within 5 minutes
   - Update Slack with completion notification

2. **Given** an audio file from another unit stored in GCS bucket
   **When** the file is uploaded to the designated GCS bucket
   **Then** system should:
   - Trigger automatically via Cloud Storage event
   - Process identically to Google Drive files
   - Extract case metadata from filename
   - Store results in same Firestore collection

3. **Given** multiple audio files uploaded simultaneously (10+ files)
   **When** all files are queued for processing
   **Then** system should:
   - Process them in parallel (not serially)
   - Complete all 10 files within 10 minutes total
   - Maintain quality standards for all transcriptions

---

### User Story 2 - Participant Profile Analysis (Priority: P1)

**As a** sales representative
**I want to** automatically identify and profile each participant in the sales call
**So that** I can understand who the decision makers are, their personality types, concerns, and influence levels

**Why this priority**: Understanding participant dynamics is critical for sales strategy. Knowing who has decision power, what their concerns are, and how to approach each person dramatically improves conversion rates.

**Independent Test**: Process a sales call with 3 participants (owner, manager, observer). System should correctly identify each person's likely role, personality traits, speaking patterns, and decision influence within 45 seconds of transcription completion.

**Acceptance Scenarios**:

1. **Given** a transcription with speaker diarization completed (3 speakers identified)
   **When** participant analysis agent processes the transcript
   **Then** system should:
   - Assign likely role to each speaker (e.g., "老闆/決策者", "店長/使用者", "觀察者")
   - Determine personality type (analytical, driver, amiable, expressive)
   - Extract key concerns and interests for each participant
   - Calculate decision power score (0-100) for each person
   - Identify key phrases that reveal their priorities
   - Mark primary vs. secondary influencers
   - Complete analysis within 30 seconds
   - Store structured results in Firestore

2. **Given** participant profiles are generated
   **When** displayed in Slack notification
   **Then** system should:
   - Show participant summary in interactive card
   - Highlight the primary decision maker
   - Display speaking time percentage
   - List key concerns per participant
   - Provide role confidence scores

---

### User Story 3 - Sentiment and Attitude Analysis (Priority: P1)

**As a** sales representative
**I want to** understand the emotional tone and buying signals throughout the conversation
**So that** I can gauge customer interest level, identify objections early, and adjust my approach

**Why this priority**: Sentiment analysis reveals hidden insights that text alone cannot provide - detecting hesitation, growing interest, or resistance helps sales reps adapt their strategy in real-time for follow-ups.

**Independent Test**: Process a sales call where customer starts curious (0-10min), becomes interested (10-25min), then hesitant (25-40min). System should detect this emotion curve and identify specific buying/objection signals.

**Acceptance Scenarios**:

1. **Given** a transcription is completed
   **When** sentiment analysis agent processes the transcript
   **Then** system should:
   - Assign overall sentiment (positive, neutral, negative) with confidence score
   - Generate emotion curve across conversation timeline
   - Calculate trust level (0-100) toward sales rep/brand
   - Calculate engagement level (0-100) based on participation
   - Identify buying signals with strength (strong/medium/weak) and timestamps
   - Identify objection signals with severity (high/medium/low) and timestamps
   - Complete analysis within 20 seconds
   - Store structured results in Firestore

2. **Given** sentiment analysis is completed
   **When** displayed in Slack notification
   **Then** system should:
   - Show overall sentiment with visual indicator (emoji/color)
   - Display emotion curve as timeline
   - Highlight strongest buying signals
   - Flag critical objections that need addressing
   - Suggest when to follow up based on sentiment trends

---

### User Story 4 - Product Needs Extraction and Recommendations (Priority: P1)

**As a** sales representative
**I want to** automatically extract explicit and implicit product needs from the conversation
**So that** I can recommend the right products, prepare accurate quotes, and address all customer requirements

**Why this priority**: Manually identifying all customer needs is error-prone and time-consuming. Automated extraction ensures no requirement is missed, and product recommendations are data-driven, increasing proposal accuracy and win rates.

**Independent Test**: Process a sales call where customer explicitly mentions "點單自動化" and implicitly reveals "尖峰時段人手不足". System should identify both needs, map to appropriate products (POS 基礎版 and POS 進階版), estimate budget range, and determine decision timeline.

**Acceptance Scenarios**:

1. **Given** a transcription is completed
   **When** needs extraction agent processes the transcript
   **Then** system should:
   - Extract explicit needs with supporting quotes from conversation
   - Infer implicit needs from mentioned pain points
   - Map each need to recommended product with fit score (perfect/good/moderate)
   - Estimate budget range and flexibility level
   - Determine payment preference (full/installment/subscription)
   - Identify decision urgency and expected timeline
   - Extract price anchoring references (competitor pricing mentioned)
   - Complete analysis within 25 seconds
   - Store structured results in Firestore

2. **Given** product needs are extracted
   **When** displayed in Slack notification
   **Then** system should:
   - Show primary needs with priority levels
   - Display recommended product bundles
   - Indicate budget estimate with confidence
   - Show decision timeline and urgency
   - Provide pricing strategy suggestions

---

### User Story 5 - Competitor Intelligence Analysis (Priority: P1)

**As a** sales representative
**I want to** automatically identify competitors mentioned in conversations and extract competitive insights
**So that** I can understand our competitive position and develop effective counter-strategies

**Why this priority**: Competitor intelligence is often buried in conversation details. Automated extraction ensures sales reps know exactly which competitors they're up against, what customers think of them, and how to position our advantages.

**Independent Test**: Process a sales call where customer mentions "之前用XX POS" and says "便宜但功能不足". System should identify competitor, extract customer opinions (pros/cons), determine relationship status (past user), and suggest winning strategies.

**Acceptance Scenarios**:

1. **Given** a transcription is completed
   **When** competitor analysis agent processes the transcript
   **Then** system should:
   - Identify all competitors mentioned by name
   - Count mention frequency for each competitor
   - Extract context around each mention
   - Categorize customer opinions (pros/cons)
   - Assess overall satisfaction with competitor (0-100)
   - Determine relationship status (current user/past user/evaluating/heard about)
   - Identify our competitive advantages based on customer pain points
   - Suggest winning strategy and key messages
   - Calculate conversion probability from competitor
   - Complete analysis within 20 seconds
   - Store structured results in Firestore

2. **Given** competitor analysis is completed
   **When** displayed in Slack notification
   **Then** system should:
   - List competitors mentioned with mention counts
   - Show customer satisfaction scores
   - Highlight our advantages vs. each competitor
   - Provide recommended positioning strategy
   - Display conversion probability

---

### User Story 6 - Discovery Questionnaire Auto-Completion (Priority: P1)

**As a** sales representative
**I want to** automatically complete discovery questionnaires based on conversation content without manual data entry
**So that** I can focus on the conversation while the system captures all feature-specific needs, barriers, and adoption intent

**Why this priority**: Manual questionnaire completion is time-consuming and often incomplete. Sales reps may forget to ask certain questions or fail to record responses accurately. Automated extraction ensures comprehensive, consistent data collection for every sales call, enabling better product-market fit analysis and sales strategy.

**Independent Test**: Process a sales call where customer discusses QR code ordering ("掃碼點餐") - mentions they don't use it because "客人都是老人家不會用", but sees value in "省人力", with medium willingness if "價格合理". System should automatically extract and structure this as questionnaire responses with confidence scores.

**Acceptance Scenarios**:

1. **Given** a transcription is completed with discussion about specific features (e.g., 掃碼點餐)
   **When** discovery questionnaire agent processes the transcript
   **Then** system should:
   - Detect which features/topics were discussed
   - For each topic, extract structured questionnaire responses:
     - Current usage status (使用/未使用/考慮中/曾使用過)
     - Need assessment (有需求/無需求/未明確)
     - Reasons for needing (with supporting quotes and confidence scores)
     - Reasons for not needing (with supporting quotes and confidence scores)
     - Perceived product value (0-100 score + positive/negative aspects)
     - Implementation willingness (high/medium/low/none)
     - Adoption barriers (budget/technology/personnel/timing/other with severity)
     - Consideration timeline (urgency and expected decision time)
   - Handle implicit responses (infer from context)
   - Calculate completeness score for each questionnaire
   - Complete analysis within 25 seconds
   - Store structured results in Firestore

2. **Given** questionnaire analysis is completed
   **When** displayed in Slack notification
   **Then** system should:
   - Show questionnaire summary for each feature discussed
   - Highlight key findings (strong needs, major barriers)
   - Display completeness score
   - Indicate confidence levels
   - Flag missing critical information (suggest follow-up questions)

3. **Given** multiple features discussed in single conversation
   **When** processing questionnaire responses
   **Then** system should:
   - Generate separate questionnaire results for each feature
   - Cross-reference responses (e.g., budget barrier mentioned for multiple features)
   - Prioritize features by implementation willingness + perceived value
   - Suggest bundling strategy if applicable

4. **Given** questionnaire templates are configurable
   **When** admin defines custom questionnaire for new feature
   **Then** system should:
   - Support template definition (feature name, key questions, expected data structure)
   - Apply new template to future conversations automatically
   - Store template in Firestore for reuse
   - Allow A/B testing different questionnaire formats

---

### User Story 7 - Comprehensive Sales Coaching (Multi-Agent Synthesis) (Priority: P1)

**As a** sales representative
**I want to** receive comprehensive, actionable coaching that synthesizes all analysis dimensions (participants, sentiment, needs, competitors, questionnaires)
**So that** I can get clear guidance on next steps, risk mitigation, and sales strategies tailored to this specific deal

**Why this priority**: The sales coaching agent synthesizes all specialized analyses into actionable recommendations. This is the final "so what?" that transforms data into decisions, directly impacting conversion rates and deal velocity.

**Independent Test**: Given completed analyses from all agents (participant, sentiment, needs, competitor, questionnaire), trigger sales coach synthesis. System should generate integrated coaching with prioritized next steps, tailored talk tracks, risk mitigation strategies, and recommended product bundle within 20 seconds.

**Acceptance Scenarios**:

1. **Given** all specialized analyses are completed (participant, sentiment, needs, competitor, questionnaire)
   **When** sales coach agent receives all analysis results
   **Then** system should:
   - Identify key decision maker and their primary concerns
   - Assess overall deal health based on sentiment + buying signals
   - Recommend optimal product bundle based on needs + budget + questionnaire insights
   - Generate competitive positioning strategy if competitors mentioned
   - Integrate questionnaire findings into strategy (e.g., if QR ordering has low willingness, deprioritize)
   - Determine sales stage (立即報價型/需要證明型/教育培養型/時機未到型)
   - Identify maximum risk (why deal might be lost)
   - Provide 3 prioritized next actions with specific timelines
   - Generate tailored talk tracks for addressing objections AND missing questionnaire info
   - Suggest risk mitigation strategies
   - Include sales rep performance feedback
   - Complete synthesis within 20 seconds
   - Store comprehensive coaching in Firestore

2. **Given** sales coaching is completed
   **When** preparing Slack notification
   **Then** system should:
   - Format coaching in clear, actionable sections
   - Highlight most critical insights (decision maker, stage, risk, questionnaire gaps)
   - Include interactive buttons for deep dive sections
   - Prepare context for follow-up AI conversations
   - Show questionnaire completeness and suggest follow-up questions

---

### User Story 8 - Interactive Slack Experience and Conversational AI (Priority: P1)

**As a** sales representative
**I want to** receive analysis results via interactive Slack messages and ask follow-up questions in natural language
**So that** I can quickly review insights, dive deeper into specific areas, and get coaching without leaving Slack

**Why this priority**: Slack-first architecture eliminates context switching and enables instant, conversational follow-up. Interactive messages with buttons reduce friction, and AI-powered Q&A provides personalized coaching on demand, dramatically improving engagement and adoption.

**Independent Test**: Complete an analysis and verify that sales rep receives interactive Slack card with analysis summary, can click buttons to view detailed sections, and can ask "這個客戶適合哪個價格方案?" and receive contextual answer within 5 seconds.

**Acceptance Scenarios**:

1. **Given** all AI analyses are completed for case "202501-IC001"
   **When** synthesis is stored in Firestore
   **Then** system should:
   - Look up sales rep's Slack ID from User_Mapping (by email)
   - Send interactive Slack Block Kit message to sales rep's DM
   - Include interactive card with:
     - Case header (customer name, ID, participants count, sentiment indicator)
     - Collapsible analysis sections (participants, sentiment, needs, competitors, questionnaires, coaching)
     - Action buttons: [📄 完整逐字稿] [🎯 參與者詳情] [📋 問卷結果] [💬 追問 AI] [⭐ 給回饋]
     - Key insights highlighted (decision maker, stage, top risk, next action, questionnaire completeness)
     - Questionnaire summary (features discussed, completeness %, critical gaps)
   - Message delivered within 1 minute
   - Store Slack thread_ts for future reference
   - Log delivery status in Firestore

2. **Given** sales rep clicks [💬 追問 AI] button
   **When** button is clicked
   **Then** system should:
   - Show ephemeral message: "請直接在此對話中輸入您的問題"
   - Enable conversational mode for this thread
   - Wait for sales rep to type question

3. **Given** sales rep asks "這個客戶適合哪個價格方案?" in the analysis thread
   **When** message is received in Slack
   **Then** system should:
   - Detect message is in case thread (by thread_ts)
   - Retrieve full case context from Firestore
   - Send question + context to Gemini conversational agent
   - Stream response back to Slack thread within 5 seconds
   - Store conversation in Firestore conversations array
   - Log tokens used

4. **Given** sales rep clicks [⭐ 給回饋] button
   **When** button is clicked
   **Then** system should:
   - Open Slack modal with feedback form
   - Pre-fill case ID automatically
   - Show fields:
     - AI 準確度 (1-5 stars slider)
     - 成交狀態 (radio: won/lost/tracking)
     - 補充說明 (optional text)
   - Enable one-click submission

5. **Given** sales rep submits feedback via Slack modal
   **When** modal is submitted
   **Then** system should:
   - Store feedback in Firestore `feedback` object
   - Sync to Google Sheets
   - Show confirmation message
   - Update case status to "feedback_received"
   - Log timestamp

---

### User Story 4 - Quality Monitoring and Auto-Retry (Priority: P2)

**As a** system administrator
**I want** automatic quality monitoring and retry for failed/low-quality transcriptions
**So that** the system maintains high reliability without manual intervention

**Why this priority**: P2 because basic functionality can work without it, but it's essential for production reliability and cost control (avoiding wasted processing).

**Independent Test**: Submit a corrupted audio file or very low-quality recording. System should detect poor quality, retry with adjusted parameters, and alert if quality remains poor after 3 attempts.

**Acceptance Scenarios**:

1. **Given** transcription completes with quality score <60
   **When** quality check runs
   **Then** system should:
   - Mark status as "low_quality"
   - Increment retry_count
   - Re-queue for processing with adjusted parameters
   - Try up to 3 times total
   - If still <60, mark as "failed" and alert admin

2. **Given** transcription fails due to download error
   **When** error is caught
   **Then** system should:
   - Log detailed error (file ID, error message, timestamp)
   - Wait 60 seconds (exponential backoff)
   - Retry download and transcription
   - Update Google Sheets with current status

3. **Given** system processes 100 files in a day
   **When** checking daily quality metrics
   **Then** system should:
   - Calculate success rate (files with quality >75)
   - Alert if success rate <95%
   - Generate quality report showing distribution

---

### User Story 5 - Cost Tracking and Optimization (Priority: P2)

**As a** system administrator
**I want to** track per-file and monthly costs
**So that** I can ensure the system stays within budget and optimize resource usage

**Why this priority**: P2 because system can function without cost tracking, but it's important for long-term sustainability and justifying the migration from old system.

**Independent Test**: Process 10 files and verify that cost data (Cloud Run execution time, Firestore operations, Gemini API calls) is logged and aggregated correctly. Monthly total should be visible in dashboard.

**Acceptance Scenarios**:

1. **Given** a file is fully processed (transcription + analysis)
   **When** processing completes
   **Then** system should log:
   - Cloud Run execution time (seconds)
   - Estimated compute cost
   - Firestore reads/writes
   - Gemini API tokens used
   - Storage costs
   - Total estimated cost for this file

2. **Given** month-end reporting
   **When** querying cost metrics
   **Then** system should provide:
   - Total files processed
   - Total cost breakdown by service
   - Average cost per file
   - Comparison to budget ($30/month target)
   - Alert if trending over budget

---

### User Story 6 - Admin Dashboard for Monitoring (Priority: P3)

**As a** system administrator
**I want to** view real-time status of processing queue and system health
**So that** I can quickly identify and resolve issues

**Why this priority**: P3 because Cloud Monitoring provides basic visibility. A custom dashboard improves UX but isn't essential for MVP.

**Independent Test**: Access dashboard URL and verify it shows current queue depth, recent processing history, success rates, and system health metrics without requiring manual log searching.

**Acceptance Scenarios**:

1. **Given** user accesses admin dashboard
   **When** page loads
   **Then** dashboard should display:
   - Current queue depth (pending, processing, completed)
   - Last 24h processing metrics (total, success rate, avg time)
   - Recent failures with error messages
   - System health indicators (Cloud Run status, Firestore connection)

2. **Given** an error occurs during processing
   **When** viewing dashboard
   **Then** should see:
   - Error highlighted in red
   - Case ID and error details
   - Retry status
   - Link to full logs in Cloud Logging

---

### Edge Cases

- **What happens when audio file is >2 hours long?**
  System should split into 30-minute chunks, process separately, then concatenate transcriptions. Alert user if any chunk fails.

- **What happens when sales rep email is not found in User_Mapping?**
  System should log warning, skip Slack notification, but still complete transcription and analysis. Admin receives alert to update User_Mapping.

- **What happens when Google Drive API quota is exceeded?**
  System should catch quota error, wait according to quota reset time, and retry. Do not fail the job; queue for later retry.

- **What happens when same audio file is uploaded twice?**
  System should detect duplicate by checking case_id + file hash. Skip processing if already exists. Option to force re-process if explicitly requested.

- **What happens when Gemini API is temporarily unavailable?**
  Transcription completes normally. Analysis queued separately and retries with exponential backoff. User notified when analysis completes (may be delayed).

- **What happens during GCP region outage?**
  [需要補充: 您希望有 disaster recovery 嗎？例如自動切換到其他 region，或只是等待恢復？]

- **What happens when audio quality is so poor that Whisper returns gibberish?**
  Quality scoring detects low confidence. System flags for manual review. Option to notify uploader that audio quality is insufficient.

- **What happens when storage quota is full?**
  [需要補充: Firestore 和 Cloud Storage 的 quota 限制？是否需要自動清理舊檔案？]

## Requirements *(mandatory)*

### Functional Requirements

#### Audio Processing
- **FR-001**: System MUST support audio uploads from Google Drive (via Google Form submission)
- **FR-002**: System MUST support audio uploads from Google Cloud Storage (via bucket upload)
- **FR-003**: System MUST support audio formats: m4a, mp3, wav, flac
- **FR-004**: System MUST handle audio files up to 2 hours in length
- **FR-005**: System MUST automatically detect new audio files within 30 seconds of upload
- **FR-006**: System MUST extract metadata from filename (case ID, customer name, date) using pattern: `YYYYMM-UNITID_CustomerName.ext`

#### Transcription
- **FR-007**: System MUST use self-hosted Faster-Whisper (not OpenAI API) for transcription
- **FR-007a**: System MUST enable speaker diarization to identify and label distinct speakers
- **FR-007b**: System MUST calculate speaking time percentage for each identified speaker
- **FR-007c**: System MUST segment transcript by speaker with timestamps
- **FR-008**: System MUST optimize transcription for Chinese language (Traditional and Simplified)
- **FR-009**: System MUST handle code-switching (mixed Chinese-English speech)
- **FR-010**: System MUST assign quality score (0-100) to each transcription based on:
  - Language detection confidence
  - Text coherence
  - Character-to-time ratio
  - Repetition detection
  - Speaker separation accuracy (if multiple speakers)
- **FR-011**: System MUST complete transcription with speaker diarization within 5 minutes per 40-minute audio file (0.125x real-time)
- **FR-012**: System MUST support parallel processing of 10+ audio files simultaneously

#### AI Analysis (Multi-Agent Architecture)
- **FR-013**: System MUST implement multi-agent architecture with specialized analysis agents
- **FR-013a**: System MUST use Google Gemini 1.5 Flash API for all agent inference
- **FR-013b**: System MUST orchestrate agent execution (parallel + sequential as needed)

##### Agent 1: Participant Profile Analyzer
- **FR-014**: System MUST analyze each identified speaker to determine:
  - Likely role (老闆/決策者, 店長/使用者, 財務主管, 觀察者, etc.)
  - Personality type (analytical, driver, amiable, expressive)
  - Key concerns and interests
  - Decision power score (0-100)
  - Influence level (primary, secondary, observer)
  - Key phrases revealing priorities
  - Role confidence score
- **FR-014a**: System MUST complete participant analysis within 30 seconds
- **FR-014b**: Analysis MUST be stored in structured format in Firestore `analysis.participants[]`

##### Agent 2: Sentiment & Attitude Analyzer
- **FR-015**: System MUST analyze conversation sentiment and emotional dynamics:
  - Overall sentiment (positive/neutral/negative) with confidence score
  - Emotion curve across conversation timeline (multiple time segments)
  - Trust level (0-100) toward sales rep/brand
  - Engagement level (0-100) based on participation patterns
  - Technology adoption/comfort level (0-100) toward proposed solutions
  - Buying signals with strength (strong/medium/weak) and timestamps
  - Objection signals with severity (high/medium/low) and timestamps
- **FR-015a**: System MUST complete sentiment analysis within 20 seconds
- **FR-015b**: Analysis MUST be stored in structured format in Firestore `analysis.sentiment`

##### Agent 3: Product Needs Extractor
- **FR-016**: System MUST extract and structure customer product needs:
  - Explicit needs with supporting quotes from transcript
  - Implicit needs inferred from pain points
  - Recommended products with fit scores (perfect/good/moderate)
  - Budget estimation (range, flexibility, payment preference)
  - Decision timeline (urgency, expected decision date, driving factors)
  - Price anchoring references (competitor pricing mentioned)
  - Price sensitivity assessment
- **FR-016a**: System MUST map needs to specific iCHEF products (requires product catalog)
- **FR-016b**: System MUST complete needs extraction within 25 seconds
- **FR-016c**: Analysis MUST be stored in structured format in Firestore `analysis.productNeeds`

##### Agent 4: Competitor Intelligence Analyzer
- **FR-017**: System MUST analyze competitive landscape from conversation:
  - Identify all competitors mentioned by name
  - Count mention frequency for each competitor
  - Extract context around each mention
  - Categorize customer opinions (pros/cons)
  - Assess customer satisfaction with competitor (0-100)
  - Determine relationship status (current_user/past_user/evaluating/heard_about)
  - Identify our competitive advantages based on pain points
  - Suggest winning strategy and key messages
  - Calculate conversion probability from competitor
- **FR-017a**: System MUST complete competitor analysis within 20 seconds
- **FR-017b**: Analysis MUST be stored in structured format in Firestore `analysis.competitors`

##### Agent 5: Discovery Questionnaire Analyzer
- **FR-017c**: System MUST automatically extract discovery questionnaire responses from conversation:
  - Feature-specific adoption status and intent
  - Customer's current situation (使用/未使用/考慮中)
  - Motivation behind adoption (為什麼需要/為什麼不需要)
  - Perceived product value (對產品的價值評估)
  - Implementation willingness (導入意願: 高/中/低/無)
  - Adoption barriers (阻礙因素: 預算/技術/人員/時機/其他)
  - Timeline for consideration (預計評估/決策時間)
  - Supporting quotes from conversation
- **FR-017d**: System MUST use prompt-based approach to detect and extract questionnaire for iCHEF feature categories:
  - **點餐與訂單管理**: 掃碼點餐、多人掃碼、套餐加價購、智慧菜單推薦
  - **線上整合服務**: 線上訂位、線上外帶、雲端餐廳、外送平台整合
  - **成本與庫存**: 會計系統、庫存管理、成本控管
  - **業績分析**: 銷售分析報表、經營數據管理
  - **客戶關係**: 零秒集點、會員管理系統
  - **企業級功能**: 總部系統、連鎖品牌管理
  - **其他功能**: Agent 應能靈活識別對話中提到的任何 iCHEF 功能
- **FR-017da**: Agent prompt MUST include complete iCHEF product catalog for context
- **FR-017db**: Admin MAY update Agent 5 prompt to adjust questionnaire focus without code changes
- **FR-017e**: For each questionnaire topic, agent MUST extract:
  ```yaml
  questionnaire:
    topic: "掃碼點餐"
    current_status: "未使用" | "使用中" | "考慮中" | "曾使用過"
    has_need: true | false | "未明確表態"
    need_reasons:
      - reason: "人手不足，希望客人自助點餐"
        quote: "尖峰時段真的忙不過來"
        confidence: 85
    no_need_reasons:
      - reason: "客群年紀大，不習慣掃碼"
        quote: "我們客人都是老人家"
        confidence: 90
    perceived_value:
      score: 75  # 0-100
      aspects:
        - aspect: "省人力"
          sentiment: "positive"
        - aspect: "擔心客人不會用"
          sentiment: "negative"
    implementation_willingness: "medium"  # high/medium/low/none
    barriers:
      - type: "budget"
        severity: "high"
        detail: "覺得月費太貴"
      - type: "customer_adoption"
        severity: "medium"
        detail: "擔心客人不習慣"
    timeline:
      consideration: "3-6個月內"
      urgency: "low"
    additional_context: "想先看其他店家使用情況"
  ```
- **FR-017f**: System MUST detect multiple questionnaire topics in single conversation
- **FR-017g**: System MUST handle implicit responses (infer from context even if not directly asked)
- **FR-017h**: System MUST calculate completeness score (% of questions answered)
- **FR-017i**: System MUST complete questionnaire analysis within 25 seconds
- **FR-017j**: Analysis MUST be stored in structured format in Firestore `analysis.discoveryQuestionnaires[]`

##### Agent 6: Sales Coach Synthesizer
- **FR-018**: System MUST synthesize all agent outputs into actionable coaching:
  - Identify key decision maker and their primary concerns
  - Assess overall deal health score (0-100)
  - Recommend optimal product bundle with pricing strategy
  - Generate competitive positioning if competitors present
  - Determine sales stage (立即報價型/需要證明型/教育培養型/時機未到型)
  - Identify maximum risk (why deal might be lost)
  - Provide 3 prioritized next actions with specific deadlines
  - Generate tailored talk tracks for addressing each objection
  - Suggest risk mitigation strategies
  - Include sales rep performance feedback
- **FR-018a**: System MUST preserve original v7.0 prompt coaching output for comparison
- **FR-018b**: System MUST complete synthesis within 20 seconds
- **FR-018c**: Coaching MUST be stored in Firestore `analysis.structured` and `analysis.rawOutput`

##### Agent 7: Customer Summary Generator
- **FR-018d**: System MUST產出可直接提供給客戶的摘要文件，內容需包含：
  - 會議整體結論（2-3 句專業、易讀的繁體中文摘要）
  - 雙方確認的重點決議與亮點（列表，每項需附對應說話者與時間戳/引用）
  - 待跟進事項，分為 `customer_actions[]` 與 `ichef_actions[]`，每項包含負責人、預計完成日或追蹤節點
  - 下一步會議/里程碑與預計時間（若未確認需給出建議追蹤時間）
  - 聯絡窗口資訊（客戶主要聯絡人與 iCHEF 專案負責人）
- **FR-018e**: 摘要 MUST 以標準 Markdown 結構輸出，至少包含章節：`## 摘要`、`## 重點決議`、`## 待跟進事項`、`## 下一步`、`## 聯絡窗口`。
- **FR-018f**: 系統 MUST 將摘要儲存在 Firestore `analysis.customerSummary`，資料結構如下：
  ```json
  {
    "summary": "string",
    "keyDecisions": [
      {
        "title": "string",
        "speakerId": "Speaker 2",
        "timestamp": "00:23:45",
        "quote": "重點引用"
      }
    ],
    "nextSteps": {
      "customer": [
        { "description": "安排門市試用", "owner": "張總", "dueDate": "2025-11-05" }
      ],
      "ichef": [
        { "description": "寄送報價與比較表", "owner": "王小美", "dueDate": "2025-11-02" }
      ]
    },
    "upcomingMilestone": {
      "status": "scheduled",
      "date": "2025-11-08",
      "note": "試營運成效回顧"
    },
    "contacts": {
      "customer": "張總 / 0900-***-*** / Line: xxxx",
      "ichef": "王小美 (AM)"
    }
  }
  ```
- **FR-018g**: Agent MUST 完成摘要生成於 15 秒內，允許參考 Agents 1-6 的結構化輸出與原始轉錄文本。
- **FR-018h**: 摘要語氣 MUST 保持客觀專業、避免過度銷售語句，並明確標示接下來需要客戶配合的事項。

##### Multi-Agent Orchestration
- **FR-019**: System MUST execute agents in optimal sequence:
  - Step 1: Transcription + Speaker Diarization (2-3 min)
  - Step 2: Agents 1-5 in parallel (30-40 sec total)
    - Agent 1: Participant Analyzer (30 sec)
    - Agent 2: Sentiment Analyzer (20 sec)
    - Agent 3: Needs Extractor (25 sec)
    - Agent 4: Competitor Analyzer (20 sec)
    - Agent 5: Questionnaire Analyzer (25 sec)
  - Step 3: Agent 6 synthesis (15-20 sec)
  - Step 4: Agent 7 customer summary (≤15 sec)
  - Total: <4.5 minutes end-to-end
- **FR-019a**: System MUST handle agent failures gracefully (continue with partial results)
- **FR-019b**: System MUST log all agent execution metrics (time, tokens, cost)
- **FR-019c**: System MUST support configurable questionnaire templates (stored in Firestore `questionnaire_templates` collection)

#### Slack Integration & Interactivity
##### Upload Interface
- **FR-020**: System MUST provide an "Upload Audio" action, accessible as a persistent Shortcut in the designated private Slack channel (near the message composer). This shortcut will trigger the upload modal.
- **FR-020a**: The upload modal MUST include:
  - Customer ID field (Format: `XXXXXX-XXXXXX`, numbers only)
  - Store Name field (Text input)
  - File upload element (supports m4a, mp3, wav, flac)
  - A 'Submit' button
- **FR-020b**: System MUST immediately respond with case ID and processing confirmation

##### Real-time Progress Updates
- **FR-021**: System MUST send progress updates in Slack thread:
  - Upload confirmed with case ID
  - Transcription progress (with percentage if available)
  - Analysis in progress
  - Completion notification
- **FR-021a**: Updates MUST modify same message (not create new ones)

##### Interactive Analysis Delivery
- **FR-022**: System MUST send Slack Block Kit interactive message upon analysis completion
- **FR-022a**: Message MUST include:
  - Case header with metadata (customer, ID, sentiment indicator, participants count)
  - Collapsible sections for different analysis dimensions
  - Action buttons: [📄 完整逐字稿] [🎯 參與者詳情] [💬 追問 AI] [⭐ 給回饋]
  - Key insights prominently highlighted (decision maker, stage, risk, next action)
- **FR-022b**: System MUST look up Slack ID from User_Mapping (Firestore `users` collection)
- **FR-022c**: System MUST deliver notification within 1 minute of analysis completion
- **FR-022d**: System MUST store slack_message_ts for thread tracking

##### Conversational AI Follow-up
- **FR-023**: System MUST enable conversational AI in analysis threads
- **FR-023a**: System MUST detect when message is in case thread (by thread_ts)
- **FR-023b**: System MUST retrieve full case context from Firestore
- **FR-023c**: System MUST send question + full context to Gemini
- **FR-023d**: System MUST respond within 5 seconds
- **FR-023e**: System MUST store all Q&A in Firestore `conversations[]` array
- **FR-023f**: System MUST track token usage per conversation

##### Feedback Collection
- **FR-024**: System MUST provide in-Slack feedback via modal
- **FR-024a**: Modal MUST include:
  - AI accuracy rating (1-5 stars)
  - Deal status (won/lost/tracking radio buttons)
  - Optional comments field
- **FR-024b**: System MUST pre-fill case ID automatically
- **FR-024c**: System MUST store feedback in Firestore and sync to Sheets
- **FR-024d**: System MUST show confirmation message after submission

#### Data Management
##### Firestore as Primary Database
- **FR-025**: System MUST use Firestore as primary database for all operations
- **FR-025a**: System MUST store all case data in `cases/{caseId}` collection with complete structure:
  - Basic metadata (caseId, customerName, salesRepEmail, timestamps)
  - Audio metadata (fileName, duration, gcsPath, deleteAt)
  - Transcription (text, speakers[], qualityScore, language)
  - Multi-agent analysis results (participants[], sentiment, productNeeds, competitors, structured coaching)
  - Notification (slack_message_ts, sentAt, deliveryStatus)
  - Feedback (accuracyRating, dealStatus, comments)
  - Conversations (Q&A history array)
  - System metrics (processing times, costs, token usage)
- **FR-025b**: System MUST store user mappings in `users/{userId}` collection:
  - email (unique)
  - slackId
  - name
  - unit
  - activeStatus
- **FR-025c**: All real-time queries MUST use Firestore (not Sheets)

##### Google Sheets Sync for Reporting
- **FR-026**: System MUST sync summarized data to Google Sheets daily for reporting
- **FR-026a**: Sheets header structure (30 columns):
  ```
  A: Case_ID
  B: Submission_Timestamp
  C: Salesperson_Email
  D: Customer_Name
  E: Audio_Duration_Min
  F: Transcription_Status
  G: Transcription_Quality
  H: Participant_Count
  I: Key_Decision_Maker_Role
  J: Decision_Maker_Power
  K: Overall_Sentiment
  L: Trust_Level
  M: Buying_Signals_Count
  N: Primary_Need
  O: Recommended_Product
  P: Estimated_Budget_Min
  Q: Estimated_Budget_Max
  R: Decision_Timeline
  S: Competitor_Mentioned
  T: Competitive_Position
  U: Conversion_Probability
  V: Sales_Stage
  W: AI_Prompt_Version
  X: Notification_Sent_At
  Y: Feedback_Deal_Status
  Z: Feedback_Accuracy_Rating
  AA: Feedback_Submitted_At
  AB: Total_Processing_Time_Sec
  AC: Total_Cost_USD
  AD: Data_Status
  ```
- **FR-026b**: Sync timing:
  - New cases: Synced within 1 hour of creation
  - Updates: Synced daily at 1:00 AM
  - Backward compatibility: Google Form submissions scanned every 5 minutes
- **FR-026c**: Sheets used ONLY for:
  - Management reporting dashboards
  - Historical data export
  - Backward compatibility with old Google Form workflow

##### Audio File Lifecycle
- **FR-027**: System MUST auto-delete audio files 7 days after processing
- **FR-027a**: Cloud Storage lifecycle policy MUST be configured for automatic deletion
- **FR-027b**: Firestore MUST retain audio metadata (fileName, original URL) for reference
- **FR-027c**: Transcription text and analysis MUST be retained indefinitely

#### Quality & Reliability
- **FR-028**: System MUST automatically retry failed jobs up to 3 times with exponential backoff (60s, 120s, 240s)
- **FR-029**: System MUST distinguish between retryable errors (network timeout) and non-retryable errors (invalid file format)
- **FR-030**: System MUST log all errors with full context (case ID, stage, error message, stack trace) to Cloud Logging
- **FR-031**: System MUST emit metrics to Cloud Monitoring:
  - Processing success/failure counts
  - Average processing time
  - Quality score distribution
  - Queue depth
- **FR-032**: System MUST alert (email/Slack) when:
  - Success rate drops below 95% in past 24h
  - Queue depth exceeds 50 pending jobs
  - Monthly cost exceeds $40

#### Integration & Compatibility
- **FR-033**: System MUST accept webhook callbacks from existing Google Apps Script system
- **FR-034**: System MUST support gradual migration (old and new systems running in parallel)
- **FR-035**: System MUST maintain API compatibility with existing Google Sheets column structure [需要補充: 請提供 Google Sheets 的欄位名稱和結構]
- **FR-036**: System MUST support manual triggering via API (for reprocessing failed cases)

#### Security & Privacy
- **FR-037**: System MUST use Google Cloud service accounts for all GCP API access
- **FR-038**: System MUST use Secret Manager for all sensitive credentials (Slack token, Gemini API key)
- **FR-039**: System MUST enforce authentication on all HTTP endpoints (Cloud Run requires auth)
- **FR-040**: System MUST encrypt all data in transit (HTTPS) and at rest (default GCP encryption)
- **FR-041**: System MUST log all access to audio files for audit trail
- **FR-042**: System MUST NOT send audio files to any third-party services (process locally only)

### Key Entities

- **Case**: Represents a single sales call recording and its processing lifecycle
  - Attributes: caseId, sourceType (google_drive/gcs), salesRep, customer, audioFile, transcription, analysis, status, timestamps, quality metrics
  - Relationships: Belongs to one User (sales rep), may have multiple QualityChecks

- **User**: Represents a sales representative or team member
  - Attributes: email, slackId, name, unit, active status
  - Relationships: Has many Cases

- **TranscriptionJob**: Represents a queued transcription task
  - Attributes: caseId, audioSource, priority, attempts, status
  - Relationships: References one Case

- **AnalysisJob**: Represents a queued AI analysis task
  - Attributes: caseId, transcriptionId, prompt version, status
  - Relationships: References one Case, depends on TranscriptionJob completion

- **Feedback**: Represents sales rep's feedback on AI analysis
  - Attributes: caseId, conversionRate, accuracyRating, comments, submittedAt
  - Relationships: Belongs to one Case

- **QualityMetric**: Tracks transcription quality for monitoring
  - Attributes: caseId, qualityScore, confidence, language, duration, processingTime
  - Relationships: Belongs to one Case

## Success Criteria *(mandatory)*

### Measurable Outcomes

#### Performance & Scalability
- **SC-001**: System processes 200-250 audio files per month with <$45 total monthly cost including multi-agent analysis (validated by Cloud Billing reports)

- **SC-002**: Average end-to-end processing time (upload → Slack notification with full analysis) is <4 minutes for 90% of cases (validated by timestamp analysis in Firestore metrics)

- **SC-003**: System successfully processes 10+ concurrent audio files without degradation (validated by load testing)

- **SC-004**: System uptime is >99.5% (measured as percentage of time all services are healthy)

#### Quality Metrics
- **SC-005**: Transcription quality score is >85 for 90% of cases (validated by quality metrics in Firestore)

- **SC-006**: Speaker diarization accuracy >80% for files with 2-3 speakers (validated by manual sampling)

- **SC-007**: Multi-agent analysis success rate >95% (all agents complete without errors)

- **SC-008**: Participant role identification accuracy >75% (validated by sales rep feedback)

- **SC-009**: Product recommendation relevance score >80% based on sales rep feedback

#### User Experience
- **SC-010**: 90% of sales reps receive interactive Slack notifications within 4 minutes of upload (validated by notification logs)

- **SC-011**: Conversational AI response time <5 seconds for 95% of follow-up questions (validated by response time logs)

- **SC-012**: Sales rep engagement rate >70% (click on at least one button or ask one question per case)

- **SC-013**: Feedback submission rate >60% (sales reps provide feedback on analysis)

- **SC-014**: Average AI accuracy rating >4.0/5.0 based on sales rep feedback

#### Backward Compatibility & Reliability
- **SC-015**: System maintains backward compatibility - existing Google Form uploads are processed correctly (validated by integration tests)

- **SC-016**: Google Sheets sync lag <1 hour for new cases, daily sync completes successfully (validated by sync logs)

- **SC-017**: Success rate (completed without errors) is >95% (validated by daily metrics)

- **SC-018**: Zero data breaches or unauthorized access to audio files (validated by security audit logs)

#### Cost Efficiency
- **SC-019**: Cost per audio file is <$0.18 including all multi-agent processing (calculated as monthly cost / number of files processed)

- **SC-020**: Gemini API costs <$15/month for all agents (validated by API usage logs)

- **SC-021**: Cloud Run costs <$20/month for all services (validated by billing reports)

---

## ✅ **已確認項目**

所有關鍵決策已於 2025-01-29 確認完成：

### 1. iCHEF 產品目錄（用於產品推薦）✅
**決策**：使用 iCHEF 官方網站 (https://www.ichefpos.com/) 作為產品目錄參考

**核心產品**：
1. 餐飲 POS 系統（提升出餐速度、減少人力依賴）
2. 線上訂位系統（接單效率提升 2 倍）
3. 掃碼點餐（客單價 +$18）
4. 雲端餐廳（建立自有流量，24 小時營業）
5. 線上外帶/配送（不依賴外送平台）
6. 總部系統（多店管理、集中控管）

**升級路徑**：
- 新客入門：POS 系統 + 線上訂位
- 成長驅動：掃碼點餐 + 智慧推薦 → 客單價提升
- 擴張路徑：雲端餐廳 → 總部系統

---

### 2. Multi-Agent 架構確認 ✅

✅ **採用 Multi-Agent 架構（7 個 Agent）**
- Agent 1: 參與者分析（30s）
- Agent 2: 情緒分析（20s）
- Agent 3: 需求提取（25s）
- Agent 4: 競品分析（20s）
- Agent 5: 問卷自動填寫（25s）
- Agent 6: 銷售教練合成（20s）
- Agent 7: 客戶摘要產生器（15s）
- 平行執行 Agents 1-5（總時長 30-40s）

✅ **啟用 Speaker Diarization**
- 準確識別說話者
- 計算發言時長
- 支援角色分析

✅ **自動產品推薦**
- 使用 iCHEF 官網產品資訊

✅ **Discovery Questionnaire 自動化**
- Prompt-based 方式（不使用 Firestore 範本）
- 22 個具體功能，6 大類別

✅ **新 Sheets Header (30 欄)**
- 完整對應已在 FR-026a 定義

**使用者回饋**："可以，請使用多 Agent"

---

### 3. Discovery Questionnaire 功能清單 ✅

**決策**：選項 B - Prompt-based 方式（MVP 不使用 Firestore 可配置範本）

#### 完整功能清單（22 個功能，6 大類別）

**1️⃣ 點餐與訂單管理**
1. 掃碼點餐（QR Code 掃碼點餐）
2. 多人掃碼點餐
3. 套餐加價購
4. 智慧菜單推薦
5. POS 點餐系統
6. 線上點餐接單

**2️⃣ 線上整合服務**
7. 線上訂位管理
8. 線上外帶自取
9. 雲端餐廳（Online Store）
10. Google 整合
11. LINE 整合
12. 外送平台整合
13. 聯絡式外帶服務

**3️⃣ 成本與庫存管理**
14. 成本控管
15. 庫存管理
16. 帳款管理

**4️⃣ 業績與銷售分析**
17. 銷售分析
18. 報表生成功能

**5️⃣ 客戶關係管理**
19. 零秒集點（忠誠點數系統 2.0）
20. 會員管理

**6️⃣ 企業級功能**
21. 總部系統
22. 連鎖品牌管理

**實作方式**：Agent 5 的 system prompt 包含完整功能清單，可靈活偵測對話中提到的任何功能。

---

### 4. 其他技術決策 ✅

#### 4a. Gemini Prompt v7.0 使用
- ✅ 保留在 FR-018a（Sales Coach Agent 使用 v7.0 作為 baseline）
- ✅ 來源：`sales-ai-gas-automation/geminiService.gs`

#### 4b. 音檔保留期限
- ✅ 7 天自動刪除（FR-027）

#### 4c. Google Sheets 結構
- ✅ 30 欄新結構（FR-026a）
- ✅ 向後相容舊 Form 上傳

#### 4d. Disaster Recovery ✅
**決策**：選項 A - 等待恢復（簡單，成本低）
- 月處理量不高（200-250 檔案）
- $0 額外成本
- 可接受每年 1-2 小時停機風險

**使用者回饋**："A"

#### 4e. Storage Quota
- ✅ 7 天自動刪除音檔
- ✅ Firestore 在 1GB 免費額度內
- ✅ Cloud Storage 預估 <5GB/月

#### 4f. 問卷結構設計 ✅
**決策**：目前結構已核准，有問題再調整
- current_status（使用狀態）
- need_reasons（需求原因 + quotes + confidence）
- perceived_value（價值評估）
- barriers（阻礙因素）
- timeline（考慮時程）
- confidence scores（信心分數 0-100）

**使用者回饋**："沒問題，有問題再改"

---

### 5. 下一步 🚀

✅ 所有決策已確認完成

**建議執行順序**：
1. **Phase 0**: 執行 6 個 POC 驗證（輸出：`research.md`）
2. **Phase 1**: 詳細設計（輸出：`data-model.md`, `contracts/`, `quickstart.md`）
3. **Phase 2**: 建立實作任務（輸出：`tasks.md`）
4. **Phase 3+**: 開始 Sprint 1-7 實作

詳細技術實作計畫請參閱 `plan.md`
