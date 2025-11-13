# Hugging Face Token Verification Report for Pyannote Diarization

## 概述

本報告驗證 Hugging Face token 是否能正確訪問 Pyannote diarization 模型。

## 配置檢查結果

### 1. 當前配置的模型名稱

根據代碼分析，使用以下模型：

| 位置 | 模型名稱 | 默認值 |
|------|---------|--------|
| `src/transcription/diarization/pyannote_diarizer.py` L51 | `model_name` 參數 | `"pyannote/speaker-diarization"` |
| `src/transcription/diarization/__init__.py` L18 | `create_diarizer()` | `"pyannote/speaker-diarization"` |
| `src/transcription/main.py` L32 | `DIARIZATION_MODEL` | `"pyannote/speaker-diarization"` |

**支持的模型**：

- `pyannote/speaker-diarization` (默認)
- `pyannote/speaker-diarization-3.1` (可配置)

### 2. Token 配置方式

#### 環境變數

- **環境變數名稱**：`HUGGINGFACE_TOKEN`
- **位置**：`src/transcription/main.py` L36
- **代碼參考**：

  ```python
  HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")
  ```

#### Token 優先級（在 `PyannoteDiarizer` 中）

1. 構造函數參數 `use_auth_token`（優先）
2. 環境變數 `HUGGINGFACE_TOKEN`（備選）

代碼見：`src/transcription/diarization/pyannote_diarizer.py` L63

```python
token = use_auth_token or os.getenv("HUGGINGFACE_TOKEN")
```

#### Docker 配置

- **Dockerfile 路徑**：`src/transcription/Dockerfile`
- **當前狀態**：沒有設置 `HUGGINGFACE_TOKEN` 環境變數
- **建議**：需要在運行時傳入環境變數或透過 Cloud Run secrets 注入

#### 環境變數範本

- **文件**：`.env.example` L10
- **內容**：`HUGGINGFACE_TOKEN=` (空值，需要填入)

### 3. Token 使用流程

```
main.py (HUGGINGFACE_TOKEN 環境變數)
    ↓
OptimizedTranscriptionPipeline.__init__()
    ├─ diarization_auth_token 參數
    ├─ _diarization_config["auth_token"]
    └─ pipeline._get_diarizer()
        ↓
        create_diarizer(use_auth_token=auth_token)
            ↓
            PyannoteDiarizer(use_auth_token=token)
                ├─ token = use_auth_token or os.getenv("HUGGINGFACE_TOKEN")
                ├─ Pipeline.from_pretrained(model_name, use_auth_token=token)
                └─ 返回初始化的 pipeline 實例
```

### 4. 錯誤處理

#### 缺少 Token

- **位置**：`src/transcription/diarization/pyannote_diarizer.py` L63-69
- **錯誤訊息**：

  ```
  RuntimeError: Missing Hugging Face token for pyannote.audio diarization.
  Set the HUGGINGFACE_TOKEN environment variable or provide `use_auth_token` when constructing PyannoteDiarizer.
  ```

#### 無效的 Token

- **位置**：`src/transcription/diarization/pyannote_diarizer.py` L77-82
- **錯誤訊息**：

  ```
  RuntimeError: Failed to load pyannote.audio pipeline, it returned None.
  This may be due to an invalid Hugging Face token or network issues.
  ```

#### 備用方案

- **位置**：`src/transcription/diarization/__init__.py` L34-39
- **機制**：如果 Pyannote 加載失敗，會回退到 `EmbeddingClusterDiarizer`

## 驗證方案

### 測試腳本

已創建驗證腳本：`verify_huggingface_token.py`

#### 功能

1. **環境變數檢查**：確認 `HUGGINGFACE_TOKEN` 已設置
2. **API 驗證**：使用 `huggingface_hub` 庫驗證 token 有效性
3. **模型訪問檢查**：驗證 token 有權訪問指定的 Pyannote 模型
4. **模型加載測試**：實際加載模型驗證完整功能

#### 使用方式

```bash
# 設置 token
export HUGGINGFACE_TOKEN="hf_xxxxxxxxxxxxxxxxxxxx"

# 運行驗證
python verify_huggingface_token.py
```

#### 輸出示例

