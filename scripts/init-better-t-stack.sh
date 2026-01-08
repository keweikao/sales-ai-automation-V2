#!/bin/bash
# =============================================================================
# Better-T Stack 整合初始化腳本
# =============================================================================
# 用途：初始化 Better-T Stack 前端專案結構
# 執行：./scripts/init-better-t-stack.sh
# =============================================================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 專案根目錄
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Better-T Stack 整合初始化${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# =============================================================================
# Phase 1: API Gateway 初始化
# =============================================================================
echo -e "${YELLOW}Phase 1: 建立 API Gateway...${NC}"

mkdir -p "$PROJECT_ROOT/api-gateway"/{routers,schemas,middleware}

# 建立 FastAPI 主程式
cat > "$PROJECT_ROOT/api-gateway/main.py" << 'EOF'
"""
Sales AI Automation API Gateway
FastAPI 應用程式主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from .config import settings
from .routers import conversations, leads, analytics, health

app = FastAPI(
    title="Sales AI Automation API",
    description="銷售 AI 自動化系統 API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(conversations.router, prefix="/api/v1", tags=["Conversations"])
app.include_router(leads.router, prefix="/api/v1", tags=["Leads"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Sales AI Automation API",
        version="2.0.0",
        description="銷售 AI 自動化系統 API",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# 建立設定檔
cat > "$PROJECT_ROOT/api-gateway/config.py" << 'EOF'
"""API Gateway 設定"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """API Gateway 設定"""

    # 環境
    environment: str = "development"

    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # GCP
    gcp_project_id: str = "sales-ai-automation-v2"
    firestore_database: str = "(default)"

    class Config:
        env_file = ".env"


settings = Settings()
EOF

# 建立 __init__.py
touch "$PROJECT_ROOT/api-gateway/__init__.py"
touch "$PROJECT_ROOT/api-gateway/routers/__init__.py"
touch "$PROJECT_ROOT/api-gateway/schemas/__init__.py"
touch "$PROJECT_ROOT/api-gateway/middleware/__init__.py"

# 建立基礎路由
cat > "$PROJECT_ROOT/api-gateway/routers/health.py" << 'EOF'
"""健康檢查路由"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "service": "api-gateway"}
EOF

cat > "$PROJECT_ROOT/api-gateway/routers/conversations.py" << 'EOF'
"""對話相關 API 路由"""
from fastapi import APIRouter, Query
from typing import Optional, List
from ..schemas.conversation import Conversation, ConversationDetail

router = APIRouter()


@router.get("/conversations", response_model=List[Conversation])
async def list_conversations(
    status: Optional[str] = Query(None, description="篩選狀態"),
    limit: int = Query(50, ge=1, le=100, description="回傳數量限制"),
):
    """列出對話記錄"""
    # TODO: 實作 Firestore 查詢
    return []


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    """取得對話詳情"""
    # TODO: 實作 Firestore 查詢
    return {}
EOF

cat > "$PROJECT_ROOT/api-gateway/routers/leads.py" << 'EOF'
"""潛客相關 API 路由"""
from fastapi import APIRouter, Query
from typing import Optional, List
from ..schemas.lead import Lead

router = APIRouter()


@router.get("/leads", response_model=List[Lead])
async def list_leads(
    status: Optional[str] = Query(None, description="篩選狀態"),
    limit: int = Query(50, ge=1, le=100, description="回傳數量限制"),
):
    """列出潛客"""
    # TODO: 實作 Firestore 查詢
    return []


@router.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str):
    """取得潛客詳情"""
    # TODO: 實作 Firestore 查詢
    return {}
EOF

cat > "$PROJECT_ROOT/api-gateway/routers/analytics.py" << 'EOF'
"""分析相關 API 路由"""
from fastapi import APIRouter
from ..schemas.analytics import DashboardStats

router = APIRouter()


@router.get("/analytics/dashboard", response_model=DashboardStats)
async def get_dashboard_stats():
    """取得儀表板統計數據"""
    # TODO: 實作統計查詢
    return {
        "totalConversations": 0,
        "completedToday": 0,
        "avgMeddicScore": 0,
        "conversionRate": 0,
    }
