# Agentic Orchestrator V3 - State-Based Dynamic Flow

## 概述

此文件記錄了 `orchestrator.py` 的 V3 重構，實作基於狀態的動態流程。

## 架構變更

### 1. AnalysisState 共享狀態物件

```python
@dataclass
class AnalysisState:
    case_id: str
    transcript: List[Dict]
    context_data: Optional[Dict] = None     # From Agent 1
    buyer_data: Optional[Dict] = None       # From Agent 2
    competitor_data: Optional[Dict] = None  # From Agent 4
    seller_data: Optional[Dict] = None      # From Agent 3
    
    # Flow Control
    feedback_history: List[str]
    quality_checks: Dict[str, bool]
    buyer_refinement_count: int = 0
    max_refinements: int = 2
    competitors_detected: bool = False
```

### 2. 執行流程

```
Phase 1: Base Analysis
├── Agent 1 (Context) ─┬─ Parallel
└── Agent 2 (Buyer)   ─┘
        │
        ▼
Phase 2: Quality Loop
├── Evaluate buyer_data quality
├── If quality check fails:
│   └── Refine Agent 2 (max 2 times)
└── Update state
        │
        ▼
Phase 3: Conditional Triggering
├── Detect competitors in transcript
├── If competitors found:
│   └── Run competitor analysis
└── If no competitors:
    └── Skip to save tokens
        │
        ▼
Phase 4: Synthesis
└── Agent 3 (Seller/Coach) with all data
        │
        ▼
Phase 5: Summary
└── Agent 4 (Summary) for customer email
```

### 3. 品質評估規則 (Agent 2)

- **Rule 1**: `identifiedNeeds` 不可為空，且至少 2 項
- **Rule 2**: `psychology.hesitations` 不可為空
- **Rule 3**: `meddic.pain` 描述至少 10 字
- **Rule 4**: `trustScore` 在 0-100 範圍內

### 4. 競品偵測關鍵字

```python
COMPETITOR_KEYWORDS = [
    "競爭對手", "對手", "其他廠商", "別家",
    "結帳快手", "海底撈", "foodpanda", "uber eats",
    "比較", "相比", "對比", "其他選擇",
]
```

## 新增功能

### base.py - refine() 方法

```python
def refine(
    self,
    transcript_segments: List[Dict],
    previous_result: Dict,
    feedback: str,
    **kwargs
) -> GeminiResponse:
    """
    基於反饋修正先前的分析結果 (Self-Correction / Reflexion)
    """
```

## 預期行為

### Scenario A: 品質差需要修正
1. Agent 2 第一次說「無痛點」
2. 系統偵測到 `hesitations` 為空
3. 自動觸發 Refine，附帶修正指示
4. 第二次 Agent 2 抓出「客戶覺得太貴」
5. Agent 3 根據「太貴」給出價格談判建議

### Scenario B: 無競品提及
1. 系統掃描 transcript，無競品關鍵字
2. 跳過 Agent 4 (Competitor)
3. 直接執行 Agent 3
4. 節省約 30% 執行時間和 Token

## 部署命令

```bash
gcloud builds submit --config=cloudbuild.analysis.deploy.yaml
```
