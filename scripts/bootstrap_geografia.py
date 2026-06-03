#!/usr/bin/env python3
"""
Bootstrap de los datasets de geografía.

Los recursos de geografía (CCAA, provincias, municipios, entidades de población)
están sembrados y programados con cron ANUAL, por lo que aún no han producido
ningún dataset y los consumidores no pueden tomar geografía. Este script los
ejecuta UNA vez, en orden de dependencia, para sembrar la primera versión.

Es deliberadamente conservador:
  - Por defecto hace DRY-RUN (no dispara nada). Hay que pasar --confirm.
  - Ejecuta de uno en uno y espera a que termine antes del siguiente, porque
    los municipios dependen de CCAA/provincias y la población de los municipios.

Requisitos:
  ODM_BASE_URL     (por defecto https://odmgr.pepelui.es)
  ODM_ADMIN_TOKEN  token de administración (tras autenticar /graphql)

Uso:
  python scripts/bootstrap_geografia.py            # dry-run: muestra el plan
  ODM_ADMIN_TOKEN=xxxx python scripts/bootstrap_geografia.py --confirm
"""
import argparse
import os
import sys
import time

import requests

# Orden de dependencia (CCAA -> provincias -> municipios -> población/pedanías).
GEO_RESOURCE_NAMES = [
    "España - Comunidades Autónomas (INE)",
    "España - Provincias (INE)",
    "España - Municipios (INE)",
    "Geonames - Entidades de Población (España)",
    "INE - Población por Municipios",
]

POLL_INTERVAL_S = 15
POLL_TIMEOUT_S = 60 * 60  # 1h por recurso


def _gql(base_url: str, token: str, query: str, variables: dict | None = None) -> dict:
    resp = requests.post(
        f"{base_url.rstrip('/')}/graphql",
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]


def resolve_ids(base_url: str, token: str) -> list[tuple[str, str]]:
    data = _gql(base_url, token, "{ resources { id name } }")
    by_name = {r["name"]: r["id"] for r in data["resources"]}
    pairs = []
    for name in GEO_RESOURCE_NAMES:
        if name not in by_name:
            print(f"  ! No encontrado: {name}", file=sys.stderr)
            continue
        pairs.append((name, by_name[name]))
    return pairs


def latest_status(base_url: str, token: str, resource_id: str) -> tuple[str | None, int | None, str | None]:
    q = ("query($id: String!) { resourceExecutions(resourceId: $id) "
         "{ status totalRecords errorMessage } }")
    execs = _gql(base_url, token, q, {"id": resource_id}).get("resourceExecutions") or []
    if not execs:
        return None, None, None
    e = execs[0]
    return e.get("status"), e.get("totalRecords"), e.get("errorMessage")


def execute(base_url: str, token: str, resource_id: str) -> dict:
    m = ("mutation($id: String!) { executeResource(id: $id) "
         "{ success message resourceId } }")
    return _gql(base_url, token, m, {"id": resource_id})["executeResource"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true",
                    help="Ejecuta de verdad. Sin este flag, solo muestra el plan.")
    args = ap.parse_args()

    base_url = os.environ.get("ODM_BASE_URL", "https://odmgr.pepelui.es")
    token = os.environ.get("ODM_ADMIN_TOKEN", "")
    if not token:
        print("ERROR: define ODM_ADMIN_TOKEN.", file=sys.stderr)
        return 2

    print(f"Instancia: {base_url}")
    pairs = resolve_ids(base_url, token)
    if not pairs:
        print("No se resolvió ningún recurso de geografía.", file=sys.stderr)
        return 1

    print("\nPlan de ejecución (en orden):")
    for i, (name, rid) in enumerate(pairs, 1):
        st, _, _ = latest_status(base_url, token, rid)
        print(f"  {i}. {name}  [{rid}]  (última ejecución: {st or 'NINGUNA'})")

    if not args.confirm:
        print("\nDRY-RUN. Repite con --confirm para ejecutar.")
        return 0

    print("\n=== EJECUTANDO ===")
    for name, rid in pairs:
        print(f"\n-> {name}")
        res = execute(base_url, token, rid)
        if not res.get("success"):
            print(f"   ABORTADO: {res.get('message')}", file=sys.stderr)
            return 1
        print(f"   lanzado: {res.get('message')}")

        # Esperar a que termine antes del siguiente (dependencias).
        waited = 0
        while waited < POLL_TIMEOUT_S:
            time.sleep(POLL_INTERVAL_S)
            waited += POLL_INTERVAL_S
            st, total, err = latest_status(base_url, token, rid)
            print(f"   estado: {st} (registros: {total})")
            if st == "completed":
                print(f"   OK: {total} registros")
                break
            if st == "failed":
                print(f"   FALLÓ: {err}", file=sys.stderr)
                return 1
        else:
            print("   TIMEOUT esperando la ejecución.", file=sys.stderr)
            return 1

    print("\nBootstrap de geografía completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
