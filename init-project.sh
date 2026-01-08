#!/bin/bash

# Sales AI Automation V2.0 - 專案初始化腳本
# 使用方式: chmod +x init-project.sh && ./init-project.sh

set -e

echo "🚀 Sales AI Automation V2.0 - 專案初始化"
echo "=========================================="

# 設定專案根目錄
PROJECT_ROOT="${1:-.}"
cd "$PROJECT_ROOT"

echo "📁 建立目錄結構..."

# ==========================================
# Claude Code Skills
# ==========================================
mkdir -p .claude/skills/{00-core-skill,01-lead-source-skill,02-mql-skill,03-sales-analysis-skill,04-deal-onboarding-skill,05-customer-success-skill,06-analytics-skill}

# ==========================================
# Core 層
# ==========================================
mkdir -p core/config/environments
mkdir -p core/database/{models,repositories,migrations}
mkdir -p core/llm/prompts
mkdir -p core/interfaces
mkdir -p core/utils

# ==========================================
# Modules
# ==========================================

# 01 - Lead Source
mkdir -p modules/01-lead-source/{google_ads,facebook_ads,squarespace,utm_tracking,handlers,tests}

# 02 - MQL Qualification
mkdir -p modules/02-mql-qualification/{transcription,first_contact_analyzer/prompts,lead_scoring,assignment,handlers,tests}

# 03 - Sales Conversation
mkdir -p modules/03-sales-conversation/{transcript_analyzer/prompts,meddic/prompts,coaching/templates,handlers,tests}

# 04 - Deal Onboarding
mkdir -p modules/04-deal-onboarding/{deal_capture,decision_logger/prompts,profile_builder/prompts,handoff/templates,handlers,tests}

# 05 - Customer Success
mkdir -p modules/05-customer-success/{journey_analyzer/prompts,timing_recommender,angle_suggester/prompts,health_monitor,handlers,tests}

# 06 - Analytics
mkdir -p modules/06-analytics/{funnel_analysis,rep_performance,customer_insights,cs_effectiveness,dashboard_api,handlers,tests}

# ==========================================
# Integrations
# ==========================================
mkdir -p integrations/slack/{bots,templates}
mkdir -p integrations/google_workspace
mkdir -p integrations/notifications/channels

# ==========================================
# Infrastructure
# ==========================================
mkdir -p infrastructure/{docker,gcp/terraform,scripts}

# ==========================================
# Tests & Docs
# ==========================================
mkdir -p tests/{integration,e2e}
mkdir -p docs/{modules,guides}

echo "📄 建立基礎檔案..."

# ==========================================
# 建立 __init__.py 檔案
# ==========================================
find . -type d -name "__pycache__" -prune -o -type d -print | while read dir; do
    if [[ "$dir" == *"core"* ]] || [[ "$dir" == *"modules"* ]] || [[ "$dir" == *"integrations"* ]] || [[ "$dir" == *"tests"* ]]; then
        if [[ ! "$dir" == *"prompts"* ]] && [[ ! "$dir" == *"templates"* ]] && [[ ! "$dir" == *".claude"* ]] && [[ ! "$dir" == *"docs"* ]] && [[ ! "$dir" == *"infrastructure"* ]]; then
            touch "$dir/__init__.py" 2>/dev/null || true
        fi
    fi
done

# ==========================================
# Core 基礎檔案
# ==========================================

# core/config/settings.py
cat > core/config/settings.py << 'EOF'
"""
全域設定載入
"""
import os
from pathlib import Path
from typing import Optional
import yaml

class Settings:
    """應用程式設定"""
    
    def __init__(self):
        self.env = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Database
        self.database_url = os.getenv("DATABASE_URL", "")
        
        # LLM
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.default_llm_model = os.getenv("DEFAULT_LLM_MODEL", "claude-sonnet-4-20250514")
        
        # Slack
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        self.slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")
        
        # Google
        self.google_credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
        
    @classmethod
    def load(cls) -> "Settings":
        return cls()

settings = Settings.load()
EOF

# core/config/constants.py
cat > core/config/constants.py << 'EOF'
"""
全域常數定義
"""

# 模組名稱
MODULE_LEAD_SOURCE = "01-lead-source"
MODULE_MQL = "02-mql-qualification"
MODULE_SALES = "03-sales-conversation"
MODULE_DEAL = "04-deal-onboarding"
MODULE_CS = "05-customer-success"
MODULE_ANALYTICS = "06-analytics"

