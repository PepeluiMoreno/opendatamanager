"""
Integration test para el recurso BDNS
Verifica que el recurso BDNS se pueda cargar desde la BD y ejecutar correctamente
"""
import pytest
import json
from app.database import SessionLocal
from app.models import Resource
from app.fetchers.rest import RestFetcher


class TestBDNSResource:
    """Test suite de integración para el recurso BDNS"""

    @pytest.fixture
    def db_session(self):
        """Fixture que proporciona una sesión de base de datos"""
        session = SessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def bdns_resource(self, db_session):
        """Fixture que carga el recurso BDNS desde la BD"""
        resource = db_session.query(Resource).filter(
            Resource.name.like('%BDNS%')
        ).first()

        if not resource:
            pytest.skip("BDNS resource not found in database")

        return resource

    def test_bdns_resource_exists(self, bdns_resource):
        """Test: El recurso BDNS existe en la base de datos"""
        assert bdns_resource is not None
        assert 'BDNS' in bdns_resource.name
        assert bdns_resource.fetcher is not None

    def test_bdns_has_required_params(self, bdns_resource):
        """Test: El recurso BDNS tiene los parámetros requeridos"""
        params = {p.key: p.value for p in bdns_resource.params}

        assert 'url' in params
        assert 'method' in params
        assert params['url'] == 'https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda'

    def test_bdns_query_params_are_valid_json(self, bdns_resource):
        """Test: Los query_params del BDNS son JSON válido"""
        params = {p.key: p.value for p in bdns_resource.params}

        if 'query_params' in params:
            query_params_str = params['query_params']
            # Should not raise exception
            query_params = json.loads(query_params_str)

            assert isinstance(query_params, dict)
            assert 'page' in query_params
            assert 'pageSize' in query_params

    def test_bdns_url_construction(self, bdns_resource):
        """Test: Verificar que la URL se construye correctamente"""
        params = {p.key: p.value for p in bdns_resource.params}

        url = params.get('url', '')
        query_params_str = params.get('query_params', '{}')
        query_params = json.loads(query_params_str)

        # Expected parameters
        assert 'page' in query_params
        assert 'pageSize' in query_params
        assert 'order' in query_params
        assert 'direccion' in query_params

        # Verify base URL
        assert url.startswith('https://www.infosubvenciones.es')
        assert 'convocatorias' in url

    def test_bdns_fetcher_creation(self, bdns_resource):
        """Test: Se puede crear un fetcher desde el recurso BDNS"""
        params = {p.key: p.value for p in bdns_resource.params}

        # Should not raise exception
        fetcher = RestFetcher(params)

        assert fetcher is not None
        assert hasattr(fetcher, 'fetch')
        assert hasattr(fetcher, 'parse')
        assert hasattr(fetcher, 'normalize')

    @pytest.mark.integration
    @pytest.mark.slow
    def test_bdns_fetch_returns_data(self, bdns_resource):
        """Test: El fetcher BDNS devuelve datos reales

        Este test requiere conexión a internet y puede ser lento.
        Se salta por defecto, ejecutar con: pytest -m integration
        """
        params = {p.key: p.value for p in bdns_resource.params}
        fetcher = RestFetcher(params)

        # Execute the full pipeline
        try:
            data = fetcher.execute()

            # Verify we got data back
            assert data is not None

            # BDNS returns paginated response with 'content' array
            if isinstance(data, dict) and 'content' in data:
                records = data['content']
                assert isinstance(records, list)
                assert len(records) > 0

                # Verify structure of first record
                first_record = records[0]
                assert 'id' in first_record
                assert 'numeroConvocatoria' in first_record
                assert 'descripcion' in first_record

                # Verify pagination info
                assert 'totalPages' in data
                assert 'totalElements' in data
                assert data['totalElements'] > 0

            elif isinstance(data, list):
                assert len(data) > 0

        except Exception as e:
            pytest.fail(f"Failed to fetch BDNS data: {str(e)}")

    def test_bdns_query_params_format(self, bdns_resource):
        """Test: Verificar formato de query params"""
        params = {p.key: p.value for p in bdns_resource.params}

        if 'query_params' in params:
            query_params_str = params['query_params']
            query_params = json.loads(query_params_str)

            # All values should be strings (for URL encoding)
            for key, value in query_params.items():
                assert isinstance(value, str), f"Query param '{key}' should be string, got {type(value)}"

    def test_bdns_expected_url_with_params(self, bdns_resource):
        """Test: Verificar URL completa esperada"""
        params = {p.key: p.value for p in bdns_resource.params}

        url = params.get('url', '')
        query_params_str = params.get('query_params', '{}')
        query_params = json.loads(query_params_str)

        # Build expected URL (manually for verification)
        base_url = 'https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda'

        assert url == base_url

        # Expected query params
        expected_params = {
            'page': '0',
            'pageSize': '100',
            'order': 'numeroConvocatoria',
            'direccion': 'desc'
        }

        for key, value in expected_params.items():
            assert key in query_params, f"Expected query param '{key}' not found"
            assert query_params[key] == value, f"Query param '{key}' has wrong value"
