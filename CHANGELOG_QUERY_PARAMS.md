# Changelog - Soporte de Query Parameters en RestFetcher

**Fecha:** 2026-01-13
**Tipo:** Feature Enhancement + Test Suite

## Resumen

Se ha añadido soporte completo para query parameters en el `RestFetcher`, permitiendo construir URLs completas con parámetros de consulta. Además, se ha creado una suite completa de tests para verificar el funcionamiento.

## Cambios en el código

### 1. RestFetcher actualizado

**Archivo:** `app/fetchers/rest.py`

**Cambios:**
- ✅ Añadido soporte para `query_params` como parámetro
- ✅ Parsing automático de query_params si vienen como JSON string
- ✅ Los query_params se pasan correctamente a `requests.request()` usando el parámetro `params`
- ✅ Import de `json` movido al inicio del módulo

**Antes:**
```python
def fetch(self) -> RawData:
    url = self.params.get("url")
    method = self.params.get("method", "GET").upper()
    headers = self.params.get("headers", {})
    timeout = int(self.params.get("timeout", 30))

    response = requests.request(method, url, headers=headers, timeout=timeout)
    return response.text
```

**Después:**
```python
def fetch(self) -> RawData:
    url = self.params.get("url")
    method = self.params.get("method", "GET").upper()
    headers = self.params.get("headers", {})
    query_params = self.params.get("query_params", {})  # NUEVO
    timeout = int(self.params.get("timeout", 30))

    # Parse headers if they're a JSON string
    if isinstance(headers, str):
        headers = json.loads(headers)

    # Parse query_params if they're a JSON string  # NUEVO
    if isinstance(query_params, str):
        query_params = json.loads(query_params)

    response = requests.request(
        method,
        url,
        headers=headers,
        params=query_params,  # NUEVO
        timeout=timeout
    )
    return response.text
```

## Ejemplo de uso

### Configuración en base de datos

```python
# Resource params
{
    "url": "https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda",
    "method": "get",
    "query_params": '{"page": "0", "pageSize": "100", "order": "numeroConvocatoria", "direccion": "desc", "vpd": "GE"}',
    "timeout": "60"
}
```

### URL resultante

```
https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda?page=0&pageSize=100&order=numeroConvocatoria&direccion=desc&vpd=GE
```

### Ejecución

```python
from app.fetchers.rest import RestFetcher

params = {
    "url": "https://api.example.com/search",
    "query_params": {"page": "0", "size": "100"}  # Puede ser dict o JSON string
}

fetcher = RestFetcher(params)
data = fetcher.execute()  # URL se construye automáticamente con query params
```

## Tests creados

### 1. tests/fetchers/test_rest_fetcher.py

**Tests unitarios para RestFetcher (11 tests):**
- ✅ `test_basic_get_request` - Petición GET básica
- ✅ `test_get_with_query_params_as_dict` - Query params como diccionario
- ✅ `test_get_with_query_params_as_json_string` - Query params como JSON string
- ✅ `test_post_with_headers` - Petición POST con headers
- ✅ `test_headers_as_json_string` - Headers como JSON string
- ✅ `test_missing_url_raises_error` - Validación de URL requerida
- ✅ `test_parse_json_response` - Parsing de JSON
- ✅ `test_normalize_returns_data_unchanged` - Normalize por defecto
- ✅ `test_default_method_is_get` - Método por defecto GET
- ✅ `test_default_timeout_is_30` - Timeout por defecto 30s
- ✅ `test_method_is_uppercase` - Conversión a mayúsculas

**Cobertura:**
- Parámetros requeridos y opcionales
- Diferentes tipos de entrada (dict, JSON string)
- Validaciones y defaults
- Parsing y normalización

### 2. tests/integration/test_bdns_resource.py

**Tests de integración para recurso BDNS (10 tests):**
- ✅ `test_bdns_resource_exists` - Recurso existe en BD
- ✅ `test_bdns_has_required_params` - Tiene parámetros requeridos
- ✅ `test_bdns_query_params_are_valid_json` - Query params válidos
- ✅ `test_bdns_url_construction` - URL se construye correctamente
- ✅ `test_bdns_fetcher_creation` - Fetcher se crea correctamente
- ✅ `test_bdns_fetch_returns_data` - Obtiene datos reales (marcado como @slow)
- ✅ `test_bdns_query_params_format` - Formato correcto de params
- ✅ `test_bdns_expected_url_with_params` - URL completa esperada

