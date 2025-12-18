from datetime import datetime
import logging
from typing import Dict, Any, List, Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)

class StatsService:
    """
    Service for aggregating sales statistics and pre-processing data for reports.
    Implements 'Aggregation on Write' pattern to avoid full-table scans.
    """
    
    def __init__(self, db_client: firestore.Client):
        self.db = db_client
        self.collection_name = "stats_daily"

    def update_daily_stats(self, case_id: str, case_data: Dict[str, Any]) -> None:
        """
        Updates the daily statistics document with the given case data.
        Should be called immediately after a case is analyzed and saved.
        """
        created_at = case_data.get("createdAt")
        if not created_at:
            logger.warning(f"Case {case_id} has no createdAt, using today.")
            created_at = datetime.utcnow()
        elif isinstance(created_at, datetime):
            pass # Already datetime
        else:
            # Handle string or timestamp conversion if necessary
            # Assuming firestore.SERVER_TIMESTAMP or datetime object usually
            pass

        # Convert to YYYY-MM-DD for document ID
        date_str = created_at.strftime("%Y-%m-%d")
        stats_ref = self.db.collection(self.collection_name).document(date_str)
        
        # Extract Sales Rep info
        sales_rep = case_data.get("salesRep", {})
        user_id = sales_rep.get("slack_id")
        user_name = sales_rep.get("name") or "Unknown"

        if not user_id:
            logger.warning(f"Case {case_id} has no sales rep slack_id. Skipping stats update.")
            return

        # Extract Metrics from Agents
        analysis = case_data.get("analysis", {})
        
        # Agent 3: Progress Score
        agent3_data = analysis.get("agents", {}).get("agent3", {}).get("data", {})
        progress_score = agent3_data.get("progress_score", 0)
        
        # Determine Lists (Priority / Risk)
        is_high_priority = self._check_high_priority(analysis)
        is_risk = self._check_risk(analysis)

        # Run Transaction
        transaction = self.db.transaction()
        StatsService._update_stats_transaction(transaction, stats_ref, user_id, user_name, progress_score, case_id, is_high_priority, is_risk)
        logger.info(f"Updated daily stats for {date_str} with case {case_id}")

    @staticmethod
    @firestore.transactional
    def _update_stats_transaction(
        transaction: firestore.Transaction, 
        stats_ref: firestore.DocumentReference, 
        user_id: str, 
        user_name: str,
        progress_score: int, 
        case_id: str,
        is_high_priority: bool,
        is_risk: bool
    ):
        snapshot = stats_ref.get(transaction=transaction)
        
        if not snapshot.exists:
            stats_data = {
                "date": stats_ref.id,
                "team_total_demos": 0,
                "team_avg_score_sum": 0,
                "reps": {},
                "updated_at": firestore.SERVER_TIMESTAMP
            }
        else:
            stats_data = snapshot.to_dict()

        # Update Team Totals
        stats_data["team_total_demos"] = stats_data.get("team_total_demos", 0) + 1
        stats_data["team_avg_score_sum"] = stats_data.get("team_avg_score_sum", 0) + progress_score

        # Update Rep Stats
        reps = stats_data.get("reps", {})
        rep_stats = reps.get(user_id, {
            "name": user_name,
            "demo_count": 0,
            "total_progress_score": 0,
            "high_priority_cases": [],
            "risk_cases": []
        })
        
        # Ensure name updates if changed
        rep_stats["name"] = user_name
        rep_stats["demo_count"] += 1
        rep_stats["total_progress_score"] += progress_score
        
        if is_high_priority:
            if case_id not in rep_stats["high_priority_cases"]:
                rep_stats["high_priority_cases"].append(case_id)
        
        if is_risk:
            if case_id not in rep_stats["risk_cases"]:
                rep_stats["risk_cases"].append(case_id)
        
        reps[user_id] = rep_stats
        stats_data["reps"] = reps
        stats_data["updated_at"] = firestore.SERVER_TIMESTAMP

        transaction.set(stats_ref, stats_data)

    def _check_high_priority(self, analysis: Dict) -> bool:
        """
        Check if case is High Priority (Quick Win).
        Condition: Progress Score > 60 AND Strategy = 'CloseNow' (立即成交)
        """
        try:
            agent3 = analysis.get("agents", {}).get("agent3", {}).get("data", {})
            score = agent3.get("progress_score", 0)
            strategy = agent3.get("recommended_strategy", "")
            
            # Simple keyword check for 'CloseNow' variants in Chinese or English
            is_close_now = "CloseNow" in strategy or "立即成交" in strategy
            
            return score > 60 and is_close_now
        except Exception:
            return False

    def _check_risk(self, analysis: Dict) -> bool:
        """
        Check if case is Risk.
        Conditions:
        1. Progress Score < 40
        2. OR (Urgency High AND Decision Maker Bad)
        """
        try:
            # Condition 1: Low Progress
            agent3 = analysis.get("agents", {}).get("agent3", {}).get("data", {})
            score = agent3.get("progress_score", 0)
            if score < 40 and score > 0: # >0 to ensure it was actually scored
                return True

            # Condition 2: Invalid Urgency
            agent1 = analysis.get("agents", {}).get("agent1", {}).get("data", {})
            urgency = agent1.get("urgency_level", "")
            decision_maker = agent1.get("decision_maker", "")
            
            is_urgent = "高" in urgency or "High" in urgency
            bad_dm = "只有員工" in decision_maker or "Staff" in decision_maker

            return is_urgent and bad_dm
        except Exception:
            return False

    def get_weekly_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Aggregates stats from multiple daily documents for a weekly report.
        """
        # Range query on document IDs (YYYY-MM-DD) works because they are lexicographical
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        docs = self.db.collection(self.collection_name)\
            .where("date", ">=", start_str)\
            .where("date", "<=", end_str)\
            .stream()
            
        aggregated = {
            "total_demos": 0,
            "weighted_score_sum": 0, # sum(daily_avg_sum)
            "reps": {}
        }
        
        for doc in docs:
            data = doc.to_dict()
            aggregated["total_demos"] += data.get("team_total_demos", 0)
            aggregated["weighted_score_sum"] += data.get("team_avg_score_sum", 0)
            
            daily_reps = data.get("reps", {})
            for uid, daily_rep_stats in daily_reps.items():
                if uid not in aggregated["reps"]:
                    aggregated["reps"][uid] = {
                        "name": daily_rep_stats.get("name"),
                        "demo_count": 0,
                        "total_score": 0,
                        "high_priority_cases": [],
                        "risk_cases": []
                    }
                
                rep_agg = aggregated["reps"][uid]
                rep_agg["demo_count"] += daily_rep_stats.get("demo_count", 0)
                rep_agg["total_score"] += daily_rep_stats.get("total_progress_score", 0)
                # Combine lists and deduct later
                rep_agg["high_priority_cases"].extend(daily_rep_stats.get("high_priority_cases", []))
                rep_agg["risk_cases"].extend(daily_rep_stats.get("risk_cases", []))
        
        # Deduplicate case lists
        for uid, r in aggregated["reps"].items():
            r["high_priority_cases"] = list(set(r["high_priority_cases"]))
            r["risk_cases"] = list(set(r["risk_cases"]))
            
        return aggregated

    def get_daily_risk_cases(self, date: datetime) -> List[str]:
        """
        Get all risk case IDs for a specific date.
        """
        date_str = date.strftime("%Y-%m-%d")
        doc = self.db.collection(self.collection_name).document(date_str).get()
        
        risk_cases = []
        if doc.exists:
            data = doc.to_dict()
            reps = data.get("reps", {})
            for _, rep_stats in reps.items():
                risk_cases.extend(rep_stats.get("risk_cases", []))
        
        return list(set(risk_cases))
