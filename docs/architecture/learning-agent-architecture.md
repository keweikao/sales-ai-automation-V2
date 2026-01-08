# Learning Agent Architecture

## 核心理念：從分析到學習的閉環

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        LEARNING AGENT SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐        │
│   │ PERCEIVE │ →  │  REASON  │ →  │   ACT    │ →  │  LEARN   │        │
│   │ 感知輸入  │    │  分析推理 │    │  執行建議 │    │  回饋學習 │        │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘        │
│        ↑                                               │               │
│        └───────────────── EVOLVE ←─────────────────────┘               │
│                          持續進化                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Outcome Tracking (結果追蹤層)

### 問題

目前系統只記錄「分析結果」，不追蹤「真實結果」：

- Agent 預測 MEDDIC 分數 85 分，但案子最後成交了嗎？
- Coach 建議「現在 close」，業務有執行嗎？結果如何？

### 解決方案

```python
# core/schemas/outcome.py

class DealOutcome(BaseModel):
    """交易結果 - 用於驗證預測準確度"""
    case_id: str

    # 預測值 (Agent 產出)
    predicted_meddic_score: int
    predicted_qualification: str  # qualified/nurture/disqualified
    predicted_close_probability: float
    coaching_suggestions: List[str]

    # 實際結果 (從 CRM 同步)
    actual_outcome: Literal["closed_won", "closed_lost", "ongoing", "stalled"]
    actual_close_date: Optional[datetime]
    actual_deal_value: Optional[float]
    days_to_close: Optional[int]

    # 行動追蹤
    suggestions_followed: List[str]  # 業務實際執行的建議
    suggestions_ignored: List[str]   # 業務忽略的建議

    # 評估指標
    prediction_accuracy: float  # 預測準確度
    coaching_effectiveness: float  # 建議有效性

    recorded_at: datetime
    salesforce_opportunity_id: Optional[str]
```

### 資料來源

1. **Salesforce Sync** - 定期同步 Opportunity 狀態
2. **Slack Interactions** - 追蹤業務對建議的回應
3. **Summary Edits** - 業務修改摘要 = 隱性回饋

---

## Layer 2: Memory System (記憶系統)

### 三種記憶類型

```text
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT MEMORY SYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ EPISODIC MEMORY │  │ SEMANTIC MEMORY │  │ PROCEDURAL MEM  │ │
│  │    情境記憶      │  │    語意記憶      │  │    程序記憶     │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │
│  │ 具體案例經驗     │  │ 抽象知識概念     │  │ 策略與技巧      │ │
│  │                 │  │                 │  │                 │ │
│  │ • 成功案例      │  │ • 產業知識      │  │ • 成交技巧      │ │
│  │ • 失敗案例      │  │ • 產品知識      │  │ • 異議處理      │ │
│  │ • 邊界案例      │  │ • 客戶類型      │  │ • 談判策略      │ │
│  │                 │  │                 │  │                 │ │
│  │ Vector DB       │  │ Knowledge Graph │  │ Strategy Pool   │ │
│  │ (Pinecone)      │  │ (Neo4j/Memgraph)│  │ (Firestore)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Episodic Memory (情境記憶) - 案例庫

```python
# infrastructure/services/learning/case_memory.py

class CaseMemory:
    """儲存和檢索相似案例"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.embedding_model = "text-embedding-004"

    async def store_case(self, case: AnalyzedCase, outcome: DealOutcome):
        """將完成的案例存入向量資料庫"""
        embedding = await self.embed(case.to_searchable_text())

        metadata = {
            "case_id": case.id,
            "industry": case.customer_industry,
            "deal_size": case.deal_size_category,
            "meddic_score": case.meddic_score,
            "outcome": outcome.actual_outcome,
            "key_objections": case.objections,
            "winning_strategy": outcome.suggestions_followed,
        }

        await self.vector_store.upsert(
            id=case.id,
            embedding=embedding,
            metadata=metadata
        )

    async def retrieve_similar_cases(
        self,
        current_case: AnalysisContext,
        outcome_filter: Optional[str] = None,  # "closed_won" for success examples
        top_k: int = 5
    ) -> List[SimilarCase]:
        """檢索相似案例作為學習參考"""
        query_embedding = await self.embed(current_case.to_searchable_text())

        filters = {}
        if outcome_filter:
            filters["outcome"] = outcome_filter

        results = await self.vector_store.query(
            embedding=query_embedding,
            filters=filters,
            top_k=top_k
        )

        return [SimilarCase.from_result(r) for r in results]
```

### 如何使用記憶

```python
# 在 Agent 分析前，先檢索相似成功案例
similar_wins = await case_memory.retrieve_similar_cases(
    current_case=context,
    outcome_filter="closed_won",
    top_k=3
)

# 將成功案例作為 few-shot examples 注入 prompt
enhanced_prompt = f"""
Based on similar successful cases:

