"""
Tests del camino PLACSP sobre la especie viva: AtomFetcher + field_map (CODICE).

El antiguo AtomPagingFetcher (parser CODICE hardcodeado) fue retirado: la
migración de junio-2026 consolidó PLACSP en la especie 'Feeds ATOM/RSS' con el
preset 'PLACSP CODICE' (field_map). Estos tests validan:
  1. Que AtomFetcher + field_map extrae los campos CODICE de un feed sintético.
  2. Que el streaming opt-in (stream_pages) cede página a página y fija el
     savepoint de reanudación — la única capacidad que aportaba AtomPaging.
  3. Que SIN stream_pages el comportamiento es el histórico (acumular y ceder
     de una vez, sin tocar current_state) — PLACSP intacto.

Sin red ni BD: se inyecta _request con respuestas sintéticas.
"""
import json
import pytest
from app.fetchers.atom import AtomFetcher


# ── Feeds sintéticos estilo PLACSP/CODICE ─────────────────────────────────────

ENTRY_TPL = """
  <entry xmlns="http://www.w3.org/2005/Atom"
         xmlns:cbc="urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2"
         xmlns:cac-place-ext="urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc-place-ext="urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2">
    <title>Contrato de prueba</title>
    <updated>{updated}</updated>
    <link rel="alternate" href="https://contrataciondelestado.es/wps/poc?idEvl={eid}"/>
    <cac-place-ext:ContractFolderStatus>
      <cbc:ContractFolderID>{exp}</cbc:ContractFolderID>
      <cbc-place-ext:ContractFolderStatusCode>RES</cbc-place-ext:ContractFolderStatusCode>
      <cac-place-ext:LocatedContractingParty>
        <cac:Party>
          <cac:PartyName><cbc:Name>Ayuntamiento de Test</cbc:Name></cac:PartyName>
        </cac:Party>
      </cac-place-ext:LocatedContractingParty>
      <cac:ProcurementProject>
        <cbc:Name>Servicio de prueba</cbc:Name>
        <cac:BudgetAmount><cbc:TotalAmount>12100.00</cbc:TotalAmount></cac:BudgetAmount>
      </cac:ProcurementProject>
      <cac:TenderResult>
        <cac:WinningParty>
          <cac:PartyName><cbc:Name>Empresa Ganadora SL</cbc:Name></cac:PartyName>
          <cac:PartyIdentification><cbc:ID>B12345678</cbc:ID></cac:PartyIdentification>
        </cac:WinningParty>
      </cac:TenderResult>
    </cac-place-ext:ContractFolderStatus>
  </entry>"""


def _feed(entries_xml: str, next_href: str = None) -> str:
    next_link = f'<link rel="next" href="{next_href}"/>' if next_href else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        '<title>PLACSP</title>'
        f'{next_link}{entries_xml}'
        '</feed>'
    )


def _entry(exp, eid, updated="2025-06-15T10:00:00.000+02:00"):
    return ENTRY_TPL.format(exp=exp, eid=eid, updated=updated)


# field_map representativo del preset 'PLACSP CODICE' (esquema VIVO)
FIELD_MAP = {
    "expediente": "ContractFolderID",
    "estado": "ContractFolderStatusCode",
    "objeto": "ProcurementProject/Name",
    "importe": "TotalAmount",
    "organo_contratacion": "LocatedContractingParty/PartyName/Name",
    "adjudicatario": "WinningParty/PartyName/Name",
    "nif_adjudicatario": "WinningParty/PartyIdentification/ID",
    "fecha": "updated",
    "url": "link@href",
}


class _FakeResp:
    def __init__(self, text):
        self.text = text
        self.status_code = 200
    def raise_for_status(self):
        pass


def _make(params):
    f = AtomFetcher({"field_map": json.dumps(FIELD_MAP), **params})
    return f


# ── 1. Extracción CODICE vía field_map (mecanismo vivo) ───────────────────────

class TestFieldMapExtraction:
    def test_campos_codice(self):
        f = _make({"url": "http://x", "max_pages": "1"})
        f._request = lambda *a, **k: _FakeResp(_feed(_entry("EXP/2025/001", "abc")))
        records = f.execute()
        assert len(records) == 1
        r = records[0]
        assert r["expediente"] == "EXP/2025/001"
        assert r["estado"] == "RES"
        assert r["objeto"] == "Servicio de prueba"
        assert r["importe"] == "12100.00"
        assert r["organo_contratacion"] == "Ayuntamiento de Test"
        assert r["adjudicatario"] == "Empresa Ganadora SL"
        assert r["nif_adjudicatario"] == "B12345678"
        assert r["url"] == "https://contrataciondelestado.es/wps/poc?idEvl=abc"


# ── 2. Streaming opt-in + savepoint (capacidad absorbida de AtomPaging) ────────

class TestStreamPagesSavepoint:
    def test_cede_por_pagina_y_fija_savepoint(self):
        seq = iter([
            _feed(_entry("E1", "1"), next_href="http://x/p2"),
            _feed(_entry("E2", "2")),  # sin next → fin
        ])
        f = _make({"url": "http://x/p1", "pagination": "rel_next", "stream_pages": "true"})
        f._request = lambda *a, **k: _FakeResp(next(seq))
        chunks = list(f.stream())
        assert len(chunks) == 2, "debe ceder una vez por página"
        assert chunks[0][0]["expediente"] == "E1"
        assert chunks[1][0]["expediente"] == "E2"
        # tras la última página sin next, el savepoint no apunta a reanudar
        assert f.current_state["pages_fetched"] == 2
        assert f.current_state["resume_url"] is None

    def test_reanudacion_desde_resume_state(self):
        seq = iter([_feed(_entry("E2", "2"))])
        f = _make({
            "url": "http://x/p1", "pagination": "rel_next", "stream_pages": "true",
            "_resume_state": json.dumps({"resume_url": "http://x/p2", "pages_fetched": 1}),
        })
        f._request = lambda *a, **k: _FakeResp(next(seq))
        chunks = list(f.stream())
        assert len(chunks) == 1
        assert chunks[0][0]["expediente"] == "E2"
        assert f.current_state["pages_fetched"] == 2


# ── 3. Sin stream_pages: comportamiento histórico (PLACSP intacto) ────────────

class TestAccumulateUnchanged:
    def test_sin_stream_pages_acumula_y_no_toca_savepoint(self):
        seq = iter([_feed(_entry("E1", "1"))])  # una página, sin next
        f = _make({"url": "http://x", "pagination": "rel_next"})  # NO stream_pages
        f._request = lambda *a, **k: _FakeResp(next(seq))
        chunks = list(f.stream())
        assert len(chunks) == 1, "BaseFetcher.stream acumula y cede una sola vez"
        assert chunks[0][0]["expediente"] == "E1"
        # la rama de acumulación NO fija savepoint: current_state queda como al init
        assert f.current_state == {}
