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


# ── §8b: morosidad trimestral (Ley 15/2010) ──────────────────────────────────
GRID_MOROSIDAD = [
    ["", "Informe Trimestral Ley 15/2010", "", "", "", ""],
    ["Periodo Medio de Pago (PMP)", "", "", "", "", "45,20"],
    ["Ratio de las Operaciones Pagadas", "", "", "", "", "38,10"],
    ["Ratio de Operaciones Pendientes de Pago", "", "", "", "", "12,00"],
]


def test_morosidad_trimestral():
    receta = [
        {"campo": "pmp_dias", "etiqueta": r"Periodo Medio de Pago", "tipo": "numero"},
        {"campo": "ratio_operaciones_pagadas",
         "etiqueta": r"Ratio de(?: las)? Operaciones Pagadas", "tipo": "numero"},
        {"campo": "ratio_operaciones_pendientes",
         "etiqueta": r"Ratio de(?: las)? Operaciones Pendientes", "tipo": "numero"},
    ]
    assert extraer_con_receta(GRID_MOROSIDAD, receta) == {
        "pmp_dias": 45.20,
        "ratio_operaciones_pagadas": 38.10,
        "ratio_operaciones_pendientes": 12.00,
    }


# ── §8b: carátula/resumen de la liquidación presupuestaria ────────────────────
GRID_LIQUIDACION = [
    ["Resultado Presupuestario del Ejercicio", "1.000.000,00"],
    ["Resultado Presupuestario Ajustado", "1.234.567,89"],
    ["Remanente de Tesorería para Gastos Generales", "987.654,32"],
    ["Remanente de Tesorería Total", "2.500.000,00"],
]


def test_liquidacion_caratula():
    receta = [
        {"campo": "resultado_presupuestario_ajustado",
         "etiqueta": r"Resultado Presupuestario Ajustado", "tipo": "numero"},
        {"campo": "remanente_tesoreria_gastos_generales",
         "etiqueta": r"Remanente de Tesorer[ií]a para Gastos Generales", "tipo": "numero"},
        {"campo": "remanente_tesoreria_total",
         "etiqueta": r"Remanente de Tesorer[ií]a Total", "tipo": "numero"},
    ]
    assert extraer_con_receta(GRID_LIQUIDACION, receta) == {
        "resultado_presupuestario_ajustado": 1234567.89,
        "remanente_tesoreria_gastos_generales": 987654.32,
        "remanente_tesoreria_total": 2500000.00,
    }