# 階段定義
STAGE_LEAD_SOURCE = "lead_source"
STAGE_MQL = "mql"
STAGE_SALES = "sales"
STAGE_DEAL = "deal"
STAGE_CS = "cs"

# 預設值
DEFAULT_PAGE_SIZE = 50
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
EOF

# core/database/models/base.py
cat > core/database/models/base.py << 'EOF'
"""
基礎資料模型
"""
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field
import uuid

def generate_id() -> str:
    return str(uuid.uuid4())

@dataclass
class BaseModel:
    """所有模型的基礎類別"""
    id: str = field(default_factory=generate_id)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
EOF

# core/database/models/journey_event.py
cat > core/database/models/journey_event.py << 'EOF'
"""
客戶歷程事件模型 - 核心資料結構
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from .base import BaseModel, generate_id

@dataclass
class JourneyEvent(BaseModel):
    """單一歷程事件"""
    lead_id: str = ""
    
    # 事件來源
    stage: str = ""                          # lead_source / mql / sales / deal / cs
    module: str = ""                         # 哪個模組產生
    event_type: str = ""                     # 事件類型
    
    # 事件內容
    summary: str = ""                        # 事件摘要（給人看）
    ai_insights: Dict = field(default_factory=dict)  # AI 產生的洞察
    decision_factors: List[str] = field(default_factory=list)  # 關鍵決策因素
    
    # 後續參考
    recommended_actions: List[str] = field(default_factory=list)  # 建議動作
    tags: List[str] = field(default_factory=list)  # 標籤
    sentiment_score: Optional[float] = None  # 情緒分數 (-1 到 1)
    
    # 原始資料參考
    source_data_ref: Optional[str] = None    # 原始資料位置
    metadata: Dict = field(default_factory=dict)  # 其他元資料
EOF

# core/database/models/customer_profile.py
cat > core/database/models/customer_profile.py << 'EOF'
"""
客戶畫像模型 - 彙整所有歷程的洞察
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from .base import BaseModel

@dataclass
class Stakeholder:
    """利害關係人"""
    name: str = ""
    role: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    influence_level: str = ""  # high / medium / low
    notes: str = ""

@dataclass
class CustomerProfile(BaseModel):
    """客戶畫像"""
    lead_id: str = ""
    
    # 基本資訊
    company_name: str = ""
    industry: str = ""
    company_size: str = ""  # small / medium / large
    location: str = ""
    
    # 從歷程彙整的洞察
    pain_points: List[str] = field(default_factory=list)
    buying_motivations: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    decision_criteria: List[str] = field(default_factory=list)
    
    # 關鍵人物
    stakeholders: List[Stakeholder] = field(default_factory=list)
    decision_maker: Optional[str] = None
    champion: Optional[str] = None
    
    # 成交資訊
    deal_date: Optional[datetime] = None
    deal_value: Optional[float] = None
    products: List[str] = field(default_factory=list)
    contract_length_months: Optional[int] = None
    
    # CS 專用
    cs_owner: Optional[str] = None
    onboarding_status: str = "pending"  # pending / in_progress / completed
    health_score: Optional[float] = None  # 0-100
    next_touch_date: Optional[datetime] = None
    recommended_angle: Optional[str] = None
    recommended_timing: Optional[str] = None
EOF

# core/interfaces/events.py
cat > core/interfaces/events.py << 'EOF'
"""
事件類型定義
"""
from enum import Enum

class Stage(str, Enum):
    LEAD_SOURCE = "lead_source"
    MQL = "mql"
    SALES = "sales"
    DEAL = "deal"
    CS = "cs"

class EventType(str, Enum):
    # Lead Source 事件
    LEAD_CREATED = "lead_created"
    UTM_CAPTURED = "utm_captured"
    AD_SOURCE_IDENTIFIED = "ad_source_identified"
    
    # MQL 事件
    FIRST_CONTACT_ANALYZED = "first_contact_analyzed"
    MQL_SCORED = "mql_scored"
    LEAD_ASSIGNED = "lead_assigned"
    MQL_QUALIFIED = "mql_qualified"
    MQL_DISQUALIFIED = "mql_disqualified"
    
    # Sales 事件
    CONVERSATION_ANALYZED = "conversation_analyzed"
    MEDDIC_EVALUATED = "meddic_evaluated"
    COACHING_GENERATED = "coaching_generated"
    OBJECTION_HANDLED = "objection_handled"
    
    # Deal 事件
    DEAL_CLOSED = "deal_closed"
    DECISION_CAPTURED = "decision_captured"
    PROFILE_BUILT = "profile_built"
    HANDOFF_GENERATED = "handoff_generated"
    
    # CS 事件
    TIMING_RECOMMENDED = "timing_recommended"
    ANGLE_SUGGESTED = "angle_suggested"
    HEALTH_UPDATED = "health_updated"
    RISK_DETECTED = "risk_detected"
    CS_TOUCHPOINT = "cs_touchpoint"
