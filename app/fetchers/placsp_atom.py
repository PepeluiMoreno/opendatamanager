"""Fetcher de licitaciones de PLACSP vía datos abiertos (sindicación ATOM/CODICE).

La Plataforma de Contratación del Sector Público publica las licitaciones del
perfil del contratante (sin contratos menores) como un feed ATOM paginado por
`rel="next"` (más reciente primero), con el XML CODICE embebido en cada entry.

Este fetcher recorre el feed hacia atrás en el tiempo hasta `max_pages` y aplana
cada licitación a un registro plano. El parseo busca por *nombre local* de
etiqueta (ignorando el namespace) para ser robusto a versiones de CODICE.

Params:
    atom_url     URL del índice de sindicación (p. ej. sindicación 643).
    max_pages    Límite de páginas a recorrer (default 5; 0 = sin límite — usar con cuidado).
    delay        Segundos entre páginas (cortesía; default 1).
    timeout      Timeout por petición (default 60).
"""
import logging
from typing import Any, Dict, Generator, List, Optional
from xml.etree import ElementTree as ET

from .base import BaseFetcher

logger = logging.getLogger(__name__)

ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _first_text(el: ET.Element, localname: str) -> Optional[str]:
    """Primer descendiente cuyo nombre local coincide; devuelve su texto."""
    for d in el.iter():
        if _local(d.tag) == localname and (d.text or "").strip():
            return d.text.strip()
    return None


def _first_el(el: ET.Element, localname: str) -> Optional[ET.Element]:
    for d in el.iter():
        if _local(d.tag) == localname:
            return d
    return None


def parse_entry(entry: ET.Element) -> Dict[str, Any]:
    """Aplana una <entry> ATOM+CODICE a un registro."""
    # Enlace al detalle de la licitación
    url = None
    for link in entry.findall(f"{ATOM_NS}link"):
        if link.get("rel") in (None, "alternate", "enclosure"):
            url = link.get("href")
            if url:
                break

    proyecto = _first_el(entry, "ProcurementProject")
    objeto = _first_text(proyecto, "Name") if proyecto is not None else None
    tipo = _first_text(proyecto, "TypeCode") if proyecto is not None else None
    subtipo = _first_text(proyecto, "SubTypeCode") if proyecto is not None else None

    # Órgano de contratación (parte localizada)
    organo = None
    parte = _first_el(entry, "LocatedContractingParty")
    if parte is not None:
        nombre_parte = _first_el(parte, "PartyName")
        if nombre_parte is not None:
            organo = _first_text(nombre_parte, "Name")

    # Adjudicatario (si la licitación está adjudicada)
    adjudicatario = None
    ganador = _first_el(entry, "WinningParty")
    if ganador is not None:
        np = _first_el(ganador, "PartyName")
        if np is not None:
            adjudicatario = _first_text(np, "Name")

    return {
        "expediente": _first_text(entry, "ContractFolderID"),
        "estado": _first_text(entry, "ContractFolderStatusCode"),
        "titulo": _first_text(entry, "title"),
        "objeto": objeto,
        "tipo_codigo": tipo,                  # CODICE ContractCode (1..) — incl. obras
        "subtipo_codigo": subtipo,
        "cpv": _first_text(entry, "ItemClassificationCode"),
        "importe": _first_text(entry, "TotalAmount"),
        "valor_estimado": _first_text(entry, "EstimatedOverallContractAmount"),
        "organo_contratacion": organo,
        "provincia": _first_text(entry, "CountrySubentity"),
        "provincia_codigo": _first_text(entry, "CountrySubentityCode"),
        "adjudicatario": adjudicatario,
        "fecha": _first_text(entry, "updated"),
        "url": url,
    }


def parse_atom_page(xml_text: str):
    """Devuelve (registros, url_siguiente)."""
    root = ET.fromstring(xml_text)
    registros = [parse_entry(e) for e in root.findall(f"{ATOM_NS}entry")]
    siguiente = None
    for link in root.findall(f"{ATOM_NS}link"):
        if link.get("rel") == "next":
            siguiente = link.get("href")
            break
    return registros, siguiente


class PlacspAtomFetcher(BaseFetcher):
    def _config(self):
        return (
            self.params.get("atom_url", ""),
            int(self.params.get("max_pages", 5)),
            float(self.params.get("delay", 1)),
            int(self.params.get("timeout", 180)),
        )

    def stream(self) -> Generator[List, None, None]:
        import time
        atom_url, max_pages, delay, timeout = self._config()
        if not atom_url:
            raise ValueError("Falta el parámetro 'atom_url' (índice de sindicación PLACSP).")
        preview_limit = getattr(self, "preview_limit", None)
        url, page, yielded = atom_url, 0, 0
        while url:
            resp = self._request(None, "GET", url, timeout=timeout,
                                  headers={"Accept": "application/atom+xml"})
            resp.raise_for_status()
            registros, siguiente = parse_atom_page(resp.text)
            if registros:
                if preview_limit:
                    registros = registros[: max(0, preview_limit - yielded)]
                yield registros
                yielded += len(registros)
            page += 1
            if preview_limit and yielded >= preview_limit:
                break
            if max_pages and page >= max_pages:
                break
            url = siguiente
            if url and delay:
                time.sleep(delay)

    def fetch(self):
        atom_url, _, _, timeout = self._config()
        resp = self._request(None, "GET", atom_url, timeout=timeout,
                             headers={"Accept": "application/atom+xml"})
        resp.raise_for_status()
        return resp.text

    def parse(self, raw):
        registros, _ = parse_atom_page(raw)
        return registros

    def normalize(self, parsed):
        return parsed
