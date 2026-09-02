"""Concrete Gemini LLM Provider implementation for NexForge Droid.

Conforms to the provider-agnostic LLMProvider interface with full support for:
- Structured Tool Call / Function Calling protocols
- Multi-turn conversation mapping (System, User, Model, Tool Response)
- Token usage & telemetry extraction
- Exponential backoff retry logic for transient errors & rate limits
"""

import asyncio
import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.config import get_settings
from app.llm.base import ChatMessage, ChatRole, LLMProvider, LLMResponse, ToolCallRequest
from app.llm.exceptions import (
    AuthenticationError,
    InvalidRequestError,
    LLMError,
    ModelUnavailableError,
    ProviderTimeoutError,
    RateLimitError,
)

logger = logging.getLogger("nexforge.llm.gemini")

DEFAULT_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    """Google Gemini LLM Provider utilizing the v1beta generateContent API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        api_base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        http_requester: Optional[Callable[[urllib.request.Request, float], Tuple[int, Dict[str, Any]]]] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key or ""
        self.model_name = model_name or settings.default_model or "gemini-2.5-flash"
        self.api_base_url = api_base_url or DEFAULT_GEMINI_ENDPOINT
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._http_requester = http_requester or self._default_http_request

    # --------------------------------------------------------------------------
    # Message & Tool Conversion Helpers
    # --------------------------------------------------------------------------

    def _convert_messages(
        self, messages: List[ChatMessage]
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Converts standard ChatMessage list into Gemini systemInstruction and contents."""
        system_instruction: Optional[Dict[str, Any]] = None
        contents: List[Dict[str, Any]] = []

        for msg in messages:
            if msg.role == ChatRole.SYSTEM:
                # Gemini handles system instructions in a dedicated top-level field
                text_content = msg.content or ""
                system_instruction = {
                    "parts": [{"text": text_content}]
                }
            elif msg.role == ChatRole.USER:
                contents.append({
                    "role": "user",
                    "parts": [{"text": msg.content or ""}],
                })
            elif msg.role == ChatRole.ASSISTANT:
                parts: List[Dict[str, Any]] = []
                if msg.content:
                    parts.append({"text": msg.content})
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        parts.append({
                            "functionCall": {
                                "name": tc.tool_name,
                                "args": tc.arguments if isinstance(tc.arguments, dict) else {},
                            }
                        })
                if not parts:
                    parts.append({"text": ""})
                contents.append({"role": "model", "parts": parts})
            elif msg.role == ChatRole.TOOL:
                # Tool responses are passed with role 'user' (or 'function' depending on API)
                # In Gemini v1beta functionResponse is within user turn parts
                tool_name = msg.name or "tool_result"
                
                # Try parsing content as JSON if it's a string, else encapsulate
                response_payload: Dict[str, Any]
                if isinstance(msg.content, str):
                    try:
                        parsed = json.loads(msg.content)
                        if isinstance(parsed, dict):
                            response_payload = parsed
                        else:
                            response_payload = {"output": parsed}
                    except Exception:
                        response_payload = {"output": msg.content}
                elif isinstance(msg.content, dict):
                    response_payload = msg.content
                else:
                    response_payload = {"output": str(msg.content)}

                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": tool_name,
                            "response": response_payload,
                        }
                    }],
                })

        return system_instruction, contents

    def _convert_tools(
        self, tools: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[Dict[str, Any]]]:
        """Normalizes external tool specifications into Gemini's functionDeclarations."""
        if not tools:
            return None

        declarations: List[Dict[str, Any]] = []

        for tool in tools:
            if not isinstance(tool, dict):
                continue

            # Support OpenAI tool format {"type": "function", "function": {...}}
            if tool.get("type") == "function" and "function" in tool:
                fn = tool["function"]
                declarations.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {}),
                })
            # Support direct declaration {"name": ..., "description": ..., "parameters": ...}
            elif "name" in tool and ("parameters" in tool or "description" in tool):
                declarations.append({
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                })
            # Support pre-wrapped Gemini declarations
            elif "functionDeclarations" in tool:
                return tools

        if not declarations:
            return None

        return [{"functionDeclarations": declarations}]

    # --------------------------------------------------------------------------
    # Response Parsing
    # --------------------------------------------------------------------------

    def _parse_response(self, response_data: Dict[str, Any]) -> LLMResponse:
        """Extracts content, tool calls, token usage, and finish reason from Gemini JSON response."""
        candidates = response_data.get("candidates", [])
        if not candidates:
            # Check for content filtering or empty generation
            prompt_feedback = response_data.get("promptFeedback", {})
            block_reason = prompt_feedback.get("blockReason")
            if block_reason:
                raise LLMError(f"Generation blocked by safety filters: {block_reason}", provider="gemini")
            return LLMResponse(
                content="",
                tool_calls=[],
                model_name=self.model_name,
                finish_reason="EMPTY",
            )

        primary_candidate = candidates[0]
        finish_reason = primary_candidate.get("finishReason", "STOP")
        content_obj = primary_candidate.get("content", {})
        parts = content_obj.get("parts", [])

        text_parts: List[str] = []
        tool_calls: List[ToolCallRequest] = []

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            if "functionCall" in part:
                fc = part["functionCall"]
                fn_name = fc.get("name", "")
                fn_args = fc.get("args", {})
                call_id = f"call_{uuid.uuid4().hex[:12]}"
                tool_calls.append(
                    ToolCallRequest(
                        call_id=call_id,
                        tool_name=fn_name,
                        arguments=fn_args,
                    )
                )

        combined_text = "".join(text_parts) if text_parts else None

        # Extract usage metadata
        usage = response_data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)

        return LLMResponse(
            content=combined_text,
            tool_calls=tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_name=self.model_name,
            finish_reason=finish_reason,
        )

    # --------------------------------------------------------------------------
    # HTTP Execution & Retry Engine
    # --------------------------------------------------------------------------

    def _default_http_request(
        self, req: urllib.request.Request, timeout: float
    ) -> Tuple[int, Dict[str, Any]]:
        """Standard library HTTP executor for Gemini API requests."""
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.getcode()
                body = response.read().decode("utf-8")
                return status_code, json.loads(body)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            try:
                parsed_error = json.loads(error_body)
            except Exception:
                parsed_error = {"raw": error_body}
            return e.code, parsed_error
        except urllib.error.URLError as e:
            raise ProviderTimeoutError(f"Network error contacting Gemini API: {str(e.reason)}", provider="gemini")
        except Exception as e:
            raise LLMError(f"Unexpected connection error: {str(e)}", provider="gemini")

    def _build_request(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: Optional[int],
    ) -> urllib.request.Request:
        """Constructs HTTP POST request to Gemini v1beta endpoint with telemetry headers."""
        if not self.api_key:
            raise AuthenticationError(
                "Gemini API key is missing. Set GEMINI_API_KEY environment variable or pass api_key to GeminiProvider.",
                provider="gemini",
                status_code=401,
            )

        system_instruction, contents = self._convert_messages(messages)
        gemini_tools = self._convert_tools(tools)

        generation_config: Dict[str, Any] = {
            "temperature": temperature,
        }
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction
        if gemini_tools:
            payload["tools"] = gemini_tools

        url = f"{self.api_base_url}/{self.model_name}:generateContent"
        data_bytes = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
            "User-Agent": "aistudio-build",
        }

        return urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

    def _execute_with_retry(
        self, request_factory: Callable[[], urllib.request.Request]
    ) -> LLMResponse:
        """Executes HTTP request with exponential backoff for transient errors & rate limits."""
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                req = request_factory()
                status_code, data = self._http_requester(req, self.timeout)

                if status_code == 200:
                    return self._parse_response(data)

                # Extract detailed error message
                error_info = data.get("error", {}) if isinstance(data, dict) else {}
                err_message = error_info.get("message", str(data))

                if status_code in (401, 403):
                    raise AuthenticationError(
                        f"Authentication failed ({status_code}): {err_message}",
                        provider="gemini",
                        status_code=status_code,
                        raw_response=json.dumps(data),
                    )

                if status_code in (400, 422):
                    raise InvalidRequestError(
                        f"Invalid request ({status_code}): {err_message}",
                        provider="gemini",
                        status_code=status_code,
                        raw_response=json.dumps(data),
                    )

                if status_code == 429:
                    raise RateLimitError(
                        f"Rate limit exceeded (429): {err_message}",
                        provider="gemini",
                        status_code=429,
                        raw_response=json.dumps(data),
                    )

                if status_code in (500, 502, 503, 504):
                    raise ModelUnavailableError(
                        f"Gemini service unavailable ({status_code}): {err_message}",
                        provider="gemini",
                        status_code=status_code,
                        raw_response=json.dumps(data),
                    )

                raise LLMError(
                    f"Unexpected HTTP {status_code}: {err_message}",
                    provider="gemini",
                    status_code=status_code,
                    raw_response=json.dumps(data),
                )

            except (RateLimitError, ModelUnavailableError, ProviderTimeoutError) as err:
                last_exception = err
                if attempt < self.max_retries:
                    # Exponential backoff with small random jitter
                    sleep_time = (self.backoff_factor ** (attempt + 1)) + (random.uniform(0.1, 0.5))
                    logger.warning(
                        "Transient error (%s). Retrying in %.2fs (attempt %d/%d)...",
                        err.message if hasattr(err, "message") else str(err),
                        sleep_time,
                        attempt + 1,
                        self.max_retries,
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error("Max retries exceeded for Gemini request: %s", str(err))
                    raise err
            except (AuthenticationError, InvalidRequestError):
                # Do not retry fatal client/auth errors
                raise
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    sleep_time = (self.backoff_factor ** (attempt + 1)) + (random.uniform(0.1, 0.4))
                    time.sleep(sleep_time)
                else:
                    raise LLMError(f"Request failed after retries: {str(e)}", provider="gemini")

        if last_exception:
            raise last_exception
        raise LLMError("Unknown error during Gemini generation", provider="gemini")

    # --------------------------------------------------------------------------
    # Public Provider Interface
    # --------------------------------------------------------------------------

    def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Synchronously generate a completion or tool call."""
        def make_req():
            return self._build_request(messages, tools, temperature, max_tokens)

        return self._execute_with_retry(make_req)

    async def generate_async(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Asynchronously generate a completion or tool call."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.generate(messages, tools, temperature, max_tokens),
        )
