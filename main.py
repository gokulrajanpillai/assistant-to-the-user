"""
ATHU (Assistant to the User) - Main Entry Point
Starts the FastAPI server and audio pipeline daemon.
"""

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

import uvicorn

from core.logger import init_db
from core.server import create_app
from core.orchestrator import Orchestrator
from core.memory import JARVISMemory
from core.scheduler import TaskScheduler
from llm.router import LLMRouter
from voice.audio_pipeline import AudioPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/athu.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("athu.main")


def load_config() -> dict:
    config_path = Path("config.json")
    if not config_path.exists():
        logger.error("config.json not found. Run: python setup.py")
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)


async def main():
    logger.info("=" * 50)
    logger.info("  ATHU - Assistant to the User  |  Starting")
    logger.info("=" * 50)

    config = load_config()

    # Initialise database
    await init_db()

    # Initialise core components
    memory = JARVISMemory()
    llm_router = LLMRouter(config)
    orchestrator = Orchestrator(config, llm_router, memory)

    # Register enabled modules
    _register_modules(orchestrator, config)

    # Initialise scheduler
    scheduler = TaskScheduler(orchestrator, config)
    scheduler.start()

    # Create FastAPI app
    app = create_app(orchestrator, config)

    # Audio pipeline callback
    async def on_transcript(text: str):
        logger.info(f"Voice input: {text}")
        response = await orchestrator.handle(text, source="voice")
        logger.info(f"ATHU: {response}")
        audio_pipeline.speak(response)

    # Start audio pipeline
    audio_pipeline = AudioPipeline(config, on_transcript)
    loop = asyncio.get_event_loop()
    audio_pipeline.start(loop)

    logger.info(f"ATHU server running at http://{config['server']['host']}:{config['server']['port']}")

    # Graceful shutdown
    def shutdown(sig, frame):
        logger.info("Shutting down ATHU...")
        audio_pipeline.stop()
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start server
    server_config = uvicorn.Config(
        app,
        host=config["server"]["host"],
        port=config["server"]["port"],
        log_level="warning",
    )
    server = uvicorn.Server(server_config)
    await server.serve()


def _register_modules(orchestrator: Orchestrator, config: dict):
    modules_cfg = config.get("modules", {})

    if modules_cfg.get("filesystem", {}).get("enabled"):
        from modules.filesystem.agent import FilesystemAgent
        orchestrator.register_module(FilesystemAgent(config))
        logger.info("Module registered: filesystem")

    if modules_cfg.get("websearch", {}).get("enabled"):
        from modules.websearch.agent import WebSearchAgent
        orchestrator.register_module(WebSearchAgent(config))
        logger.info("Module registered: websearch")

    if modules_cfg.get("trading", {}).get("enabled"):
        from modules.trading.agent import TradingAgent
        orchestrator.register_module(TradingAgent(config))
        logger.info("Module registered: trading")

    if modules_cfg.get("youtube", {}).get("enabled"):
        from modules.youtube.agent import YouTubeAgent
        orchestrator.register_module(YouTubeAgent(config))
        logger.info("Module registered: youtube")

    if modules_cfg.get("fitness", {}).get("enabled"):
        from modules.fitness.agent import FitnessAgent
        orchestrator.register_module(FitnessAgent(config))
        logger.info("Module registered: fitness")

    if modules_cfg.get("advisor", {}).get("enabled"):
        from modules.advisor.agent import AdvisorAgent
        orchestrator.register_module(AdvisorAgent(config))
        logger.info("Module registered: advisor")


if __name__ == "__main__":
    asyncio.run(main())

