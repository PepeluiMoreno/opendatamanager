import os
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Resource
from app.manager.fetcher_manager import FetcherManager
import logging

logger = logging.getLogger(__name__)

# Cortesía por publisher: intervalo mínimo (segundos) entre arranques de
# recursos que comparten el mismo publisher, para no martillear un portal
# público cuando varios cron coinciden. Configurable por entorno.
_PUBLISHER_MIN_INTERVAL_S = float(os.environ.get("ODM_PUBLISHER_MIN_INTERVAL_S", "30"))
_publisher_last_start: dict[str, float] = {}
_publisher_lock = threading.Lock()


def _await_publisher_slot(publisher: str | None) -> None:
    """Espera, si hace falta, hasta respetar el intervalo mínimo del publisher."""
    if not publisher or _PUBLISHER_MIN_INTERVAL_S <= 0:
        return
    with _publisher_lock:
        now = time.monotonic()
        last = _publisher_last_start.get(publisher)
        wait = 0.0 if last is None else (last + _PUBLISHER_MIN_INTERVAL_S) - now
        # Reservamos el slot ya (marca el arranque previsto) para que arranques
        # concurrentes del mismo publisher se serialicen correctamente.
        _publisher_last_start[publisher] = max(now, (last or 0) + _PUBLISHER_MIN_INTERVAL_S)
    if wait > 0:
        logger.info(f"Cortesía publisher '{publisher}': esperando {wait:.0f}s")
        time.sleep(wait)


class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()

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
            # Cortesía por publisher antes de arrancar (solo en ejecución programada).
            resource = session.query(Resource).filter(Resource.id == resource_id).first()
            if resource is not None:
                _await_publisher_slot(resource.publisher)
            FetcherManager.run(session, resource_id)
        except Exception as e:
            logger.error(f"Error executing scheduled job for resource {resource_id}: {e}")
        finally:
            session.close()

