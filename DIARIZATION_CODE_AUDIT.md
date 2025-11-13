# Pyannote Diarization 代碼審計

## 審計概述

本審計檢查了 Hugging Face token 在整個代碼庫中的配置、使用和錯誤處理。

## 核心代碼分析

### 1. Token 定義

**文件**: `/src/transcription/diarization/pyannote_diarizer.py`

```python
# L63: Token 獲取邏輯
token = use_auth_token or os.getenv("HUGGINGFACE_TOKEN")
if not token:
    raise RuntimeError(
        "Missing Hugging Face token for pyannote.audio diarization. "
        "Set the HUGGINGFACE_TOKEN environment variable or provide "
        "`use_auth_token` when constructing PyannoteDiarizer."
    )
```

**評估**:

- ✓ 清晰的優先級：構造函數參數 > 環境變數
- ✓ 明確的錯誤訊息指導用戶
- ✓ 支持兩種方式注入 token

### 2. Token 使用

**文件**: `/src/transcription/diarization/pyannote_diarizer.py`

```python
# L77: 在模型加載中使用 token
self.pipeline = Pipeline.from_pretrained(model_name, use_auth_token=token)
if self.pipeline is None:
    raise RuntimeError(
        "Failed to load pyannote.audio pipeline, it returned None. "
        "This may be due to an invalid Hugging Face token or network issues."
    )
```

**評估**:

- ✓ 正確傳遞 token 到 Pyannote Pipeline
- ✓ 驗證加載結果不為 None
- ✓ 提供有用的錯誤訊息

### 3. Pipeline 集成

**文件**: `/src/transcription/pipeline.py`

```python
# L296-300: Diarizer 初始化
self.diarizer = create_diarizer(
    model_name=self._diarization_config["model_name"],
    use_auth_token=self._diarization_config["auth_token"],
    allow_overlap=self._diarization_config["allow_overlap"],
)
```

**評估**:

- ✓ 正確傳遞認證 token
- ✓ 支持模型名稱配置
- ✓ 錯誤處理適當（try-except 捕獲）

### 4. Flask 應用配置

**文件**: `/src/transcription/main.py`

```python
# L32: 模型配置
DIARIZATION_MODEL = os.environ.get("DIARIZATION_MODEL", "pyannote/speaker-diarization")

# L36: Token 配置
HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")

# L54: 傳遞到 Pipeline
diarization_auth_token=HUGGINGFACE_TOKEN,
```

**評估**:

- ✓ 使用環境變數配置
- ✓ 提供合理的默認模型
- ✓ 正確傳遞 token 到 Pipeline

## 環境配置檢查

### 文件清單

| 文件 | 內容 | 狀態 |
|------|------|------|
| `.env.example` | 環境變數範本 | ✓ 包含 HUGGINGFACE_TOKEN |
| `src/transcription/Dockerfile` | 容器配置 | ✓ 暴露 PORT，無 hardcode token |
| `requirements.txt` | Python 依賴 | ✓ 包含 pyannote.audio 依賴 |

### .env.example 檢查

```env
# L10: Token 佔位符
HUGGINGFACE_TOKEN=
```

**評估**:

- ✓ 包含 token 環境變數
- ✓ 以空值作為佔位符（安全）

### Dockerfile 檢查

**文件**: `/src/transcription/Dockerfile`

```dockerfile
# 未包含硬編碼的 token
# 環境變數應在運行時注入
```

**評估**:

- ✓ 未在 Dockerfile 中硬編碼任何敏感信息
- ✓ 正確依靠運行時環境變數注入

## 錯誤處理分析

### 1. 缺少 Token 錯誤

**觸發條件**: `HUGGINGFACE_TOKEN` 未設置且未傳遞 `use_auth_token` 參數

**錯誤消息**:

```
RuntimeError: Missing Hugging Face token for pyannote.audio diarization.
Set the HUGGINGFACE_TOKEN environment variable or provide `use_auth_token`
when constructing PyannoteDiarizer.
```

