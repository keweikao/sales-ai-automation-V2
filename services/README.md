# Services Map

統一整理各服務所在路徑，保持命名一致性並方便查找。

| Service | Location (symlink → source) | Notes |
| --- | --- | --- |
| Analysis / Orchestrator | `services/analysis` → `analysis-service/` | Orchestrator、Gemini 分析流程與測試；Cloud Run 部署定義於同目錄 `cloudbuild.yaml`、`Dockerfile` |
| Web UI / API | `services/web` → `web-service/` | Web 介面、模板與 API；含 `Dockerfile`、`requirements.txt`、`tests/` |
| Slack App | `services/slack` → `src/slack_app/` | Slack Bolt app、handlers/interactions/notifications、MCP adapter；部署檔在該目錄 |
| Transcription Pipeline | `services/transcription` → `src/transcription/` | Faster-Whisper、VAD/diarization、平行處理與品質檢查；附 `README.md`、`requirements.txt` |

> 已建立 `services/<name>` 符號連結供統一路徑使用（Windows/不支援 symlink 的環境請直接使用原路徑）。現有匯入與 CI 仍以原路徑運作，逐步切換時請同步更新腳本與文件。