EOF

# 建立 Schema
cat > "$PROJECT_ROOT/api-gateway/schemas/conversation.py" << 'EOF'
"""對話相關 Schema"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class Conversation(BaseModel):
    """對話基本資訊"""
    id: str
    leadId: Optional[str] = None
    salesRepName: Optional[str] = None
    status: str
    conversationType: Optional[str] = None
    createdAt: datetime
    completedAt: Optional[datetime] = None


class Transcript(BaseModel):
    """逐字稿"""
    segments: List[Dict[str, Any]]
    fullText: Optional[str] = None
    language: str = "zh-TW"
    durationSeconds: Optional[float] = None


class AnalysisResult(BaseModel):
    """分析結果"""
    contextData: Optional[Dict[str, Any]] = None
    buyerData: Optional[Dict[str, Any]] = None
    sellerCoaching: Optional[Dict[str, Any]] = None
    meddicScore: Optional[int] = None
    summary: Optional[str] = None


class ConversationDetail(Conversation):
    """對話詳情（包含逐字稿和分析）"""
    transcript: Optional[Transcript] = None
    analysis: Optional[AnalysisResult] = None
EOF

cat > "$PROJECT_ROOT/api-gateway/schemas/lead.py" << 'EOF'
"""潛客相關 Schema"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Lead(BaseModel):
    """潛客資訊"""
    id: str
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    status: str
    score: int = 0
    createdAt: datetime
    updatedAt: Optional[datetime] = None
EOF

cat > "$PROJECT_ROOT/api-gateway/schemas/analytics.py" << 'EOF'
"""分析相關 Schema"""
from pydantic import BaseModel
from typing import List, Optional


class PerformerStats(BaseModel):
    """業務表現統計"""
    name: str
    conversationCount: int
    avgMeddicScore: float


class DashboardStats(BaseModel):
    """儀表板統計數據"""
    totalConversations: int
    completedToday: int
    avgMeddicScore: float
    conversionRate: float
    topPerformers: Optional[List[PerformerStats]] = None
EOF

# 建立 requirements.txt
cat > "$PROJECT_ROOT/api-gateway/requirements.txt" << 'EOF'
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
google-cloud-firestore>=2.14.0
python-multipart>=0.0.6
EOF

echo -e "${GREEN}✓ API Gateway 結構已建立${NC}"

# =============================================================================
# Phase 2: Dashboard Monorepo 初始化
# =============================================================================
echo ""
echo -e "${YELLOW}Phase 2: 建立 Dashboard Monorepo 結構...${NC}"

mkdir -p "$PROJECT_ROOT/dashboard"/{apps/{web,admin},packages/{ui,api-client,types}}/src

# 建立根 package.json
cat > "$PROJECT_ROOT/dashboard/package.json" << 'EOF'
{
  "name": "sales-ai-dashboard",
  "private": true,
  "workspaces": [
    "apps/*",
    "packages/*"
  ],
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "typecheck": "turbo run typecheck",
    "lint": "turbo run lint",
    "generate:api-client": "turbo run generate --filter=@sales-ai/api-client"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "typescript": "^5.3.0"
  },
  "packageManager": "bun@1.0.0"
}
EOF

# 建立 turbo.json
cat > "$PROJECT_ROOT/dashboard/turbo.json" << 'EOF'
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "typecheck": {
      "dependsOn": ["^build"]
    },
    "lint": {},
    "generate": {
      "cache": false,
      "inputs": ["../../api-gateway/openapi.json"]
    }
  }
}
EOF

# 建立基礎 tsconfig
cat > "$PROJECT_ROOT/dashboard/tsconfig.base.json" << 'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "jsx": "react-jsx"
  }
}
EOF

# =============================================================================
# Phase 3: 建立 packages/ui
# =============================================================================
echo ""
echo -e "${YELLOW}Phase 3: 建立 @sales-ai/ui 套件...${NC}"

