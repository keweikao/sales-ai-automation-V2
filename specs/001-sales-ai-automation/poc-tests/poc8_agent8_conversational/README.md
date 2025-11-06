# POC 8 – Agent 8 对话式交互验证

## Purpose

验证 Agent 8 对话式交互功能的核心能力，包括自然语言问题理解、数据查询准确性、回答质量，以及与现有 Slack App 的集成。这是实现业务主管随时查询团队数据的关键 POC。

## Questions To Answer

1. **问题理解准确性**：Agent 8 能否正确识别 6 大类问题类型并提取正确的查询参数？
2. **数据查询正确性**：根据解析的参数，能否从 Firestore 正确查询到相关案件和数据？
3. **回答质量**：生成的回答是否准确、有洞察力、可操作？
4. **对话连贯性**：能否维护对话历史并支持追问？
5. **集成可行性**：能否顺利集成到现有 slack-service 中？
6. **响应时间**：从接收问题到返回答案的端到端延迟是否可接受？

## Success Criteria

| Metric | Target | 说明 |
|--------|--------|------|
| 问题分类准确率 | ≥ 90% | 在 30 个测试问题中，正确识别问题类型 |
| 参数提取准确率 | ≥ 85% | 正确提取时间范围、人名、案件 ID 等关键参数 |
| 数据查询召回率 | ≥ 95% | 应该返回的案件都被正确查询到 |
| 回答相关性 | ≥ 4/5 | 人工评分：回答是否回答了问题 |
| 回答洞察力 | ≥ 3.5/5 | 人工评分：是否提供了有价值的洞察和建议 |
| 端到端响应时间 | ≤ 8s | 从接收 Slack 命令到返回答案（P95） |
| 对话追问准确率 | ≥ 80% | 带上下文的追问能正确理解 |

## Test Data

### 准备工作

1. **Firestore 测试数据**：
   - 准备 20-30 个模拟案件，包含完整的 Agent 1-6 分析结果
   - 涵盖不同业务（3-5 个虚拟业务名字）
   - 涵盖不同健康度（30-90 分范围）
   - 涵盖不同时间段（本日、本周、上周、上月）
   - 包含常见竞品（Eats365、Foodpanda POS、iCHEF 竞品）

2. **测试问题集**：
   - 创建 `test_questions.json` 包含 30 个测试问题
   - 涵盖 6 大类问题：
     - **团队整体表现**（5 题）：今天团队表现如何？本周完成几件案件？
     - **个人业务绩效**（5 题）：王小明本周表现如何？谁的健康度最低？
     - **案件详细分析**（5 题）：#202501-IC003 的情况？有哪些案件需要关注？
     - **竞品情报**（5 题）：Eats365 被提到几次？客户对竞品的评价？
     - **产品需求洞察**（5 题）：扫码点餐需求如何？最热门的功能是什么？
     - **趋势对比**（5 题）：本周 vs 上周健康度变化？团队成长趋势？

3. **对话追问场景**（10 组）：
   - 模拟真实对话流程，测试上下文理解

### 测试数据文件结构

```
poc8_agent8_conversational/
├── test_data/
│   ├── firestore_mock_cases.json       # 30 个模拟案件
│   ├── test_questions.json             # 30 个单轮问题 + 预期结果
│   ├── conversation_scenarios.json     # 10 组多轮对话场景
│   └── ground_truth.json               # 每个问题的正确答案（用于评分）
└── results/
    ├── question_parsing_results.json   # 问题解析结果
    ├── data_fetching_results.json      # 数据查询结果
    ├── answer_quality_scores.json      # 回答质量评分
    └── poc8_summary.json               # 汇总结果
```

## Steps Overview

### Phase 1: 问题理解测试（Question Understanding）

1. 实现 `question_parser.py` 模块
2. 对 30 个测试问题进行解析
3. 检查问题类型分类准确率
4. 检查参数提取准确率（时间、人名、案件 ID、关键词）
5. 记录解析结果到 `question_parsing_results.json`

### Phase 2: 数据查询测试（Data Fetching）

1. 实现 `data_fetcher.py` 模块
2. 使用 Phase 1 解析的参数查询 Firestore 测试数据
3. 验证查询结果的召回率和准确率
4. 测试边界情况（无数据、大量数据）
5. 记录查询性能（延迟、返回数量）

### Phase 3: 回答生成测试（Answer Generation）

1. 实现 `conversational_agent8.py` 模块
2. 使用 Gemini 2.0 Flash 生成回答
3. 人工评分回答质量（相关性、洞察力、可操作性）
4. 验证回答格式（是否符合预期结构）
5. 测试 Token 使用量和成本

### Phase 4: 对话流程测试（Conversation Flow）

