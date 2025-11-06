"""
Unit tests for MCP Adapter.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from slack_app.mcp_adapter import MCPAdapter, PIIAnonymizer, ToolRegistry


class TestPIIAnonymizer:
    def test_email_anonymization(self):
        anonymizer = PIIAnonymizer(session_id="test-001")

        data = {"email": "test@example.com", "name": "John"}
        result = anonymizer.anonymize(data)

        assert result["email"].startswith("[EMAIL_")
        assert result["name"] == "John"
        assert "test@example.com" in anonymizer.pii_map["email"].values()

    def test_phone_anonymization(self):
        anonymizer = PIIAnonymizer(session_id="test-002")

        data = {"phone": "0912-345-678"}
        result = anonymizer.anonymize(data)

        assert result["phone"].startswith("[PHONE_")

    def test_nested_anonymization(self):
        anonymizer = PIIAnonymizer(session_id="test-003")

        data = {
            "users": [
                {"email": "user1@test.com"},
                {"email": "user2@test.com"}
            ]
        }
        result = anonymizer.anonymize(data)

        assert result["users"][0]["email"].startswith("[EMAIL_")
        assert result["users"][1]["email"].startswith("[EMAIL_")
        assert len(anonymizer.pii_map["email"]) == 2


class TestToolRegistry:
    def test_discover_tools_names_only(self):
        registry = ToolRegistry(tools_dir="tools")

        # Should return list of tool names
        tools = registry.discover_tools(category="firestore", detail_level="names")

        assert isinstance(tools, list)
        # Will be empty until tools are created
        assert "firestore.query" in tools  # Uncomment after Phase 2

    def test_load_tool_definition(self):
        registry = ToolRegistry(tools_dir="tools")

        # Should cache tool definition
        tool_def = registry.load_tool_definition("firestore.query")
        assert "name" in tool_def
        assert "description" in tool_def
        assert "parameters" in tool_def


class TestMCPAdapter:
    def test_initialization(self):
        mcp = MCPAdapter(session_id="test-session-001")

        assert mcp.session_id == "test-session-001"
        assert mcp.registry is not None
        assert mcp.executor is not None
        assert mcp.anonymizer is not None

    def test_get_session_stats(self):
        mcp = MCPAdapter(session_id="test-session-002")

        stats = mcp.get_session_stats()

        assert stats["session_id"] == "test-session-002"
        assert "cached_tools" in stats
        assert "pii_detections" in stats
