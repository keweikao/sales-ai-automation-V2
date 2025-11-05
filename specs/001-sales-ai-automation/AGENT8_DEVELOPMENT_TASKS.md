# Agent 8 开发任务清单

**项目**：Agent 8 对话式交互 + 定时报告
**最后更新**：2025-11-04

---

## 📋 任务概览

本文档列出 Agent 8 从 POC 验证到完整实现的所有开发任务，分为以下阶段：

1. **Phase 0**: POC 验证（6 天）
2. **Phase 1**: 对话式交互 MVP（8-10 天）- **优先级：高**
3. **Phase 2**: 定时报告功能（2-3 天）- **优先级：中**
4. **Phase 3**: 优化和扩展（持续）

---

## 🎯 Phase 0: POC 验证（6 天）

**目标**：验证 Agent 8 的核心技术可行性，确保 Go/No-Go 决策有依据。

### 0.1 准备工作（0.5 天）

- [ ] **0.1.1** 创建 POC 8 测试目录结构
  - `poc8_agent8_conversational/`
  - `test_data/`
  - `scripts/`
  - `tests/`
  - `results/`

- [ ] **0.1.2** 创建虚拟环境并安装依赖
  - `requirements.txt`：google-cloud-firestore, google-generativeai, slack-bolt, pytest

- [ ] **0.1.3** 配置 GCP 和 Gemini 凭证
  - Service Account JSON
  - Gemini API Key
  - Firestore 测试数据库

### 0.2 测试数据准备（1 天）

- [ ] **0.2.1** 创建 30 个模拟案件数据
  - 完整的 Agent 1-6 分析结果
  - 涵盖 3-5 个虚拟业务名字
  - 不同健康度范围（30-90）
  - 不同时间段（本日、本周、上周、上月）
  - 文件：`test_data/firestore_mock_cases.json`

- [ ] **0.2.2** 创建 30 个测试问题
  - 团队整体表现（5 题）
  - 个人业务绩效（5 题）
  - 案件详细分析（5 题）
  - 竞品情报（5 题）
  - 产品需求洞察（5 题）
  - 趋势对比（5 题）
  - 文件：`test_data/test_questions.json`

- [ ] **0.2.3** 创建 10 组对话场景
  - 多轮对话，测试上下文理解
  - 文件：`test_data/conversation_scenarios.json`

- [ ] **0.2.4** 创建预期答案（Ground Truth）
  - 用于自动评分和人工对比
  - 文件：`test_data/ground_truth.json`

- [ ] **0.2.5** 将测试数据加载到 Firestore
  - 创建 `test_opportunities` collection
  - 脚本：`scripts/load_test_data.py`

### 0.3 Phase 1: 问题理解测试（2 天）

- [ ] **0.3.1** 实现问题解析模块
  - 文件：`src/agents/question_parser.py`
  - 功能：
    - `parse_question(question: str) -> QuestionParams`
    - 使用 Gemini 或规则识别问题类型
    - 提取时间范围、人名、案件 ID、关键词等参数

- [ ] **0.3.2** 创建问题类型定义
  - `QuestionType` enum（6 种类型）
  - `QuestionParams` dataclass

- [ ] **0.3.3** 实现测试脚本
  - 文件：`tests/test_question_parsing.py`
  - 测试 30 个问题的解析准确率

- [ ] **0.3.4** 运行测试并记录结果
  - 计算分类准确率
  - 计算参数提取准确率
  - 保存到 `results/question_parsing_results.json`

- [ ] **0.3.5** 分析失败案例，优化 Prompt
  - 如果准确率 < 90%，调整解析逻辑

### 0.4 Phase 2: 数据查询测试（1 天）

- [ ] **0.4.1** 实现数据查询模块
  - 文件：`src/agents/data_fetcher.py`
  - 功能：
    - `fetch_relevant_data(params: QuestionParams) -> QueryResult`
    - 从 Firestore 查询相关案件
    - 支持时间范围、业务筛选、健康度筛选

- [ ] **0.4.2** 实现查询逻辑
  - 团队整体查询（按时间聚合）
  - 个人业务查询（按 salesRepId）
  - 案件详细查询（按 caseId）
  - 竞品查询（遍历 agent4Competitors）
  - 产品需求查询（遍历 agent5Questionnaires）

