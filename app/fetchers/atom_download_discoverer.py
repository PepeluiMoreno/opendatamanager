"""
AtomDownloadDiscoverer — Descubridor de servicios ATOM de descarga (INSPIRE / OpenSearch).

Patrón canónico de los Download Services predefinidos de INSPIRE (Catastro, IGN,
y casi cualquier IDE europea): un ATOM de servicio cuyos <entry> NO son registros,
sino enlaces a OTROS feeds (por territorio/gerencia/provincia) que, a su vez,
enlazan a los FICHEROS descargables (GML/GZ/ZIP) — habitualmente uno por municipio.

Esta nave nodriza recorre esa jerarquía de N niveles y emite un recurso-hijo por
cada fichero hoja, con la URL de descarga ya resuelta. Es agnóstico de dominio:
no sabe nada de Catastro ni de parcelas/edificios — solo distingue "esto es un
sub-feed, desciendo" de "esto es un fichero, lo propongo", por el type/extensión
del <link>. El parseo del payload (p. ej. GML→features) es del consumidor o de la
especie-hoja; aquí solo se descubre QUÉ descargar y DESDE DÓNDE.

Clasificación de cada <entry> (por sus <link>):
  · enlace a fichero  (ext en leaf_exts, o type zip/gzip/octet-stream) -> HOJA -> se propone.
  · enlace a sub-feed (type atom/rss, o href .xml/.atom)               -> se DESCIENDE.
La hoja gana sobre el sub-feed si una entrada tuviera ambos.

Filtro opt-in `filtro_incluir`: lista de subcadenas; una hoja pasa solo si su
título/id/href contiene alguna. Para Catastro se pasan los códigos de municipio
(p. ej. ["11020"] para Jerez) — pero el mecanismo es genérico.

Cortesía: las lecturas de feed pasan por self._request, así que heredan reintentos
y, si el recurso fija rate_limit_per_second/request_delay_ms/max_per_hour, el
throttle por host. Esas mismas claves se propagan a los hijos para que la descarga
masiva sea igual de respetuosa.

modos: ["descubrir"].
"""
from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from app.fetchers.base import BaseDiscoverer

logger = logging.getLogger(__name__)

# Claves de cortesía que se propagan tal cual desde el descubridor a cada hijo.
_THROTTLE_KEYS = ("rate_limit_per_second", "request_delay_ms", "max_per_hour")
_DEFAULT_LEAF_EXTS = ("zip", "gz", "gml", "tar", "7z", "rar", "tgz")


def _localname(tag: str) -> str:
    """Nombre local de una etiqueta, ignorando el namespace ('{ns}entry' -> 'entry')."""
    return tag.rsplit("}", 1)[-1].lower() if "}" in tag else tag.lower()


def _ext(href: str) -> str:
    path = urlparse(href).path.lower()
    return path.rsplit(".", 1)[-1] if "." in path.rsplit("/", 1)[-1] else ""


