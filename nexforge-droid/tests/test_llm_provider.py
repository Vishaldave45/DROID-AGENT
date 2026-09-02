"""Unit and integration tests for LLM abstraction and Gemini provider."""

import asyncio
import json
import unittest
import urllib.request
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock

from app.config import Settings, get_settings, reset_settings
from app.llm import (
    AuthenticationError,
    ChatMessage,
    ChatRole,
    GeminiProvider,
    InvalidRequestError,
    LLMError,
    MockLLMProvider,
    ModelUnavailableError,
    RateLimitError,
    ToolCallRequest,
    create_llm_provider,
    get_default_provider,
    register_provider,
)


class TestGeminiProvider(unittest.TestCase):
    """Test suite for Gemini Provider message mapping, tool protocols, and execution."""

    def setUp(self):
        reset_settings()

    def tearDown(self):
        reset_settings()

    def test_gemini_provider_initialization(self):
        """Verify initialization with explicit and fallback settings."""
        provider = GeminiProvider(api_key="test_key_123", model_name="gemini-2.5-flash")
        self.assertEqual(provider.api_key, "test_key_123")
        self.assertEqual(provider.model_name, "gemini-2.5-flash")
        self.assertEqual(provider.max_retries, 3)

    def test_convert_messages_system_user_assistant(self):
        """Verify multi-role messages format accurately to Gemini schema."""
        provider = GeminiProvider(api_key="test_key")

        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content="You are an expert software engineer."),
            ChatMessage(role=ChatRole.USER, content="Implement a binary search function."),
            ChatMessage(role=ChatRole.ASSISTANT, content="Here is the implementation: ..."),
        ]

        system_inst, contents = provider._convert_messages(messages)

        # System instruction verification
        self.assertIsNotNone(system_inst)
        self.assertEqual(system_inst["parts"][0]["text"], "You are an expert software engineer.")

        # User and Model turns verification
        self.assertEqual(len(contents), 2)
        self.assertEqual(contents[0]["role"], "user")
        self.assertEqual(contents[0]["parts"][0]["text"], "Implement a binary search function.")
        self.assertEqual(contents[1]["role"], "model")
        self.assertEqual(contents[1]["parts"][0]["text"], "Here is the implementation: ...")

    def test_convert_messages_with_tool_calls_and_responses(self):
        """Verify assistant tool call requests and subsequent tool response mapping."""
        provider = GeminiProvider(api_key="test_key")

        messages = [
            ChatMessage(
                role=ChatRole.ASSISTANT,
                content="I will check the file contents.",
                tool_calls=[
                    ToolCallRequest(
                        call_id="call_read_1",
                        tool_name="read_file",
                        arguments={"path": "/workspace/main.py"},
                    )
                ],
            ),
            ChatMessage(
                role=ChatRole.TOOL,
                name="read_file",
                content=json.dumps({"content": "print('hello')", "bytes": 14}),
            ),
        ]

        _, contents = provider._convert_messages(messages)

        self.assertEqual(len(contents), 2)
        # Model turn with functionCall
        model_turn = contents[0]
        self.assertEqual(model_turn["role"], "model")
        self.assertEqual(len(model_turn["parts"]), 2)
        self.assertEqual(model_turn["parts"][0]["text"], "I will check the file contents.")
        self.assertEqual(model_turn["parts"][1]["functionCall"]["name"], "read_file")
        self.assertEqual(model_turn["parts"][1]["functionCall"]["args"]["path"], "/workspace/main.py")

        # Tool response turn
        tool_turn = contents[1]
        self.assertEqual(tool_turn["role"], "user")
        fn_resp = tool_turn["parts"][0]["functionResponse"]
        self.assertEqual(fn_resp["name"], "read_file")
        self.assertEqual(fn_resp["response"]["content"], "print('hello')")

    def test_convert_tools_openai_and_gemini_format(self):
        """Verify tool specification normalization into Gemini functionDeclarations."""
        provider = GeminiProvider(api_key="test_key")

        # OpenAI format tool
        openai_tool = {
            "type": "function",
            "function": {
                "name": "run_shell",
                "description": "Execute a bash command in the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
        }

        # Gemini native format tool
        gemini_tool = {
            "name": "view_file",
            "description": "Inspect file contents.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }

        tools = provider._convert_tools([openai_tool, gemini_tool])
        self.assertIsNotNone(tools)
        self.assertEqual(len(tools), 1)
        self.assertIn("functionDeclarations", tools[0])
        decls = tools[0]["functionDeclarations"]
        self.assertEqual(len(decls), 2)
        self.assertEqual(decls[0]["name"], "run_shell")
        self.assertEqual(decls[1]["name"], "view_file")

    def test_parse_response_text_and_tokens(self):
        """Verify extracting text and usage metadata from Gemini response payload."""
        provider = GeminiProvider(api_key="test_key", model_name="gemini-2.5-flash")

        mock_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Code refactored successfully."}],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 42,
                "candidatesTokenCount": 88,
                "totalTokenCount": 130,
            },
        }

        resp = provider._parse_response(mock_payload)
        self.assertEqual(resp.content, "Code refactored successfully.")
        self.assertEqual(resp.prompt_tokens, 42)
        self.assertEqual(resp.completion_tokens, 88)
        self.assertEqual(resp.finish_reason, "STOP")
        self.assertEqual(len(resp.tool_calls), 0)

    def test_parse_response_tool_calls(self):
        """Verify parsing function calls into structured ToolCallRequest objects."""
        provider = GeminiProvider(api_key="test_key")

        mock_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "write_file",
                                    "args": {"path": "test.py", "content": "import sys"},
                                }
                            }
                        ],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 30},
        }

        resp = provider._parse_response(mock_payload)
        self.assertIsNone(resp.content)
        self.assertEqual(len(resp.tool_calls), 1)
        call = resp.tool_calls[0]
        self.assertEqual(call.tool_name, "write_file")
        self.assertEqual(call.arguments["path"], "test.py")
        self.assertTrue(call.call_id.startswith("call_"))

    def test_sync_generate_with_mocked_http_requester(self):
        """Verify successful synchronous generation with custom HTTP requester."""
        mock_response_data = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Unit test generated."}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 35},
        }

        def mock_http(req: urllib.request.Request, timeout: float) -> Tuple[int, Dict[str, Any]]:
            # Verify headers and URL
            self.assertEqual(req.headers.get("X-goog-api-key"), "valid_key")
            self.assertEqual(req.headers.get("User-agent"), "aistudio-build")
            return 200, mock_response_data

        provider = GeminiProvider(api_key="valid_key", http_requester=mock_http)
        response = provider.generate([ChatMessage(role=ChatRole.USER, content="Generate test")])

        self.assertEqual(response.content, "Unit test generated.")
        self.assertEqual(response.prompt_tokens, 20)
        self.assertEqual(response.completion_tokens, 35)

    def test_async_generate_with_mocked_http(self):
        """Verify asynchronous generation works seamlessly."""
        mock_response_data = {
            "candidates": [{"content": {"parts": [{"text": "Async result"}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 15},
        }

        def mock_http(req: urllib.request.Request, timeout: float) -> Tuple[int, Dict[str, Any]]:
            return 200, mock_response_data

        provider = GeminiProvider(api_key="valid_key", http_requester=mock_http)

        async def run_async():
            return await provider.generate_async([ChatMessage(role=ChatRole.USER, content="Hello async")])

        response = asyncio.run(run_async())
        self.assertEqual(response.content, "Async result")

    def test_retry_on_rate_limit_429_then_succeed(self):
        """Verify exponential backoff retry on HTTP 429 recovers when subsequent call succeeds."""
        call_count = 0

        def flaky_http(req: urllib.request.Request, timeout: float) -> Tuple[int, Dict[str, Any]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 429, {"error": {"message": "Resource has been exhausted (quota exceeded)"}}
            return 200, {
                "candidates": [{"content": {"parts": [{"text": "Success after retry"}]}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 10},
            }

        provider = GeminiProvider(api_key="test_key", backoff_factor=0.01, http_requester=flaky_http)
        response = provider.generate([ChatMessage(role=ChatRole.USER, content="Test retry")])

        self.assertEqual(response.content, "Success after retry")
        self.assertEqual(call_count, 2)

    def test_retry_exhaustion_raises_ratelimit_error(self):
        """Verify exceeding max retries raises the appropriate RateLimitError."""
        def persistently_failing_http(req: urllib.request.Request, timeout: float) -> Tuple[int, Dict[str, Any]]:
            return 429, {"error": {"message": "Quota limit reached"}}

        provider = GeminiProvider(api_key="test_key", max_retries=2, backoff_factor=0.01, http_requester=persistently_failing_http)

        with self.assertRaises(RateLimitError):
            provider.generate([ChatMessage(role=ChatRole.USER, content="Trigger limit")])

    def test_authentication_error_fails_immediately_no_retry(self):
        """Verify HTTP 401/403 fails immediately without wasteful retries."""
        call_count = 0

        def auth_failing_http(req: urllib.request.Request, timeout: float) -> Tuple[int, Dict[str, Any]]:
            nonlocal call_count
            call_count += 1
            return 403, {"error": {"message": "API key not valid"}}

        provider = GeminiProvider(api_key="bad_key", max_retries=3, http_requester=auth_failing_http)

        with self.assertRaises(AuthenticationError):
            provider.generate([ChatMessage(role=ChatRole.USER, content="Auth check")])

        self.assertEqual(call_count, 1)

    def test_invalid_request_400_fails_immediately(self):
        """Verify HTTP 400 fails immediately without retrying."""
        call_count = 0

        def bad_req_http(req: urllib.request.Request, timeout: float) -> Tuple[int, Dict[str, Any]]:
            nonlocal call_count
            call_count += 1
            return 400, {"error": {"message": "Invalid JSON argument"}}

        provider = GeminiProvider(api_key="valid_key", max_retries=3, http_requester=bad_req_http)

        with self.assertRaises(InvalidRequestError):
            provider.generate([ChatMessage(role=ChatRole.USER, content="Bad query")])

        self.assertEqual(call_count, 1)


class TestProviderRegistryAndMock(unittest.TestCase):
    """Test suite for Provider Registry, Factory, and Mock Provider behavior."""

    def setUp(self):
        reset_settings()

    def test_create_gemini_provider_via_factory(self):
        """Verify factory instantiates GeminiProvider with provided configuration."""
        provider = create_llm_provider("gemini", api_key="custom_key", model_name="gemini-3.7-flash")
        self.assertIsInstance(provider, GeminiProvider)
        self.assertEqual(provider.api_key, "custom_key")
        self.assertEqual(provider.model_name, "gemini-3.7-flash")

    def test_mock_provider_deterministic_behavior(self):
        """Verify MockLLMProvider returns scripted text and tool calls accurately."""
        mock_p = MockLLMProvider()
        mock_p.queue_text("Hello from mock")
        mock_p.queue_tool_call("grep_search", {"query": "def calculate"}, call_id="call_grep_1")

        # 1st call
        res1 = mock_p.generate([ChatMessage(role=ChatRole.USER, content="Hi")])
        self.assertEqual(res1.content, "Hello from mock")
        self.assertEqual(len(res1.tool_calls), 0)

        # 2nd call
        res2 = mock_p.generate([ChatMessage(role=ChatRole.USER, content="Search for calculate")])
        self.assertIsNone(res2.content)
        self.assertEqual(len(res2.tool_calls), 1)
        self.assertEqual(res2.tool_calls[0].tool_name, "grep_search")
        self.assertEqual(res2.tool_calls[0].arguments["query"], "def calculate")

        # 3rd call (default echo)
        res3 = mock_p.generate([ChatMessage(role=ChatRole.USER, content="Echo test")])
        self.assertIn("Mock response to: Echo test", res3.content)

    def test_unsupported_provider_raises_value_error(self):
        """Verify attempting to create an unregistered provider raises ValueError."""
        with self.assertRaises(ValueError):
            create_llm_provider("unsupported_backend_xyz")


if __name__ == "__main__":
    unittest.main()