```
============================================================
Step 1: Checking HUGGINGFACE_TOKEN environment variable
============================================================
✓ HUGGINGFACE_TOKEN is set: hf_xxxxxxxxxxxxxxxxxx*****xxxxxxxx

============================================================
Step 2: Verifying token with Hugging Face API
============================================================
✓ Token is valid!
  Username: your-username
  Organization: your-org

============================================================
Step 3: Checking access to pyannote/speaker-diarization
============================================================
✓ Model found: pyannote/speaker-diarization
  Downloads (last month): 50000
  Task: automatic-speech-recognition

============================================================
Step 4: Testing model loading from pyannote/speaker-diarization
============================================================
Loading pipeline: pyannote/speaker-diarization
(This may take a few minutes on first run...)
✓ Model loaded successfully!
  Pipeline type: <class 'pyannote.audio.core.pipeline.Pipeline'>

============================================================
VERIFICATION SUMMARY
============================================================
✓ env_variable: PASS
✓ huggingface_api: PASS
✓ model_access_pyannote/speaker-diarization: PASS
✓ model_loading_pyannote/speaker-diarization: PASS
✓ model_access_pyannote/speaker-diarization-3.1: PASS
✓ model_loading_pyannote/speaker-diarization-3.1: PASS

============================================================
SUCCESS: All checks passed!
Your Hugging Face token is properly configured for Pyannote diarization.
============================================================
```

## 常見問題與解決方案

### 問題 1：Token 無效或過期

**症狀**：

```
RuntimeError: Failed to load pyannote.audio pipeline, it returned None.
```

**解決方案**：

1. 驗證 token 格式：應以 `hf_` 開頭
2. 檢查 token 是否過期（在 <https://huggingface.co/settings/tokens> 檢查）
3. 重新生成 token（如需要）

### 問題 2：需要接受模型使用條款

**症狀**：

```
gated model
```

**解決方案**：

1. 訪問 <https://huggingface.co/pyannote/speaker-diarization>
2. 閱讀並接受模型使用條款
3. 使用具有"讀取"權限的 token

### 問題 3：Token 權限不足

**症狀**：

```
401 Unauthorized
```

**解決方案**：

1. 檢查 token 是否有"讀取"權限
2. 在 <https://huggingface.co/settings/tokens> 檢查 token 範圍
3. 如需要，建立新的 token 並授予適當權限

### 問題 4：網絡連接問題

**症狀**：

```
Connection error to Hugging Face
```

**解決方案**：

1. 檢查網絡連接
2. 確認能訪問 <https://huggingface.co>
3. 如在公司網絡，檢查防火牆設置

## 配置更新建議

### 1. Docker 環境變數設置

**文件**：`src/transcription/Dockerfile`

建議在 Cloud Run 或容器編排系統中配置：

```dockerfile
# 注意：不要直接在 Dockerfile 中設置 token
# 而應通過環境變數或 secrets 注入
ENV HUGGINGFACE_TOKEN=""
```

### 2. Cloud Run 部署配置

```bash
# 使用 secrets
gcloud run deploy transcription-service \
  --set-secrets HUGGINGFACE_TOKEN=huggingface-token:latest \
  --image gcr.io/project/transcription-service
```

### 3. Kubernetes 部署配置

```yaml
env:
  - name: HUGGINGFACE_TOKEN
    valueFrom:
      secretKeyRef:
        name: huggingface-secrets
        key: token
```

### 4. 本地開發配置

```bash
# 在 .env 文件中設置（不要提交到版本控制）
echo "HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx" >> .env
source .env
```

## 相關文件清單

| 文件 | 用途 | 關鍵代碼行 |
|------|------|----------|
| `src/transcription/diarization/pyannote_diarizer.py` | 核心 Diarizer 實現 | L51, L63, L77 |
| `src/transcription/diarization/__init__.py` | Diarizer 工廠函數 | L18, L29 |
| `src/transcription/main.py` | Flask 應用主程序 | L32, L36, L54 |
| `src/transcription/pipeline.py` | 轉錄流程管理 | L38-40, L296-300 |
| `src/transcription/Dockerfile` | 容器配置 | (無 token 設置) |
| `.env.example` | 環境變數範本 | L10 |
| `requirements.txt` | Python 依賴 | L30-31 |

## 依賴版本

```
pyannote.audio==3.1.1
speechbrain==1.0.3
huggingface-hub (隱含依賴)
```

## 驗證步驟總結

### 快速驗證

```bash
# 1. 設置 token
export HUGGINGFACE_TOKEN="your-token-here"

# 2. 運行驗證腳本
python verify_huggingface_token.py

# 3. 檢查所有檢查項都通過
```

### 完整測試

```bash
# 1. 部署到測試環境
# 2. 上傳音檔到 GCS
# 3. 調用 /transcribe 端點啟用 diarization
# 4. 驗證 speaker_segments 在響應中正確返回
```

## 結論

當前配置已正確支持 Hugging Face token 認證，但需要：

1. **設置環境變數**：在運行時確保 `HUGGINGFACE_TOKEN` 被設置
2. **獲取有效 Token**：從 <https://huggingface.co/settings/tokens> 創建
3. **接受模型條款**：訪問 <https://huggingface.co/pyannote/speaker-diarization> 並接受條款
4. **驗證配置**：使用提供的 `verify_huggingface_token.py` 腳本進行驗證

一旦完成這些步驟，系統將能夠正確加載並使用 Pyannote diarization 模型進行說話者分離。
