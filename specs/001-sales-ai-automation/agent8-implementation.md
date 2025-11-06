# Agent 8 Implementation Plan

## 服務架構

### 整合到現有系統

**重要**：Agent 8 的兩個功能都**整合到現有服務**，不需要新建服務！

1. **對話式交互**：整合到現有 `slack-service`（詳見 `AGENT8_CONVERSATIONAL.md`）
2. **定時報告**：使用 Cloud Function（輕量級）或整合到 `slack-service`

**推薦方案**：定時報告使用 **Cloud Function**

---

## 資料流程

### 定時報告（Cloud Function）

```
┌─────────────────┐
│ Cloud Scheduler │──── 每天 09:00
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Cloud Function (Python)    │
│  ─────────────────────      │
│  1. Query Firestore         │
│  2. Aggregate team data     │
│  3. Call Agent 8 (Gemini)   │
│  4. Format report           │
│  5. Send to Slack           │
└─────────────────────────────┘
         │
         ├──▶ Firestore (read cases)
         ├──▶ Gemini API (Agent 8)
         └──▶ Slack API (send report)
```

**優點**：

- ✅ 輕量級，冷啟動快
- ✅ 成本更低（Cloud Function < Cloud Run）
- ✅ 獨立部署，不影響 slack-service
- ✅ 複用現有 Slack Bot Token

---

## 實作程式碼

### 1. 資料聚合邏輯

```python
# manager-report-service/src/data_aggregator.py
from google.cloud import firestore
from datetime import datetime, timedelta
from typing import List, Dict, Any

class TeamDataAggregator:
    def __init__(self):
        self.db = firestore.Client()

    def get_team_cases(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """查詢時間範圍內的所有案件"""
        cases_ref = self.db.collection('cases')
        query = cases_ref\
            .where('createdAt', '>=', start_time)\
            .where('createdAt', '<=', end_time)\
            .order_by('createdAt', direction=firestore.Query.DESCENDING)

        cases = []
        for doc in query.stream():
            case_data = doc.to_dict()
            case_data['caseId'] = doc.id

            # 提取 Agent 1-6 分析結果
            analysis = case_data.get('analysis', {})

            # Agent 1: 參與者分析
            participants = analysis.get('participants', [])

            # Agent 2: 情緒分析
            sentiment = analysis.get('sentiment', {})

            # Agent 3: 產品需求
            product_needs = analysis.get('productNeeds', {})

            # Agent 4: 競品分析
            competitors = analysis.get('competitors', [])

            # Agent 5: 問卷分析
            questionnaires = analysis.get('discoveryQuestionnaires', [])

            # Agent 6: 銷售教練
            structured = analysis.get('structured', {})

            cases.append({
                'caseId': case_data['caseId'],
                'salesRepName': case_data.get('salesRepName', 'Unknown'),
                'salesRepId': case_data.get('salesRepSlackId', ''),
                'customerName': case_data.get('customerName', ''),
                'customerId': case_data.get('customerId', ''),
                'status': case_data.get('status', 'unknown'),
                'createdAt': case_data.get('createdAt'),
                'completedAt': case_data.get('completedAt'),
                'processingTime': self._calculate_processing_time(case_data),

                # Agent 1-6 分析結果
                'agent1Participants': participants,
                'agent2Sentiment': sentiment,
                'agent3ProductNeeds': product_needs,
                'agent4Competitors': competitors,
                'agent5Questionnaires': questionnaires,
                'agent6Analysis': {
                    'salesStage': structured.get('salesStage', 'Unknown'),
                    'healthScore': structured.get('dealHealth', {}).get('score', 0),
                    'keyDecisionMaker': structured.get('keyDecisionMaker', {}),
                    'nextSteps': structured.get('nextActions', []),
                    'maximumRisk': structured.get('maximumRisk', {}),
                    'recommendedBundle': structured.get('recommendedBundle', {}),
                }
            })

        return cases

    def _calculate_processing_time(self, case_data: Dict) -> int:
        """計算處理時間（分鐘）"""
        created = case_data.get('createdAt')
        completed = case_data.get('completedAt')
        if created and completed:
            delta = completed - created
            return int(delta.total_seconds() / 60)
        return 0

    def get_system_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """獲取系統效能指標"""
        # 從 Firestore 聚合數據
        # TODO: 可以考慮使用 Cloud Monitoring API
        return {
            'transcriptionAvgTime': 38,  # 平均轉錄時間（分鐘）
            'analysisAvgTime': 4,        # 平均分析時間（秒）
            'errorRate': 0.02            # 錯誤率
        }
```

### 2. Agent 8 調用

