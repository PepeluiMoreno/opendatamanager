"""Autenticación por sesión opaca (cookie httpOnly) y permisos RBAC.

La sesión vive en BD (revocable al instante). El invitado (sin cookie) recibe
el conjunto de funcionalidades marcadas con ``es_lectura=True``.
"""
import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Set

from fastapi import Request

from app.models import Funcionalidad, Sesion, Usuario
from app.passwords import verify_password

SESSION_COOKIE = "odm_session"
SESSION_DAYS = int(os.getenv("ODM_SESSION_DAYS", "30"))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate(db, username: str, password: str) -> Optional[Usuario]:
    user = db.query(Usuario).filter(Usuario.username == username).first()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db, usuario: Usuario) -> str:
    """Crea una sesión y devuelve el token en claro (solo viaja en la cookie)."""
    token = secrets.token_urlsafe(32)
    db.add(Sesion(
        usuario_id=usuario.id,
        token_hash=_hash_token(token),
        expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS),
    ))
    usuario.last_login_at = datetime.utcnow()
    db.commit()
    return token


def revoke_session(db, token: str) -> None:
    if not token:
        return
    db.query(Sesion).filter(Sesion.token_hash == _hash_token(token)).delete()
    db.commit()


def revoke_user_sessions(db, usuario_id) -> None:
    """Cierra todas las sesiones de un usuario (p. ej. al desactivarlo)."""
    db.query(Sesion).filter(Sesion.usuario_id == usuario_id).delete()
    db.commit()


def get_user_by_token(db, token: str) -> Optional[Usuario]:
    if not token:
        return None
    ses = (
        db.query(Sesion)
        .filter(Sesion.token_hash == _hash_token(token),
                Sesion.expires_at > datetime.utcnow())
        .first()
    )
    if not ses:
        return None
    user = ses.usuario
    if not user or not user.is_active:
        return None
    ses.last_seen_at = datetime.utcnow()
    db.commit()
    return user


def current_user_from_request(db, request: Request) -> Optional[Usuario]:
    return get_user_by_token(db, request.cookies.get(SESSION_COOKIE, ""))


# ── Permisos ─────────────────────────────────────────────────────────────

def user_permissions(usuario: Optional[Usuario]) -> Set[str]:
    """Códigos de funcionalidad concedidos por los roles del usuario."""
    if usuario is None:
        return set()
    perms: Set[str] = set()
    for rol in usuario.roles:
        perms.update(f.code for f in rol.funcionalidades)
    return perms


def guest_permissions(db) -> Set[str]:
    """Funcionalidades visibles para el invitado (es_lectura=True)."""
    rows = db.query(Funcionalidad.code).filter(Funcionalidad.es_lectura.is_(True)).all()
    return {code for (code,) in rows}


def effective_permissions(db, usuario: Optional[Usuario]) -> Set[str]:
    """Permisos efectivos: los del invitado son base común para todos."""
    return guest_permissions(db) | user_permissions(usuario)