{format_similar_cases(similar_wins)}

Now analyze this conversation and provide recommendations
that align with proven success patterns.
"""
```

---

## Layer 3: Feedback Loop (回饋迴路)

### 三種回饋類型

```text
┌─────────────────────────────────────────────────────────────────┐
│                      FEEDBACK TAXONOMY                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. EXPLICIT FEEDBACK (顯性回饋)                                │
│     - 對 Coach 建議的反應 (接受/拒絕)                           │
│     - 業務編輯/修正摘要內容                                     │
│     - Manager 對分析的評分                                      │
│                                                                 │
│  2. IMPLICIT FEEDBACK (隱性回饋)                                │
│     - 建議被執行 = 正向訊號                                     │
│     - 建議被忽略 = 負向訊號                                     │
│     - 回覆速度/頻率 = 緊急程度                                  │
│                                                                 │
│  3. OUTCOME FEEDBACK (結果回饋)                                 │
│     - Deal Closed Won = 驗證分析正確                            │
│     - Deal Closed Lost = 分析哪裡出錯？                         │
│     - 預測 vs 實際的差異 = 校正模型                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 回饋收集系統

```python
# infrastructure/services/learning/feedback_collector.py

class FeedbackCollector:
    """收集各種回饋訊號"""

    async def on_summary_edited(
        self,
        case_id: str,
        original: str,
        edited: str,
        editor: str
    ):
        """業務編輯摘要 = 隱性回饋"""
        diff = compute_semantic_diff(original, edited)

        feedback = ImplicitFeedback(
            case_id=case_id,
            feedback_type="summary_correction",
            original_content=original,
            corrected_content=edited,
            correction_categories=classify_corrections(diff),
            editor_id=editor,
            timestamp=datetime.utcnow()
        )

        await self.store_feedback(feedback)
        await self.trigger_learning_signal(feedback)

    async def on_coaching_response(
        self,
        case_id: str,
        suggestion_id: str,
        response_type: Literal["accepted", "rejected", "modified"],
        rep_comment: Optional[str]
    ):
        """業務對 Coach 建議的回應"""
        feedback = ExplicitFeedback(
            case_id=case_id,
            suggestion_id=suggestion_id,
            response_type=response_type,
            rep_comment=rep_comment,
            timestamp=datetime.utcnow()
        )

        await self.store_feedback(feedback)

        # 如果是拒絕，分析原因
        if response_type == "rejected" and rep_comment:
            rejection_reason = await self.analyze_rejection_reason(rep_comment)
            await self.update_strategy_pool(suggestion_id, rejection_reason)
```

---

## Layer 4: Evaluation Framework (評估框架)

### 追蹤的指標

```python
# core/schemas/agent_metrics.py

class AgentPerformanceMetrics(BaseModel):
    """Agent 效能指標"""

    agent_id: str
    evaluation_period: str  # "weekly", "monthly"

    # 預測準確度
    meddic_prediction_accuracy: float  # 預測分數 vs 實際結果的相關性
    qualification_accuracy: float      # qualified/disqualified 準確率
    close_probability_mae: float       # 成交機率的平均絕對誤差

    # 建議有效性
    suggestion_acceptance_rate: float  # 建議被採納的比率
    suggestion_outcome_correlation: float  # 被採納建議與成交的相關性

    # 業務滿意度
    summary_edit_rate: float  # 摘要被編輯的比率 (越低越好)
    average_edit_distance: float  # 平均編輯距離 (越低越好)

    # 效率指標
    average_processing_time: float
    token_cost_per_case: float

    # 比較基準
    vs_baseline: Dict[str, float]  # 與基準的比較
    vs_previous_period: Dict[str, float]  # 與上期的比較
```

### 評估流程

```python
# infrastructure/services/learning/evaluator.py

class AgentEvaluator:
    """定期評估 Agent 效能"""

    async def evaluate_weekly(self) -> EvaluationReport:
        """每週評估"""

        # 1. 收集本週完成的案例
        cases = await self.get_completed_cases(days=7)

        # 2. 收集結果資料
        outcomes = await self.get_outcomes(case_ids=[c.id for c in cases])

        # 3. 計算預測準確度
        predictions = [(c.meddic_score, o.actual_outcome) for c, o in zip(cases, outcomes)]
        accuracy = self.calculate_prediction_accuracy(predictions)

        # 4. 分析建議有效性
        suggestions = await self.get_all_suggestions(case_ids=[c.id for c in cases])
        feedback = await self.get_all_feedback(suggestion_ids=[s.id for s in suggestions])
        effectiveness = self.calculate_suggestion_effectiveness(suggestions, feedback, outcomes)

        # 5. 識別改進機會
        improvement_areas = self.identify_improvement_areas(accuracy, effectiveness)

        return EvaluationReport(
            period="weekly",
            accuracy_metrics=accuracy,
            effectiveness_metrics=effectiveness,
            improvement_areas=improvement_areas,
            recommended_actions=self.generate_recommendations(improvement_areas)
        )
```

---

## Layer 5: Adaptive Learning (自適應學習)

### 學習策略

```text
┌─────────────────────────────────────────────────────────────────┐
│                    ADAPTIVE LEARNING STRATEGIES                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Strategy 1: PROMPT EVOLUTION (提示詞進化)                      │
│  -----------------------------------------------------------   │
│  - A/B 測試不同 prompt 版本                                     │
│  - 基於回饋自動調整 prompt                                      │
│  - 保留表現最佳的版本                                           │
│                                                                 │
│  Strategy 2: FEW-SHOT LEARNING (少樣本學習)                     │
│  -----------------------------------------------------------   │
│  - 動態選擇最相關的成功案例作為 examples                        │
│  - 根據案例類型調整 example 選擇策略                            │
│  - 持續更新 example pool                                        │
│                                                                 │
│  Strategy 3: PERSONALIZATION (個人化)                           │
│  -----------------------------------------------------------   │
│  - 學習每位業務的風格偏好                                       │
│  - 根據業務經驗調整建議深度                                     │
│  - 追蹤個人成功模式                                             │
│                                                                 │
│  Strategy 4: STRATEGY POOL (策略池)                             │
│  -----------------------------------------------------------   │
│  - 維護一個經過驗證的銷售策略庫                                 │
│  - 根據情境匹配最佳策略                                         │
│  - 淘汰無效策略，發掘新策略                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Prompt Evolution 實作

```python
# infrastructure/services/learning/prompt_evolution.py

class PromptEvolver:
    """自動進化 Prompt"""

    def __init__(self):
        self.prompt_versions: Dict[str, List[PromptVersion]] = {}
        self.active_experiments: Dict[str, ABExperiment] = {}

    async def create_experiment(
        self,
        agent_id: str,
        hypothesis: str,
        control_prompt: str,
        treatment_prompt: str,
        success_metric: str,
        sample_size: int = 100
    ) -> ABExperiment:
        """建立 A/B 測試實驗"""
        experiment = ABExperiment(
            id=f"exp_{agent_id}_{datetime.now().strftime('%Y%m%d')}",
            agent_id=agent_id,
            hypothesis=hypothesis,
            control=PromptVariant(prompt=control_prompt, name="control"),
            treatment=PromptVariant(prompt=treatment_prompt, name="treatment"),
            success_metric=success_metric,
            required_sample_size=sample_size,
            status="running"
        )

        self.active_experiments[experiment.id] = experiment
        return experiment

    async def assign_variant(self, experiment_id: str, case_id: str) -> PromptVariant:
        """隨機分配實驗組別"""
        experiment = self.active_experiments[experiment_id]

        # 50/50 隨機分配
        variant = random.choice([experiment.control, experiment.treatment])

        await self.record_assignment(experiment_id, case_id, variant.name)
        return variant

    async def analyze_experiment(self, experiment_id: str) -> ExperimentResult:
        """分析實驗結果"""
        experiment = self.active_experiments[experiment_id]

        control_outcomes = await self.get_outcomes(experiment_id, "control")
        treatment_outcomes = await self.get_outcomes(experiment_id, "treatment")

        # 統計顯著性檢定
        p_value = self.calculate_significance(control_outcomes, treatment_outcomes)

        if len(control_outcomes) >= experiment.required_sample_size:
            winner = self.determine_winner(control_outcomes, treatment_outcomes, p_value)

            if winner and p_value < 0.05:
                # 顯著差異，採用勝出版本
                await self.promote_prompt(experiment.agent_id, winner)

            experiment.status = "completed"

        return ExperimentResult(
            experiment_id=experiment_id,
            control_metrics=self.calculate_metrics(control_outcomes),
            treatment_metrics=self.calculate_metrics(treatment_outcomes),
            p_value=p_value,
            winner=winner,
            status=experiment.status
        )
```

### Personalized Agent (個人化 Agent)

```python
# modules/03-sales-conversation/meddic/agents/adaptive_coach.py

class AdaptiveCoachAgent(CoachAgent):
    """自適應教練 Agent - 學習每位業務的風格"""

    def __init__(self, rep_memory: RepMemory, case_memory: CaseMemory):
        super().__init__()
        self.rep_memory = rep_memory
        self.case_memory = case_memory

    async def generate_coaching(
        self,
        context: AnalysisContext,
        rep_id: str
    ) -> CoachingResult:
        """生成個人化教練建議"""

        # 1. 獲取業務的歷史表現
        rep_profile = await self.rep_memory.get_profile(rep_id)

        # 2. 找出該業務的成功模式
        rep_wins = await self.case_memory.retrieve_cases(
            rep_id=rep_id,
            outcome="closed_won",
            top_k=5
        )

        # 3. 識別該業務的弱點
        rep_losses = await self.case_memory.retrieve_cases(
            rep_id=rep_id,
            outcome="closed_lost",
            top_k=3
        )
        loss_patterns = self.analyze_loss_patterns(rep_losses)

        # 4. 生成個人化提示
        personalized_context = f"""
        ## Rep Profile
        - Experience Level: {rep_profile.experience_level}
        - Preferred Communication Style: {rep_profile.communication_style}
        - Strengths: {', '.join(rep_profile.strengths)}
        - Areas for Improvement: {', '.join(rep_profile.improvement_areas)}

        ## Past Success Patterns
        {self.format_success_patterns(rep_wins)}

        ## Common Pitfalls to Avoid
        {self.format_loss_patterns(loss_patterns)}

        ## Current Case
        {context.to_prompt()}
        """

        # 5. 調整建議的風格和深度
        coaching = await super().generate_coaching(personalized_context)

        return self.adapt_to_rep_style(coaching, rep_profile)
```

---

## Layer 6: Self-Improvement Pipeline (自我改進管線)

### 完整的學習循環

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                     SELF-IMPROVEMENT PIPELINE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐         │
│   │ COLLECT │ --> │ ANALYZE │ --> │  LEARN  │ --> │  APPLY  │         │
│   └─────────┘     └─────────┘     └─────────┘     └─────────┘         │
│        │               │               │               │               │
│        v               v               v               v               │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐         │
│   │Outcomes │     │Patterns │     │Insights │     │Updates  │         │
│   │Feedback │     │Anomalies│     │New Rules│     │Prompts  │         │
│   │Metrics  │     │Trends   │     │Examples │     │Strategies│        │
│   └─────────┘     └─────────┘     └─────────┘     └─────────┘         │
│                                                                         │
│   Daily              Weekly           Weekly          Continuous        │
│   Continuous         Scheduled        Human Review    Auto-Deploy       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 實作

```python
# infrastructure/services/learning/self_improvement.py

class SelfImprovementPipeline:
    """Agent 自我改進管線"""

    def __init__(
        self,
        feedback_collector: FeedbackCollector,
        evaluator: AgentEvaluator,
        prompt_evolver: PromptEvolver,
        case_memory: CaseMemory
    ):
        self.feedback_collector = feedback_collector
        self.evaluator = evaluator
        self.prompt_evolver = prompt_evolver
        self.case_memory = case_memory

    async def run_weekly_improvement_cycle(self):
        """每週改進循環"""

        # Phase 1: Collect - 收集本週資料
        outcomes = await self.feedback_collector.get_week_outcomes()
        feedback = await self.feedback_collector.get_week_feedback()

        # Phase 2: Analyze - 分析表現
        evaluation = await self.evaluator.evaluate_weekly()

        # Phase 3: Learn - 提取學習
        learnings = await self.extract_learnings(evaluation, outcomes, feedback)

        # Phase 4: Apply - 應用改進
        improvements = await self.apply_improvements(learnings)

        # Generate report
        report = ImprovementReport(
            period=f"Week of {datetime.now().strftime('%Y-%m-%d')}",
            evaluation_summary=evaluation.summary,
            key_learnings=learnings,
            improvements_applied=improvements,
            next_experiments=await self.plan_next_experiments(learnings)
        )

        await self.notify_stakeholders(report)
        return report

    async def extract_learnings(
        self,
        evaluation: EvaluationReport,
        outcomes: List[DealOutcome],
        feedback: List[Feedback]
    ) -> List[Learning]:
        """從資料中提取學習"""
        learnings = []

        # 1. 分析預測失誤
        prediction_errors = self.analyze_prediction_errors(outcomes)
        for error in prediction_errors:
            learnings.append(Learning(
                type="prediction_error",
                insight=f"MEDDIC score overestimated for {error.pattern}",
                action="Adjust scoring criteria for {error.pattern}",
                confidence=error.confidence
            ))

        # 2. 分析建議被拒原因
        rejection_patterns = self.analyze_rejection_patterns(feedback)
        for pattern in rejection_patterns:
            learnings.append(Learning(
                type="suggestion_rejection",
                insight=f"'{pattern.suggestion_type}' often rejected: {pattern.common_reason}",
                action=f"Revise prompt to address: {pattern.common_reason}",
                confidence=pattern.confidence
            ))

        # 3. 發現成功模式
        success_patterns = self.analyze_success_patterns(outcomes)
        for pattern in success_patterns:
            learnings.append(Learning(
                type="success_pattern",
                insight=f"High close rate when: {pattern.condition}",
                action=f"Add to strategy pool: {pattern.strategy}",
                confidence=pattern.confidence
            ))

        return learnings

    async def apply_improvements(self, learnings: List[Learning]) -> List[Improvement]:
        """應用學習到系統"""
        improvements = []

        for learning in learnings:
            if learning.confidence < 0.7:
                # 信心不足，設為實驗
                experiment = await self.prompt_evolver.create_experiment(
                    agent_id=learning.target_agent,
                    hypothesis=learning.insight,
                    control_prompt=learning.current_prompt,
                    treatment_prompt=learning.proposed_prompt
                )
                improvements.append(Improvement(
                    type="experiment_started",
                    learning=learning,
                    action=f"Started A/B test: {experiment.id}"
                ))
            else:
                # 高信心，直接應用
                if learning.type == "success_pattern":
                    await self.case_memory.add_to_example_pool(learning)
                elif learning.type == "suggestion_rejection":
                    await self.prompt_evolver.update_prompt(learning)

                improvements.append(Improvement(
                    type="direct_application",
                    learning=learning,
                    action=f"Applied: {learning.action}"
                ))

        return improvements
```

---

## 實作路線圖

### Phase 1: Foundation

- 建立 Outcome Tracking Schema
- 實作 Salesforce Outcome Sync
- 建立 Feedback Collection System
- 設置 BigQuery 資料倉儲

### Phase 2: Memory

- 整合 Vector Database (Pinecone/Weaviate)
- 實作 Case Memory Service
- 建立 Example Pool 管理
- 實作相似案例檢索

### Phase 3: Evaluation

- 定義 Agent Performance Metrics
- 實作 Weekly Evaluation Job
- 建立 Dashboard 視覺化
- 設置 Alert 機制

### Phase 4: Adaptation

- 實作 Prompt A/B Testing
- 建立 Personalization Layer
- 實作 Strategy Pool
- 整合 Self-Improvement Pipeline

---

## 技術選型建議

| 元件 | 推薦 | 替代方案 |
|------|------|----------|
| Vector DB | Pinecone | Weaviate, Qdrant, pgvector |
| Data Warehouse | BigQuery | Snowflake, ClickHouse |
| Experiment Tracking | Custom + Firestore | MLflow, Weights & Biases |
| Job Scheduling | Cloud Scheduler | Airflow, Prefect |
| Embedding Model | text-embedding-004 | OpenAI embeddings |

---

## 關鍵成功指標

1. **Prediction Accuracy** > 75%
   - MEDDIC 分數與成交結果的相關性

2. **Suggestion Acceptance Rate** > 60%
   - 業務採納教練建議的比率

3. **Summary Edit Rate** < 20%
   - 摘要需要修改的比率

4. **Time to Value** < 4 週
   - 新模式被發現到應用的時間

5. **Model Improvement Rate** > 5% per quarter
   - 每季度準確度提升
