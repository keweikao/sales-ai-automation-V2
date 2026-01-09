"""
檢查 2026 年 1 月上傳但未完成 Agent 1-4 分析的音檔
"""

from google.cloud import firestore
from datetime import datetime
from typing import Dict, Any, List

# Initialize Firestore
db = firestore.Client(project='sales-ai-automation-v2')


def check_agent_status(case_data: Dict[str, Any]) -> Dict[str, str]:
    """檢查每個 Agent 的狀態"""
    analysis = case_data.get('analysis', {})
    agents = analysis.get('agents', {})

    result = {}
    for i in range(1, 5):
        agent_key = f'agent{i}'
        agent_data = agents.get(agent_key, {})
        status = agent_data.get('status', 'not_started')
        has_data = bool(agent_data.get('data'))

        if status == 'success' and has_data:
            result[agent_key] = '✓'
        elif status == 'failed':
            result[agent_key] = '✗ failed'
        elif status == 'processing':
            result[agent_key] = '⏳ processing'
        else:
            result[agent_key] = '- not_started'

    return result


def is_complete(case_data: Dict[str, Any]) -> bool:
    """判斷是否所有 Agent 1-4 都完成"""
    analysis = case_data.get('analysis', {})
    agents = analysis.get('agents', {})

    for i in range(1, 5):
        agent_key = f'agent{i}'
        agent_data = agents.get(agent_key, {})
        if agent_data.get('status') != 'success' or not agent_data.get('data'):
            return False
    return True


def main():
    # 查詢 2026 年 1 月的案件
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 2, 1)

    print("=" * 80)
    print("檢查 2026 年 1 月上傳但未完成 Agent 1-4 分析的音檔")
    print("=" * 80)
    print(f"查詢範圍: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print()

    # 查詢所有 1 月份的 cases
    cases_ref = db.collection('cases')
    query = cases_ref.where('createdAt', '>=', start_date).where('createdAt', '<', end_date)

    docs = list(query.stream())
    print(f"共找到 {len(docs)} 個 1 月份的案件")
    print()

    incomplete_cases: List[Dict] = []
    complete_cases: List[Dict] = []

    for doc in docs:
        case_data = doc.to_dict()
        case_id = doc.id

        created_at = case_data.get('createdAt')
        # Handle DatetimeWithNanoseconds
        if hasattr(created_at, 'timestamp'):
            created_at = datetime.fromtimestamp(created_at.timestamp())

        case_info = {
            'case_id': case_id,
            'customer_name': case_data.get('customerName', 'N/A'),
            'sales_rep': case_data.get('salesRepName', 'N/A'),
            'status': case_data.get('status', 'N/A'),
            'created_at': created_at,
            'agent_status': check_agent_status(case_data)
        }

        if is_complete(case_data):
            complete_cases.append(case_info)
        else:
            incomplete_cases.append(case_info)

    # 顯示未完成的案件
    print("=" * 80)
    print(f"未完成分析的案件: {len(incomplete_cases)} 個")
    print("=" * 80)

    if incomplete_cases:
        for case in incomplete_cases:
            created_str = case['created_at'].strftime('%Y-%m-%d %H:%M') if case['created_at'] else 'N/A'
            print(f"\n案件 ID: {case['case_id']}")
            print(f"  客戶: {case['customer_name']}")
            print(f"  業務: {case['sales_rep']}")
            print(f"  狀態: {case['status']}")
            print(f"  建立時間: {created_str}")
            print("  Agent 狀態:")
            for agent, status in case['agent_status'].items():
                print(f"    {agent}: {status}")
    else:
        print("所有案件都已完成分析！")

    # 顯示已完成的案件摘要
    print()
    print("=" * 80)
    print(f"已完成分析的案件: {len(complete_cases)} 個")
    print("=" * 80)

    if complete_cases:
        for case in complete_cases:
            created_str = case['created_at'].strftime('%Y-%m-%d %H:%M') if case['created_at'] else 'N/A'
            print(f"  ✓ {case['case_id']} - {case['customer_name']} ({created_str})")

    # 統計摘要
    print()
    print("=" * 80)
    print("統計摘要")
    print("=" * 80)
    total = len(docs)
    complete_count = len(complete_cases)
    incomplete_count = len(incomplete_cases)

    print(f"總案件數: {total}")
    print(f"已完成: {complete_count} ({complete_count/total*100:.1f}%)" if total > 0 else "已完成: 0")
    print(f"未完成: {incomplete_count} ({incomplete_count/total*100:.1f}%)" if total > 0 else "未完成: 0")

    # 分析未完成案件的原因
    if incomplete_cases:
        print()
        print("未完成原因分析:")
        agent_issues = {f'agent{i}': {'failed': 0, 'not_started': 0, 'processing': 0} for i in range(1, 5)}

        for case in incomplete_cases:
            for agent, status in case['agent_status'].items():
                if 'failed' in status:
                    agent_issues[agent]['failed'] += 1
                elif 'not_started' in status:
                    agent_issues[agent]['not_started'] += 1
                elif 'processing' in status:
                    agent_issues[agent]['processing'] += 1

        for agent, issues in agent_issues.items():
            if any(v > 0 for v in issues.values()):
                print(f"  {agent}: failed={issues['failed']}, not_started={issues['not_started']}, processing={issues['processing']}")


if __name__ == '__main__':
    main()
