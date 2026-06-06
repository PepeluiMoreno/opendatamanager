"""Segunda pasada del inferer: consolidación de plantillas hermanas.

La primera pasada plantilla cada URL con reconocedores tipados (year, month,
quarter, date). Lo que esos reconocedores no capturan queda como literal, así
que ficheros como:

    {year}-002_Resolucion.pdf
    {year}-004_Resolucion.pdf
    {year}-005_Resolucion.pdf

producen UNA plantilla por número → un aluvión de propuestas de un solo
documento. Esta pasada detecta que esas plantillas son idénticas salvo en UN
átomo (el 002/004/005), que ese átomo toma ≥ MIN_GENERIC valores distintos y
que no es de ningún tipo reconocido, y las colapsa en una sola plantilla con
una dimensión genérica `{code}`. El operador la renombra al promover.

Función pura: opera sobre las plantillas ya agrupadas, sin red ni BD.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

MIN_GENERIC = 3            # nº mínimo de valores distintos para considerar enumeración
_SEP_RE = re.compile(r"([-_.])")
_PLACEHOLDER_RE = re.compile(r"^\{.+\}$")


def _atomize(template_tuple: Tuple[str, ...]) -> List[str]:
    """Plantilla → lista plana de átomos: cada segmento de path es un átomo y el
    filename se trocea por separadores (-, _, .) conservándolos."""
    atoms: List[str] = list(template_tuple[:-1])
    atoms.append("\x00")  # frontera path|filename para no fundir un seg con un token
    atoms.extend(p for p in _SEP_RE.split(template_tuple[-1]) if p != "")
    return atoms


def _deatomize(atoms: List[str]) -> Tuple[str, ...]:
    """Inverso de _atomize: reconstruye la tupla (segmentos..., filename)."""
    boundary = atoms.index("\x00")
    segs = atoms[:boundary]
    fname = "".join(atoms[boundary + 1:])
    return tuple(list(segs) + [fname])


def _es_valor(atom: str) -> bool:
    """Átomo candidato a variar: token alfanumérico que no es placeholder, ni
    separador, ni extensión conocida."""
    if atom in ("\x00", "-", "_", ".") or _PLACEHOLDER_RE.match(atom):
        return False
    if atom.lower() in ("pdf", "xlsx", "xls", "csv", "tsv"):
        return False
    return bool(atom.strip())


def consolidate(
    grouped: Dict[Tuple[str, str, Tuple[str, ...]], List[Dict[str, Any]]],
    grouped_dims: Dict[Tuple[str, str, Tuple[str, ...]], List[List[Dict[str, Any]]]],
) -> Tuple[Dict, Dict]:
    """Colapsa grupos hermanos que difieren en un único átomo de valor con
    cardinalidad ≥ MIN_GENERIC. Itera hasta punto fijo (permite colapsar varias
    posiciones: p. ej. número de resolución y, en otra pasada, mes embebido)."""
    grouped = dict(grouped)
    grouped_dims = dict(grouped_dims)

    cambiado = True
    while cambiado:
        cambiado = False
        # indexar por (scheme, netloc, longitud_atomos, posicion_enmascarada)
        atoms_by_key = {k: _atomize(k[2]) for k in grouped}
        for (scheme, netloc, _tpl), atoms in list(atoms_by_key.items()):
            pass

        # buscar la mejor posición de colapso entre todas las claves
        buckets: Dict[Tuple[Any, ...], List[Tuple[Tuple, int]]] = defaultdict(list)
        for key, atoms in atoms_by_key.items():
            scheme, netloc, _ = key
            for i, atom in enumerate(atoms):
                if not _es_valor(atom):
                    continue
                masked = tuple(a if j != i else "\x01" for j, a in enumerate(atoms))
                buckets[(scheme, netloc, len(atoms), i, masked)].append((key, i))

        # elegir el bucket más grande con cardinalidad de valores distintos ≥ MIN
        mejor = None
        for bkey, miembros in buckets.items():
            if len(miembros) < MIN_GENERIC:
                continue
            valores = {atoms_by_key[k][i] for k, i in miembros}
            if len(valores) < MIN_GENERIC:
                continue
            if mejor is None or len(miembros) > len(mejor[1]):
                mejor = (bkey, miembros)

        if mejor is None:
            break

        (scheme, netloc, _n, idx, _masked), miembros = mejor
        # construir la clave consolidada (átomo variable → {code})
        ejemplo = list(atoms_by_key[miembros[0][0]])
        ejemplo[idx] = "{code}"
        nueva_tpl = _deatomize(ejemplo)
        nueva_key = (scheme, netloc, nueva_tpl)

        entries_acc: List[Dict[str, Any]] = []
        dims_acc: List[List[Dict[str, Any]]] = []
        for key, i in miembros:
            valor = atoms_by_key[key][i]
            for entry, edims in zip(grouped[key], grouped_dims[key]):
                entries_acc.append(entry)
                dims_acc.append(list(edims) + [{
                    "name": "code", "kind": "code", "segment_index": idx,
                    "in_filename": True, "value": valor,
                }])
            del grouped[key]
            del grouped_dims[key]

        # fusionar con un consolidado previo de la misma plantilla si existiera
        if nueva_key in grouped:
            grouped[nueva_key].extend(entries_acc)
            grouped_dims[nueva_key].extend(dims_acc)
        else:
            grouped[nueva_key] = entries_acc
            grouped_dims[nueva_key] = dims_acc
        cambiado = True

    return grouped, grouped_dims


TYPED_KINDS = {"year", "month", "quarter", "date"}


def _dims_de(grouped_dims_grupo: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return grouped_dims_grupo[0] if grouped_dims_grupo else []


PERIODIC_KINDS = {"month", "quarter", "date"}
SMALL_FOLDER = 3  # nº de series distintas bajo una carpeta por debajo del cual se conservan sueltas


def bundle_residuals(
    grouped: Dict[Tuple[str, str, Tuple[str, ...]], List[Dict[str, Any]]],
    grouped_dims: Dict[Tuple[str, str, Tuple[str, ...]], List[List[Dict[str, Any]]]],
) -> Tuple[Dict, Dict]:
    """Distingue *serie* de *pila*.

    - Serie: tiene alguna dimensión tipada (year/month/quarter/date) y NINGUNA
      dimensión genérica `{code}`. Es un dataset que se repite limpio por su
      dimensión → se conserva tal cual.
    - Pila: todo lo demás (carpetas con documentos heterogéneos, donde lo que
      varía es un `{code}`). Se reagrupa por su carpeta-plantilla (ignorando el
      filename) en UNA propuesta-bundle con filename `{*}`: "todos los ficheros
      de esta carpeta por año", en vez de una propuesta por documento.
    """
    series: Dict = {}
    series_dims: Dict = {}
    por_carpeta: Dict[Tuple, List[Tuple]] = defaultdict(list)        # candidatas a fundir
    year_only_por_carpeta: Dict[Tuple, List[Tuple]] = defaultdict(list)

    for key, entries in grouped.items():
        dims = _dims_de(grouped_dims[key])
        kinds = {d["kind"] for d in dims}
        scheme, netloc, tpl = key
        carpeta = (scheme, netloc, tpl[:-1])
        if kinds & PERIODIC_KINDS and "code" not in kinds:
            # serie periódica real (mes/trimestre/fecha) → siempre suelta
            series[key] = entries
            series_dims[key] = grouped_dims[key]
        elif (kinds & TYPED_KINDS) and "code" not in kinds:
            # serie solo-anual: depende de cuántas haya en su carpeta
            year_only_por_carpeta[carpeta].append(key)
            por_carpeta[carpeta].append(key)
        else:
            # pila (varía un {code} u otra cosa no tipada)
            por_carpeta[carpeta].append(key)

    # Carpetas pequeñas con solo-anuales y sin pilas → conservar sueltas;
    # el resto (muchas series o presencia de pilas) → un bundle por carpeta.
    for carpeta, keys in por_carpeta.items():
        solo_anuales = year_only_por_carpeta.get(carpeta, [])
        hay_pila = len(keys) > len(solo_anuales)
        if not hay_pila and len(solo_anuales) <= SMALL_FOLDER:
            for k in solo_anuales:
                series[k] = grouped[k]
                series_dims[k] = grouped_dims[k]
            continue
        # fundir toda la carpeta en un bundle
        scheme, netloc, carpeta_tpl = carpeta
        entries_acc: List[Dict[str, Any]] = []
        dims_acc: List[List[Dict[str, Any]]] = []
        for k in keys:
            for entry, edims in zip(grouped[k], grouped_dims[k]):
                entries_acc.append(entry)
                typed = [d for d in edims if d["kind"] in TYPED_KINDS and not d["in_filename"]]
                dims_acc.append(typed)
        nueva_tpl = tuple(list(carpeta_tpl) + ["{*}"])
        series[(scheme, netloc, nueva_tpl)] = entries_acc
        series_dims[(scheme, netloc, nueva_tpl)] = dims_acc

    return series, series_dims


