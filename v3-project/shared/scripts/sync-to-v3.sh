#!/bin/bash
# V2 → V3 單向同步腳本
# 執行方式: ./shared/scripts/sync-to-v3.sh

set -e

V2_ROOT="/home/user/sales-ai-automation-V2"
V3_ROOT="/home/user/Sales_ai_automation_v3"

echo "🔄 Syncing shared resources from V2 to V3..."
echo ""

# 檢查 V3 專案是否存在
if [ ! -d "$V3_ROOT" ]; then
  echo "❌ V3 專案不存在: $V3_ROOT"
  echo "請先執行 Phase 0 建立 V3 專案"
  exit 1
fi

# 確保 V3 shared 目錄存在
mkdir -p "$V3_ROOT/shared"

# Sync prompts
echo "📝 Syncing prompts..."
rsync -av --delete \
  "$V2_ROOT/shared/prompts/" \
  "$V3_ROOT/shared/prompts/"

# Sync schemas
echo "📋 Syncing schemas..."
rsync -av --delete \
  "$V2_ROOT/shared/schemas/" \
  "$V3_ROOT/shared/schemas/"

# Sync docs
echo "📚 Syncing docs..."
rsync -av --delete \
  "$V2_ROOT/shared/docs/" \
  "$V3_ROOT/shared/docs/"

# Sync config (if exists)
if [ -d "$V2_ROOT/shared/config" ]; then
  echo "⚙️ Syncing config..."
  rsync -av --delete \
    "$V2_ROOT/shared/config/" \
    "$V3_ROOT/shared/config/"
fi

echo ""
echo "✅ Sync complete!"
echo ""
echo "📊 Summary:"
echo "  - Prompts: $(find $V3_ROOT/shared/prompts -name '*.md' | wc -l) files"
echo "  - Schemas: $(find $V3_ROOT/shared/schemas -name '*.yaml' | wc -l) files"
echo "  - Docs: $(find $V3_ROOT/shared/docs -name '*.md' | wc -l) files"
echo ""
echo "💡 Next steps:"
echo "  1. cd $V3_ROOT"
echo "  2. bun run generate:types  # 從 YAML 生成 TypeScript 類型"
