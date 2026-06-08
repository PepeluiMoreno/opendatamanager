"""Tests del redactor de datos sensibles y del catálogo de transacciones."""
from types import SimpleNamespace
from app.rbac import (
    MAPA_TRANSACCIONES, es_clave_sensible, redactar_recurso, redactar_ejecucion,
)


def test_claves_sensibles():
    assert es_clave_sensible("api_key") and es_clave_sensible("Authorization")
    assert es_clave_sensible("client_secret") and es_clave_sensible("PASSWORD")
    assert not es_clave_sensible("url") and not es_clave_sensible("rows_selector")


def test_redactar_recurso_param_sensible_y_headers():
    rt = SimpleNamespace(params=[
        SimpleNamespace(param_name="api_key", param_value="SECRETO"),
        SimpleNamespace(param_name="url", param_value="https://x"),
        SimpleNamespace(param_name="headers", param_value={"Authorization": "Bearer abc", "Accept": "json"}),
    ])
    redactar_recurso(rt)
    assert rt.params[0].param_value == "•••redactado•••"
    assert rt.params[1].param_value == "https://x"
    assert rt.params[2].param_value["Authorization"] == "•••redactado•••"
    assert rt.params[2].param_value["Accept"] == "json"


def test_redactar_ejecucion():
    et = SimpleNamespace(execution_params={"token": "abc", "limit": 10})
    redactar_ejecucion(et)
    assert et.execution_params == {"token": "•••redactado•••", "limit": 10}


def test_mapa_cubre_familias_clave():
    # Garantías mínimas de la matriz acordada
    assert MAPA_TRANSACCIONES["delete_resource"] == "recursos.borrar"
    assert MAPA_TRANSACCIONES["create_fetcher"] == "fetchers.gestionar"
    assert MAPA_TRANSACCIONES["execute_resource"] == "ejecuciones.lanzar"
    assert MAPA_TRANSACCIONES["preview_resource_data"] == "recursos.testar"
    # §11/§12: aprobaciones y gestión de tokens
    assert MAPA_TRANSACCIONES["aprobar_recurso"] == "recursos.aprobar"
    assert MAPA_TRANSACCIONES["aprobar_solicitud_ingreso"] == "aplicaciones.aprobar"
    assert MAPA_TRANSACCIONES["rotar_token_aplicacion"] == "aplicaciones.aprobar"
