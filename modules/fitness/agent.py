"""
ATHU Module - Fitness Agent
Scheduled check-ins, workout logging, and weekly summaries.
"""

import logging
from typing import Callable
from datetime import datetime

from modules.base_module import BaseModule
from core.logger import log_fitness, get_fitness_summary

logger = logging.getLogger("athu.fitness")


class FitnessAgent(BaseModule):
    MODULE_NAME = "fitness"

    def get_tools(self) -> list[tuple[str, dict, Callable]]:
        return [
            (
                "log_fitness_checkin",
                {
                    "name": "log_fitness_checkin",
                    "description": "Log a fitness check-in with sleep quality, workout status, and notes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sleep_quality": {"type": "string", "enum": ["great", "good", "fair", "poor"]},
                            "workout_done": {"type": "boolean"},
                            "workout_type": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                        "required": [],
                    },
                },
                self.log_fitness_checkin,
            ),
            (
                "get_fitness_summary",
                {
                    "name": "get_fitness_summary",
                    "description": "Get a weekly fitness summary showing workout consistency.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer", "description": "Number of days to summarise (default 7)"},
                        },
                        "required": [],
                    },
                },
                self.fitness_summary,
            ),
        ]

    async def log_fitness_checkin(
        self,
        sleep_quality: str = None,
        workout_done: bool = False,
        workout_type: str = None,
        notes: str = None,
    ) -> str:
        await log_fitness(sleep_quality, workout_done, workout_type, notes)
        parts = []
        if sleep_quality:
            parts.append("Sleep: " + sleep_quality)
        if workout_done:
            parts.append("Workout: " + (workout_type or "completed"))
        elif workout_done is False and workout_type is None:
            parts.append("No workout today")
        if notes:
            parts.append("Notes: " + notes)
        return "Fitness check-in logged. " + " | ".join(parts) if parts else "Fitness check-in logged."

    async def fitness_summary(self, days: int = 7) -> str:
        records = await get_fitness_summary(days)
        if not records:
            return "No fitness data found for the past " + str(days) + " days."
        workouts = sum(1 for r in records if r.get("workout_done"))
        total = len(records)
        return (
            "Fitness summary (" + str(days) + " days): "
            + str(workouts) + "/" + str(total) + " workouts completed. "
            + ("Great consistency, Sir!" if workouts >= total * 0.7 else "There is room for improvement, Sir.")
        )
