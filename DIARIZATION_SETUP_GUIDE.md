# Pyannote Diarization 設置指南

## 快速開始

### 1. 獲取 Hugging Face Token

#### 步驟

1. 訪問 <https://huggingface.co/login（如未登錄）>
2. 進入 <https://huggingface.co/settings/tokens>
3. 點擊 "New token"
4. 配置：
   - **Name**: `sales-ai-diarization` (或你喜歡的名字)
   - **Role**: 選擇 `read`
   - **Expiration**: 按需選擇（建議生產環境設置較長期限）

#### Token 格式

- Token 應以 `hf_` 開頭
- 示例: `hf_abcdefghijklmnopqrstuvwxyz1234567890`

### 2. 接受模型條款

訪問 <https://huggingface.co/pyannote/speaker-diarization> 並接受模型使用條款。

這是必要的，否則會遇到錯誤：

```
gated model
Repository Not Found
```

### 3. 配置環境變數

#### 本地開發環境

**方案 A: 使用 .env 文件（推薦開發環境）**

```bash
# 1. 編輯 .env 文件
echo "HUGGINGFACE_TOKEN=hf_your_token_here" >> .env

# 2. 確保 .env 在 .gitignore 中
echo ".env" >> .gitignore

# 3. 在運行代碼前加載
source .env
python your_script.py
```

**方案 B: 直接導出環境變數**

```bash
export HUGGINGFACE_TOKEN="hf_your_token_here"
python your_script.py
```

**方案 C: 使用 python-dotenv（應用代碼層級）**

```python
from dotenv import load_dotenv
import os

# 加載 .env 文件
load_dotenv()

# 使用環境變數
token = os.getenv("HUGGINGFACE_TOKEN")
```

#### Docker 環境

**方案 A: 使用 Cloud Run Secrets（推薦生產環境）**

```bash
# 1. 建立 secret
gcloud secrets create huggingface-token \
  --replication-policy="automatic" \
  --data-file=- <<< "hf_your_token_here"

# 2. 部署時綁定 secret
gcloud run deploy transcription-service \
  --image gcr.io/your-project/transcription:latest \
  --set-secrets HUGGINGFACE_TOKEN=huggingface-token:latest \
  --region asia-east1

# 3. 驗證
gcloud secrets versions access latest --secret="huggingface-token"
```

**方案 B: 使用環境變數（開發環境）**

```bash
docker run \
  -e HUGGINGFACE_TOKEN="hf_your_token_here" \
  -p 8080:8080 \
  gcr.io/your-project/transcription:latest
```

**方案 C: 使用 docker-compose**

```yaml
version: '3'
services:
  transcription:
    image: gcr.io/your-project/transcription:latest
    ports:
      - "8080:8080"
    environment:
      HUGGINGFACE_TOKEN: ${HUGGINGFACE_TOKEN}
    volumes:
      - ./data:/app/data
```

運行：

```bash
export HUGGINGFACE_TOKEN="hf_your_token_here"
docker-compose up
```

#### Kubernetes 環境

**方案 A: 使用 Secrets（推薦）**

```bash
# 1. 建立 secret
kubectl create secret generic huggingface-secrets \
  --from-literal=token=hf_your_token_here

# 2. 修改 Deployment 配置
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: transcription-service
spec:
  template:
    spec:
      containers:
      - name: transcription
        image: gcr.io/your-project/transcription:latest
        env:
        - name: HUGGINGFACE_TOKEN
          valueFrom:
            secretKeyRef:
              name: huggingface-secrets
              key: token
EOF
```

**方案 B: 使用 ConfigMap（不推薦用於敏感信息）**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: transcription-config
data:
  HUGGINGFACE_TOKEN: hf_your_token_here
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: transcription-service
spec:
  template:
    spec:
      containers:
      - name: transcription
        image: gcr.io/your-project/transcription:latest
        envFrom:
        - configMapRef:
            name: transcription-config
