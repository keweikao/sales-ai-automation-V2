# Phase 4: 業務模組開發上下文

本文件提供給負責 Phase 4 (業務模組補完) 的 Agent 使用。

## 專案狀態

### 已完成
- **Phase 0**: P0 阻塞問題已修復
- **Phase 1**: API Gateway + 前端基礎
- **Phase 2**: Dashboard 開發完成

### 本階段目標
完成 Module 04-07 的業務邏輯實作。

---

## 任務清單

| 優先度 | 模組 | 功能 | 目前狀態 |
|--------|------|------|----------|
| P4-1 | Module 06: Analytics | 週報生成、Rep 績效分析 | 部分完成 |
| P4-2 | Module 07: Ops Automation | 監控、自動修復 | 部分完成 |
| P4-3 | Module 04: Deal Onboarding | 成交入職流程 | 僅有目錄 |
| P4-4 | Module 05: Customer Success | 健康評分、續約預測 | 僅有目錄 |

---

## P4-1: Module 06 - Analytics

### 目錄結構

```
modules/06-analytics/
├── __init__.py
├── weekly_reports/
│   ├── generator.py         # 已有基礎框架
│   ├── upload_data_aggregator.py
│   ├── upload_report_models.py
│   └── upload_slack_formatter.py
└── rep_performance/
    └── __init__.py           # 待實作
```

### 待完成功能

#### 1. 週報生成器 (`weekly_reports/generator.py`)

目前狀態：有框架但 TODO 未實作

```python
# 需要實作的方法
class WeeklyReportGenerator:
    async def generate(self, week_start: Optional[datetime] = None) -> WeeklyReportData:
        # TODO: Query conversations from the period
        # TODO: Aggregate metrics
        # TODO: Generate insights
```

**實作需求**：
- 查詢指定週期內的對話 (`ConversationRepository.list_by_date_range`)
- 聚合指標：總對話數、已分析數、平均 MEDDIC 分數
- 按業務員分組統計
- 使用 LLM 生成 top insights 和 coaching highlights

#### 2. 業務員績效模組 (`rep_performance/`)

**需要新建的檔案**：

```python
# rep_performance/analyzer.py
class RepPerformanceAnalyzer:
    """分析單一業務員的績效趨勢"""

    async def analyze(self, rep_id: str, period_days: int = 30) -> RepPerformance:
        """
        分析業務員績效

        Returns:
            RepPerformance 包含:
            - conversation_count: int
            - avg_meddic_score: float
            - score_trend: 'up' | 'down' | 'stable'
            - strengths: list[str]
            - improvement_areas: list[str]
            - comparison_to_team: float (百分位)
        """
        pass

# rep_performance/leaderboard.py
class RepLeaderboard:
    """業務員排行榜"""

    async def get_top_performers(self, limit: int = 10, period_days: int = 7) -> list[PerformerStats]:
        pass

    async def get_team_stats(self) -> TeamStats:
        pass
```

---

## P4-2: Module 07 - Ops Automation

### 目錄結構

```
modules/07-ops-automation/
├── __init__.py
├── monitoring/
│   ├── __init__.py
│   └── error_notifier.py    # 已有基礎實作
├── health_check/            # 待建立
└── remediation/             # 待建立
```

### 待完成功能

#### 1. 完善錯誤通知 (`monitoring/error_notifier.py`)

目前狀態：有框架，需要連接 NotificationService

```python
# 需要完善的部分
async def _send_immediate(self, error: dict):
    # 目前只是 print，需要實際發送
    if self.notification_service:
        await self.notification_service.send_slack_message(
            channel=self.slack_channel,
            text=f"[{error['severity']}] {error['message']}",
            blocks=self._build_error_blocks(error),
        )
```

#### 2. 健康檢查模組 (`health_check/`)

**需要新建的檔案**：

```python
# health_check/checker.py
from enum import Enum

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthChecker:
    """檢查各服務健康狀態"""

    async def check_all(self) -> dict[str, ServiceStatus]:
        """
        檢查所有服務狀態

        Returns:
            {
                "transcription": ServiceStatus.HEALTHY,
                "analysis": ServiceStatus.HEALTHY,
                "notification": ServiceStatus.DEGRADED,
                "database": ServiceStatus.HEALTHY,
            }
        """
        pass

    async def check_transcription(self) -> ServiceStatus:
        """檢查 Transcription Service"""
        pass

    async def check_llm_gateway(self) -> ServiceStatus:
        """檢查 LLM Gateway"""
        pass
```

