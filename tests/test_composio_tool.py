"""
Unit tests for tools/composio_tool.py — Composio MCP HTTP integration.
"""

import json
import unittest
from unittest.mock import patch, MagicMock
from tools.composio_tool import (
    composio_execute_action,
    composio_search_tools,
    composio_read_sandbox_result,
    _call_composio_mcp,
)


def _mock_mcp_response(content_text: str) -> MagicMock:
    """Helper: creates a mock requests.Response returning JSON-RPC result."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": content_text}]}
    })
    return mock_resp


class TestComposioTool(unittest.TestCase):

    @patch("tools.composio_tool.requests.post")
    def test_search_tools_success(self, mock_post):
        mock_post.return_value = _mock_mcp_response(
            json.dumps({"session_id": "test_session_abc", "tools": ["GMAIL_FETCH_EMAILS"]})
        )
        res = composio_search_tools.invoke({"query": "list Gmail inbox messages"})
        self.assertEqual(res["status"], "success")
        self.assertIn("query", res["data"])
        self.assertIn("results", res["data"])

    @patch("tools.composio_tool.requests.post")
    def test_execute_action_gmail_fetch(self, mock_post):
        search_resp = _mock_mcp_response(
            json.dumps({"session_id": "flag", "tools": ["GMAIL_FETCH_EMAILS"]})
        )
        execute_resp = _mock_mcp_response(
            json.dumps({"status": "success", "messages": [{"subject": "Test Email", "from": "test@example.com"}]})
        )
        mock_post.side_effect = [search_resp, execute_resp]

        res = composio_execute_action.invoke({
            "intent": "Fetch 5 most recent Gmail emails",
            "tool_slug": "GMAIL_FETCH_EMAILS",
            "tool_arguments": '{"max_results": 5, "label_ids": ["INBOX"], "user_id": "me"}'
        })
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["tool_slug"], "GMAIL_FETCH_EMAILS")

    @patch("tools.composio_tool.requests.post")
    def test_execute_action_sends_email(self, mock_post):
        search_resp = _mock_mcp_response(json.dumps({"session_id": "flag"}))
        send_resp = _mock_mcp_response(json.dumps({"status": "success", "message_id": "msg_12345"}))
        mock_post.side_effect = [search_resp, send_resp]

        res = composio_execute_action.invoke({
            "intent": "Send an email",
            "tool_slug": "GMAIL_SEND_EMAIL",
            "tool_arguments": json.dumps({
                "to": "test@example.com",
                "subject": "Jarvis PCB Report",
                "body": "Here is your audit report."
            })
        })
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["tool_slug"], "GMAIL_SEND_EMAIL")

    @patch("tools.composio_tool.requests.post")
    def test_read_sandbox_result(self, mock_post):
        mock_post.return_value = _mock_mcp_response(
            '{"subject": "Test Subject", "from": "me@example.com"}'
        )
        res = composio_read_sandbox_result.invoke({
            "session_id": "flag",
            "file_path": "/mnt/files/mex/help.json"
        })
        self.assertEqual(res["status"], "success")
        self.assertIn("output", res["data"])

    @patch("tools.composio_tool.requests.post")
    def test_auth_error_handling(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        result = _call_composio_mcp("tools/call", {"name": "COMPOSIO_SEARCH_TOOLS", "arguments": {}})
        self.assertIn("error", result)

    @patch("tools.composio_tool.requests.post")
    def test_optional_param_missing_tool_arguments(self, mock_post):
        """Verifies default empty tool_arguments '{}' is used when omitted."""
        search_resp = _mock_mcp_response(json.dumps({"session_id": "flag"}))
        exec_resp = _mock_mcp_response(json.dumps({"status": "success"}))
        mock_post.side_effect = [search_resp, exec_resp]

        res = composio_execute_action.invoke({
            "intent": "Check supply chain",
            "tool_slug": "GMAIL_LIST_LABELS"
            # tool_arguments omitted — should default to "{}"
        })
        self.assertEqual(res["status"], "success")


if __name__ == "__main__":
    unittest.main()
