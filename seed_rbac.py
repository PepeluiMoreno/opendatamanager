"""Seed RBAC idempotente: catálogo de funcionalidades, roles y admin inicial.

Codifica la matriz acordada:
- invitado (sin credenciales): funcionalidades con es_lectura=True
- lector: toda la lectura (incl. sensible)
- operador: lector + definir y testar recursos (sin borrar, sin ejecutar, sin cron)
- administrador: todo

El admin inicial se crea desde ODM_ADMIN_USER / ODM_ADMIN_PASSWORD si no existe.
Pensado para ejecutarse en cada arranque (entrypoint): upserts por code.
"""
import os
import sys

from app.database import SessionLocal
from app.models import Funcionalidad, Rol, Usuario
from app.passwords import hash_password

# (code, nombre, modulo, es_lectura)
FUNCIONALIDADES = [
    ("panel.ver",             "Ver paneles y estadísticas",        "panel",        True),
    ("recursos.ver",          "Ver recursos (sin datos sensibles)", "recursos",     True),
    ("ejecuciones.ver",       "Ver estado de ejecuciones",         "ejecuciones",  True),
    ("datos.ver",             "Explorar datos públicos",           "datos",        True),
    ("recursos.ver_sensible", "Ver params completos y credenciales", "recursos",   False),
    ("logs.ver",              "Ver logs",                          "ejecuciones",  False),
    ("recursos.crear",        "Crear recursos",                    "recursos",     False),
    ("recursos.editar",       "Editar recursos",                   "recursos",     False),
    ("recursos.testar",       "Probar recursos",                   "recursos",     False),
    ("recursos.borrar",       "Borrar/restaurar recursos",         "recursos",     False),
    ("ejecuciones.lanzar",    "Lanzar ejecuciones",                "ejecuciones",  False),
    ("ejecuciones.parar",     "Parar ejecuciones",                 "ejecuciones",  False),
    ("fetchers.gestionar",    "CRUD de fetchers",                  "fetchers",     False),
    ("programacion.gestionar", "Programación de procesos (cron)",  "programacion", False),
    ("publishers.gestionar",  "Gestionar publishers",              "catalogos",    False),
    ("aplicaciones.gestionar", "Gestionar aplicaciones y suscripciones", "catalogos", False),
    ("usuarios.gestionar",    "Gestionar usuarios y roles",        "usuarios",     False),
    ("settings.gestionar",    "Gestionar settings",                "settings",     False),
]

_LECTURA = ["panel.ver", "recursos.ver", "ejecuciones.ver", "datos.ver",
            "recursos.ver_sensible", "logs.ver"]

ROLES = {
    "lector": ("Lector", "Lectura completa, sin mutaciones", _LECTURA),
    "operador": ("Operador", "Define y prueba recursos",
                 _LECTURA + ["recursos.crear", "recursos.editar", "recursos.testar"]),
    "administrador": ("Administrador", "Acceso total",
                      [c for c, *_ in FUNCIONALIDADES]),
}


def seed(db) -> None:
    # Funcionalidades (upsert por code)
    by_code = {}
    for code, nombre, modulo, es_lectura in FUNCIONALIDADES:
        f = db.query(Funcionalidad).filter_by(code=code).first()
        if f is None:
            f = Funcionalidad(code=code)
            db.add(f)
        f.nombre, f.modulo, f.es_lectura = nombre, modulo, es_lectura
        by_code[code] = f
    db.flush()

    # Roles (upsert por code) con sus funcionalidades exactas
    for code, (nombre, descripcion, perms) in ROLES.items():
        r = db.query(Rol).filter_by(code=code).first()
        if r is None:
            r = Rol(code=code, is_system=True)
            db.add(r)
        r.nombre, r.descripcion, r.is_system = nombre, descripcion, True
        r.funcionalidades = [by_code[p] for p in perms]
    db.commit()

    # Admin inicial desde entorno (no sobreescribe contraseñas existentes)
    username = (os.getenv("ODM_ADMIN_USER") or "").strip()
    password = os.getenv("ODM_ADMIN_PASSWORD") or ""
    if username and password:
        admin_rol = db.query(Rol).filter_by(code="administrador").first()
        u = db.query(Usuario).filter_by(username=username).first()
        if u is None:
            u = Usuario(username=username, password_hash=hash_password(password), is_active=True)
            db.add(u)
            print(f"[seed_rbac] creado admin inicial '{username}'")
        if admin_rol not in u.roles:
            u.roles.append(admin_rol)
        db.commit()
    else:
        print("[seed_rbac] ODM_ADMIN_USER/ODM_ADMIN_PASSWORD no definidos; sin admin inicial")


if __name__ == "__main__":
    if SessionLocal is None:
        print("[seed_rbac] DATABASE_URL no configurada; nada que sembrar")
        sys.exit(0)
    session = SessionLocal()
    try:
        seed(session)
        print("[seed_rbac] OK")
    finally:
        session.close()