```

## 驗證配置

### 方案 1: 使用驗證腳本（推薦）

```bash
# 完整驗證
export HUGGINGFACE_TOKEN="hf_your_token_here"
python verify_huggingface_token.py

# 快速檢查
python quick_hf_check.py

# 集成測試
python test_diarization_integration.py
```

### 方案 2: 手動驗證

```python
import os
from huggingface_hub import HfApi

# 檢查 token
token = os.getenv("HUGGINGFACE_TOKEN")
assert token, "HUGGINGFACE_TOKEN not set"

# 驗證 token 有效性
api = HfApi()
user_info = api.whoami(token=token)
print(f"✓ Token valid for: {user_info['name']}")

# 驗證模型訪問
model_info = api.model_info("pyannote/speaker-diarization", token=token)
print(f"✓ Can access: {model_info.id}")

# 驗證模型加載
from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization",
    use_auth_token=token
)
print(f"✓ Model loaded: {type(pipeline)}")
```

## 代碼集成

### 基本使用

```python
from src.transcription.diarization import PyannoteDiarizer
import os

# 從環境變數獲取 token
token = os.getenv("HUGGINGFACE_TOKEN")

# 創建 diarizer
diarizer = PyannoteDiarizer(
    model_name="pyannote/speaker-diarization",
    use_auth_token=token,
    enable_overlap=False,
)

# 執行說話者分離
segments = diarizer.diarize("audio_file.wav")

# 輸出結果
for seg in segments:
    print(f"Speaker {seg.speaker}: {seg.start:.2f}s - {seg.end:.2f}s")
```

### Pipeline 集成

```python
from src.transcription.pipeline import OptimizedTranscriptionPipeline
import os

pipeline = OptimizedTranscriptionPipeline(
    model_size="medium",
    device="cuda",
    enable_diarization=True,
    diarization_model="pyannote/speaker-diarization",
    diarization_auth_token=os.getenv("HUGGINGFACE_TOKEN"),
)

result = pipeline.process_audio("audio_file.wav")

# 結果包含 speaker_segments
if result["success"]:
    for seg in result.get("speaker_segments", []):
        print(f"Speaker {seg['speaker']}: {seg['start']:.2f}s - {seg['end']:.2f}s")
```

## 故障排除

### 問題 1: Token 未設置

**錯誤訊息**：

```
RuntimeError: Missing Hugging Face token for pyannote.audio diarization.
Set the HUGGINGFACE_TOKEN environment variable or provide `use_auth_token` when constructing PyannoteDiarizer.
```

**解決方案**：

```bash
# 檢查 token 是否設置
echo $HUGGINGFACE_TOKEN

# 如果為空，設置它
export HUGGINGFACE_TOKEN="hf_your_token_here"
```

### 問題 2: Token 無效或過期

**錯誤訊息**：

```
RuntimeError: Failed to load pyannote.audio pipeline, it returned None.
This may be due to an invalid Hugging Face token or network issues.
```

**解決方案**：

1. 檢查 token 格式（應以 `hf_` 開頭）
2. 驗證 token 是否過期
3. 在 <https://huggingface.co/settings/tokens> 重新生成 token
4. 使用驗證腳本檢查：`python quick_hf_check.py`

### 問題 3: 模型條款未接受

**錯誤訊息**：

```
gated model
Repository Not Found
```

**解決方案**：

1. 訪問 <https://huggingface.co/pyannote/speaker-diarization>
2. 點擊 "Access repository" 按鈕
3. 閱讀並接受模型條款
4. 重試

### 問題 4: 網絡連接問題

**錯誤訊息**：

```
Connection refused
Remote end closed connection without response
```

**解決方案**：

1. 檢查網絡連接：`ping huggingface.co`
2. 檢查防火牆設置
3. 嘗試使用代理（如果在公司網絡）：

   ```python
   import os
   os.environ["http_proxy"] = "http://proxy.example.com:8080"
   os.environ["https_proxy"] = "https://proxy.example.com:8080"
   ```

### 問題 5: 記憶體不足

**錯誤訊息**：

```
RuntimeError: CUDA out of memory
```

**解決方案**：

```python
# 使用 CPU 而不是 GPU
pipeline = OptimizedTranscriptionPipeline(
    device="cpu",  # 改為 CPU
    ...
)

