"""Taxonomía al vuelo de un crawler Web Tree (§ ramas/CKAN).

Los `pathTemplate` de los candidatos codifican el árbol del portal
(`.../a06-contratos/b-convenios/{year}/14-urbanismo/{*}`). Este servicio deriva,
en memoria y sin re-crawl, el árbol de RAMAS (segmentos de ruta constantes,
ignorando dimensiones `{...}`) con agregados por nodo, para poder navegarlo y
promover una rama entera de una vez.

No define modelo nuevo: es una vista derivada de los candidatos existentes.
"""
from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse


def segmentos_constantes(path_template: str) -> List[str]:
    """Segmentos del path que NO son placeholders (`{year}`, `{*}`, ...)."""
    try:
        path = urlparse(path_template).path
    except Exception:
        path = path_template or ""
    out = []
    for s in path.split("/"):
        if not s:
            continue
        if s.startswith("{") and s.endswith("}"):
            continue
        out.append(s)
    return out


def construir_taxonomia(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Construye el árbol de ramas y lo devuelve como lista plana de nodos.

    `items`: dicts con al menos `id` y `path_template`; opcional `matched_urls`,
    `file_types` (dict), `dimensions` (lista de {kind|name}), `suggested_name`.

    Cada nodo de salida:
      path            ruta de la rama, "a06-contratos/b-convenios" (id único)
      label           segmento(s) propios tras colapsar cadenas lineales
      parent          path del nodo padre interesante (None en la raíz efectiva)
      depth           profundidad entre nodos interesantes
      num_candidatos  candidatos en TODO el subárbol
      num_directos    candidatos cuya hoja es exactamente este nodo
      num_urls        URLs acumuladas en el subárbol
      formatos        {ext: conteo} acumulado en el subárbol
      dimensiones     tipos de dimensión presentes en el subárbol (p.ej. ["year"])
      candidato_ids   ids de los candidatos directos (promovibles aquí)
    """
    # 1) Trie de segmentos constantes con agregados por nodo.
    nodos: Dict[tuple, Dict[str, Any]] = {}

    def nodo(key: tuple) -> Dict[str, Any]:
        if key not in nodos:
            nodos[key] = {"key": key, "hijos": set(), "directos": [],
                          "sub": 0, "urls": 0, "formatos": {}, "dims": set()}
        return nodos[key]

    nodo(())  # raíz
    for it in items:
        segs = tuple(segmentos_constantes(it.get("path_template", "")))
        nurls = len(it.get("matched_urls") or [])
        fts = it.get("file_types") or {}
        dims = {(d.get("kind") or d.get("name")) for d in (it.get("dimensions") or []) if (d.get("kind") or d.get("name"))}
        for i in range(len(segs) + 1):
            n = nodo(segs[:i])
            n["sub"] += 1
            n["urls"] += nurls
            for ft, c in fts.items():
                n["formatos"][ft] = n["formatos"].get(ft, 0) + int(c)
            n["dims"] |= dims
            if i < len(segs):
                n["hijos"].add(segs[: i + 1])
        nodo(segs)["directos"].append(it.get("id"))

    # 2) Colapsar cadenas lineales: un nodo es "interesante" si es la raíz, si
    #    ramifica (>1 hijo) o si tiene candidatos directos. Los nodos de paso se
    #    absorben en la etiqueta del siguiente interesante.
    def interesante(key: tuple) -> bool:
        n = nodos[key]
        return key == () or len(n["hijos"]) > 1 or len(n["directos"]) > 0

    salida: List[Dict[str, Any]] = []

    def emitir(key: tuple, parent_path, depth: int, etiqueta_acc: List[str]):
        n = nodos[key]
        etiqueta_acc = etiqueta_acc + ([key[-1]] if key else [])
        if interesante(key):
            path = "/".join(key)
            salida.append({
                "path": path,
                "label": "/".join(etiqueta_acc) or "(raíz)",
                "parent": parent_path,
                "depth": depth,
                "num_candidatos": n["sub"],
                "num_directos": len(n["directos"]),
                "num_urls": n["urls"],
                "formatos": dict(n["formatos"]),
                "dimensiones": sorted(d for d in n["dims"] if d),
                "candidato_ids": list(n["directos"]),
            })
            for h in sorted(n["hijos"]):
                emitir(h, path, depth + 1, [])
        else:
            # nodo de paso: no se emite; su etiqueta se acumula en el hijo único
            for h in sorted(n["hijos"]):
                emitir(h, parent_path, depth, etiqueta_acc)

    emitir((), None, 0, [])
    return salida


def _segmentos_crudos(path_template: str) -> List[str]:
    """Segmentos del path TAL CUAL, conservando placeholders (`{year}`, `{*}`)."""
    try:
        path = urlparse(path_template).path
    except Exception:
        path = path_template or ""
    return [s for s in path.split("/") if s]


def _firma_forma(segs: List[str]) -> tuple:
    """Firma estructural: longitud + qué posiciones son placeholders (y cuál)."""
    return tuple((i, s) for i, s in enumerate(segs) if s.startswith("{") and s.endswith("}"))


def fundir_rama(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Funde las hojas de una rama en uno o varios recursos generalizados.

    Cada hoja (candidato) aporta su `path_template`. Las hojas con la MISMA forma
    estructural (misma longitud y placeholders en las mismas posiciones) se funden
    en un recurso: las posiciones cuyo valor CONSTANTE varía entre hojas se abren
    como una dimensión derivada (`kind="branch"`), además de las dimensiones ya
    detectadas (year, ...). Hojas de formas distintas → fusiones distintas.

    Devuelve, por cada forma, un dict:
      path_template   plantilla generalizada (`.../{year}/{rama1}/{*}`)
      dimensions      dimensiones originales alineadas + derivadas
      matched_urls    unión de todas las hojas
      file_types      suma de conteos
      candidato_ids   ids fundidos
      num_hojas       nº de hojas fundidas
    """
    if not items:
        return []

    # Agrupar por forma estructural.
    grupos: Dict[tuple, List[Dict[str, Any]]] = {}
    for it in items:
        segs = _segmentos_crudos(it.get("path_template", ""))
        grupos.setdefault(_firma_forma(segs), []).append(it)

    fusiones: List[Dict[str, Any]] = []
    for _firma, grupo in grupos.items():
        seg_lists = [_segmentos_crudos(it.get("path_template", "")) for it in grupo]
        n = len(seg_lists[0])
        plantilla: List[str] = []
        derivadas: List[Dict[str, Any]] = []
        contador = 0
        for i in range(n):
            col = {sl[i] for sl in seg_lists}
            tok = seg_lists[0][i]
            if tok.startswith("{") and tok.endswith("}"):
                plantilla.append(tok)                       # placeholder existente ({year}, {*})
            elif len(col) == 1:
                plantilla.append(tok)                        # constante común
            else:
                contador += 1
                name = f"rama{contador}"
                plantilla.append("{" + name + "}")           # segmento que varía → dimensión
                derivadas.append({
                    "kind": "branch", "name": name, "in_filename": False,
                    "segment_index": i, "sample_values": sorted(col),
                })

        # Reconstruir path completo con el esquema+host del primero.
        base = grupo[0].get("path_template", "")
        try:
            pr = urlparse(base)
            prefijo = f"{pr.scheme}://{pr.netloc}" if pr.scheme else ""
        except Exception:
            prefijo = ""
        path_template = prefijo + "/" + "/".join(plantilla)

        # Dimensiones: las originales de la primera hoja (year, ...) + las derivadas.
        dims_orig = list(grupo[0].get("dimensions") or [])
        # Unión de URLs y file_types.
        urls: List[str] = []
        fts: Dict[str, int] = {}
        ids: List[Any] = []
        for it in grupo:
            for u in (it.get("matched_urls") or []):
                if u not in urls:
                    urls.append(u)
            for ft, c in (it.get("file_types") or {}).items():
                fts[ft] = fts.get(ft, 0) + int(c)
            if it.get("id") is not None:
                ids.append(it["id"])

        fusiones.append({
            "path_template": path_template,
            "dimensions": dims_orig + derivadas,
            "matched_urls": urls,
            "file_types": fts,
            "candidato_ids": ids,
            "num_hojas": len(grupo),
        })

    return fusiones