#### 3. 自動修復模組 (`remediation/`)

```python
# remediation/auto_retry.py
class AutoRetryService:
    """自動重試失敗的任務"""

    async def retry_failed_transcriptions(self, max_retries: int = 3) -> int:
        """
        重試失敗的轉錄任務

        Returns:
            成功重試的數量
        """
        pass

    async def retry_failed_analyses(self, max_retries: int = 3) -> int:
        """重試失敗的分析任務"""
        pass

# remediation/cleanup.py
class DataCleanupService:
    """清理過期或無效的數據"""

    async def cleanup_stale_pending(self, hours_threshold: int = 24) -> int:
        """清理超過 N 小時仍在 pending 的任務"""
        pass
```

---

## P4-3: Module 04 - Deal Onboarding

### 目錄結構 (待建立)

```
modules/04-deal-onboarding/
├── __init__.py
├── checklist/
│   ├── __init__.py
│   ├── template.py          # 入職清單模板
│   └── tracker.py           # 進度追蹤
├── handoff/
│   ├── __init__.py
│   └── sales_to_cs.py       # 銷售→客戶成功交接
└── schemas.py
```

### 功能需求

#### 1. Schema 定義 (`schemas.py`)

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional

class OnboardingStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class ChecklistItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    required: bool = True
    status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    notes: Optional[str] = None

class OnboardingChecklist(BaseModel):
    deal_id: str
    customer_name: str
    sales_rep_id: str
    cs_rep_id: Optional[str] = None
    items: list[ChecklistItem]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    overall_status: OnboardingStatus = OnboardingStatus.NOT_STARTED

class HandoffDocument(BaseModel):
    deal_id: str
    from_rep: str              # 銷售
    to_rep: str                # 客戶成功
    customer_summary: str      # 來自分析結果
    key_pain_points: list[str]
    identified_needs: list[str]
    champion_info: Optional[str] = None
    decision_process: Optional[str] = None
    special_notes: Optional[str] = None
    handoff_date: datetime
```

#### 2. 清單模板 (`checklist/template.py`)

```python
DEFAULT_CHECKLIST_ITEMS = [
    {
        "id": "contract_signed",
        "title": "合約簽署",
        "description": "確認合約已完成簽署",
        "required": True,
    },
    {
        "id": "payment_received",
        "title": "款項確認",
        "description": "確認首期款項已入帳",
        "required": True,
    },
    {
        "id": "kickoff_scheduled",
        "title": "Kickoff 會議安排",
        "description": "安排客戶啟動會議",
        "required": True,
    },
    {
        "id": "cs_assigned",
        "title": "客戶成功經理指派",
        "description": "指派專屬 CS 經理",
        "required": True,
    },
    {
        "id": "handoff_completed",
        "title": "交接完成",
        "description": "銷售與 CS 完成交接",
        "required": True,
    },
    {
        "id": "welcome_email_sent",
        "title": "歡迎信發送",
        "description": "發送客戶歡迎信",
        "required": False,
    },
    {
        "id": "training_scheduled",
        "title": "培訓安排",
        "description": "安排產品培訓時間",
        "required": False,
    },
]

class ChecklistTemplate:
    @staticmethod
    def create_default(deal_id: str, customer_name: str, sales_rep_id: str) -> OnboardingChecklist:
        pass
```

#### 3. 交接服務 (`handoff/sales_to_cs.py`)

```python
class SalesToCSHandoff:
    """處理銷售到客戶成功的交接"""

    def __init__(self, conversation_repo, notification_service):
        self.conversation_repo = conversation_repo
        self.notification_service = notification_service

    async def create_handoff(
        self,
        deal_id: str,
        sales_rep_id: str,
        cs_rep_id: str,
    ) -> HandoffDocument:
        """
        建立交接文件

        1. 從相關對話中提取分析結果
        2. 彙整客戶摘要、痛點、需求
        3. 建立交接文件
        4. 通知 CS 經理
        """
        pass

    async def notify_cs_rep(self, handoff: HandoffDocument) -> None:
        """發送交接通知給 CS 經理"""
        pass
