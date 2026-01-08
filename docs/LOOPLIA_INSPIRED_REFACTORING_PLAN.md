# Sales AI V2 架構重構計劃

## 參考 Looplia Core 設計模式

> 本計劃將由三個 AI Agent 並行開發，分別負責三個 Phase

---

## 概覽

| Phase | Agent | 任務 | 預估時間 | 依賴 |
|-------|-------|------|---------|------|
| Phase 1 | Agent A | Markdown Workflow 定義 | 2-3 週 | 無 |
| Phase 2 | Agent B | Skills Registry 系統 | 3-4 週 | 無 (可並行) |
| Phase 3 | Agent C | Plugin 架構分離 | 4-6 週 | Phase 1 + 2 完成後 |

```text
時間軸：
Week 1-3:  [====Agent A====] [====Agent B====]  (並行開發)
Week 4-7:  [====Agent B====]                    (Agent B 繼續)
Week 8-12:                   [======Agent C======] (依賴前兩者)
```

---

## Agent A: Phase 1 - Markdown Workflow 定義

### 任務概述

將現有 `orchestrator.py` 中寫死的流程邏輯抽取為 Markdown + YAML 格式的宣告式工作流定義。

### 目標

- 非工程師（銷售主管）可以閱讀和理解工作流
- 工作流變更不需要修改 Python 程式碼
- 版本控制友善，PR review 更容易

### 關鍵輸入檔案

```text
modules/03-sales-conversation/
├── transcript_analyzer/
│   └── orchestrator.py              # 820+ 行，核心流程邏輯
├── meddic/agents/
│   ├── base.py                      # Agent 基類
│   ├── context_agent.py             # Agent 1
│   ├── buyer_agent.py               # Agent 2
│   ├── seller_agent.py              # Agent 3
│   ├── summary_agent.py             # Agent 4
│   ├── coach_agent.py               # Agent 5
│   └── crm_agent.py                 # Agent 6
└── config.yaml                       # 現有配置
```

### 預期輸出

#### 1. 新增目錄結構

```text
modules/03-sales-conversation/
├── workflows/                        # 新增
│   ├── meddic-analysis.md           # 主要工作流定義
│   ├── quick-analysis.md            # 簡化版工作流
│   └── schemas/
│       └── workflow-schema.json     # 工作流 JSON Schema
├── transcript_analyzer/
│   ├── orchestrator.py              # 重構：讀取 workflow 定義
│   └── workflow_loader.py           # 新增：解析 workflow 檔案
```

#### 2. Workflow 定義格式 (meddic-analysis.md)

```markdown
---
# 工作流元數據
name: MEDDIC 銷售對話分析
version: 2.0.0
description: 使用 6 個 AI Agent 分析銷售對話，產出 MEDDIC 評估和教練建議

# 輸入定義
inputs:
  transcript:
    type: array
    description: 對話逐字稿片段
    required: true
  demo_meta:
    type: object
    description: Demo 會議元數據
    required: false

# 輸出定義
outputs:
  context_data:
    from: context-agent
    description: 會議背景分析
  buyer_data:
    from: buyer-agent
    description: 客戶洞察 (MEDDIC)
  seller_data:
    from: seller-agent
    description: 銷售教練建議
  summary_data:
    from: summary-agent
    description: 客戶摘要

# 執行階段定義
phases:
  - name: base-analysis
    description: 基礎分析（平行執行）
    parallel: true
    steps:
      - agent: context-agent
        inputs:
          transcript: $inputs.transcript
          demo_meta: $inputs.demo_meta
      - agent: buyer-agent
        inputs:
          transcript: $inputs.transcript

  - name: quality-loop
    description: 品質檢查與修正
    type: refinement
    target: buyer-agent
    max_iterations: 2
    condition: quality_check_failed

  - name: competitor-detection
    description: 競爭對手分析
    condition: competitors_detected
    steps:
      - agent: competitor-agent
        inputs:
          transcript: $inputs.transcript
          buyer_data: $phases.base-analysis.buyer-agent.output

  - name: synthesis
    description: 綜合分析
    steps:
      - agent: seller-agent
        inputs:
          transcript: $inputs.transcript
          context_data: $phases.base-analysis.context-agent.output
          buyer_data: $phases.base-analysis.buyer-agent.output

  - name: summary
    description: 產出摘要
    steps:
      - agent: summary-agent
        inputs:
          transcript: $inputs.transcript
          context_data: $phases.base-analysis.context-agent.output

  - name: crm-extraction
    description: CRM 欄位擷取
    steps:
      - agent: crm-agent
        inputs:
          transcript: $inputs.transcript
          context_data: $phases.base-analysis.context-agent.output
          buyer_data: $phases.base-analysis.buyer-agent.output
          seller_data: $phases.synthesis.seller-agent.output

  - name: coaching
    description: 教練評估
    steps:
      - agent: coach-agent
        inputs:
          context_data: $phases.base-analysis.context-agent.output
          buyer_data: $phases.base-analysis.buyer-agent.output
          seller_data: $phases.synthesis.seller-agent.output

# 品質規則
quality_rules:
  buyer-agent:
    - rule: identified_needs_count >= 2
      message: "識別到的需求太少，請更仔細分析"
    - rule: psychology.hesitations.length > 0
      message: "未識別到客戶疑慮"
    - rule: meddic.pain.length >= 10
      message: "MEDDIC 痛點描述過於簡短"

# 條件定義
conditions:
  competitors_detected:
    type: keyword_match
    keywords:
      - 競爭對手
      - 對手
      - 其他廠商
      - 別家
---

## 工作流說明

此工作流程實作 MEDDIC 銷售方法論，透過 6 個專門化 AI Agent 分析銷售對話：

### Agent 說明

1. **Context Agent** - 分析會議背景、參與者、時間軸
2. **Buyer Agent** - 深入分析客戶需求、痛點、MEDDIC 指標
3. **Seller Agent** - 提供銷售教練建議、話術優化
4. **Summary Agent** - 產出客戶導向的會議摘要
5. **Coach Agent** - 評估銷售表現、觸發警示
6. **CRM Agent** - 擷取 Salesforce 所需欄位

### 執行流程

Phase 1: [Context] + [Buyer] 平行執行
Phase 2: [Buyer] 品質檢查 (最多 2 次修正)
Phase 3: [Competitor] 條件執行 (若偵測到競爭對手)
Phase 4: [Seller] 綜合分析
Phase 5: [Summary] 產出摘要
Phase 6: [CRM] 欄位擷取
Phase 7: [Coach] 教練評估
```

