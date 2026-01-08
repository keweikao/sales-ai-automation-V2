"""
Integration tests for API Gateway endpoints.

Tests the Firestore mock and basic data operations.
Since the API Gateway uses relative imports that don't work
in isolated test context, these tests focus on data layer validation.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from typing import Generator


@pytest.fixture
def mock_firestore():
    """Mock Firestore client for testing."""
    from tests.e2e.mocks.firestore_mock import MockFirestore
    return MockFirestore()


@pytest.fixture
def mock_firestore_with_data(mock_firestore):
    """Mock Firestore with sample data."""
    # Add sample leads
    mock_firestore.collection("leads").document("lead-001").set({
        "customerId": "CU001",
        "storeName": "Test Restaurant",
        "customerName": "John Doe",
        "phone": "0912345678",
        "status": "new",
        "source": "website",
        "createdAt": datetime.now(),
    })
    mock_firestore.collection("leads").document("lead-002").set({
        "customerId": "CU002",
        "storeName": "Another Store",
        "customerName": "Jane Smith",
        "phone": "0987654321",
        "status": "qualified",
        "source": "referral",
        "createdAt": datetime.now(),
    })

    # Add sample cases
    mock_firestore.collection("cases").document("case-001").set({
        "caseId": "202501-IC001",
        "status": "completed",
        "completedAt": datetime.now(),
        "analysis": {
            "agents": {
                "agent2": {
                    "data": {"meddic_score": 75}
                }
            }
        }
    })
    mock_firestore.collection("cases").document("case-002").set({
        "caseId": "202501-IC002",
        "status": "completed",
        "completedAt": datetime.now(),
        "analysis": {
            "agents": {
                "agent2": {
                    "data": {"meddic_score": 85}
                }
            }
        }
    })

    return mock_firestore


# ===== Firestore Mock Basic Tests =====

class TestFirestoreMock:
    """Tests for MockFirestore functionality."""

    def test_set_and_get_document(self, mock_firestore):
        """Test setting and getting a document."""
        mock_firestore.collection("test").document("doc1").set({
            "name": "Test",
            "value": 123,
        })

        doc = mock_firestore.collection("test").document("doc1").get()
        assert doc.exists
        data = doc.to_dict()
        assert data["name"] == "Test"
        assert data["value"] == 123

    def test_get_nonexistent_document(self, mock_firestore):
        """Test getting a document that doesn't exist."""
        doc = mock_firestore.collection("test").document("nonexistent").get()
        assert not doc.exists

    def test_list_documents_via_stream(self, mock_firestore_with_data):
        """Test listing documents using stream."""
        docs = list(mock_firestore_with_data.collection("leads").stream())
        assert len(docs) == 2

    def test_document_update(self, mock_firestore):
        """Test updating a document."""
        doc_ref = mock_firestore.collection("test").document("doc1")
        doc_ref.set({"name": "Original", "count": 1})

        doc_ref.update({"count": 2})

        doc = doc_ref.get()
        data = doc.to_dict()
        assert data["name"] == "Original"  # unchanged
        assert data["count"] == 2  # updated

    def test_document_delete(self, mock_firestore):
        """Test deleting a document."""
        doc_ref = mock_firestore.collection("test").document("doc1")
        doc_ref.set({"name": "ToDelete"})

        doc_ref.delete()

        doc = doc_ref.get()
        assert not doc.exists

    def test_where_query(self, mock_firestore_with_data):
        """Test filtering with where clause."""
        query = mock_firestore_with_data.collection("leads").where(
            "status", "==", "new"
        )
        docs = list(query.stream())

        assert len(docs) == 1
        assert docs[0].to_dict()["status"] == "new"

    def test_limit_query(self, mock_firestore_with_data):
        """Test limiting results."""
        query = mock_firestore_with_data.collection("leads").limit(1)
        docs = list(query.stream())

        assert len(docs) == 1

    def test_subcollection_support(self, mock_firestore):
        """Test subcollection functionality."""
        # Create parent document
        mock_firestore.collection("cases").document("case-001").set({
            "status": "completed"
        })

        # Create subcollection document
        subcol_ref = (
            mock_firestore.collection("cases")
            .document("case-001")
            .collection("analysis")
        )
        subcol_ref.document("result-001").set({
            "score": 85,
            "timestamp": datetime.now(),
        })

        # Verify subcollection
        doc = subcol_ref.document("result-001").get()
        assert doc.exists
        data = doc.to_dict()
        assert data["score"] == 85


