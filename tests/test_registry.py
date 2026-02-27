"""Tests for ToolRegistry."""
import pytest

from tools.registry import ToolRegistry

DUMMY_TOOL = {
    "name": "dummy_tool",
    "description": "A dummy tool for testing",
    "input_schema": {
        "type": "object",
        "properties": {"x": {"type": "string"}},
        "required": ["x"],
    },
}


async def dummy_handler(x: str) -> str:
    return f"handled:{x}"


def test_register_and_list():
    registry = ToolRegistry()
    registry.register(DUMMY_TOOL, dummy_handler)
    tools = registry.get_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "dummy_tool"


def test_has_tool():
    registry = ToolRegistry()
    registry.register(DUMMY_TOOL, dummy_handler)
    assert registry.has_tool("dummy_tool")
    assert not registry.has_tool("nonexistent")


@pytest.mark.asyncio
async def test_dispatch_calls_handler():
    registry = ToolRegistry()
    registry.register(DUMMY_TOOL, dummy_handler)
    result = await registry.dispatch("dummy_tool", {"x": "hello"})
    assert result == "handled:hello"


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_raises():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="Unknown tool"):
        await registry.dispatch("nonexistent", {})


def test_scoped_registries_are_independent():
    """Each agent should get its own ToolRegistry with no cross-domain tools."""
    reg_a = ToolRegistry()
    reg_b = ToolRegistry()

    tool_a = {**DUMMY_TOOL, "name": "tool_a"}
    tool_b = {**DUMMY_TOOL, "name": "tool_b"}

    reg_a.register(tool_a, dummy_handler)
    reg_b.register(tool_b, dummy_handler)

    assert reg_a.has_tool("tool_a")
    assert not reg_a.has_tool("tool_b")
    assert reg_b.has_tool("tool_b")
    assert not reg_b.has_tool("tool_a")