#### 3. Workflow Loader (workflow_loader.py)

```python
"""
Workflow Loader - 解析 Markdown 工作流定義

Usage:
    loader = WorkflowLoader()
    workflow = loader.load("workflows/meddic-analysis.md")
    phases = workflow.phases
"""

from __future__ import annotations

import re
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowStep:
    """單一執行步驟"""
    agent: str
    inputs: Dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowPhase:
    """執行階段"""
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    parallel: bool = False
    condition: Optional[str] = None
    type: str = "sequential"  # sequential, refinement
    max_iterations: int = 1
    target: Optional[str] = None


@dataclass
class QualityRule:
    """品質檢查規則"""
    rule: str
    message: str


@dataclass
class Workflow:
    """工作流定義"""
    name: str
    version: str
    description: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    phases: List[WorkflowPhase]
    quality_rules: Dict[str, List[QualityRule]]
    conditions: Dict[str, Any]
    raw_yaml: Dict[str, Any]


class WorkflowLoader:
    """載入並解析 Markdown 工作流定義"""

    def load(self, path: str | Path) -> Workflow:
        """從 Markdown 檔案載入工作流"""
        content = Path(path).read_text(encoding="utf-8")
        yaml_content = self._extract_frontmatter(content)
        return self._parse_workflow(yaml_content)

    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """提取 YAML frontmatter"""
        pattern = r'^---\s*\n(.*?)\n---'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            raise ValueError("No YAML frontmatter found")
        return yaml.safe_load(match.group(1))

    def _parse_workflow(self, data: Dict[str, Any]) -> Workflow:
        """解析工作流資料結構"""
        phases = []
        for phase_data in data.get("phases", []):
            steps = [
                WorkflowStep(
                    agent=step["agent"],
                    inputs=step.get("inputs", {})
                )
                for step in phase_data.get("steps", [])
            ]
            phases.append(WorkflowPhase(
                name=phase_data["name"],
                description=phase_data.get("description", ""),
                steps=steps,
                parallel=phase_data.get("parallel", False),
                condition=phase_data.get("condition"),
                type=phase_data.get("type", "sequential"),
                max_iterations=phase_data.get("max_iterations", 1),
                target=phase_data.get("target"),
            ))

        quality_rules = {}
        for agent, rules in data.get("quality_rules", {}).items():
            quality_rules[agent] = [
                QualityRule(rule=r["rule"], message=r["message"])
                for r in rules
            ]

        return Workflow(
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            phases=phases,
            quality_rules=quality_rules,
            conditions=data.get("conditions", {}),
            raw_yaml=data,
        )
```

### 實施步驟

#### Step 1: 建立 Workflow Schema (Day 1-2)

