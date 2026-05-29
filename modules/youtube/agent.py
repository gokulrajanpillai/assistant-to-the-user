"""
ATHU Module - YouTube Channel Manager
Script generation, video creation (D-ID/Remotion), and YouTube upload.
NOTE: D-ID and Runway free tiers are limited. Remotion + local TTS is the fully free path.
"""

import logging
from typing import Callable
from modules.base_module import BaseModule

logger = logging.getLogger("athu.youtube")


class YouTubeAgent(BaseModule):
    MODULE_NAME = "youtube"

    def get_tools(self) -> list[tuple[str, dict, Callable]]:
        return [
            (
                "generate_video_script",
                {
                    "name": "generate_video_script",
                    "description": "Generate a YouTube video script for a given topic.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"},
                            "style": {"type": "string", "default": "educational"},
                            "duration_minutes": {"type": "integer", "default": 5},
                        },
                        "required": ["topic"],
                    },
                },
                self.generate_video_script,
            ),
            (
                "get_channel_stats",
                {
                    "name": "get_channel_stats",
                    "description": "Get YouTube channel statistics: views, subscribers, top videos.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
                self.get_channel_stats,
            ),
        ]

    async def generate_video_script(self, topic: str, style: str = "educational", duration_minutes: int = 5) -> str:
        # Script generation happens via LLM orchestrator prompt - this is a placeholder
        return (
            "Script generation request for topic: " + topic + " | Style: " + style
            + " | Duration: " + str(duration_minutes) + " min. "
            "Pass this to the LLM for full script generation. Full pipeline in Phase 3."
        )

    async def get_channel_stats(self) -> str:
        # TODO: Phase 3 - YouTube Data API v3 integration
        return "YouTube API integration pending. Provide youtube_client_id in config.json."
