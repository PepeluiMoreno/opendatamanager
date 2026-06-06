"""Arnés batch de pruebas de recursos.

Recorre los recursos vivos ejecutando una vista previa acotada
(_preview_limit=3) y clasifica el resultado:

  OK            — devuelve filas
  SIN FILAS     — responde pero extrae 0 registros (config rota probable)
  FUENTE CAÍDA  — error de red/HTTP (404, 5xx, timeout, DNS)
  CONFIG ROTA   — error de configuración (parámetro ausente, JSON inválido...)
  BUG           — excepción inesperada del fetcher

Uso:
    DATABASE_URL=... python scripts/arnes_recursos.py [--solo NOMBRE] [--timeout 90]

Sella last_tested_at de cada recurso probado (misma semántica que el botón
de prueba del UI: el sello es del intento, no del éxito).
"""
import argparse
import concurrent.futures as cf
import sys
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models import Resource  # noqa: E402
from app.fetchers.factory import FetcherFactory  # noqa: E402

RED = ("ConnectionError", "ConnectTimeout", "ReadTimeout", "Timeout",
       "SSLError", "NewConnectionError", "MaxRetryError", "HTTPError")


def clasificar(exc: BaseException) -> str:
    nombre = type(exc).__name__
    texto = str(exc)
    import re as _re
    if nombre in RED or _re.search(r"HTTP ?(?:Error )?[45]\d\d|\b[45]\d\d (?:Client|Server) Error", texto):
        return "FUENTE CAÍDA"
    if any(t in texto.lower() for t in ("requerido", "required", "falta", "missing",
                                        "json inválido", "invalid json", "pivot_values")):
        return "CONFIG ROTA"
    return "BUG"


def probar(resource, timeout: int):
    fetcher = FetcherFactory.create_from_resource(
        resource, execution_params={"_preview_limit": "3", "timeout": str(timeout)})
    filas = fetcher.execute()  # fetch → parse → normalize, mismo contrato que la ejecución real
    return len(filas or [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", help="probar solo el recurso cuyo nombre contenga este texto")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--saltar-recientes", type=int, default=0, metavar="MIN",
                    help="omitir recursos probados hace menos de MIN minutos (para trocear pasadas)")
    ap.add_argument("--tope", type=int, default=120, help="tope duro de segundos por recurso")
    ap.add_argument("--paralelo", type=int, default=6)
    args = ap.parse_args()

    db = SessionLocal()
    q = db.query(Resource).filter(Resource.deleted_at.is_(None), Resource.active.is_(True))
    if args.solo:
        q = q.filter(Resource.name.ilike(f"%{args.solo}%"))
    recursos = q.order_by(Resource.name).all()
    if args.saltar_recientes:
        umbral = datetime.utcnow() - timedelta(minutes=args.saltar_recientes)
        recursos = [r for r in recursos if not r.last_tested_at or r.last_tested_at < umbral]
        print(f"(quedan {len(recursos)} sin probar en esta ventana)")

    ids = [r.id for r in recursos]
    db.close()

    def _uno(rid):
        dbl = SessionLocal()
        try:
            r = dbl.get(Resource, rid)
            inicio = datetime.utcnow()
            try:
                with cf.ThreadPoolExecutor(max_workers=1) as ej:
                    n = ej.submit(probar, r, args.timeout).result(timeout=args.tope)
                estado, detalle = ("OK" if n > 0 else "SIN FILAS"), f"{n} filas"
            except cf.TimeoutError:
                estado, detalle = "FUENTE CAÍDA", f"tope de {args.tope}s superado"
            except Exception as e:  # noqa: BLE001 — el arnés clasifica, no muere
                estado = clasificar(e)
                detalle = f"{type(e).__name__}: {str(e)[:140]}"
                if estado == "BUG":
                    detalle += " | " + traceback.format_exc().splitlines()[-2][:100]
            dur = (datetime.utcnow() - inicio).total_seconds()
            r.last_tested_at = datetime.utcnow()
            dbl.commit()
            return (estado, r.name, f"{dur:.0f}s", detalle)
        finally:
            dbl.close()

    resultados = []
    with cf.ThreadPoolExecutor(max_workers=args.paralelo) as pool:
        for res in pool.map(_uno, ids):
            resultados.append(res)
            estado, nombre, dur, detalle = res
            print(f"[{estado:12}] {nombre[:48]:48} {dur:>5}  {detalle[:90]}", flush=True)
    db = SessionLocal()

    print("\n── Resumen ──")
    for estado in ("OK", "SIN FILAS", "FUENTE CAÍDA", "CONFIG ROTA", "BUG"):
        grupo = [x for x in resultados if x[0] == estado]
        if grupo:
            print(f"{estado}: {len(grupo)}")
            if estado != "OK":
                for _, nombre, _, det in grupo:
                    print(f"   · {nombre} — {det[:110]}")
    db.close()


if __name__ == "__main__":
    main()