**位置**: `src/transcription/diarization/pyannote_diarizer.py:L65-68`

**評估**: ✓ 清晰指導用戶解決問題

### 2. 無效 Token 錯誤

**觸發條件**: Token 無效、過期或無權訪問模型

**錯誤消息**:

```
RuntimeError: Failed to load pyannote.audio pipeline, it returned None.
This may be due to an invalid Hugging Face token or network issues.
```

**位置**: `src/transcription/diarization/pyannote_diarizer.py:L79-82`

**評估**: ✓ 提示可能的原因

### 3. 備用方案

**位置**: `src/transcription/diarization/__init__.py:L34-39`

```python
try:
    return PyannoteDiarizer(...)
except Exception as exc:
    # 回退到 SpeechBrain-based diarizer
    try:
        return EmbeddingClusterDiarizer()
    except Exception as fallback_exc:
        raise RuntimeError(f"{exc} | {fallback_exc}") from fallback_exc
```

**評估**:

- ✓ 實現了優雅降級
- ✓ 如果 Pyannote 失敗，自動嘗試備用方案
- ✓ 合併錯誤信息以便調試

## 數據流追蹤

### 完整的 Token 流程

```
環境或構造函數參數
        ↓
    main.py (L36)
    HUGGINGFACE_TOKEN = os.environ.get(...)
        ↓
OptimizedTranscriptionPipeline.__init__ (L54)
    diarization_auth_token=HUGGINGFACE_TOKEN
        ↓
    _diarization_config["auth_token"] (L65)
        ↓
    _get_diarizer() (L296-300)
    create_diarizer(use_auth_token=...)
        ↓
PyannoteDiarizer.__init__ (L49-83)
    token = use_auth_token or os.getenv("HUGGINGFACE_TOKEN")
        ↓
    Pipeline.from_pretrained(model_name, use_auth_token=token)
        ↓
    成功返回 Pipeline 實例或失敗
```

**評估**: ✓ Token 正確傳遞整個調用鏈

## 依賴分析

### Pyannote 依賴

**文件**: `requirements.txt`

```
pyannote.audio==3.1.1
speechbrain==1.0.3
```

**評估**:

- ✓ 指定了明確的版本
- ✓ 包含了必要的依賴
- ✓ 版本選擇合理（3.1.1 是相對較新的穩定版本）

### 潛在的相容性問題

**依賴鏈**:

- pyannote.audio 依賴 torch >= 2.0.0
- pyannote.audio 依賴 torchaudio >= 2.0.0
- torch 和 torchaudio 版本必須匹配

**建議**: ✓ 當前 requirements.txt 已正確指定 torch >= 2.0.0 和 torchaudio >= 2.0.0

## 安全性評估

### 1. Token 不會被洩露

**檢查項**:

- ✓ Token 未被記錄到日誌（except 掩蓋後的版本用於驗證腳本）
- ✓ Token 未被保存到臨時文件
- ✓ Token 未被硬編碼在代碼中
- ✓ Docker 鏡像中未包含 token

**結論**: ✓ Token 安全处理

### 2. 環境變數洩露風險

**潛在風險**:

- Docker 層中洩露（低風險 - 未檢測到）
- 日誌中洩露（低風險 - 應避免記錄敏感信息）
- 進程環境中洩露（中等風險 - 正常情況）

**建議**:

- ✓ 使用 Cloud Run Secrets 而不是明文環境變數
- ✓ 定期更換 token

### 3. 代碼審查結果

**發現的問題**: 無

**潛在改進**:

1. 可以在初始化時驗證 token 格式（檢查是否以 `hf_` 開頭）
2. 可以添加 token 過期警告

## 日誌分析

### 當前日誌級別

**文件**: `src/transcription/main.py:L17`

```python
logging.basicConfig(level=logging.INFO, format='...')
```

**評估**:

- ✓ INFO 級別適當
- ✓ 格式清晰包含時間戳和級別

