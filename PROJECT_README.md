# Sales AI Automation V2.0

## iCHEF 銷售 AI 自動化系統

使用 Gemini 3 Flash 進行銷售通話轉錄與多 Agent AI 分析，透過 Slack 提供互動式體驗。

---

## 📊 系統概覽

| 項目 | 說明 |
|------|------|
| **核心模型** | Gemini 3 Flash Preview |
| **轉錄引擎** | Gemini Audio API |
| **雲端平台** | Google Cloud Platform |
| **使用介面** | Slack |

---

## 🏗️ 系統架構

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Slack App  │───▶│  Transcription   │───▶│    Analysis     │
│ (Cloud Run) │    │    Service       │    │    Service      │
└─────────────┘    │  (Cloud Run)     │    │  (Cloud Run)    │
       │           └──────────────────┘    └─────────────────┘
       │                    │                       │
       ▼                    ▼                       ▼
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ SMS Service │    │   Cloud Storage  │    │    Firestore    │
│ (Cloud Run) │    │  (Audio Files)   │    │   (Cases DB)    │
└─────────────┘    └──────────────────┘    └─────────────────┘
       │
       ▼
┌─────────────┐
│ Web Service │
│ (Summary)   │
└─────────────┘
```

### 微服務列表

| 服務 | 路徑 | 說明 |
|------|------|------|
| **slack-app** | `src/slack_app/` | Slack 互動介面、檔案上傳 |
| **transcription-service** | `src/transcription/` | 音訊轉錄 (Gemini Audio) |
| **analysis-service** | `analysis-service/` | 多 Agent AI 分析 |
| **sms-service** | `sms-service/` | SMS/Email 發送 |
| **web-service** | `web-service/` | 摘要網頁展示 |

---

## 🤖 Multi-Agent AI 架構

| Agent | 名稱 | 功能 | 模型 |
|-------|------|------|------|
| **Agent 1** | Context Analyzer | 會議脈絡、參與者分析 | gemini-2.5-flash |
| **Agent 2** | Buyer Analyzer | 買家心理、MEDDIC 分析 | gemini-2.5-pro |
| **Agent 3** | Seller Coach | 銷售技巧建議 | gemini-2.5-pro |
| **Agent 4** | Summary Generator | 客戶摘要、SMS 文案 | gemini-2.5-flash |

---

## 🔧 技術棧

### 核心依賴

| 類別 | 技術 | 版本 |
|------|------|------|
| **AI** | Google Gemini | 3 Flash Preview |
| **Web** | Flask | 2.2.5 |
| **Slack** | slack-bolt | 1.18.1 |
| **Database** | Firestore | 2.13.1 |
| **轉錄** | Gemini Audio API | - |

### 雲端服務

- **Cloud Run**: 所有微服務 (asia-east1)
- **Cloud Storage**: 音訊檔案儲存
- **Cloud Tasks**: 非同步任務處理
- **Secret Manager**: API Keys 管理

---

## 💰 成本估算 (100 案件/月)

| 項目 | 成本 |
|------|------|
| Gemini 3 Flash API | ~$12/月 |
| Cloud Run | ~$15/月 |
| Firestore | ~$2/月 |
| Cloud Storage | ~$1/月 |
| **總計** | **~$30/月** |

---

## 📁 專案結構

```
sales-ai-automation-V2/
├── analysis-service/          # 分析服務
│   ├── src/
│   │   ├── agents/            # AI Agents
│   │   ├── prompts/           # Prompt 模板
│   │   └── main.py
│   └── requirements.txt
├── src/
│   ├── slack_app/             # Slack 應用
│   └── transcription/         # 轉錄服務
├── sms-service/               # SMS/Email 服務
├── web-service/               # 摘要網頁服務
├── deploy/                    # 部署配置
├── specs/                     # 規格文件
├── docs/                      # 文檔
└── tests/                     # 測試
```

---

## 🚀 部署

### CloudBuild 配置

| 服務 | 配置檔 |
|------|--------|
| Analysis | `cloudbuild.analysis.deploy.yaml` |
| Transcription | `cloudbuild.transcription.yaml` |
| Slack | `cloudbuild.slack.yaml` |
| SMS | `cloudbuild.sms-service.yaml` |
| Web | `cloudbuild.summary-web-service.yaml` |

### 快速部署

```bash
# 部署 Analysis Service
gcloud builds submit --config=cloudbuild.analysis.deploy.yaml

# 部署 Transcription Service  
gcloud builds submit --config=cloudbuild.transcription.yaml
```

---

## 📚 文檔索引

| 文檔 | 說明 |
|------|------|
| [`QUICK_START_FOR_AI.md`](./QUICK_START_FOR_AI.md) | AI 助理快速入門 |
| [`DEVELOPMENT_LOG.md`](./DEVELOPMENT_LOG.md) | 開發日誌 |
| [`specs/`](./specs/) | 功能規格書 |
| [`docs/`](./docs/) | 技術文檔 |

---

## 📈 效能指標

- **轉錄時間**: ~1 分鐘 / 10 分鐘音訊
- **分析時間**: ~30 秒 (4 Agents 並行)
- **端到端**: < 2 分鐘

---

*最後更新: 2025-12-18*
