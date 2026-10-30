"""
MCP Client Module
Connects to the MCP Calculator Server over stdio, manages sessions,
discovers tools, and executes tool calls according to the MCP specification.
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


class MCPCalculatorClient:
    """
    Client interface for interacting with the MCP Calculator Server.
    Maintains stdio communication with the server process.
    """

    def __init__(self, server_script: str = "mcp_server.py"):
        self.server_script = server_script
        self.server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_script],
            env=os.environ.copy()
        )
        self._cached_tools: Optional[List[Dict[str, Any]]] = None

    async def list_tools_async(self) -> List[Dict[str, Any]]:
        """Query the MCP server for available tools and their schemas."""
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_response = await session.list_tools()
                tools_list = []
                for tool in tools_response.tools:
                    tools_list.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema if hasattr(tool, "inputSchema") else getattr(tool, "input_schema", {})
                    })
                self._cached_tools = tools_list
                return tools_list

    async def call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke an MCP tool on the server and return the parsed result.
        """
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                
                # Parse text contents from MCP result
                text_outputs = []
                for content in result.content:
                    if hasattr(content, "text"):
                        text_outputs.append(content.text)
                    elif isinstance(content, dict) and "text" in content:
                        text_outputs.append(content["text"])
                    else:
                        text_outputs.append(str(content))
                
                raw_text = "\n".join(text_outputs)
                try:
                    parsed_json = json.loads(raw_text)
                    return parsed_json
                except json.JSONDecodeError:
                    return {"status": "success", "raw_output": raw_text}

    def list_tools(self) -> List[Dict[str, Any]]:
        """Synchronous wrapper for list_tools_async."""
        return asyncio.run(self.list_tools_async())

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for call_tool_async."""
        return asyncio.run(self.call_tool_async(tool_name, arguments))


if __name__ == "__main__":
    # Quick self-test
    client = MCPCalculatorClient()
    print("Testing MCP client...")
    tools = client.list_tools()
    print(f"Found {len(tools)} tools:")
    for t in tools:
        print(f" - {t['name']}: {t['description'][:60]}...")
    
    res = client.call_tool("calculate", {"expression": "sqrt(256) * 10"})
    print("\nCalculation test:", res)
