"""
Tests para RestFetcher
Verifica que el fetcher REST construya correctamente URLs con query parameters
"""
import pytest
import json
from unittest.mock import Mock, patch
from app.fetchers.rest import RestFetcher


class TestRestFetcher:
    """Test suite para RestFetcher"""

    def test_basic_get_request(self):
        """Test: Petición GET básica sin query params"""
        params = {
            "url": "https://api.example.com/data",
            "method": "GET",
            "timeout": 30
        }

        fetcher = RestFetcher(params)

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.text = '{"result": "success"}'
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response

            result = fetcher.fetch()

            # Verify request was called correctly
            mock_request.assert_called_once_with(
                'GET',
                'https://api.example.com/data',
                headers={},
                params={},
                timeout=30
            )

            assert result == '{"result": "success"}'

    def test_get_with_query_params_as_dict(self):
        """Test: Petición GET con query params como diccionario"""
        params = {
            "url": "https://api.example.com/search",
            "method": "GET",
            "query_params": {
                "page": "0",
                "pageSize": "100",
                "order": "id"
            },
            "timeout": 30
        }

        fetcher = RestFetcher(params)

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.text = '{"items": []}'
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response

            result = fetcher.fetch()

            # Verify query params were passed correctly
            call_args = mock_request.call_args
            assert call_args[1]['params'] == {
                "page": "0",
                "pageSize": "100",
                "order": "id"
            }

    def test_get_with_query_params_as_json_string(self):
        """Test: Petición GET con query params como string JSON"""
        params = {
            "url": "https://api.example.com/search",
            "method": "GET",
            "query_params": '{"page": "0", "pageSize": "100", "order": "id"}',
            "timeout": 30
        }

        fetcher = RestFetcher(params)

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.text = '{"items": []}'
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response

            result = fetcher.fetch()

            # Verify query params were parsed and passed correctly
            call_args = mock_request.call_args
            assert call_args[1]['params'] == {
                "page": "0",
                "pageSize": "100",
                "order": "id"
            }

    def test_post_with_headers(self):
        """Test: Petición POST con headers personalizados"""
        params = {
            "url": "https://api.example.com/create",
            "method": "POST",
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 30
        }

        fetcher = RestFetcher(params)

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.text = '{"created": true}'
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response

            result = fetcher.fetch()

            # Verify headers were passed correctly
            call_args = mock_request.call_args
            assert call_args[1]['headers'] == {"Authorization": "Bearer token123"}
            assert call_args[0][0] == 'POST'

    def test_headers_as_json_string(self):
        """Test: Headers como string JSON se parsean correctamente"""
        params = {
            "url": "https://api.example.com/data",
            "method": "GET",
            "headers": '{"Authorization": "Bearer token123", "Content-Type": "application/json"}',
            "timeout": 30
        }

        fetcher = RestFetcher(params)

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.text = '{"data": []}'
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response

            result = fetcher.fetch()

            # Verify headers were parsed correctly
            call_args = mock_request.call_args
            assert call_args[1]['headers'] == {
                "Authorization": "Bearer token123",
                "Content-Type": "application/json"
            }

    def test_missing_url_raises_error(self):
        """Test: Sin URL debe lanzar ValueError"""
        params = {
            "method": "GET",
            "timeout": 30
        }

        fetcher = RestFetcher(params)

        with pytest.raises(ValueError, match="El parámetro 'url' es obligatorio"):
            fetcher.fetch()

    def test_parse_json_response(self):
        """Test: Parse de respuesta JSON"""
        params = {
            "url": "https://api.example.com/data",
            "method": "GET"
        }

        fetcher = RestFetcher(params)

        raw_json = '{"items": [{"id": 1}, {"id": 2}], "total": 2}'
        parsed = fetcher.parse(raw_json)

        assert parsed == {"items": [{"id": 1}, {"id": 2}], "total": 2}
        assert len(parsed["items"]) == 2

    def test_normalize_returns_data_unchanged(self):
        """Test: Normalize devuelve datos sin cambios por defecto"""
        params = {
            "url": "https://api.example.com/data",
            "method": "GET"
        }

        fetcher = RestFetcher(params)

        data = {"items": [{"id": 1}, {"id": 2}]}
        normalized = fetcher.normalize(data)

        assert normalized == data

    def test_default_method_is_get(self):
        """Test: Método por defecto es GET"""
        params = {
            "url": "https://api.example.com/data",
            "timeout": 30
        }

        fetcher = RestFetcher(params)

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.text = '{"result": "ok"}'
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response

            fetcher.fetch()

            # Verify default method is GET
            assert mock_request.call_args[0][0] == 'GET'

    def test_default_timeout_is_30(self):
        """Test: Timeout por defecto es 30 segundos"""
        params = {
            "url": "https://api.example.com/data",
            "method": "GET"
        }

        fetcher = RestFetcher(params)

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.text = '{"result": "ok"}'
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response

            fetcher.fetch()

            # Verify default timeout is 30
            assert mock_request.call_args[1]['timeout'] == 30

    def test_method_is_uppercase(self):
        """Test: Método HTTP se convierte a mayúsculas"""
        params = {
            "url": "https://api.example.com/data",
            "method": "post",
            "timeout": 30
        }

        fetcher = RestFetcher(params)

        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.text = '{"created": true}'
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response

            fetcher.fetch()

            # Verify method was converted to uppercase
            assert mock_request.call_args[0][0] == 'POST'
