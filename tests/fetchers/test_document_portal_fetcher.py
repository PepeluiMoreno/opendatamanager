import io
import json
from unittest.mock import Mock, patch

import pandas as pd

from app.fetchers.document_portal import DocumentPortalFetcher
from app.fetchers.file_parsers import parse_structured_file


def custom_csv_parser(content: bytes, params: dict, source_name: str, format: str):
    return [{"kind": "custom", "source_name": source_name, "format": format}]


class TestDocumentPortalFetcher:
    def test_parse_structured_file_xlsx(self):
        df = pd.DataFrame([{"Nombre": "Cadiz", "Valor": 3}])
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")

        records = parse_structured_file(buffer.getvalue(), "xlsx", {})

        assert records == [{"nombre": "Cadiz", "valor": "3"}]

    def test_document_portal_fetcher_crawls_and_parses_files(self):
        params = {
            "start_url": "https://example.com/root",
            "max_depth": "1",
            "page_context_selectors": json.dumps({"section": "h1"}),
            "file_link_selector": "a.file",
            "navigation_link_selector": "a.nav",
            "batch_size": "10",
        }
        fetcher = DocumentPortalFetcher(params)

        responses = {
            "https://example.com/root": (
                """
                <html><body>
                  <h1>Root</h1>
                  <a class="nav" href="/reports">Reports</a>
                  <a class="file" href="/files/root.csv">Root CSV</a>
                </body></html>
                """,
                None,
            ),
            "https://example.com/reports": (
                """
                <html><body>
                  <h1>Reports</h1>
                  <a class="file" href="/files/report.csv">Report CSV</a>
                </body></html>
                """,
                None,
            ),
            "https://example.com/files/root.csv": (None, b"name;value\nalpha;1\n"),
            "https://example.com/files/report.csv": (None, b"city;population\ncadiz;2\n"),
        }

        def fake_request(self, method, url, timeout=30, **kwargs):
            text, content = responses[url]
            response = Mock()
            response.raise_for_status = Mock()
            response.text = text or ""
            response.content = content or b""
            return response

        with patch("requests.sessions.Session.request", new=fake_request):
            records = fetcher.execute()

        assert len(records) == 2
        assert records[0]["section"] == "Root"
        assert records[0]["_source_file_name"] == "root.csv"
        assert records[0]["_source_format"] == "csv"
        assert records[1]["section"] == "Reports"
        assert records[1]["city"] == "cadiz"
        assert records[1]["_source_page_url"] == "https://example.com/reports"

    def test_document_portal_fetcher_supports_custom_parser_hook(self):
        params = {
            "start_url": "https://example.com/root",
            "file_link_selector": "a.file",
            "parser_options": json.dumps({
                "csv": {
                    "custom_parser": "tests.fetchers.test_document_portal_fetcher:custom_csv_parser"
                }
            }),
        }
        fetcher = DocumentPortalFetcher(params)

        responses = {
            "https://example.com/root": (
                '<html><body><a class="file" href="/files/special.csv">Special</a></body></html>',
                None,
            ),
            "https://example.com/files/special.csv": (None, b"ignored"),
        }

        def fake_request(self, method, url, timeout=30, **kwargs):
            text, content = responses[url]
            response = Mock()
            response.raise_for_status = Mock()
            response.text = text or ""
            response.content = content or b""
            return response

        with patch("requests.sessions.Session.request", new=fake_request):
            records = fetcher.execute()

        assert records == [{
            "kind": "custom",
            "source_name": "https://example.com/files/special.csv",
            "format": "csv",
            "_source_page_url": "https://example.com/root",
            "_source_depth": 0,
            "_source_file_url": "https://example.com/files/special.csv",
            "_source_file_name": "special.csv",
            "_source_format": "csv",
            "_source_anchor_text": "Special",
        }]