- [ ] **0.4.3** 创建测试脚本
  - 文件：`tests/test_data_fetching.py`
  - 验证查询召回率和准确率

- [ ] **0.4.4** 运行测试并记录结果
  - 计算召回率、准确率
  - 测量查询延迟
  - 保存到 `results/data_fetching_results.json`

### 0.5 Phase 3: 回答生成测试（1 天）

- [ ] **0.5.1** 设计 Agent 8 Prompt
  - 基于 `agent8-manager-prompt.md`
  - 适配对话式交互场景
  - 支持 6 种问题类型

- [ ] **0.5.2** 实现 Agent 8 模块
  - 文件：`src/agents/conversational_agent8.py`
  - 功能：
    - `generate_answer(question, history, data) -> str`
    - 调用 Gemini 2.0 Flash
    - 返回结构化回答

- [ ] **0.5.3** 创建测试脚本
  - 文件：`tests/test_answer_generation.py`
  - 生成 30 个问题的回答

- [ ] **0.5.4** 人工评分回答质量
  - 相关性（1-5 分）
  - 洞察力（1-5 分）
  - 可操作性（1-5 分）
  - 保存到 `results/answer_quality_scores.json`

- [ ] **0.5.5** 计算 Token 使用和成本
  - 平均每次查询的 Token 数
  - 估算月成本

### 0.6 Phase 4: 对话流程测试（1 天）

- [ ] **0.6.1** 实现对话历史管理
  - 文件：`src/agents/conversation_manager.py`
  - 功能：
    - `save_conversation(user_id, message, response)`
    - `get_conversation_history(user_id, limit=5)`
    - 使用 Firestore 存储

- [ ] **0.6.2** 创建对话测试脚本
  - 文件：`tests/test_conversation_flow.py`
  - 测试 10 组多轮对话

- [ ] **0.6.3** 运行测试并评估
  - 追问准确率
  - 上下文理解能力

### 0.7 Phase 5: 集成测试（1 天）

- [ ] **0.7.1** 实现 Slack 命令处理器
  - 文件：`src/commands/ask_agent8_handler.py`
  - 功能：
    - 注册 `/ask-agent8` 命令
    - 权限检查（是否为主管）
    - 调用 Agent 8 并返回结果

- [ ] **0.7.2** 本地启动 slack-service
  - 使用 ngrok 或类似工具暴露本地端点
  - 配置 Slack App

- [ ] **0.7.3** 端到端测试
  - 在 Slack 中发送 `/ask-agent8` 命令
  - 验证响应时间和结果

- [ ] **0.7.4** 错误处理测试
  - 无权限用户
  - 超时情况
  - Gemini API 失败
  - Firestore 查询失败

### 0.8 Phase 6: 性能测试（0.5 天）

- [ ] **0.8.1** 创建性能测试脚本
  - 文件：`tests/test_performance.py`
  - 模拟 100 次查询

- [ ] **0.8.2** 测量延迟分布
  - P50、P95、P99 响应时间

- [ ] **0.8.3** 测试并发能力
  - 5 个并发请求

- [ ] **0.8.4** 成本估算
  - 基于实际 Token 使用量

### 0.9 总结和报告（0.5 天）

- [ ] **0.9.1** 生成 POC 汇总结果
  - 脚本：`scripts/generate_poc8_report.py`
  - 输出：`results/poc8_summary.json`

- [ ] **0.9.2** 编写完整测试报告
  - 文档：`POC8_REPORT.md`
  - 包含：测试方法、结果分析、问题和限制、Go/No-Go 建议

- [ ] **0.9.3** Go/No-Go 决策会议
  - 与团队讨论结果
  - 决定是否进入 Phase 1 开发

---

## 🚀 Phase 1: 对话式交互 MVP（8-10 天）

**前提**：POC 8 通过，决定 GO。

**目标**：实现可用的对话式 Agent 8，集成到现有 slack-service，部署到生产环境。

### 1.1 代码重构和整合（2 天）

- [ ] **1.1.1** 将 POC 代码迁移到 slack-service
  - 从 `poc8_agent8_conversational/src/` 迁移到 `src/slack_app/agents/`
  - 调整导入路径和配置