class AtomDownloadDiscoverer(BaseDiscoverer):

    def _cfg(self) -> Dict[str, Any]:
        p = self.params

        def _as_list(v) -> List[str]:
            if not v:
                return []
            if isinstance(v, list):
                return [str(x).strip() for x in v if str(x).strip()]
            s = str(v).strip()
            if s.startswith("["):
                try:
                    return [str(x).strip() for x in json.loads(s) if str(x).strip()]
                except Exception:
                    pass
            return [t.strip() for t in s.split(",") if t.strip()]

        leaf_exts = _as_list(p.get("leaf_exts")) or list(_DEFAULT_LEAF_EXTS)
        child_params = p.get("child_params")
        if isinstance(child_params, str):
            child_params = json.loads(child_params) if child_params.strip() else {}
        return {
            "url": p.get("url"),
            "child": p.get("child_fetcher") or "Compressed File",
            "filtro": _as_list(p.get("filtro_incluir")),
            "leaf_exts": {e.lower().lstrip(".") for e in leaf_exts},
            "max_depth": int(p.get("max_depth", 0) or 0),       # 0 = auto por type/ext
            "max_entries": int(p.get("max_entries", 0) or 0),    # 0 = sin tope
            "max_feeds": int(p.get("max_feeds", 500) or 500),    # cota dura anti-bucle
            "child_params": child_params or {},
            "timeout": int(p.get("timeout", 60) or 60),
        }

    def _clasificar_link(self, href: str, type_attr: str, leaf_exts: set) -> Optional[str]:
        """'leaf' | 'feed' | None (enlace no utilizable)."""
        if not href:
            return None
        t = (type_attr or "").lower()
        ext = _ext(href)
        if ext in leaf_exts or "zip" in t or "gzip" in t or "octet-stream" in t:
            return "leaf"
        if "atom" in t or "rss" in t or ext in ("xml", "atom", "rss"):
            return "feed"
        return None

    def _links_de_entrada(self, entry: ET.Element) -> List[Tuple[str, str, str]]:
        """[(href, rel, type)] de una <entry> Atom o <item> RSS."""
        out: List[Tuple[str, str, str]] = []
        for el in entry.iter():
            ln = _localname(el.tag)
            if ln == "link":
                href = el.get("href") or (el.text or "").strip()  # Atom: @href; RSS: texto
                if href:
                    out.append((href, (el.get("rel") or "").lower(), el.get("type") or ""))
            elif ln in ("enclosure", "url") and (el.get("url") or el.text):
                out.append(((el.get("url") or el.text or "").strip(), "enclosure", el.get("type") or ""))
        return out

    def _clave_match(self, entry: ET.Element, href: str) -> str:
        partes = [href]
        for el in entry.iter():
            if _localname(el.tag) in ("title", "id") and el.text:
                partes.append(el.text.strip())
        return " ".join(partes)

    def _entradas(self, root: ET.Element) -> List[ET.Element]:
        return [el for el in root.iter() if _localname(el.tag) in ("entry", "item")]

    def propose(self) -> List[Dict[str, Any]]:
        cfg = self._cfg()
        if not cfg["url"]:
            raise ValueError("AtomDownloadDiscoverer: falta el parámetro 'url' (feed de servicio).")

        throttle_passthrough = {k: self.params[k] for k in _THROTTLE_KEYS if self.params.get(k) not in (None, "")}

        visitados: set = set()
        # cola de (feed_url, profundidad)
        cola: deque = deque([(cfg["url"], 0)])
        hojas: List[Tuple[str, str]] = []   # (href, clave_match)
        feeds_leidos = 0
        descartadas_filtro = 0

        while cola:
            feed_url, depth = cola.popleft()
            if feed_url in visitados:
                continue
            visitados.add(feed_url)
            if feeds_leidos >= cfg["max_feeds"]:
                logger.warning(f"[atom-discover] tope de feeds ({cfg['max_feeds']}) alcanzado; corto el descenso.")
                break

            resp = self._request(None, "GET", feed_url, timeout=cfg["timeout"])
            resp.raise_for_status()
            feeds_leidos += 1
            try:
                root = ET.fromstring(resp.text)
            except ET.ParseError as e:
                logger.warning(f"[atom-discover] feed no parseable, lo salto: {feed_url} ({e})")
                continue

            forzar_hoja = cfg["max_depth"] > 0 and depth >= cfg["max_depth"]

            for entry in self._entradas(root):
                links = self._links_de_entrada(entry)
                href_hoja = href_feed = None
                for href, _rel, type_attr in links:
                    clase = "leaf" if forzar_hoja else self._clasificar_link(href, type_attr, cfg["leaf_exts"])
                    if clase == "leaf" and href_hoja is None:
                        href_hoja = href
                    elif clase == "feed" and href_feed is None:
                        href_feed = href
                if href_hoja:                       # la hoja gana sobre el sub-feed
                    hojas.append((href_hoja, self._clave_match(entry, href_hoja)))
                elif href_feed:
                    cola.append((href_feed, depth + 1))

        # Filtro opt-in por subcadenas (p. ej. códigos de municipio).
        proposals: List[Dict[str, Any]] = []
        vistos_href: set = set()
        for href, clave in hojas:
            if cfg["filtro"] and not any(sub in clave for sub in cfg["filtro"]):
                descartadas_filtro += 1
                continue
            if href in vistos_href:
                continue
            vistos_href.add(href)
            nombre = href.rsplit("/", 1)[-1] or href
            target_params = {"url": href, "format": _ext(href) or "zip"}
            target_params.update(cfg["child_params"])
            target_params.update(throttle_passthrough)
            proposals.append({
                "suggested_name": nombre[:200],
                "matched_urls": [href],
                "file_types": {_ext(href) or "?": 1},
                "confidence": 0.95,
                "target_fetcher_code": cfg["child"],
                "target_params": target_params,
            })
            if cfg["max_entries"] and len(proposals) >= cfg["max_entries"]:
                break

        self.profile_stats = {
            "total_files": len(proposals),
            "feeds_leidos": feeds_leidos,
            "hojas_encontradas": len(hojas),
            "descartadas_por_filtro": descartadas_filtro,
        }
        logger.info(f"[atom-discover] {feeds_leidos} feed(s) recorridos, {len(hojas)} hoja(s); "
                    f"filtro fuera: {descartadas_filtro} -> {len(proposals)} hijo(s).")
        return proposals