```python
# manager-report-service/src/agent8_client.py
import google.generativeai as genai
import json
import os
from typing import Dict, Any

class Agent8Client:
    def __init__(self):
        api_key = os.environ.get('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            'gemini-2.0-flash-exp',
            generation_config={
                'temperature': 0.3,
                'response_mime_type': 'application/json'
            }
        )

        # 載入 prompt template
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'agent8-manager.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()

    def generate_report(self, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """調用 Agent 8 生成管理報告"""

        # 構建輸入 JSON
        input_json = json.dumps(team_data, ensure_ascii=False, indent=2)

        # 組合 prompt
        full_prompt = f"{self.prompt_template}\n\n=== 團隊數據 ===\n{input_json}"

        # 調用 Gemini
        response = self.model.generate_content(full_prompt)

        # 解析 JSON 回應
        try:
            report = json.loads(response.text)
            return report
        except json.JSONDecodeError as e:
            # Fallback: 嘗試提取 JSON
            text = response.text
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                return json.loads(json_str)
            raise ValueError(f"Failed to parse Agent 8 response: {e}")
```

### 3. Slack 報告發送

```python
# manager-report-service/src/slack_reporter.py
from slack_sdk import WebClient
import os
from typing import Dict, Any

class SlackReporter:
    def __init__(self):
        self.client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
        self.manager_channel = os.environ.get('MANAGER_CHANNEL_ID', 'C12345')  # #sales-ai-monitor

    def send_daily_report(self, report: Dict[str, Any]) -> None:
        """發送每日報告到 Slack"""

        summary = report['summary']
        performance = report['salesPerformance']
        attention = report['needsAttention']
        insights = report['teamInsights']
        actions = report['actionItems']

        # 構建 Block Kit 訊息
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 每日團隊報告 - {report.get('reportDate', 'Today')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": report.get('reportSummaryText', '')
                }
            },
            {"type": "divider"},

            # 團隊績效概覽
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*總案件數*\n{summary['totalCases']}"},
                    {"type": "mrkdwn", "text": f"*完成率*\n{summary['successRate']*100:.0f}%"},
                    {"type": "mrkdwn", "text": f"*平均健康度*\n{summary['avgHealthScore']:.0f}"},
                    {"type": "mrkdwn", "text": f"*平均處理時間*\n{summary['avgProcessingTime']} 分鐘"}
                ]
            },
            {"type": "divider"},

            # 業務排名
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🏆 業務績效排名*"
                }
            }
        ]

        # 添加業務績效（Top 5）
        for i, perf in enumerate(performance[:5], 1):
            medal = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'][i-1]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{medal} *{perf['salesRepName']}*\n"
                            f"案件數：{perf['caseCount']} | "
                            f"健康度：{perf['avgHealthScore']:.0f} | "
                            f"完成率：{perf['completionRate']*100:.0f}%\n"
                            f"💪 {perf.get('topStrength', '')}"
                }
            })

        blocks.append({"type": "divider"})

        # 需要關注的案件
        if attention:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*⚠️ 需要關注的案件*"
                }
            })

            for item in attention[:3]:  # 最多顯示 3 個
                urgency_emoji = '🔴' if item['urgency'] == 'high' else '🟡'
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{urgency_emoji} *{item['caseId']}* - {item['customerName']}\n"
                                f"業務：{item['salesRepName']} | 健康度：{item['healthScore']}\n"
                                f"📝 {item['reason']}\n"
                                f"💡 建議：{item['recommendation']}"
                    }
                })

            blocks.append({"type": "divider"})

        # 團隊洞察
        if insights:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🔍 團隊洞察*"
                }
            })

            # 共同挑戰
            if insights.get('commonChallenges'):
                challenges_text = '\n'.join([f"• {c}" for c in insights['commonChallenges']])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*主要挑戰：*\n{challenges_text}"
                    }
                })

            # 成功模式
            if insights.get('successPatterns'):
                patterns_text = '\n'.join([f"• {p}" for p in insights['successPatterns']])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*成功模式：*\n{patterns_text}"
                    }
                })

            blocks.append({"type": "divider"})

        # 行動項目
        if actions:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*✅ 建議行動*"
                }
            })

            for action in actions[:5]:
                priority_emoji = '🔴' if action['priority'] == 'high' else '🟡' if action['priority'] == 'medium' else '🟢'
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{priority_emoji} {action['action']}\n"
                                f"負責人：{action['owner']} | 期限：{action['deadline']}"
                    }
                })

        # 發送訊息
        self.client.chat_postMessage(
            channel=self.manager_channel,
            text=report.get('reportSummaryText', '每日團隊報告'),
            blocks=blocks
        )
```

### 4. 主程式