```

---

## P4-4: Module 05 - Customer Success

### 目錄結構 (待建立)

```
modules/05-customer-success/
├── __init__.py
├── health_score/
│   ├── __init__.py
│   ├── calculator.py        # 健康分數計算
│   └── factors.py           # 評分因素
├── renewal/
│   ├── __init__.py
│   └── predictor.py         # 續約預測
├── upsell/
│   ├── __init__.py
│   └── detector.py          # 增購機會偵測
└── schemas.py
```

### 功能需求

#### 1. Schema 定義 (`schemas.py`)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class HealthLevel(str, Enum):
    HEALTHY = "healthy"       # 80-100
    AT_RISK = "at_risk"       # 50-79
    CRITICAL = "critical"     # 0-49

class RenewalProbability(str, Enum):
    HIGH = "high"             # >80%
    MEDIUM = "medium"         # 50-80%
    LOW = "low"               # <50%

class CustomerHealth(BaseModel):
    customer_id: str
    customer_name: str
    health_score: int         # 0-100
    health_level: HealthLevel

    # 評分因素
    engagement_score: int     # 互動頻率
    sentiment_score: int      # 情感分析 (從對話)
    usage_score: int          # 產品使用率
    support_score: int        # 支援互動

    # 風險指標
    risk_factors: list[str]
    improvement_actions: list[str]

    last_check_in: Optional[datetime] = None
    next_check_in_due: Optional[datetime] = None
    calculated_at: datetime

class RenewalPrediction(BaseModel):
    customer_id: str
    contract_end_date: datetime
    days_until_renewal: int
    renewal_probability: RenewalProbability
    confidence: float         # 0-1

    positive_factors: list[str]
    negative_factors: list[str]
    recommended_actions: list[str]

    predicted_at: datetime

class UpsellOpportunity(BaseModel):
    customer_id: str
    opportunity_type: str     # e.g., "seat_expansion", "feature_upgrade"
    confidence: float         # 0-1
    estimated_value: Optional[float] = None

    signals: list[str]        # 觸發信號
    recommended_approach: str
    best_timing: Optional[str] = None

    detected_at: datetime
```

#### 2. 健康分數計算 (`health_score/calculator.py`)

```python
class HealthScoreCalculator:
    """計算客戶健康分數"""

    # 權重配置
    WEIGHTS = {
        "engagement": 0.30,
        "sentiment": 0.25,
        "usage": 0.25,
        "support": 0.20,
    }

    def __init__(self, conversation_repo):
        self.conversation_repo = conversation_repo

    async def calculate(self, customer_id: str) -> CustomerHealth:
        """
        計算客戶健康分數

        步驟：
        1. 計算 engagement_score (互動頻率、回應速度)
        2. 計算 sentiment_score (從對話分析結果)
        3. 計算 usage_score (產品使用數據 - 可能需外部整合)
        4. 計算 support_score (支援工單數量、解決速度)
        5. 加權平均得出總分
        6. 識別風險因素
        7. 建議改善行動
        """
        pass

    async def _calculate_sentiment_score(self, customer_id: str) -> int:
        """
        從對話分析結果計算情感分數

        - 使用最近 N 次對話的 trustScore
        - 考慮 hesitations 和 painPoints 的趨勢
        """
        pass
```

#### 3. 續約預測 (`renewal/predictor.py`)

```python
class RenewalPredictor:
    """預測客戶續約可能性"""

    def __init__(self, health_calculator: HealthScoreCalculator):
        self.health_calculator = health_calculator

    async def predict(self, customer_id: str) -> RenewalPrediction:
        """
        預測續約可能性

        考慮因素：
        - 客戶健康分數
        - 合約剩餘時間
        - 歷史互動趨勢
        - 最近對話中的信號 (如抱怨、競品提及)
        """
        pass

    async def get_at_risk_customers(
        self,
        days_until_renewal: int = 90,
        min_risk_level: str = "medium"
    ) -> list[RenewalPrediction]:
        """取得高風險客戶列表"""
        pass
```

#### 4. 增購偵測 (`upsell/detector.py`)

```python
class UpsellDetector:
    """偵測增購機會"""

    SIGNAL_PATTERNS = [
        {"pattern": "需要更多使用者", "type": "seat_expansion"},
        {"pattern": "進階功能", "type": "feature_upgrade"},
        {"pattern": "其他部門", "type": "cross_sell"},
    ]

    async def detect(self, customer_id: str) -> list[UpsellOpportunity]:
        """
        從對話中偵測增購信號

        分析最近對話中的：
        - 明確需求表達
        - 隱含的擴展意圖
        - 使用瓶頸暗示
        """
        pass

    async def get_top_opportunities(self, limit: int = 10) -> list[UpsellOpportunity]:
        """取得最佳增購機會"""
        pass
```

---

## 共用資源

### 資料庫 Repositories

已有的 Repository 可直接使用：

