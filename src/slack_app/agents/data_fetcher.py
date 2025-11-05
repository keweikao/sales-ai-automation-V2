"""
數據查詢模塊 - 從 Firestore 查詢相關案件

根據 QuestionParams 查詢對應的案件數據
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from google.cloud import firestore
from .question_parser import QuestionParams, QuestionType

logger = logging.getLogger(__name__)


class QueryResult(Dict[str, Any]):
    """查詢結果"""
    pass


class DataFetcher:
    """數據查詢器"""

    def __init__(
        self,
        project_id: Optional[str] = None,
        db_client: Optional[firestore.Client] = None
    ):
        """
        初始化數據查詢器

        Args:
            project_id: GCP 項目 ID
            db_client: Firestore Client（可選，如果提供則直接使用）
        """
        if db_client:
            self.db = db_client
        else:
            project_id = project_id or os.getenv("GCP_PROJECT_ID")
            if not project_id:
                raise ValueError("GCP_PROJECT_ID 未設定")
            self.db = firestore.Client(project=project_id)

        self.collection_name = os.getenv("FIRESTORE_COLLECTION", "opportunities")

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

    def fetch_relevant_data(self, params: QuestionParams) -> QueryResult:
        """
        根據問題參數查詢相關數據

        Args:
            params: 問題參數

        Returns:
            QueryResult: 查詢結果
        """
        try:
            query = self.db.collection(self.collection_name)

            # 1. 時間範圍篩選
            if params.timeRange:
                start, end = self._parse_timerange(params.timeRange)
                query = query.where("createdAt", ">=", start).where("createdAt", "<=", end)

            # 2. 業務名字篩選
            if params.salesRepName:
                query = query.where("salesRepName", "==", params.salesRepName)

            # 3. 業務 ID 篩選
            if params.salesRepId:
                query = query.where("salesRepId", "==", params.salesRepId)

            # 4. 案件 ID 篩選
            if params.caseId:
                query = query.where("caseId", "==", params.caseId)

            # 5. 客戶名字篩選
            if params.customerName:
                query = query.where("customerName", "==", params.customerName)

            # 執行查詢
            docs = query.stream()
            cases = []
            for doc in docs:
                case_data = doc.to_dict()
                case_data['id'] = doc.id
                cases.append(case_data)

            # 6. 健康度篩選（在記憶體中過濾，因為 Firestore 不支持嵌套欄位查詢）
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

            # 7. 銷售階段篩選
            if params.salesStage:
                cases = [
                    c for c in cases
                    if c.get("analysis", {}).get("structured", {}).get("salesStage") == params.salesStage
                ]

            # 8. 競品篩選
            if params.competitorName:
                filtered_cases = []
                for case in cases:
                    competitors = case.get("analysis", {}).get("competitors", [])
                    for comp in competitors:
                        if comp.get("name") == params.competitorName:
                            filtered_cases.append(case)
                            break
                cases = filtered_cases

            # 9. 功能需求篩選
            if params.feature:
                filtered_cases = []
                for case in cases:
                    questionnaires = case.get("analysis", {}).get("discoveryQuestionnaires", [])
                    for q in questionnaires:
                        if params.feature.lower() in q.get("topic", "").lower():
                            filtered_cases.append(case)
                            break
                cases = filtered_cases

            # 10. 排序
            if params.sort:
                cases = self._sort_cases(cases, params.sort)

            # 11. 計算團隊統計
            team_stats = self._calculate_team_stats(cases)

            logger.info(f"查詢結果：{len(cases)} 個案件，參數：{params.model_dump(exclude_none=True)}")

            return QueryResult({
                "relevantCases": cases,
                "teamStats": team_stats,
                "timeRange": params.timeRange,
                "totalCases": len(cases)
            })

        except Exception as e:
            logger.error(f"查詢數據失敗：{e}", exc_info=True)
            raise

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
                key=lambda c: c.get("createdAt", datetime.min),
                reverse=True
            )
        elif sort_by == "created_asc":
            return sorted(
                cases,
                key=lambda c: c.get("createdAt", datetime.min)
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
