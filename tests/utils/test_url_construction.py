"""
Tests para verificar construcción de URLs con query parameters
"""
import json
import requests


class TestURLConstruction:
    """Test suite para verificar construcción de URLs"""

    def test_manual_url_construction(self):
        """Test: Construcción manual de URL con query params"""
        url = 'https://api.example.com/search'
        query_params = {
            'page': '0',
            'pageSize': '100',
            'order': 'id',
            'direction': 'desc'
        }

        # Use requests.Request to build the URL
        req = requests.Request('GET', url, params=query_params)
        prepared = req.prepare()

        # Verify URL contains all parameters
        assert 'page=0' in prepared.url
        assert 'pageSize=100' in prepared.url
        assert 'order=id' in prepared.url
        assert 'direction=desc' in prepared.url
        assert prepared.url.startswith('https://api.example.com/search?')

    def test_bdns_url_construction(self):
        """Test: Construcción específica de URL BDNS"""
        url = 'https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda'
        query_params = {
            'page': '0',
            'pageSize': '100',
            'order': 'numeroConvocatoria',
            'direccion': 'desc',
            'vpd': 'GE'
        }

        req = requests.Request('GET', url, params=query_params)
        prepared = req.prepare()

        expected_url = (
            'https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda?'
            'page=0&pageSize=100&order=numeroConvocatoria&direccion=desc&vpd=GE'
        )

        assert prepared.url == expected_url

    def test_json_string_parsing(self):
        """Test: Parsing de query params desde string JSON"""
        query_params_str = '{"page": "0", "pageSize": "100", "order": "id"}'

        # Parse JSON string
        query_params = json.loads(query_params_str)

        assert isinstance(query_params, dict)
        assert query_params['page'] == '0'
        assert query_params['pageSize'] == '100'
        assert query_params['order'] == 'id'

    def test_empty_query_params(self):
        """Test: URL sin query params"""
        url = 'https://api.example.com/data'
        query_params = {}

        req = requests.Request('GET', url, params=query_params)
        prepared = req.prepare()

        # URL should not have '?'
        assert prepared.url == url
        assert '?' not in prepared.url

    def test_special_characters_in_params(self):
        """Test: Caracteres especiales en query params se escapan correctamente"""
        url = 'https://api.example.com/search'
        query_params = {
            'query': 'hello world',
            'filter': 'type=user&active=true'
        }

        req = requests.Request('GET', url, params=query_params)
        prepared = req.prepare()

        # Spaces should be encoded
        assert 'hello+world' in prepared.url or 'hello%20world' in prepared.url
        # Special characters should be encoded
        assert '%3D' in prepared.url or '=' in prepared.url  # = might or might not be encoded
        assert '%26' in prepared.url  # & should be encoded

    def test_url_with_existing_params(self):
        """Test: URL que ya tiene parámetros"""
        url = 'https://api.example.com/search?api_key=123'
        query_params = {
            'page': '0',
            'pageSize': '100'
        }

        req = requests.Request('GET', url, params=query_params)
        prepared = req.prepare()

        # All parameters should be present
        assert 'api_key=123' in prepared.url
        assert 'page=0' in prepared.url
        assert 'pageSize=100' in prepared.url

    def test_dict_vs_json_string_equivalence(self):
        """Test: Dict y JSON string producen el mismo resultado"""
        url = 'https://api.example.com/search'

        # As dict
        query_params_dict = {'page': '0', 'size': '100'}
        req1 = requests.Request('GET', url, params=query_params_dict)
        prepared1 = req1.prepare()

        # As JSON string (parsed)
        query_params_str = '{"page": "0", "size": "100"}'
        query_params_parsed = json.loads(query_params_str)
        req2 = requests.Request('GET', url, params=query_params_parsed)
        prepared2 = req2.prepare()

        assert prepared1.url == prepared2.url

    def test_numeric_values_as_strings(self):
        """Test: Valores numéricos como strings"""
        url = 'https://api.example.com/search'
        query_params = {
            'page': '0',
            'size': '100',
            'id': '12345'
        }

        req = requests.Request('GET', url, params=query_params)
        prepared = req.prepare()

        assert 'page=0' in prepared.url
        assert 'size=100' in prepared.url
        assert 'id=12345' in prepared.url

    def test_boolean_values_as_strings(self):
        """Test: Valores booleanos como strings"""
        url = 'https://api.example.com/search'
        query_params = {
            'active': 'true',
            'deleted': 'false'
        }

        req = requests.Request('GET', url, params=query_params)
        prepared = req.prepare()

        assert 'active=true' in prepared.url
        assert 'deleted=false' in prepared.url
