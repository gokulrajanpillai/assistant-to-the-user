"""
ATHU Module - Advisor Agent
Morning briefing, evening debrief, proactive daily suggestions.
"""

import logging
from datetime import datetime
from typing import Callable
from modules.base_module import BaseModule

logger = logging.getLogger("athu.advisor")


class AdvisorAgent(BaseModule):
    MODULE_NAME = "advisor"

    def get_tools(self) -> list[tuple[str, dict, Callable]]:
        return [
            (
                "get_morning_briefing",
                {
                    "name": "get_morning_briefing",
                    "description": "Generate morning briefing: date, weather, calendar, tasks.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
                self.get_morning_briefing,
            ),
            (
                "get_evening_debrief",
                {
                    "name": "get_evening_debrief",
                    "description": "Start evening debrief: day review, accomplishments, tomorrow planning.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
                self.get_evening_debrief,
            ),
            (
                "get_weather",
                {
                    "name": "get_weather",
                    "description": "Get current weather for the user location.",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": [],
                    },
                },
                self.get_weather,
            ),
        ]

    async def get_morning_briefing(self) -> str:
        now = datetime.now()
        day_str = now.strftime("%A, %d %B %Y")
        return (
            "Good morning, Sir. Today is " + day_str + ". "
            "Calendar and weather integration: Phase 3. Have a productive day."
        )

    async def get_evening_debrief(self) -> str:
        return (
            "Good evening, Sir. How did your day go? "
            "What did you accomplish, and what remains for tomorrow?"
        )

    async def get_weather(self, location: str = None) -> str:
        # TODO: Phase 3 - wttr.in or OpenWeatherMap free tier
        return "Weather integration coming in Phase 3."
