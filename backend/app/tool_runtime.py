"""Controlled execution of regular Skills and MCP tools."""
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .skills.basic import create_greeting, get_business_information


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SKILL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "skill_create_greeting",
            "description": "Create a greeting for a caller. Use when greeting a caller by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The caller's name, if known.",
                    }
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_get_business_information",
            "description": "Read the configured medical clinic name, services, opening hours, and scheduling restrictions using the regular Python Skill.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
]


def execute_skill(name: str, arguments: dict[str, Any]) -> str:
    """Execute only explicitly registered regular Skills."""
    if name == "skill_create_greeting":
        if set(arguments) - {"name"}:
            raise ValueError("Unsupported greeting arguments.")
        caller_name = arguments.get("name", "there")
        if not isinstance(caller_name, str):
            raise ValueError("The greeting name must be text.")
        result = create_greeting(caller_name)

    elif name == "skill_get_business_information":
        if arguments:
            raise ValueError("This Skill does not accept arguments.")
        result = get_business_information()

    else:
        raise ValueError(f"Unregistered Skill: {name}")

    return json.dumps(result, ensure_ascii=False)


async def run_with_mcp(call_name: str, arguments: dict[str, Any]) -> str:
    """Discover and execute one explicitly permitted MCP tool."""
    allowed_tools = {
        "mcp_get_business_information": "get_business_information",
        "mcp_create_greeting": "create_greeting",
    }

    server_tool_name = allowed_tools.get(call_name)
    if server_tool_name is None:
        raise ValueError(f"Unregistered MCP tool: {call_name}")

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.app.mcp.server"],
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            available = await session.list_tools()
            registered = {
                tool.name: tool
                for tool in available.tools
            }

            if server_tool_name not in registered:
                raise RuntimeError(
                    f"MCP server does not expose {server_tool_name}."
                )

            if server_tool_name == "get_business_information" and arguments:
                raise ValueError("Business information accepts no arguments.")

            if server_tool_name == "create_greeting":
                if set(arguments) - {"name"}:
                    raise ValueError("Unsupported MCP greeting arguments.")
                if "name" in arguments and not isinstance(arguments["name"], str):
                    raise ValueError("The greeting name must be text.")

            result = await session.call_tool(
                server_tool_name,
                arguments=arguments,
            )

            if result.isError:
                raise RuntimeError(f"MCP tool {server_tool_name} failed.")

            content = []
            for item in result.content:
                if hasattr(item, "text"):
                    content.append(item.text)

            if not content:
                return json.dumps({"result": "MCP tool completed."})

            return "\n".join(content)


async def execute_tool(name: str, arguments_json: str) -> str:
    """Validate tool arguments and dispatch to the correct provider."""
    try:
        arguments = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise ValueError("The model supplied invalid JSON arguments.") from exc

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object.")

    if name.startswith("skill_"):
        return await asyncio.to_thread(execute_skill, name, arguments)

    if name.startswith("mcp_"):
        return await run_with_mcp(name, arguments)

    raise ValueError(f"Unknown tool: {name}")
