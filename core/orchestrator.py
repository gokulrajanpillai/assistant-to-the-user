"""
ATHU Core - Orchestrator
Routes user input to the correct module via LLM function-calling.
Manages the plugin registry and conversation flow.
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable

from core.logger import log_interaction

logger = logging.getLogger("athu.orchestrator")


class ModuleRegistry:
    """Registry for all ATHU capability modules."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, module_name: str, tool_name: str, schema: dict, fn: Callable):
        self._tools[tool_name] = {
            "schema": schema,
            "fn": fn,
            "module": module_name,
        }
        logger.debug(f"Registered tool: {tool_name} (module: {module_name})")

    def get_schemas(self) -> list[dict]:
        return [t["schema"] for t in self._tools.values()]

    def get_module_for_tool(self, tool_name: str) -> str:
        return self._tools.get(tool_name, {}).get("module", "unknown")

    async def call(self, tool_name: str, arguments: dict) -> Any:
        if tool_name not in self._tools:
            return f"Unknown tool: {tool_name}"
        fn = self._tools[tool_name]["fn"]
        try:
            if asyncio.iscoroutinefunction(fn):
                return await fn(**arguments)
            return fn(**arguments)
        except Exception as e:
            logger.error(f"Tool {tool_name} error: {e}")
            return f"Tool execution failed: {e}"


class Orchestrator:
    """Central brain — receives input, routes via LLM, executes tools, returns response."""

    def __init__(self, config: dict, llm_router, memory):
        self.config = config
        self.llm = llm_router
        self.memory = memory
        self.registry = ModuleRegistry()

    def register_module(self, module_instance):
        """Register a module. Module must implement .get_tools() and .MODULE_NAME."""
        for name, schema, fn in module_instance.get_tools():
            self.registry.register(module_instance.MODULE_NAME, name, schema, fn)

    async def handle(self, user_input: str, source: str = "voice") -> str:
        start = time.monotonic()
        response_text = ""
        llm_used = "unknown"
        module_used = "general"

        try:
            from llm.prompt_builder import build_system_prompt, build_messages

            memory_context = self.memory.get_context_for_query(user_input)
            system_prompt = build_system_prompt(self.config["user"], memory_context)
            messages = build_messages(
                system_prompt,
                self.memory.short_term.get_history(),
                user_input,
            )

            tools = self.registry.get_schemas()
            result, llm_used = await self.llm.complete(
                messages,
                module=module_used,
                tools=tools or None,
            )

            # Handle tool call vs plain text response
            if isinstance(result, str):
                response_text = result
            else:
                tool_calls = getattr(result, "tool_calls", None) or result.get("tool_calls", [])
                if tool_calls:
                    tc = tool_calls[0]
                    if hasattr(tc, "function"):
                        tool_name = tc.function.name
                        arguments = json.loads(tc.function.arguments)
                    else:
                        tool_name = tc["function"]["name"]
                        arguments = tc["function"]["arguments"]
                        if isinstance(arguments, str):
                            arguments = json.loads(arguments)

                    module_used = self.registry.get_module_for_tool(tool_name)
                    logger.info(f"Tool call: {tool_name}({arguments})")
                    tool_result = await self.registry.call(tool_name, arguments)

                    # Feed tool result back to LLM
                    messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": getattr(tc, "id", "0"),
                        "content": str(tool_result),
                    })
                    response_text, llm_used = await self.llm.complete(
                        messages, module=module_used
                    )
                else:
                    response_text = getattr(result, "content", str(result))

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            response_text = f"I'm afraid I encountered an error, Sir: {e}"

        duration_ms = int((time.monotonic() - start) * 1000)
        self.memory.record_exchange(user_input, response_text)

        await log_interaction(
            source=source,
            user_input=user_input,
            module=module_used,
            response=response_text,
            duration_ms=duration_ms,
            llm_used=llm_used,
        )
        return response_text
