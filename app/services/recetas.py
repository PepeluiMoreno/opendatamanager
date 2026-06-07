"""Recetas de extracción dirigida (§8b): pescar datos concretos en
ficheros-formulario (informes maquetados donde el parseo tabular solo saca ruido).

Una receta es una lista de capturas declarativas:

    [{"campo": "pmp_global_dias",
      "etiqueta": "Periodo Medio de Pago Global",
      "tipo": "numero"}]

Para cada captura se localiza la celda cuyo texto casa con `etiqueta` (regex,
sin distinguir mayúsculas) y se busca el valor en cascada:
  1. el resto de la propia celda (etiqueta y valor en la misma celda),
  2. las celdas a su derecha en la misma fila,
  3. la fila siguiente (formularios donde el dato vive bajo el rótulo).
`posicion` permite forzar una opción ("celda" | "derecha" | "debajo" | "ultima").
"ultima" toma el último valor convertible a la derecha (la última columna), no el
primero — útil cuando la fila trae cifras intermedias antes del dato buscado.

La gramática es única para XLSX y PDF: ambos se reducen a una rejilla de
celdas de texto (el PDF, por su tabla extraída o, en su defecto, por líneas).
De cada fichero sale UNA fila limpia: {capturas} — las dimensiones y la
procedencia las añade el fetcher.

Funciones puras: sin red ni BD.
"""
from __future__ import annotations

import io
import re
from typing import Any, Dict, List, Optional

_NUM_RE = re.compile(r"-?\d[\d.,]*")


def _a_numero(token: str) -> Optional[float]:
    m = _NUM_RE.search(token or "")
    if not m:
        return None
    t = m.group(0).rstrip(".,")
    if "," in t:                      # español: 139.200,00 → puntos miles, coma decimal
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1:            # 1.234.567 → puntos miles
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def _convertir(token: str, tipo: str) -> Optional[Any]:
    if tipo == "numero":
        return _a_numero(token)
    token = token.strip()
    return token or None


def _buscar_en(tokens: List[str], tipo: str) -> Optional[Any]:
    for t in tokens:
        v = _convertir(t, tipo)
        if v is not None:
            return v
    return None


def _buscar_ultimo(tokens: List[str], tipo: str) -> Optional[Any]:
    """Último convertible de la lista (no el primero). Para estados donde el
    dato vive en la ÚLTIMA columna y la fila trae cifras intermedias (p. ej.
    'Resultado Presupuestario Ajustado': el valor está tras derechos/obligaciones)."""
    ultimo = None
    for t in tokens:
        v = _convertir(t, tipo)
        if v is not None:
            ultimo = v
    return ultimo


def extraer_con_receta(grid: List[List[str]], receta: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aplica la receta sobre una rejilla de celdas. Devuelve {campo: valor}
    (valor None si la captura no encontró nada — el fallo es un dato)."""
    out: Dict[str, Any] = {}
    for cap in receta or []:
        campo = cap.get("campo")
        if not campo:
            continue
        rx = re.compile(str(cap.get("etiqueta", "")), re.IGNORECASE)
        tipo = str(cap.get("tipo", "texto")).lower()
        posicion = cap.get("posicion")  # None = cascada
        valor = None
        for i, fila in enumerate(grid):
            for j, celda in enumerate(fila):
                m = rx.search(celda or "")
                if not m:
                    continue
                resto = (celda or "")[m.end():]
                if posicion in (None, "celda"):
                    valor = _convertir(resto, tipo)
                if valor is None and posicion in (None, "derecha"):
                    valor = _buscar_en(fila[j + 1:], tipo)
                if valor is None and posicion in (None, "debajo") and i + 1 < len(grid):
                    valor = _buscar_en(grid[i + 1], tipo)
                if valor is None and posicion == "ultima":
                    valor = _buscar_ultimo(fila[j + 1:], tipo)
                if valor is not None:
                    break
            if valor is not None:
                break
        out[campo] = valor
    return out


# ── Constructores de rejilla ──────────────────────────────────────────────────

def grid_de_excel(content: bytes) -> List[List[str]]:
    import pandas as pd
    raw = pd.read_excel(io.BytesIO(content), header=None, dtype=str).fillna("")
    return [[str(c).strip() for c in fila] for fila in raw.values.tolist()]


def grid_de_pdf(content: bytes) -> List[List[str]]:
    """Tabla extraída si la hay; si no, cada línea de texto es una fila de una
    celda (la cascada 'misma celda' pesca el valor dentro de la línea)."""
    import pdfplumber
    grid: List[List[str]] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            tabla = page.extract_table()
            if tabla:
                grid.extend([[str(c or "").strip() for c in fila] for fila in tabla])
            else:
                texto = page.extract_text() or ""
                grid.extend([[linea.strip()] for linea in texto.splitlines() if linea.strip()])
    return grid


def grid_de_fichero(content: bytes, fmt: str) -> List[List[str]]:
    fmt = (fmt or "").lower()
    if fmt in ("xlsx", "xls"):
        return grid_de_excel(content)
    if fmt == "pdf":
        return grid_de_pdf(content)
    # csv/tsv y demás texto plano
    texto = content.decode("utf-8", errors="replace")
    sep = ";" if ";" in texto.splitlines()[0] else ","
    return [[c.strip() for c in linea.split(sep)] for linea in texto.splitlines() if linea.strip()]
