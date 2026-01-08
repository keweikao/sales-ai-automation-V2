# Development Environment Setup

設定本地開發環境。

## Usage
```
/dev-setup
```

## Steps

1. 檢查 Python 版本（需要 3.11+）
2. 建立虛擬環境
3. 安裝依賴套件
4. 設定環境變數
5. 驗證 GCP 認證

請執行以下步驟來設定開發環境：

```bash
# 建立虛擬環境
python3.11 -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
pip install -r analysis-service/requirements.txt
pip install -r src/slack_app/requirements.txt

# 複製環境變數範本
cp .env.example .env
```

請編輯 `.env` 檔案，填入必要的 API keys。
