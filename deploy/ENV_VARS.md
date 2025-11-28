# Service Environment Variables (Reference)

集中列出各服務部署時用到的主要環境變數名稱（僅列名稱/用途，不含值）。

## Slack App (`cloudbuild.slack.yaml`)

來自 Cloud Build 部署參數：

- `SLACK_AUDIO_BUCKET`
- `TRANSCRIPTION_TASK_QUEUE`
- `TRANSCRIPTION_TASK_HANDLER_URL`
- `TRANSCRIPTION_TASK_SERVICE_ACCOUNT`
- `GCP_PROJECT_ID`
- `SLACK_PROGRESS_TOKEN`
- `SUMMARY_BASE_URL`
- `SHORT_URL_BASE`
- `SUMMARY_DELIVERY_QUEUE`
- `SUMMARY_DELIVERY_LOCATION`
- `SUMMARY_DELIVERY_HANDLER_URL`

Secrets:

- `SLACK_BOT_TOKEN`
- `SLACK_SIGNING_SECRET`

## Transcription Service (`cloudbuild.transcription.yaml`)

來自 Cloud Build 部署參數：

- `TRANSCRIPTION_ENGINE`
- `GEMINI_MODEL`
- `SLACK_PROGRESS_ENDPOINT`
- `SLACK_PROGRESS_TOKEN`

Secrets:

- `GEMINI_API_KEY`
- `HUGGINGFACE_TOKEN`

## Analysis Service

目前部署腳本保留既有 Cloud Run 設定（未在 YAML 內覆寫）。如需調整，請先列出既有環境變數與 secrets，避免部署時覆蓋。