1. 实现 `conversation_manager.py` 模块
2. 测试 10 组多轮对话场景
3. 验证上下文理解和追问准确率
4. 测试对话历史管理（存储、检索、清理）

### Phase 5: 集成测试（Integration）

1. 在 `slack-service` 中实现 `/ask-agent8` 命令处理器
2. 本地启动 slack-service 模拟环境
3. 使用 Slack API 测试工具发送命令
4. 验证端到端响应时间
5. 测试错误处理（权限检查、超时、API 失败）

### Phase 6: 性能与成本测试

1. 模拟 100 次查询，测量 P50、P95、P99 延迟
2. 计算平均 Token 使用量
3. 估算月成本（基于预期使用量）
4. 测试并发请求处理能力

## Required Setup

### 环境变量

```bash
# GCP 项目
export GCP_PROJECT_ID=sales-ai-automation-v2
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json

# Gemini API
export GEMINI_API_KEY=your-gemini-api-key

# Firestore
export FIRESTORE_DATABASE=(default)

# Slack（用于集成测试）
export SLACK_BOT_TOKEN=xoxb-test-token
export SLACK_SIGNING_SECRET=test-signing-secret
```

### 依赖安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# requirements.txt 应包含:
# - google-cloud-firestore
# - google-generativeai
# - slack-bolt
# - pytest
# - pytest-asyncio
```

### Firestore 测试数据初始化

```bash
# 加载测试数据到 Firestore
python scripts/load_test_data.py \
  --input test_data/firestore_mock_cases.json \
  --collection test_opportunities \
  --project $GCP_PROJECT_ID
```

## Deliverables

### 代码模块

1. **`src/agents/question_parser.py`** - 问题解析模块
   - `parse_question(question: str) -> QuestionParams`
   - 识别问题类型、提取参数

2. **`src/agents/data_fetcher.py`** - 数据查询模块
   - `fetch_relevant_data(params: QuestionParams) -> QueryResult`
   - 从 Firestore 查询相关案件

3. **`src/agents/conversational_agent8.py`** - Agent 8 核心
   - `generate_answer(question, history, data) -> str`
   - 调用 Gemini 生成回答

4. **`src/agents/conversation_manager.py`** - 对话历史管理
   - `save_conversation(user_id, message, response)`
   - `get_conversation_history(user_id, limit=5)`

5. **`src/commands/ask_agent8_handler.py`** - Slack 命令处理器
   - 注册 `/ask-agent8` 命令
   - 权限检查、调用 Agent 8、返回结果

### 测试脚本

1. **`test_question_parsing.py`** - 测试问题解析
2. **`test_data_fetching.py`** - 测试数据查询
3. **`test_answer_generation.py`** - 测试回答生成
4. **`test_conversation_flow.py`** - 测试对话流程
5. **`test_integration.py`** - 端到端集成测试
6. **`test_performance.py`** - 性能和成本测试

### 数据文件

1. **`test_data/firestore_mock_cases.json`** - 30 个模拟案件
2. **`test_data/test_questions.json`** - 30 个测试问题
3. **`test_data/conversation_scenarios.json`** - 10 组对话场景
4. **`test_data/ground_truth.json`** - 预期答案（用于评分）

### 结果文档

1. **`results/poc8_summary.json`** - POC 汇总结果

   ```json
   {
     "questionUnderstanding": {
       "classificationAccuracy": 0.93,
       "parameterExtractionAccuracy": 0.87,
       "testCases": 30
     },
     "dataFetching": {
       "recallRate": 0.97,
       "precisionRate": 0.92,
       "avgQueryTimeMs": 245
     },
     "answerQuality": {
       "relevanceScore": 4.2,
       "insightScore": 3.8,
       "actionabilityScore": 3.9
     },
     "conversationFlow": {
       "contextAccuracy": 0.85,
       "followUpSuccessRate": 0.82
     },
     "performance": {
       "p50LatencyMs": 4200,
       "p95LatencyMs": 7800,
       "p99LatencyMs": 9500,
       "avgTokensPerQuery": 2100,
       "estimatedMonthlyCost": 0.62
     }
   }
   ```

2. **`POC8_REPORT.md`** - 完整测试报告
   - 测试方法说明
   - 详细结果分析
   - 发现的问题和限制
   - Go/No-Go 建议

## How to Run the POC

### 快速开始（完整流程）

```bash
# 1. 设置环境
cd specs/001-sales-ai-automation/poc-tests/poc8_agent8_conversational
source venv/bin/activate
export $(cat .env | xargs)  # 加载环境变量

# 2. 初始化测试数据
python scripts/load_test_data.py

# 3. 运行所有测试
pytest tests/ -v --tb=short

# 4. 生成汇总报告
python scripts/generate_poc8_report.py
```

### 分阶段运行

```bash
# Phase 1: 测试问题解析
pytest tests/test_question_parsing.py -v