- [ ] 設計 workflow YAML schema
- [ ] 建立 JSON Schema 驗證檔
- [ ] 撰寫 schema 文件

#### Step 2: 建立 Workflow Loader (Day 3-5)

- [ ] 實作 `workflow_loader.py`
- [ ] 支援 YAML frontmatter 解析
- [ ] 支援變數引用 (`$inputs.xxx`, `$phases.xxx.output`)
- [ ] 撰寫單元測試

#### Step 3: 撰寫第一個 Workflow (Day 6-8)

- [ ] 將 `orchestrator.py` 流程轉換為 `meddic-analysis.md`
- [ ] 驗證所有 phase 和 condition 正確
- [ ] 確保向後相容

#### Step 4: 重構 Orchestrator (Day 9-12)

- [ ] 修改 `orchestrator.py` 讀取 workflow 定義
- [ ] 實作 phase 執行引擎
- [ ] 實作 condition 評估器
- [ ] 保留 legacy 模式作為 fallback

#### Step 5: 整合測試 (Day 13-15)

- [ ] 端對端測試 (E2E)
- [ ] 效能比較 (重構前後)
- [ ] 文件更新

### 驗收標準

1. **功能完整性**
   - [ ] 新舊模式產出相同結果
   - [ ] 所有 6 個 Agent 正常執行
   - [ ] 品質檢查迴圈正常運作

2. **可維護性**
   - [ ] 非工程師可讀懂 workflow 檔案
   - [ ] 修改 workflow 不需要改 Python code

3. **測試覆蓋**
   - [ ] workflow_loader 單元測試 > 90%
   - [ ] E2E 測試通過

---

## Agent B: Phase 2 - Skills Registry 系統

### 任務概述

建立 Skills Registry 系統，讓 Agent 可以動態註冊、載入和執行。

### 目標

- Agent 抽象化為可重用的 Skill
- 支援動態載入（不需重啟服務）
- 為未來 Marketplace 機制奠定基礎

### 關鍵輸入檔案

```text
modules/03-sales-conversation/meddic/agents/
├── base.py                          # GeminiJSONAgent 基類
├── context_agent.py                 # 需抽象為 Skill
├── buyer_agent.py
├── seller_agent.py
├── summary_agent.py
├── coach_agent.py
├── crm_agent.py
└── prompts/
    ├── agent1-context.md
    ├── agent2-buyer.md
    ├── agent3-seller.md
    ├── agent4-summary.md
    ├── agent6-crm-extractor.md
    └── global-context.md
```

### 預期輸出

#### 1. 新增目錄結構

```text
core/
├── skills/                           # 新增
│   ├── __init__.py
│   ├── base.py                      # Skill 抽象基類
│   ├── registry.py                  # Skills Registry
│   ├── loader.py                    # Skill 載入器
│   └── schema.py                    # Skill Schema 定義

modules/03-sales-conversation/
├── skills/                           # 新增：模組專屬 Skills
│   ├── context-agent/
│   │   ├── skill.yaml               # Skill 定義
│   │   ├── prompt.md                # Prompt 模板
│   │   ├── schema.py                # Input/Output Schema
│   │   └── __init__.py
│   ├── buyer-agent/
│   │   ├── skill.yaml
│   │   ├── prompt.md
│   │   ├── schema.py
│   │   └── __init__.py
│   ├── seller-agent/
│   │   └── ...
│   ├── summary-agent/
│   │   └── ...
│   ├── coach-agent/
│   │   └── ...
│   └── crm-agent/
│       └── ...
```

#### 2. Skill 定義格式 (skill.yaml)

```yaml
# modules/03-sales-conversation/skills/buyer-agent/skill.yaml

# 基本資訊
name: buyer-agent
version: 1.0.0
description: 分析客戶需求、痛點、MEDDIC 指標
author: iCHEF Sales AI Team

# 分類標籤
tags:
  - sales
  - meddic
  - buyer-insight
  - analysis

# 執行配置
execution:
  type: llm-agent
  model: gemini-2.0-flash
  temperature: 0.2
  timeout: 60

# 輸入定義
inputs:
  transcript_segments:
    type: array
    description: 對話逐字稿片段
    required: true
    schema:
      items:
        type: object
        properties:
          start: { type: number }
          end: { type: number }
          speaker: { type: string }
          text: { type: string }

  context_insights:
    type: object
    description: Context Agent 的輸出
    required: false

# 輸出定義
outputs:
  identified_needs:
    type: array
    description: 識別到的客戶需求
  psychology:
    type: object
    description: 客戶心理分析
    properties:
      trustScore: { type: number, min: 0, max: 100 }
      hesitations: { type: array }
  meddic:
    type: object
    description: MEDDIC 指標
    properties:
      metrics: { type: string }
      economic_buyer: { type: string }
      decision_criteria: { type: string }
      decision_process: { type: string }
      pain: { type: string }
      champion: { type: string }

# 品質規則
quality_rules:
  - rule: "len(outputs.identified_needs) >= 2"
    message: "識別到的需求太少"
  - rule: "len(outputs.psychology.hesitations) > 0"
    message: "未識別到客戶疑慮"
  - rule: "len(outputs.meddic.pain) >= 10"
    message: "痛點描述過於簡短"

# 支援的操作
capabilities:
  - analyze      # 主要分析
  - refine       # 修正重跑

# 依賴
dependencies:
  core:
    - core.llm.client
    - core.database.models

# Prompt 檔案
prompt_file: prompt.md
```