# 或使用較小的模型
pipeline = OptimizedTranscriptionPipeline(
    model_size="small",  # 使用 small 而不是 medium
    ...
)
```

## 監控和日誌

### 啟用詳細日誌

```python
import logging

# 設置 DEBUG 級別
logging.basicConfig(level=logging.DEBUG)

# 或針對特定模塊
logging.getLogger("pyannote").setLevel(logging.DEBUG)
logging.getLogger("src.transcription").setLevel(logging.DEBUG)
```

### 常用日誌位置

- **Flask 應用日誌**: 由 gunicorn 輸出到 stdout
- **Cloud Run 日誌**: <https://console.cloud.google.com/logs>
- **本地日誌**: 控制台輸出（如使用 logging 配置）

### 日誌示例

```
2024-01-15 10:30:45 - INFO - Initializing pyannote diarization pipeline (model=pyannote/speaker-diarization, overlap=False)
2024-01-15 10:30:46 - INFO - Loading diarization model...
2024-01-15 10:31:20 - INFO - Diarization model loaded successfully
2024-01-15 10:31:21 - INFO - Running speaker diarization on /tmp/audio.wav
2024-01-15 10:31:45 - INFO - Diarization produced 5 segments
```

## 性能考慮

### 記憶體使用

- **Pyannote 模型加載**: ~2-3 GB
- **同時多個請求**: 需要更多記憶體
- **推薦配置**:
  - CPU 模式: 至少 4GB RAM
  - GPU 模式: 至少 8GB VRAM

### 處理時間

- **100 秒音檔**: ~30-60 秒處理時間（取決於硬件）
- **優化建議**:
  - 使用 GPU 加速
  - 啟用批處理
  - 使用 lazy loading（已在代碼中實現）

### 成本優化

1. **本地 Token 驗證**: 減少 API 調用
2. **模型緩存**: Hugging Face 自動緩存下載的模型
3. **按需加載**: Pipeline 只在需要時加載模型

## 相關資源

- **Hugging Face 文檔**: <https://huggingface.co/docs>
- **Pyannote 文檔**: <https://github.com/pyannote/pyannote-audio>
- **Pyannote 模型卡**: <https://huggingface.co/pyannote/speaker-diarization>
- **GCP Cloud Run**: <https://cloud.google.com/run/docs>
- **Kubernetes Secrets**: <https://kubernetes.io/docs/concepts/configuration/secret/>

## 常見命令

```bash
# 設置 token
export HUGGINGFACE_TOKEN="hf_xxxxxxxxxxxxxxxxxxxx"

# 驗證
python quick_hf_check.py

# 完整檢查
python verify_huggingface_token.py

# 運行集成測試
python test_diarization_integration.py

# 在 Docker 中運行
docker run \
  -e HUGGINGFACE_TOKEN="$HUGGINGFACE_TOKEN" \
  -p 8080:8080 \
  gcr.io/your-project/transcription:latest

# 部署到 Cloud Run
gcloud run deploy transcription \
  --set-secrets HUGGINGFACE_TOKEN=huggingface-token:latest \
  --image gcr.io/your-project/transcription:latest
```

## 下一步

1. 獲取 Hugging Face Token
2. 接受模型條款
3. 運行驗證腳本確認配置
4. 在應用中啟用 diarization：

   ```python
   enable_diarization=True,
   diarization_auth_token=os.getenv("HUGGINGFACE_TOKEN"),
   ```

5. 測試端到端流程

## 支持

如遇到問題，請：

1. 檢查日誌輸出
2. 運行驗證腳本
3. 查看故障排除部分
4. 聯繫技術支持
