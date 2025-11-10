#!/bin/bash
# 清除 Firestore 測試資料

PROJECT_ID="sales-ai-automation-v2"

echo "🔍 正在查詢 Firestore 資料..."

# 使用 gcloud alpha firestore 命令（需要 alpha 組件）
# 注意：這需要手動操作，因為 gcloud 沒有直接的批量刪除命令

echo ""
echo "請前往 Firebase Console 手動刪除資料："
echo "https://console.firebase.google.com/project/${PROJECT_ID}/firestore"
echo ""
echo "需要刪除的集合："
echo "  1. cases - 刪除所有文檔"
echo "  2. processed_files - 刪除所有文檔"
echo ""
echo "或者，你可以使用 Firebase CLI："
echo "  firebase firestore:delete --all-collections -P ${PROJECT_ID}"