cat > "$PROJECT_ROOT/dashboard/packages/ui/package.json" << 'EOF'
{
  "name": "@sales-ai/ui",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "build": "tsc",
    "typecheck": "tsc --noEmit"
  },
  "peerDependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.3.0"
  }
}
EOF

cat > "$PROJECT_ROOT/dashboard/packages/ui/tsconfig.json" << 'EOF'
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist"
  },
  "include": ["src"]
}
EOF

cat > "$PROJECT_ROOT/dashboard/packages/ui/src/index.ts" << 'EOF'
// 基礎組件
export * from './components/button';
export * from './components/card';

// 工具
export * from './lib/utils';
EOF

mkdir -p "$PROJECT_ROOT/dashboard/packages/ui/src/"{components,lib}

cat > "$PROJECT_ROOT/dashboard/packages/ui/src/lib/utils.ts" << 'EOF'
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
EOF

cat > "$PROJECT_ROOT/dashboard/packages/ui/src/components/button.tsx" << 'EOF'
import * as React from 'react';
import { cn } from '../lib/utils';

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    return (
      <button
        className={cn(
          'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button };
EOF

cat > "$PROJECT_ROOT/dashboard/packages/ui/src/components/card.tsx" << 'EOF'
import * as React from 'react';
import { cn } from '../lib/utils';

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)}
    {...props}
  />
));
Card.displayName = 'Card';

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col space-y-1.5 p-6', className)}
    {...props}
  />
));
CardHeader.displayName = 'CardHeader';

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
));
CardContent.displayName = 'CardContent';

export { Card, CardHeader, CardContent };
EOF

echo -e "${GREEN}✓ @sales-ai/ui 套件已建立${NC}"

# =============================================================================
# Phase 4: 建立 packages/api-client
# =============================================================================
echo ""
echo -e "${YELLOW}Phase 4: 建立 @sales-ai/api-client 套件...${NC}"

cat > "$PROJECT_ROOT/dashboard/packages/api-client/package.json" << 'EOF'
{
  "name": "@sales-ai/api-client",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "build": "tsc",
    "typecheck": "tsc --noEmit",
    "generate": "bun run scripts/generate.ts"
  },
  "dependencies": {
    "openapi-fetch": "^0.9.0"
  },
  "devDependencies": {
    "openapi-typescript": "^6.7.0",
    "typescript": "^5.3.0"
  }
}
EOF

cat > "$PROJECT_ROOT/dashboard/packages/api-client/tsconfig.json" << 'EOF'
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist"
  },
  "include": ["src"]
}
EOF

mkdir -p "$PROJECT_ROOT/dashboard/packages/api-client/scripts"

cat > "$PROJECT_ROOT/dashboard/packages/api-client/scripts/generate.ts" << 'EOF'
/**
 * API Client 類型生成腳本
 * 從 OpenAPI Schema 生成 TypeScript 類型
 */
import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { resolve } from 'path';

const OPENAPI_PATH = resolve(__dirname, '../../../../api-gateway/openapi.json');
const OUTPUT_PATH = resolve(__dirname, '../src/schema.d.ts');

console.log('🔍 Checking OpenAPI schema...');

if (!existsSync(OPENAPI_PATH)) {
  console.log('⚠️  OpenAPI schema not found at:', OPENAPI_PATH);
  console.log('📝 Creating placeholder schema.d.ts...');

  // 建立佔位符
  const placeholder = `
// 此檔案由 openapi-typescript 自動生成
// 執行 'bun run generate' 來重新生成
// 需要先啟動 API Gateway 並產生 openapi.json

export interface paths {}
export interface components {}
export interface operations {}
`;

  require('fs').writeFileSync(OUTPUT_PATH, placeholder);
  console.log('✅ Placeholder created');
  process.exit(0);
}

console.log('📦 Generating API client types...');

