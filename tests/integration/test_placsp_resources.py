"""
Integration tests para los recursos PLACSP (Plataforma de Contratación del Sector Público).

Tests unitarios (sin red):
    pytest tests/integration/test_placsp_resources.py

Tests de integración con red real (lentos):
    pytest tests/integration/test_placsp_resources.py -m integration
"""
import pytest
from app.database import SessionLocal
from app.models import Resource
from app.fetchers.atom_paging import AtomPagingFetcher


LICITACIONES_URL = (
    "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643"
    "/licitacionesPerfilesContratanteCompleto3.atom"
)
CONTRATOS_MENORES_URL = (
    "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_1143"
    "/contratosMenoresPerfilesContratantes.atom"
)

EXPECTED_CODICE_FIELDS = {
    "expediente", "estado", "organo", "nif_organo", "dir3_organo",
    "objeto", "tipo_contrato", "presupuesto_sin_iva", "presupuesto_con_iva",
    "lugar_ejecucion", "cpv", "procedimiento",
    "resultado", "fecha_adjudicacion", "num_ofertas",
    "importe_adjudicacion", "adjudicatario", "nif_adjudicatario",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def licitaciones_resource(db):
    r = db.query(Resource).filter(Resource.name == "PLACSP - Licitaciones").first()
    if not r:
        pytest.skip("Resource 'PLACSP - Licitaciones' not found in database")
    return r


@pytest.fixture(scope="module")
def contratos_resource(db):
    r = db.query(Resource).filter(Resource.name == "PLACSP - Contratos Menores").first()
    if not r:
        pytest.skip("Resource 'PLACSP - Contratos Menores' not found in database")
    return r


# ── Tests de configuración (sin red) ──────────────────────────────────────────

class TestPlacspResourceConfig:

    def test_licitaciones_exists(self, licitaciones_resource):
        assert licitaciones_resource.active is True
        assert licitaciones_resource.fetcher is not None

    def test_licitaciones_params(self, licitaciones_resource):
        params = {p.key: p.value for p in licitaciones_resource.params}
        assert params.get("url") == LICITACIONES_URL
        assert int(params.get("max_pages", 0)) >= 100

    def test_contratos_exists(self, contratos_resource):
        assert contratos_resource.active is True
        assert contratos_resource.fetcher is not None

    def test_contratos_params(self, contratos_resource):
        params = {p.key: p.value for p in contratos_resource.params}
        assert params.get("url") == CONTRATOS_MENORES_URL
        assert int(params.get("max_pages", 0)) >= 100


# ── Tests de normalización (sin red, datos sintéticos) ────────────────────────

class TestNormalizeEntry:

    SAMPLE_ENTRY = {
        "id": "https://contrataciondelestado.es/sindicacion/licitacionesPerfilContratante/12345",
        "title": "Contrato de prueba",
        "updated": "2025-06-15T10:00:00.000+02:00",
        "link": {"@href": "https://contrataciondelestado.es/wps/poc?idEvl=abc"},
        "cac-place-ext:ContractFolderStatus": {
            "cbc:ContractFolderID": "EXP/2025/001",
            "cbc-place-ext:ContractFolderStatusCode": "RES",
            "cac-place-ext:LocatedContractingParty": {
                "cac:Party": {
                    "cac:PartyName": {"cbc:Name": "Ayuntamiento de Test"},
                    "cac:PartyIdentification": [
                        {"cbc:ID": {"@schemeName": "NIF", "#text": "P1234567A"}},
                        {"cbc:ID": {"@schemeName": "DIR3", "#text": "L01234567"}},
                    ],
                }
            },
            "cac:ProcurementProject": {
                "cbc:Name": "Servicio de prueba",
                "cbc:TypeCode": {"@listURI": "...", "#text": "2"},
                "cac:BudgetAmount": {
                    "cbc:TaxExclusiveAmount": {"@currencyID": "EUR", "#text": "10000.00"},
                    "cbc:TotalAmount": {"@currencyID": "EUR", "#text": "12100.00"},
                },
                "cac:RealizedLocation": {"cbc:CountrySubentityCode": "ES61"},
                "cac:RequiredCommodityClassification": {
                    "cbc:ItemClassificationCode": {"@listURI": "...", "#text": "72000000"},
                },
            },
            "cac:TenderingProcess": {
                "cbc:ProcedureCode": {"@listURI": "...", "#text": "1"},
            },
            "cac:TenderResult": {
                "cbc:ResultCode": {"@listURI": "...", "#text": "8"},
                "cbc:AwardDate": "2025-06-10",
                "cbc:ReceivedTenderQuantity": "3",
                "cac:AwardedTenderedProject": {
                    "cac:LegalMonetaryTotal": {
                        "cbc:TaxExclusiveAmount": {"@currencyID": "EUR", "#text": "9800.00"},
                    }
                },
                "cac:WinningParty": {
                    "cac:PartyName": {"cbc:Name": "Empresa Ganadora SL"},
                    "cac:PartyIdentification": {"cbc:ID": {"@schemeName": "NIF", "#text": "B12345678"}},
                },
            },
        },
    }

    def test_all_codice_fields_present(self):
        result = AtomPagingFetcher._normalize_entry(self.SAMPLE_ENTRY)
        missing = EXPECTED_CODICE_FIELDS - set(result.keys())
        assert not missing, f"Campos CODICE ausentes: {missing}"

    def test_atom_envelope_fields(self):
        result = AtomPagingFetcher._normalize_entry(self.SAMPLE_ENTRY)
        assert result["id"] == self.SAMPLE_ENTRY["id"]
        assert result["title"] == "Contrato de prueba"
        assert result["updated"] == "2025-06-15T10:00:00.000+02:00"
        assert result["link"] == "https://contrataciondelestado.es/wps/poc?idEvl=abc"

    def test_expediente_and_estado(self):
        result = AtomPagingFetcher._normalize_entry(self.SAMPLE_ENTRY)
        assert result["expediente"] == "EXP/2025/001"
        assert result["estado"] == "RES"

    def test_organo_and_ids(self):
        result = AtomPagingFetcher._normalize_entry(self.SAMPLE_ENTRY)
        assert result["organo"] == "Ayuntamiento de Test"
        assert result["nif_organo"] == "P1234567A"
        assert result["dir3_organo"] == "L01234567"

    def test_proyecto(self):
        result = AtomPagingFetcher._normalize_entry(self.SAMPLE_ENTRY)
        assert result["objeto"] == "Servicio de prueba"
        assert result["tipo_contrato"] == "2"
        assert result["presupuesto_sin_iva"] == "10000.00"
        assert result["presupuesto_con_iva"] == "12100.00"
        assert result["lugar_ejecucion"] == "ES61"
        assert result["cpv"] == "72000000"

    def test_adjudicacion(self):
        result = AtomPagingFetcher._normalize_entry(self.SAMPLE_ENTRY)
        assert result["fecha_adjudicacion"] == "2025-06-10"
        assert result["num_ofertas"] == "3"
        assert result["importe_adjudicacion"] == "9800.00"
        assert result["adjudicatario"] == "Empresa Ganadora SL"
        assert result["nif_adjudicatario"] == "B12345678"

    def test_raw_xml_content_preserved(self):
        result = AtomPagingFetcher._normalize_entry(self.SAMPLE_ENTRY)
        assert "raw_xml_content" in result
        assert result["raw_xml_content"] is self.SAMPLE_ENTRY

    def test_entry_without_codice_returns_minimal(self):
        entry = {"id": "x", "title": "y", "updated": "2025-01-01T00:00:00Z", "link": {"@href": "http://x"}}
        result = AtomPagingFetcher._normalize_entry(entry)
        assert result["id"] == "x"
        assert "expediente" not in result
        assert "raw_xml_content" in result


# ── Tests de integración con red real ─────────────────────────────────────────

class TestPlacspStreamIntegration:

    @pytest.mark.integration
    def test_licitaciones_stream_first_page(self):
        """Descarga la primera página del feed de licitaciones y valida estructura."""
        f = AtomPagingFetcher({"url": LICITACIONES_URL, "max_pages": "1", "timeout": "60"})
        pages = list(f.stream())
        assert len(pages) == 1
        assert len(pages[0]) > 0
        rec = pages[0][0]
        assert "expediente" in rec
        assert "estado" in rec
        assert "organo" in rec

    @pytest.mark.integration
    def test_contratos_stream_first_page(self):
        """Descarga la primera página del feed de contratos menores y valida estructura."""
        f = AtomPagingFetcher({"url": CONTRATOS_MENORES_URL, "max_pages": "1", "timeout": "60"})
        pages = list(f.stream())
        assert len(pages) == 1
        assert len(pages[0]) > 0
        rec = pages[0][0]
        assert "expediente" in rec
        assert "adjudicatario" in rec

    @pytest.mark.integration
    @pytest.mark.slow
    def test_licitaciones_anio_filter(self):
        """Filtra licitaciones por año actual y verifica que todos los registros son de ese año.

        Usa el año en curso para no tener que paginar cientos de páginas hasta años anteriores.
        La lógica de corte es la misma independientemente del año elegido.
        Para ejecutar contra 2025 en producción: anio="2025", max_pages=500+.
        """
        anio = "2026"
        f = AtomPagingFetcher({
            "url": LICITACIONES_URL,
            "max_pages": "10",
            "anio": anio,
            "timeout": "60",
        })
        records = [r for chunk in f.stream() for r in chunk]
        assert len(records) > 0, f"No se obtuvieron registros del año {anio}"
        for rec in records:
            assert rec["updated"][:4] == anio, f"Registro fuera del año: {rec['updated']}"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_contratos_anio_filter(self):
        """Filtra contratos menores por año actual y verifica que todos son de ese año.

        Usa el año en curso para no tener que paginar cientos de páginas hasta años anteriores.
        Para ejecutar contra 2025 en producción: anio="2025", max_pages=2000.
        """
        anio = "2026"
        f = AtomPagingFetcher({
            "url": CONTRATOS_MENORES_URL,
            "max_pages": "10",
            "anio": anio,
            "timeout": "60",
        })
        records = [r for chunk in f.stream() for r in chunk]
        assert len(records) > 0, f"No se obtuvieron registros del año {anio}"
        for rec in records:
            assert rec["updated"][:4] == anio, f"Registro fuera del año: {rec['updated']}"
