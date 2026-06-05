"""
Scheduler para ejecución automática periódica de Resources.
Usa APScheduler con persistencia en PostgreSQL.
"""
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        db_url = os.getenv("DATABASE_URL", "").replace("+psycopg2", "")
        _scheduler = BackgroundScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=db_url, tableschema="opendata")},
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600},
        )
    return _scheduler


def _run_resource(resource_id: str) -> None:
    from app.database import SessionLocal
    from app.manager.fetcher_manager import FetcherManager

    session = SessionLocal()
    try:
        logger.info(f"Scheduled execution: resource {resource_id}")
        FetcherManager.run(session, resource_id)
    except Exception as e:
        logger.error(f"Scheduled execution failed for resource {resource_id}: {e}")
    finally:
        session.close()


def _maintenance() -> None:
    """Job diario: revisa la salud de las fuentes (baja/recuperación por origen)
    y despacha el digest de avisos por email."""
    from app.database import SessionLocal
    from app.services.salud_fuentes import revisar_salud_fuentes
    from app.services.eventos import enviar_digest

    session = SessionLocal()
    try:
        salud = revisar_salud_fuentes(session)
        envio = enviar_digest(session)
        logger.info(f"Mantenimiento: salud={salud} avisos={envio}")
    except Exception as e:
        logger.error(f"Mantenimiento falló: {e}")
    finally:
        session.close()


def sync_schedule(resource_id: str, schedule: str | None) -> None:
    """Registra, actualiza o elimina el job de un resource."""
    scheduler = _get_scheduler()
    job_id = f"resource_{resource_id}"

    if schedule and schedule.strip():
        parts = schedule.strip().split()
        if len(parts) != 5:
            logger.warning(f"Expresión cron inválida para resource {resource_id}: '{schedule}'")
            return
        trigger = CronTrigger(
            minute=parts[0], hour=parts[1], day=parts[2],
            month=parts[3], day_of_week=parts[4]
        )
        scheduler.add_job(
            _run_resource, trigger=trigger,
            id=job_id, args=[resource_id],
            replace_existing=True,
        )
        logger.info(f"Job registrado: {job_id} → '{schedule}'")
    else:
        try:
            scheduler.remove_job(job_id)
            logger.info(f"Job eliminado: {job_id}")
        except Exception:
            pass


def start() -> None:
    """Arranca el scheduler y carga todos los resources con schedule activo."""
    from app.database import SessionLocal
    from app.models import Resource

    scheduler = _get_scheduler()
    session = SessionLocal()
    try:
        resources = session.query(Resource).filter(
            Resource.active == True,
            Resource.schedule != None,
        ).all()
        for resource in resources:
            sync_schedule(str(resource.id), resource.schedule)
        logger.info(f"Scheduler iniciado con {len(resources)} jobs activos")
    finally:
        session.close()

    # Job diario de mantenimiento: salud de fuentes + digest de avisos (08:00).
    scheduler.add_job(
        _maintenance, trigger=CronTrigger(hour=8, minute=0),
        id="mantenimiento_salud_avisos", replace_existing=True,
    )

    scheduler.start()


def stop() -> None:
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")
