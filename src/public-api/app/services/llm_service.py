"""LLM service for multi-provider support (Anthropic, OpenAI, Google)"""

import re
from typing import Any, Dict, List, Optional

import httpx
from anthropic import AsyncAnthropic
from app.core.config import settings
from app.services.goat_tools import get_tools_for_provider
from openai import AsyncOpenAI


class LLMService:
    """Handle LLM interactions with multi-provider support"""

    def __init__(self, model: str, user_api_key: Optional[str] = None):
        self.model = model
        self.user_api_key = user_api_key
        self.provider = self._detect_provider(model)

    def _detect_provider(self, model: str) -> str:
        """Detect provider from model name"""
        if model.startswith("claude"):
            return "anthropic"
        elif model.startswith("gpt"):
            return "openai"
        # Google Gemini can appear as "gemini-*" or "models/gemini-*"
        elif (
            model.startswith("gemini")
            or model.startswith("models/gemini")
            or ("gemini" in model)
        ):
            return "google"
        else:
            raise ValueError(f"Unknown model provider: {model}")

    def _validate_google_model(self, model: str) -> None:
        """Validate Google model string format."""
        # Accept friendly names (gemini-*) and full IDs (models/gemini-*)
        if model.startswith("gemini"):
            return
        if re.match(r"^models/gemini-[\w\.-]+$", model):
            return
        raise ValueError(
            f"Invalid Google model string: '{model}'. "
            "Use a discovered ID like 'models/gemini-2.5-flash' "
            "or a friendly name like 'gemini-1.5-flash'."
        )

    def _get_api_key(self) -> str:
        """Get appropriate API key (user's or default)"""
        if self.user_api_key:
            return self.user_api_key

        if self.provider == "anthropic":
            return settings.anthropic_api_key
        elif self.provider == "openai":
            return settings.openai_api_key
        elif self.provider == "google":
            return settings.google_api_key

        raise ValueError(f"No API key configured for {self.provider}")

    def _google_model_candidates(self, model: str) -> List[str]:
        """Return ordered candidate IDs for a given friendly Gemini model name."""
        base_map = {
            "gemini-1.5-flash": [
                "gemini-1.5-flash",
                "gemini-1.5-flash-latest",
                "models/gemini-1.5-flash",
                "models/gemini-1.5-flash-latest",
            ],
            "gemini-1.5-pro": [
                "gemini-1.5-pro",
                "gemini-1.5-pro-latest",
                "models/gemini-1.5-pro",
                "models/gemini-1.5-pro-latest",
            ],
            "gemini-2.0-flash-exp": [
                "gemini-2.0-flash-exp",
                "models/gemini-2.0-flash-exp",
                # Fallbacks
                "gemini-1.5-flash",
                "models/gemini-1.5-flash",
            ],
        }
        return base_map.get(model, [model, f"models/{model}"])

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage and model"""
        pricing = {
            "claude-sonnet-4-5-20241022": {"input": 3.0, "output": 15.0},
            "claude-sonnet-3-5-20241022": {"input": 3.0, "output": 15.0},
            "claude-haiku-3-5-20241022": {"input": 0.80, "output": 4.0},
            "gpt-4o": {"input": 2.50, "output": 10.0},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gemini-1.5-pro": {"input": 1.25, "output": 5.0},
            "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
            "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},  # Free tier
        }

        model_pricing = pricing.get(self.model, {"input": 0, "output": 0})
        cost = (
            input_tokens / 1_000_000 * model_pricing["input"]
            + output_tokens / 1_000_000 * model_pricing["output"]
        )
        return round(cost, 6)

    async def query(self, question: str, mcp_client: Any = None) -> Dict[str, Any]:
        """Execute query with appropriate provider"""
        if self.provider == "anthropic":
            return await self._query_anthropic(question, mcp_client)
        elif self.provider == "openai":
            return await self._query_openai(question, mcp_client)
        elif self.provider == "google":
            return await self._query_google(question, mcp_client)

    async def _query_anthropic(self, question: str, mcp_client: Any) -> Dict[str, Any]:
        """Query using Anthropic Claude"""
        client = AsyncAnthropic(api_key=self._get_api_key())
        tools = get_tools_for_provider("anthropic")

        messages = [{"role": "user", "content": question}]
        total_input_tokens = 0
        total_output_tokens = 0

        # Tool calling loop
        max_iterations = 10
        for _ in range(max_iterations):
            response = await client.messages.create(
                model=self.model, max_tokens=4096, tools=tools, messages=messages
            )

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            if response.stop_reason != "tool_use":
                # Final answer
                answer = next(
                    (
                        block.text
                        for block in response.content
                        if hasattr(block, "text")
                    ),
                    "No response generated",
                )
                break

            # Execute tool calls via MCP
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await self._execute_mcp_tool(
                        mcp_client, block.name, block.input
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        }
                    )

            messages.append({"role": "user", "content": tool_results})
        else:
            answer = "Maximum iterations reached"

        return {
            "answer": answer,
            "tokens": {
                "input": total_input_tokens,
                "output": total_output_tokens,
                "total": total_input_tokens + total_output_tokens,
            },
            "cost_usd": self.calculate_cost(total_input_tokens, total_output_tokens),
        }

    async def _query_openai(self, question: str, mcp_client: Any) -> Dict[str, Any]:
        """Query using OpenAI GPT"""
        client = AsyncOpenAI(api_key=self._get_api_key())
        tools = get_tools_for_provider("openai")

        messages = [{"role": "user", "content": question}]
        total_input_tokens = 0
        total_output_tokens = 0

        max_iterations = 10
        for _ in range(max_iterations):
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
            )

            total_input_tokens += response.usage.prompt_tokens
            total_output_tokens += response.usage.completion_tokens

            message = response.choices[0].message

            if not message.tool_calls:
                # Final answer
                answer = message.content or "No response generated"
                break

            # Execute tool calls
            messages.append(message)

            for tool_call in message.tool_calls:
                import json

                result = await self._execute_mcp_tool(
                    mcp_client,
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments),
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    }
                )
        else:
            answer = "Maximum iterations reached"

        return {
            "answer": answer,
            "tokens": {
                "input": total_input_tokens,
                "output": total_output_tokens,
                "total": total_input_tokens + total_output_tokens,
            },
            "cost_usd": self.calculate_cost(total_input_tokens, total_output_tokens),
        }

    async def _execute_mcp_tool(
        self, mcp_client: Any, tool_name: str, tool_input: Dict[str, Any]
    ) -> Any:
        """Execute MCP tool call"""
        if mcp_client is None:
            # Fallback: direct HTTP call to GoaT API
            return await self._fallback_goat_call(tool_name, tool_input)

        # Map tool names: goat_xxx -> xxx (strip goat_ prefix)
        if tool_name.startswith("goat_"):
            mcp_tool_name = tool_name[5:]  # Remove "goat_" prefix
        else:
            mcp_tool_name = tool_name

        print(f"Calling MCP tool: {mcp_tool_name} (from {tool_name})")

        # Use MCP client - returns dict with "content" key
        result = await mcp_client.call_tool(mcp_tool_name, tool_input)

        # Extract content from MCP response
        if isinstance(result, dict):
            return result.get("content", [])
        return result

    async def _query_google(self, question: str, mcp_client: Any) -> Dict[str, Any]:
        """Query using Google Gemini via REST API with tool calling"""
        # Validate model string early
        self._validate_google_model(self.model)

        # Determine model ID
        if self.model.startswith("models/gemini-"):
            model_id = self.model
        else:
            # Try friendly name candidates
            candidates = self._google_model_candidates(self.model)
            model_id = candidates[0] if candidates else self.model
            # Ensure models/ prefix
            if not model_id.startswith("models/"):
                model_id = f"models/{model_id}"

        # Get tools in Google format
        tools_list = get_tools_for_provider("google")
        tools_config = None
        if tools_list:
            tools_config = {
                "function_declarations": [
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    }
                    for tool in tools_list
                ]
            }

        # Initialize conversation
        api_key = self._get_api_key()
        base_url = "https://generativelanguage.googleapis.com/v1beta"
        url = f"{base_url}/{model_id}:generateContent"

        contents = [{"parts": [{"text": question}], "role": "user"}]
        total_input_tokens = 0
        total_output_tokens = 0

        # Tool calling loop (max 10 iterations)
        for iteration in range(10):
            payload = {"contents": contents}
            if tools_config:
                payload["tools"] = [tools_config]

            # Make HTTP request
            client = httpx.AsyncClient(timeout=60.0)
            try:
                response = await client.post(
                    url,
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )

                # Check for HTTP errors
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error", {}).get("message", "")

                    # Handle specific Google API errors
                    if response.status_code == 429:
                        raise Exception(
                            "Rate limit exceeded. Please wait a moment "
                            "before trying again."
                        )
                    elif response.status_code == 400:
                        if "API_KEY_INVALID" in str(error_data):
                            raise Exception("Invalid Google API key.")
                        raise Exception(f"Bad request: {error_msg}")
                    elif response.status_code == 403:
                        raise Exception(
                            f"Access forbidden: {error_msg}. "
                            "Check your API key permissions."
                        )
                    else:
                        raise Exception(
                            f"Google API error ({response.status_code}): "
                            f"{error_msg}"
                        )

                response.raise_for_status()
                data = response.json()
            finally:
                await client.aclose()

            # Extract token usage
            if "usageMetadata" in data:
                usage = data["usageMetadata"]
                total_input_tokens += usage.get("promptTokenCount", 0)
                total_output_tokens += usage.get("candidatesTokenCount", 0)

            # Check for function calls
            if "candidates" not in data or not data["candidates"]:
                break

            candidate = data["candidates"][0]
            if "content" not in candidate:
                break

            content = candidate["content"]
            parts = content.get("parts", [])

            # Add model response to conversation
            contents.append({"parts": parts, "role": "model"})

            # Check if there are function calls
            function_calls = [p for p in parts if "functionCall" in p]

            if not function_calls:
                # No more function calls, return final answer
                answer_text = "".join(p.get("text", "") for p in parts if "text" in p)
                return {
                    "answer": answer_text,
                    "tokens": {
                        "input": total_input_tokens,
                        "output": total_output_tokens,
                        "total": total_input_tokens + total_output_tokens,
                    },
                    "cost_usd": self.calculate_cost(
                        total_input_tokens, total_output_tokens
                    ),
                }

            # Execute function calls
            function_responses = []
            for fc in function_calls:
                call = fc["functionCall"]
                tool_name = call["name"]
                tool_args = call.get("args", {})

                print(f"Executing tool: {tool_name} with args: {tool_args}")

                # Execute tool via MCP
                result = await self._execute_mcp_tool(mcp_client, tool_name, tool_args)

                print(f"Tool result: {result}")

                # Format response for Google
                function_responses.append(
                    {
                        "functionResponse": {
                            "name": tool_name,
                            "response": {"result": str(result)},
                        }
                    }
                )

            # Add function responses to conversation
            contents.append({"parts": function_responses, "role": "user"})

        # Fallback if loop exhausted
        return {
            "answer": "Max tool iterations reached",
            "tokens": {
                "input": total_input_tokens,
                "output": total_output_tokens,
                "total": total_input_tokens + total_output_tokens,
            },
            "cost_usd": self.calculate_cost(total_input_tokens, total_output_tokens),
        }

    async def _fallback_goat_call(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> str:
        """Fallback: call GoaT API directly without MCP"""
        # Map MCP tool names to GoaT API endpoints
        # This is a simplified version - you'd need actual GoaT API
        return f"Tool {tool_name} executed with {tool_input}"
