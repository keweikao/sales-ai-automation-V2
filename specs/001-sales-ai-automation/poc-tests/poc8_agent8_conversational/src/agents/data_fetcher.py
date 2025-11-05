"""
數據查詢模塊 - 從 Firestore 或測試數據查詢相關案件

根據 QuestionParams 查詢對應的案件數據
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from google.cloud import firestore
from .question_parser import QuestionParams, QuestionType


class QueryResult(Dict[str, Any]):
    """查詢結果"""
    pass


class DataFetcher:
    """數據查詢器"""

    def __init__(
        self,
        project_id: Optional[str] = None,
        test_mode: bool = False,
        test_data_path: Optional[str] = None
    ):
        """
        初始化數據查詢器

        Args:
            project_id: GCP 項目 ID
            test_mode: 是否使用測試模式（從 JSON 讀取數據）
            test_data_path: 測試數據文件路徑
        """
        self.test_mode = test_mode or os.getenv("TEST_MODE", "false").lower() == "true"
        self.test_data_path = test_data_path
        self.test_data: List[Dict] = []

        if self.test_mode:
            # 測試模式：從 JSON 加載數據
            if not self.test_data_path:
                # 預設路徑
                current_dir = os.path.dirname(os.path.abspath(__file__))
                self.test_data_path = os.path.join(
                    current_dir,
                    "../../test_data/firestore_mock_cases.json"
                )

            with open(self.test_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.test_data = data.get("cases", [])

            print(f"[測試模式] 載入 {len(self.test_data)} 個案件")
        else:
            # 生產模式：連接 Firestore
            project_id = project_id or os.getenv("GCP_PROJECT_ID")
            if not project_id:
                raise ValueError("GCP_PROJECT_ID 未設定")

            self.db = firestore.Client(project=project_id)
            self.collection_name = os.getenv("TEST_COLLECTION", "opportunities")

    def _parse_timerange(self, time_range: str) -> tuple:
        """
        解析時間範圍為開始和結束時間

        Args:
            time_range: 時間範圍字串

        Returns:
            (start_datetime, end_datetime)
        """
        now = datetime.utcnow()

        if time_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_range == "this_week":
            # 本週一到現在
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = now
        elif time_range == "last_week":
            days_since_monday = now.weekday()
            end_of_last_week = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            start = end_of_last_week - timedelta(days=7)
            end = end_of_last_week
        elif time_range == "this_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_range == "last_month":
            first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = first_day_this_month
            # 上個月第一天
            if now.month == 1:
                start = first_day_this_month.replace(year=now.year-1, month=12)
            else:
                start = first_day_this_month.replace(month=now.month-1)
        elif time_range == "recent":
            # 最近 7 天
            start = now - timedelta(days=7)
            end = now
        else:
            # 預設最近 7 天
            start = now - timedelta(days=7)
            end = now

        return start, end

    def _filter_cases_by_time(self, cases: List[Dict], time_range: str) -> List[Dict]:
        """
        根據時間範圍篩選案件

        Args:
            cases: 案件列表
            time_range: 時間範圍

        Returns:
            篩選後的案件列表
        """
        if not time_range:
            return cases

        start, end = self._parse_timerange(time_range)

        filtered_cases = []
        for case in cases:
            created_at_str = case.get("createdAt", "")
            try:
                # 解析 ISO 8601 格式
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if start <= created_at <= end:
                    filtered_cases.append(case)
            except:
                # 如果解析失敗，保留這個案件
                filtered_cases.append(case)

        return filtered_cases

    def fetch_relevant_data(self, params: QuestionParams) -> QueryResult:
        """
        根據問題參數查詢相關數據

        Args:
            params: 問題參數

        Returns:
            QueryResult: 查詢結果
        """
        if self.test_mode:
            return self._fetch_from_test_data(params)
        else:
            return self._fetch_from_firestore(params)

    def _fetch_from_test_data(self, params: QuestionParams) -> QueryResult:
        """
        從測試數據查詢

        Args:
            params: 問題參數

        Returns:
            QueryResult: 查詢結果
        """
        cases = self.test_data.copy()

        # 1. 時間範圍篩選
        if params.timeRange:
            cases = self._filter_cases_by_time(cases, params.timeRange)

        # 2. 業務名字篩選
        if params.salesRepName:
            cases = [c for c in cases if c.get("salesRepName") == params.salesRepName]

        # 3. 案件 ID 篩選
        if params.caseId:
            cases = [c for c in cases if c.get("caseId") == params.caseId]

        # 4. 客戶名字篩選
        if params.customerName:
            cases = [c for c in cases if c.get("customerName") == params.customerName]

        # 5. 健康度篩選
        if params.healthScoreMin is not None:
            cases = [
                c for c in cases
                if c.get("analysis", {}).get("structured", {}).get("healthScore", 0) >= params.healthScoreMin
            ]
        if params.healthScoreMax is not None:
            cases = [
                c for c in cases
                if c.get("analysis", {}).get("structured", {}).get("healthScore", 100) <= params.healthScoreMax
            ]

        # 6. 銷售階段篩選
        if params.salesStage:
            cases = [
                c for c in cases
                if c.get("analysis", {}).get("structured", {}).get("salesStage") == params.salesStage
            ]

        # 7. 競品篩選
        if params.competitorName:
            filtered_cases = []
            for case in cases:
                competitors = case.get("analysis", {}).get("competitors", [])
                for comp in competitors:
                    if comp.get("name") == params.competitorName:
                        filtered_cases.append(case)
                        break
            cases = filtered_cases

        # 8. 功能需求篩選
        if params.feature:
            filtered_cases = []
            for case in cases:
                questionnaires = case.get("analysis", {}).get("discoveryQuestionnaires", [])
                for q in questionnaires:
                    if params.feature.lower() in q.get("topic", "").lower():
                        filtered_cases.append(case)
                        break
            cases = filtered_cases

        # 9. 排序
        if params.sort:
            cases = self._sort_cases(cases, params.sort)

        # 10. 計算團隊統計
        team_stats = self._calculate_team_stats(cases)

        return QueryResult({
            "relevantCases": cases,
            "teamStats": team_stats,
            "timeRange": params.timeRange,
            "totalCases": len(cases)
        })

    def _fetch_from_firestore(self, params: QuestionParams) -> QueryResult:
        """
        從 Firestore 查詢（生產模式）

        Args:
            params: 問題參數

        Returns:
            QueryResult: 查詢結果
        """
        # TODO: 實現 Firestore 查詢邏輯
        # 這裡是生產環境的實現
        query = self.db.collection(self.collection_name)

        # 根據 params 建立查詢條件
        # ...

        # 執行查詢
        # docs = query.stream()
        # cases = [doc.to_dict() for doc in docs]

        # 暫時返回空結果
        return QueryResult({
            "relevantCases": [],
            "teamStats": {},
            "timeRange": params.timeRange,
            "totalCases": 0
        })

    def _sort_cases(self, cases: List[Dict], sort_by: str) -> List[Dict]:
        """
        排序案件

        Args:
            cases: 案件列表
            sort_by: 排序方式

        Returns:
            排序後的案件列表
        """
        if sort_by == "health_desc":
            return sorted(
                cases,
                key=lambda c: c.get("analysis", {}).get("structured", {}).get("healthScore", 0),
                reverse=True
            )
        elif sort_by == "health_asc":
            return sorted(
                cases,
                key=lambda c: c.get("analysis", {}).get("structured", {}).get("healthScore", 0)
            )
        elif sort_by == "created_desc":
            return sorted(
                cases,
                key=lambda c: c.get("createdAt", ""),
                reverse=True
            )
        elif sort_by == "created_asc":
            return sorted(
                cases,
                key=lambda c: c.get("createdAt", "")
            )
        else:
            return cases

    def _calculate_team_stats(self, cases: List[Dict]) -> Dict[str, Any]:
        """
        計算團隊統計數據

        Args:
            cases: 案件列表

        Returns:
            團隊統計數據
        """
        if not cases:
            return {
                "totalCases": 0,
                "avgHealthScore": 0,
                "salesReps": []
            }

        # 總案件數
        total_cases = len(cases)

        # 平均健康度
        health_scores = [
            c.get("analysis", {}).get("structured", {}).get("healthScore", 0)
            for c in cases
        ]
        avg_health_score = sum(health_scores) / len(health_scores) if health_scores else 0

        # 業務統計
        sales_rep_stats = {}
        for case in cases:
            rep_name = case.get("salesRepName", "未知")
            rep_id = case.get("salesRepId", "unknown")

            if rep_id not in sales_rep_stats:
                sales_rep_stats[rep_id] = {
                    "salesRepName": rep_name,
                    "salesRepId": rep_id,
                    "caseCount": 0,
                    "healthScores": []
                }

            sales_rep_stats[rep_id]["caseCount"] += 1
            health_score = case.get("analysis", {}).get("structured", {}).get("healthScore", 0)
            sales_rep_stats[rep_id]["healthScores"].append(health_score)

        # 計算每個業務的平均健康度
        sales_reps = []
        for rep_data in sales_rep_stats.values():
            avg = sum(rep_data["healthScores"]) / len(rep_data["healthScores"]) if rep_data["healthScores"] else 0
            sales_reps.append({
                "salesRepName": rep_data["salesRepName"],
                "salesRepId": rep_data["salesRepId"],
                "caseCount": rep_data["caseCount"],
                "avgHealthScore": round(avg, 1)
            })

        # 按健康度排序
        sales_reps.sort(key=lambda x: x["avgHealthScore"], reverse=True)

        return {
            "totalCases": total_cases,
            "avgHealthScore": round(avg_health_score, 1),
            "salesReps": sales_reps
        }


# 單例模式
_fetcher_instance: Optional[DataFetcher] = None


def get_data_fetcher(test_mode: bool = False) -> DataFetcher:
    """
    獲取 DataFetcher 單例

    Args:
        test_mode: 是否使用測試模式

    Returns:
        DataFetcher 實例
    """
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = DataFetcher(test_mode=test_mode)
    return _fetcher_instance


if __name__ == "__main__":
    # 測試用
    from question_parser import QuestionParams, QuestionType

    fetcher = DataFetcher(test_mode=True)

    # 測試案例 1：今天的團隊數據
    params1 = QuestionParams(
        type=QuestionType.TEAM_OVERVIEW,
        timeRange="today"
    )
    result1 = fetcher.fetch_relevant_data(params1)
    print(f"\n測試 1 - 今天團隊數據:")
    print(f"  案件數: {result1['totalCases']}")
    print(f"  平均健康度: {result1['teamStats']['avgHealthScore']}")

    # 測試案例 2：王小明的案件
    params2 = QuestionParams(
        type=QuestionType.SALES_REP_PERFORMANCE,
        salesRepName="王小明",
        timeRange="recent"
    )
    result2 = fetcher.fetch_relevant_data(params2)
    print(f"\n測試 2 - 王小明的案件:")
    print(f"  案件數: {result2['totalCases']}")

    # 測試案例 3：低健康度案件
    params3 = QuestionParams(
        type=QuestionType.CASE_DETAILS,
        healthScoreMax=50,
        timeRange="recent"
    )
    result3 = fetcher.fetch_relevant_data(params3)
    print(f"\n測試 3 - 低健康度案件 (<= 50):")
    print(f"  案件數: {result3['totalCases']}")
    for case in result3['relevantCases']:
        print(f"    - {case['caseId']}: {case.get('analysis', {}).get('structured', {}).get('healthScore', 0)} 分")
