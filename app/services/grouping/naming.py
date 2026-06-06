"""Generación de nombre legible a partir del path templatizado y las dimensiones."""

from __future__ import annotations

from typing import Any, Dict, List

from .templating import humanize


# Tokens que aparecen como carpetas administrativas en muchos CMS (TypO3, WordPress…)
# y no aportan al nombre del recurso. Se filtran del suggested_name; nunca del grouping.
_NOISE_NAME_SEGMENTS = {
    "transparencia", "fileadmin", "documentos", "infopublica",
    "content", "files", "docs", "public", "wp-content", "uploads",
    "media", "assets", "data", "datos",
}


import re

# Código de ordenación del portal: a07-, c-, 04-, b2-… Se conserva (es señalética
# para quien navega el portal) pero en mayúsculas y pegado a su etiqueta.
_CODE_RE = re.compile(r"^([a-z]{1,3}\d{0,3}|\d{1,3})-(.+)$", re.IGNORECASE)

# Etiquetas de sección completas (rótulos de menú habituales en portales de
# transparencia españoles) y acentos del vocabulario administrativo común.
_SEGMENT_LABELS = {
    "economica": "Información Económica",
    "otrainfo": "Otra Información",
    "cuentageneral": "Cuenta General",
    "resolucionesalcaldia": "Resoluciones de Alcaldía",
    "planajuste": "Plan de Ajuste",
    "planajuste seg": "Plan de Ajuste (seguimiento)",
    "plantesoreria": "Plan de Tesorería",
    "plancontrolfinanciero": "Plan de Control Financiero",
    "planestrategicosubvenciones": "Plan Estratégico de Subvenciones",
    "plansostenibilidad": "Plan de Sostenibilidad",
    "pmp": "PMP",
}
_WORD_LABELS = {
    "economica": "Económica", "ejecucion": "Ejecución", "liquidacion": "Liquidación",
    "planificacion": "Planificación", "informacion": "Información",
    "tesoreria": "Tesorería", "alcaldia": "Alcaldía", "normativa": "Normativa",
    "institucional": "Institucional", "contratacion": "Contratación",
    "presupuesto": "Presupuesto", "deuda": "Deuda", "morosidad": "Morosidad",
    "publicidad": "Publicidad", "subvenciones": "Subvenciones", "pmp": "PMP",
    "ayto": "Ayto.", "informe": "Informe", "estrategico": "Estratégico",
    "rectificacion": "Rectificación", "consolidada": "Consolidada",
}


def _etiqueta(texto: str) -> str:
    """Humaniza una etiqueta: rótulo de sección si lo hay; si no, palabra a
    palabra con acentos, capitalizando."""
    crudo = texto.strip().lower()
    if crudo in _SEGMENT_LABELS:
        return _SEGMENT_LABELS[crudo]
    texto = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", texto)  # camelCase → palabras
    palabras = [w for w in re.split(r"[\s_]+", humanize(texto)) if w]
    out = [_WORD_LABELS.get(w.lower(), w[:1].upper() + w[1:]) for w in palabras]
    return " ".join(out)


def _render_segmento(seg: str) -> str:
    m = _CODE_RE.match(seg)
    if m:
        return f"{m.group(1).upper()}-{_etiqueta(m.group(2))}"
    return _etiqueta(seg)


def _sin_codigo(parte: str) -> str:
    return parte.split("-", 1)[1] if "-" in parte and _CODE_RE.match(parte.lower().replace("—", "-")) else parte


def suggested_name(
    constant_path_segments: List[str],
    templated_filename: str,
    dims: List[Dict[str, Any]],
) -> str:
    """Construye un nombre legible humano para la propuesta."""
    parts: List[str] = []
    for seg in constant_path_segments:
        if seg.startswith("{") or not seg:
            continue
        crudo = seg.lower()
        m = _CODE_RE.match(crudo)
        etiqueta_cruda = m.group(2) if m else crudo
        if crudo in _NOISE_NAME_SEGMENTS or etiqueta_cruda in _NOISE_NAME_SEGMENTS:
            continue
        render = _render_segmento(seg)
        # deduplicar etiquetas consecutivas (c-deuda / deuda → una sola)
        if parts and _sin_codigo(parts[-1]).casefold() == _sin_codigo(render).casefold():
            continue
        parts.append(render)
    base = templated_filename.rsplit(".", 1)[0] if "." in templated_filename else templated_filename
    if base and not base.startswith("{"):
        # quitar los huecos de plantilla del nombre de fichero: la periodicidad
        # ya lo dice el sufijo ('Informe_PMP_{year}_{month}' → 'Informe PMP')
        limpio = re.sub(r"\{[^}]+\}", " ", base)
        limpio = re.sub(r"[\s_\-]{2,}", " ", limpio).strip(" _-")
        if limpio:
            render = _etiqueta(limpio)
            if not parts or _sin_codigo(parts[-1]).casefold() != render.casefold():
                parts.append(render)
    if not parts:
        parts.append("recurso")
    name = " — ".join(p for p in parts if p)
    if name:
        name = name[0].upper() + name[1:]

    has_year = any(d["kind"] == "year" for d in dims)
    has_month = any(d["kind"] == "month" for d in dims)
    has_quarter = any(d["kind"] == "quarter" for d in dims)
    has_date = any(d["kind"] == "date" for d in dims)
    if has_date:
        name += " por fecha"
    elif has_year and has_month:
        name += " mensual"
    elif has_year and has_quarter:
        name += " trimestral"
    elif has_year:
        name += " anual"
    elif has_month:
        name += " mensual"
    elif has_quarter:
        name += " trimestral"
    return name