- [ ] **1.1.2** 创建正式的目录结构
  ```
  src/slack_app/
  ├── agents/
  │   ├── __init__.py
  │   ├── question_parser.py
  │   ├── data_fetcher.py
  │   ├── conversational_agent8.py
  │   └── conversation_manager.py
  ├── commands/
  │   ├── __init__.py
  │   └── ask_agent8_handler.py
  └── main.py
  ```

- [ ] **1.1.3** 更新 `main.py` 注册 Agent 8 命令
  ```python
  from commands.ask_agent8_handler import register_ask_agent8_handler
  register_ask_agent8_handler(app)
  ```

- [ ] **1.1.4** 配置环境变量
  - 在 Cloud Run 中添加 `GEMINI_API_KEY`
  - 配置 Firestore 连接

- [ ] **1.1.5** 更新 `requirements.txt`
  - 添加 `google-generativeai`

### 1.2 权限管理（1 天）

- [ ] **1.2.1** 设计主管权限管理方案
  - 选择方案：Firestore 存储（推荐）或硬编码

- [ ] **1.2.2** 创建权限检查模块
  - 文件：`src/slack_app/auth/manager_auth.py`
  - 功能：
    - `is_manager(user_id: str) -> bool`
    - 从 Firestore `users` collection 读取 `role` 字段

- [ ] **1.2.3** 在 Firestore 中创建主管列表
  - Collection: `users`
  - Document: `{slack_user_id}`
  - Fields: `role: "manager"`, `name`, `email`

- [ ] **1.2.4** 在命令处理器中添加权限检查
  - 未授权用户返回友好提示

### 1.3 Prompt 优化（2 天）

- [ ] **1.3.1** 基于 POC 结果优化问题解析 Prompt
  - 提高分类准确率
  - 改进参数提取

- [ ] **1.3.2** 优化 Agent 8 回答生成 Prompt
  - 提升洞察力和可操作性
  - 调整回答风格（专业、简洁、友好）

- [ ] **1.3.3** 创建 Prompt 版本管理
  - 文件：`src/slack_app/prompts/`
  - `question_parser_v1.txt`
  - `agent8_conversational_v1.txt`

- [ ] **1.3.4** A/B 测试不同 Prompt 版本
  - 使用真实主管反馈优化

### 1.4 用户体验优化（1 天）

- [ ] **1.4.1** 添加"正在思考"消息
  - 接收命令后立即发送临时消息
  - 避免用户以为命令没有响应

- [ ] **1.4.2** 格式化 Slack 回答
  - 使用 Slack Block Kit 美化回答
  - 添加 emoji、分隔线、代码块

- [ ] **1.4.3** 添加快速操作按钮
  - "查看详情"：深入某个案件
  - "导出数据"：生成 CSV（Phase 3 功能）
  - "追问"：预设追问问题

- [ ] **1.4.4** 错误处理和友好提示
  - 查询无结果时的提示
  - API 超时时的重试提示
  - 问题不清晰时的澄清请求

### 1.5 测试（2 天）

- [ ] **1.5.1** 单元测试
  - 测试所有模块的核心功能
  - 使用 pytest，覆盖率 > 80%

- [ ] **1.5.2** 集成测试
  - 在 dev 环境完整测试
  - 模拟真实 Slack 交互

- [ ] **1.5.3** 用户验收测试（UAT）
  - 邀请 1-2 位业务主管试用
  - 收集反馈并快速迭代

- [ ] **1.5.4** 性能测试
  - 在 dev 环境测试响应时间
  - 确保 P95 < 8s

### 1.6 部署（1 天）

- [ ] **1.6.1** 在 Slack App 配置中添加 `/ask-agent8` 命令
  - Command: `/ask-agent8`
  - Request URL: `https://slack-service-xyz.run.app/slack/events`
  - Description: "询问团队数据和业务分析"
  - Usage Hint: "今天团队表现如何？"

- [ ] **1.6.2** 部署 slack-service 到 Cloud Run
  - 更新 Docker 镜像
  - 部署到 dev 环境
  - 测试通过后部署到 production

- [ ] **1.6.3** 配置主管权限
  - 在 Firestore 中添加主管用户

- [ ] **1.6.4** 监控和日志
  - 配置 Cloud Logging
  - 设置错误告警（Slack 通知）

### 1.7 文档（1 天）

- [ ] **1.7.1** 编写用户使用指南
  - 文档：`docs/AGENT8_USER_GUIDE.md`
  - 如何使用 `/ask-agent8`
  - 支持的问题类型和示例
  - 常见问题解答

