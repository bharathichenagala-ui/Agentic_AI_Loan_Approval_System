"""
Base agent: wraps the Anthropic SDK tool-use loop with FastMCP in-process transport.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic
from fastmcp import Client, FastMCP

logger = logging.getLogger(__name__)


class MCPAgent:
    """
    An agent that calls Claude with tools sourced from a FastMCP server.

    Claude decides which tools to call; we execute them via the MCP client
    and feed results back until Claude produces a final text response.
    """

    def __init__(self, mcp_server: FastMCP, system_prompt: str, max_tokens: int = 2048):
        self.mcp_server = mcp_server
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.model = os.getenv("CLAUDE_MODEL", "global.anthropic.claude-sonnet-4-6")
        # AsyncAnthropic is required — sync client blocks the event loop in async LangGraph nodes
        self._anthropic = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    async def run(self, user_message: str) -> str:
        """Execute the agent loop and return Claude's final text response."""
        async with Client(self.mcp_server) as mcp_client:
            mcp_tools = await mcp_client.list_tools()
            tools = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema,
                }
                for t in mcp_tools
            ]

            messages: list[dict[str, Any]] = [
                {"role": "user", "content": user_message}
            ]

            for iteration in range(10):  # safety cap on iterations
                response = await self._anthropic.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=self.system_prompt,
                    tools=tools,
                    messages=messages,
                )
                logger.debug("Claude stop_reason=%s", response.stop_reason)

                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            return block.text
                    return ""

                if response.stop_reason != "tool_use":
                    logger.warning("Unexpected stop_reason: %s", response.stop_reason)
                    break

                # Append assistant message
                messages.append({"role": "assistant", "content": response.content})

                # Execute all tool calls
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    logger.info("Calling MCP tool: %s(%s)", block.name, block.input)
                    try:
                        result = await mcp_client.call_tool(block.name, block.input)
                        # FastMCP 3.x returns CallToolResult — use .data (str) if present,
                        # otherwise fall back to first content block's text
                        if hasattr(result, "data") and result.data is not None:
                            content_text = result.data if isinstance(result.data, str) else json.dumps(result.data)
                        elif hasattr(result, "content") and result.content:
                            content_text = result.content[0].text
                        else:
                            content_text = str(result)
                    except Exception as exc:
                        content_text = json.dumps({"error": str(exc)})

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content_text,
                    })

                messages.append({"role": "user", "content": tool_results})

            raise RuntimeError(f"Agent loop did not reach end_turn after {iteration + 1} iterations")
