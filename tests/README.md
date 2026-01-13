# Tests - OpenDataManager

Este directorio contiene los tests del proyecto OpenDataManager.

## Estructura

```
tests/
├── core/               # Tests del core del sistema
├── fetchers/          # Tests de los fetchers
│   └── test_rest_fetcher.py
├── integration/       # Tests de integración
│   └── test_bdns_resource.py
├── utils/            # Tests de utilidades
│   └── test_url_construction.py
└── README.md         # Este archivo
```

## Instalación de dependencias

Para ejecutar los tests, necesitas instalar pytest:

```bash
pip install pytest pytest-cov
```

## Ejecutar tests

### Todos los tests (excepto lentos e integración)

```bash
pytest
```

### Tests específicos

```bash
# Solo tests de fetchers
pytest tests/fetchers/

# Solo un archivo específico
pytest tests/fetchers/test_rest_fetcher.py

# Solo una clase específica
pytest tests/fetchers/test_rest_fetcher.py::TestRestFetcher

# Solo un test específico
pytest tests/fetchers/test_rest_fetcher.py::TestRestFetcher::test_basic_get_request
```

### Tests por categoría (markers)

```bash
# Solo tests unitarios
pytest -m unit

# Excluir tests de integración
pytest -m "not integration"

# Excluir tests lentos
pytest -m "not slow"

# Solo tests de integración (requieren BD y pueden llamar a APIs externas)
pytest -m integration

# Tests de integración Y lentos
pytest -m "integration and slow"
```

### Opciones útiles

```bash
# Ver más detalles de los tests
pytest -v

# Ver salida print() incluso si los tests pasan
pytest -s

# Parar en el primer fallo
pytest -x

# Ejecutar solo tests que fallaron la última vez
pytest --lf

# Ver coverage (requiere pytest-cov)
pytest --cov=app --cov-report=html
```

## Descripción de los tests

### test_rest_fetcher.py

Tests unitarios para el `RestFetcher`:
- ✅ Peticiones GET/POST básicas
- ✅ Query parameters como dict y como JSON string
- ✅ Headers personalizados
- ✅ Parsing de respuestas JSON
- ✅ Validación de parámetros requeridos
- ✅ Defaults (método GET, timeout 30s)

### test_bdns_resource.py

Tests de integración para el recurso BDNS:
- ✅ Carga del recurso desde base de datos
- ✅ Validación de parámetros requeridos
- ✅ Construcción de URL con query params
- ✅ Ejecución real contra API (marcado como `@pytest.mark.integration`)

**Nota:** Los tests marcados con `@pytest.mark.integration` y `@pytest.mark.slow`
requieren:
- Conexión a base de datos
- Conexión a internet (para APIs externas)
- Pueden tardar varios segundos

### test_url_construction.py

Tests de utilidades para construcción de URLs:
- ✅ Construcción manual de URLs con query params
- ✅ Parsing de JSON strings
- ✅ Encoding de caracteres especiales
- ✅ Equivalencia entre dict y JSON string

## Añadir nuevos tests

### Convenciones

1. **Nombres de archivos**: `test_*.py`
2. **Nombres de clases**: `Test*`
3. **Nombres de funciones**: `test_*`
4. **Organización**: Agrupar tests relacionados en clases

### Ejemplo de test

```python
import pytest
from app.fetchers.rest import RestFetcher

class TestMyFeature:
    """Descripción de qué se está probando"""

    def test_something(self):
        """Test: Descripción específica del caso de prueba"""
        # Arrange
        params = {"url": "https://api.example.com"}
        fetcher = RestFetcher(params)

        # Act
        result = fetcher.some_method()

        # Assert
        assert result is not None
```

### Markers útiles

```python
@pytest.mark.unit
def test_unit():
    """Test unitario rápido"""
    pass

@pytest.mark.integration
def test_integration():
    """Test que usa BD o APIs externas"""
    pass

@pytest.mark.slow
def test_slow():
    """Test que tarda más de 1 segundo"""
    pass

@pytest.mark.skip(reason="Work in progress")
def test_wip():
    """Test que se salta temporalmente"""
    pass

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_parametrized(input, expected):
    """Test parametrizado - se ejecuta 3 veces"""
    assert input * 2 == expected
```

## CI/CD

En un entorno de CI/CD, puedes configurar:

```yaml
# .github/workflows/tests.yml (ejemplo)
- name: Run unit tests
  run: pytest -m "not integration and not slow"

- name: Run integration tests
  run: pytest -m integration
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

## Coverage

Para ver qué código está cubierto por tests:

```bash
# Generar reporte HTML
pytest --cov=app --cov-report=html

# Ver reporte en navegador
# El reporte se genera en htmlcov/index.html
```

## Troubleshooting

### ImportError: No module named 'app'

Asegúrate de estar en el directorio raíz del proyecto:
```bash
cd c:/Users/Jose/dev/opendatamanager
pytest
```

### Tests de integración fallan

Los tests de integración requieren:
1. Base de datos configurada y con datos
2. Conexión a internet (para APIs externas)
3. Variables de entorno configuradas

Para saltarlos:
```bash
pytest -m "not integration"
```

### Tests lentos

Si los tests tardan mucho:
```bash
# Saltar tests lentos
pytest -m "not slow"

# Ejecutar tests en paralelo (requiere pytest-xdist)
pip install pytest-xdist
pytest -n auto
```