#### 3. Core Skills Module

##### base.py - Skill 抽象基類

```python
"""
core/skills/base.py - Skill 抽象基類
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
import yaml


@dataclass
class SkillMetadata:
    """Skill 元數據"""
    name: str
    version: str
    description: str
    author: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class SkillConfig:
    """Skill 執行配置"""
    type: str = "llm-agent"
    model: str = "gemini-2.0-flash"
    temperature: float = 0.2
    timeout: int = 60


@dataclass
class SkillResult:
    """Skill 執行結果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Skill(ABC):
    """Skill 抽象基類"""

    def __init__(
        self,
        skill_dir: Path,
        config_override: Optional[Dict[str, Any]] = None
    ):
        self.skill_dir = Path(skill_dir)
        self.config_file = self.skill_dir / "skill.yaml"
        self.raw_config = self._load_config()
        self.config_override = config_override or {}

        # 解析配置
        self.metadata = self._parse_metadata()
        self.execution_config = self._parse_execution_config()
        self.inputs_schema = self.raw_config.get("inputs", {})
        self.outputs_schema = self.raw_config.get("outputs", {})
        self.quality_rules = self.raw_config.get("quality_rules", [])
        self.capabilities = self.raw_config.get("capabilities", ["analyze"])

        # 載入 Prompt
        prompt_file = self.raw_config.get("prompt_file", "prompt.md")
        self.prompt_template = self._load_prompt(prompt_file)

    def _load_config(self) -> Dict[str, Any]:
        """載入 skill.yaml"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Skill config not found: {self.config_file}")
        return yaml.safe_load(self.config_file.read_text(encoding="utf-8"))

    def _parse_metadata(self) -> SkillMetadata:
        """解析元數據"""
        return SkillMetadata(
            name=self.raw_config["name"],
            version=self.raw_config["version"],
            description=self.raw_config.get("description", ""),
            author=self.raw_config.get("author", ""),
            tags=self.raw_config.get("tags", []),
        )

    def _parse_execution_config(self) -> SkillConfig:
        """解析執行配置"""
        exec_config = self.raw_config.get("execution", {})
        # 允許 config_override 覆蓋
        exec_config.update(self.config_override)
        return SkillConfig(
            type=exec_config.get("type", "llm-agent"),
            model=exec_config.get("model", "gemini-2.0-flash"),
            temperature=exec_config.get("temperature", 0.2),
            timeout=exec_config.get("timeout", 60),
        )

    def _load_prompt(self, filename: str) -> str:
        """載入 Prompt 模板"""
        prompt_path = self.skill_dir / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return ""

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version

    def validate_inputs(self, inputs: Dict[str, Any]) -> List[str]:
        """驗證輸入參數，回傳錯誤列表"""
        errors = []
        for key, schema in self.inputs_schema.items():
            if schema.get("required", False) and key not in inputs:
                errors.append(f"Missing required input: {key}")
        return errors

    @abstractmethod
    def execute(self, **inputs) -> SkillResult:
        """執行 Skill"""
        pass

    def refine(
        self,
        previous_result: Dict[str, Any],
        feedback: str,
        **inputs
    ) -> SkillResult:
        """修正先前的結果"""
        raise NotImplementedError("This skill does not support refinement")
```

##### registry.py - Skills Registry

