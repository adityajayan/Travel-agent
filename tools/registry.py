import inspect
from typing import Any, Callable


class ToolRegistry:
    """Scoped registry of tool definitions and their async handlers."""

    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, tool_def: dict, handler: Callable) -> None:
        name = tool_def["name"]
        self._tools[name] = tool_def
        self._handlers[name] = handler

    def get_tools(self) -> list[dict]:
        return list(self._tools.values())

    async def dispatch(self, tool_name: str, tool_input: dict) -> Any:
        if tool_name not in self._handlers:
            raise ValueError(f"Unknown tool: '{tool_name}'")
        handler = self._handlers[tool_name]
        sig = inspect.signature(handler)
        accepted = {
            k: v for k, v in tool_input.items()
            if k in sig.parameters
        }
        return await handler(**accepted)

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def tool_names(self) -> list[str]:
        return list(self._tools.keys())
