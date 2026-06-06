"""Detección de cabecera en Excel: las filas-pancarta antes de la cabecera real
no deben convertirse en nombres de columna (bug cazado en prod con la
'Ejecución de gastos de publicidad' de Jerez)."""
import io
import openpyxl
from app.fetchers.file_parsers import _parse_excel


def _xlsx(filas):
    wb = openpyxl.Workbook()
    ws = wb.active
    for fila in filas:
        ws.append(fila)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_pancarta_antes_de_la_cabecera():
    contenido = _xlsx([
        ["226 02 PUBLICIDAD Y PROPAGANDA EJECUCION ABRIL 2026", None, None, None],
        ["Descripción", "Créditos Totales", "Total gastado", "Saldo de Crédito"],
        ["Publicidad Comunicación", "139200,00", "102439,73", "36760,27"],
        ["Publicidad Presidencia", "13600,00", "0,00", "13600,00"],
    ])
    filas = _parse_excel(contenido, {}, "xlsx")
    assert "descripcion" in filas[0] and "creditos_totales" in filas[0]
    assert filas[0]["descripcion"] == "Publicidad Comunicación"
    assert len(filas) == 2


def test_cabecera_en_primera_fila_sigue_igual():
    contenido = _xlsx([
        ["org", "descripcion", "importe"],
        ["CO-CO", "Radio municipal", "696905.2"],
    ])
    filas = _parse_excel(contenido, {}, "xlsx")
    assert filas == [{"org": "CO-CO", "descripcion": "Radio municipal", "importe": "696905.2"}]


def test_header_row_explicito_manda():
    contenido = _xlsx([
        ["lo que sea", "x"],
        ["a", "b"],
        ["1", "2"],
    ])
    filas = _parse_excel(contenido, {"header_row": 1}, "xlsx")
    assert filas == [{"a": "1", "b": "2"}]


def test_columnas_integramente_vacias_se_podan():
    contenido = _xlsx([
        ["", "a", "b", ""],
        ["", "1", "2", ""],
        ["", "3", "4", ""],
    ])
    filas = _parse_excel(contenido, {}, "xlsx")
    assert filas == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
