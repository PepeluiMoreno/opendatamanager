"""
Autenticación del endpoint de administración.

La API de datos (/graphql/data) y los endpoints REST de SOLO LECTURA permanecen
públicos. Las mutations de administración (/graphql) y los endpoints REST que
modifican o borran estado quedan protegidos por un token de administración.

El token se configura con la variable de entorno ODM_ADMIN_TOKEN. Si no está
definida, la dependencia rechaza toda petición con 503 (fail-closed): es
preferible dejar la administración inaccesible a dejarla abierta.

Cabecera esperada:
    Authorization: Bearer <ODM_ADMIN_TOKEN>
"""
import os
import secrets

from fastapi import Header, HTTPException


def require_admin(authorization: str | None = Header(default=None)) -> None:
    """Dependencia FastAPI que exige un token de administración válido.

    Se aplica a nivel HTTP, de modo que también bloquea la introspección del
    esquema GraphQL (la petición POST entera se rechaza antes de resolverse).
    """
    token = os.environ.get("ODM_ADMIN_TOKEN")
    if not token:
        # Fail-closed: sin token configurado, la administración no se sirve.
        raise HTTPException(
            status_code=503,
            detail="Administración no disponible: ODM_ADMIN_TOKEN no configurado.",
        )

    expected = f"Bearer {token}"
    # compare_digest evita ataques de temporización al comparar el token.
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="No autorizado.")
