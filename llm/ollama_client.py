"""
ATHU LLM - Ollama Client
Local LLM inference via Ollama (free, private, runs on-device).
Supports plain chat and function/tool calling.
"""

import json
import logging
import httpx

logger = logging.getLogger("athu.ollama")


class OllamaClient:
    """
    HTTP client for the Ollama local inference server.
    Default: http://localhost:11434
    """

    DEFAULT_OPTIONS = {
        "temperature": 0.7,
        "num_predict": 1024,
        "stop": [],
    }

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                return [m["name"] for m in r.json().get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def chat(self, messages: list[dict], options: dict | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {**self.DEFAULT_OPTIONS, **(options or {})},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]

    async def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> dict:
        """
        Send messages with tool schemas. Returns the raw message dict
        which may contain 'tool_calls' or plain 'content'.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]

    async def generate(self, prompt: str, system: str = "", options: dict | None = None) -> str:
        """Raw generation endpoint (no conversation history)."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {**self.DEFAULT_OPTIONS, **(options or {})},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{self.base_url}/api/generate", json=payload)
            r.raise_for_status()
            return r.json()["response"]
