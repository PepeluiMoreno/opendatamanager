"""§12 — Tests de autenticación M2M por token Bearer.

Primitivas puras + validación de fila con dobles (SimpleNamespace), al estilo
del resto de tests RBAC del repo (sin BD).
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

import app.service_auth as sa


# ── Primitivas ───────────────────────────────────────────────────────────

def test_prefijo_y_localizador():
    assert sa.es_token_de_servicio("odm_app_abc")
    assert not sa.es_token_de_servicio("Bearer abc")
    assert not sa.es_token_de_servicio("")
    tok = "odm_app_" + "x" * 40
    loc = sa._localizador(tok)
    assert loc.startswith("odm_app_") and len(loc) == len("odm_app_") + 8


def test_hash_y_comparacion_tiempo_constante():
    tok = "odm_app_secreto"
    h = sa._hash(tok)
    assert len(h) == 64  # sha256 hex
    assert sa.coincide(h, tok)
    assert not sa.coincide(h, "odm_app_otro")
    assert not sa.coincide(h, "")
    assert not sa.coincide("", tok)


def test_extraer_bearer():
    assert sa.extraer_bearer("Bearer odm_app_x") == "odm_app_x"
    assert sa.extraer_bearer("bearer odm_app_x") == "odm_app_x"  # case-insensitive
    assert sa.extraer_bearer("odm_app_x") is None  # sin esquema
    assert sa.extraer_bearer("Basic abc") is None
    assert sa.extraer_bearer(None) is None
    assert sa.extraer_bearer("") is None


# ── validar_fila: el corazón del rechazo uniforme ─────────────────────────

def _fila(token, *, revoked=False, expires=None, activo=True, tipo="aplicacion"):
    return SimpleNamespace(
        token_hash=sa._hash(token),
        revoked_at=datetime.utcnow() if revoked else None,
        expires_at=expires,
        usuario=SimpleNamespace(is_active=activo, tipo=tipo),
    )


def test_validar_fila_ok():
    tok = "odm_app_bueno"
    u = sa.validar_fila(_fila(tok), tok)
    assert u is not None and u.tipo == "aplicacion"


def test_validar_fila_hash_distinto():
    assert sa.validar_fila(_fila("odm_app_a"), "odm_app_b") is None


def test_validar_fila_revocado_expirado():
    tok = "odm_app_x"
    assert sa.validar_fila(_fila(tok, revoked=True), tok) is None
    pasado = datetime.utcnow() - timedelta(seconds=1)
    assert sa.validar_fila(_fila(tok, expires=pasado), tok) is None
    futuro = datetime.utcnow() + timedelta(hours=1)
    assert sa.validar_fila(_fila(tok, expires=futuro), tok) is not None


def test_validar_fila_usuario_invalido():
    tok = "odm_app_x"
    assert sa.validar_fila(_fila(tok, activo=False), tok) is None
    # un usuario humano NUNCA debe autenticarse por esta vía
    assert sa.validar_fila(_fila(tok, tipo="humano"), tok) is None
    assert sa.validar_fila(None, tok) is None


# ── emitir_token: display-once y hash en reposo ───────────────────────────

class _FakeDB:
    def __init__(self):
        self.added = []
    def add(self, x):
        self.added.append(x)
    def commit(self):
        pass


def test_emitir_token_display_once_y_hash():
    db = _FakeDB()
    usuario = SimpleNamespace(id="u1")
    fila, secreto = sa.emitir_token(db, usuario, label="CI")
    # el secreto en claro tiene prefijo y entropía
    assert secreto.startswith("odm_app_") and len(secreto) > 40
    # en reposo solo el hash, nunca el secreto
    assert fila.token_hash == sa._hash(secreto)
    assert secreto not in (fila.prefix, fila.token_hash)
    # el prefijo guardado coincide con el localizador del secreto
    assert fila.prefix == sa._localizador(secreto)
    assert fila.label == "CI" and fila.usuario_id == "u1"
    # y un Bearer con ese secreto valida contra la fila emitida (con su principal)
    fila.usuario = SimpleNamespace(is_active=True, tipo="aplicacion")
    assert sa.validar_fila(fila, secreto) is not None
