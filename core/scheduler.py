"""
ATHU Core - Task Scheduler
APScheduler wrapper for proactive, time-triggered module actions.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("athu.scheduler")


class TaskScheduler:
    def __init__(self, orchestrator, config: dict):
        self.orchestrator = orchestrator
        self.config = config
        self._scheduler = AsyncIOScheduler(timezone=config["user"].get("timezone", "UTC"))

    def start(self):
        self._register_jobs()
        self._scheduler.start()
        logger.info("Task scheduler started.")

    def stop(self):
        self._scheduler.shutdown(wait=False)
        logger.info("Task scheduler stopped.")

    def _register_jobs(self):
        modules_cfg = self.config.get("modules", {})

        # Fitness check-ins
        fitness_cfg = modules_cfg.get("fitness", {})
        if fitness_cfg.get("enabled"):
            for time_str in fitness_cfg.get("checkin_times", ["07:00", "20:00"]):
                hour, minute = map(int, time_str.split(":"))
                self._scheduler.add_job(
                    self._fitness_checkin,
                    CronTrigger(hour=hour, minute=minute),
                    id=f"fitness_{time_str}",
                    replace_existing=True,
                )
                logger.info(f"Scheduled fitness check-in at {time_str}")

        # Daily advisor briefing
        advisor_cfg = modules_cfg.get("advisor", {})
        if advisor_cfg.get("enabled"):
            briefing_time = advisor_cfg.get("briefing_time", "07:05")
            debrief_time = advisor_cfg.get("debrief_time", "21:00")

            bh, bm = map(int, briefing_time.split(":"))
            self._scheduler.add_job(
                self._morning_briefing,
                CronTrigger(hour=bh, minute=bm),
                id="morning_briefing",
                replace_existing=True,
            )

            dh, dm = map(int, debrief_time.split(":"))
            self._scheduler.add_job(
                self._evening_debrief,
                CronTrigger(hour=dh, minute=dm),
                id="evening_debrief",
                replace_existing=True,
            )

    async def _fitness_checkin(self):
        hour = datetime.now().hour
        if hour < 12:
            prompt = "It is time for the morning fitness check-in. Ask the user about their sleep and workout plan for today."
        else:
            prompt = "It is time for the evening fitness check-in. Ask the user about their workout and how they are feeling."
        try:
            await self.orchestrator.handle(prompt, source="scheduler")
        except Exception as e:
            logger.error(f"Fitness check-in error: {e}")

    async def _morning_briefing(self):
        prompt = "Generate the morning briefing: date, weather if available, calendar events today, top tasks pending, and a motivational note."
        try:
            await self.orchestrator.handle(prompt, source="scheduler")
        except Exception as e:
            logger.error(f"Morning briefing error: {e}")

    async def _evening_debrief(self):
        prompt = "Initiate the evening debrief: ask the user how their day went, what was accomplished, and what is pending for tomorrow."
        try:
            await self.orchestrator.handle(prompt, source="scheduler")
        except Exception as e:
            logger.error(f"Evening debrief error: {e}")

    def add_one_time_job(self, fn, run_at: datetime, job_id: str):
        self._scheduler.add_job(fn, "date", run_date=run_at, id=job_id, replace_existing=True)
