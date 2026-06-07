"""Motor de recetas (§8b): cascada celda→derecha→debajo, números en formato
español, fallo como dato (None)."""
from app.services.recetas import extraer_con_receta, _a_numero

GRID_PMP = [
    ["", "PERIODO MEDIO DE PAGO GLOBAL A PROVEEDORES MENSUAL", ""],
    ["", "MES ENERO", ""],
    ["", "Periodo Medio de Pago Global a Proveedores Mensual", ""],
    ["", "Jerez de la Frontera", "", "", "", "", "84.89", ""],
]


def test_pmp_cascada_debajo_y_derecha():
    receta = [{"campo": "pmp_dias", "etiqueta": "Periodo Medio de Pago Global a Proveedores Mensual",
               "tipo": "numero"}]
    assert extraer_con_receta(GRID_PMP, receta) == {"pmp_dias": 84.89}


def test_valor_en_la_misma_celda_linea_pdf():
    grid = [["Periodo Medio de Pago Global a Proveedores: 91,30 días"]]
    receta = [{"campo": "pmp", "etiqueta": "Pago Global a Proveedores", "tipo": "numero"}]
    assert extraer_con_receta(grid, receta) == {"pmp": 91.30}


def test_numeros_formato_espanol():
    assert _a_numero("139.200,00") == 139200.0
    assert _a_numero("84.89") == 84.89
    assert _a_numero("1.234") == 1.234  # ambiguo: punto decimal gana sin coma


def test_captura_sin_hallazgo_es_none():
    receta = [{"campo": "inexistente", "etiqueta": "NoEstá", "tipo": "numero"}]
    assert extraer_con_receta(GRID_PMP, receta) == {"inexistente": None}


# ── §8b: liquidación — remanente de tesorería ────────────────────────────────
# Rejilla calcada del PDF real (2023, 4.1_remanente_de_tesoreria_..._ical.pdf):
# el rótulo lleva sufijo "(I - II - III)" y el valor no es adyacente (hay celdas
# vacías intercaladas), tal como lo entrega pdfplumber. La cascada "derecha"
# salta los vacíos y coge el primer número (el principal), no el de la última col.
GRID_REMANENTE = [
    ["", "I. Remanente de tesorería total (1 + 2 - 3 + 4)", "", "222.081.219,48", "", ""],
    ["", "II. Saldos de dudoso cobro", "", "100.000.000,00", "", ""],
    ["", "IV. Remanente de tesorería para gastos generales (I - II - III)", "", "39.677.571,37", "", "4.543.800,24"],
]


def test_liquidacion_remanente():
    receta = [
        {"campo": "remanente_tesoreria_total",
         "etiqueta": r"Remanente de Tesorer[ií]a Total", "tipo": "numero",
         "posicion": "derecha"},
        {"campo": "remanente_tesoreria_gastos_generales",
         "etiqueta": r"Remanente de Tesorer[ií]a para Gastos Generales", "tipo": "numero",
         "posicion": "derecha"},
    ]
    assert extraer_con_receta(GRID_REMANENTE, receta) == {
        "remanente_tesoreria_total": 222081219.48,
        "remanente_tesoreria_gastos_generales": 39677571.37,
    }