# Phase 2: 测试数据查询
pytest tests/test_data_fetching.py -v

# Phase 3: 测试回答生成
pytest tests/test_answer_generation.py -v

# Phase 4: 测试对话流程
pytest tests/test_conversation_flow.py -v

# Phase 5: 集成测试
pytest tests/test_integration.py -v

# Phase 6: 性能测试
pytest tests/test_performance.py -v --benchmark
```

### 单独测试特定功能

```bash
# 测试单个问题解析
python -m src.agents.question_parser --question "今天团队表现如何？"

# 测试单个数据查询
python -m src.agents.data_fetcher --params '{"type":"team_overview","timeRange":"today"}'

# 测试单个回答生成
python -m src.agents.conversational_agent8 \
  --question "王小明本周表现如何？" \
  --data test_data/sample_response.json
```

## 执行检查清单

完成测试后，请确认：

- [ ] `results/poc8_summary.json` 包含所有指标，且达到成功标准
- [ ] 问题分类准确率 ≥ 90%
- [ ] 参数提取准确率 ≥ 85%
- [ ] 数据查询召回率 ≥ 95%
- [ ] 回答相关性 ≥ 4/5
- [ ] 回答洞察力 ≥ 3.5/5
- [ ] P95 响应时间 ≤ 8s
- [ ] 对话追问准确率 ≥ 80%
- [ ] 月成本估算 < $1.00（基于 Gemini Flash 定价）
- [ ] 集成测试通过，Slack 命令能正常工作
- [ ] 错误处理测试通过（无权限、超时、API 失败等）
- [ ] 性能测试通过，能处理并发请求
- [ ] `POC8_REPORT.md` 文档完整，包含 Go/No-Go 建议

## Go/No-Go Decision Criteria

### ✅ GO 条件（所有条件必须满足）

1. **核心功能**：
   - 问题分类准确率 ≥ 90%
   - 数据查询召回率 ≥ 95%
   - 回答相关性 ≥ 4/5

2. **用户体验**：
   - P95 响应时间 ≤ 8s
   - 对话追问准确率 ≥ 80%

3. **成本可控**：
   - 估算月成本 < $2.00（基于合理使用量）

4. **技术可行**：
   - 集成测试通过
   - 无阻塞性技术问题

### ⚠️ GO WITH CAUTION（部分条件不满足，但可接受）

- 回答洞察力 3.0-3.5/5（可通过优化 Prompt 改进）
- P95 响应时间 8-10s（可通过缓存优化）
- 对话追问准确率 70-80%（可在 MVP 中接受，后续改进）

### ❌ NO-GO（任一条件触发）

- 问题分类准确率 < 80%（核心功能不可用）
- 数据查询召回率 < 85%（数据不准确）
- 回答相关性 < 3/5（用户体验差）
- P95 响应时间 > 12s（用户体验差）
- 估算月成本 > $5.00（成本过高）
- 集成测试失败且无法解决

## Extensions (Later Phases)

### Phase 2 功能扩展

1. **更多问题类型**：
   - 案件预测（"下周可能成交的案件"）
   - 业务对比（"王小明 vs 李大华"）
   - 异常检测（"有哪些异常案件"）

2. **高级交互**：
   - 支持 Slack 交互式按钮（"查看详情"、"导出报表"）
   - 支持图表生成（健康度趋势图、业务排名图）
   - 支持数据导出（CSV、PDF 报告）

3. **智能推荐**：
   - 主动推送风险案件提醒
   - 智能建议下一步行动
   - 学习主管偏好，个性化回答

4. **多语言支持**：
   - 支持英文、简体中文、繁体中文
   - 自动检测语言并回答

5. **性能优化**：
   - 实现查询缓存（Redis）
   - 预计算常见查询
   - 使用 Gemini Flash Thinking 提升推理能力

## Timeline Estimate

- **Phase 1-2**（问题理解 + 数据查询）：2 天
- **Phase 3**（回答生成）：1 天
- **Phase 4**（对话流程）：1 天
- **Phase 5**（集成测试）：1 天
- **Phase 6**（性能测试）：0.5 天
- **文档和报告**：0.5 天

**总计**：6 天

## Notes

- 本 POC 专注于**对话式交互**功能，不包括定时报告功能（定时报告将在后续 Phase 实现）
- 测试数据应覆盖真实业务场景，包括边界情况（无数据、大量数据、模糊问题）
- 回答质量评分需要人工评审，建议邀请 1-2 位业务主管参与评分
- 集成测试可以先在本地环境验证，不必立即部署到 Cloud Run
- 如果 Gemini Flash 效果不佳，可以尝试 Gemini Pro（成本会增加）