try {
  execSync(`bunx openapi-typescript ${OPENAPI_PATH} -o ${OUTPUT_PATH}`, {
    stdio: 'inherit',
  });
  console.log('✅ API client types generated successfully!');
} catch (error) {
  console.error('❌ Failed to generate types:', error);
  process.exit(1);
}
EOF

cat > "$PROJECT_ROOT/dashboard/packages/api-client/src/index.ts" << 'EOF'
export { api, createAuthenticatedClient } from './client';
export type { paths, components, operations } from './schema';
EOF

cat > "$PROJECT_ROOT/dashboard/packages/api-client/src/client.ts" << 'EOF'
import createClient from 'openapi-fetch';
import type { paths } from './schema';

const getBaseUrl = () => {
  if (typeof window !== 'undefined') {
    return (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
  }
  return process.env.API_URL || 'http://localhost:8000';
};

export const api = createClient<paths>({
  baseUrl: getBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

export function createAuthenticatedClient(token: string) {
  return createClient<paths>({
    baseUrl: getBaseUrl(),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });
}
EOF

# 建立空的 schema.d.ts
cat > "$PROJECT_ROOT/dashboard/packages/api-client/src/schema.d.ts" << 'EOF'
// 此檔案由 openapi-typescript 自動生成
// 執行 'bun run generate' 來重新生成
// 需要先啟動 API Gateway 並產生 openapi.json

export interface paths {}
export interface components {}
export interface operations {}
EOF

echo -e "${GREEN}✓ @sales-ai/api-client 套件已建立${NC}"

# =============================================================================
# Phase 5: 建立 packages/types
# =============================================================================
echo ""
echo -e "${YELLOW}Phase 5: 建立 @sales-ai/types 套件...${NC}"

cat > "$PROJECT_ROOT/dashboard/packages/types/package.json" << 'EOF'
{
  "name": "@sales-ai/types",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "build": "tsc",
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "typescript": "^5.3.0"
  }
}
EOF

cat > "$PROJECT_ROOT/dashboard/packages/types/tsconfig.json" << 'EOF'
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist"
  },
  "include": ["src"]
}
EOF

cat > "$PROJECT_ROOT/dashboard/packages/types/src/index.ts" << 'EOF'
// 共用類型定義

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'manager' | 'sales';
}

export interface PaginationParams {
  page: number;
  limit: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}
EOF

echo -e "${GREEN}✓ @sales-ai/types 套件已建立${NC}"

# =============================================================================
# 完成
# =============================================================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  初始化完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "已建立以下結構："
echo ""
echo -e "  ${BLUE}api-gateway/${NC}"
echo -e "  ├── main.py           # FastAPI 主程式"
echo -e "  ├── config.py         # 設定"
echo -e "  ├── routers/          # API 路由"
echo -e "  └── schemas/          # Pydantic 模型"
echo ""
echo -e "  ${BLUE}dashboard/${NC}"
echo -e "  ├── apps/"
echo -e "  │   ├── web/          # Dashboard (Agent G)"
echo -e "  │   └── admin/        # Admin Panel (Agent H)"
echo -e "  └── packages/"
echo -e "      ├── ui/           # @sales-ai/ui"
echo -e "      ├── api-client/   # @sales-ai/api-client"
echo -e "      └── types/        # @sales-ai/types"
echo ""
echo -e "${YELLOW}下一步：${NC}"
echo ""
echo -e "1. ${BLUE}Agent A${NC}: 完善 API Gateway"
echo -e "   cd api-gateway"
echo -e "   pip install -r requirements.txt"
echo -e "   uvicorn main:app --reload"
echo ""
echo -e "2. ${BLUE}Agent I${NC}: 安裝依賴並生成 API Client"
echo -e "   cd dashboard"
echo -e "   bun install"
echo -e "   bun run generate:api-client"
echo ""
echo -e "3. ${BLUE}Agent G/H${NC}: 初始化前端應用"
echo -e "   需要使用 Better-T Stack CLI 或手動建立"
echo ""
echo -e "📖 詳細說明請參考: docs/BETTER-T-STACK-INTEGRATION-PLAN.md"