EOF

# core/interfaces/journey_logger.py
cat > core/interfaces/journey_logger.py << 'EOF'
"""
客戶歷程記錄介面 - 所有模組必須透過此介面記錄事件
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime

class JourneyLoggerInterface(ABC):
    """
    客戶歷程記錄介面
    
    所有模組必須透過此介面記錄重要事件，
    這是模組間解耦和後續 CS 分析的關鍵。
    """
    
    @abstractmethod
    async def log_event(
        self,
        lead_id: str,
        stage: str,
        event_type: str,
        summary: str,
        ai_insights: Dict = None,
        decision_factors: List[str] = None,
        recommended_actions: List[str] = None,
        tags: List[str] = None,
        sentiment_score: float = None,
        source_data_ref: str = None,
        metadata: Dict = None
    ) -> str:
        """
        記錄一筆歷程事件
        
        Args:
            lead_id: 客戶 ID
            stage: 階段 (lead_source/mql/sales/deal/cs)
            event_type: 事件類型
            summary: 事件摘要（給人看的描述）
            ai_insights: AI 產生的結構化洞察
            decision_factors: 關鍵決策因素
            recommended_actions: 建議的後續動作
            tags: 標籤（用於後續檢索）
            sentiment_score: 情緒分數 (-1 到 1)
            source_data_ref: 原始資料參考位置
            metadata: 其他元資料
            
        Returns:
            event_id: 事件 ID
        """
        pass
    
    @abstractmethod
    async def get_journey(
        self,
        lead_id: str,
        stages: List[str] = None,
        event_types: List[str] = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        取得客戶的歷程事件
        
        Args:
            lead_id: 客戶 ID
            stages: 篩選特定階段
            event_types: 篩選特定事件類型
            start_date: 開始日期
            end_date: 結束日期
            limit: 最大回傳數量
            
        Returns:
            事件列表
        """
        pass
    
    @abstractmethod
    async def get_insights_summary(
        self,
        lead_id: str
    ) -> Dict:
        """
        彙整客戶的所有洞察（主要給 CS Agent 使用）
        
        Args:
            lead_id: 客戶 ID
            
        Returns:
            彙整後的洞察，包含：
            - pain_points: 痛點清單
            - buying_motivations: 購買動機
            - concerns: 顧慮/反對意見
            - decision_factors: 決策因素
            - key_events: 關鍵事件摘要
            - recommended_angle: 建議切角
        """
        pass
    
    @abstractmethod
    async def get_tags_for_lead(
        self,
        lead_id: str
    ) -> List[str]:
        """取得客戶的所有標籤"""
        pass
EOF

# core/llm/client.py
cat > core/llm/client.py << 'EOF'
"""
LLM 客戶端封裝
"""
import os
from typing import Optional, List, Dict
from anthropic import Anthropic

