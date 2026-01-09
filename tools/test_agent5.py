import sys
import os
import unittest
from unittest.mock import MagicMock

# Add analysis-service/src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../analysis-service/src')))

from agents.agent5_coach import CoachAgent

class TestCoachAgent(unittest.TestCase):
    def setUp(self):
        # Mock Firestore Client
        self.mock_db = MagicMock()
        self.agent = CoachAgent(db_client=self.mock_db)

    def test_evaluate_close_now_alert(self):
        """Test 'close_now' alert logic"""
        # Data setup
        seller_data = {"progress_score": 85, "recommended_strategy": "CloseNow (立即成交)"}
        buyer_data = {} # Not used for this rule
        context_data = {"urgency_level": "High", "decision_maker": "Boss"}
        
        alert = self.agent.evaluate(
            case_id="case_123",
            rep_id="rep_1",
            rep_name="Test Rep",
            store_name="Test Store",
            context_data=context_data,
            buyer_data=buyer_data,
            seller_data=seller_data
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, "close_now")
        print(f"✅ test_evaluate_close_now_alert Passed: Triggered {alert.alert_type}")

    def test_evaluate_no_alert(self):
        """Test normal case with no alert"""
        seller_data = {"progress_score": 70, "recommended_strategy": "Nurture"}
        context_data = {"urgency_level": "Medium", "decision_maker": "Staff"}
        
        alert = self.agent.evaluate(
            case_id="case_124",
            rep_id="rep_1",
            rep_name="Test Rep", 
            store_name="Test Store",
            context_data=context_data,
            buyer_data={},
            seller_data=seller_data
        )
        
        self.assertIsNone(alert)
        print("✅ test_evaluate_no_alert Passed: No trigger")

    def test_manager_alert_consecutive_low(self):
        """Test manager alert for 3 consecutive low scores"""
        # Mock DB query for history
        # We need to mock the chain: collection().where().where().order_by().limit().stream()
        
        # Create mock docs
        doc1 = MagicMock()
        doc1.to_dict.return_value = {
            "uploadedByName": "Test Rep",
            "analysis": {"agents": {"agent3": {"data": {"progress_score": 40}}}}
        }
        
        doc2 = MagicMock()
        doc2.to_dict.return_value = {
            "uploadedByName": "Test Rep",
            "analysis": {"agents": {"agent3": {"data": {"progress_score": 45}}}}
        }
        
        # Setup mock chain
        mock_collection = self.mock_db.collection.return_value
        mock_query = mock_collection.where.return_value.where.return_value.order_by.return_value.limit.return_value
        mock_query.stream.return_value = [doc1, doc2]
        
        # Current score is 30 (Low)
        alert = self.agent.evaluate_manager_alert(
            case_id="current_case",
            rep_id="rep_1",
            current_score=30
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, "consecutive_low_scores")
        self.assertEqual(alert.severity, "high")
        self.assertIn("40", alert.reason)
        self.assertIn("45", alert.reason)
        print(f"✅ test_manager_alert_consecutive_low Passed: {alert.reason}")

    def test_manager_alert_not_consecutive(self):
        """Test manager alert NOT triggering if history has high score"""
        # History: [40, 60] -> One low, one high. Chain broken.
        doc1 = MagicMock()
        doc1.to_dict.return_value = {
            "analysis": {"agents": {"agent3": {"data": {"progress_score": 40}}}}
        }
        doc2 = MagicMock()
        doc2.to_dict.return_value = {
            "analysis": {"agents": {"agent3": {"data": {"progress_score": 60}}}}
        }
        
        mock_collection = self.mock_db.collection.return_value
        mock_query = mock_collection.where.return_value.where.return_value.order_by.return_value.limit.return_value
        mock_query.stream.return_value = [doc1, doc2]
        
        alert = self.agent.evaluate_manager_alert(
            case_id="current_case",
            rep_id="rep_1",
            current_score=30
        )
        
        self.assertIsNone(alert)
        print("✅ test_manager_alert_not_consecutive Passed: No trigger")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
