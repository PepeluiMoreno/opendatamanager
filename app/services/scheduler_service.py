from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Resource
from app.manager.fetcher_manager import FetcherManager
import logging

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started.")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down.")

    def add_resource_jobs(self):
        session = SessionLocal()
        try:
            resources = session.query(Resource).filter(Resource.active == True).all()
            for resource in resources:
                if resource.schedule:
                    self.add_job(
                        resource_id=str(resource.id),
                        cron_expression=resource.schedule
                    )
        finally:
            session.close()

    def add_job(self, resource_id: str, cron_expression: str):
        # Remove existing job for this resource if it exists
        job_id = f"resource_job_{resource_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job for resource {resource_id}")

        self.scheduler.add_job(
            self._run_resource_job,
            CronTrigger.from_crontab(cron_expression),
            args=[resource_id],
            id=job_id,
            name=f"Run resource {resource_id}"
        )
        logger.info(f"Added job for resource {resource_id} with schedule: {cron_expression}")

    def _run_resource_job(self, resource_id: str):
        logger.info(f"Executing scheduled job for resource {resource_id}")
        session = SessionLocal()
        try:
            FetcherManager.run(session, resource_id)
        except Exception as e:
            logger.error(f"Error executing scheduled job for resource {resource_id}: {e}")
        finally:
            session.close()

