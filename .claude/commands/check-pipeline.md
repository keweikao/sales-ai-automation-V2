# Check Pipeline Status

檢查轉錄和分析 pipeline 的目前狀態。

## Usage
```
/check-pipeline [service]
```

## Services
- `transcription` - 轉錄服務狀態
- `analysis` - 分析服務狀態
- `all` - 所有服務（預設）

## Steps
1. 檢查 Cloud Run 服務狀態
2. 檢視最近的處理紀錄
3. 回報任何錯誤或警告

請執行以下檢查：
- 檢視 Firestore 中最近 5 筆案件的狀態
- 確認服務是否正常運作