```python
from core.database import ConversationRepository, LeadRepository

# 使用範例
repo = ConversationRepository()
conversations = await repo.list_by_sales_rep(rep_id, start_date, end_date)
```

### 需要新增的 Repository

```python
# core/database/repositories/customer_repository.py
class CustomerRepository:
    """客戶資料 Repository"""

    COLLECTION = "customers"

    async def get(self, customer_id: str) -> Optional[Customer]:
        pass

    async def list_with_upcoming_renewal(self, days: int = 90) -> list[Customer]:
        pass

    async def update_health_score(self, customer_id: str, health: CustomerHealth) -> None:
        pass

# core/database/repositories/onboarding_repository.py
class OnboardingRepository:
    """入職流程 Repository"""

    COLLECTION = "onboarding_checklists"

    async def get(self, deal_id: str) -> Optional[OnboardingChecklist]:
        pass

    async def create(self, checklist: OnboardingChecklist) -> OnboardingChecklist:
        pass

    async def update_item_status(self, deal_id: str, item_id: str, status: str) -> None:
        pass
```

### Notification Service

使用已實作的 NotificationService：

```python
from infrastructure.services.notification import NotificationService

service = NotificationService()

# 發送 Slack 訊息
await service.send_slack_message(
    channel="#customer-success",
    text="客戶健康警報",
    blocks=[...],
)

# 發送分析完成通知
await service.send_analysis_notification(
    channel="#sales-team",
    case_id="case_001",
    summary="...",
    meddic_score=75,
    insights=["..."],
)
```

---

## API 端點擴展

Phase 4 完成後，需要在 API Gateway 新增以下端點：

### Analytics API (擴展)

```
GET  /api/v1/analytics/rep/{rep_id}/details
     Response: RepPerformanceDetail

GET  /api/v1/analytics/team
     Response: TeamStats
```

### Onboarding API (新增)

```
POST /api/v1/onboarding/checklist
     Body: { deal_id, customer_name, sales_rep_id }
     Response: OnboardingChecklist

GET  /api/v1/onboarding/checklist/{deal_id}
     Response: OnboardingChecklist

PATCH /api/v1/onboarding/checklist/{deal_id}/items/{item_id}
      Body: { status, notes }
      Response: ChecklistItem

POST /api/v1/onboarding/handoff
     Body: { deal_id, sales_rep_id, cs_rep_id }
     Response: HandoffDocument
```

### Customer Success API (新增)

```
GET  /api/v1/customers/{customer_id}/health
     Response: CustomerHealth

GET  /api/v1/customers/at-risk
     Query: threshold (default: 50)
     Response: { customers: CustomerHealth[] }

GET  /api/v1/customers/{customer_id}/renewal-prediction
     Response: RenewalPrediction

GET  /api/v1/customers/upsell-opportunities
     Query: limit (default: 10)
     Response: { opportunities: UpsellOpportunity[] }
```

---

## 開發順序建議

1. **P4-1 (Analytics)** - 先完成，因為其他模組會依賴分析數據
2. **P4-2 (Ops)** - 獨立性高，可與 P4-1 平行開發
3. **P4-3 (Onboarding)** - 依賴分析結果 (交接文件需要)
4. **P4-4 (Customer Success)** - 最後完成，依賴健康分數計算

---

## 重要檔案參考

- Core Schemas: `core/schemas/`
- Database Repositories: `core/database/repositories/`
- Notification Service: `infrastructure/services/notification/service.py`
- API Gateway: `api-gateway/`
- 現有週報生成器: `modules/06-analytics/weekly_reports/generator.py`
- 現有錯誤通知: `modules/07-ops-automation/monitoring/error_notifier.py`

---

## 驗收標準

### P4-1 Analytics
- [ ] `WeeklyReportGenerator.generate()` 返回真實數據
- [ ] `RepPerformanceAnalyzer.analyze()` 可計算業務員績效
- [ ] 週報可透過 Slack 發送

### P4-2 Ops Automation
- [ ] `HealthChecker.check_all()` 可檢查所有服務
- [ ] `AutoRetryService` 可自動重試失敗任務
- [ ] 錯誤通知實際發送到 Slack

### P4-3 Deal Onboarding
- [ ] 可建立入職清單
- [ ] 可追蹤清單進度
- [ ] 可產生交接文件並通知 CS

### P4-4 Customer Success
- [ ] 可計算客戶健康分數
- [ ] 可預測續約可能性
- [ ] 可偵測增購機會