**Características:**
- Tests de integración con base de datos real
- Test de llamada real a API (marcado como `@pytest.mark.integration` y `@pytest.mark.slow`)
- Verificación de estructura de respuesta
- Fixtures reutilizables

### 3. tests/utils/test_url_construction.py

**Tests de utilidades de construcción de URLs (10 tests):**
- ✅ `test_manual_url_construction` - Construcción manual
- ✅ `test_bdns_url_construction` - Caso específico BDNS
- ✅ `test_json_string_parsing` - Parsing de JSON
- ✅ `test_empty_query_params` - URL sin query params
- ✅ `test_special_characters_in_params` - Encoding de caracteres especiales
- ✅ `test_url_with_existing_params` - URL con params existentes
- ✅ `test_dict_vs_json_string_equivalence` - Equivalencia dict vs JSON
- ✅ `test_numeric_values_as_strings` - Valores numéricos
- ✅ `test_boolean_values_as_strings` - Valores booleanos

**Utilidad:**
- Verifica comportamiento de `requests` library
- Documenta casos edge
- Sirve como referencia de implementación

## Configuración de tests

### pytest.ini

Archivo de configuración de pytest con:
- Test discovery patterns
- Markers: `integration`, `slow`, `unit`, `api`
- Output options configuradas
- Asyncio mode

### requirements-dev.txt

Dependencias de desarrollo:
- pytest
- pytest-cov (coverage)
- pytest-asyncio
- pytest-mock
- black, flake8, mypy, isort (code quality)

## Ejecutar los tests

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Ejecutar todos los tests (excepto lentos)
pytest

# Solo tests unitarios
pytest tests/fetchers/test_rest_fetcher.py

# Solo tests de integración
pytest -m integration

# Excluir tests lentos
pytest -m "not slow"

# Con coverage
pytest --cov=app --cov-report=html
```

## Documentación

### tests/README.md

Documentación completa de la suite de tests que incluye:
- Estructura de directorios
- Cómo ejecutar tests
- Descripción de cada archivo de test
- Convenciones y ejemplos
- Troubleshooting

## Impacto en recursos existentes

### BDNS Resource

**Antes:** Solo se usaba la URL base, ignorando query_params
```
https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda
```

**Después:** Se usa la URL completa con todos los parámetros
```
https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda?page=0&pageSize=100&order=numeroConvocatoria&direccion=desc&vpd=GE
```

**Resultado:**
- ✅ Obtiene 100 registros por página (configurado en pageSize)
- ✅ Ordenados por numeroConvocatoria descendente
- ✅ Filtrados por vpd=GE
- ✅ Total: 605,085 elementos en 6,051 páginas

## Retrocompatibilidad

✅ **Totalmente retrocompatible**

Si un resource no tiene `query_params`, el comportamiento es idéntico al anterior:
- `query_params` default es `{}`
- Requests se hace con `params={}` (equivalente a no pasar params)

## Próximos pasos sugeridos

1. **Paginación automática:** Implementar fetcher que itere automáticamente sobre páginas
2. **Rate limiting:** Añadir soporte para rate limiting en fetchers
3. **Request body:** Añadir soporte para POST/PUT con body JSON
4. **Retry logic:** Implementar reintentos automáticos con backoff
5. **Caching:** Añadir cache de respuestas HTTP

## Verificación

Para verificar que todo funciona correctamente:

```bash
# Test de construcción de URL
python -c "
import requests
url = 'https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda'
params = {'page': '0', 'pageSize': '100'}
req = requests.Request('GET', url, params=params)
prepared = req.prepare()
print('URL:', prepared.url)
"

# Test del fetcher con recurso BDNS
python -c "
from app.database import SessionLocal
from app.models import Resource
from app.fetchers.rest import RestFetcher

session = SessionLocal()
bdns = session.query(Resource).filter(Resource.name.like('%BDNS%')).first()
params = {p.key: p.value for p in bdns.params}
fetcher = RestFetcher(params)
data = fetcher.execute()
print(f'Success! Got {len(data[\"content\"])} records' if isinstance(data, dict) else f'Got {len(data)} records')
session.close()
"
```

## Referencias

- [Requests documentation - Query Parameters](https://requests.readthedocs.io/en/latest/user/quickstart/#passing-parameters-in-urls)
- [pytest documentation](https://docs.pytest.org/)
- [pytest markers](https://docs.pytest.org/en/stable/example/markers.html)