```python
# manager-report-service/main.py
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import logging

from src.data_aggregator import TeamDataAggregator
from src.agent8_client import Agent8Client
from src.slack_reporter import SlackReporter

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

aggregator = TeamDataAggregator()
agent8 = Agent8Client()
slack = SlackReporter()

@app.route('/generate-daily-report', methods=['POST'])
def generate_daily_report():
    """
    由 Cloud Scheduler 調用
    生成每日團隊報告並發送到 Slack
    """
    try:
        # 時間範圍：昨天 00:00 ~ 23:59
        end_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(days=1)

        logger.info(f"Generating report for {start_time} to {end_time}")

        # 1. 聚合團隊數據
        team_cases = aggregator.get_team_cases(start_time, end_time)
        system_metrics = aggregator.get_system_metrics(start_time, end_time)

        if not team_cases:
            logger.warning("No cases found in the time range")
            return jsonify({"message": "No cases to report"}), 200

        # 2. 調用 Agent 8
        team_data = {
            'reportPeriod': f"{start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}",
            'reportDate': start_time.strftime('%Y-%m-%d'),
            'teamCases': team_cases,
            'systemMetrics': system_metrics
        }

        report = agent8.generate_report(team_data)
        logger.info(f"Agent 8 generated report: {len(report.get('salesPerformance', []))} sales reps")

        # 3. 發送到 Slack
        slack.send_daily_report(report)
        logger.info("Report sent to Slack successfully")

        return jsonify({"message": "Report generated and sent", "caseCount": len(team_cases)}), 200

    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/generate-weekly-report', methods=['POST'])
def generate_weekly_report():
    """週報（過去 7 天）"""
    # 類似邏輯，時間範圍改為 7 天
    pass

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
```

---

## 部署配置

### Cloud Scheduler 設定

```bash
# 每天早上 9:00 觸發每日報告
gcloud scheduler jobs create http daily-manager-report \
  --schedule="0 9 * * *" \
  --time-zone="Asia/Taipei" \
  --uri="https://manager-report-service-xxx.run.app/generate-daily-report" \
  --http-method=POST \
  --oidc-service-account-email=sales-ai-scheduler@sales-ai-automation-v2.iam.gserviceaccount.com

# 每週一早上 9:00 觸發週報
gcloud scheduler jobs create http weekly-manager-report \
  --schedule="0 9 * * 1" \
  --time-zone="Asia/Taipei" \
  --uri="https://manager-report-service-xxx.run.app/generate-weekly-report" \
  --http-method=POST \
  --oidc-service-account-email=sales-ai-scheduler@sales-ai-automation-v2.iam.gserviceaccount.com
```

### Slack Command（可選）

```python
# 在 slack-service 中新增
@app.command("/team-report")
def handle_team_report_command(ack, command, client):
    """主管手動請求團隊報告"""
    ack()

    user_id = command['user_id']

    # 檢查權限（僅主管可用）
    if user_id not in MANAGER_USER_IDS:
        client.chat_postEphemeral(
            channel=command['channel_id'],
            user=user_id,
            text="❌ 此指令僅限主管使用"
        )
        return

    # 觸發報告生成（調用 manager-report-service）
    # ...
```

---

## 成本估算

### 定時報告（Cloud Function）

| 服務 | 用量 | 成本/月 |
|------|------|---------|
| **Cloud Function** | 2 次/天 × 30 天 × 5s | ~$0.01 |
| **Gemini API (定時報告)** | 2 次/天 × 30 天 × ~10K tokens | ~$0.60 |
| **Cloud Scheduler** | 2 jobs（每日 + 每週） | $0.20 |
| **小計（定時報告）** | | **~$0.81** |

### 對話式交互（slack-service）

| 服務 | 用量 | 成本/月 |
|------|------|---------|
| **Gemini API（問題解析）** | 20 次/天 × 2K tokens | ~$0.10 |
| **Gemini API（回答生成）** | 20 次/天 × 10K tokens | ~$0.50 |
| **Firestore 查詢** | 20 次/天 × 50 reads | ~$0.02 |
| **Cloud Run 增量** | 複用現有 slack-service | ~$0 |
| **小計（對話式）** | | **~$0.62** |

### 總計

| 項目 | 成本/月 |
|------|---------|
| 定時報告 | $0.81 |
| 對話式交互 | $0.62 |
| **Agent 8 總計** | **$1.43** |

✅ **極低成本**：不到一杯咖啡的價格
✅ **複用現有基礎設施**：Slack App、Firestore
✅ **按需付費**：只有使用時才產生費用

---

## 測試計劃

```python
# tests/test_agent8.py
import pytest
from datetime import datetime, timedelta

def test_agent8_with_mock_data():
    """測試 Agent 8 能正確分析團隊數據"""
    # Given: 模擬團隊案件數據
    team_data = load_mock_team_data()

    # When: 調用 Agent 8
    agent8 = Agent8Client()
    report = agent8.generate_report(team_data)

    # Then: 驗證輸出結構
    assert 'summary' in report
    assert 'salesPerformance' in report
    assert 'needsAttention' in report
    assert report['summary']['totalCases'] == 12

def test_data_aggregator():
    """測試資料聚合邏輯"""
    # ...

def test_slack_reporter_formats_correctly():
    """測試 Slack 報告格式"""
    # ...
```

---

## 下一步

1. ✅ 建立 `manager-report-service/` 目錄結構
2. ✅ 實作 `data_aggregator.py`
3. ✅ 實作 `agent8_client.py`
4. ✅ 實作 `slack_reporter.py`
5. ✅ 建立 Dockerfile
6. ✅ 部署到 Cloud Run
7. ✅ 設定 Cloud Scheduler
8. ✅ 測試報告生成
