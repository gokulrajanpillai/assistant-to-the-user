"""
ATHU LLM - Prompt Builder
Constructs system prompts with ATHU persona, user profile, and memory context.
"""

import json
from datetime import datetime


ATHU_PERSONA = """You are ATHU (Assistant to the User), a personal AI assistant.
Personality: Confident, precise, slightly formal British English. Address the user as "Sir" or by name.
Be proactive, efficient, and concise. Speak in complete but brief sentences.
Do not apologise unnecessarily. When uncertain, state it directly.
You are loyal to your user and prioritise their goals and safety above all else.
You have access to tools — use them when they are the most efficient solution.
Current datetime: {datetime}
User profile:
{user_profile}
"""


def build_system_prompt(user_profile: dict, memory_context: str = "") -> str:
    base = ATHU_PERSONA.format(
        datetime=datetime.now().strftime("%A, %d %B %Y %H:%M"),
        user_profile=json.dumps(user_profile, indent=2),
    )
    if memory_context:
        base += f"\nRelevant context from memory:\n{memory_context}"
    return base


def build_messages(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
) -> list[dict]:
    """Build the messages list for an LLM API call."""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history[-40:])  # last 20 turns = 40 messages
    messages.append({"role": "user", "content": user_message})
    return messages


def build_tool_schema(
    name: str,
    description: str,
    parameters: dict,
) -> dict:
    """Build an OpenAI-compatible function schema for the plugin registry."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": [k for k, v in parameters.items() if v.get("required", False)],
            },
        },
    }
