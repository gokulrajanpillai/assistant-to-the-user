"""
ATHU LLM - Router
Routes LLM requests: free-first (Ollama) with premium API fallback.
Routing modes: free_only, prefer_free, premium_for_trading, always_premium
"""

import logging
from enum import Enum

logger = logging.getLogger("athu.llm_router")


class LLMRouting(str, Enum):
    FREE_ONLY = "free_only"
    PREFER_FREE = "prefer_free"
    PREMIUM_FOR_TRADING = "premium_for_trading"
    ALWAYS_PREMIUM = "always_premium"


class LLMRouter:
    """
    Routes LLM calls based on configured strategy.
    Priority: Ollama (local, free) -> OpenAI -> Anthropic
    """

    def __init__(self, config: dict):
        self.config = config
        self.routing = LLMRouting(config["llm"]["routing"])
        self._ollama = None
        self._openai = None
        self._anthropic = None

    @property
    def ollama(self):
        if self._ollama is None:
            from llm.ollama_client import OllamaClient
            self._ollama = OllamaClient(
                base_url=self.config["llm"]["ollama_base_url"],
                model=self.config["llm"]["free_model"],
            )
        return self._ollama

    @property
    def openai_client(self):
        if self._openai is None:
            from openai import AsyncOpenAI
            self._openai = AsyncOpenAI(api_key=self.config["api_keys"]["openai"])
        return self._openai

    @property
    def anthropic_client(self):
        if self._anthropic is None:
            import anthropic
            self._anthropic = anthropic.AsyncAnthropic(
                api_key=self.config["api_keys"]["anthropic"]
            )
        return self._anthropic

    def _should_use_premium(self, module: str) -> bool:
        if self.routing == LLMRouting.ALWAYS_PREMIUM:
            return True
        if self.routing == LLMRouting.FREE_ONLY:
            return False
        if self.routing == LLMRouting.PREMIUM_FOR_TRADING and module == "trading":
            return True
        return False

    async def complete(
        self,
        messages: list[dict],
        module: str = "general",
        tools: list[dict] | None = None,
    ) -> tuple[str | dict, str]:
        """
        Returns (response, llm_used_name).
        response is str for plain text, or message dict for tool calls.
        """
        force_premium = self._should_use_premium(module)

        if not force_premium and self.routing != LLMRouting.ALWAYS_PREMIUM:
            # Try Ollama first
            try:
                ollama_ok = await self.ollama.is_available()
                if ollama_ok:
                    if tools:
                        result = await self.ollama.chat_with_tools(messages, tools)
                        return result, "ollama"
                    else:
                        text = await self.ollama.chat(messages)
                        return text, "ollama"
                else:
                    if self.routing == LLMRouting.FREE_ONLY:
                        raise RuntimeError("Ollama is not running and routing is free_only.")
                    logger.warning("Ollama unavailable, falling back to premium.")
            except RuntimeError:
                raise
            except Exception as e:
                if self.routing == LLMRouting.FREE_ONLY:
                    raise RuntimeError(f"Ollama failed: {e}")
                logger.warning(f"Ollama failed ({e}), trying premium fallback.")

        # Premium: OpenAI
        if self.config["api_keys"].get("openai"):
            try:
                return await self._call_openai(messages, tools, module), "openai"
            except Exception as e:
                logger.warning(f"OpenAI failed ({e}), trying Anthropic.")

        # Premium: Anthropic
        if self.config["api_keys"].get("anthropic"):
            try:
                return await self._call_anthropic(messages), "anthropic"
            except Exception as e:
                logger.error(f"Anthropic also failed: {e}")

        raise RuntimeError(
            "All LLM providers failed. Ensure Ollama is running or provide API keys."
        )

    async def _call_openai(self, messages: list[dict], tools: list[dict] | None, module: str) -> str | dict:
        model = (
            self.config["llm"].get("premium_model_trading", "gpt-4o")
            if module == "trading"
            else "gpt-4o-mini"
        )
        kwargs = {"model": model, "messages": messages, "max_tokens": 1024}
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t["function"]} if "function" in t else t for t in tools]
        response = await self.openai_client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        if tools and choice.message.tool_calls:
            return choice.message
        return choice.message.content

    async def _call_anthropic(self, messages: list[dict]) -> str:
        sys_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m for m in messages if m["role"] != "system"]
        response = await self.anthropic_client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=sys_msg,
            messages=user_msgs,
        )
        return response.content[0].text
