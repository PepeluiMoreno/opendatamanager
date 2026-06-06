"""Bautizador: códigos de sección conservados con dignidad, acentos, sin ruido."""
from app.services.grouping.naming import suggested_name


def test_deuda_anual_estilo_corcho():
    n = suggested_name(["a-infopublica", "a07-economica", "c-deuda", "{year}", "deuda"],
                       "{*}", [{"kind": "year"}])
    assert n == "A07-Información Económica — C-Deuda anual"


def test_camel_y_placeholders_de_filename():
    n = suggested_name(["a-infopublica", "a07-economica", "a-presupuesto", "{year}", "03-ejecucionAyto"],
                       "{*}", [{"kind": "year"}])
    assert "Ejecución Ayto." in n and "03-" in n
    n2 = suggested_name(["a-infopublica", "a07-economica", "c-deuda", "{year}", "pmp"],
                        "Informe_PMP_{year}_{month}", [{"kind": "year"}, {"kind": "month"}])
    assert n2.endswith("Informe PMP mensual") and "{" not in n2
