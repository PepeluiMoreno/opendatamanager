#!/usr/bin/env python3
"""
Retirada de fuentes de carácter privado de OpenDataManager.

Criterio (decisión de gobernanza): ODM solo aloja datos de organismos públicos o
de colectivos con dependencia de entes públicos (corporaciones de derecho público
como Notariado, Registradores o Colegios profesionales), MÁS fuentes abiertas por
licencia (p. ej. OpenStreetMap, ODbL). El resto —fuentes privadas y scraping de
portales sin autorización— queda fuera de ODM y se trata en el dominio de la app
consumidora (zona confidencial).

Este script hace SOFT-DELETE (reversible: marca deleted_at, conserva historial) de
los resources y publishers indicados, vía la API admin autenticada. Es
conservador: DRY-RUN por defecto; hay que pasar --confirm para ejecutar.

Requisitos:
  ODM_BASE_URL     (por defecto https://odmgr.pepelui.es)
  ODM_ADMIN_TOKEN  token de administración

Uso:
  python scripts/retirar_fuentes_privadas.py                      # dry-run
  ODM_ADMIN_TOKEN=xxx python scripts/retirar_fuentes_privadas.py --confirm
"""
import argparse
import os
import sys

import requests

# Fuentes a retirar de ODM: privadas (no públicas ni de derecho público).
# - Fotocasa (nivel PRIVADO): portal inmobiliario privado.
# - CEE (Conferencia Episcopal Española): entidad privada. Se retira por el
#   criterio estricto; la jerarquía eclesiástica y la taxonomía de entidades
#   religiosas pasan al dominio de SIPI (o se toman del público RER - Min. Justicia,
#   que permanece en ODM). No producía dataset en vivo.
CONFIRMADAS = {
    "resources": [
        "Agencias Inmobiliarias (Fotocasa)",
        "Oferta Inmobiliaria en Venta (Fotocasa)",
        "Diócesis y Entidades Religiosas (CEE)",
    ],
    "publishers_acronimo": ["FOTOCASA", "CEE"],
}


def _gql(base_url, token, query, variables=None):
    r = requests.post(
        f"{base_url.rstrip('/')}/graphql",
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="Ejecuta el soft-delete de verdad.")
    args = ap.parse_args()

    base_url = os.environ.get("ODM_BASE_URL", "https://odmgr.pepelui.es")
    token = os.environ.get("ODM_ADMIN_TOKEN", "")
    if not token:
        print("ERROR: define ODM_ADMIN_TOKEN.", file=sys.stderr)
        return 2

    targets = {
        "resources": list(CONFIRMADAS["resources"]),
        "publishers_acronimo": list(CONFIRMADAS["publishers_acronimo"]),
    }

    res_by_name = {r["name"]: r["id"] for r in _gql(base_url, token, "{ resources { id name } }")["resources"]}
    pub_by_acr = {p["acronimo"]: p["id"] for p in _gql(base_url, token, "{ publishers { id acronimo } }")["publishers"]}

    plan_res = [(n, res_by_name.get(n)) for n in targets["resources"]]
    plan_pub = [(a, pub_by_acr.get(a)) for a in targets["publishers_acronimo"]]

    print(f"Instancia: {base_url}")
    print("\nResources a retirar (soft-delete):")
    for n, rid in plan_res:
        print(f"  - {n}  -> {rid or 'NO ENCONTRADO'}")
    print("Publishers a retirar (soft-delete):")
    for a, pid in plan_pub:
        print(f"  - {a}  -> {pid or 'NO ENCONTRADO'}")

    if not args.confirm:
        print("\nDRY-RUN. Repite con --confirm para ejecutar el soft-delete.")
        return 0

    print("\n=== RETIRANDO (soft-delete, reversible) ===")
    for n, rid in plan_res:
        if not rid:
            continue
        ok = _gql(base_url, token,
                  "mutation($id:String!){ deleteResource(id:$id, hardDelete:false) }",
                  {"id": rid})["deleteResource"]
        print(f"  resource {n}: {'OK' if ok else 'FALLO'}")
    for a, pid in plan_pub:
        if not pid:
            continue
        ok = _gql(base_url, token,
                  "mutation($id:String!){ deletePublisher(id:$id, hardDelete:false) }",
                  {"id": pid})["deletePublisher"]
        print(f"  publisher {a}: {'OK' if ok else 'FALLO'}")
    print("\nHecho. Reversible (deleted_at). Para revertir, restaurar en BD o re-sembrar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