```python
"""
core/skills/registry.py - Skills Registry

Usage:
    registry = SkillRegistry()
    registry.discover("modules/03-sales-conversation/skills")
    buyer_skill = registry.get("buyer-agent")
    result = buyer_skill.execute(transcript_segments=[...])
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base import Skill
from .loader import SkillLoader

logger = logging.getLogger(__name__)


class SkillNotFoundError(Exception):
    """Skill 未找到"""
    pass


class SkillRegistry:
    """
    Skills Registry - 管理所有已註冊的 Skills

    Features:
    - 從目錄自動發現 Skills
    - 動態載入/卸載
    - 版本管理
    - 依賴解析
    """

    _instance: Optional["SkillRegistry"] = None

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._skill_versions: Dict[str, List[str]] = {}
        self._loader = SkillLoader()

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        """取得單例實例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, skill: Skill) -> None:
        """註冊 Skill"""
        key = skill.name
        self._skills[key] = skill

        # 追蹤版本
        if key not in self._skill_versions:
            self._skill_versions[key] = []
        if skill.version not in self._skill_versions[key]:
            self._skill_versions[key].append(skill.version)

        logger.info(f"Registered skill: {key} v{skill.version}")

    def unregister(self, name: str) -> bool:
        """取消註冊 Skill"""
        if name in self._skills:
            del self._skills[name]
            logger.info(f"Unregistered skill: {name}")
            return True
        return False

    def get(self, name: str, version: Optional[str] = None) -> Skill:
        """取得 Skill"""
        if name not in self._skills:
            raise SkillNotFoundError(f"Skill not found: {name}")

        skill = self._skills[name]
        if version and skill.version != version:
            raise SkillNotFoundError(f"Skill {name} version {version} not found")

        return skill

    def has(self, name: str) -> bool:
        """檢查 Skill 是否存在"""
        return name in self._skills

    def list_skills(self) -> List[str]:
        """列出所有已註冊的 Skills"""
        return list(self._skills.keys())

    def list_by_tag(self, tag: str) -> List[str]:
        """依標籤列出 Skills"""
        return [
            name for name, skill in self._skills.items()
            if tag in skill.metadata.tags
        ]

    def discover(
        self,
        directory: str | Path,
        recursive: bool = True
    ) -> int:
        """
        從目錄發現並載入 Skills

        Returns:
            載入的 Skill 數量
        """
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Skills directory not found: {directory}")
            return 0

        loaded = 0
        pattern = "**/skill.yaml" if recursive else "*/skill.yaml"

        for skill_config in directory.glob(pattern):
            try:
                skill = self._loader.load(skill_config.parent)
                self.register(skill)
                loaded += 1
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_config}: {e}")

        logger.info(f"Discovered {loaded} skills from {directory}")
        return loaded

    def get_skill_info(self, name: str) -> Dict[str, Any]:
        """取得 Skill 詳細資訊"""
        skill = self.get(name)
        return {
            "name": skill.name,
            "version": skill.version,
            "description": skill.metadata.description,
            "author": skill.metadata.author,
            "tags": skill.metadata.tags,
            "capabilities": skill.capabilities,
            "inputs": skill.inputs_schema,
            "outputs": skill.outputs_schema,
        }
```

##### loader.py - Skill Loader

```python
"""
core/skills/loader.py - Skill Loader

負責從目錄載入 Skill 實例
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type

from .base import Skill, SkillResult

logger = logging.getLogger(__name__)


class LLMAgentSkill(Skill):
    """基於 LLM 的 Skill 實作"""

    def __init__(self, skill_dir: Path, config_override: Optional[Dict] = None):
        super().__init__(skill_dir, config_override)
        self._agent = None

    def _ensure_agent(self):
        """延遲初始化 LLM Agent"""
        if self._agent is None:
            from modules.sales_conversation.meddic.agents.base import (
                GeminiJSONAgent,
            )
            # 動態建立 agent
            self._agent = self._create_agent()
        return self._agent

    def _create_agent(self):
        """建立底層 Agent（子類可覆寫）"""
        # 預設使用 GeminiJSONAgent
        pass

    def execute(self, **inputs) -> SkillResult:
        """執行 Skill"""
        import time

        # 驗證輸入
        errors = self.validate_inputs(inputs)
        if errors:
            return SkillResult(
                success=False,
                error=f"Input validation failed: {errors}"
            )

        start = time.time()
        try:
            agent = self._ensure_agent()
            response = agent.invoke(**inputs)
            return SkillResult(
                success=True,
                data=response.data,
                duration=time.time() - start,
                metadata={"report": response.report}
            )
        except Exception as e:
            logger.error(f"Skill {self.name} execution failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                duration=time.time() - start
            )


class SkillLoader:
    """Skill 載入器"""

    def load(
        self,
        skill_dir: str | Path,
        config_override: Optional[Dict] = None
    ) -> Skill:
        """
        從目錄載入 Skill

        優先順序：
        1. 如果有 __init__.py，嘗試載入自定義 Skill 類
        2. 否則使用 LLMAgentSkill 預設實作
        """
        skill_dir = Path(skill_dir)
        init_file = skill_dir / "__init__.py"

        if init_file.exists():
            # 嘗試載入自定義實作
            custom_skill = self._load_custom_skill(skill_dir)
            if custom_skill:
                return custom_skill(skill_dir, config_override)

        # 使用預設 LLM Agent Skill
        return LLMAgentSkill(skill_dir, config_override)

    def _load_custom_skill(self, skill_dir: Path) -> Optional[Type[Skill]]:
        """載入自定義 Skill 類"""
        try:
            init_file = skill_dir / "__init__.py"
            spec = importlib.util.spec_from_file_location(
                f"skill_{skill_dir.name}",
                init_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 尋找繼承自 Skill 的類
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type) and
                    issubclass(attr, Skill) and
                    attr is not Skill
                ):
                    return attr
        except Exception as e:
            logger.warning(f"Failed to load custom skill from {skill_dir}: {e}")

        return None
```

