"""Regresión: paginated_rest no debe reenviar params internos (_-prefijados) a la fuente."""
from app.fetchers.paginated_rest import PaginatedRestFetcher


def test_params_internos_no_se_reenvian():
    params = {
        "url": "https://example.org/api",
        "method": "GET", "page_param": "offset", "page_size_param": "limit",
        "page_size": "1000", "content_field": "result.records", "id_field": "_id",
        "resource_id": "abc-123",                 # legítimo de la fuente -> debe ir
        "_staging_path": "data/staging/x.jsonl",  # interno -> NO debe ir
        "_resume_state": {"page": 3},             # interno -> NO debe ir
        "_discover_mode": "true",                 # interno -> NO debe ir
    }
    fixed_params = PaginatedRestFetcher(params)._build_request_config()[4]
    assert fixed_params.get("resource_id") == "abc-123"
    assert "_staging_path" not in fixed_params
    assert "_resume_state" not in fixed_params
    assert "_discover_mode" not in fixed_params
