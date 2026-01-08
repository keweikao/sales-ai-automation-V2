# Analyze Sales Case

分析指定的銷售案件，執行 MEDDIC 評估並提供建議。

## Usage
```
/analyze-case <case_id>
```

## Steps
1. 從 Firestore 取得案件資料
2. 檢視轉錄內容
3. 執行 MEDDIC 分析
4. 提供銷售建議

## Example
```
/analyze-case CASE-2024-001
```

請提供案件 ID：$ARGUMENTS