### 實施步驟

#### Step 1: 建立 Core Skills 模組 (Day 1-3)

- [ ] 建立 `core/skills/` 目錄結構
- [ ] 實作 `base.py` - Skill 抽象基類
- [ ] 實作 `schema.py` - 資料結構定義
- [ ] 撰寫單元測試

#### Step 2: 實作 Registry 和 Loader (Day 4-7)

- [ ] 實作 `registry.py` - Skills Registry
- [ ] 實作 `loader.py` - Skill Loader
- [ ] 支援動態發現和載入
- [ ] 撰寫整合測試

#### Step 3: 遷移現有 Agents (Day 8-14)

- [ ] 建立 `modules/03-sales-conversation/skills/` 目錄
- [ ] 遷移 Context Agent → `context-agent/`
- [ ] 遷移 Buyer Agent → `buyer-agent/`
- [ ] 遷移 Seller Agent → `seller-agent/`
- [ ] 遷移 Summary Agent → `summary-agent/`
- [ ] 遷移 Coach Agent → `coach-agent/`
- [ ] 遷移 CRM Agent → `crm-agent/`

#### Step 4: 整合 Orchestrator (Day 15-18)

- [ ] 修改 `orchestrator.py` 使用 SkillRegistry
- [ ] 確保向後相容
- [ ] 效能測試

#### Step 5: 文件和測試 (Day 19-21)

- [ ] 撰寫 Skills 開發指南
- [ ] E2E 測試
- [ ] API 文件

### 驗收標準

1. **功能完整性**
   - [ ] 所有 6 個 Agent 成功遷移為 Skills
   - [ ] Registry 可動態載入/卸載
   - [ ] 向後相容現有 orchestrator

2. **可擴展性**
   - [ ] 新增 Skill 只需建立目錄和 skill.yaml
   - [ ] 支援自定義 Skill 類

3. **測試覆蓋**
   - [ ] core/skills 單元測試 > 90%
   - [ ] E2E 整合測試通過

---

## Agent C: Phase 3 - Plugin 架構分離

### 任務概述

將系統重構為 Plugin 架構，分離基礎設施和業務邏輯。

### 目標

- 基礎設施（transcription, notification, llm-gateway）與業務邏輯（MEDDIC 分析）分離
- 支援未來多租戶、多方法論
- 獨立部署、獨立測試

### 依賴

> **重要**：此 Phase 依賴 Phase 1 和 Phase 2 完成

- Phase 1: Workflow 定義格式
- Phase 2: Skills Registry 系統

### 關鍵輸入

```text
# Phase 1 輸出
modules/03-sales-conversation/workflows/
modules/03-sales-conversation/transcript_analyzer/workflow_loader.py

# Phase 2 輸出
core/skills/
modules/03-sales-conversation/skills/
```

### 預期輸出

#### 1. 新增目錄結構

```text
plugins/                              # 新增：Plugin 根目錄
├── README.md
├── sales-core/                       # 基礎設施 Plugin
│   ├── plugin.yaml                  # Plugin 定義
│   ├── __init__.py
│   ├── transcription/               # 從 infrastructure/services/ 遷移
│   │   ├── service.py
│   │   ├── routes.py
│   │   └── providers/
│   ├── notification/                # 從 infrastructure/services/ 遷移
│   │   ├── service.py
│   │   └── channels/
│   ├── llm-gateway/                 # 從 infrastructure/services/ 遷移
│   │   ├── routing/
│   │   └── resilience/
│   └── tests/
│
├── sales-meddic/                     # MEDDIC 方法論 Plugin
│   ├── plugin.yaml
│   ├── __init__.py
│   ├── skills/                       # 從 modules/03-sales-conversation/skills/ 遷移
│   │   ├── context-agent/
│   │   ├── buyer-agent/
│   │   └── ...
│   ├── workflows/                    # 從 modules/03-sales-conversation/workflows/ 遷移
│   │   └── meddic-analysis.md
│   └── tests/
│
└── sales-ichef/                      # iCHEF 客製化 Plugin (可選)
    ├── plugin.yaml
    ├── slack-integration/
    ├── crm-sync/
    └── tests/
```