- [ ] **1.7.2** 编写开发者文档
  - 文档：`docs/AGENT8_DEVELOPER_GUIDE.md`
  - 架构设计
  - 代码结构
  - 如何扩展功能

- [ ] **1.7.3** 更新 README
  - 在项目 README 中添加 Agent 8 说明

---

## 📊 Phase 2: 定时报告功能（2-3 天）

**优先级**：中（可在 Phase 1 稳定后再实施）

**目标**：每天/每周自动生成团队报告，发送到 Slack。

### 2.1 Cloud Function 开发（1 天）

- [ ] **2.1.1** 创建 Cloud Function 目录结构
  ```
  src/agent8_scheduled_report/
  ├── main.py
  ├── requirements.txt
  ├── report_generator.py
  └── slack_sender.py
  ```

- [ ] **2.1.2** 实现数据聚合逻辑
  - 文件：`report_generator.py`
  - 功能：
    - 查询 Firestore 获取指定时间范围的案件
    - 聚合团队数据
    - 调用 Agent 8（使用 `agent8-manager-prompt.md`）

- [ ] **2.1.3** 实现报告格式化
  - 将 Agent 8 输出转换为 Slack 消息
  - 使用 Block Kit 美化

- [ ] **2.1.4** 实现 Slack 发送
  - 文件：`slack_sender.py`
  - 使用 Slack Web API 发送消息到指定频道

- [ ] **2.1.5** 实现 Cloud Function 入口
  - 文件：`main.py`
  - HTTP 触发器或 Pub/Sub 触发器

### 2.2 Cloud Scheduler 配置（0.5 天）

- [ ] **2.2.1** 创建每日报告 Scheduler
  - 名称：`agent8-daily-report`
  - 时间：每天 09:00（台北时间）
  - Cron: `0 9 * * *`
  - Target: Cloud Function HTTP 端点

- [ ] **2.2.2** 创建周报 Scheduler
  - 名称：`agent8-weekly-report`
  - 时间：每周一 09:00
  - Cron: `0 9 * * 1`

- [ ] **2.2.3** 配置时区
  - 设置为 `Asia/Taipei`

### 2.3 测试和部署（0.5 天）

- [ ] **2.3.1** 本地测试
  - 使用 Functions Framework 本地运行
  - 验证报告生成逻辑

- [ ] **2.3.2** 手动触发测试
  - 使用 `gcloud scheduler jobs run` 手动触发
  - 检查 Slack 消息

- [ ] **2.3.3** 部署 Cloud Function
  - `gcloud functions deploy agent8-scheduled-report`
  - 配置环境变量

- [ ] **2.3.4** 验证 Scheduler
  - 等待下一次自动触发
  - 检查日志和 Slack 消息

### 2.4 配置和文档（0.5 天）

- [ ] **2.4.1** 配置报告接收者
  - 在 Firestore 中存储主管 Slack Channel ID
  - 或使用固定频道（如 `#sales-reports`）

- [ ] **2.4.2** 编写部署文档
  - 文档：`docs/AGENT8_SCHEDULED_REPORT_DEPLOYMENT.md`
  - 如何修改报告频率
  - 如何调整报告内容

---

## 🎨 Phase 3: 优化和扩展（持续）

**优先级**：低（在 MVP 稳定后逐步实施）

### 3.1 功能扩展

- [ ] **3.1.1** 支持更多问题类型
  - 案件预测："下周可能成交的案件"
  - 业务对比："王小明 vs 李大华"
  - 异常检测："有哪些异常案件"

- [ ] **3.1.2** 支持图表生成
  - 健康度趋势图
  - 业务排名图
  - 使用 Matplotlib 或 Plotly

- [ ] **3.1.3** 支持数据导出
  - CSV 导出
  - PDF 报告生成

- [ ] **3.1.4** 智能推荐
  - 主动推送风险案件提醒
  - 智能建议下一步行动

### 3.2 性能优化

- [ ] **3.2.1** 实现查询缓存
  - 使用 Redis 缓存常见查询
  - 设置 TTL（如 5 分钟）

- [ ] **3.2.2** 预计算常见查询
  - 每小时计算团队整体数据
  - 存储到 Firestore 或 Redis

