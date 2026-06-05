#!/usr/bin/env python3
"""Crea (o actualiza) un usuario y le asigna un rol del sistema.

Uso:
    ODM_USER=Miguel ODM_PASSWORD=... python scripts/crear_usuario.py [--rol ejecutor]
    python scripts/crear_usuario.py --user Miguel --password ... --rol ejecutor

Idempotente: si el usuario existe, no pisa su contraseña salvo --reset; siempre
garantiza que tenga el rol indicado. Requiere DATABASE_URL y que seed_rbac haya
creado los roles (el rol 'ejecutor' otorga la capacidad de lanzar/parar ejecuciones).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Rol, Usuario
from app.passwords import hash_password


def crear_usuario(db, username: str, password: str, rol_code: str, reset: bool) -> str:
    rol = db.query(Rol).filter_by(code=rol_code).first()
    if rol is None:
        disponibles = [r.code for r in db.query(Rol).all()]
        raise SystemExit(f"El rol '{rol_code}' no existe. Roles: {disponibles}. "
                         "¿Has ejecutado seed_rbac?")
    u = db.query(Usuario).filter_by(username=username).first()
    accion = "actualizado"
    if u is None:
        if not password:
            raise SystemExit("Usuario nuevo: hace falta contraseña (ODM_PASSWORD o --password).")
        u = Usuario(username=username, password_hash=hash_password(password), is_active=True)
        db.add(u)
        accion = "creado"
    elif reset and password:
        u.password_hash = hash_password(password)
        accion = "actualizado (contraseña reseteada)"
    if rol not in u.roles:
        u.roles.append(rol)
    db.commit()
    return accion


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.getenv("ODM_USER"))
    ap.add_argument("--password", default=os.getenv("ODM_PASSWORD"))
    ap.add_argument("--rol", default=os.getenv("ODM_ROL", "ejecutor"))
    ap.add_argument("--reset", action="store_true", help="Pisar la contraseña si el usuario ya existe")
    args = ap.parse_args()
    if not args.user:
        raise SystemExit("Falta el nombre de usuario (ODM_USER o --user).")
    db = SessionLocal()
    try:
        accion = crear_usuario(db, args.user.strip(), args.password or "", args.rol, args.reset)
        roles = [r.code for r in db.query(Usuario).filter_by(username=args.user.strip()).first().roles]
        print(f"[crear_usuario] '{args.user}' {accion}; roles: {roles}")
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
