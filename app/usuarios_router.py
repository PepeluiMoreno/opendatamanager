"""Gestión de usuarios y roles (REST), protegida por la funcionalidad
``usuarios.gestionar``. Incluye salvaguarda anti-bloqueo: nunca puede quedar
el sistema sin al menos un administrador activo.
"""
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import requiere_funcionalidad, revoke_user_sessions
from app.database import get_db
from app.models import Rol, Usuario
from app.passwords import hash_password

ROL_ADMIN = "administrador"



router = APIRouter(
    prefix="/api/usuarios",
    tags=["usuarios"],
    dependencies=[Depends(requiere_funcionalidad("usuarios.gestionar"))],
)


class UsuarioCrear(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    roles: List[str] = []
    is_active: bool = True


class UsuarioActualizar(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None


def _perfil(u: Usuario) -> dict:
    return {
        "id": str(u.id),
        "username": u.username,
        "email": u.email,
        "is_active": u.is_active,
        "roles": [r.code for r in u.roles],
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
    }


def _quedaria_sin_admin(db, excluyendo_id=None, nuevo_estado_roles=None) -> bool:
    """¿La operación dejaría el sistema sin ningún administrador activo?"""
    activos = (
        db.query(Usuario)
        .filter(Usuario.is_active.is_(True))
        .all()
    )
    for u in activos:
        if excluyendo_id is not None and str(u.id) == str(excluyendo_id):
            roles = nuevo_estado_roles if nuevo_estado_roles is not None else [r.code for r in u.roles]
            if ROL_ADMIN in roles:
                return False
            continue
        if any(r.code == ROL_ADMIN for r in u.roles):
            return False
    return True


@router.get("")
def listar(db=Depends(get_db)):
    return [_perfil(u) for u in db.query(Usuario).order_by(Usuario.username).all()]


@router.get("/roles")
def roles(db=Depends(get_db)):
    return [
        {"code": r.code, "nombre": r.nombre, "descripcion": r.descripcion}
        for r in db.query(Rol).order_by(Rol.code).all()
    ]


@router.post("", status_code=201)
def crear(payload: UsuarioCrear, db=Depends(get_db)):
    username = payload.username.strip()
    if not username or not payload.password:
        raise HTTPException(400, "username y password son obligatorios.")
    if db.query(Usuario).filter(Usuario.username == username).first():
        raise HTTPException(409, f"El usuario '{username}' ya existe.")
    roles = db.query(Rol).filter(Rol.code.in_(payload.roles or [])).all()
    u = Usuario(
        username=username,
        email=(payload.email or None),
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
        roles=roles,
    )
    db.add(u)
    db.commit()
    return _perfil(u)


@router.patch("/{usuario_id}")
def actualizar(usuario_id: str, payload: UsuarioActualizar, db=Depends(get_db)):
    u = db.get(Usuario, usuario_id)
    if u is None:
        raise HTTPException(404, "Usuario no encontrado.")

    nuevos_roles = payload.roles if payload.roles is not None else None
    nuevo_activo = payload.is_active if payload.is_active is not None else u.is_active
    roles_si_cambia = nuevos_roles if nuevos_roles is not None else [r.code for r in u.roles]
    if (not nuevo_activo or ROL_ADMIN not in roles_si_cambia) and _quedaria_sin_admin(
        db, excluyendo_id=u.id, nuevo_estado_roles=roles_si_cambia if nuevo_activo else []
    ):
        raise HTTPException(409, "Operación rechazada: dejaría el sistema sin administradores activos.")

    if payload.email is not None:
        u.email = payload.email or None
    if nuevos_roles is not None:
        u.roles = db.query(Rol).filter(Rol.code.in_(nuevos_roles)).all()
    if payload.is_active is not None:
        u.is_active = payload.is_active
        if not u.is_active:
            revoke_user_sessions(db, u.id)
    if payload.password:
        u.password_hash = hash_password(payload.password)
        revoke_user_sessions(db, u.id)
    db.commit()
    return _perfil(u)


@router.delete("/{usuario_id}")
def desactivar(usuario_id: str, db=Depends(get_db)):
    """Desactivación (no borrado físico): conserva trazabilidad y evita huérfanos."""
    u = db.get(Usuario, usuario_id)
    if u is None:
        raise HTTPException(404, "Usuario no encontrado.")
    if _quedaria_sin_admin(db, excluyendo_id=u.id, nuevo_estado_roles=[]):
        raise HTTPException(409, "Operación rechazada: dejaría el sistema sin administradores activos.")
    u.is_active = False
    revoke_user_sessions(db, u.id)
    db.commit()
    return {"ok": True}