# ===== Lead Data Tests =====

class TestLeadData:
    """Tests for lead data operations."""

    def test_lead_data_structure(self, mock_firestore_with_data):
        """Test lead document structure."""
        doc = mock_firestore_with_data.collection("leads").document("lead-001").get()
        data = doc.to_dict()

        assert "customerId" in data
        assert "storeName" in data
        assert "customerName" in data
        assert "phone" in data
        assert "status" in data

    def test_filter_leads_by_status(self, mock_firestore_with_data):
        """Test filtering leads by status."""
        new_leads = list(
            mock_firestore_with_data.collection("leads")
            .where("status", "==", "new")
            .stream()
        )
        qualified_leads = list(
            mock_firestore_with_data.collection("leads")
            .where("status", "==", "qualified")
            .stream()
        )

        assert len(new_leads) == 1
        assert len(qualified_leads) == 1


# ===== Case/Conversation Data Tests =====

class TestCaseData:
    """Tests for case/conversation data operations."""

    def test_case_data_structure(self, mock_firestore_with_data):
        """Test case document structure."""
        doc = mock_firestore_with_data.collection("cases").document("case-001").get()
        data = doc.to_dict()

        assert "caseId" in data
        assert "status" in data
        assert "analysis" in data

    def test_extract_meddic_score(self, mock_firestore_with_data):
        """Test extracting MEDDIC score from case analysis."""
        doc = mock_firestore_with_data.collection("cases").document("case-001").get()
        data = doc.to_dict()

        score = (
            data.get("analysis", {})
            .get("agents", {})
            .get("agent2", {})
            .get("data", {})
            .get("meddic_score")
        )

        assert score == 75

    def test_filter_completed_cases(self, mock_firestore_with_data):
        """Test filtering completed cases."""
        completed = list(
            mock_firestore_with_data.collection("cases")
            .where("status", "==", "completed")
            .stream()
        )

        assert len(completed) == 2


# ===== Analytics Aggregation Tests =====

class TestAnalyticsAggregation:
    """Tests for analytics-style aggregations."""

    def test_count_by_status(self, mock_firestore_with_data):
        """Test counting documents by status."""
        leads = list(mock_firestore_with_data.collection("leads").stream())

        status_counts = {}
        for doc in leads:
            status = doc.to_dict().get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        assert status_counts.get("new", 0) == 1
        assert status_counts.get("qualified", 0) == 1

    def test_aggregate_scores_by_date(self, mock_firestore_with_data):
        """Test aggregating scores by date."""
        cases = list(mock_firestore_with_data.collection("cases").stream())

        daily_scores: dict[str, list] = {}
        for doc in cases:
            data = doc.to_dict()
            completed_at = data.get("completedAt")

            if isinstance(completed_at, datetime):
                day_key = completed_at.strftime("%Y-%m-%d")
            else:
                continue

            score = (
                data.get("analysis", {})
                .get("agents", {})
                .get("agent2", {})
                .get("data", {})
                .get("meddic_score")
            )

            if day_key not in daily_scores:
                daily_scores[day_key] = []
            if score:
                daily_scores[day_key].append(score)

        # Today should have scores
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in daily_scores
        assert len(daily_scores[today]) == 2


# ===== Conversation Analysis Tests =====

class TestConversationAnalysis:
    """Tests for conversation analysis retrieval."""

    def test_get_analysis_from_case(self, mock_firestore_with_data):
        """Test getting analysis from a case document."""
        doc = mock_firestore_with_data.collection("cases").document("case-001").get()
        assert doc.exists

        data = doc.to_dict()
        assert "analysis" in data
        assert "agents" in data["analysis"]
        assert data["analysis"]["agents"]["agent2"]["data"]["meddic_score"] == 75

    def test_calculate_average_meddic(self, mock_firestore_with_data):
        """Test calculating average MEDDIC score."""
        cases = list(mock_firestore_with_data.collection("cases").stream())

        scores = []
        for doc in cases:
            data = doc.to_dict()
            if analysis := data.get("analysis", {}):
                if agents := analysis.get("agents", {}):
                    if agent2 := agents.get("agent2", {}):
                        if score := agent2.get("data", {}).get("meddic_score"):
                            scores.append(score)

        avg_score = sum(scores) / len(scores) if scores else 0
        assert avg_score == 80  # (75 + 85) / 2