#### 2. Plugin 定義格式 (plugin.yaml)

```yaml
# plugins/sales-meddic/plugin.yaml

name: sales-meddic
version: 1.0.0
description: MEDDIC 銷售方法論 Plugin
type: domain  # domain | infrastructure

# 依賴
dependencies:
  plugins:
    - sales-core@^1.0.0
  core:
    - core.skills
    - core.database

# 提供的 Skills
skills:
  - context-agent
  - buyer-agent
  - seller-agent
  - summary-agent
  - coach-agent
  - crm-agent

# 提供的 Workflows
workflows:
  - meddic-analysis
  - quick-analysis

# 配置 Schema
config_schema:
  meddic_weights:
    type: object
    properties:
      metrics: { type: number, default: 15 }
      economic_buyer: { type: number, default: 20 }
      # ...

# 生命週期鉤子
hooks:
  on_install: scripts/install.py
  on_enable: scripts/enable.py
  on_disable: scripts/disable.py
```

#### 3. Core Plugin Manager

```python
"""
core/plugins/manager.py - Plugin Manager

管理 Plugin 的載入、啟用、停用
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from core.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class PluginMetadata:
    """Plugin 元數據"""
    def __init__(self, data: Dict[str, Any]):
        self.name = data["name"]
        self.version = data["version"]
        self.description = data.get("description", "")
        self.type = data.get("type", "domain")
        self.dependencies = data.get("dependencies", {})
        self.skills = data.get("skills", [])
        self.workflows = data.get("workflows", [])


class Plugin:
    """Plugin 實例"""

    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir
        self.config_file = plugin_dir / "plugin.yaml"
        self.raw_config = self._load_config()
        self.metadata = PluginMetadata(self.raw_config)
        self._enabled = False

    def _load_config(self) -> Dict[str, Any]:
        """載入 plugin.yaml"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Plugin config not found: {self.config_file}")
        return yaml.safe_load(self.config_file.read_text(encoding="utf-8"))

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self, skill_registry: SkillRegistry) -> None:
        """啟用 Plugin"""
        if self._enabled:
            return

        # 載入 Skills
        skills_dir = self.plugin_dir / "skills"
        if skills_dir.exists():
            skill_registry.discover(skills_dir)

        self._enabled = True
        logger.info(f"Plugin enabled: {self.name}")

    def disable(self, skill_registry: SkillRegistry) -> None:
        """停用 Plugin"""
        if not self._enabled:
            return

        # 卸載 Skills
        for skill_name in self.metadata.skills:
            skill_registry.unregister(skill_name)

        self._enabled = False
        logger.info(f"Plugin disabled: {self.name}")


class PluginManager:
    """
    Plugin Manager - 管理所有 Plugins

    Features:
    - 從目錄發現 Plugins
    - 依賴解析
    - 生命週期管理
    """

    _instance: Optional["PluginManager"] = None

    def __init__(self, skill_registry: Optional[SkillRegistry] = None):
        self._plugins: Dict[str, Plugin] = {}
        self._skill_registry = skill_registry or SkillRegistry.get_instance()

    @classmethod
    def get_instance(cls) -> "PluginManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def discover(self, directory: str | Path) -> int:
        """發現並載入 Plugins"""
        directory = Path(directory)
        if not directory.exists():
            return 0

        loaded = 0
        for plugin_config in directory.glob("*/plugin.yaml"):
            try:
                plugin = Plugin(plugin_config.parent)
                self._plugins[plugin.name] = plugin
                loaded += 1
                logger.info(f"Discovered plugin: {plugin.name}")
            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_config}: {e}")

        return loaded

    def enable(self, name: str) -> bool:
        """啟用 Plugin"""
        if name not in self._plugins:
            logger.error(f"Plugin not found: {name}")
            return False

        plugin = self._plugins[name]

        # 檢查依賴
        for dep_name in plugin.metadata.dependencies.get("plugins", []):
            # 解析版本（簡化處理）
            dep_plugin = dep_name.split("@")[0]
            if dep_plugin not in self._plugins:
                logger.error(f"Missing dependency: {dep_plugin}")
                return False
            if not self._plugins[dep_plugin].enabled:
                self.enable(dep_plugin)

        plugin.enable(self._skill_registry)
        return True

    def disable(self, name: str) -> bool:
        """停用 Plugin"""
        if name not in self._plugins:
            return False

        self._plugins[name].disable(self._skill_registry)
        return True

    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有 Plugins"""
        return [
            {
                "name": p.name,
                "version": p.metadata.version,
                "type": p.metadata.type,
                "enabled": p.enabled,
                "skills": p.metadata.skills,
            }
            for p in self._plugins.values()
        ]
```

