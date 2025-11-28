# Deploy Artifacts Map

集中列出現有部署檔與對應服務，避免遺漏或名稱混淆。

## Cloud Build

| File | Target |
| --- | --- |
| `cloudbuild.yaml` | 預設管線入口（請檢視內含步驟確認用途） |
| `cloudbuild.analysis.deploy.yaml` (`deploy/analysis/`) | Analysis/Orchestrator 部署 |
| `cloudbuild.summary-web-service.yaml` (`deploy/web/`) | Web Service 部署 |
| `cloudbuild.transcription.yaml` (`deploy/transcription/`) | Transcription 服務部署 |
| `cloudbuild.slack.yaml` (`deploy/slack/`) | Slack App 部署（唯一版本；原 `cloudbuild-slack.yaml` 已移除） |

## Dockerfile

| File | Target |
| --- | --- |
| `Dockerfile` | 通用/根目錄建置（確認服務用途後使用） |
| `Dockerfile.slack` | Slack App |
| `src/slack_app/Dockerfile` | Slack App（同目標，請對齊使用） |
| `src/transcription/Dockerfile` | Transcription 服務 |
| `analysis-service/Dockerfile` | Analysis/Orchestrator |
| `web-service/Dockerfile` | Web Service |

> 建議：未來統一命名並放入對應服務資料夾，例如 `services/<name>/deploy/`，並更新 CI/CD 腳本。此表為過渡期間的權威清單。舊文件若提到 `cloudbuild-slack.yaml`，請一律改用 `cloudbuild.slack.yaml`。環境變數對照見 `deploy/ENV_VARS.md`。

### Deploy 指令建議

- Slack: `gcloud builds submit --config deploy/slack/cloudbuild.slack.yaml .`
- Transcription: `gcloud builds submit --config deploy/transcription/cloudbuild.transcription.yaml .`
- Analysis: `gcloud builds submit --config deploy/analysis/cloudbuild.analysis.deploy.yaml .`
- Web: `gcloud builds submit --config deploy/web/cloudbuild.summary-web-service.yaml .`