### Diarization 日誌

**位置**: `src/transcription/diarization/pyannote_diarizer.py:L71-75`

```python
logger.info(
    "Initializing pyannote diarization pipeline (model=%s, overlap=%s)",
    model_name,
    enable_overlap,
)
```

**評估**: ✓ 適當的信息日誌記錄

## 性能考慮

### 模型加載時間

**位置**: `src/transcription/pipeline.py:L292-304`

```python
def _get_diarizer(self):
    """Lazily instantiate the diarizer to reduce peak memory usage."""
    if not self.enable_diarization:
        return None

    if self.diarizer is None:
        # 第一次加載時會下載/初始化模型
```

**評估**:

- ✓ 使用了 lazy loading（延遲加載）
- ✓ 減少了啟動時間
- ✓ 只在需要時加載模型

### 記憶體使用

**考慮**:

- Pyannote 模型大小: ~2-3GB
- Lazy loading 減少啟動時記憶體
- 長時間運行應監控記憶體泄漏

**當前實現**: ✓ 已進行記憶體使用日誌記錄 (L294, L304)

## 建議改進

### 優先級 1: 立即實施

1. **添加 Token 格式驗證**

   ```python
   if token and not token.startswith("hf_"):
       logger.warning("Token may be invalid: should start with 'hf_'")
   ```

2. **使用 Cloud Run Secrets**
   - 避免在環境變數中存儲敏感信息
   - 使用 `gcloud secrets` 管理 token

### 優先級 2: 短期計劃

1. **添加 Token 過期檢查**

   ```python
   # 驗證 token 過期時間（從 HF API）
   ```

2. **實現 Token 輪換機制**
   - 支持舊 token 和新 token 的過渡期

3. **添加監控告警**
   - 當 Token 認證失敗時告警
   - 追蹤 Diarization API 調用失敗率

### 優先級 3: 長期規劃

1. **使用專用服務帳戶 Token**
   - 而不是個人 token

2. **實現 Token 自動更新**
   - 使用 Hugging Face API 自動刷新 token

3. **增強錯誤報告**
   - 集成到錯誤追蹤系統（如 Sentry）

## 代碼審計檢查清單

| 項目 | 狀態 | 註釋 |
|------|------|------|
| Token 未硬編碼 | ✓ | 正確使用環境變數 |
| Token 正確傳遞 | ✓ | 通過整個調用鏈傳遞 |
| Token 驗證 | ✓ | 存在驗證邏輯 |
| 錯誤處理 | ✓ | 有適當的錯誤訊息 |
| 日誌記錄 | ✓ | 適當的信息日誌 |
| 備用方案 | ✓ | 實現了降級到備用 diarizer |
| Dockerfile 安全 | ✓ | 未包含敏感信息 |
| 依賴版本 | ✓ | 指定了明確版本 |
| Token 安全 | ✓ | 不洩露到日誌或文件 |
| Lazy loading | ✓ | 模型按需加載 |

## 總體評估

### 代碼質量: A

**優點**:

- 清晰的代碼結構
- 適當的錯誤處理
- 正確的 token 管理
- 實現了優雅降級
- 包含 lazy loading 優化

**需要改進**:

- Token 格式驗證可更強化
- Token 過期檢查
- 更詳細的錯誤訊息

### 配置質量: A

**優點**:

- 環境變數使用正確
- 支持多種配置方式
- .env.example 完整

**需要改進**:

- Docker 和 Kubernetes 部署文檔
- CI/CD 集成指南

### 安全性: A

**優點**:

- Token 未被洩露
- 未硬編碼敏感信息
- 正確的優先級處理

**需要改進**:

- 使用 Cloud Run Secrets
- Token 輪換機制

## 結論

當前代碼實現了 Hugging Face token 的正確、安全的配置和使用。系統已為生產部署做好準備，但建議實施上述改進以進一步增強安全性和可靠性。

所有驗證腳本都已創建，可用於開發和部署流程中的 token 驗證。