- [ ] **3.2.3** 优化 Firestore 查询
  - 添加索引
  - 减少字段读取

### 3.3 用户体验优化

- [ ] **3.3.1** 多语言支持
  - 支持英文、简体中文、繁体中文
  - 自动检测语言

- [ ] **3.3.2** 个性化回答
  - 学习主管偏好
  - 调整回答风格

- [ ] **3.3.3** 交互式按钮
  - Slack Block Kit 按钮
  - 支持深度下钻

### 3.4 监控和分析

- [ ] **3.4.1** 使用统计
  - 记录每次查询的类型、用户、时间
  - 分析最常见的问题

- [ ] **3.4.2** 质量监控
  - 收集用户反馈（👍 / 👎）
  - 持续优化 Prompt

- [ ] **3.4.3** 成本监控
  - 监控 Gemini API 使用量
  - 设置预算告警

---

## 📊 里程碑和时间线

| 阶段 | 任务 | 预计时间 | 依赖 |
|------|------|---------|------|
| **Phase 0** | POC 验证 | 6 天 | - |
| **Go/No-Go 决策** | 评估 POC 结果 | 0.5 天 | Phase 0 |
| **Phase 1** | 对话式交互 MVP | 8-10 天 | Phase 0 通过 |
| **Phase 2** | 定时报告功能 | 2-3 天 | Phase 1 完成（可选） |
| **Phase 3** | 优化和扩展 | 持续 | Phase 1 完成 |

**总计**（不含 Phase 3）：**16-19.5 天**

如果 2 人并行工作（1 人 POC，1 人准备基础设施）：**约 12-14 天**

---

## ✅ 交付检查清单

### Phase 0 交付物

- [ ] `poc8_agent8_conversational/` 完整目录
- [ ] `POC8_REPORT.md` 测试报告
- [ ] `results/poc8_summary.json` 汇总结果
- [ ] Go/No-Go 决策文档

### Phase 1 交付物

- [ ] `src/slack_app/agents/` 所有模块
- [ ] `src/slack_app/commands/ask_agent8_handler.py`
- [ ] 单元测试和集成测试（覆盖率 > 80%）
- [ ] `docs/AGENT8_USER_GUIDE.md`
- [ ] `docs/AGENT8_DEVELOPER_GUIDE.md`
- [ ] Slack App 配置完成
- [ ] 部署到 production 并验证

### Phase 2 交付物

- [ ] `src/agent8_scheduled_report/` Cloud Function
- [ ] Cloud Scheduler 配置完成
- [ ] 测试报告（每日 + 周报）
- [ ] `docs/AGENT8_SCHEDULED_REPORT_DEPLOYMENT.md`

---

## 🚨 风险和注意事项

### 技术风险

1. **Gemini API 稳定性**：
   - **风险**：Gemini API 可能有延迟或失败
   - **缓解**：实现重试机制，设置超时，考虑降级到简单规则

2. **Firestore 查询性能**：
   - **风险**：复杂查询可能超时
   - **缓解**：添加索引，实现缓存，优化查询逻辑

3. **Slack 消息长度限制**：
   - **风险**：回答过长可能被截断
   - **缓解**：分段发送，提供"查看更多"按钮

### 产品风险

1. **用户期望过高**：
   - **风险**：主管期望 Agent 8 能回答所有问题
   - **缓解**：在用户指南中明确说明支持的问题类型

2. **数据质量问题**：
   - **风险**：如果 Agent 1-6 数据不准确，Agent 8 回答也会有问题
   - **缓解**：先确保 Agent 1-6 质量，Agent 8 只是汇总和洞察

3. **隐私和权限**：
   - **风险**：主管可能查询到不应看到的数据
   - **缓解**：严格权限检查，记录所有查询日志

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| `AGENT8_SUMMARY.md` | Agent 8 完整方案总结 |
| `AGENT8_CONVERSATIONAL.md` | 对话式 Agent 8 设计 |
| `agent8-implementation.md` | 定时报告实施计划 |
| `agent8-manager-prompt.md` | Agent 8 的 Gemini Prompt |
| `AGENT_DATA_FOR_MANAGERS.md` | Agent 1-6 数据说明 |
| `poc-tests/poc8_agent8_conversational/README.md` | POC 8 测试计划 |

---

**下一步**：开始 Phase 0 POC 验证！🚀
