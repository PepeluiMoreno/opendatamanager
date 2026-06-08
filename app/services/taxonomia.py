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
