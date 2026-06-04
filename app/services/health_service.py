"""
Salud y frescura por recurso.

Eleva a la superficie lo que un consumidor (p. ej. SIPI) necesita para confiar
en un dataset: cuándo se actualizó por última vez con éxito, qué antigüedad
tiene el dato, la tasa de fallo y si está "vencido" respecto a su programación.

Construido sobre ResourceExecution y Dataset (ya existentes). No requiere
dependencias nuevas: el periodo del cron se deriva con apscheduler, que ya es
dependencia del proyecto.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import Dataset, Resource, ResourceExecution


def _schedule_period_seconds(schedule: Optional[str]) -> Optional[float]:
    """Periodo nominal (segundos) entre dos disparos consecutivos del cron.

    Devuelve None si no hay schedule o no se puede calcular.
    """
    if not schedule:
        return None
    try:
        from apscheduler.triggers.cron import CronTrigger
        trigger = CronTrigger.from_crontab(schedule)
        now = datetime.now(timezone.utc)
        n1 = trigger.get_next_fire_time(None, now)
        if n1 is None:
            return None
        n2 = trigger.get_next_fire_time(n1, n1)
        if n2 is None:
            return None
        return (n2 - n1).total_seconds()
    except Exception:
        return None


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def resource_health(session) -> List[Dict]:
    """Lista de salud por recurso (no incluye recursos soft-borrados)."""
    now = datetime.now(timezone.utc)
    resources = (
        session.query(Resource)
        .filter(Resource.deleted_at.is_(None))
        .order_by(Resource.name)
        .all()
    )

    out: List[Dict] = []
    for res in resources:
        execs = (
            session.query(ResourceExecution)
            .filter(ResourceExecution.resource_id == res.id)
            .order_by(ResourceExecution.started_at.desc())
            .all()
        )
        completed = [e for e in execs if e.status == "completed"]
        failed = [e for e in execs if e.status == "failed"]
        last = execs[0] if execs else None
        last_success = completed[0] if completed else None

        # Antigüedad del dato: preferimos el created_at del último dataset real;
        # si no hay dataset, caemos a la última ejecución con éxito.
        latest_ds = (
            session.query(Dataset)
            .filter(Dataset.resource_id == res.id)
            .filter(Dataset.deleted_at.is_(None))
            .order_by(
                Dataset.major_version.desc(),
                Dataset.minor_version.desc(),
                Dataset.patch_version.desc(),
            )
            .first()
        )
        data_ts = _as_utc(latest_ds.created_at) if latest_ds else _as_utc(
            last_success.completed_at if last_success else None
        )
        data_age_seconds = (now - data_ts).total_seconds() if data_ts else None

        denom = len(completed) + len(failed)
        success_rate = (len(completed) / denom) if denom else None

        period = _schedule_period_seconds(res.schedule)
        # Vencido si nunca produjo dato, o si el dato es más viejo que un periodo
        # (con un 10% de gracia) respecto a su cadencia programada.
        if res.schedule is None:
            is_overdue = None  # sin programación, "vencido" no aplica
        elif data_ts is None:
            is_overdue = True
        elif period is None:
            is_overdue = None
        else:
            is_overdue = data_age_seconds > period * 1.1

        out.append({
            "resource_id": str(res.id),
            "resource_name": res.name,
            "publisher": res.publisher,
            "active": res.active,
            "schedule": res.schedule,
            "expected_period_seconds": period,
            "last_run_at": _as_utc(last.started_at).isoformat() if last and last.started_at else None,
            "last_status": last.status if last else None,
            "last_success_at": _as_utc(last_success.completed_at).isoformat() if last_success and last_success.completed_at else None,
            "latest_version": latest_ds.version_string if latest_ds else None,
            "data_age_seconds": data_age_seconds,
            "is_overdue": is_overdue,
            "total_executions": len(execs),
            "successful_executions": len(completed),
            "failed_executions": len(failed),
            "success_rate": success_rate,
        })
    return out