### 實施步驟

#### Step 1: 建立 Plugin 基礎架構 (Day 1-5)

- [ ] 建立 `plugins/` 目錄結構
- [ ] 實作 `core/plugins/manager.py`
- [ ] 設計 plugin.yaml schema
- [ ] 撰寫單元測試

#### Step 2: 建立 sales-core Plugin (Day 6-12)

- [ ] 遷移 `infrastructure/services/transcription/`
- [ ] 遷移 `infrastructure/services/notification/`
- [ ] 遷移 `infrastructure/services/llm_gateway/`
- [ ] 建立 plugin.yaml
- [ ] 整合測試

#### Step 3: 建立 sales-meddic Plugin (Day 13-20)

- [ ] 遷移 Phase 2 的 Skills
- [ ] 遷移 Phase 1 的 Workflows
- [ ] 建立 plugin.yaml
- [ ] 整合測試

#### Step 4: 建立 sales-ichef Plugin (Day 21-25) [可選]

- [ ] 遷移 Slack 整合
- [ ] 遷移 CRM 同步
- [ ] iCHEF 特定配置

#### Step 5: 整合和遷移 (Day 26-30)

- [ ] 修改啟動流程使用 PluginManager
- [ ] 更新部署腳本
- [ ] E2E 測試
- [ ] 文件更新

### 驗收標準

1. **功能完整性**
   - [ ] sales-core Plugin 正常運作
   - [ ] sales-meddic Plugin 正常運作
   - [ ] 依賴解析正確

2. **獨立性**
   - [ ] 每個 Plugin 可獨立測試
   - [ ] 每個 Plugin 可獨立部署
   - [ ] 停用 Plugin 不影響其他 Plugin

3. **測試覆蓋**
   - [ ] PluginManager 單元測試 > 90%
   - [ ] E2E 整合測試通過

---

## 附錄

### A. 三 Agent 協作指南

#### 並行開發規則

```text
Agent A (Phase 1) 和 Agent B (Phase 2) 可以並行開發：

Agent A 專注於：
- modules/03-sales-conversation/workflows/
- modules/03-sales-conversation/transcript_analyzer/workflow_loader.py
- 不要修改 meddic/agents/ 目錄

Agent B 專注於：
- core/skills/
- modules/03-sales-conversation/skills/
- 不要修改 workflows/ 目錄

Agent C (Phase 3) 在 Phase 1 + 2 完成後開始：
- 依賴 Agent A 的 workflow 格式
- 依賴 Agent B 的 skills 結構
```

#### 共享介面定義

```python
# 三個 Agent 共同遵守的介面

# 1. Skill 執行結果 (Phase 2 定義，Phase 1 和 3 使用)
@dataclass
class SkillResult:
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    duration: float

# 2. Workflow Phase 定義 (Phase 1 定義，Phase 3 使用)
@dataclass
class WorkflowPhase:
    name: str
    steps: List[WorkflowStep]
    parallel: bool
    condition: Optional[str]
```

#### 溝通檢查點

| 時間點 | 檢查項目 |
|--------|---------|
| Week 1 結束 | Agent A/B 確認 schema 定義一致 |
| Week 3 結束 | Agent A/B 完成初版，準備交接給 Agent C |
| Week 5 結束 | Agent C 完成 sales-core Plugin |
| Week 7 結束 | 全系統整合測試 |

### B. 測試策略

```text
tests/
├── unit/
│   ├── workflow_loader_test.py      # Agent A
│   ├── skills_registry_test.py      # Agent B
│   └── plugin_manager_test.py       # Agent C
├── integration/
│   ├── workflow_execution_test.py   # Agent A + B
│   └── plugin_loading_test.py       # Agent B + C
└── e2e/
    └── full_pipeline_test.py        # 全系統
```

### C. 文件清單

完成後需更新的文件：

- [ ] `README.md` - 專案概述
- [ ] `docs/ARCHITECTURE.md` - 架構說明
- [ ] `docs/SKILLS_DEVELOPMENT.md` - Skills 開發指南
- [ ] `docs/PLUGIN_DEVELOPMENT.md` - Plugin 開發指南
- [ ] `docs/WORKFLOW_AUTHORING.md` - Workflow 撰寫指南
- [ ] `AGENTS.md` - Agent 設計文件
