"""Endpoints de autenticación: /api/auth/login, /logout, /me."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app import auth as auth_svc
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginInput(BaseModel):
    username: str
    password: str


def _me_payload(db, user) -> dict:
    return {
        "autenticado": True,
        "username": user.username,
        "roles": [r.code for r in user.roles],
        "permisos": sorted(auth_svc.effective_permissions(db, user)),
        "uiPrefs": user.ui_prefs or {},
    }


class UiPrefInput(BaseModel):
    key: str
    value: object = None


@router.post("/login")
def login(data: LoginInput, response: Response, db=Depends(get_db)):
    user = auth_svc.authenticate(db, data.username.strip(), data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    token = auth_svc.create_session(db, user)
    response.set_cookie(
        auth_svc.SESSION_COOKIE,
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth_svc.SESSION_DAYS * 86400,
        path="/",
    )
    return _me_payload(db, user)


@router.post("/logout")
def logout(request: Request, response: Response, db=Depends(get_db)):
    auth_svc.revoke_session(db, request.cookies.get(auth_svc.SESSION_COOKIE, ""))
    response.delete_cookie(auth_svc.SESSION_COOKIE, path="/")
    return {"ok": True}


@router.post("/ui-prefs")
def set_ui_pref(data: UiPrefInput, request: Request, db=Depends(get_db)):
    """Fija una preferencia de UI del usuario actual (merge key→valor). Solo
    usuarios humanos autenticados (el invitado no persiste prefs)."""
    user = auth_svc.current_user_from_request(db, request)
    if not user:
        raise HTTPException(status_code=401, detail="Inicia sesión para guardar preferencias.")
    if not data.key:
        raise HTTPException(status_code=400, detail="Falta 'key'.")
    # JSONB sin MutableDict: hay que REASIGNAR un dict nuevo para que SQLAlchemy
    # detecte el cambio.
    prefs = dict(user.ui_prefs or {})
    prefs[data.key] = data.value
    user.ui_prefs = prefs
    db.commit()
    return {"uiPrefs": prefs}


@router.get("/me")
def me(request: Request, db=Depends(get_db)):
    user = auth_svc.current_user_from_request(db, request)
    if user:
        return _me_payload(db, user)
    return {
        "autenticado": False,
        "username": None,
        "roles": [],
        "permisos": sorted(auth_svc.guest_permissions(db)),
        "uiPrefs": {},
    }