class LLMClient:
    """統一的 LLM 呼叫介面"""
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.default_model = os.getenv("DEFAULT_LLM_MODEL", "claude-sonnet-4-20250514")
    
    async def complete(
        self,
        prompt: str,
        system: str = None,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        執行 LLM 補全
        
        Args:
            prompt: 使用者提示
            system: 系統提示
            model: 模型名稱（預設使用 DEFAULT_LLM_MODEL）
            max_tokens: 最大 token 數
            temperature: 溫度參數
            
        Returns:
            LLM 回應文字
        """
        messages = [{"role": "user", "content": prompt}]
        
        response = self.client.messages.create(
            model=model or self.default_model,
            max_tokens=max_tokens,
            system=system or "",
            messages=messages,
            temperature=temperature
        )
        
        return response.content[0].text
    
    async def complete_with_history(
        self,
        messages: List[Dict],
        system: str = None,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """執行帶有對話歷史的 LLM 補全"""
        response = self.client.messages.create(
            model=model or self.default_model,
            max_tokens=max_tokens,
            system=system or "",
            messages=messages,
            temperature=temperature
        )
        
        return response.content[0].text

# 全域實例
llm_client = LLMClient()
EOF

echo "📝 建立 Skills SKILL.md 檔案..."

# ==========================================
# Skills SKILL.md 檔案
# ==========================================

# 00 - Core Skill
cat > .claude/skills/00-core-skill/SKILL.md << 'EOF'
# Core Development Skill

## 你的身份

你是 **Agent A**，負責 Sales AI Automation V2 的核心層開發。

## 你的職責

1. **資料模型設計** (`core/database/models/`)
   - 定義所有共用的資料結構
   - 確保模型向下相容

2. **資料存取介面** (`core/database/repositories/`)
   - 提供統一的 CRUD 操作
   - 實作 JourneyLogger

3. **LLM 呼叫封裝** (`core/llm/`)
   - 統一的 API 呼叫介面
   - Token 使用追蹤

4. **模組間介面** (`core/interfaces/`)
   - 定義事件類型
   - 維護介面穩定性

5. **基礎建設** (`infrastructure/`)
   - Docker 設定
   - GCP 部署配置
   - CI/CD 流程

## 可修改範圍

```
✅ core/**/*
✅ infrastructure/**/*
✅ tests/integration/**/*
✅ tests/e2e/**/*
✅ pyproject.toml
✅ requirements.txt
✅ requirements-dev.txt
✅ .env.example
✅ README.md
✅ AGENTS.md
```

## 禁止修改

```
❌ modules/**/*
❌ integrations/**/*
❌ .claude/skills/01-* 到 06-*
```

## 關鍵設計原則

1. **介面穩定性**：`core/interfaces/` 的介面一旦發布不得破壞相容性
2. **向下相容**：修改資料模型必須提供遷移腳本
3. **文件優先**：任何介面變更必須更新文件

## 常用指令

```bash
# 資料庫遷移
python -m alembic upgrade head

# 執行整合測試
pytest tests/integration/ -v

# 部署
./infrastructure/scripts/deploy.sh staging
```
EOF

# 01 - Lead Source Skill
cat > .claude/skills/01-lead-source-skill/SKILL.md << 'EOF'
# Lead Source Skill

## 你的身份

你是 **Agent B**，負責廣告來源追蹤模組開發。

## 你的職責

1. **Google Ads 整合** - 廣告活動資料和轉換追蹤
2. **Facebook Ads 整合** - 名單表單和 Pixel 事件
3. **Squarespace 整合** - Webhook 接收和表單解析
4. **UTM 追蹤** - UTM 參數解析和歸因

## 可修改範圍

```
✅ modules/01-lead-source/**/*
✅ integrations/google_workspace/**/*
```

## 禁止修改

```
❌ core/**/*
❌ modules/02-* 到 06-*
❌ infrastructure/**/*
```

## 如何記錄歷程事件

```python
from core.interfaces.journey_logger import JourneyLogger
from core.interfaces.events import Stage, EventType

logger = JourneyLogger()

await logger.log_event(
    lead_id=lead.id,
    stage=Stage.LEAD_SOURCE,
    event_type=EventType.LEAD_CREATED,
    summary=f"新名單從 {source} 進入，廣告活動: {campaign}",
    ai_insights={
        "source": "google_ads",
        "campaign": campaign_name,
        "ad_group": ad_group,
        "keyword": keyword
    },
    tags=["google_ads", campaign_type],
    metadata={"utm": utm_params}
)
```

## 輸出規範

每個新名單必須產出：
- `lead_id`: 唯一識別碼
- `source`: 來源平台
- `campaign_info`: 廣告活動資訊
- `utm_params`: UTM 參數
- `raw_data_ref`: 原始資料參考
EOF

# 02 - MQL Skill
cat > .claude/skills/02-mql-skill/SKILL.md << 'EOF'
# MQL Qualification Skill

## 你的身份

你是 **Agent C**，負責 MQL 開發分析模組。

## 你的職責

1. **音檔轉錄** - 首次聯繫通話轉文字
2. **首次聯繫分析** - 品質評估和關鍵資訊提取
3. **MQL 評分** - 根據標準評分
4. **自動指派** - 根據規則指派給業務

## 可修改範圍

```
✅ modules/02-mql-qualification/**/*
```

## 禁止修改

```
❌ core/**/*
❌ modules/01-*, 03-* 到 06-*
❌ integrations/**/*
❌ infrastructure/**/*
```

## 如何記錄歷程事件

```python
from core.interfaces.journey_logger import JourneyLogger
from core.interfaces.events import Stage, EventType

logger = JourneyLogger()

# 首次聯繫分析完成
await logger.log_event(
    lead_id=lead_id,
    stage=Stage.MQL,
    event_type=EventType.FIRST_CONTACT_ANALYZED,
    summary=f"首次聯繫分析完成，品質評分: {quality_score}",
    ai_insights={
        "quality_score": quality_score,
        "customer_needs": extracted_needs,
        "budget_mentioned": budget_info,
        "timeline": timeline_info,
        "objections": initial_objections
    },
    decision_factors=decision_factors,
    recommended_actions=["確認預算範圍", "了解決策流程"],
    tags=tags,
    source_data_ref=f"gs://bucket/recordings/{recording_id}"
)

# MQL 評分完成
await logger.log_event(
    lead_id=lead_id,
    stage=Stage.MQL,
    event_type=EventType.MQL_SCORED,
    summary=f"MQL 評分: {mql_score}，{status}",
    ai_insights={
        "mql_score": mql_score,
        "score_breakdown": breakdown,
        "qualification_status": status
    },
    tags=[f"mql_score_{score_tier}"]
)
```

## 評分標準

MQL 評分維度（0-100）：
- 需求明確度 (25%)
- 預算符合度 (25%)
- 時程急迫性 (20%)
- 決策權力 (20%)
- 溝通品質 (10%)
EOF

# 03 - Sales Analysis Skill
cat > .claude/skills/03-sales-analysis-skill/SKILL.md << 'EOF'
# Sales Analysis Skill

## 你的身份

你是 **Agent D**，負責銷售對話分析模組。

## 你的職責

1. **對話分析** - 逐字稿內容分析
2. **MEDDIC 評分** - 銷售方法論評估
3. **教練回饋** - 給業務的改善建議
4. **Slack Bot** - 結果推送和互動

## 可修改範圍

```
✅ modules/03-sales-conversation/**/*
✅ integrations/slack/**/*
```

## 禁止修改

```
❌ core/**/*
❌ modules/01-*, 02-*, 04-* 到 06-*
❌ infrastructure/**/*
```

## 如何記錄歷程事件

```python
from core.interfaces.journey_logger import JourneyLogger
from core.interfaces.events import Stage, EventType

logger = JourneyLogger()

# 對話分析完成
await logger.log_event(
    lead_id=lead_id,
    stage=Stage.SALES,
    event_type=EventType.CONVERSATION_ANALYZED,
    summary=f"銷售對話分析完成，整體評分: {overall_score}",
    ai_insights={
        "overall_score": overall_score,
        "buyer_signals": buyer_signals,
        "objections_raised": objections,
        "objections_handled": handled,
        "next_steps_agreed": next_steps,
        "competitive_mentions": competitors
    },
    decision_factors=key_decision_factors,
    recommended_actions=coaching_actions,
    tags=conversation_tags,
    sentiment_score=sentiment,
    source_data_ref=transcript_url
)

# MEDDIC 評估
await logger.log_event(
    lead_id=lead_id,
    stage=Stage.SALES,
    event_type=EventType.MEDDIC_EVALUATED,
    summary=f"MEDDIC 評分: {total_score}/100",
    ai_insights={
        "total_score": total_score,
        "metrics": metrics_score,
        "economic_buyer": eb_score,
        "decision_criteria": dc_score,
        "decision_process": dp_score,
        "identify_pain": ip_score,
        "champion": ch_score,
        "gaps": identified_gaps
    },
    recommended_actions=gap_closing_actions,
    tags=[f"meddic_{score_tier}"]
)
```

## MEDDIC 評分維度

- **M**etrics - 量化指標 (0-20)
- **E**conomic Buyer - 經濟買家 (0-20)
- **D**ecision Criteria - 決策標準 (0-15)
- **D**ecision Process - 決策流程 (0-15)
- **I**dentify Pain - 痛點識別 (0-15)
- **C**hampion - 內部支持者 (0-15)
EOF

# 04 - Deal Onboarding Skill
cat > .claude/skills/04-deal-onboarding-skill/SKILL.md << 'EOF'
# Deal Onboarding Skill

## 你的身份

你是 **Agent E**，負責成交導入和客戶成功模組。

## 你的職責（Deal Onboarding）

1. **成交資訊捕捉** - 記錄成交詳情
2. **決策記錄** - 提取關鍵決策點
3. **客戶畫像建立** - 彙整歷程洞察
4. **交接文件產生** - 給 CS 的交接摘要

## 可修改範圍

```
✅ modules/04-deal-onboarding/**/*
✅ modules/05-customer-success/**/*
```

## 禁止修改

```
❌ core/**/*
❌ modules/01-* 到 03-*, 06-*
❌ integrations/**/*
❌ infrastructure/**/*
```

## 如何記錄歷程事件

```python
from core.interfaces.journey_logger import JourneyLogger
from core.interfaces.events import Stage, EventType

logger = JourneyLogger()

# 成交記錄
await logger.log_event(
    lead_id=lead_id,
    stage=Stage.DEAL,
    event_type=EventType.DEAL_CLOSED,
    summary=f"成交！金額: {deal_value}，產品: {products}",
    ai_insights={
        "deal_value": deal_value,
        "products": products,
        "contract_length": contract_months,
        "payment_terms": payment_terms,
        "special_conditions": conditions
    },
    decision_factors=closing_factors,
    tags=["deal_closed", deal_size_tier]
)

# 決策點捕捉
await logger.log_event(
    lead_id=lead_id,
    stage=Stage.DEAL,
    event_type=EventType.DECISION_CAPTURED,
    summary="關鍵決策因素記錄完成",
    ai_insights={
        "primary_motivation": primary_motivation,
        "key_concerns_resolved": resolved_concerns,
        "unresolved_concerns": remaining_concerns,
        "promises_made": sales_promises,
        "customer_expectations": expectations
    },
    recommended_actions=cs_action_items,
    tags=motivation_tags
)

# 客戶畫像建立
await logger.log_event(
    lead_id=lead_id,
    stage=Stage.DEAL,
    event_type=EventType.PROFILE_BUILT,
    summary="客戶畫像建立完成",
    ai_insights={
        "pain_points": aggregated_pain_points,
        "buying_motivations": motivations,
        "concerns": all_concerns,
        "decision_criteria": criteria,
        "stakeholders": stakeholder_map
    }
)
```

## 客戶畫像必須包含

1. **痛點清單** - 從所有歷程提取
2. **購買動機** - 為什麼選擇我們
3. **顧慮清單** - 包含已解決和未解決
4. **業務承諾** - 銷售過程中的承諾
5. **客戶期望** - 對產品/服務的期望
6. **利害關係人** - 關鍵聯絡人資訊
EOF

# 05 - Customer Success Skill
cat > .claude/skills/05-customer-success-skill/SKILL.md << 'EOF'
# Customer Success Skill

## 你的身份

你是 **Agent E**，同時負責客戶成功模組。

## 你的職責（Customer Success）

1. **歷程分析** - 分析客戶完整旅程
2. **時機建議** - 最佳接觸時機推薦
3. **切角建議** - 根據歷程給出切入話術
4. **健康度監控** - 客戶健康度評估

## 核心邏輯：切角建議

```python
async def suggest_angle(lead_id: str) -> Dict:
    """
    根據客戶歷程，產生 CS 切入建議
    """
    # 1. 取得歷程摘要
    journey_summary = await journey_logger.get_insights_summary(lead_id)
    
    # 2. 分析關鍵因素
    prompt = f"""
    根據以下客戶歷程，建議 CS 的切入時機和話術：
    
    【客戶痛點】
    {journey_summary['pain_points']}
    
    【購買動機】
    {journey_summary['buying_motivations']}
    
    【業務承諾】
    {journey_summary['promises_made']}
    
    【未解決顧慮】
    {journey_summary['unresolved_concerns']}
    
    【成交產品】
    {journey_summary['products']}
    
    請提供：
    1. 建議的首次接觸時機（導入後第幾天）
    2. 建議的切入角度（基於哪個痛點或承諾）
    3. 開場白範例
    4. 需要注意的事項
    """
    
    return await llm_client.complete(prompt)
```

## 如何記錄歷程事件

```python
# 時機建議
await logger.log_event(
    lead_id=lead_id,
    stage=Stage.CS,
    event_type=EventType.TIMING_RECOMMENDED,
    summary=f"建議接觸時機: 導入後第 {days} 天",
    ai_insights={
        "recommended_day": days,
        "reason": reason,
        "lifecycle_stage": stage,
        "trigger_event": trigger
    }
)

# 切角建議
await logger.log_event(
    lead_id=lead_id,
    stage=Stage.CS,
    event_type=EventType.ANGLE_SUGGESTED,
    summary=f"建議切角: {angle_summary}",
    ai_insights={
        "angle": angle,
        "based_on": based_on_factors,
        "opening_script": script,
        "cautions": cautions,
        "follow_up_topics": topics
    },
    recommended_actions=action_items
)
```

## 輸出範例

```json
{
  "timing": {
    "recommended_day": 7,
    "reason": "客戶在銷售階段特別關注報表功能，建議導入初期即安排教學"
  },
  "angle": {
    "primary": "報表功能進階教學",
    "based_on": ["銷售承諾專人教學", "客戶關注營收掌控"],
    "opening_script": "王老闆您好，我是 iCHEF 客戶成功團隊的 OOO，想跟您約個時間，教您怎麼用報表功能來掌握每日營收...",
    "cautions": [
      "客戶曾擔心員工學不會，主動提供教育訓練資源",
      "避免一次介紹太多功能"
    ]
  }
}
```
EOF

# 06 - Analytics Skill
cat > .claude/skills/06-analytics-skill/SKILL.md << 'EOF'
# Analytics Skill

## 你的身份

你是 **Agent F**，負責分析報表模組。

## 你的職責

1. **漏斗分析** - 各階段轉換率
2. **業務表現** - 個人和團隊績效
3. **客戶洞察** - 客群行為分析
4. **CS 成效** - 客戶成功指標

## 可修改範圍

```
✅ modules/06-analytics/**/*
```

## 禁止修改

```
❌ core/**/*
❌ modules/01-* 到 05-*
❌ integrations/**/*
❌ infrastructure/**/*
```

## 關鍵指標

### 漏斗指標
- Lead → MQL 轉換率
- MQL → SQL 轉換率
- SQL → Deal 轉換率
- 平均銷售週期
- 各階段停留時間

### 業務指標
- 成交率
- 平均客單價
- MEDDIC 平均分數
- 教練建議採納率

### CS 指標
- 客戶健康度分布
- 首次接觸及時率
- 續約率
- NPS 分數

## Dashboard API 規範

```python
# GET /api/analytics/funnel
{
    "period": "2024-Q4",
    "stages": [
        {"name": "Lead", "count": 1000, "conversion_rate": null},
        {"name": "MQL", "count": 300, "conversion_rate": 0.30},
        {"name": "SQL", "count": 150, "conversion_rate": 0.50},
        {"name": "Deal", "count": 45, "conversion_rate": 0.30}
    ],
    "avg_cycle_days": 28
}

# GET /api/analytics/rep/{rep_id}
{
    "rep_id": "xxx",
    "period": "2024-Q4",
    "metrics": {
        "deals_closed": 12,
        "total_value": 360000,
        "avg_deal_size": 30000,
        "win_rate": 0.35,
        "avg_meddic_score": 72
    }
}
```
EOF

echo "📄 建立模組 README..."

# 各模組 README
for i in 01-lead-source 02-mql-qualification 03-sales-conversation 04-deal-onboarding 05-customer-success 06-analytics; do
    cat > "modules/$i/README.md" << EOF
# Module: $i

## 概述

此模組是 Sales AI Automation V2 的一部分。

## 開發指南

請參考對應的 Skill 文件：
\`.claude/skills/${i%-*}-*-skill/SKILL.md\`

## 目錄結構

\`\`\`
$i/
├── __init__.py
├── README.md
├── config.yaml
├── handlers/
└── tests/
\`\`\`

## 測試

\`\`\`bash
pytest modules/$i/tests/ -v
\`\`\`
EOF
done

# ==========================================
# 根目錄檔案
# ==========================================

# .env.example
cat > .env.example << 'EOF'
# Environment
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/sales_ai

# LLM
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
DEFAULT_LLM_MODEL=claude-sonnet-4-20250514

# Slack
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_SIGNING_SECRET=xxx
SLACK_APP_TOKEN=xapp-xxx

# Google
GOOGLE_CREDENTIALS_PATH=./credentials/google-service-account.json
GOOGLE_ADS_DEVELOPER_TOKEN=xxx
GOOGLE_ADS_CLIENT_ID=xxx
GOOGLE_ADS_CLIENT_SECRET=xxx

# Facebook
FACEBOOK_APP_ID=xxx
FACEBOOK_APP_SECRET=xxx
FACEBOOK_ACCESS_TOKEN=xxx

# Squarespace
SQUARESPACE_API_KEY=xxx
EOF

# .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local
*.env

# Credentials
credentials/
*.json
!package.json

# Build
dist/
build/
*.egg-info/

# Test
.pytest_cache/
.coverage
htmlcov/

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db
EOF

# pyproject.toml
cat > pyproject.toml << 'EOF'
[project]
name = "sales-ai-automation-v2"
version = "2.0.0"
description = "AI-powered sales automation system"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests", "modules"]
python_files = ["test_*.py"]
asyncio_mode = "auto"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100
EOF

# requirements.txt
cat > requirements.txt << 'EOF'
# Core
anthropic>=0.40.0
openai>=1.50.0
pydantic>=2.0.0

# Database
sqlalchemy>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0

# API
fastapi>=0.115.0
uvicorn>=0.32.0

# Integrations
slack-sdk>=3.33.0
google-api-python-client>=2.150.0
google-auth>=2.35.0
facebook-business>=21.0.0

# Utils
python-dotenv>=1.0.0
httpx>=0.27.0
tenacity>=9.0.0

# Audio Processing
openai-whisper>=20240930
pydub>=0.25.0
EOF

# requirements-dev.txt
cat > requirements-dev.txt << 'EOF'
# Testing
pytest>=8.3.0
pytest-asyncio>=0.24.0
pytest-cov>=6.0.0

# Code Quality
black>=24.10.0
isort>=5.13.0
flake8>=7.1.0
mypy>=1.13.0

# Development
ipython>=8.29.0
rich>=13.9.0
EOF

# README.md
cat > README.md << 'EOF'
# Sales AI Automation V2.0 🚀

AI 驅動的完整銷售生命週期自動化系統。

## 功能模組

| 模組 | 說明 |
|------|------|
| 01-lead-source | 廣告來源追蹤 (Google Ads, Facebook, Squarespace) |
| 02-mql-qualification | MQL 開發分析和自動指派 |
| 03-sales-conversation | 銷售對話分析和教練回饋 |
| 04-deal-onboarding | 成交導入和客戶畫像建立 |
| 05-customer-success | CS 切入時機和話術建議 |
| 06-analytics | 漏斗分析和業務績效報表 |

## 快速開始

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env

# 執行測試
pytest
```

## 多實例開發

本專案支援多個 Claude Code 實例同時開發。請參考 `AGENTS.md` 了解分工方式。

## 文件

- [架構說明](docs/architecture.md)
- [API 文件](docs/api-reference.md)
- [開發指南](docs/guides/local-development.md)
EOF

# AGENTS.md
cat > AGENTS.md << 'EOF'
# Claude Code Agents 開發指南

## Agent 分工

| Agent | 負責範圍 | 工作目錄 |
|-------|----------|----------|
| A | Core + Infrastructure | `/` |
| B | Lead Source | `/modules/01-lead-source` |
| C | MQL Qualification | `/modules/02-mql-qualification` |
| D | Sales Conversation + Slack | `/modules/03-sales-conversation` |
| E | Deal Onboarding + CS | `/modules/04-deal-onboarding` |
| F | Analytics | `/modules/06-analytics` |

## 啟動指令

詳見各 Agent 的 SKILL.md 檔案：
- `.claude/skills/00-core-skill/SKILL.md`
- `.claude/skills/01-lead-source-skill/SKILL.md`
- 以此類推...

## 衝突避免原則

1. **鎖定檔案**：`core/` 只有 Agent A 能修改
2. **分支隔離**：每個 Agent 用獨立的 feature branch
3. **介面穩定**：修改 `core/interfaces/` 前需協調
EOF

echo ""
echo "✅ 專案初始化完成！"
echo ""
echo "📁 目錄結構已建立"
echo "📄 基礎檔案已建立"
echo "📝 Skills SKILL.md 已建立"
echo ""
echo "下一步："
echo "1. cd $PROJECT_ROOT"
echo "2. cp .env.example .env"
echo "3. 編輯 .env 填入 API keys"
echo "4. pip install -r requirements.txt"
echo ""
echo "開始開發："
echo "- Agent A: cd . && claude"
echo "- Agent B: cd modules/01-lead-source && claude"
echo "- Agent C: cd modules/02-mql-qualification && claude"
echo "- Agent D: cd modules/03-sales-conversation && claude"
echo "- Agent E: cd modules/04-deal-onboarding && claude"
echo "- Agent F: cd modules/06-analytics && claude"
