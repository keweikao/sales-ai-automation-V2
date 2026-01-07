# Gemini Model Version Management

本文件說明如何管理和更新 Gemini 模型版本,避免因 Google 模型版本變更導致的服務中斷。

## 背景

2026-01-06 我們遇到了因模型版本錯誤導致的系統故障:
- 使用 `gemini-1.5-flash` 在 v1beta API 中返回 404 錯誤
- Circuit breaker 被觸發,導致所有後續請求被阻擋
- 最近 10 個 cases 全部失敗

**根本原因**: Google 持續更新和合併模型版本,舊版本可能被棄用或不支援特定 API 版本。

## 當前穩定版本 (2026-01)

### 推薦使用的模型

| 模型名稱 | 用途 | 支援功能 | 狀態 |
|---------|------|---------|------|
| `gemini-2.0-flash` | 轉錄、分析 | Audio, Text, Image | ✅ 穩定 |
| `gemini-2.5-flash` | 高效能分析 | Audio, Text, Image | ✅ 穩定 |
| `gemini-2.5-pro` | 複雜推理 | Audio, Text, Image, Video | ✅ 穩定 |

### 已棄用的模型

| 模型名稱 | 替代方案 | 原因 |
|---------|---------|------|
| `gemini-1.5-flash` | `gemini-2.0-flash` | 404 in v1beta API |
| `gemini-1.5-pro` | `gemini-2.5-pro` | 功能已被新版本取代 |
| `gemini-pro` | `gemini-2.0-flash` | 已棄用 |

## 模型管理工具

我們提供了 `tools/gemini_model_manager.py` 來自動化管理模型版本。

### 安裝

```bash
pip install google-generativeai
```

### 使用方式

#### 1. 驗證當前配置

檢查代碼庫中的所有 Gemini 模型使用:

```bash
python tools/gemini_model_manager.py validate
```

輸出範例:
```
🔍 Scanning codebase for Gemini model usages...

📊 Found 12 model usages:

✅ Stable models (10):
   src/transcription/gemini_pipeline.py:41 - gemini-2.0-flash
   analysis-service/src/agents/base.py:73 - gemini-2.0-flash
   ...

⚠️  Deprecated models (2):
   tools/verify_gemini_simple.py:42 - gemini-1.5-flash → gemini-2.0-flash
   ...

💡 Run 'python tools/gemini_model_manager.py update' to fix deprecated models
```

#### 2. 測試特定模型

測試模型是否可用:

```bash
export GEMINI_API_KEY="your-api-key"
python tools/gemini_model_manager.py test --model gemini-2.0-flash
```

#### 3. 列出可用模型

從 API 獲取最新可用模型列表:

```bash
python tools/gemini_model_manager.py list-available
```

#### 4. 自動更新

預覽更新 (dry-run):
```bash
python tools/gemini_model_manager.py update --dry-run
```

執行更新:
```bash
python tools/gemini_model_manager.py update
```

#### 5. 生成遷移計劃

```bash
python tools/gemini_model_manager.py migration-plan > migration.json
```

## CI/CD 自動化檢查

我們已設置 GitHub Actions 自動檢查:

### 觸發時機

1. **每週檢查**: 每週一 UTC 9:00 自動運行
2. **Pull Request**: 當修改 Python 或 YAML 檔案時
3. **手動觸發**: 在 GitHub Actions 頁面手動執行

### 當發現棄用模型時

系統會自動:
1. 驗證失敗,標記 PR 或建立 Issue
2. 生成遷移計劃並上傳為 artifact
3. 如果是定期檢查,自動建立 Issue 通知團隊

### 配置

在 GitHub repo 設定中添加 secret:
```
GEMINI_API_KEY=your-api-key
```

## 在代碼中使用模型

### 最佳實踐

#### 1. 使用環境變數

✅ **推薦**:
```python
model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
```

❌ **不推薦**:
```python
model_name = "gemini-1.5-flash"  # 硬編碼
```

#### 2. 添加註解

```python
# Using stable Gemini 2.0 Flash (2026-01)
# Avoid gemini-1.5-flash: caused 404 in v1beta API
model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
```

#### 3. 實作 Fallback 機制

```python
def get_model(preferred: str = "gemini-2.0-flash"):
    """Get Gemini model with fallback."""
    try:
        return genai.GenerativeModel(preferred)
    except Exception as e:
        logger.warning(f"Failed to load {preferred}: {e}")
        # Fallback to stable alternative
        return genai.GenerativeModel("gemini-2.5-flash")
```

## 環境變數配置

### 轉錄服務

在 `cloudbuild.transcription.yaml`:
```yaml
--set-env-vars=GEMINI_MODEL=gemini-2.0-flash
```

### 分析服務

在 `analysis-service/src/main.py`:
```python
GEMINI_MODEL_DEFAULT = os.environ.get("GEMINI_MODEL_DEFAULT", "gemini-2.0-flash")
```

## 處理模型版本變更

### 當 Google 更新模型時

1. **監控**: GitHub Actions 會自動檢測
2. **測試**: 在 staging 環境測試新模型
3. **更新**: 使用管理工具批量更新
4. **部署**: 逐步部署到 production

### 遷移檢查清單

- [ ] 運行 `gemini_model_manager.py validate`
- [ ] 檢查棄用模型清單
- [ ] 在 staging 測試新模型
- [ ] 運行 `gemini_model_manager.py update --dry-run`
- [ ] 審查更改
- [ ] 執行實際更新
- [ ] 提交 PR 並測試
- [ ] 部署到 production
- [ ] 監控錯誤和 circuit breaker 狀態

## 緊急應對

### 如果遇到 404 錯誤

1. **檢查模型名稱**:
```bash
python tools/gemini_model_manager.py validate
```

2. **測試替代模型**:
```bash
python tools/gemini_model_manager.py test --model gemini-2.0-flash
```

3. **快速修復** - 更新環境變數:
```bash
gcloud run services update transcription-service \
  --region=asia-east1 \
  --update-env-vars=GEMINI_MODEL=gemini-2.0-flash
```

### 如果 Circuit Breaker 開啟

Circuit breaker 會在 30 秒後自動嘗試恢復 (HALF_OPEN 狀態)。

手動重置 (需要部署代碼):
```python
from src.resilience import reset_circuit
reset_circuit("gemini_api")
```

## 參考資料

- [Gemini API Models Documentation](https://ai.google.dev/gemini-api/docs/models)
- [Model Versions and Lifecycle](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions)
- Circuit Breaker: [analysis-service/src/resilience.py](../analysis-service/src/resilience.py)

## 更新歷史

| 日期 | 變更 | 原因 |
|------|------|------|
| 2026-01-07 | `gemini-1.5-flash` → `gemini-2.0-flash` | 404 錯誤修復 |
| 2026-01-07 | 建立模型管理工具 | 自動化版本管理 |

---

**維護者**: DevOps Team
**最後更新**: 2026-01-07
**下次審查**: 2026-02-07
