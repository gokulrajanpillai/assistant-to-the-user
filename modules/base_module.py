"""
ATHU Modules - Base Module
Abstract base class that all ATHU capability modules must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseModule(ABC):
    """
    Every ATHU module must inherit from this class and implement:
    - MODULE_NAME: str - unique identifier
    - get_tools(): returns list of (name, schema, callable) tuples
    """

    MODULE_NAME: str = "base"

    def __init__(self, config: dict):
        self.config = config
        self.module_config = config.get("modules", {}).get(self.MODULE_NAME, {})

    @abstractmethod
    def get_tools(self) -> list[tuple[str, dict, Callable]]:
        """
        Return a list of (tool_name, schema_dict, callable) for each tool this module exposes.
        Schema must be OpenAI function-calling compatible.
        """
        ...

    def is_enabled(self) -> bool:
        return self.module_config.get("enabled", False)

    def describe(self) -> str:
        """Human-readable description of this module's capabilities."""
        tools = self.get_tools()
        tool_names = [t[0] for t in tools]
        return f"Module '{self.MODULE_NAME}': {len(tools)} tools: {', '.join(tool_names)}"
