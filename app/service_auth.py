"""§12 — Autenticación M2M de aplicaciones por token Bearer.

Una aplicación es un principal de primera clase: un ``Usuario`` con
``tipo='aplicacion'`` (reutiliza RBAC, auditoría y cuota). Se autentica con un
token de API, NO con contraseña: una máquina acabaría guardando la contraseña
en claro. Propiedades del token (ver docs/DECISIONES_pendientes.md §12):

- Alta entropía (``secrets.token_urlsafe(32)``) con prefijo identificable
  ``odm_app_`` para escaneo de secretos.
- En reposo solo el HASH (sha256); el secreto en claro se muestra una sola vez.
- Comparación en TIEMPO CONSTANTE (``hmac.compare_digest``) contra timing.
- Transporte: ``Authorization: Bearer <token>`` sobre HTTPS, nunca en URL.
- Ciclo de vida: ``last_used_at``, ``expires_at`` opcional, ``revoked_at``
  (revocación inmediata); varios tokens por app para rotar sin corte.
- Rechazo UNIFORME: un fallo no revela si el token era inexistente, revocado o
  expirado.
"""
import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Optional, Tuple

from app.models import ServiceToken, Usuario

PRINCIPAL_APLICACION = "aplicacion"
TOKEN_PREFIX = "odm_app_"
# Nº de caracteres del secreto (tras el prefijo) que se guardan en claro como
# localizador. No es secreto: sirve para acotar candidatos y para soporte.
_PREFIX_TAIL = 8


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def es_token_de_servicio(token: str) -> bool:
    return bool(token) and token.startswith(TOKEN_PREFIX)


def _localizador(token: str) -> str:
    """Prefijo visible almacenado para localizar el candidato (no secreto)."""
    return token[: len(TOKEN_PREFIX) + _PREFIX_TAIL]


def coincide(stored_hash: str, presentado: str) -> bool:
    """Comparación en tiempo constante del hash almacenado con el presentado."""
    return hmac.compare_digest(stored_hash or "", _hash(presentado or ""))


def emitir_token(db, usuario: Usuario, label: Optional[str] = None,
                 expires_at: Optional[datetime] = None) -> Tuple[ServiceToken, str]:
    """Emite un token para la aplicación y devuelve (fila, secreto_en_claro).

    El secreto en claro SOLO se devuelve aquí (display-once). En reposo queda su
    hash. No se valida aquí el tipo del usuario; las capas de gestión deben
    emitir solo para principales 'aplicacion'.
    """
    secreto = TOKEN_PREFIX + secrets.token_urlsafe(32)
    fila = ServiceToken(
        usuario_id=usuario.id,
        label=label,
        prefix=_localizador(secreto),
        token_hash=_hash(secreto),
        expires_at=expires_at,
    )
    db.add(fila)
    db.commit()
    return fila, secreto


def revocar_token(db, token_id) -> bool:
    fila = db.query(ServiceToken).filter(ServiceToken.id == token_id,
                                         ServiceToken.revoked_at.is_(None)).first()
    if not fila:
        return False
    fila.revoked_at = datetime.utcnow()
    db.commit()
    return True


def rotar_token(db, token_id, label: Optional[str] = None,
                expires_at: Optional[datetime] = None) -> Optional[Tuple[ServiceToken, str]]:
    """Emite un token nuevo para la misma app y revoca el viejo. Sin corte si el
    consumidor adopta el nuevo antes de que el viejo deje de usarse (se revoca
    de inmediato; para solape, emitir y revocar por separado)."""
    viejo = db.query(ServiceToken).filter(ServiceToken.id == token_id).first()
    if not viejo:
        return None
    usuario = viejo.usuario
    nuevo, secreto = emitir_token(db, usuario, label=label or viejo.label, expires_at=expires_at)
    viejo.revoked_at = datetime.utcnow()
    db.commit()
    return nuevo, secreto


def validar_fila(fila, token: str, ahora: Optional[datetime] = None) -> Optional[Usuario]:
    """Valida una fila ServiceToken contra el token presentado (lógica pura).

    Devuelve el principal 'aplicacion' si todo encaja, o None ante cualquier
    fallo (hash no coincide, revocado, expirado, usuario inactivo o no-app).
    """
    ahora = ahora or datetime.utcnow()
    if fila is None or fila.revoked_at is not None:
        return None
    if not coincide(fila.token_hash, token):
        return None
    if fila.expires_at is not None and fila.expires_at <= ahora:
        return None
    usuario = fila.usuario
    if not usuario or not usuario.is_active or usuario.tipo != PRINCIPAL_APLICACION:
        return None
    return usuario


def aplicacion_por_bearer(db, token: str) -> Optional[Usuario]:
    """Resuelve el principal 'aplicacion' a partir de un token Bearer.

    Rechazo uniforme: devuelve None ante cualquier fallo (prefijo inválido, no
    encontrado, revocado, expirado, usuario inactivo o no-aplicacion) sin
    distinguir el motivo. En éxito, marca ``last_used_at``.
    """
    if not es_token_de_servicio(token):
        return None
    candidatos = (
        db.query(ServiceToken)
        .filter(ServiceToken.prefix == _localizador(token),
                ServiceToken.revoked_at.is_(None))
        .all()
    )
    ahora = datetime.utcnow()
    for fila in candidatos:
        usuario = validar_fila(fila, token, ahora)
        if usuario is not None:
            fila.last_used_at = ahora
            db.commit()
            return usuario
    return None


def extraer_bearer(authorization_header: Optional[str]) -> Optional[str]:
    """Extrae el token de un encabezado 'Authorization: Bearer <token>'."""
    if not authorization_header:
        return None
    partes = authorization_header.split(None, 1)
    if len(partes) != 2 or partes[0].lower() != "bearer":
        return None
    return partes[1].strip()
